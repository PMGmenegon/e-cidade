"""Orquestrador da bateria Laravel (5.4 x 12): meta, rodada, codigo de saida e protecao da baseline.

    python -m regressao.laravel.bateria gravar   --saida DIR [--alvo URL] [--confirmo-sobrescrever]
    python -m regressao.laravel.bateria comparar --saida DIR [--alvo URL] [--sem-restaurar]

`gravar` grava a baseline (regressao/baseline/laravel/) contra `Alvos.ref` (:8080, Laravel 5.4);
`comparar` roda os casos contra `Alvos.laravel_novo` (REGRESSAO_LARAVEL_NOVO_URL, padrao :8087), ou
contra `--alvo URL` (usado para provar a estabilidade contra o proprio :8080).

A baseline e a REFERENCIA PRE-MIGRACAO. Regrava-la com um sistema ja migrado destroi a comparacao;
por isso `gravar` recusa (RecusaBaseline, exit 2) sobrescrever uma baseline existente e gravar contra
um alvo que nao seja o 5.4 sem `--confirmo-sobrescrever` (e, para outro alvo, `--alvo` explicito).
Um `gravar` bem-sucedido NAO produz casos (so meta + a linha GRAVACAO no resumo): nada foi comparado.

Ordem de `comparar`: boot do alvo (se fora do ar: UM caso ERRO_AMBIENTE `laravel:boot`, o banco NAO
e restaurado) -> ambiente (docker/banco) -> baseline/meta -> restauracao (~260 s) -> casos. Tudo isso
mora em `caso.comparar`; aqui entram meta, rodada, codigo de saida e o mapeamento de erros.

Rede de seguranca: depois da validacao dos argumentos, NADA estoura sem escrever a rodada; qualquer
excecao inesperada vira UM ERRO_AMBIENTE `laravel:inesperado` (+ `erro.log` redigido), exit 2; se nem
a rodada puder ser escrita, o erro redigido vai para o stderr, exit 2.

Ids dos casos (ja namespaced): rota:<METHOD>:<uri>, auth-..., escrita-..., laravel:boot,
laravel:baseline, laravel:banco, laravel:gravacao, laravel:comparacao, laravel:inesperado,
fingerprint:probes. Duplicata residual ganha #2, #3... (meta.ids_renomeados). Chaves de
conhecidas.tsv = esses ids. INCONCLUSIVO (5xx nos dois lados etc.) conta mas NAO deixa a rodada
vermelha e NAO e aprovacao.
"""
import argparse
import json
import sys
import time
import traceback
from collections import Counter
from dataclasses import replace
from pathlib import Path

from regressao.laravel import caso
from regressao.laravel.caso import DIR_BASELINE, DIR_CASOS, ErroGravacao, ErroRequisicao, carrega_casos
from regressao.laravel.rotas import CONTAINER_PHP, DIR_APP
from regressao.laravel.token import laravel_sobe, redige
from regressao.nucleo import git
from regressao.nucleo.ambiente import alvos_do_ambiente, verifica
from regressao.nucleo.banco import ARQ_SHA256, BancoDiferente, ErroAmbienteBanco, _docker
from regressao.nucleo.conhecidas import carregar_conhecidas, marcar
from regressao.nucleo.relatorio import RodadaInvalida
from regressao.nucleo.veredito import Caso, Veredito
from regressao.php.bateria import _fim, _ids_unicos

CONHECIDAS = Path(__file__).resolve().parents[1] / "conhecidas.tsv"
AREA = "laravel"
AVISO_SEM_RESTAURAR = "banco NAO restaurado: resultado nao comparavel"
AVISO_GRAVACAO = "GRAVACAO da baseline — nao e comparacao; nenhum caso foi avaliado"
MODOS = ("gravar", "comparar")


class RecusaBaseline(ValueError):
    """`gravar` recusado para proteger a baseline pre-migracao (nada foi executado)."""


def _norm(url: str) -> str:
    return url.rstrip("/")


