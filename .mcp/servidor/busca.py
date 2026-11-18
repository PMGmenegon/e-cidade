"""Varredura estatica do codigo (sem ripgrep: Python puro, deterministico, confinado a raiz do repo)."""
from __future__ import annotations

import bisect
import os
import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from servidor.config import Config
from servidor.padroes import CATALOGO, Padrao, ocorrencias, padroes_para
from servidor.seguranca import ErroFerramenta, eh_segredo, relativo, resolver_caminho, validar_regex

EXTENSOES_PADRAO = (".php", ".inc", ".class", ".phtml", ".module")
DIRS_IGNORADOS = {".git", "vendor", "node_modules", ".venv", "__pycache__", ".mcp", ".idea", ".pytest_cache"}
MAX_LINHA_REGEX = 5000
MAX_TRECHO = 200


def iterar_arquivos(config: Config, base: Path, extensoes: tuple[str, ...]) -> Iterator[Path]:
    """Arquivos sob `base` (ordem estavel), sem diretorios ignorados, segredos nem symlinks para fora."""
    raiz = config.raiz.resolve()
    if base.is_file():
        yield base
        return
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in DIRS_IGNORADOS)
        for nome in sorted(filenames):
            if not nome.lower().endswith(extensoes):
                continue
            p = Path(dirpath) / nome
            if p.is_symlink():
                alvo = p.resolve()
                if raiz not in alvo.parents or ".git" in alvo.relative_to(raiz).parts:
                    continue
            if eh_segredo(Path(nome)):
                continue
            yield p


def ler_texto(p: Path, max_bytes: int) -> str | None:
    try:
        if p.stat().st_size > max_bytes:
            return None
        dados = p.read_bytes()
    except OSError:
        return None
    try:
        return dados.decode("utf-8")
    except UnicodeDecodeError:
        return dados.decode("latin-1")  # base do e-Cidade e LATIN1


class _Linhas:
    def __init__(self, texto: str):
        self.texto = texto
        self.inicios = [0]
        i = texto.find("\n")
        while i >= 0:
            self.inicios.append(i + 1)
            i = texto.find("\n", i + 1)

    def linha(self, offset: int) -> int:
        return bisect.bisect_right(self.inicios, offset)

    def trecho(self, n: int) -> str:
        ini = self.inicios[n - 1]
        fim = self.texto.find("\n", ini)
        s = self.texto[ini:fim if fim >= 0 else len(self.texto)].strip()
        return s[:MAX_TRECHO] + ("..." if len(s) > MAX_TRECHO else "")


def buscar(
    config: Config,
    *,
    padrao: str | None = None,
    regex: str | None = None,
    caminho: str | None = None,
    extensoes: tuple[str, ...] = EXTENSOES_PADRAO,
    limite: int = 100,
    incluir_baixa_confianca: bool = False,
    ignorar_arquivos: set[str] | None = None,
    prazo_s: float | None = None,
) -> dict[str, Any]:
    if padrao and regex:
        raise ErroFerramenta("parametro_invalido", "informe `padrao` OU `regex`, nao os dois")
    if not padrao and not regex:
        return {"catalogo": [p.como_dict() for p in sorted(CATALOGO, key=lambda p: p.prioridade)],
                "dica": "chame de novo com padrao=<nome> (ou 'todos') ou regex=<expressao>"}
    if not (1 <= limite <= 2000):
        raise ErroFerramenta("parametro_invalido", "limite precisa estar entre 1 e 2000")
    exts = tuple(e if e.startswith(".") else "." + e for e in extensoes)
    lista: list[Padrao] = padroes_para(padrao, incluir_baixa_confianca) if padrao else []
    rx = validar_regex(regex) if regex else None
    base = resolver_caminho(config.raiz, caminho or config.dir_codigo)
    prazo = config.timeout_busca_s if prazo_s is None else prazo_s
    fim = time.monotonic() + prazo
    ignorar = ignorar_arquivos or set()

    achados: list[dict[str, Any]] = []
    totais: Counter[str] = Counter()
    por_arquivo: Counter[str] = Counter()
    varridos, truncado, motivo = 0, False, ""
    for p in iterar_arquivos(config, base, exts):
        if time.monotonic() > fim:
            truncado, motivo = True, f"tempo: passou de {prazo:.0f}s (resultado parcial; restrinja `caminho`)"
            break
        rel = relativo(config.raiz, p)
        if rel in ignorar:
            continue
        texto = ler_texto(p, config.max_arquivo)
        if texto is None:
            continue
        varridos += 1
        linhas = None
        encontrados: list[tuple[int, str]] = []
        if rx is not None:
            for n, linha in enumerate(texto.splitlines(), start=1):
                if len(linha) <= MAX_LINHA_REGEX and rx.search(linha):
                    encontrados.append((n, "regex"))
        else:
            for pd in lista:
                offs = ocorrencias(pd, texto)
                if offs:
                    linhas = linhas or _Linhas(texto)
                    encontrados.extend((linhas.linha(o), pd.nome) for o in offs)
        for n, nome in sorted(encontrados):
            if len(achados) >= limite:
                truncado, motivo = True, f"limite de {limite} ocorrencias (aumente `limite` ou restrinja `caminho`)"
                break
            linhas = linhas or _Linhas(texto)
            achados.append({"arquivo": rel, "linha": n, "padrao": nome, "trecho": linhas.trecho(n)})
            totais[nome] += 1
            por_arquivo[rel] += 1
        if truncado:
            break
    return {
        "padrao": padrao, "regex": regex, "caminho": relativo(config.raiz, base),
        "ocorrencias": achados, "totais_por_padrao": dict(totais), "arquivos_com_ocorrencia": len(por_arquivo),
        "arquivos_varridos": varridos, "truncado": truncado, "motivo_truncado": motivo,
        "aviso": "busca estatica: aponta candidatos (comentarios/strings tambem casam); confirme no codigo",
    }
