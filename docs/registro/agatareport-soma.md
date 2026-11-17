# AgataReport: soma com célula não numérica (T-041)

**Defeito (só no 8.5):** `pro1_relcgm002` gera PDF no 5.6 e dá 500 no 8.5. O `AgataReport` soma células vindas do banco (texto) em
`$this->newSummary[...]['sum'] += $Cell` e usa `pow($Cell - $average, 2)`. No 5.6 uma string não numérica entrava na conta pelo prefixo
numérico (`"12abc"` = 12, `"abc"` e `""` = 0, `"0x1A"` = 26); no PHP 8 a string sem número é `TypeError`.

**Correção** (`ecidade/dbagata/classes/reports/AgataReport.class`, ISO-8859-1 preservado): método `CellNumber($Cell)`, usado nas duas contas.
Número e string numérica passam direto (a conta do PHP faz o resto, int ou float como antes); string não numérica vira o prefixo
numérico como no 5.6: hexadecimal `0x…` sem sinal, ou `[sinal]dígitos[.dígitos][e[sinal]dígitos]`, senão 0. Nenhum layout e nenhuma fórmula mudou.

## Pontos do `dbagata/` com aritmética sobre célula/valor do banco (critério 1)

| Onde (antes da correção) | Conta | Situação |
|---|---|---|
| `classes/reports/AgataReport.class:122` | `['sum'] += $Cell` | **quebrava; corrigido** |
| `classes/reports/AgataReport.class:168` | `pow($Cell - $average, 2)` | **quebrava; corrigido** |
| `AgataReport.class:123-132` | `>`/`<` entre células e `max`/`min` | sem mudança: célula é string do `pg_fetch` (ou null) e a regra string × string é a mesma nos dois |
| `AgataReport.class:165` e `Summarize()` | `sum / count`, `sum_var / (count-1)` | `count` ≥ 1 quando há soma; `gavg` já testa antes de dividir |
| `classes/reports/AgataMergePdf.class:244`, `AgataMergeSxw.class:413` | `['sum'] += $SubConteudo` | já protegidos por `is_numeric($SubConteudo)` |
| `classes/reports/AgataBarCode.class:845,899` (`$txt[$i] * $w`, `$ck + $txt[$i]`) | dígito de verificação do código de barras | **não corrigido**: só a `AgataOOParser` (mala direta do OpenOffice) usa, nenhuma tela chama; o texto são dígitos |
| `functions/**/*.fun` (`numbers/a_accumulate_value:11`, `custom/a_saldo:15,21`, `a_saldo_disponivel:11,13`, `a_saldo_disponivel_produto:14,16`) | `$string_column - $array_row[...]` | **não corrigido**: funções de exemplo da Agata sem chamador (nenhum `.agt` de `dbagata/reports` usa `function`) |
| `AgataDia`, `AgataHtml`, `AgataTxt*`, `MyPdf`, `fpdf151`, `pclzip` | `+=`, `-=` | contadores e geometria internos, não células |

**Fora do escopo, registrado (defeito de migração, só no 8.5):** `ProcessFormula()` calcula fórmulas de total com `@eval("\$result = $Formula;")`
(`sum(2) / max(7)`); divisão por zero ali dava warning e `false` no 5.6 e é `DivisionByZeroError` no 8 (o `@` não suprime). Não aparece em `pro1_relcgm002`;
fica para tarefa própria se algum relatório chegar lá.
Conferido: `origin/nucleo/correcoes-transversais` não difere de `laravel/integracao` em `ecidade/dbagata/` (`git diff --stat` vazio): nada a reaproveitar nem repetir.

## Verificação

- **Trecho isolado** (`tests/suite/dbagata/AgataReportSomaTest.php`, camada integração): 19 células (`"12"`, `"1.5"`, `"abc"`, `""`, `null`, `"12abc"`,
  `" 3"`, `"3 "`, `"1e3x"`, `"-4.5kg"`, `".5"`, `"5."`, `"+7z"`, `"1.5e2"`, `"0x1A"`, `"-0x1A"`, `"abc12"`, `"1e"`, `"012"`): soma (tipo e valor) e variância iguais
  aos medidos no 5.6 com a expressão original. Passa no 5.6 (PHPUnit 5.7) e no 8.5 (9.6). Antes da correção o 8.5 dá `TypeError` em `"abc"`, `""`, `"abc12"`.
- **`pro1_relcgm002`** (`?ordenacao=z01_numcgm&z01_numcgm_inicial=1&z01_numcgm_final=40`): triagem por leitura do código — só lê (`cl_dbagata` com `SELECT`);
  as únicas gravações são `db_usuariosonline`/`db_logsacessa` das libs. Rodado em container que grava, com `vigia-banco.sh` em volta: **rc=0**, mudaram só
  `db_logsacessa_202611_0` e `db_usuariosonline`. 5.6: PDF 200, 1 página A4, 2.243 bytes; **8.5 com a correção: PDF idêntico** (`pdftotext -layout` sem diferença; só a hora de emissão muda,
  mascarada). **8.5 sem a correção** (arquivo da integração restaurado só nessa medição): 500 `Erro interno`.
- Suíte (unitário + integração) na branch, base `0114188f9`: 5.6 **282/282**; 8.5 **76/78** (as 2 falhas são o handler V3 da T-026, ainda não integrada).
- `php -l` ok nos dois runtimes (`AgataReport.class`, teste).
