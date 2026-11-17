# Migração das janelas de pesquisa (`ecidade/func_*.php`) — branch `feat/func-php85-migrated`

Registro do que foi alterado, medido e deixado pendente nas janelas de pesquisa `ecidade/func_*.php` a partir da base `base-php84` (`59ce715060e7046067ba821288f2b7157970a637`).

---

## O quadro geral dos 2.993 arquivos

Nem todo `func_*.php` precisava de alteração. Um censo feito com `token_get_all(..., TOKEN_PARSE)` e `short_open_tag=1` separou os **2.993** arquivos do diretório `ecidade/` em grupos sem sobreposição:

| Grupo | Arquivos | Situação nesta branch |
|---|---:|---|
| `parse_str()` de 1 argumento (`parse1_only`) | 2.496 | Migrados (`parse_str(..., $__qs); extract($__qs);`) |
| `parse_str()` de 1 arg + `split()` literal | 17 | Migrados (as duas substituições) |
| Somente `split()` literal | 3 | Migrados (`split()` → `explode()`) |
| Frente `split()` com regex (`excluded_split_regex`) | 11 | Migrados (12 `split` regex, 10 `split` literais e 9 `parse_str`) |
| **Total alterado na branch** | **2.527** | Commitados em `feat/func-php85-migrated` |
| Já usavam `$__qs` na base | 253 | Intocados |
| Já usavam `parse_str()` com 2 argumentos | 71 | Intocados |
| Sem `parse_str()` nem `split()` | 139 | Intocados |
| Erro de sintaxe pré-existente na base | 3 | Mantidos intactos |

Os três arquivos que continuam quebrados de origem são:
- `ecidade/func_calendario_atendimento_lembrete.php` (linha 50)
- `ecidade/func_calendario_atendimento_relatorio.php` (linha 151)
- `ecidade/func_issarquivoretencaodisarq.php` (linha 33)

Eles já falham no `php -l` tanto no PHP 5.6 quanto no PHP 8.5 na própria `base-php84`. Mexer neles agora misturaria reparo manual de código quebrado com migração mecânica, então ficaram de fora.

---

## O que mudou no código (e por quê)

### 1. `parse_str()` de um argumento

No PHP 5.6, `parse_str($str)` jogava variáveis direto no escopo atual. No PHP 8, chamar `parse_str()` sem o segundo parâmetro é erro fatal.

A substituição adotada segue o padrão já usado nos 253 arquivos da base:

```php
// antes
parse_str($_SERVER["QUERY_STRING"]);

// depois
parse_str($_SERVER["QUERY_STRING"], $__qs);
extract($__qs);
```

Quando o `parse_str()` aparecia direto no corpo de um `if` ou `else` sem chaves (como em `func_nome_01102004.php` e em quatro arquivos da frente regex), o transformador envolveu o bloco em `{ ... }` para que `extract($__qs)` não escapasse da condição.

**Trade-off assumido aqui:** `parse_str(..., $__qs); extract($__qs);` não é 100% invisível. Se existir uma variável `$__qs` prévia, ela é sobrescrita (confirmado em teste sintético antes da escala). Além disso, entradas com nomes reservados como `?this=`, `?_POST=` ou `?GLOBALS=` colidem ou falham no bootstrap `Emulate.php` antes mesmo de chegar ao `func_*.php`. Antes de unir os lotes na branch, essas limitações foram registradas explicitamente e aceitas para este escopo em troca de manter o mesmo padrão já adotado no repositório.

### 2. `split()` literal e os 11 casos com regex

`split()` foi removida no PHP 7.0. Os casos se dividiam em dois conjuntos:

- **20 arquivos com separador literal** (`"/"`, `"-"`, `","`, `"#"`): trocados diretamente por `explode()`. Antes de gerar o lote, testamos 28 entradas de borda (vazio, `"0"`, separador no início, no fim e repetido) contra o `split()` nativo do PHP 5.6 CLI — sem o shim `Emulate::split` — e contra `explode()` no PHP 5.6.40 e no PHP 8.5.12. Todos os 28 retornaram arrays idênticos.
- **11 arquivos com regex POSIX** (12 chamadas ao todo):
  - 8 chamadas com `"\\|"` e 1 com `"[\|]"` (`func_interval.php:54`) → `explode("|", ...)`
  - 1 chamada com `"\."` (`func_consbens001.php:127`) → `explode(".", ...)`
  - 2 chamadas com `'[/.-]'` (`func_empempenhoaut001.php`, linhas 171 e 177) → `preg_split('/[\/.-]/', ...)`

No teste com oráculo POSIX nativo do PHP 5.6 (44 entradas por padrão × 4 padrões = 176 comparações, incluindo acentos em Latin-1), `explode()` e `preg_split('/[\/.-]/', ...)` sem modificador `/u` bateram byte a byte entre PHP 5.6 nativo, candidato 5.6 e candidato 8.5.

