# Núcleo — migração do PHP 7.4 (PR #8) para o 8.5

Branch `nucleo/8.5`, criada da `tributario/8.5` (PR #29), que parte de `migracao/parse-str-e-guardas-sql`: o
`parse_str` de 1 argumento e as guardas `pg_*` dos *wrappers* centrais já vêm de lá e não são refeitos aqui.
Escopo combinado com o grupo. Ferramentas: o MCP do grupo (`.mcp/`) para reivindicar/liberar arquivos no quadro,
validar nos dois runtimes (`validar_arquivo_php`) e buscar padrões (`buscar_codigo_legado`); `scratchpad/cmp.py` para
as baterias.

## 1. Tamanho (20/11/2026)

| Pasta | Arquivos | Linhas |
|---|---|---|
| `libs/` | 93 | 65.204 |
| `dbforms/` | 47 | 17.071 |
| `config/` | 5 | 433 |
| `fpdf151/` | 203 | 66.018 |
| `std/` | 42 | 8.990 |
| `dbagata/` | 216 | 85.433 |

Com `FrontController.php` e as telas de login: 611 arquivos. `php -l`: 5 não compilam no 7.4 (pré-existente) e **16 só no
8.5**. Inventário (código sem comentários e textos): 153 construtores estilo PHP 4 (128 no `dbagata/`), 66 offsets
`$s{i}` em 12 arquivos, 31 `each()`, 17 `ereg` (já quebrado no 7.4), 3 `money_format`/`magic_quotes`, 1
`create_function`, ~28 `is_resource`/`gettype(...) == "resource"` sobre resultado do PostgreSQL.

## 2. Lotes

| Lote | O quê | Por que nesta ordem |
|---|---|---|
| **1** | os 12 arquivos com offset `$s{i}` (parse error no 8.5) | `fpdf151/fpdf.php` e `libs/JSON.php` travavam ~2.400 telas |
| 2 | jpgraph (`libs/jpgraph`, `dbagata/classes/jpgraph`): ~30 assinaturas incompatíveis com a mãe (o `php -l` só acusa as do mesmo arquivo; as outras explodem ao carregar o gráfico) | último grupo que não carrega no 8.5 |
| 3 | funções centrais que mudaram de resultado: `is_resource`/`gettype` sobre `PgSql\Result` (`db_selectrecord`, `db_multiploselect`…), comparações número × texto no `db_select`/`db_inputdata`, `reset()`/`count()` de nulo | silenciosas: a tela abre, mas com dado faltando |
| 4 | construtores estilo PHP 4 do `dbagata/`, `fpdf151/` e `libs/` (153), com as chamadas cruzadas ao nome antigo | relatórios do Agata |
| 5 | `each()`, `create_function`, `money_format`/`magic_quotes`, `pg_lo_export` na ordem antiga (`std/DBLargeObject.php`), `Deprecated` de `pg_*()` sem conexão | cauda |

## 3. Lote 1 — `$s{i}` → `$s[i]` (20/11/2026)

`CurlyToSquareBracketArrayStringRector` sozinha (Rector 2.8.5, `.php`/`.class`/`.inc`), rodada até zero. O Rector
também apagava espaços de 6 linhas em branco: restauradas. Diff conferido caractere a caractere: 62 linhas em 12
arquivos, **a única mudança é `{`→`[` e `}`→`]`**.

Arquivos: `fpdf151/fpdf.php`, `libs/JSON.php`, `fpdf151/impmodelos/mod_imprime10/12/13/1333.php`,
`libs/mail/func.php`, `libs/jpgraph/jpgraph.php`, `dbagata/classes/fpdf151/fpdf.php`, `dbagata/classes/fpdf151/teste.php`,
`dbagata/classes/jpgraph/jpgraph.php`, `dbagata/classes/util/editor.class`.

Prova:
- `validar_arquivo_php` (MCP, `versao=ambas`): 10 de 12 compilam no 7.4 e no 8.5; as 2 `jpgraph.php` passam a mostrar
  a camada seguinte (assinaturas, lote 2).
- **7.4 inalterado:** resposta do 7.4 em 80 telas sorteadas entre as que incluem os arquivos, com o código antes e depois
  do commit: 71 idênticas; as 9 restantes são PDFs que variam sozinhos de uma captura para outra com o mesmo código
  (horário dentro do fluxo comprimido), e o texto de cada uma (`pdftotext`, sem a hora) é idêntico antes e depois.
- **8.5:** bateria 7.4 × 8.5 nas 2.435 telas que incluem diretamente `fpdf151/`, `libs/JSON.php` ou `libs/mail/func.php`:
  **1.833 idênticas**. Nenhuma das 593 divergentes quebra mais nesses arquivos.
- No Tributário (com bateria anterior para comparar): das 362 telas alcançadas, divergentes **339 → 86**; 253 passaram
  a idênticas; nenhuma divergência nova.

O que as 593 mostram agora é a camada de trás, quase toda **das próprias telas**: `pg_num_rows`/`pg_numrows` sobre consulta
que falhou em 446 telas (decisão 2a do grupo: arquivo a arquivo, por área), `count()`/`sizeof()` de nulo, `cal_days_in_month`
com mês vazio, `mktime` com texto, assinaturas do `RelatoriosLegaisBase` (Financeiro, já tratadas na branch dele). Do núcleo
aparecem `dbforms/db_funcoes.php:1342` (5 telas), `fpdf151/pdf1.php:165` (4), `model/dbGeradorRelatorio.model.php` e
`model/cda.model.php` com `$s{i}` (8; `model/` não estava no escopo medido do lote 1) e uma divisão de texto em
`fpdf151/fpdf.php` (1).
