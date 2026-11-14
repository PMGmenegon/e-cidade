"""Orquestrador da bateria PHP (5.6 x 8.5): ambiente -> baseline -> restauracao -> sessao ->
sintaxe -> classes -> telas -> POSTs -> relatorios -> conhecidas -> escreve_rodada.

    python -m regressao.php.bateria --saida DIR [--area NOME ...] [--sem-normalizar]
        [--incluir-nao-verificados] [--sem-restaurar]
"""
import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from regressao.nucleo.ambiente import alvos_do_ambiente, verifica
from regressao.nucleo.banco import (ARQ_DUMP, ARQ_SHA256, BancoDiferente, ErroAmbienteBanco,
                                    _docker, confere_baseline, restaura_dump)
from regressao.nucleo.conhecidas import carregar_conhecidas, marcar
from regressao.nucleo.normaliza import REGRAS
from regressao.nucleo.relatorio import RodadaInvalida, escreve_rodada
from regressao.nucleo.veredito import Caso, Veredito, codigo_saida
from regressao.php.classes import roda_classes
from regressao.php.cobertura import cobertura_telas
from regressao.php.hashes import grava_hashes
from regressao.php.posts import CATALOGO as CATALOGO_POSTS
from regressao.php.posts import carrega_catalogo, roda_post
from regressao.php.relatorios import CATALOGO as CATALOGO_RELATORIOS
from regressao.php.relatorios import carrega_catalogo_relatorios, roda_relatorio
from regressao.php.sintaxe import roda_lint
from regressao.php.telas import lista_telas, obtem_sid, roda_telas, sessao_autenticada

RAIZ = Path(__file__).resolve().parents[2]
CONHECIDAS = Path(__file__).resolve().parents[1] / "conhecidas.tsv"
AREA_BATERIA = "php-bateria"
AVISO_SEM_RESTAURAR = "banco NAO restaurado: resultado nao comparavel"

# Area -> prefixos das telas de menu (atendcadarea -> db_menu -> db_itensmenu, mesma consulta de
# scratchpad/prefixos_area.py, so telas existentes em disco). Fora: `func` (patrimonial; 4 telas
# de menu mas 2993 janelas de consulta func_*.php em disco) e prefixos sem arquivo em disco.
AREAS: dict[str, tuple[str, ...]] = {
    "assistenciasocial": ("hab", "pro", "rec", "soc"),
    "cidadao": ("con", "pre"),
    "configuracao": ("amb", "ate", "cai", "con", "edu", "hab", "mat", "orc", "pat", "pro", "sys"),
    "educacao": ("bib", "edu", "esc", "mat", "mer", "pro", "rel", "sec", "tre"),
    "financeiro": ("age", "cad", "cai", "com", "con", "cus", "div", "emp", "hab", "inf", "iss",
                   "orc", "pes", "pl", "pla", "pro", "sys", "tes"),
    "gestor": ("ges",),
    "integracoes": ("edf", "efd", "eso", "sped"),
    "patrimonial": ("ac", "aco", "cad", "cai", "com", "con", "emp", "lic", "mat", "orc", "ouv",
                    "pat", "pro", "processo", "prot", "vei"),
    "recursoshumanos": ("cai", "con", "es", "eso", "lic", "pes", "rec", "rh", "sped"),
    "saude": ("age", "amb", "far", "fum", "hip", "lab", "mat", "prot", "sau", "tfd", "vac"),
    "tributario": ("agu", "amb", "arr", "cad", "cai", "cem", "con", "div", "dv", "dvr", "fis",
                   "inf", "iss", "itb", "itbi", "jur", "mar", "not", "pre", "pro", "prot", "rec",
                   "sys", "tri"),
}
ALIASES = {"rh": "recursoshumanos", "assistencia": "assistenciasocial", "social": "assistenciasocial",
           "tributaria": "tributario", "configuracoes": "configuracao"}


class AreaDesconhecida(ValueError):
    pass


