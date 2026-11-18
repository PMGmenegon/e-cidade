"""validar_arquivo_php: php -l / PHPStan / Pint / PHPCS dentro dos conteineres 7.4 (referencia) e 8.5 (alvo)."""
from __future__ import annotations

import json
from typing import Any

from servidor.config import Config
from servidor.docker_exec import FERRAMENTAS, DockerExec, caminho_no_conteiner, comando_ferramenta
from servidor.seguranca import ErroFerramenta, limitar, relativo, resolver_caminho

VERSOES = {"referencia": "7.4 (referencia)", "alvo": "8.5 (alvo)"}
MAX_MENSAGENS = 100


def _phpstan(stdout: str) -> tuple[bool | None, list[dict[str, Any]]]:
    try:
        dados = json.loads(stdout[stdout.find("{"):]) if "{" in stdout else None
    except json.JSONDecodeError:
        dados = None
    if not isinstance(dados, dict) or "totals" not in dados:
        return None, []
    msgs = [{"linha": m.get("line"), "mensagem": m.get("message", "")}
            for f in (dados.get("files") or {}).values() for m in f.get("messages", [])]
    msgs += [{"linha": None, "mensagem": e} for e in dados.get("errors") or []]
    t = dados["totals"]
    return (t.get("errors", 0) == 0 and t.get("file_errors", 0) == 0), msgs[:MAX_MENSAGENS]


def _um(docker: DockerExec, conteiner: str, ferramenta: str, arquivo: str, nivel: int | None,
        config: Config) -> dict[str, Any]:
    item: dict[str, Any] = {"conteiner": conteiner, "ferramenta": ferramenta}
    try:
        if ferramenta in ("pint", "phpcs", "phpstan"):
            binario = {"pint": "vendor/bin/pint", "phpcs": "vendor/bin/phpcs", "phpstan": "vendor/bin/phpstan"}[ferramenta]
            t = docker.executar(conteiner, ["test", "-x", binario], timeout=20)
            if t.codigo_saida != 0:
                raise ErroFerramenta("ferramenta_indisponivel",
                                     f"{binario} nao esta instalado em {conteiner} (dependencia de dev do composer); "
                                     "instalar e decisao da equipe")
        timeout = config.timeout_phpstan_s if ferramenta == "phpstan" else config.timeout_lint_s
        r = docker.executar(conteiner, comando_ferramenta(ferramenta, arquivo, nivel), timeout=timeout)
    except ErroFerramenta as e:
        item.update(ok=False, erro=e.como_dict())
        return item
    saida, _ = limitar((r.stdout + ("\n" + r.stderr if r.stderr.strip() else "")).strip(), 8000)
    item.update(codigo_saida=r.codigo_saida, duracao_s=r.duracao_s)
    if ferramenta == "phpstan":
        ok, msgs = _phpstan(r.stdout)
        if ok is None:
            item.update(ok=False, saida=saida, aviso="saida do PHPStan nao e JSON (erro de execucao?)")
        else:
            item.update(ok=ok, mensagens=msgs)
    else:
        item.update(ok=r.codigo_saida == 0, saida=saida)
    return item


def validar_arquivo_php(
    config: Config,
    caminho: str,
    ferramentas: list[str] | None = None,
    versao: str = "ambas",
    nivel_phpstan: int | None = None,
    docker: DockerExec | None = None,
) -> dict[str, Any]:
    ferramentas = ferramentas or ["lint"]
    for f in ferramentas:
        if f not in FERRAMENTAS:
            raise ErroFerramenta("ferramenta_desconhecida", f"{f!r}; use {', '.join(FERRAMENTAS)}")
    if versao not in ("ambas", "alvo", "referencia"):
        raise ErroFerramenta("parametro_invalido", "versao: ambas | alvo | referencia")
    arq = resolver_caminho(config.raiz, caminho, tipo="arquivo")
    no_conteiner = caminho_no_conteiner(config, arq)
    docker = docker or DockerExec(config)
    alvos = [("referencia", config.container_ref), ("alvo", config.container_alvo)]
    if versao != "ambas":
        alvos = [a for a in alvos if a[0] == versao]
    resultados = []
    for papel, conteiner in alvos:
        for f in ferramentas:
            item = _um(docker, conteiner, f, no_conteiner, nivel_phpstan, config)
            resultados.append({"versao": VERSOES[papel], **item})
    falhas = [f"{r['ferramenta']} em {r['versao']}" for r in resultados if not r["ok"]]
    lint = {r["versao"]: r["ok"] for r in resultados if r["ferramenta"] == "lint" and "erro" not in r}
    resumo = "tudo ok" if not falhas else "falhou: " + "; ".join(falhas)
    if lint.get(VERSOES["referencia"]) and lint.get(VERSOES["alvo"]) is False:
        resumo += ". Compila no 7.4 e NAO no 8.5: e quebra da migracao"
    elif lint.get(VERSOES["referencia"]) is False and lint.get(VERSOES["alvo"]) is False:
        resumo += ". Nao compila em nenhum dos dois: ja estava quebrado na referencia"
    return {"arquivo": relativo(config.raiz, arq), "no_conteiner": no_conteiner, "ok": not falhas,
            "resultados": resultados, "resumo": resumo}
