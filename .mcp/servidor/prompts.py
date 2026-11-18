"""Prompts: roteiros padronizados para a IA de cada pessoa seguir do mesmo jeito."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

REGRAS_COMUNS = """Regras fixas (valem para todo o trabalho):
- Leia antes os resources ecidade://docs/regras-arquitetura e ecidade://docs/breaking-changes.
- O gabarito e a referencia PHP 7.4/Laravel 8. Mudanca de comportamento visivel ao usuario e regressao, nao melhoria.
- Altere o minimo necessario; nada de refatoracao "de carona".
- PHP/PHPStan/Pint so pelas tools (rodam no Docker do projeto). Nunca rode shell livre.
- Commit so dos caminhos que voce tocou (git add <caminho>), nunca `git add -A`/`git add .`; sem push sem pedido.
- INCONCLUSIVO e ERRO_AMBIENTE da regressao NUNCA sao aprovacao."""


def registrar(mcp: MCPServer) -> None:
    @mcp.prompt(name="migrar-arquivo", title="Migrar um arquivo para PHP 8.5",
                description="Roteiro completo para migrar UM arquivo: reivindicar, achar padroes, corrigir, validar "
                            "nos dois PHPs, rodar a regressao e liberar")
    def migrar_arquivo(caminho: str) -> str:
        return f"""Migre o arquivo `{caminho}` do e-Cidade da base PHP 7.4/Laravel 8 para PHP 8.5 (e Laravel 12 se for
codigo Laravel), sem mudar o comportamento.

{REGRAS_COMUNS}

Passos:
1. `quadro` para ver se alguem ja esta nele; depois `reivindicar_arquivo(caminho="{caminho}", motivo="migracao")`.
2. `buscar_codigo_legado(padrao="todos", caminho="{caminho}")` e leia o arquivo inteiro. Considere tambem includes/
   requires que ele usa (a quebra pode estar la).
3. `validar_arquivo_php(caminho="{caminho}", versao="ambas")`: anote se compila no 7.4 e no 8.5.
4. Para cada ocorrencia, aplique a correcao padrao do guia (`padroes_ja_corrigidos` mostra a forma canonica usada
   no repositorio). Ocorrencia que nao e bug (comentario, string, falso positivo): deixe e explique.
5. Valide de novo nas duas versoes (`lint`; e `phpstan` com versao="alvo" se for classe/model).
6. `rodar_regressao(bateria="php", prefixo=["^<nome_da_tela_sem_extensao>\\\\.php$"])` (ou a area) e acompanhe com
   `ler_resultado_regressao`. Compare com `ler_triagem` se o caso ja era conhecido.
7. So com IDENTICO (ou DIVERGE explicada e aceita pelo usuario): `liberar_arquivo(caminho="{caminho}",
   concluido=true, padroes_corrigidos=[...])`.
8. Mostre ao usuario: o diff, o resultado da validacao e da regressao, e a sugestao de commit
   (`git add {caminho}` + mensagem `migra(<padrao>): ...`). Nao faca push."""

    @mcp.prompt(name="auditar-model", title="Auditar um Model Eloquent para Laravel 12",
                description="Revisao (sem editar) de um Model Eloquent: o que quebra ou muda do Laravel 8 ao 12")
    def auditar_model(caminho: str) -> str:
        return f"""Audite o Model `{caminho}` para a ida Laravel 8 -> 12 (PHP 8.5). NAO edite nada: produza um relatorio.

{REGRAS_COMUNS}

Verifique e cite linha a linha:
1. `buscar_codigo_legado(padrao="todos", caminho="{caminho}")` (inclui $dates, helpers globais, Carbon diffIn*,
   Doctrine DBAL, nulo implicito).
2. Propriedades: `$dates` (removido no 10: vira `$casts` datetime), `$casts` (o 11 aceita metodo `casts()`; a
   propriedade continua valida), `$fillable`/`$guarded`, `$appends`, `$hidden`, `$table`/`$primaryKey`/`$keyType`/
   `$incrementing` (PostgreSQL com schemas: confira o nome qualificado), `$timestamps`, `$dateFormat`.
3. Datas: Carbon 3 (diffIn* com sinal e float), serializacao de datas (toArray/JSON) e fuso; comparacoes de data.
4. Relacionamentos: tipos de retorno, chaves estrangeiras explicitas, `withDefault`, eager loading usado pelas rotas.
5. Accessors/mutators (`getXAttribute`/`setXAttribute` continuam funcionando; `Attribute::make` e opcional), scopes,
   eventos (`boot`/`booted`), observers.
