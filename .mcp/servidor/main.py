"""Servidor MCP do e-Cidade (stdio). Ponto de entrada: `.mcp/.venv/bin/python .mcp/servidor/main.py`.

stdout e EXCLUSIVO do JSON-RPC: logs vao para stderr; durante o servico o SDK ainda desvia o fd 1 para stderr,
entao nem print() acidental nem subprocesso escapam para o protocolo. Toda tool devolve o envelope
`{"ok": bool, "dados": {...} | null, "erro": {"codigo", "mensagem", "detalhes"} | null}` e nunca derruba o servidor.
"""
from __future__ import annotations

import io
import logging
import os
import sys
from pathlib import Path

if __package__ in (None, ""):  # executado como script: .mcp/ no sys.path para achar o pacote `servidor`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collections.abc import Callable  # noqa: E402
from typing import Annotated, Any, Literal  # noqa: E402

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from servidor import prompts, resources  # noqa: E402
from servidor.busca import buscar  # noqa: E402
from servidor.config import carregar_config  # noqa: E402
from servidor.padroes import PADROES  # noqa: E402
from servidor.seguranca import ErroFerramenta  # noqa: E402
from servidor.tools import coordenacao, regressao  # noqa: E402
from servidor.tools.composer import analisar_composer  # noqa: E402
from servidor.tools.validar import validar_arquivo_php  # noqa: E402

log = logging.getLogger("ecidade-mcp")
VERSAO = "0.1.0"

NomePadrao = Literal[("todos", *PADROES)]  # type: ignore[valid-type]
Caminho = Annotated[str, Field(min_length=1, max_length=1024,
                               description="caminho relativo a raiz do repositorio, ex.: ecidade/arr1_grupotaxa001.php")]
Quem = Annotated[str | None, Field(default=None, max_length=80,
                                   description="seu nome (padrao: ECIDADE_MCP_USUARIO ou git config user.name)")]

INSTRUCOES = """Servidor da migracao do e-Cidade (base PHP 7.4/Laravel 8 -> PHP 8.5/Laravel 12).
Antes de mexer em codigo: leia ecidade://docs/regras-arquitetura e ecidade://docs/breaking-changes, veja o `quadro`
e reivindique o arquivo (`reivindicar_arquivo`). PHP/PHPStan/Pint rodam no Docker do projeto (`validar_arquivo_php`);
a regressao roda com `rodar_regressao` e se le com `ler_resultado_regressao`. INCONCLUSIVO/ERRO_AMBIENTE nunca sao
aprovacao. Commits so por caminho (nunca git add -A) e sem push sem pedido do usuario. Toda resposta tem
{ok, dados, erro}: se ok=false, leia erro.codigo/erro.mensagem e corrija a causa."""


class Erro(BaseModel):
    codigo: str
    mensagem: str
    detalhes: dict[str, Any] | None = None


class Resposta(BaseModel):
    ok: bool
    dados: dict[str, Any] | None = None
    erro: Erro | None = None


def executar(nome: str, fn: Callable[..., dict[str, Any]], **kw: Any) -> Resposta:
    try:
        cfg = carregar_config()
        return Resposta(ok=True, dados=fn(cfg, **kw))
    except ErroFerramenta as e:
        log.info("%s: %s", nome, e)
        return Resposta(ok=False, erro=Erro(**e.como_dict()))
    except Exception as e:  # nunca derruba o servidor
        log.exception("erro inesperado em %s", nome)
        return Resposta(ok=False, erro=Erro(codigo="erro_interno", mensagem=f"{type(e).__name__}: {e}"))


LEITURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
ESCRITA_ESTADO = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False,
                                 open_world_hint=False)


