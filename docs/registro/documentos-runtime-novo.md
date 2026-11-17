# mPDF, PhpSpreadsheet e PhpWord novos no runtime novo: o código que precisou mudar (T-065, 14/11/2026)

**Resumo:** o conjunto do runtime novo (`ecidade/composer-runtime-novo.json`/`.lock`, ver `dependencias-laravel13.md`)
já traz as versões medidas em `documentos-candidatas.md`: `mpdf/mpdf` v8.3.1, `phpoffice/phpspreadsheet` 5.11.0 e
`phpoffice/phpword` 1.4.0. Aqui entram só as duas mudanças de código que aquele registro listou, cada uma com prova
antes/depois, e a comparação dos casos de documento do runtime novo com a linha de base do 5.6:

| Ponto | No runtime novo, antes | Mudança | Depois |
|---|---|---|---|
| `app/Domain/Financeiro/Planejamento/Relatorios/ProgramaGestaoXls.php` (32 chamadas) | `Call to undefined method ...Worksheet::mergeCellsByColumnAndRow()` | 3 métodos privados com o nome e o efeito dos que a 1.8.2 tinha; as chamadas trocam `$this->sheet->` por `$this->` | xlsx igual ao do 5.6 |
| `src/Library/SpreadSheet/Template/Parser.php:115,147` | `anexo12.xlsx` estoura 512 MB | o laço de células vai até `ultimaColuna()`: a coluna mais alta, salvo `XFD` | os 24 modelos geram xlsx igual ao do 5.6 |

No 5.6 os dois arquivos geram **o mesmo xlsx byte a byte** antes e depois (todas as partes do pacote, menos a data de
criação em `docProps/core.xml`). O `composer.json`/`composer.lock` do 5.6 não mudou (sha256 igual).

## `ProgramaGestaoXls`: os métodos `*ByColumnAndRow`

`setCellValueByColumnAndRow`, `mergeCellsByColumnAndRow` e `getStyleByColumnAndRow` não existem a partir do
PhpSpreadsheet 2. Na 1.8.2 (`vendor/phpoffice/phpspreadsheet/src/PhpSpreadsheet/Worksheet/Worksheet.php`) cada um só
monta a coordenada com `Coordinate::stringFromColumnIndex()` e chama o método por coordenada (`setCellValue`,
`mergeCells`, `getStyle`), que existem nas duas versões. A classe ganhou três métodos privados que fazem exatamente
isso, com o mesmo nome, e as 32 chamadas passaram a usá-los. Nenhuma chamada usa o valor de retorno de
`setCellValue…`/`mergeCells…`; as de `getStyle…` passam sempre os 4 argumentos.

Prova (`scratchpad/t065_programa_gestao.php`: emite o relatório com dados fixos — 2 programas, órgãos, iniciativas com e
sem metas, 4 exercícios —, sem banco nem HTTP; `scratchpad/t065_dump.php` descreve o xlsx sempre com o leitor do 5.6:
valores, células mescladas e negrito/borda/alinhamento de cada célula com valor):

| | 5.6 | runtime novo |
|---|---|---|
| antes | gera | `Error: Call to undefined method ...mergeCellsByColumnAndRow()` |
| depois | gera; xlsx igual ao de antes byte a byte (fora a data) | gera; descrição igual à do 5.6 |

Quem usa: o relatório `POST /v4/api/financeiro/planejamento/programa-gestao` (Laravel). Não foi pedido por HTTP: no
runtime novo o Laravel 13 ainda não passa do boot.

## `Template/Parser.php`: a coluna `XFD`

O leitor de xlsx da 1.8.2 trata um `<col min="5" max="16384">` criando só a primeira coluna do intervalo
(`Reader/Xlsx/ColumnAndRowAttributes.php:139`, `if ((int) ($column['max']) == 16384) break;`); a 5.11 cria as 16.380.
Com isso `getHighestColumn()` do `anexo12.xlsx` passa de `E` para `XFD`, e o `Parser`, que percorre cada linha até a
coluna mais alta com `setIterateOnlyExistingCells(false)` (o que cria as células), cria 16.384 × 990 células.