6. Tipagem: `declare(strict_types=1)`, tipos de parametro/retorno, nulo implicito (8.4), propriedades dinamicas (8.2:
   depreciado; a classe Model permite, classes comuns nao).
7. Rode `validar_arquivo_php(caminho="{caminho}", ferramentas=["lint", "phpstan"], versao="alvo")`.
8. Liste as rotas/telas que usam o Model e diga qual bateria da regressao (laravel/php) cobre cada uma.

Formato do relatorio: tabela `linha | problema | versao que quebra | correcao proposta | risco`, depois
"o que a regressao cobre" e "o que precisa de teste manual"."""

    @mcp.prompt(name="corrigir-padrao-mecanico", title="Corrigir um padrao mecanico em lote",
                description="Pega o proximo lote de arquivos de UM padrao (ex.: parse_str_1_arg), corrige com a "
                            "forma canonica, valida e registra")
    def corrigir_padrao_mecanico(padrao: str, limite: str = "10") -> str:
        return f"""Corrija em lote o padrao legado `{padrao}` (no maximo {limite} arquivos), de forma mecanica e
identica ao que o repositorio ja faz.

{REGRAS_COMUNS}

Passos:
1. `padroes_ja_corrigidos()` para ver a forma canonica e os commits `migra({padrao}): ...` anteriores.
2. `proximo_trabalho(padrao="{padrao}", limite={limite}, reivindicar=true)`: ele pula o que outros reivindicaram e o
   que ja foi concluido, e reivindica o lote para voce.
3. Em cada arquivo, troque SO as ocorrencias do padrao pela forma canonica (`exemplo_depois`). Nao mexa em mais
   nada. Se uma ocorrencia nao se encaixa na forma mecanica (ex.: split com separador regex), corrija a mao e anote.
4. `validar_arquivo_php(caminho=..., versao="ambas")` em cada arquivo: precisa compilar nos dois.
5. `rodar_regressao(bateria="php", prefixo=[...])` com os prefixos das telas tocadas (um regex por grupo). Leia com
   `ler_resultado_regressao`. Telas que eram DIVERGE por este padrao devem virar IDENTICO ou mostrar a proxima
   camada (efeito "cebola" descrito em ecidade://regressao/decisoes): reporte qual.
6. `liberar_arquivo(..., concluido=true, padroes_corrigidos=["{padrao}"])` para cada arquivo pronto; libere sem
   concluir os que ficaram para tras.
7. Proponha UM commit: `git add <cada caminho>` + `migra({padrao}): <N> arquivos (<area>)`, e o commit separado de
   `.mcp/estado/trabalho.json`."""

    @mcp.prompt(name="verificar-com-regressao", title="Verificar uma mudanca com a regressao",
                description="Escolhe a bateria e o recorte certos para uma mudanca, roda e interpreta o resultado")
    def verificar_com_regressao(alvo: str) -> str:
        return f"""Verifique com a suite de regressao a mudanca em: {alvo}

{REGRAS_COMUNS}

Passos:
1. Leia ecidade://regressao/como-usar (se existir) para lembrar o que cada bateria prova.
2. Escolha o recorte: telas legadas (`*.php` na raiz de ecidade/) -> bateria `php` com `prefixo` ancorado
   (ex.: `^arr1_grupotaxa001\\\\.php$`) ou `area`; codigo Laravel (`app/`, rotas `/v4`, `rest/v1`) -> bateria `laravel`
   (so compara; a baseline do Laravel 8 nunca e regravada pelo MCP); fluxo de navegador -> `fluxos`.
3. `rodar_regressao(...)` e anote o id. Cada rodada restaura o banco (~4 min) e so roda uma por vez.
4. `ler_resultado_regressao(id=...)` ate `status=concluida`. Interprete:
   - IDENTICO: mesma resposta que a referencia 7.4 (no escopo do que foi exercitado).
   - DIVERGE: achado real; abra o diff e explique a causa (`ler_triagem(busca=...)` mostra se ja era conhecido).
   - INCONCLUSIVO: NAO exercitado (ex.: 500 nos dois lados, tela sem parametros). Nao conta como aprovado.
   - ERRO_AMBIENTE: a rodada nao vale; corrija o ambiente (conteiner, sessao, baseline) e rode de novo.
5. Responda com: comando usado, totais por veredito, DIVERGE novas com causa, o que NAO foi exercitado, e se a
   mudanca pode seguir (so com zero DIVERGE nova sem explicacao e nenhum ERRO_AMBIENTE)."""
