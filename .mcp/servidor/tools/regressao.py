"""rodar_regressao / ler_resultado_regressao / ler_triagem.

A suite `regressao/` roda no host com o venv dela (ela mesma orquestra os conteineres e74 por HTTP e
`docker exec`; o codigo dela nao esta montado nos conteineres). A tool so dispara comandos FIXOS da suite, em
processo destacado, depois de conferir os conteineres; nunca `gravar` baseline (protecao da referencia).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from servidor.config import Config
from servidor.docker_exec import DockerExec
from servidor.seguranca import ErroFerramenta, limitar, relativo, resolver_caminho, validar_regex

AREAS = ("assistenciasocial", "cidadao", "configuracao", "educacao", "financeiro", "gestor", "integracoes",
         "patrimonial", "recursoshumanos", "saude", "tributario")
BATERIAS = ("php", "laravel", "fluxos", "completa")
VEREDITOS = ("IDENTICO", "DIVERGE", "INCONCLUSIVO", "ERRO_AMBIENTE")
_ID = re.compile(r"^\d{8}-\d{6}-(php|laravel|fluxos|completa)-[0-9a-f]{4}$")
_FLUXO = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
EXECUTOR = Path(__file__).resolve().parents[1] / "executor.py"
AVISO = ("INCONCLUSIVO e ERRO_AMBIENTE NUNCA sao aprovacao: INCONCLUSIVO = caso nao exercitado (lacuna), "
         "ERRO_AMBIENTE = nada se conclui. O gabarito e a referencia PHP 7.4/Laravel 8. A bateria PHP mede paridade "
         "7.4 x 8.5 sobre o MESMO codigo (nao detecta bug igual nos dois lados).")
SIGNIFICADO_SAIDA = {0: "sem DIVERGE nova e sem ERRO_AMBIENTE (leia INCONCLUSIVO e a cobertura antes de confiar)",
                     1: "ha DIVERGE nao conhecida: achado real (veja divergencias_novas e diffs/)",
                     2: "ERRO_AMBIENTE ou rodada invalida: nada se conclui"}


def _agora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cmdline_executor(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OverflowError):
        return False
    try:
        return b"executor.py" in Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False


def _status(d: Path, vivo: Callable[[int], bool]) -> tuple[str, int | None]:
    fim = d / "fim.json"
    if fim.is_file():
        try:
            return "concluida", json.loads(fim.read_text(encoding="utf-8")).get("codigo_saida")
        except (json.JSONDecodeError, OSError):
            return "concluida", None
    try:
        pid = int(json.loads((d / "meta.json").read_text(encoding="utf-8")).get("pid", 0))
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return "desconhecida", None
    return ("em_andamento" if pid and vivo(pid) else "interrompida"), None


def _argv(config: Config, bateria: str, saida: Path, area: list[str], prefixo: list[str], fluxo: list[str],
          sem_fluxos: bool) -> list[str]:
    base = [str(config.raiz / config.python_regressao), "-m"]
    if bateria == "php":
        return base + ["regressao.php.bateria", "--saida", str(saida)] + \
            [f"--area={a}" for a in area] + [f"--prefixo={p}" for p in prefixo]
    if bateria == "laravel":
        return base + ["regressao.laravel.bateria", "comparar", "--saida", str(saida)]
    if bateria == "fluxos":
        return base + ["regressao.completa.fluxos", "comparar", "--saida", str(saida)] + [f"--fluxo={f}" for f in fluxo]
    return base + ["regressao.completa.orquestra", "--saida", str(saida)] + \
        [f"--area={a}" for a in area] + [f"--prefixo={p}" for p in prefixo] + (["--sem-fluxos"] if sem_fluxos else [])


def rodar_regressao(
    config: Config,
    bateria: str,
    area: list[str] | None = None,
    prefixo: list[str] | None = None,
    fluxo: list[str] | None = None,
    sem_fluxos: bool = False,
    confirmo_rodada_longa: bool = False,
    quem: str | None = None,
    docker: DockerExec | None = None,
    popen: Callable[..., Any] = subprocess.Popen,
    _cmdline_executor: Callable[[int], bool] = _cmdline_executor,
) -> dict[str, Any]:
    area, prefixo, fluxo = list(area or []), list(prefixo or []), list(fluxo or [])
    if bateria not in BATERIAS:
        raise ErroFerramenta("parametro_invalido", f"bateria: {', '.join(BATERIAS)}")
    for a in area:
        if a not in AREAS:
            raise ErroFerramenta("parametro_invalido", f"area {a!r}; validas: {', '.join(AREAS)}")
    if len(area) > len(AREAS) or len(prefixo) > 10 or len(fluxo) > 10:
        raise ErroFerramenta("parametro_invalido", "no maximo 10 prefixos/fluxos")
    for p in prefixo:
        validar_regex(p)
    for f in fluxo:
        if not _FLUXO.match(f):
            raise ErroFerramenta("parametro_invalido", f"fluxo invalido: {f!r}")
    if (area or prefixo) and bateria not in ("php", "completa"):
        raise ErroFerramenta("parametro_invalido", "area/prefixo so valem para as baterias php e completa")
    if fluxo and bateria != "fluxos":
        raise ErroFerramenta("parametro_invalido", "fluxo so vale para a bateria fluxos")
    if bateria in ("php", "completa") and not (area or prefixo) and not confirmo_rodada_longa:
        raise ErroFerramenta("confirmacao_necessaria",
                             "sem area/prefixo a bateria PHP roda ~12 mil telas (HORAS). Restrinja com prefixo "
                             "(ex.: '^arr1_') ou passe confirmo_rodada_longa=true")

    py = config.raiz / config.python_regressao
    if not py.is_file():
        raise ErroFerramenta("venv_regressao_ausente",
                             f"{config.python_regressao} nao existe: python3 -m venv regressao/.venv && "
                             "regressao/.venv/bin/pip install -r regressao/requirements.txt")
    docker = docker or DockerExec(config)
    for nome in (config.container_ref, config.container_alvo, config.container_banco):
        docker.verificar_conteiner(nome)

    config.dir_rodadas.mkdir(parents=True, exist_ok=True)
    for d in sorted(config.dir_rodadas.iterdir()):
        if d.is_dir() and _ID.match(d.name) and _status(d, _cmdline_executor)[0] == "em_andamento":
            raise ErroFerramenta("rodada_em_andamento",
                                 f"a rodada {d.name} ainda roda (cada bateria restaura o banco: duas juntas se "
                                 "atrapalham). Acompanhe com ler_resultado_regressao", id=d.name)

    rid = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{bateria}-{secrets.token_hex(2)}"
    d = config.dir_rodadas / rid
    d.mkdir()
    argv = _argv(config, bateria, d / "saida", area, prefixo, fluxo, sem_fluxos)
    meta = {"id": rid, "bateria": bateria, "argv": argv, "raiz": str(config.raiz), "inicio": _agora_iso(),
            "quem": quem or config.usuario or "", "pid": None}
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(d / "execucao.log", "wb") as log:
        proc = popen([sys.executable, str(EXECUTOR), str(d / "meta.json")], cwd=str(config.raiz),
                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                     close_fds=True)
    meta["pid"] = proc.pid
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"id": rid, "status": "iniciada", "pasta": relativo(config.raiz, d), "comando": argv[2:],
            "acompanhe": f"ler_resultado_regressao(id='{rid}')",
            "duracao_esperada": "restauracao do banco ~4 min + casos (prefixo pequeno ~5-6 min; area inteira: horas)"}


def _cauda(p: Path, n: int = 30) -> str:
    try:
        linhas = p.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return ""
    return limitar("\n".join(linhas), 4000)[0]


def _resultado(saida: Path, max_itens: int, veredito: str | None) -> dict[str, Any] | None:
    arq = saida / "resultado.json"
    if not arq.is_file():
        return None
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
        casos = dados["casos"]
    except (json.JSONDecodeError, KeyError, OSError) as e:
        return {"erro_leitura": f"resultado.json invalido: {e}"}
    totais = {v: 0 for v in VEREDITOS}
    for c in casos:
        totais[c.get("veredito", "?")] = totais.get(c.get("veredito", "?"), 0) + 1
    novas = [c for c in casos if c.get("veredito") == "DIVERGE" and not c.get("conhecida")]
    erros = [c for c in casos if c.get("veredito") == "ERRO_AMBIENTE"]
    inc = Counter((c.get("detalhe") or "")[:100] for c in casos if c.get("veredito") == "INCONCLUSIVO")
    corta = lambda xs: [{k: c.get(k) for k in ("id", "area", "detalhe")} for c in xs[:max_itens]]  # noqa: E731
    r: dict[str, Any] = {
        "totais": totais, "total_casos": len(casos),
        "divergencias_novas": corta(novas), "divergencias_novas_total": len(novas),
        "divergencias_conhecidas_total": sum(1 for c in casos if c.get("veredito") == "DIVERGE" and c.get("conhecida")),
        "erros_ambiente": corta(erros), "inconclusivo_por_motivo": dict(inc.most_common(15)),
        "meta": {k: v for k, v in (dados.get("meta") or {}).items()
                 if k in ("tipo", "comparavel", "versoes", "baseline_sha256", "tempos_s", "baterias", "git_commit")},
    }
    if veredito:
        r["filtrados"] = corta([c for c in casos if c.get("veredito") == veredito])
    resumo = saida / "resumo.md"
    if resumo.is_file():
        r["resumo_md"] = limitar(resumo.read_text(encoding="utf-8", errors="replace"), 6000)[0]
    return r


def ler_resultado_regressao(
    config: Config,
    id: str | None = None,
    pasta: str | None = None,
    max_itens: int = 50,
    veredito: str | None = None,
    _cmdline_executor: Callable[[int], bool] = _cmdline_executor,
) -> dict[str, Any]:
    if veredito and veredito not in VEREDITOS:
        raise ErroFerramenta("parametro_invalido", f"veredito: {', '.join(VEREDITOS)}")
    if not (1 <= max_itens <= 500):
        raise ErroFerramenta("parametro_invalido", "max_itens entre 1 e 500")
    if pasta:
        d = resolver_caminho(config.raiz, pasta, tipo="diretorio")
        res = _resultado(d, max_itens, veredito) or _resultado(d / "saida", max_itens, veredito)
        if res is None:
            raise ErroFerramenta("rodada_inexistente", f"{pasta} nao tem resultado.json")
        return {"pasta": relativo(config.raiz, d), **res, "aviso": AVISO}
    if id is None:
        rodadas = []
        if config.dir_rodadas.is_dir():
            for d in sorted((x for x in config.dir_rodadas.iterdir() if x.is_dir() and _ID.match(x.name)),
                            key=lambda x: x.name, reverse=True)[:20]:
                st, cod = _status(d, _cmdline_executor)
                rodadas.append({"id": d.name, "bateria": d.name.split("-")[2], "status": st, "codigo_saida": cod})
        return {"rodadas": rodadas, "dica": "chame com id=<id> para o detalhe"}
    if not _ID.match(id or ""):
        raise ErroFerramenta("parametro_invalido", "id no formato AAAAMMDD-HHMMSS-<bateria>-xxxx")
    d = config.dir_rodadas / id
    if not d.is_dir():
        raise ErroFerramenta("rodada_inexistente", f"rodada {id} nao existe em .mcp/rodadas/")
    st, cod = _status(d, _cmdline_executor)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").is_file() else {}
    r: dict[str, Any] = {"id": id, "bateria": meta.get("bateria"), "status": st, "inicio": meta.get("inicio"),
                         "quem": meta.get("quem"), "codigo_saida": cod,
                         "significado_saida": SIGNIFICADO_SAIDA.get(cod) if cod is not None else None,
                         "log_final": _cauda(d / "execucao.log")}
    res = _resultado(d / "saida", max_itens, veredito)
    if res is None:
        alt = next(iter(sorted((d / "saida").glob("*/resultado.json"))), None) if (d / "saida").is_dir() else None
        res = _resultado(alt.parent, max_itens, veredito) if alt else None
    if res:
        r.update(res)
    elif st == "em_andamento":
        r["dica"] = "ainda rodando: chame de novo em alguns minutos"
    r["aviso"] = AVISO
    return r


# ---------- triagem ----------

DOCUMENTOS = {
    "triagem": "regressao/baseline/triagem-divergencias.md",
    "decisoes": "regressao/baseline/decisoes-migracao.md",
    "lab_lar12": "regressao/baseline/lab-lar12-resultado.md",
    "como_usar": "regressao/COMO-USAR.md",
}
_TITULO = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def ler_triagem(config: Config, documento: str = "triagem", secao: str | None = None,
                busca: str | None = None) -> dict[str, Any]:
    if documento not in DOCUMENTOS:
        raise ErroFerramenta("parametro_invalido", f"documento: {', '.join(DOCUMENTOS)}")
    rel = DOCUMENTOS[documento]
    try:
        arq = resolver_caminho(config.raiz, rel, tipo="arquivo")
    except ErroFerramenta as e:
        if e.codigo == "caminho_inexistente":
            raise ErroFerramenta("documento_inexistente", f"{rel} ainda nao existe nesta branch") from None
        raise
    linhas = arq.read_text(encoding="utf-8", errors="replace").splitlines()
    secoes = []
    em_codigo = False
    for i, l in enumerate(linhas, start=1):
        if l.lstrip().startswith("```"):
            em_codigo = not em_codigo
        m = None if em_codigo else _TITULO.match(l)
        if m:
            secoes.append({"titulo": m.group(2), "nivel": len(m.group(1)), "linha": i})
    cab = " ".join(linhas[:3])
    base = "7.4 x 8.5" if "7.4" in cab else ("5.6 x 8.5 (historico: gabarito antigo)" if "5.6" in cab else "?")
    r: dict[str, Any] = {"documento": rel, "base": base, "secoes": secoes}
    if secao:
        alvo = _norm(secao)
        partes = []
        for k, s in enumerate(secoes):
            if alvo in _norm(s["titulo"]):
                fim = next((t["linha"] - 1 for t in secoes[k + 1:] if t["nivel"] <= s["nivel"]), len(linhas))
                partes.append("\n".join(linhas[s["linha"] - 1:fim]).strip())
        if not partes:
            raise ErroFerramenta("secao_inexistente", f"nenhuma secao com {secao!r}; veja `secoes`")
        r["texto"] = limitar("\n\n".join(partes), config.max_saida)[0]
    elif busca:
        alvo = _norm(busca)
        r["linhas"] = [{"linha": i, "texto": l} for i, l in enumerate(linhas, start=1) if alvo in _norm(l)][:100]
    else:
        r["texto"], r["truncado"] = limitar("\n".join(linhas), config.max_saida)
    return r