Medido em cada uma das 24 planilhas-modelo versionadas (`config/templates/IN22`, `config/templates/MDF/RREO/2020`,
`storage/financeiro`; `scratchpad/parser_colunas.php`): coluna mais alta igual na 1.8.2 e na 5.11 em todas, **menos o
`anexo12.xlsx`**; em nenhuma a 1.8.2 dá `XFD`. Em três a coluna mais alta já passa da última com célula na 1.8.2
(`anexo10` `AMJ`/`I`, `modelo_evolucao_despesa` e `_receita` `BL`/`T`): limitar sempre à última coluna com célula
mudaria o xlsx que o 5.6 gera hoje, por isso o limite só vale para `XFD`:

```php
private function ultimaColuna()
{
    $coluna = $this->getActiveSheet()->getHighestColumn();
    return $coluna === 'XFD' ? $this->getActiveSheet()->getHighestDataColumn() : $coluna;
}
// nos dois laços: $row->getCellIterator('A', $this->ultimaColuna())
```

Com a 1.8.2, `getCellIterator('A', getHighestColumn())` é o que `getCellIterator()` sem argumento faz, e o ramo `XFD`
não acontece nos modelos. Os outros dois laços do arquivo (`parseSection`, `show`) percorrem só células existentes e
não foram tocados.

Prova (`scratchpad/t065_parser.php`: `loadXLS` + `parse` + `save` de cada modelo, sem dados; descrição com
`t065_dump.php`):

| | 5.6 | runtime novo |
|---|---|---|
| antes | 24 de 24 | para no `anexo12.xlsx`: `Allowed memory size of 536870912 bytes exhausted` |
| depois | 24 de 24; xlsx igual ao de antes byte a byte (fora a data) | 24 de 24; descrição igual à do 5.6 |

Quem usa: os anexos IN22 do TCE-RO, os anexos do RREO e do planejamento (`src/Financeiro/.../IN22/*`,
`app/Domain/Financeiro/...`), o extrato do contribuinte (`arr2_extratocontribuinte002.php`). Nenhum foi emitido por
tela: a base não tem os dados.

## Casos de documento: runtime novo × linha de base

`ecidade/tests/sistema/documentos/documentos.py captura` com `--c85` apontando para o runtime novo (5.6 `:8170`,
runtime novo `:8172`, containers que gravam, vigia antes/depois de cada pedido: 6 de 6 `OK`), só os três casos destas
bibliotecas; cada `.txt` comparado com o `.56.txt` de `tests/sistema/documentos/base/`:

| Caso | 5.6 × base | runtime novo × base |
|---|---|---|
| `razao_xlsx` (emissão real, PhpSpreadsheet escrita) | igual | **igual** |
| `phpword_docx` (dublê) | igual | **igual** (descrição estrutural) |
| `planilhas_leitura` (dublê) | igual | igual, salvo **1 linha de metadado**: `anexo12.xlsx` `A1:XFD990` × `A1:E990` (dimensão calculada pela biblioteca; 39 células e hash iguais) |

O dublê `tests/sistema/documentos/dubles/le_planilhas.php` faz o mesmo laço do `Parser` e, como ele, estourava a
memória no runtime novo (`Collection/Cells.php:446`, código 255). Recebeu a mesma regra de fim de linha; no 5.6 a saída
continua igual à da linha de base (tabela acima).

Diferenças de saída da própria biblioteca, já registradas em `documentos-candidatas.md` e que não pedem código:
`razao_xlsx` só em metadado e valores padrão do formato; `phpword_docx` com `<w:noWrap/>` nas células de tabela.

## Lacunas

- `pimaco_mpdf`, o único caso com mPDF, continua parado no gerador de código de barras (`picqer` 0.2.2 não compila no
  8.5): fica para quando esse gerador for trocado.
- O relatório "programa de gestão" e os relatórios que usam o `Parser` não foram emitidos por tela (Laravel 13 sem boot;
  base sem os dados): a prova é dos dois trechos rodados direto, com dados fixos e os modelos versionados.