def _baseline_existe() -> bool:
    """Ha baseline se existe o _meta.json ou algum registro .json (um .gitkeep nao conta)."""
    d = Path(DIR_BASELINE)
    return d.is_dir() and ((d / "_meta.json").exists() or any(d.glob("*.json")))


def _metadados_ambiente(alvo: str) -> dict:
    meta: dict = {}
    try:
        meta["php_56"] = _docker(["exec", CONTAINER_PHP, "php", "-r", "echo PHP_VERSION;"], 30).decode().strip()
    except Exception as e:
        meta["php_56"] = f"indisponivel: {type(e).__name__}"
    if _norm(alvo) == _norm(alvos_do_ambiente().ref):
        try:
            saida = _docker(["exec", "-w", DIR_APP, CONTAINER_PHP, "php", "artisan", "--version"], 60)
            meta["laravel_alvo"] = saida.decode(errors="replace").strip().splitlines()[-1]
        except Exception as e:
            meta["laravel_alvo"] = f"indisponivel: {type(e).__name__}"
    else:
        meta["laravel_alvo"] = "indisponivel (alvo nao e o 5.4 de referencia)"
    meta["git_commit"] = git.commit(caso.RAIZ_REPO)
    meta.update(git.sujo(caso.RAIZ_REPO))
    try:
        meta["dump_sha256"] = ARQ_SHA256.read_text().split()[0]
    except Exception as e:
        meta["dump_sha256"] = f"indisponivel: {type(e).__name__}"
    return meta


def _meta_baseline() -> dict:
    try:
        m = json.loads((Path(DIR_BASELINE) / "_meta.json").read_text(encoding="utf-8"))
        return {"dump_sha256": m.get("dump_sha256"), "commit": m.get("commit"), "data": m.get("data"),
                "n_casos": m.get("n_casos"), "alvo": m.get("alvo")}
    except Exception as e:
        return {"erro": f"indisponivel: {type(e).__name__}"}


def _resumo_cobertura() -> dict:
    """Resumo de baseline/laravel/_cobertura.json (gerado por `python -m regressao.laravel.cobertura`)."""
    try:
        c = json.loads((Path(DIR_BASELINE) / "_cobertura.json").read_text(encoding="utf-8"))
        cobertas = sum(v["cobertas"] for v in c["por_origem"].values())
        return {"rotas_cobertas": cobertas, "rotas_total": c["total"], "classes_na_referencia": c["classes"],
                "casos_5xx_inconclusivos": len(c["casos"]["inconclusivos_5xx"]),
                "casos_rejeicao_esperada_5xx": len(c["casos"]["rejeicao_esperada_5xx"])}
    except Exception as e:
        return {"erro": f"indisponivel: {type(e).__name__}"}


def _motivo_inconclusivo(c: Caso) -> str:
    d = c.detalhe.strip()
    if d.startswith("HTTP ") and "nos dois lados" in d:
        return "5xx nos dois lados (nao exercitado)"
    return d or "sem motivo"


def _inconclusivos_por_motivo(casos: list[Caso]) -> dict[str, int]:
    return dict(Counter(_motivo_inconclusivo(c) for c in casos if c.veredito == Veredito.INCONCLUSIVO))


def _erro(id: str, e: Exception) -> Caso:
    return Caso(id, AREA, Veredito.ERRO_AMBIENTE, redige(f"{type(e).__name__}: {e}"))


class _CronometraRestauro:
    """Mede (sem alterar) o restaura_dump que `caso` chama; `segundos` fica None se nao restaurou."""
    def __init__(self):
        self.segundos: float | None = None

    def __enter__(self):
        self._orig = caso.restaura_dump

        def medido(*a, **k):
            t0 = time.monotonic()
            try:
                return self._orig(*a, **k)
            finally:
                self.segundos = round(time.monotonic() - t0, 1)
        caso.restaura_dump = medido
        return self

    def __exit__(self, *exc):
        caso.restaura_dump = self._orig


