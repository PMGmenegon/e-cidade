"""Mascara de campos volateis em JSON para comparar respostas de API."""
import copy
import re

MARCA = "<X>"


def _aplica(no, partes):
    if not partes:
        return MARCA
    p, resto = partes[0], partes[1:]
    if p == "*":
        if isinstance(no, list):
            return [_aplica(x, resto) for x in no]
        return no
    if isinstance(no, dict) and p in no:
        no[p] = _aplica(no[p], resto)
    return no


def _ordena(no):
    if isinstance(no, dict):
        return {k: _ordena(no[k]) for k in sorted(no, key=str)}
    if isinstance(no, list):
        return [_ordena(x) for x in no]
    return no


# --- Mascara de ERRO, aplicada so na COMPARACAO (a baseline em disco guarda o registro bruto) --------
# Erros do Laravel em modo debug trazem file/line/trace/stacktrace absolutos do servidor: num Laravel 12 em
# outro caminho eles sempre diferem sem que a API tenha mudado. Decisao: mascarar esses CAMPOS (so em objetos
# com cara de erro: tem `exception`, `message` ou `trace`) e normalizar caminhos absolutos de vendor/app/... em
# qualquer texto. `exception` (classe) e `message` continuam comparados: mudar a excecao e DIVERGE real.
CAMPOS_DE_ERRO = ("file", "line", "trace", "stacktrace", "stack_trace")
_SINAIS_DE_ERRO = ("exception", "message", "trace", "stacktrace", "stack_trace")
_RE_CAMINHO = re.compile(
    r"(?:/[\w.\-@]+)*/(?:vendor|app|bootstrap|storage|ecidade|libs|model|classes|dbforms|public)/[^\s\"'),;]*?"
    r"(?:\.php)?(?::\d+)?(?=[\s\"'),;]|$)")
_RE_NA_LINHA = re.compile(r"\bon line \d+")


def _texto(s: str) -> str:
    return _RE_NA_LINHA.sub("on line <N>", _RE_CAMINHO.sub("<caminho>", s))


def normaliza_erro(obj):
    """Copia de `obj` sem file/line/trace de erro e com caminhos absolutos normalizados."""
    if isinstance(obj, str):
        return _texto(obj)
    if isinstance(obj, list):
        return [normaliza_erro(x) for x in obj]
    if isinstance(obj, dict):
        erro = any(k in obj for k in _SINAIS_DE_ERRO)
        return {k: (MARCA if erro and k in CAMPOS_DE_ERRO else normaliza_erro(v)) for k, v in obj.items()}
    return obj


def mascara_json(obj, campos_volateis: list[str]):
    """Copia `obj` trocando por "<X>" os valores nos caminhos dados (pontos; `*` = cada
    elemento de lista) e ordenando as chaves recursivamente. Caminhos ausentes sao
    ignorados; a entrada nao e alterada."""
    novo = copy.deepcopy(obj)
    for caminho in campos_volateis:
        novo = _aplica(novo, caminho.split("."))
    return _ordena(novo)