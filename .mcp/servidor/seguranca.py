"""Confinamento de caminhos, segredos, regex e limites. Toda tool passa por aqui antes de tocar no disco.

Regras: so caminhos dentro da raiz do repositorio (symlinks resolvidos), nunca `..`, nunca `.git/`, nunca
arquivos de segredo (.env, chaves, db_conn.php). Erros viram `ErroFerramenta` (resposta estruturada).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

MAX_CAMINHO = 1024
MAX_REGEX = 300

_SEGREDOS_NOME = re.compile(
    r"^(\.env(\..+)?|db_conn\.php|auth\.json|id_rsa.*|.*\.(key|pem|p12|pfx|crt))$", re.IGNORECASE
)
_NAO_SEGREDO = {".env.example", ".env.dist", ".env.testing.example", "db_conn.php.dist"}


class ErroFerramenta(Exception):
    """Erro previsto de uma tool: vira `{"ok": false, "erro": {...}}` e nunca derruba o servidor."""

    def __init__(self, codigo: str, mensagem: str, **detalhes: Any) -> None:
        super().__init__(f"{codigo}: {mensagem}")
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes

    def como_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"codigo": self.codigo, "mensagem": self.mensagem}
        if self.detalhes:
            d["detalhes"] = self.detalhes
        return d


def eh_segredo(rel: Path) -> bool:
    nome = rel.name
    if nome.lower() in _NAO_SEGREDO:
        return False
    return bool(_SEGREDOS_NOME.match(nome))


def resolver_caminho(
    raiz: Path,
    caminho: str,
    *,
    deve_existir: bool = True,
    tipo: Literal["arquivo", "diretorio"] | None = None,
) -> Path:
    """Caminho absoluto, com symlinks resolvidos, garantidamente dentro de `raiz`."""
    if not isinstance(caminho, str) or not caminho or "\x00" in caminho or len(caminho) > MAX_CAMINHO:
        raise ErroFerramenta("caminho_invalido", "caminho vazio, longo demais ou com byte nulo")
    p = Path(caminho)
    if ".." in p.parts:
        raise ErroFerramenta("caminho_fora_da_raiz", "nao use '..': informe o caminho relativo a raiz do repositorio")
    raiz_r = raiz.resolve(strict=True)
    alvo = (p if p.is_absolute() else raiz_r / p).resolve(strict=False)
    if alvo != raiz_r and raiz_r not in alvo.parents:
        raise ErroFerramenta("caminho_fora_da_raiz", f"{caminho!r} fica fora do repositorio")
    rel = alvo.relative_to(raiz_r)
    if ".git" in rel.parts:
        raise ErroFerramenta("caminho_proibido", "o diretorio .git nao e acessivel pelas tools")
    if eh_segredo(rel):
        raise ErroFerramenta("caminho_proibido", f"{rel.as_posix()} parece arquivo de segredo e nao e lido")
    if deve_existir and not alvo.exists():
        raise ErroFerramenta("caminho_inexistente", f"{rel.as_posix() or '.'} nao existe")
    if tipo == "arquivo" and alvo.exists() and not alvo.is_file():
        raise ErroFerramenta("tipo_invalido", f"{rel.as_posix() or '.'} nao e arquivo")
    if tipo == "diretorio" and alvo.exists() and not alvo.is_dir():
        raise ErroFerramenta("tipo_invalido", f"{rel.as_posix() or '.'} nao e diretorio")
    return alvo


def relativo(raiz: Path, p: Path) -> str:
    rel = p.resolve().relative_to(raiz.resolve()).as_posix()
    return rel or "."


def validar_regex(rx: str, flags: int = 0) -> re.Pattern[str]:
    if not isinstance(rx, str) or not rx or len(rx) > MAX_REGEX:
        raise ErroFerramenta("regex_invalida", f"regex vazia ou maior que {MAX_REGEX} caracteres")
    try:
        return re.compile(rx, flags)
    except re.error as e:
        raise ErroFerramenta("regex_invalida", f"regex invalida: {e}") from None


def limitar(texto: str, maximo: int) -> tuple[str, bool]:
    if len(texto) <= maximo:
        return texto, False
    return texto[:maximo] + f"\n[... truncado: {len(texto) - maximo} caracteres omitidos]", True