def _chave_area(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[\s_\-]+", "", s)
    return ALIASES.get(s, s)


def resolve_areas(areas: list[str] | None) -> tuple[list[str], list[str]]:
    """(nomes canonicos, prefixos sem repeticao). None = todas as areas. Desconhecida -> AreaDesconhecida."""
    if areas is None:
        nomes = sorted(AREAS)
    else:
        nomes = []
        for a in areas:
            k = _chave_area(a)
            if k not in AREAS:
                raise AreaDesconhecida(f"area desconhecida: {a!r}; validas: {', '.join(sorted(AREAS))}")
            if k not in nomes:
                nomes.append(k)
    prefixos: list[str] = []
    for n in nomes:
        for p in AREAS[n]:
            if p not in prefixos:
                prefixos.append(p)
    return nomes, prefixos


def _regex_prefixo(p: str) -> str:
    return rf"^{p}[0-9]*_"


def _tela_da_area(tela: str, prefixos: list[str]) -> bool:
    return any(re.match(_regex_prefixo(p), tela, re.I) for p in prefixos)


@contextmanager
def sem_normalizacao():
    """Esvazia REGRAS no proprio objeto (o default de normaliza/hash_corpo) enquanto durar o bloco,
    para as Tasks 5/7 compararem/hashearem o corpo cru. Nao alcanca o cmp.py (subprocesso)."""
    guardadas = list(REGRAS)
    REGRAS.clear()
    try:
        yield
    finally:
        REGRAS[:] = guardadas


def _classes_das_telas(telas: list[str]) -> list[str]:
    """Classes `classes/db_*_classe.php` que as telas incluem (as que existem em disco)."""
    achadas: set[str] = set()
    pad = re.compile(rb"classes/(db_[A-Za-z0-9_]+_classe\.php)")
    for t in telas:
        try:
            achadas.update(m.decode() for m in pad.findall((RAIZ / "ecidade" / t).read_bytes()))
        except OSError:
            continue
    return [f"classes/{c}" for c in sorted(achadas) if (RAIZ / "ecidade" / "classes" / c).is_file()]


def _metadados_ambiente() -> dict:
    meta: dict = {}
    for nome, cont in (("php_56", "ecidade_php56"), ("php_85", "ecidade_php85")):
        try:
            meta[nome] = _docker(["exec", cont, "php", "-r", "echo PHP_VERSION;"], 30).decode().strip()
        except Exception as e:
            meta[nome] = f"indisponivel: {e}"
    try:
        meta["git_commit"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True,
                                            text=True, timeout=15).stdout.strip()
    except Exception as e:
        meta["git_commit"] = f"indisponivel: {e}"
    try:
        meta["baseline_sha256"] = ARQ_SHA256.read_text().split()[0]
    except Exception as e:
        meta["baseline_sha256"] = f"indisponivel: {e}"
    return meta


def _passo(nome: str, area: str, fn) -> list[Caso]:
    """Um passo que falha vira ERRO_AMBIENTE desse passo; o proximo continua."""
    try:
        return list(fn())
    except Exception as e:
        return [Caso(f"passo:{nome}", area, Veredito.ERRO_AMBIENTE, f"{type(e).__name__}: {e}")]


def _fim(diretorio: Path, casos: list[Caso], meta: dict, avisos: list[str]) -> int:
    """Escreve a rodada (resumo.md ganha os avisos e a meta logo abaixo do titulo)."""
    escreve_rodada(diretorio, casos, meta)
    bloco = [""]
    if avisos:
        bloco += ["## AVISOS", ""] + [f"- **{a}**" for a in avisos] + [""]
    bloco += ["## Meta", ""] + [f"- {k}: {v}" for k, v in meta.items()] + [""]
    arq = Path(diretorio) / "resumo.md"
    linhas = arq.read_text(encoding="utf-8").split("\n")
    arq.write_text("\n".join(linhas[:1] + bloco + linhas[1:]), encoding="utf-8", newline="\n")
    return codigo_saida(casos)


def _filtra_catalogo(linhas, prefixos, todas_areas: bool, incluir_nv: bool, tela_de):
    """(a rodar, pulados nao-verificado, pulados de outra area)."""
    rodar, nv, outra = [], [], []
    for r in linhas:
        if not todas_areas and not _tela_da_area(tela_de(r), prefixos):
            outra.append(r)
        elif not r.verificado and not incluir_nv:
            nv.append(r)
        else:
            rodar.append(r)
    return rodar, nv, outra


def roda_bateria_php(diretorio_saida: Path, areas: list[str] | None = None, normalizar: bool = True,
                     incluir_nao_verificados: bool = False, restaurar: bool = True) -> int:
    nomes, prefixos = resolve_areas(areas)  # area desconhecida: levanta antes de qualquer passo
    diretorio_saida = Path(diretorio_saida)
    inicio = time.monotonic()
    tempos: dict[str, float] = {}
    meta: dict = {"areas": nomes, "prefixos": prefixos, "normalizar": normalizar,
                  "incluir_nao_verificados": incluir_nao_verificados}
    avisos: list[str] = []
    if not restaurar:
        avisos.append(AVISO_SEM_RESTAURAR)
        meta["aviso"] = AVISO_SEM_RESTAURAR
    if not normalizar:
        avisos.append("rodada SEM normalizacao (diff cru; o cmp.py das telas mantem a propria normalizacao)")

    def termina(casos: list[Caso]) -> int:
        tempos["total_s"] = round(time.monotonic() - inicio, 1)
        meta["tempos_s"] = tempos
        return _fim(diretorio_saida, casos, meta, avisos)

    def para(nome: str, detalhe: str) -> int:
        meta.update(_metadados_ambiente())
        return termina([Caso(nome, AREA_BATERIA, Veredito.ERRO_AMBIENTE, detalhe)])

    # 1. ambiente (o laboratorio Laravel nao faz parte da bateria PHP: ref ocupa o lugar dele)
    alvos = alvos_do_ambiente()
    problemas = verifica(replace(alvos, laravel_novo=alvos.ref))
    if problemas:
        return para("ambiente", "; ".join(problemas))

    # 2-3. baseline + restauracao (uma vez por rodada)
    try:
        confere_baseline(ARQ_DUMP)
        if restaurar:
            t0 = time.monotonic()
            restaura_dump(ARQ_DUMP)
            meta["restauracao_s"] = tempos["restauracao_s"] = round(time.monotonic() - t0, 1)
        else:
            meta["restauracao_s"] = None
    except (BancoDiferente, ErroAmbienteBanco, RodadaInvalida) as e:
        return para("banco", f"{type(e).__name__}: {e}")

    # 4. sessao autenticada (sobrevive ao restore: vive no volume de sessoes, nao no banco)
    try:
        sid = obtem_sid()
        if not sessao_autenticada(sid):
            return para("sessao", "sessao nao autenticada (pagina 'Sessao invalida')")
    except (ErroAmbienteBanco, OSError, subprocess.SubprocessError) as e:
        return para("sessao", f"{type(e).__name__}: {e}")

    meta.update(_metadados_ambiente())
    with (sem_normalizacao() if not normalizar else _nada()):
        return _passos(termina, meta, tempos, sid, nomes, prefixos, areas is None,
                       incluir_nao_verificados, diretorio_saida)


@contextmanager
def _nada():
    yield


def _cronometra(tempos: dict, fase: str, fn):
    t0 = time.monotonic()
    try:
        return fn()
    finally:
        tempos[fase + "_s"] = round(time.monotonic() - t0, 1)


def _passos(termina, meta, tempos, sid, nomes, prefixos, todas, incluir_nv, diretorio) -> int:
    casos: list[Caso] = []
    rotulo = "+".join(nomes) if len(nomes) <= 3 else "todas"

    # telas por prefixo (a lista tambem alimenta lint e classes)
    telas_alvo: list[str] = []
    for p in prefixos:
        try:
            telas_alvo += lista_telas(_regex_prefixo(p))
        except OSError as e:
            casos.append(Caso(f"passo:lista_telas:{p}", rotulo, Veredito.ERRO_AMBIENTE, str(e)))
    telas_alvo = sorted(set(telas_alvo))
    meta["telas_selecionadas"] = len(telas_alvo)

    casos += _cronometra(tempos, "sintaxe", lambda: _passo("sintaxe", rotulo, lambda: roda_lint(telas_alvo)))

    def _classes():
        lista = _classes_das_telas(telas_alvo)
        meta["classes_selecionadas"] = len(lista)
        return roda_classes(lista) if lista else []
    casos += _cronometra(tempos, "classes", lambda: _passo("classes", rotulo, _classes))

    corpos: dict[str, bytes] = {}

    def _telas():
        saida: list[Caso] = []
        for p in prefixos:
            cs, cp = roda_telas(sid, _regex_prefixo(p), rotulo)
            saida += cs
            if not any(c.veredito == Veredito.ERRO_AMBIENTE for c in cs):
                corpos.update(cp)  # corpos parciais acompanham ERRO_AMBIENTE: ignorados
        return saida
    casos += _cronometra(tempos, "telas", lambda: _passo("telas", rotulo, _telas))

    def _catalogo(nome, carrega, caminho, tela_de, roda):
        try:
            linhas = carrega(caminho)
        except Exception as e:
            meta[f"catalogo_{nome}"] = {"erro": str(e)}
            return [Caso(f"passo:catalogo_{nome}", rotulo, Veredito.ERRO_AMBIENTE, f"{type(e).__name__}: {e}")]
        rodar, nv, outra = _filtra_catalogo(linhas, prefixos, todas, incluir_nv, tela_de)
        meta[f"catalogo_{nome}"] = {
            "linhas": len(linhas), "rodadas": len(rodar), "nao_verificado_pulados": len(nv),
            "nao_verificado_pulados_ids": [tela_de(r) for r in nv], "fora_da_area": len(outra),
            "verificado": sum(1 for r in linhas if r.verificado),
            "nao_verificado": sum(1 for r in linhas if not r.verificado)}
        saida: list[Caso] = []
        for r in rodar:
            try:
                saida.append(roda(sid, r))
            except Exception as e:
                saida.append(Caso(tela_de(r), r.area, Veredito.ERRO_AMBIENTE, f"{type(e).__name__}: {e}"))
        return saida

    casos += _cronometra(tempos, "posts", lambda: _passo("posts", rotulo, lambda: _catalogo(
        "posts", carrega_catalogo, CATALOGO_POSTS, lambda r: r.tela, roda_post)))
    casos += _cronometra(tempos, "relatorios", lambda: _passo("relatorios", rotulo, lambda: _catalogo(
        "relatorios", carrega_catalogo_relatorios, CATALOGO_RELATORIOS, lambda r: r.tela, roda_relatorio)))

    # conhecidas
    try:
        casos = marcar(casos, carregar_conhecidas(CONHECIDAS))
    except Exception as e:
        casos.append(Caso("passo:conhecidas", rotulo, Veredito.ERRO_AMBIENTE, f"{type(e).__name__}: {e}"))

    # hashes das telas e cobertura
    def _artefatos():
        arq = grava_hashes(Path(diretorio), corpos)
        meta["hashes"] = arq.name
        cob = cobertura_telas(casos, corpos)
        meta["telas_com_dados"] = len(cob["com_dados"])
        meta["telas_tabela_vazia"] = len(cob["tabela_vazia"])
        (Path(diretorio) / "cobertura.json").write_text(json.dumps(cob, ensure_ascii=False, indent=2),
                                                        encoding="utf-8", newline="\n")
        return []
    casos += _passo("artefatos", rotulo, _artefatos)

    return termina(casos)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m regressao.php.bateria", description=__doc__.split("\n")[0])
    ap.add_argument("--saida", required=True, type=Path)
    ap.add_argument("--area", action="append", default=None, help=f"repetivel; validas: {', '.join(sorted(AREAS))}")
    ap.add_argument("--sem-normalizar", action="store_true")
    ap.add_argument("--incluir-nao-verificados", action="store_true")
    ap.add_argument("--sem-restaurar", action="store_true",
                    help="SO desenvolvimento: nao restaura a baseline; resultado nao comparavel")
    a = ap.parse_args(argv)
    try:
        return roda_bateria_php(a.saida, a.area, normalizar=not a.sem_normalizar,
                                incluir_nao_verificados=a.incluir_nao_verificados,
                                restaurar=not a.sem_restaurar)
    except AreaDesconhecida as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
