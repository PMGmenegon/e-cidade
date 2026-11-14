"""Inventario de rotas: Laravel 5.4 (route:list, inclui rest/v1), Silex api/V1."""
import re
from dataclasses import dataclass
from pathlib import Path

from regressao.nucleo.banco import _docker

CONTAINER_PHP = "ecidade_php56"
DIR_APP = "/var/www/html"
ARQ_INVENTARIO = Path(__file__).resolve().parent / "casos" / "_inventario.tsv"
ORIGENS = ("laravel", "rest", "silex")


@dataclass
class Rota:
    metodo: str
    caminho: str
    middleware: list[str]
    controller: str
    origem: str  # "laravel" | "rest" | "silex"


def parseia_route_list(texto: str) -> list[Rota]:
    """Tabela do `artisan route:list` (5.4): Domain|Method|URI|Name|Action|Middleware.
    Colunas pelas posicoes da linha de borda (Method tem `|`, ex.: GET|HEAD)."""
    linhas = texto.splitlines()
    borda = next((l for l in linhas if l.startswith("+-")), None)
    if borda is None:
        return []
    cortes = [i for i, c in enumerate(borda) if c == "+"]
    rotas: list[Rota] = []
    for l in linhas:
        if not l.startswith("|") or len(l) < cortes[-1]:
            continue
        cel = [l[a + 1:b].strip() for a, b in zip(cortes, cortes[1:])]
        if len(cel) != 6 or cel[1] == "Method":
            continue
        _dom, metodo, uri, _nome, acao, mw = cel
        if not metodo and not uri and rotas:  # continuacao de linha
            if mw:
                rotas[-1].middleware += [m for m in mw.split(",") if m]
            continue
        caminho = "/" + uri.lstrip("/")
        origem = "rest" if caminho.startswith("/rest/") else "laravel"
        rotas.append(Rota(metodo, caminho, [m for m in mw.split(",") if m], acao, origem))
    return rotas


def rotas_laravel() -> list[Rota]:
    saida = _docker(["exec", "-w", DIR_APP, CONTAINER_PHP, "php", "artisan", "route:list"], 180)
    return parseia_route_list(saida.decode("utf-8", errors="replace"))


_MOUNT = re.compile(r"""->mount\(\s*\$prefix\s*\.\s*['"]([^'"]*)['"]\s*,\s*new\s+(\w+)""")
_VERBO = re.compile(
    r"""\$\w+->(get|post|put|delete|patch|match)\(\s*['"]([^'"]*)['"]\s*,\s*['"]([^'"]*)['"]""")
_PREFIXO_API = "/api/v1"


def varre_silex(raiz: Path) -> list[Rota]:
    api = Path(raiz) / "ecidade" / "api" / "V1"
    try:
        prov = (api / "APIServiceProvider.php").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    montagem = {cls: pref for pref, cls in _MOUNT.findall(prov)}
    rotas: list[Rota] = []
    for arq in sorted((api / "Providers" / "Controller").glob("*.php")):
        pref = montagem.get(arq.stem)
        if pref is None:
            continue
        for verbo, caminho, handler in _VERBO.findall(arq.read_text(encoding="utf-8", errors="replace")):
            completo = _PREFIXO_API + pref + "/" + caminho.lstrip("/")
            rotas.append(Rota(verbo.upper(), completo, ["silex"], handler, "silex"))
    return sorted(rotas, key=_chave)


def _chave(r: Rota):
    return (r.origem, r.caminho, r.metodo, r.controller, ",".join(r.middleware))


def grava_tsv(rotas: list[Rota], destino: Path = ARQ_INVENTARIO) -> None:
    linhas = ["metodo\turi\tmiddleware\taction\torigem"]
    for r in sorted(rotas, key=_chave):
        linhas.append("\t".join([r.metodo, r.caminho, ",".join(r.middleware), r.controller, r.origem]))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(("\n".join(linhas) + "\n").encode("utf-8"))


def contagem(rotas: list[Rota]) -> dict[str, int]:
    return {o: sum(1 for r in rotas if r.origem == o) for o in ORIGENS}


def inventario(raiz: Path) -> list[Rota]:
    """Inventario completo (laravel + rest + silex); grava `casos/_inventario.tsv` e imprime
    a contagem por origem (entra no resumo.md como limite de cobertura)."""
    rotas = rotas_laravel() + varre_silex(raiz)
    grava_tsv(rotas)
    c = contagem(rotas)
    print("inventario de rotas: " + ", ".join(f"{o}={c[o]}" for o in ORIGENS) + f", total={len(rotas)}")
    return sorted(rotas, key=_chave)


if __name__ == "__main__":
    inventario(Path(__file__).resolve().parents[2])