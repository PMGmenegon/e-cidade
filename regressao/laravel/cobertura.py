"""Relatorio de cobertura de rotas: inventario x casos carregados x resposta da referencia.

`_cobertura.json` e `_cobertura.md` ficam em `baseline/laravel/` e alimentam o relatorio final.
Um 5xx na referencia significa "rota quebrada ou que precisa de dados em dev": e contado e
listado (nao escondido); como o caso e identico nos dois lados, o veredito sera INCONCLUSIVO.

Uso: python -m regressao.laravel.cobertura
"""
import json
import sys
from pathlib import Path

from regressao.laravel import gerador
from regressao.laravel.caso import DIR_BASELINE, DIR_CASOS, CasoHttp, _le_registro, carrega_casos, nome_arquivo
from regressao.laravel.rotas import ORIGENS, Rota


def _classe(status: int) -> str:
    return f"{status // 100}xx"


def _status_do_caso(dir_baseline: Path, c: CasoHttp) -> int | None:
    arq = Path(dir_baseline) / nome_arquivo(c.id)
    if not arq.is_file():
        return None
    try:
        return int(_le_registro(arq)["status"])
    except (ValueError, KeyError, TypeError):
        return None


def cobertura_rotas(rotas: list[Rota], casos: list[CasoHttp], dir_baseline: Path,
                    ajustes: dict | None = None) -> dict:
    ajustes = gerador.le_ajustes() if ajustes is None else ajustes
    instaveis = ajustes.get("instaveis") or {}
    por_rota: dict[tuple[str, str], list[CasoHttp]] = {}
    for c in casos:
        por_rota.setdefault((c.metodo, c.caminho), []).append(c)
    origens = {o: {"total": 0, "cobertas": 0, "nao_cobertas": 0} for o in ORIGENS}
    classes = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "sem_baseline": 0}
    cobertas: list[dict] = []
    nao_cobertas: list[dict] = []
    inconclusivos: list[str] = []
    for r in sorted(rotas, key=lambda r: (r.origem, r.caminho, r.metodo)):
        origens[r.origem]["total"] += 1
        achados = [c for m in r.metodo.split("|") for c in por_rota.get((m, r.caminho), [])]
        if not achados:
            motivo = gerador.motivo_nao_gerada(r)
            if motivo is None:
                inst = instaveis.get(gerador.id_do_caso(r))
                motivo = f"instavel (_instaveis.yml): {inst}" if inst else "sem caso carregado"
            origens[r.origem]["nao_cobertas"] += 1
            nao_cobertas.append({"origem": r.origem, "metodo": r.metodo, "uri": r.caminho,
                                 "motivo": motivo})
            continue
        origens[r.origem]["cobertas"] += 1
        # a classe da rota e a do primeiro caso (na ordem de carga) que tenha baseline
        status, ids = None, [c.id for c in achados]
        for c in achados:
            status = _status_do_caso(dir_baseline, c)
            if status is not None:
                break
        if status is None:
            classes["sem_baseline"] += 1
            classe = "sem_baseline"
        else:
            classe = _classe(status)
            classes[classe] = classes.get(classe, 0) + 1
            if classe == "5xx":
                inconclusivos.append(ids[0])
        cobertas.append({"origem": r.origem, "metodo": r.metodo, "uri": r.caminho,
                         "casos": ids, "status": status, "classe": classe})
    return {"total": len(rotas), "por_origem": origens, "classes": classes,
            "inconclusivos_5xx": inconclusivos, "cobertas": cobertas, "nao_cobertas": nao_cobertas}


def _md(rel: dict) -> str:
    L = ["# Cobertura de rotas (Laravel)", "",
         f"Rotas no inventario: **{rel['total']}**.", "",
         "| origem | total | cobertas | nao cobertas |", "|---|---:|---:|---:|"]
    for o, v in rel["por_origem"].items():
        L.append(f"| {o} | {v['total']} | {v['cobertas']} | {v['nao_cobertas']} |")
    c = rel["classes"]
    L += ["", "## Resposta da referencia (Laravel 5.4) nas rotas cobertas", "",
          f"2xx: {c['2xx']}  3xx: {c['3xx']}  4xx: {c['4xx']}  5xx: {c['5xx']}  "
          f"sem baseline: {c['sem_baseline']}", "",
          f"**5xx na referencia: {c['5xx']}.** Rota quebrada ou que precisa de dados em dev; "
          "o caso e IDENTICO nos dois lados mas termina INCONCLUSIVO (500 x 500): a rota nao "
          "foi exercitada, so o seu roteamento/erro. Lista:", ""]
    L += [f"- `{i}`" for i in rel["inconclusivos_5xx"]] or ["- (nenhuma)"]
    L += ["", "## Nao cobertas", ""]
    por_motivo: dict[str, list[dict]] = {}
    for n in rel["nao_cobertas"]:
        chave = n["motivo"].split(":")[0].split(" (")[0].strip()
        por_motivo.setdefault(chave, []).append(n)
    for chave, itens in sorted(por_motivo.items()):
        L.append(f"- {chave}: {len(itens)}")
    L += ["", "| origem | metodo | uri | motivo |", "|---|---|---|---|"]
    for n in rel["nao_cobertas"]:
        L.append(f"| {n['origem']} | {n['metodo']} | `{n['uri']}` | {n['motivo']} |")
    return "\n".join(L) + "\n"


def escreve_cobertura(rel: dict, destino: Path) -> None:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "_cobertura.json").write_bytes(
        (json.dumps(rel, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    (destino / "_cobertura.md").write_bytes(_md(rel).encode("utf-8"))


def main() -> int:
    rotas = gerador.le_inventario()
    rel = cobertura_rotas(rotas, carrega_casos(DIR_CASOS), DIR_BASELINE)
    escreve_cobertura(rel, DIR_BASELINE)
    o = rel["por_origem"]
    print("cobertura: " + ", ".join(f"{k}={v['cobertas']}/{v['total']}" for k, v in o.items())
          + f"; classes={rel['classes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