def roda_bateria_laravel(diretorio_saida: Path, modo: str, alvo: str | None = None,
                         confirmo_sobrescrever: bool = False, restaurar: bool = True) -> int:
    if modo not in MODOS:
        raise ValueError(f"modo invalido: {modo!r}; validos: {', '.join(MODOS)}")
    if modo == "gravar" and not restaurar:
        raise ValueError("--sem-restaurar nao vale para gravar: a baseline nasce sempre de banco restaurado")
    diretorio_saida = Path(diretorio_saida)
    estado: dict = {"url": alvo or "(nao resolvido)", "meta": {"modo": modo, "comparavel": restaurar,
                                                               "restauracao_s": None},
                    "avisos": [], "inicio": time.monotonic()}
    try:
        return _executa(diretorio_saida, modo, alvo, confirmo_sobrescrever, restaurar, estado)
    except RecusaBaseline:
        raise
    except Exception as e:  # rede de seguranca: nunca estourar sem rodada
        return _falha_inesperada(diretorio_saida, estado, e)


def _falha_inesperada(diretorio: Path, estado: dict, e: Exception) -> int:
    msg = redige(f"{type(e).__name__}: {e}")
    try:
        diretorio.mkdir(parents=True, exist_ok=True)
        (diretorio / "erro.log").write_text(redige(traceback.format_exc()), encoding="utf-8", newline="\n")
        estado["meta"]["erro_log"] = "erro.log"
    except Exception:
        pass
    try:
        return _termina(diretorio, estado, [Caso("laravel:inesperado", AREA, Veredito.ERRO_AMBIENTE, msg)])
    except Exception as e2:
        print(f"erro: {msg}; e a rodada nao pode ser escrita em {diretorio}: "
              f"{redige(f'{type(e2).__name__}: {e2}')}", file=sys.stderr)
        return 2


def _termina(diretorio: Path, estado: dict, casos: list[Caso]) -> int:
    meta, avisos, url = estado["meta"], estado["avisos"], estado["url"]
    casos, renomeados = _ids_unicos(casos)
    meta["ids_renomeados"] = renomeados
    if renomeados:
        avisos.append(f"{len(renomeados)} id(s) duplicado(s) renomeado(s) com #N (ver meta.ids_renomeados)")
    try:
        casos = marcar(casos, carregar_conhecidas(CONHECIDAS))
    except Exception as e:
        casos.append(_erro("laravel:conhecidas", e))
    contagem = Counter(c.veredito.value for c in casos)
    meta["veredictos"] = {v.value: contagem.get(v.value, 0) for v in Veredito}
    inc = _inconclusivos_por_motivo(casos)
    if inc:
        meta["inconclusivos_por_motivo"] = inc
        avisos.append(f"{sum(inc.values())} caso(s) INCONCLUSIVO: NAO sao aprovacao (a rota nao foi "
                      "exercitada). Motivos: " + "; ".join(f"{m}: {n}" for m, n in inc.items()))
    erros = [c for c in casos if c.veredito == Veredito.ERRO_AMBIENTE]
    for c in erros[:10]:
        avisos.append(f"ERRO_AMBIENTE {c.id}: {c.detalhe.splitlines()[0] if c.detalhe else ''}")
    if len(erros) > 10:
        avisos.append(f"... e mais {len(erros) - 10} ERRO_AMBIENTE (ver resultado.json)")
    meta["baseline"] = _meta_baseline()
    meta["cobertura"] = _resumo_cobertura()
    try:
        meta.update(_metadados_ambiente(url))
    except Exception as e:
        meta["ambiente"] = f"indisponivel: {type(e).__name__}"
    meta["tempo_total_s"] = round(time.monotonic() - estado["inicio"], 1)
    return _fim(diretorio, casos, meta, avisos)


