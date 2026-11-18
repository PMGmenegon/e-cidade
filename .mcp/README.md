# Servidor MCP do e-Cidade

Um "ajudante" que a sua IA (Claude Code, Cursor, VS Code/Copilot) usa para trabalhar na migração do e-Cidade
**do mesmo jeito que o resto da equipe**: as mesmas regras, a mesma lista de problemas conhecidos, o mesmo PHP (o do
Docker do projeto), a mesma regressão e um quadro de quem está mexendo em quê.

Ele roda **na sua máquina** (nada de servidor central) e conversa com a IA pelo terminal (stdio). Não faz push, não
apaga nada, não roda comando livre.

## Em 3 passos

Tudo no **WSL/Linux**, na **raiz do repositório**.

1. **Instale** (uma vez):

   ```bash
   python3 -m venv .mcp/.venv
   .mcp/.venv/bin/pip install -r .mcp/requirements.txt
   ```

2. **Suba o ambiente Docker do projeto** (precisa para validar PHP e rodar a regressão; o resto funciona sem ele):

   ```bash
   docker compose -p e74 -f regressao/lab/docker-compose.e74.yml up -d
   ```

   (Primeira vez? Siga a seção 1 de `regressao/README.md` para criar o banco.)

3. **Abra o repositório na sua IA.** A configuração já vem no repositório; veja abaixo a sua IA. Teste pedindo:
   *"use a tool quadro do servidor ecidade"*.

## Como cada IA conecta

| IA | Arquivo (já no repositório) | O que fazer |
|---|---|---|
| **Claude Code** | `.mcp.json` | Rode `claude` **na raiz do repositório** (dentro do WSL). Na primeira vez ele pergunta se confia no servidor `ecidade`: aceite. `/mcp` mostra o status. |
| **Cursor** | `.cursor/mcp.json` | Abra a pasta **pelo WSL** (Cursor → *Connect to WSL* → pasta do repositório). Em *Settings → MCP*, ative `ecidade`. |
| **VS Code** (Copilot Chat) | `.vscode/mcp.json` | Abra a pasta **pelo WSL** (`code .` dentro do WSL, ou extensão *WSL*). No Chat, modo **Agent** → ícone de ferramentas → `ecidade` → *Start*. |

Os arquivos usam caminhos relativos ao projeto (`${workspaceFolder}` no Cursor/VS Code; a raiz do projeto no Claude
Code). Se a sua versão não aceitar, troque por caminho absoluto (ex.: `/home/voce/e-cidade-74/.mcp/.venv/bin/python`).

**Sem abrir pelo WSL (IA rodando no Windows)**: chame o servidor através do `wsl.exe`. Claude Code:

```bash
claude mcp add ecidade --scope local -- wsl.exe -d Ubuntu-24.04 -- /home/voce/e-cidade-74/.mcp/.venv/bin/python /home/voce/e-cidade-74/.mcp/servidor/main.py
```

Cursor/VS Code: mesmo `command: "wsl.exe"` com esses `args`. (Testado: o protocolo passa pelo `wsl.exe` sem problema.)

## O que cada tool faz

Toda resposta vem no formato `{"ok": true|false, "dados": {...}, "erro": {"codigo", "mensagem"}}`. Se der erro, a
mensagem diz o que fazer; o servidor continua de pé.

| Tool | Para que serve | Exemplo de pedido |
|---|---|---|
| `quadro` | Quem está mexendo em quê, o que já foi concluído, últimas rodadas da regressão | `quadro()` |
| `reivindicar_arquivo` | "Estou mexendo neste arquivo" (vale 4 h; chamar de novo renova). Recusa se outra pessoa já pegou | `reivindicar_arquivo(caminho="ecidade/mat2_cadunidade002.php", motivo="parse_str")` |
| `liberar_arquivo` | Solta o arquivo; com `concluido=true` registra o que foi corrigido | `liberar_arquivo(caminho="ecidade/mat2_cadunidade002.php", concluido=true, padroes_corrigidos=["parse_str_1_arg"])` |
| `proximo_trabalho` | Próximo lote de arquivos de um problema mecânico, pulando os de outros e os já feitos (`reivindicar=true` já pega o lote) | `proximo_trabalho(padrao="parse_str_1_arg", limite=10, reivindicar=true)` |
| `buscar_codigo_legado` | Procura código antigo por **nome de problema** (`parse_str_1_arg`, `construtor_php4`, `split`, `each`, `ereg`, `create_function`, `count_null`, `pg_resultado_false`, `reflection_getclass`, `laravel_dates_property`… ou `todos`) ou por regex. Sem nada, lista o catálogo | `buscar_codigo_legado(padrao="todos", caminho="ecidade/con2_balancrece002.php")` |
| `padroes_ja_corrigidos` | Como cada problema é corrigido no repositório (forma padrão), o que já foi feito e quanto falta | `padroes_ja_corrigidos(contar_em="ecidade/classes")` |
| `validar_arquivo_php` | `php -l`, PHPStan, Pint ou PHPCS **dentro do Docker**: PHP 7.4 (referência), 8.5 (alvo) ou os dois | `validar_arquivo_php(caminho="ecidade/con2_conhist002.php", versao="ambas")` |
| `analisar_composer` | O que no `composer.json`/`composer.lock` trava o PHP 8.5/Laravel 12 | `analisar_composer()` |
| `rodar_regressao` | Dispara a regressão em segundo plano e devolve o id (uma por vez). Baterias: `php` (com `prefixo` ou `area`), `laravel` e `fluxos` (só comparam), `completa` | `rodar_regressao(bateria="php", prefixo=["^arr1_grupotaxa001\\.php$"])` |
| `ler_resultado_regressao` | Andamento e resultado de uma rodada (sem id: lista as rodadas) | `ler_resultado_regressao(id="20261117-153000-php-1a2b")` |
| `ler_triagem` | Lê a triagem das divergências e as decisões da migração, por seção ou busca | `ler_triagem(documento="decisoes", secao="Resumo executivo")` |

