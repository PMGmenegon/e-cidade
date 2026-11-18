"""Resources: documentos de referencia e o estado atual, lidos do repositorio a cada pedido."""
from __future__ import annotations

import json
from collections.abc import Callable

from mcp.server.mcpserver import MCPServer

from servidor.config import carregar_config
from servidor.estado import Estado
from servidor.padroes import CATALOGO
from servidor.seguranca import ErroFerramenta, resolver_caminho

DOCUMENTOS: dict[str, tuple[str, str, str]] = {
    # uri: (caminho relativo, nome, descricao)
    "ecidade://docs/regras-arquitetura": (".mcp/docs/regras-arquitetura.md", "regras-arquitetura",
                                          "Regras de codigo e de trabalho da migracao (strict_types, DTOs, Actions, "
                                          "injecao no construtor, commits por caminho, regressao)"),
    "ecidade://docs/breaking-changes": (".mcp/docs/guia-breaking-changes.md", "guia-breaking-changes",
                                        "Guia de quebras PHP 7.4 -> 8.5 e Laravel 8 -> 12 com a correcao padrao"),
    "ecidade://regressao/como-usar": ("regressao/COMO-USAR.md", "regressao-como-usar",
                                      "Como rodar e ler a suite de regressao (para dev, QA e gestor)"),
    "ecidade://regressao/triagem": ("regressao/baseline/triagem-divergencias.md", "triagem-divergencias",
                                    "Triagem das divergencias da rodada 'antes' (causas e exemplos)"),
    "ecidade://regressao/decisoes": ("regressao/baseline/decisoes-migracao.md", "decisoes-migracao",
                                     "Decisoes da migracao: impacto, ordem recomendada e esforco"),
}


def _leitor(rel: str) -> Callable[[], str]:
    def ler() -> str:
        try:
            cfg = carregar_config()
            arq = resolver_caminho(cfg.raiz, rel, tipo="arquivo")
        except ErroFerramenta as e:
            return f"(documento indisponivel: {rel}: {e.mensagem})\n"
        return arq.read_text(encoding="utf-8", errors="replace")
    return ler


def registrar(mcp: MCPServer) -> None:
    for uri, (rel, nome, desc) in DOCUMENTOS.items():
        mcp.resource(uri, name=nome, description=desc, mime_type="text/markdown")(_leitor(rel))

    @mcp.resource("ecidade://estado/trabalho", name="estado-trabalho", mime_type="application/json",
                  description="Quem reivindicou qual arquivo (ativas/expiradas) e o que ja foi concluido")
    def estado_trabalho() -> str:
        cfg = carregar_config()
        try:
            q = Estado(cfg.arquivo_estado, expira_horas=cfg.expira_horas).quadro()
        except ErroFerramenta as e:
            q = {"erro": e.como_dict()}
        return json.dumps(q, ensure_ascii=False, indent=2)

    @mcp.resource("ecidade://padroes", name="padroes-legados", mime_type="application/json",
                  description="Catalogo dos padroes legados que buscar_codigo_legado reconhece, com a correcao")
    def padroes() -> str:
        return json.dumps([p.como_dict() for p in sorted(CATALOGO, key=lambda p: p.prioridade)],
                          ensure_ascii=False, indent=2)
