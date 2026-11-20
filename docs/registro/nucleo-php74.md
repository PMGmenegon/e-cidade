# Núcleo — migração do PHP 7.4 (PR #8) para o 8.5

Branch `nucleo/8.5`, criada da `tributario/8.5` (PR #29), que parte de `migracao/parse-str-e-guardas-sql`: o
`parse_str` de 1 argumento e as guardas `pg_*` dos *wrappers* centrais já vêm de lá e não são refeitos aqui.
Escopo combinado com o grupo. Cada arquivo é reservado e concluído no quadro de trabalho (`.mcp/estado/trabalho.json`),
com `php -l` nos dois runtimes; as baterias de telas usam `scratchpad/cmp.py` (`docs/como-testamos.md`).

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

## 4. Lote 2 — jpgraph (20/11/2026)

Só três pontos do sistema carregam o jpgraph: `tra_estatdia002.php` (linha, jpgraph de `libs/`; no menu por
`tra_estatdia001.php`), `libs/jpgraph/ass_rreqtotais002.php` (pizza e pizza 3D, `libs/`; fora do menu) e
`dbagata/classes/reports/AgataGraph.class` (linha e barra, jpgraph do Agata). O lote ficou no que esses pontos
carregam; os módulos que ninguém carrega estão no fim desta seção.

Dois commits manuais, só a linha da declaração:

| Arquivo | Método | Mudança |
|---|---|---|
| `libs/jpgraph/jpgraph.php`, `dbagata/classes/jpgraph/jpgraph.php` | `GraphTabTitle::SetPos`, `::Stroke` | parâmetros que a mãe (`Text`) tem: acrescentados com padrão, sem uso |
| `libs/jpgraph/jpgraph.php`, `dbagata/classes/jpgraph/gd_image.inc.php` | `RotImage::FilledArc` | `$style=""`, como na mãe, sem uso |
| `libs/jpgraph/jpgraph.php` | `SuperScriptText::GetWidth`, `::GetFontHeight` | sem `&`, como na mãe (o método não reatribui `$aImg`) |
| `libs/jpgraph/jpgraph_pie.php` | `PiePlotC::Stroke`, `PieGraph::Add` | com `&`, como na mãe (não reatribuem; as chamadas passam variável) |
| `libs/jpgraph/jpgraph_pie3d.php` | `PiePlot3D::Stroke`; `::AddSliceToCSIM` | `&` como na mãe; os 2 últimos parâmetros com padrão (a única chamada passa os 8) |
| `libs/jpgraph/jpgraph.php` | `JpGraphError::Install`, `::Raise`, `Image::CreateFromString` | `static`: o próprio jpgraph os chama como `Classe::metodo()` e nenhum usa `$this` (no 8.5 é erro fatal) |

Prova:
- `php -l` nos dois runtimes: 5 de 5 sem erro (antes, os dois `jpgraph.php` falhavam no 8.5).
- **7.4 inalterado:** `tra_estatdia001`, `tra_estatdia002` e `ass_rreqtotais002` com a mesma resposta antes e depois; os
  gráficos desenhados direto (linha, linha girada, pizza, pizza 3D, barra, imagem de erro) com a mesma saída ou o
  mesmo erro antes e depois.
- **7.4 × 8.5 nas telas:** 3 de 3 idênticas **antes e depois** do lote: `tra_estatdia002` e `ass_rreqtotais002` dão HTTP
  500 nos dois, porque o jpgraph não desenha nem no 7.4 (defeitos abaixo). O que muda é onde o 8.5 para: antes, na
  declaração das classes; agora, no mesmo ponto do 7.4.
- Numa cópia de teste do jpgraph de `libs/` (fora do repositório, igual nos dois runtimes) com os defeitos de
  carregamento do 7.4 contornados, a imagem de erro do jpgraph sai com **os mesmos pixels no 7.4 e no 8.5** (antes, o
  8.5 não gerava imagem), e linha e pizza 3D param no mesmo erro nos dois.

Defeitos encontrados, todos já no 7.4 (registrados, não corrigidos):

| Onde | O quê | Efeito no 7.4 |
|---|---|---|
| `libs/jpgraph/jpgraph_plotmark.inc:63`, incluído no fim de `libs/jpgraph/jpgraph.php` | `=& new` | erro de sintaxe: nenhum gráfico de `libs/` é desenhado |
| `libs/jpgraph/jpgraph.php:3225` e `:7064`, `jpgraph_line.php:38`, `jpgraph_pie.php:595` e `:763` (e o mesmo em `jpgraph_bar`, `_canvas`, `_error`, `_log`) | construtor da mãe chamado pelo nome antigo depois de virar `__construct` | `Call to undefined method` |
| `libs/jpgraph/jpgraph.php:2623` e `:4380` | `Text::GetTextHeight()` não existe; `Ticks::__construct()` chamado sem o argumento | erro fatal |
| `libs/jpgraph/jpgraph.php:632` | `GenImgName()` lê `$HTTP_SERVER_VARS` (removida no PHP 5.4) | nome de arquivo `'auto'` sempre vira imagem de erro |
| `dbagata/classes/jpgraph/gd_image.inc.php:2016` | `RotImage` chama `$this->Image()`, que virou `__construct` | `new Graph()` morre: nenhum gráfico do Agata |
| `dbagata/classes/jpgraph/jpgraph_errhandler.inc.php:192` | chama `adie()`, que não existe | erro fatal quando o erro do jpgraph sai em texto |
| `dbagata/classes/jpgraph/jpgraph.php:193` | `CheckPHPVersion()` usa `explode()` com expressão regular | aviso (no 8.5, `Warning`) |

Diferenças do 8.5 que ficam para os próximos lotes. Hoje não aparecem, porque o 7.4 falha antes:
- **Construtores estilo PHP 4 no jpgraph** (24 no jpgraph do Agata, como `Text`, `GraphTabTitle` e `RotImage`, e
  `PlotMark` em `libs/`). No 8.5 deixam de ser construtores (lote 4). É por isso que, no 8.5, o gráfico do Agata não
  para em `RotImage::Image()` e estoura a memória ao desenhar.
- **`imagefilledarc()` com a cor em texto** (`libs/jpgraph/jpgraph.php:6483`): `TypeError` no 8.5, aviso no 7.4.
- **Assinaturas incompatíveis em módulos que nenhuma tela carrega.** No Agata são 27: `BoxPlot::ModBox`,
  `DateScale::AutoScale`, `GanttGraph::Add`/`SetScale`, `LogScale::AutoScale`, `OdoGraph::Add`, `OdoNeedle::Stroke`,
  `PieGraph::Add`, `PiePlotC::StrokeLabel`, `PolarAxis::Stroke`, `PolarGraph::SetScale`, `StockPlot::Stroke`,
  `TextPropertyBelow::GetColWidth`, mais 7 de `Radar*` e 7 de `Spider*`. Os módulos equivalentes de `libs/` não
  foram medidos, porque o carregamento para no `plotmark`.

## 5. Lote 3 — funções centrais que mudaram de resultado (20/11/2026)

Três commits manuais, só nas linhas indicadas:

| Categoria | Onde | Forma |
|---|---|---|
| `is_resource()`/`gettype() == "resource"` sobre resultado ou conexão do PostgreSQL (no 8.5 são objetos: o teste dá falso sem aviso) | `db_funcoes.php`: `db_multiploselect` (416, 475), `db_selectrecord` (859), `db_selectmultiple` (927, 937, 984); `db_stdlib.php:2911` (`db_logsmanual_demais`); `db_libconsole.php:83, 172`; `db_stdlibwebseller.php:4389`; `db_libcontabilidade.php:3678` | o teste do 7.4 `\|\| $x instanceof \PgSql\Result` (ou `Connection`); no 7.4 a classe não existe e o `instanceof` é sempre falso |
| `pg_*` sobre consulta que falhou (decisão 2a) | `db_funcoes.php:1342` (`ultimo_dia_mes`), `db_stdlibwebseller.php:437` (`eduparametros`), `db_libcontabilidade.php:4636` | `($rs ? pg_x($rs) : null)` |
| `pg_query()` sem conexão aberta: aviso e `false` no 7.4, `Error` no 8.x | `db_stdlib.php:100` (`db_query`) | `try`/`catch` só do `Error` dessa situação, que vira `false` |
| `date()` com texto | `db_stdlib.php:1651` (`db_vencimento`) | `false` para texto sem número, `(int)` nos demais (o 7.4 usa o número do começo do texto e trata `null` como 0; o 8.5 usava a hora atual) |
| número × texto não numérico (`"" == 0` era verdadeiro) | `db_funcoes.php`: `db_select` (1055, 1071), `db_selectrecord` (761, 861), `db_selectmultiple` (966), `db_ancora` e `db_inputdata` (`$db_opcao < 3`) | forma do precedente do Tributário: compara com `(float)` do texto quando um lado é número e o outro texto não numérico |
| `!= ""` com o valor 0 | `db_funcoes.php:822` | `($x != "" && $x !== 0 && $x !== 0.0)` |
| lista nula no `db_select` (`reset`/`sizeof` de `null`: aviso no 7.4, `TypeError` no 8) | `db_funcoes.php:1051, 1069` | pula o `reset` e conta 0 quando a lista é `null` |

Prova:
- `php -l` nos dois runtimes nos 5 arquivos.
- Cada forma caracterizada numa grade de valores (original no 7.4 = nova no 7.4 = nova no 8.5). As funções chamadas
  direto com resultado real do banco, em 42 casos, dão o mesmo resultado nos três. Sem o lote, 13 deles diferiam no
  8.5. Exemplos: com a variável vazia, o `db_select` deixava de marcar a opção 0; o `db_selectrecord` somente leitura
  perdia a descrição; o `db_multiploselect` saía vazio.
- `db_libconsole`: o `db_query` do 8.5 recusava a conexão válida e o script morria. `db_logsmanual_demais`: o 8.5 não
  gravava o log de acesso; agora grava como o 7.4 (medido numa transação desfeita, sem gravar nada).
- **7.4 inalterado:** 210 telas sorteadas entre as da bateria, antes e depois: 206 iguais byte a byte; as 4 restantes
  diferem só na hora atual (um campo de hora e 3 PDFs com o texto idêntico, que mudam sozinhos entre capturas).
- **8.5:** bateria 7.4 × 8.5 nas 4.324 telas que chamam essas funções, direto ou pelo formulário que incluem:
  **253 → 167 divergentes, 86 resolvidas, nenhuma nova**.

O que as 167 mostram agora:
- **Formulários das áreas** (cerca de 30 telas): `label()` sobre nulo, porque o construtor estilo PHP 4 da classe de
  dados não roda.
- **`pg_*` sobre consulta que falhou na própria tela** (decisão 2a, trabalho das áreas).
- **Assinaturas de `RelatoriosLegaisBase`**, do Financeiro.
- **Núcleo, ainda pendente:** `db_stdlibwebseller.php:479` e `libs/db_conecta.php:284` (`pg_*` sobre consulta que
  falhou), `dbforms/db_classesgenericas.php:756` (`reset` de `null`), `libs/db_app.utils.php:39` (constante
  `DB_VERSION`) e `model/dbGeradorRelatorio.model.php:602` (`$s{i}`).

Fica para decisão do grupo, sem correção: no 8, dois textos numéricos com espaço no fim (`"1" == "1 "`) passaram a
ser comparados como número (verdadeiro); no 7.4 o `"1 "` não era numérico e a comparação era de texto (falso). A
mudança vale para todo `==` do sistema, e as colunas `char(n)` completadas com espaço são o caso real.

## 6. Lote 3b — pendências expostas pelo lote 3 (20/11/2026)

| Onde | Problema no 8.5 | Forma |
|---|---|---|
| `model/cda.model.php:1276`, `model/dbGeradorRelatorio.model.php:602, 1235` | `$s{i}`: não compila | Rector, commit só dele (como no lote 1) |
| `libs/db_stdlibwebseller.php:479` (`VerParametroNota`) | `pg_num_rows` sobre consulta que falhou | `($rs ? pg_num_rows($rs) : null)` (decisão 2a) |
| `libs/db_conecta.php:284` (pid para o `application_name`) | `pg_fetch_result` sobre consulta que falhou | o mesmo, com o resultado guardado em `$rsPidConexao` |
| `dbforms/db_classesgenericas.php:756–894` (abas) | `reset`/`sizeof`/`key` de lista `null`: aviso no 7.4, `TypeError` no 8 | pula o `reset`, conta 0 e devolve `null` como chave quando a lista é `null` |
| `libs/db_app.utils.php:39–42` (`db_app::load`) | `DB_VERSION` não definida: no 7.4 virava o texto `"DB_VERSION"`; no 8, `Error` | `(defined("DB_VERSION") ? DB_VERSION : "DB_VERSION")` |

Prova:
- `php -l` nos dois runtimes nos 6 arquivos.
- Cada forma caracterizada nos dois runtimes (original no 7.4 = nova no 7.4 = nova no 8.5).
- **7.4 inalterado:** 216 telas (a amostra do lote 3 mais as 6 telas-alvo de fora dela) com a mesma resposta antes e
  depois; as 4 que diferem são as mesmas do lote 3, só na hora atual (texto dos PDFs idêntico).
- **8.5:** bateria nas 4.330 telas (as do lote 3 mais as 6): **173 → 161 divergentes, 12 resolvidas, nenhuma nova**.

Fora do lote:
- `model/contabilidade/arquivos/siai/v2021/SiaiArquivoPPAXML.model.php` não compila nem no 7.4 (literal numérico
  inválido na linha 202). Fica registrado.
- Das telas-alvo, 3 do Tributário ainda divergem, agora pelo código da própria área: `div2_certtermo_002.php:89`
  (`pg_num_rows` sobre consulta que falhou) e `fis2_fis_autolote002`/`fis2_fis_notlanclote002`
  (`classes/db_fis_parfiscal_classe.php:893`, `pg_*` sem conexão aberta).

## 7. Lote 4 — construtores estilo PHP 4 (20/11/2026)

No 8.x, o método com o nome da classe deixou de ser construtor: o objeto nasce sem o estado que o construtor monta.
Foram levantadas por análise de tokens as classes sem namespace que têm o método com o nome da classe e nenhum
`__construct`, ou seja, as que o 7.4 de fato usa como construtor. São **153**: 144 em `dbagata/classes` (jpgraph 49,
util 58, phpdocwriter 12, core 6, barcode128 2, reports 2, fpdf151 1), 7 em `libs/jpgraph` (`ImgData_*`, `PlotMark`),
`PostgreSQLUtils` (`libs/db_libpostgres.php`) e `db_impcarne` (`fpdf151/impcarneGuiaQuitacaoItbi.php`).

Um commit manual, 108 arquivos:
- **Declarações:** só a linha da declaração muda, de `function X(` para `function __construct(`, nas 153.
- **Chamadas pelo nome antigo:** as 29 chamadas ao construtor da mãe que o 7.4 executa (`parent::X(`, `$this->X(`,
  `X::X(`) viram `parent::__construct(`. Em cada uma foi conferido que `X` é a mãe direta.
- **Chamadas já quebradas, deixadas como estão:** as que apontam para classes que o PR #8 já tinha convertido para
  `__construct` já falham no 7.4. São 13 no jpgraph de `libs/` e `div2_inicial_cda_002.php:161`.

Prova:
- `php -l` nos dois runtimes: os mesmos erros de antes. Já falhavam no 7.4 `util/FileBox.class`,
  `util/GtkPopDate.class` e `libs/jpgraph/jpgraph_plotmark.inc`; só no 8.5, `jpgraph_gantt` e `jpgraph_pie` do
  Agata (assinaturas, seção 4).
- Objetos criados direto, com o código original e o novo: o 7.4 dá o mesmo estado nos dois. Com o lote, o 8.5 dá o
  mesmo estado do 7.4 em 32 de 34 classes; sem o lote, quase todos nasciam vazios. Os 2 restantes não vêm deste lote:
  - `ScatterPlot`: `count(false)` no construtor, que já era `__construct`. É aviso no 7.4 e `TypeError` no 8; fica para
    o lote 5.
  - `Grid`: efeito do teste, que passou `null` literal num parâmetro por referência.
- **7.4 inalterado** nas 210 telas que carregam essas classes (Agata, barcode128, carnê do ITBI, `PostgreSQLUtils`): as
  diferenças são só a hora atual. Num campo de hora e numa ata, a hora muda entre capturas; nos PDFs, o texto é idêntico.
- **8.5:** bateria nas mesmas 210 telas, com **74 → 44 divergentes, 30 resolvidas** (relatórios do Agata) e **nenhuma
  nova**.

Achado durante a prova: a primeira versão tratava cada subpasta do `dbagata` como uma biblioteca separada e
classificou como "já quebrada" a chamada `FPDF::FPDF()` de `reports/MyPdf.class`. Ela usa o `FPDF` de `fpdf151/`,
que estava sendo renomeado. Por isso a comparação do 7.4 antes e depois acusou os relatórios do Agata respondendo
com a página de erro. A classificação foi corrigida para tratar o `dbagata` inteiro como uma biblioteca, o lote foi
reaplicado do zero e a bateria foi refeita; os números acima são da bateria refeita.
