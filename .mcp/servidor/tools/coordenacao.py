"""Coordenacao da equipe: reivindicar/liberar arquivo, quadro, proximo lote mecanico, padroes ja corrigidos.

Nenhuma destas tools faz commit: elas devolvem a sugestao (`git add` do caminho exato, nunca `-A`).
"""
from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from typing import Any

from servidor.busca import buscar
from servidor.config import Config
from servidor.estado import Estado
from servidor.padroes import CATALOGO, PADROES, padroes_para
from servidor.seguranca import ErroFerramenta, relativo, resolver_caminho
from servidor.tools.regressao import ler_resultado_regressao

_COMMIT_MIGRA = re.compile(r"^migra\(([a-z0-9_]+)\):")


def _estado(config: Config) -> Estado:
    return Estado(config.arquivo_estado, expira_horas=config.expira_horas)


def _git(config: Config, args: list[str], runner: Callable[..., Any]) -> subprocess.CompletedProcess | None:
    try:
        return runner(["git", "-C", str(config.raiz), *args], capture_output=True, text=True, encoding="utf-8",
                      errors="replace", timeout=20, stdin=subprocess.DEVNULL, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def quem_sou(config: Config, quem: str | None, git_runner: Callable[..., Any] = subprocess.run) -> str:
    """Identidade: parametro > ECIDADE_MCP_USUARIO > git config user.name (nunca o e-mail)."""
    for c in (quem, config.usuario):
        if c and c.strip():
            v = c.strip()
            if len(v) > 80 or "\n" in v:
                raise ErroFerramenta("parametro_invalido", "quem: ate 80 caracteres, uma linha")
            return v
    r = _git(config, ["config", "--get", "user.name"], git_runner)
    if r is not None and r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()[:80]
    raise ErroFerramenta("quem_desconhecido",
                         "informe `quem` (seu nome), ou defina ECIDADE_MCP_USUARIO, ou `git config user.name`")


def _sugestao(acao: str, caminho: str) -> str:
    return f"git add .mcp/estado/trabalho.json && git commit -m \"estado: {acao} {caminho}\""


def reivindicar_arquivo(config: Config, caminho: str, motivo: str, quem: str | None = None,
                        horas: float | None = None) -> dict[str, Any]:
    rel = relativo(config.raiz, resolver_caminho(config.raiz, caminho, tipo="arquivo"))
    eu = quem_sou(config, quem)
    r = _estado(config).reivindicar(rel, eu, (motivo or "")[:200], horas)
    return {**r, "sugestao_commit": _sugestao("reivindica", rel),
            "lembrete": "renove chamando de novo antes de expirar; libere com liberar_arquivo ao terminar"}


def liberar_arquivo(config: Config, caminho: str, quem: str | None = None, concluido: bool = False,
                    padroes_corrigidos: list[str] | None = None, observacao: str = "") -> dict[str, Any]:
    rel = relativo(config.raiz, resolver_caminho(config.raiz, caminho, deve_existir=False))
    for p in padroes_corrigidos or []:
        if p not in PADROES:
            raise ErroFerramenta("padrao_desconhecido", f"padrao {p!r}; validos: {', '.join(PADROES)}")
    eu = quem_sou(config, quem)
    r = _estado(config).liberar(rel, eu, concluido=concluido, padroes=padroes_corrigidos,
                                observacao=(observacao or "")[:500])
    acao = "conclui" if concluido else "libera"
    dica = (f"commit do codigo: git add {rel} && git commit -m \"migra(<padrao>): {rel}\"" if concluido else "")
    return {**r, "sugestao_commit": _sugestao(acao, rel), "commit_do_codigo": dica}


def quadro(config: Config) -> dict[str, Any]:
    q = _estado(config).quadro()
    try:
        rodadas = ler_resultado_regressao(config)["rodadas"][:5]
    except ErroFerramenta:
        rodadas = []
    return {
        "reivindicacoes_ativas": q["reivindicacoes_ativas"],
        "reivindicacoes_expiradas": q["reivindicacoes_expiradas"],
        "concluidos_recentes": q["concluidos"][:30],
        "total_concluidos": len(q["concluidos"]),
        "rodadas_recentes": rodadas,
        "expiracao_horas": config.expira_horas,
        "lembrete": "o estado vale entre maquinas so depois de commit/pull de .mcp/estado/trabalho.json",
    }


def proximo_trabalho(config: Config, padrao: str | None = None, caminho: str | None = None, limite: int = 10,
                     quem: str | None = None, reivindicar: bool = False) -> dict[str, Any]:
    if not (1 <= limite <= 50):
        raise ErroFerramenta("parametro_invalido", "limite entre 1 e 50 arquivos")
    eu = quem_sou(config, quem)
    est = _estado(config)
    candidatos = padroes_para(padrao) if padrao else [
        p for p in sorted(CATALOGO, key=lambda p: p.prioridade) if p.mecanico in ("sim", "semi") and p.confianca != "baixa"]
    ativos = est.reivindicados_ativos()
    de_outros = {c for c, r in ativos.items() if r["quem"] != eu}
    feitos = est.concluidos_por_padrao()
    for p in candidatos:
        res = buscar(config, padrao=p.nome, caminho=caminho, limite=min(2000, limite * 40),
                     ignorar_arquivos=de_outros | set(feitos.get(p.nome, [])))
        por_arquivo: dict[str, list[int]] = {}
        for o in res["ocorrencias"]:
            por_arquivo.setdefault(o["arquivo"], []).append(o["linha"])
        if not por_arquivo:
            continue
        arquivos = [{"arquivo": a, "ocorrencias": len(ls), "linhas": ls[:20], "ja_e_seu": a in ativos}
                    for a, ls in list(por_arquivo.items())[:limite]]
        out: dict[str, Any] = {
            "padrao": p.como_dict(), "arquivos": arquivos, "quem": eu,
            "passos": ["reivindique (reivindicar=true ou reivindicar_arquivo)",
                       "aplique a correcao EXATA do padrao (exemplo_depois), sem refatorar o resto",
                       "validar_arquivo_php(versao='ambas') em cada arquivo",
                       "rodar_regressao(bateria='php', prefixo=[...]) cobrindo as telas tocadas",
                       "liberar_arquivo(concluido=true, padroes_corrigidos=[padrao]) e commit por caminho"],
        }
        if res["truncado"] and "tempo" in res["motivo_truncado"]:
            out["aviso"] = res["motivo_truncado"]
        if reivindicar:
            ok, recusados = [], []
            for a in arquivos:
                try:
                    est.reivindicar(a["arquivo"], eu, p.nome)
                    ok.append(a["arquivo"])
                except ErroFerramenta as e:
                    recusados.append({"arquivo": a["arquivo"], "erro": e.como_dict()})
            out["reivindicados"] = ok
            out["recusados"] = recusados
            out["sugestao_commit"] = _sugestao("reivindica lote", p.nome)
        return out
    return {"padrao": None, "arquivos": [], "quem": eu,
            "mensagem": "nenhum arquivo pendente para os padroes pedidos (fora os reivindicados por outros e os ja "
                        "concluidos)"}


def padroes_ja_corrigidos(config: Config, contar_em: str | None = None,
                          git_runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    avisos: list[str] = []
    registrados = _estado(config).concluidos_por_padrao()
    commits: dict[str, list[dict[str, str]]] = {}
    r = _git(config, ["log", "-n", "500", "-E", "--grep=^migra\\(", "--format=%h%x09%an%x09%s"], git_runner)
    if r is None or r.returncode != 0:
        avisos.append("git log indisponivel: commits `migra(<padrao>): ...` nao foram contados")
    else:
        for linha in r.stdout.splitlines():
            partes = linha.split("\t", 2)
            if len(partes) == 3 and (m := _COMMIT_MIGRA.match(partes[2])):
                commits.setdefault(m.group(1), []).append({"hash": partes[0], "autor": partes[1], "assunto": partes[2]})
    restantes: dict[str, int] = {}
    if contar_em:
        res = buscar(config, padrao="todos", caminho=contar_em, limite=2000)
        restantes = res["totais_por_padrao"]
        if res["truncado"]:
            avisos.append(f"contagem parcial em {contar_em}: {res['motivo_truncado']}")
    padroes = []
    for p in sorted(CATALOGO, key=lambda p: p.prioridade):
        item: dict[str, Any] = {
            "nome": p.nome, "titulo": p.titulo, "correcao": p.correcao, "forma_canonica": p.exemplo_depois,
            "registrados_no_estado": len(registrados.get(p.nome, [])),
            "arquivos_registrados": registrados.get(p.nome, [])[:50],
            "commits": commits.get(p.nome, [])[:10],
        }
        if contar_em:
            item["restantes_em_contar_em"] = restantes.get(p.nome, 0)
        padroes.append(item)
    return {"padroes": padroes, "avisos": avisos,
            "convencao_commit": "migra(<nome_do_padrao>): <o que mudou> — um padrao por commit, so os caminhos tocados"}
