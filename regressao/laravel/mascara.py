"""Mascara de campos volateis em JSON para comparar respostas de API."""
import copy

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


def mascara_json(obj, campos_volateis: list[str]):
    """Copia `obj` trocando por "<X>" os valores nos caminhos dados (pontos; `*` = cada
    elemento de lista) e ordenando as chaves recursivamente. Caminhos ausentes sao
    ignorados; a entrada nao e alterada."""
    novo = copy.deepcopy(obj)
    for caminho in campos_volateis:
        novo = _aplica(novo, caminho.split("."))
    return _ordena(novo)