def criar_servidor() -> MCPServer:
    mcp = MCPServer(name="ecidade-migracao", title="e-Cidade: migracao PHP 8.5 / Laravel 12", version=VERSAO,
                    instructions=INSTRUCOES)

    @mcp.tool(name="analisar_composer", annotations=LEITURA,
              description="Le composer.json/composer.lock e aponta o que trava a ida para PHP 8.5/Laravel 12: "
                          "restricao de PHP de cada pacote do lock, pacotes abandonados/antigos e a sugestao. "
                          "Ex.: analisar_composer() ou analisar_composer(caminho='ecidade/composer.json')")
    def t_analisar_composer(caminho: Caminho = "ecidade/composer.json") -> Resposta:
        return executar("analisar_composer", analisar_composer, caminho=caminho)

    @mcp.tool(name="buscar_codigo_legado", annotations=LEITURA,
              description="Busca estatica de codigo legado com padroes nomeados (parse_str_1_arg, construtor_php4, "
                          "split, each, ereg, create_function, count_null, pg_resultado_false, reflection_getclass, "
                          "laravel_dates_property...; 'todos' = catalogo sem os de baixa confianca) ou regex livre. "
                          "Sem padrao nem regex devolve o catalogo. Ex.: buscar_codigo_legado(padrao='parse_str_1_arg', "
                          "caminho='ecidade/classes', limite=50)")
    def t_buscar(
        padrao: Annotated[NomePadrao | None, Field(description="nome do padrao ou 'todos'")] = None,
        regex: Annotated[str | None, Field(max_length=300, description="regex Python aplicada linha a linha")] = None,
        caminho: Annotated[str | None, Field(max_length=1024, description="arquivo ou diretorio (padrao: ecidade)")] = None,
        limite: Annotated[int, Field(ge=1, le=2000)] = 100,
        incluir_baixa_confianca: bool = False,
    ) -> Resposta:
        return executar("buscar_codigo_legado", buscar, padrao=padrao, regex=regex, caminho=caminho, limite=limite,
                        incluir_baixa_confianca=incluir_baixa_confianca)

    @mcp.tool(name="validar_arquivo_php", annotations=LEITURA,
              description="Roda php -l (e opcionalmente phpstan, pint, phpcs) no arquivo DENTRO dos conteineres do "
                          "projeto: 7.4 (referencia) e/ou 8.5 (alvo). So arquivos de ecidade/. Ex.: "
                          "validar_arquivo_php(caminho='ecidade/con2_conhist002.php', versao='ambas')")
    def t_validar(
        caminho: Caminho,
        ferramentas: Annotated[list[Literal["lint", "phpstan", "pint", "phpcs"]],
                               Field(min_length=1, max_length=4)] = ["lint"],  # noqa: B006
        versao: Literal["ambas", "alvo", "referencia"] = "ambas",
        nivel_phpstan: Annotated[int, Field(ge=0, le=9, description="nivel do PHPStan (o phpstan.neon do projeto "
                                                                    "nao define nivel)")] = 0,
    ) -> Resposta:
        return executar("validar_arquivo_php", validar_arquivo_php, caminho=caminho, ferramentas=list(ferramentas),
                        versao=versao, nivel_phpstan=nivel_phpstan)

    @mcp.tool(name="rodar_regressao", annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                                                  idempotent_hint=False, open_world_hint=False),
              description="Dispara a suite regressao/ em segundo plano e devolve o id da rodada (uma por vez; cada "
                          "bateria restaura o banco de teste do ambiente e74). Baterias: php (7.4 x 8.5, use prefixo "
                          "ou area), laravel (so comparar com a baseline do Laravel 8), fluxos (comparar), completa. "
                          "Ex.: rodar_regressao(bateria='php', prefixo=['^arr1_grupotaxa001\\\\.php$'])")
    def t_rodar(
        bateria: Literal["php", "laravel", "fluxos", "completa"],
        area: Annotated[list[Literal[regressao.AREAS]], Field(max_length=11)] = [],  # noqa: B006
        prefixo: Annotated[list[Annotated[str, Field(max_length=300)]], Field(max_length=10)] = [],  # noqa: B006
        fluxo: Annotated[list[Annotated[str, Field(max_length=41)]], Field(max_length=10)] = [],  # noqa: B006
        sem_fluxos: bool = False,
        confirmo_rodada_longa: Annotated[bool, Field(description="obrigatorio para php/completa sem area/prefixo "
                                                                  "(horas de execucao)")] = False,
        quem: Quem = None,
    ) -> Resposta:
        return executar("rodar_regressao", regressao.rodar_regressao, bateria=bateria, area=list(area),
                        prefixo=list(prefixo), fluxo=list(fluxo), sem_fluxos=sem_fluxos,
                        confirmo_rodada_longa=confirmo_rodada_longa, quem=quem)

    @mcp.tool(name="ler_resultado_regressao", annotations=LEITURA,
              description="Status e resultado de uma rodada: totais por veredito, DIVERGE novas, ERRO_AMBIENTE, "
                          "INCONCLUSIVO por motivo, resumo.md e o fim do log. Sem id lista as rodadas. Ex.: "
                          "ler_resultado_regressao(id='20261117-153000-php-1a2b')")
    def t_ler_resultado(
        id: Annotated[str | None, Field(max_length=40)] = None,
        pasta: Annotated[str | None, Field(max_length=1024, description="pasta de rodada dentro do repo")] = None,
        max_itens: Annotated[int, Field(ge=1, le=500)] = 50,
        veredito: Literal["IDENTICO", "DIVERGE", "INCONCLUSIVO", "ERRO_AMBIENTE"] | None = None,
    ) -> Resposta:
        return executar("ler_resultado_regressao", regressao.ler_resultado_regressao, id=id, pasta=pasta,
                        max_itens=max_itens, veredito=veredito)

    @mcp.tool(name="ler_triagem", annotations=LEITURA,
              description="Le a triagem das divergencias e as decisoes da migracao (regressao/baseline). Filtra por "
                          "secao (titulo) ou por busca de texto. Ex.: ler_triagem(documento='decisoes', "
                          "secao='Causa por causa') ou ler_triagem(busca='parse_str')")
    def t_ler_triagem(
        documento: Literal["triagem", "decisoes", "lab_lar12", "como_usar"] = "triagem",
        secao: Annotated[str | None, Field(max_length=200)] = None,
        busca: Annotated[str | None, Field(max_length=200)] = None,
    ) -> Resposta:
        return executar("ler_triagem", regressao.ler_triagem, documento=documento, secao=secao, busca=busca)

    @mcp.tool(name="reivindicar_arquivo", annotations=ESCRITA_ESTADO,
              description="Marca em .mcp/estado/trabalho.json que voce esta mexendo no arquivo (expira em 4 h; "
                          "chamar de novo renova). Recusa se outra pessoa ja reivindicou. Ex.: "
                          "reivindicar_arquivo(caminho='ecidade/mat2_cadunidade002.php', motivo='parse_str_1_arg')")
    def t_reivindicar(
        caminho: Caminho,
        motivo: Annotated[str, Field(max_length=200)] = "",
        quem: Quem = None,
        horas: Annotated[float | None, Field(gt=0, le=72)] = None,
    ) -> Resposta:
        return executar("reivindicar_arquivo", coordenacao.reivindicar_arquivo, caminho=caminho, motivo=motivo,
                        quem=quem, horas=horas)

    @mcp.tool(name="liberar_arquivo", annotations=ESCRITA_ESTADO,
              description="Libera um arquivo que voce reivindicou; com concluido=true registra os padroes corrigidos. "
                          "Ex.: liberar_arquivo(caminho='ecidade/x.php', concluido=true, "
                          "padroes_corrigidos=['parse_str_1_arg'])")
    def t_liberar(
        caminho: Caminho,
        concluido: bool = False,
        padroes_corrigidos: Annotated[list[Literal[tuple(PADROES)]], Field(max_length=30)] = [],  # type: ignore[valid-type]  # noqa: B006
        observacao: Annotated[str, Field(max_length=500)] = "",
        quem: Quem = None,
    ) -> Resposta:
        return executar("liberar_arquivo", coordenacao.liberar_arquivo, caminho=caminho, quem=quem,
                        concluido=concluido, padroes_corrigidos=list(padroes_corrigidos), observacao=observacao)

    @mcp.tool(name="quadro", annotations=LEITURA,
              description="Quadro da equipe: reivindicacoes ativas e expiradas, concluidos recentes e ultimas rodadas "
                          "da regressao. Ex.: quadro()")
    def t_quadro() -> Resposta:
        return executar("quadro", coordenacao.quadro)

    @mcp.tool(name="proximo_trabalho", annotations=ESCRITA_ESTADO,
              description="Proximo lote mecanico: arquivos com o padrao de maior prioridade (ou o pedido) que ninguem "
                          "reivindicou e ninguem concluiu, com as linhas. reivindicar=true ja reivindica o lote. Ex.: "
                          "proximo_trabalho(padrao='parse_str_1_arg', limite=10, reivindicar=true)")
    def t_proximo(
        padrao: Annotated[NomePadrao | None, Field(description="padrao (padrao: o mecanico de maior prioridade)")] = None,
        caminho: Annotated[str | None, Field(max_length=1024)] = None,
        limite: Annotated[int, Field(ge=1, le=50)] = 10,
        reivindicar: bool = False,
        quem: Quem = None,
    ) -> Resposta:
        return executar("proximo_trabalho", coordenacao.proximo_trabalho, padrao=None if padrao == "todos" else padrao,
                        caminho=caminho, limite=limite, quem=quem, reivindicar=reivindicar)

    @mcp.tool(name="padroes_ja_corrigidos", annotations=LEITURA,
              description="Para cada padrao: a forma canonica de corrigir, os arquivos registrados como concluidos e "
                          "os commits `migra(<padrao>): ...`; com contar_em conta o que ainda resta. Ex.: "
                          "padroes_ja_corrigidos(contar_em='ecidade/classes')")
    def t_padroes(contar_em: Annotated[str | None, Field(max_length=1024)] = None) -> Resposta:
        return executar("padroes_ja_corrigidos", coordenacao.padroes_ja_corrigidos, contar_em=contar_em)

    resources.registrar(mcp)
    prompts.registrar(mcp)
    return mcp


def servir(mcp: MCPServer) -> None:
    """Serve por stdio protegendo o protocolo.

    O SDK aponta o fd 1 para o stderr enquanto serve e devolve o fd ao terminar. Um `print()` sem flush ficaria no
    buffer do sys.stdout e sairia no stdout de verdade na saida do processo: por isso o sys.stdout vira um
    TextIOWrapper SEM buffer sobre o fd 1 (cada escrita vai na hora para onde o fd 1 aponta, ou seja, o stderr).
    """
    sys.stdout.flush()
    sys.stdout = io.TextIOWrapper(io.FileIO(1, "w", closefd=False), encoding="utf-8", errors="replace",
                                  write_through=True)
    mcp.run("stdio")


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=os.environ.get("ECIDADE_MCP_LOG", "INFO").upper(),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log.info("ecidade-mcp %s iniciando (stdio)", VERSAO)
    servir(criar_servidor())


if __name__ == "__main__":
    main()