def _executa(diretorio_saida: Path, modo: str, alvo: str | None, confirmo_sobrescrever: bool,
             restaurar: bool, estado: dict) -> int:
    meta, avisos = estado["meta"], estado["avisos"]
    alvos = alvos_do_ambiente()
    if modo == "gravar":
        if alvo is not None and _norm(alvo) != _norm(alvos.ref) and not confirmo_sobrescrever:
            raise RecusaBaseline(
                f"gravar contra {alvo} recusado: a baseline e a referencia do Laravel 5.4 ({alvos.ref}). "
                "Gravar contra outro alvo exige --alvo explicito E --confirmo-sobrescrever.")
        if _baseline_existe() and not confirmo_sobrescrever:
            raise RecusaBaseline(
                f"gravar recusado: {DIR_BASELINE} ja tem baseline. Ela e a referencia pre-migracao; "
                "sobrescreve-la com um sistema migrado destroi a comparacao. Se tem certeza "
                "(ex.: regravar no 5.4 apos mudar os casos), use --confirmo-sobrescrever.")
    url = _norm(alvo if alvo is not None else (alvos.ref if modo == "gravar" else alvos.laravel_novo))
    estado["url"] = url
    meta["alvo"] = url
    if not restaurar:
        avisos.append(AVISO_SEM_RESTAURAR)
        meta["aviso"] = AVISO_SEM_RESTAURAR
        print(f"AVISO: {AVISO_SEM_RESTAURAR}", file=sys.stderr)

    def para(id: str, detalhe: str) -> int:
        return _termina(diretorio_saida, estado, [Caso(id, AREA, Veredito.ERRO_AMBIENTE, redige(detalhe))])

    # 1. comparar: o boot do alvo vem ANTES de tudo (alvo fora do ar = um unico ERRO_AMBIENTE, sem banco)
    if modo == "comparar":
        boot = laravel_sobe(url)
        if boot is not None:
            return _termina(diretorio_saida, estado, [boot])
    # 2. ambiente: so o alvo e o banco (os demais laboratorios nao fazem parte desta bateria)
    problemas = verifica(replace(alvos, ref=url, php_novo=url, laravel_novo=url, proxy=url))
    if problemas:
        return para("laravel:ambiente", "; ".join(problemas))
    # 3. casos
    try:
        casos_http = carrega_casos(DIR_CASOS)
    except Exception as e:
        return _termina(diretorio_saida, estado, [_erro("laravel:casos", e)])
    # 4. baseline + restauracao + casos (caso.gravar / caso.comparar)
    t_casos = time.monotonic()
    with _CronometraRestauro() as t:
        try:
            if modo == "gravar":
                caso.gravar(casos_http, url, DIR_BASELINE, completo=True)
                res: list[Caso] = []  # gravar NAO avalia nada: nenhum Caso (nada que pareca aprovacao)
                avisos.append(AVISO_GRAVACAO)
                meta["gravacao"] = {"n_casos": len(casos_http), "baseline": str(DIR_BASELINE)}
            else:
                res = caso.comparar(casos_http, url, DIR_BASELINE, restaurar=restaurar)
        except BancoDiferente as e:
            res = [_erro("laravel:banco", e)]
        except Exception as e:  # ErroGravacao, ErroAmbienteBanco, ErroRequisicao, RodadaInvalida e o resto
            res = [_erro("laravel:gravacao" if modo == "gravar" else "laravel:comparacao", e)]
    meta["restauracao_s"] = t.segundos
    meta["tempo_casos_s"] = round(time.monotonic() - t_casos - (t.segundos or 0), 1)
    return _termina(diretorio_saida, estado, res)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m regressao.laravel.bateria", description=__doc__.split("\n")[0])
    ap.add_argument("modo", help="gravar | comparar")
    ap.add_argument("--saida", required=True, type=Path)
    ap.add_argument("--alvo", default=None, metavar="URL")
    ap.add_argument("--confirmo-sobrescrever", action="store_true",
                    help="permite gravar sobre baseline existente / contra alvo diferente do 5.4")
    ap.add_argument("--sem-restaurar", action="store_true",
                    help="SO desenvolvimento (comparar): nao restaura o banco; resultado nao comparavel")
    a = ap.parse_args(argv)
    try:
        return roda_bateria_laravel(a.saida, a.modo, a.alvo, a.confirmo_sobrescrever, not a.sem_restaurar)
    except ValueError as e:  # modo invalido, RecusaBaseline, --sem-restaurar em gravar
        print(f"erro: {redige(str(e))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