**Resources** (a IA lê como documentos): `ecidade://docs/regras-arquitetura`, `ecidade://docs/breaking-changes`,
`ecidade://regressao/como-usar`, `ecidade://regressao/triagem`, `ecidade://regressao/decisoes`,
`ecidade://estado/trabalho`, `ecidade://padroes`.

**Prompts** (roteiros prontos; no Claude Code aparecem como `/mcp__ecidade__...`): `migrar-arquivo`,
`auditar-model`, `corrigir-padrao-mecanico`, `verificar-com-regressao`.

## Como a equipe se coordena

- O quadro fica em `.mcp/estado/trabalho.json`, **no Git**. Depois de reivindicar/liberar, faça commit **só desse
  arquivo** (`git add .mcp/estado/trabalho.json`). Detalhes e o que fazer em conflito: `.mcp/estado/README.md`.
- Commit de código: **só os arquivos que você mexeu** (`git add <arquivo>`), nunca `git add -A`. Mensagem
  `migra(<problema>): <o que mudou>`. Regras completas: `.mcp/docs/regras-arquitetura.md`.

## O que o servidor NUNCA faz

- Rodar comando livre: só uma lista fechada (`php -l`, PHPStan, Pint, PHPCS) nos contêineres `ecidade74_php74` e
  `ecidade74_php85`, e os comandos fixos da suíte `regressao/`.
- Ler ou escrever fora do repositório, seguir atalho (symlink) para fora, entrar em `.git/` ou ler segredos (`.env`,
  `db_conn.php`, chaves).
- Regravar baseline da regressão, fazer commit ou push.
- Escrever qualquer coisa no stdout além do protocolo (os logs vão para o stderr).

## Ajustes (variáveis de ambiente, opcionais)

| Variável | Padrão | Para que |
|---|---|---|
| `ECIDADE_MCP_USUARIO` | `git config user.name` | seu nome no quadro |
| `ECIDADE_MCP_EXPIRA_HORAS` | `4` | validade da reivindicação |
| `REGRESSAO_CONTAINER_REF` / `REGRESSAO_CONTAINER_PHP_NOVO` / `REGRESSAO_CONTAINER_BANCO` | `ecidade74_php74` / `ecidade74_php85` / `ecidade74_database` | nomes dos contêineres (os mesmos da suíte `regressao/`) |
| `ECIDADE_MCP_TIMEOUT_PHPSTAN` | `600` | segundos |
| `ECIDADE_MCP_LOG` | `INFO` | nível do log (stderr) |

## Problemas comuns

| `erro.codigo` | O que fazer |
|---|---|
| `conteiner_indisponivel` / `conteiner_parado` | suba o ambiente (passo 2) |
| `docker_indisponivel` | o Docker não está no PATH desta sessão (no WSL: Docker Desktop com integração WSL ligada) |
| `venv_regressao_ausente` | `python3 -m venv regressao/.venv && regressao/.venv/bin/pip install -r regressao/requirements.txt` |
| `ferramenta_indisponivel` | Pint/PHPCS não estão instalados no `vendor/` do projeto (instalar é decisão da equipe) |
| `quem_desconhecido` | passe `quem="seu nome"` ou defina `ECIDADE_MCP_USUARIO` |
| `ja_reivindicado` | outra pessoa está no arquivo até a hora em `detalhes.expira`; escolha outro (`proximo_trabalho`) |
| `rodada_em_andamento` | espere a rodada atual (`ler_resultado_regressao`) |
| `estado_corrompido` | conflito do Git em `trabalho.json`: veja `.mcp/estado/README.md` |
| `confirmacao_necessaria` | a rodada pedida leva horas: restrinja com `prefixo`/`area` |

## Para quem mantém o servidor

- Código em `.mcp/servidor/` (`main.py` registra tools/resources/prompts; `seguranca.py` confina caminhos;
  `docker_exec.py` tem a lista de comandos permitidos; `estado.py` a escrita atômica com trava; `padroes.py` o
  catálogo). SDK oficial `mcp` 2.x (`MCPServer`, o antigo FastMCP) e `pydantic`, versões fixas em `requirements.txt`.
- Testes (sem Docker, tudo simulado): `cd .mcp && .venv/bin/python -m pytest`. Inclui cliente MCP em processo, o
  servidor de verdade por stdio, a garantia de que o stdout só tem JSON-RPC e uma corrida com 2 processos no estado.
- Teste manual com o inspetor oficial: `npx @modelcontextprotocol/inspector .mcp/.venv/bin/python .mcp/servidor/main.py`;
  no Claude Code, `claude mcp list` mostra se o `ecidade` conectou.