Um detalhe importante: o shim `Emulate::split()` do bootstrap repassa o padrão direto para `explode()` sem interpretar regex. Ou seja, restaurar a semântica POSIX fiel em `func_empempenhoaut001.php` e `func_interval.php` muda o comportamento em relação ao que o shim fazia em PHP 8 — diferença aceita para recuperar o comportamento original do PHP 5.6.

---

## Armadilhas que o transformador pegou no caminho

O primeiro gerador travou em **13 arquivos** dos 2.496 elegíveis (`quarantined`). Em vez de relaxar as checagens e arriscar editar código errado, analisamos cada falha antes de mexer no parser:

- **12 arquivos** quebraram porque SQL interpolado em strings (`"$sql ... ($var) ..."`, token `T_ENCAPSED_AND_WHITESPACE`) continha parênteses e chaves literais. O contador antigo lia o texto do token e se perdia na contagem de delimitadores.
- **1 arquivo** (`func_empempenho001.php`) tinha causa diferente: o parser antigo de `switch/case` consumia o `if` seguinte e via o `else` como órfão.

Corrigimos o analisador para considerar pontuação estrutural apenas nos tokens de pontuação reais e na abertura de interpolação (`T_CURLY_OPEN` / `T_DOLLAR_OPEN_CURLY_BRACES`), escrevemos 11 testes unitários e rodamos o script novo sobre todos os **2.483** arquivos já gerados antes: **0 bytes de diferença** (`2.483/2.483` idênticos) e todos os 13 recuperados limpos.

---

## O que foi verificado depois da união dos lotes

Na árvore final da branch `feat/func-php85-migrated` (comparada a `base-php84` em `59ce71506`):

- **Escopo exato:** `git diff --name-only` bate com a lista dos **2.527** arquivos (`2527 files changed, 2575 insertions(+), 2570 deletions(-)`). Nenhum outro arquivo foi tocado.
- **Sintaxe nos dois PHPs (`short_open_tag=1`):** `php -l` em `php:5.6-cli` e `php:8.5-cli` passou nos **2.527** arquivos alterados com **0 falhas** (apenas avisos de depreciação pré-existentes na base, como `case ...;` em `func_empempenhoMovimentacaoPatrimonial.php:174` e casts `(integer)`).
- **Varredura por tokens na árvore final:** **0 chamadas** restantes de `split()` e **0 chamadas** de `parse_str()` com um argumento nos 2.527 arquivos.
- **Bytes, EOL e encoding:** mantidos sem alteração (Latin-1/UTF-8 e quebras LF/CRLF originais de cada arquivo).
- **Testes HTTP em laboratório isolado (PHP 5.6 original vs 5.6 candidato vs 8.5 candidato, com restauração de sessão e SHA-256 por requisição):**
  - No **PHP 5.6**, o candidato empatou com o original em todos os cenários exercitados (lote piloto 1 com 103 cenários, amostra estratificada `parse_str` com 14, frente `split` literal com 36, sublote de quarentena com 26 e frente regex com 22).
  - No **PHP 8.5**, os cenários de tela que avançaram além da linha migrada expuseram **dependências pré-existentes fora dos `func_*.php`** (detalhadas abaixo).

---

## O que esta branch NÃO resolve (e continua pendente)

Esta entrega trata **apenas** das incompatibilidades de `parse_str()` (1 argumento) e `split()` dentro dos `func_*.php`. Ela **não** torna toda tela de pesquisa funcional sozinha em PHP 8.5 onde existam dependências externas ainda não migradas:

1. **Classes DAO com construtor PHP 4:** várias telas quebram logo após o `parse_str()` ao instanciar `$cl...->rotulo->label(...)` sobre `null` (ex.: `func_acordocomissaotipo.php:37`, `func_gestorgrupoindicador.php:39`, `func_gestorindicador.php:39` e 6 telas do lote 1).
2. **Tipagem estrita e erros de runtime pós-linha no PHP 8.5:** falhas como `TypeError` em `pg_num_rows(false)` (`func_agendamentotarefas.php:142`, `func_calendario_atendimento_consulta.php:145`, `func_consbens001.php:335`, `EmpenhoFinanceiro.model.php:114` via `func_empempenho001.php`), `mktime()` recebendo string (`func_calendar.php:208`) e `DivisionByZeroError` (`func_informarvalores.php:104`).
3. **`$HTTP_POST_VARS` no debug de `func_tarefahorario.php:35`:** `db_postmemory($HTTP_POST_VARS, 2)` imprimiu valores vazios no PHP 8.5 antes da linha 36 (`parse_str`), embora a saída seguinte gerada pelos parâmetros de `QUERY_STRING` tenha coincidido.
4. **Cobertura não instrumentada:** testes HTTP em laboratório sem fixtures completas de banco não exercitam todos os desvios internos de `split()`, escritas no banco nem callbacks JavaScript no navegador.

---

## Como conferir ou fazer rollback

A `base-php84` permaneceu intacta em `59ce715060e7046067ba821288f2b7157970a637`. Para inspecionar o diff completo ou descartar sem risco:

```bash
git fetch origin
git diff --stat base-php84..feat/func-php85-migrated
git checkout feat/func-php85-migrated
```
