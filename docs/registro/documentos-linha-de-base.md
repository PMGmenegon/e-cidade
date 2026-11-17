# Documentos emitidos (PDF, planilha, Word, QR, código de barras): inventário e linha de base

Preparação para a atualização das bibliotecas de documento. Medido em 13/11/2026, sobre `laravel/integracao` (`132fd39da`), com o `vendor/` atual
(o mesmo nos dois runtimes): PHP 5.6 (referência) × PHP 8.5.12. Nada foi trocado nem corrigido: é a fotografia de **hoje**,
para saber o que muda quando as bibliotecas forem atualizadas.

Ferramentas (todas em `ecidade/tests/sistema/documentos/`):

| Arquivo | Faz |
|---|---|
| `inventario.py` | varre o código e conta quem usa cada biblioteca (direto e até 2 níveis); gera a tabela 1 |
| `triagem.py` | triagem por leitura de código dos emissores (padrões de escrita), antes de rodar qualquer um |
| `documentos.py` | `captura` (pede o documento aos dois runtimes, com o vigia em volta de cada pedido), `compara` (5.6 × 8.5) e `confere` (repetição × linha de base) |
| `casos.tsv` | os 14 casos: nome, biblioteca, caminho (HTTP ou `cli:` para dublê) e, se houver, a divergência conhecida |
| `dubles/*.php` | cinco scripts CLI que exercitam a biblioteca com as classes do sistema onde a base de exemplo não tem dados |
| `base/*.txt` | a linha de base: descrição estrutural normalizada de cada caso, nos dois runtimes (28 arquivos) |

## 1. Inventário: biblioteca → versão → uso → telas de exemplo

Versões: `ecidade/composer.lock` (e `fpdf151/fpdf.php`, `dbagata/VERSION`). "Diretos": arquivos `.php` (fora de `vendor/`, `tmp/` e
migrations) que contêm o padrão da biblioteca. "Telas da raiz": arquivos da raiz de `ecidade/` que chegam a um deles por
`include`/`require` ou por referência a classe, **até 2 níveis** (a partir daí o casamento por nome de classe vira ruído: com
profundidade ilimitada 15 mil arquivos "usavam" a mesma biblioteca; nós com mais de 300 consumidores, como `libs/db_stdlib.php`,
não valem como ponte). Os números de "telas" são, portanto, **cota superior**. "Menu": entre elas, as que estão em
`db_itensmenu.funcao` (5.744 telas; `SELECT DISTINCT trim(funcao) FROM db_itensmenu`, só leitura).

| Biblioteca | Versão | Diretos | Telas da raiz (≤2 níveis) | Menu | 3 telas de exemplo |
|---|---|---|---|---|---|
| FPDF (`fpdf151/`, `db_conectapdf`) | 1.51 (código local) | 1.680 | 2.038 | 137 | `iss2_classes002.php`, `orc2_programatrabalho002.php`, `con2_razaocontas002.php` (formato PDF) |
| dbagata (relatórios Agata, `cl_dbagata`) | local (`dbagata/`) | 73 | 82 | 0 | `orc2_relitens002.php`, `orc2_relplanos002.php`, `orc2_relconcedentes002.php` |
| mPDF | 7.1.9 | 3 | 3 | 1 | `pro4_protprocessovolume.php`, `agu3_conscadastro_impressao.php`, `db_download_todos_arquivos_visualizador.php` (também por Pimaco) |
| Dompdf | 0.8.3 | 2 | 3 | 0 | `con2_importacaopcasp002.php`, `src/Tributario/Grm/WebService/BoletoGrm.php` (web service), PCASP `Importacao.php` |
| FPDI | 1.6.2 | 0 | 0 | 0 | instalado e sem uso: a classe `FPDI` não aparece no código |
| PhpSpreadsheet | 1.8.2 | 25 | 6 | 0 | `con2_razaocontas002.php` (formato xlsx), `con2_emissaoanexoXII002.php`, `arr2_extratocontribuinte002.php` |
| PHPExcel | **não instalado** | 2 | 1 | 0 | `pes4_geracaoarquivorefeisul.RPC.php` (fatal nos dois runtimes: a classe não existe no `vendor/`) |
| PhpWord | 0.17.0 | 10 | 17 | 0 | `lic4_geracaoatas002.php`, `lic1_pcorcamtroca001.php`, `agu1_aguacontrato.RPC.php` |
| Pimaco (etiquetas Patrimônio; usa mPDF e picqer 0.2.2) | proner/phppimaco 1.3.0 | 6 | 0 | 0 | `EtiquetasPimacoPDF`, `EtiquetaModelo01Builder`, `EmitirEtiquetasService` (acionados pelo controller `/v4`, não por tela da raiz) |
| QR (aferrandini/phpqrcode 1.0.1) | 1.0.1 | 6 | 0 | 0 | `fpdf151/impmodelos/mod_imprime6.php`, `mod_imprime16.php`, `mod_imprime109.php` (carregados por `include` dinâmico `mod_imprime$N`) |
| Código de barras (`FPDF::int25`, `db_barras`) | local | 79 | 568 | 10 | `bib2_etiquetas002.php`, `cai4_recibo003.php`, `cai3_gerfinanc003.php` |
| Planilha/Excel por cabeçalho HTTP (HTML ou CSV servido como `.xls`) | — | 6 | 22 | 1 | `pla2_planejamento_previsao_rcl001.php`, `pla2_anexos_ldo001.php`, `con2_demonstrativoevolucaodespesa_001.php` |
| Word por cabeçalho HTTP (HTML servido como `.doc`) | — | 9 | 326 | 94 | `emp4_empageconflay001.php`, `pre1_leis001.php`, `orc2_suplementacaoprojeto002.php` |

Observações que mudam a leitura da tabela:

- **O emissor quase nunca está no menu.** A tela de menu é o formulário (`...001.php`); o documento sai de um segundo pedido
  (`...002.php`, aberto por JavaScript com os filtros). Por isso "Menu" é pequeno onde "Telas da raiz" é grande.
- **"Planilha por cabeçalho" e "Word por cabeçalho" têm contagem inflada**: passam por `db_download.php` e `FileEstorage`, que
  servem qualquer arquivo. Os usos diretos de verdade estão nos exemplos.
- **QR e código de barras dos modelos de impressão** (`impmodelos/mod_imprime*`) são carregados por nome calculado; o varredor
  estático não os liga às telas. Quem emite é a família `fpdf151/impcarne.php`/`pdf1.php`.
- `endroid/qr-code 2.5.1`, `bacon/bacon-qr-code 1.0.3`, `khanamiryan/qrcode-detector-decoder`, `picqer 0.2.2` (só via Pimaco) e
  `nfephp-org/sped-common` estão no `composer.lock`; a única biblioteca de QR **usada** no código é a `aferrandini/phpqrcode`.
- Gráficos (`jpgraph`, 59 arquivos) são imagem, não documento: tratados à parte.

## 2. Triagem por leitura de código (feita antes de rodar cada emissor)

Em container `SOMENTE_LEITURA=1` a maioria dos emissores nem chega a gerar o documento: `fpdf151/pdf.php` inclui
`libs/db_usuariosonline.php`, que faz INSERT (1ª vez) ou UPDATE no registro de usuário online
(`Erro:(27) inserindo arquivo em db_usuariosonline: ... transação de leitura-apenas`). Medido: 75 de 80 emissores FPDF sorteados.
Rodar em container que grava só vale **depois de triagem**. A triagem (`triagem.py` + leitura) olha o emissor, o que ele
inclui (exceto `libs/`, `dbforms/` e `classes/db_*_classe.php`, que só **definem** `incluir/alterar/excluir`) e o `.agt` do Agata,
procurando INSERT/UPDATE/DELETE, `->incluir/alterar/excluir`, transação, `db_acount*`, `pg_lo_*`, `orcparamseqfiltropadrao`.

| Emissor | Resultado | Motivo |
|---|---|---|
| `iss2_classes002.php`, `iss2_tiponotas002.php` | rodou | sem achado; só `SELECT` |
| `orc2_programatrabalho002.php` | rodou | sem achado |
| `com2_certidaopenalidadeindividual002.php` | rodou | só a *definição* de `db_inicio_transacao` em `db_funcoes.php`; sem chamada |
| `con2_razaocontas002.php` (PDF e xlsx) | rodou | sem achado; `RelatorioRazaoPorConta` só lê |
| `orc2_relitens002.php`, `orc2_relplanos002.php`, `orc2_relconcedentes002.php` | rodou | sem achado no PHP nem no `.agt` |
| `emp4_empageconflay003.php` | **descartado** | `incluir` em `empagegera`/`empageconfgera`, `alterar` em `empagetipo`, transação |
| `con2_emissaoanexoXII002.php` | **descartado** | `model/relatorioContabil.model.php:506,511` faz `incluir/alterar` de linhas do relatório (configuração do relatório) |
| `pre1_leis001.php` | **descartado** | INSERT/UPDATE/DELETE em `db_leis` (upload) |
| `pat1_bensnovo.RPC.php` | **descartado** | RPC de cadastro de bens, 16 achados de transação/escrita |
| `lic4_geracaoatas002.php` | **descartado** | transação + `pg_lo_*` + `documentoTemplate`; e a base não tem ata (`liclicitaata` vazia) |
| `orc2_suplementacaoprojeto002.php` | **descartado** | transação no `documentoTemplate`; e `orcsuplem` vazia |
| `pro4_protprocessovolume.php` | lacuna | o GET só mostra o formulário; o mPDF é acionado pelo POST que cria o volume (grava) |
| `agu3_conscadastro_impressao.php`, `arr2_extratocontribuinte002.php` | lacuna | sem dados na base (`aguabase`, `arrecad` vazias) |
| `pes4_geracaoarquivorefeisul.RPC.php` | lacuna | classe `PHPExcel` inexistente nos dois runtimes (não está no `composer.lock`) |

## 3. Linha de base (14 casos, 5.6 × 8.5)

Cada pedido foi feito aos dois containers (porta 8130 = 5.6, 8131 = 8.5), com a sessão do login restaurada antes de cada um
(`sessao.sh`, em `ecidade/tests/sistema/relatorios-kernel/`), e **o vigia do banco antes/depois de cada pedido** (28 pedidos por rodada). Descrição
estrutural (`documentos.py`): para PDF, nº de páginas, tamanho, texto extraído (`pdftotext -layout`), nº e hash das imagens e hash do
conteúdo de cada página (vetores, inclusive as barras); para xlsx, abas, dimensões e células; para docx, arquivos e texto.
Normalizados: horas `HH:MM:SS`, `Data:`/`DATA EMISSÃO:`, nome de arquivo temporário. O tamanho em bytes é gravado mas não comparado.

| Caso | Biblioteca | Origem | Resultado nos dois runtimes |
|---|---|---|---|
| `fpdf_classes` | FPDF 1.51 | `iss2_classes002.php?opcaoOrdem=alfabetica` | PDF 1 pág., 10 classes, logo; **igual** |
| `fpdf_tiponotas` | FPDF 1.51 | `iss2_tiponotas002.php?opcaoOrdem=numerica` | PDF 1 pág., 7 tipos; **igual** |
| `fpdf_programatrabalho` | FPDF 1.51 | `orc2_programatrabalho002.php` | PDF 1 pág.; **igual** |
| `pdfdoc_penalidade` | FPDF (PDFDocument) | `com2_certidaopenalidadeindividual002.php` | PDF 1 pág. (sem penalidades); **igual** |
| `razao_pdf` | FPDF (PDFDocument) | `con2_razaocontas002.php`, `tiporelatorio=1` | PDF 1 pág.; **igual** |
| `agata_relitens` / `agata_relplanos` / `agata_relconcedentes` | dbagata | `orc2_rel{itens,planos,concedentes}002.php` | 3 PDFs de 1 pág. (cabeçalho, sem linhas: tabelas vazias); **iguais** |
| `razao_xlsx` | PhpSpreadsheet 1.8.2 | `con2_razaocontas002.php`, `tiporelatorio=2` | xlsx, aba `Worksheet` A1:Q1 (só o cabeçalho; sem lançamentos); **igual** |
| `barras_qr` | `FPDF::int25` + aferrandini/phpqrcode | dublê `gera_barras_qr.php` | PDF 2 pág., 3 códigos 2 de 5 e QR 1 imagem; **PDF byte a byte idêntico** (47.505 B) |
| `phpword_docx` | PhpWord 0.17.0 | dublê `gera_phpword.php` | docx (texto, tabela 3×2, quebra de página); **igual** |
| `planilhas_leitura` | PhpSpreadsheet (leitura) + `fgetcsv` | dublê `le_planilhas.php` | 21 modelos `config/templates/IN22/*.xlsx` e 2 CSV; conteúdo **igual**, mas só o 8.5 emite Warning (ver 4) |
| `pimaco_mpdf` | Pimaco + mPDF 7.1.9 + picqer | dublê `gera_pimaco.php` (classes reais do Patrimônio) | 5.6: PDF 1 pág., 8 imagens (4 códigos de barras e uma imagem fixa repetida 4 vezes); **8.5: não roda** (ver 4) |
| `dompdf_pdf` | Dompdf 0.8.3 | dublê `gera_dompdf.php` | 5.6: PDF 1 pág.; **8.5: não roda** (ver 4) |

Repetição (critério "como verificar"): uma segunda captura completa, depois de reiniciar o ciclo, deu **28/28 iguais à linha de
base** (`documentos.py confere`). Os documentos reais têm pouco conteúdo porque a base de exemplo é pequena: classes (10),
tipos de nota (7), programas (4), CGM (3); empenhos, bens, débitos, biblioteca e processos estão vazios ou quase.

Os dublês existem para o que a base não alimenta: usam as classes do sistema (`EtiquetaModelo01/02Builder`,
`EtiquetasPimacoPDF`, `FPDF::int25`, `\PHPQRCode\QRcode::png`, `PhpWord`, `Dompdf`, `IOFactory`) com dados inventados, por CLI, **sem
HTTP e sem banco**. Não substituem a emissão real do carnê/recibo/etiqueta com dados: ficam como lacuna para a base de
uma prefeitura.

## 4. Divergências 5.6 × 8.5 de hoje (caracterizadas)

Todas são do `vendor/` atual rodando no PHP 8.5 — é exatamente o que a atualização de bibliotecas precisa tratar.
Não são defeito do código do sistema nem herdadas do legado.

| Caso | 5.6 | 8.5 | Causa |
|---|---|---|---|
| `pimaco_mpdf` | gera | `Parse error: syntax error, unexpected token "{" in vendor/mpdf/mpdf/src/Mpdf.php on line 2238` | mPDF 7.1.9 não compila no PHP 8.5; derruba também toda etiqueta Pimaco |
| `dompdf_pdf` | gera | `Dompdf\Exception: file_get_contents(): Passing null to parameter #2 ($use_include_path) of type bool is deprecated` (`Helpers.php:507`) | Dompdf 0.8.3 transforma o Deprecated do 8.5 em exceção; derruba `BoletoGrm` e a importação PCASP |
| `planilhas_leitura` | sem avisos | `Warning: Trying to access array offset on null` em `phpspreadsheet/.../Reader/Xlsx/Styles.php:133-134` | PhpSpreadsheet 1.8.2; o conteúdo lido é idêntico |

`documentos.py compara` imprime essas três como `DIVERGE (conhecida)` (coluna 4 do `casos.tsv`) e sai 0; se uma passar a ser
igual (biblioteca atualizada), imprime `AGORA IGUAL` e sai 1, para atualizar a linha de base.

## 5. Vigia do banco

Duas rodadas completas (56 pedidos): **56 `OK: so tabelas permitidas`**. Tabelas que mudaram, e só elas:
`configuracoes.db_usuariosonline` (1 linha por pedido de tela) e `configuracoes.db_logsacessa_202611_0` (log de acesso).
Nenhum `db_acount*`, nenhuma tabela de configuração. Nenhum alerta; nada foi limpo. Os pedidos dos dublês não tocam o banco.

## 6. Importação de planilha (critério 3)

Telas que importam planilha/arquivo: `con1_importartransacao002.php`, `con4_ajustecontratos001.php`,
`con4_importacaosaldoinicialMSC.RPC.php`, `con4_importatransacoes.RPC.php`, `con2_importacaopcasp002.php`/`con1_importacaopcasp.RPC.php`
(PCASP, usa Dompdf/PhpWord), `con1_ementarioreceita.RPC.php`, `pes2_importaatestados003.php`, `model/material/PlanilhaDistribuicao.model.php`
e `src/File/Csv/LerCsv.php` (`fgetcsv`). **Todas gravam no banco** ao importar: ficam como lacuna, sem rodar.

Arquivos de exemplo que existem no repositório e foram lidos nos dois runtimes (`le_planilhas.php`, caso `planilhas_leitura`):
21 modelos `config/templates/IN22/*.xlsx` (modelos TCE-RO, lidos por `src/Library/SpreadSheet/Template/Parser.php`) e os CSV
`config/financeiro/siconfi/recursos/recurso_2018.csv`/`recurso_2019.csv`. Resultado: abas, dimensões, nº de células e hash dos
valores **iguais** nos dois; os dois CSV têm **0 bytes**; além disso `TipoRecursos::getCodigoParaAno()` faz `foreach` sobre a string de `file_get_contents()` (defeito já existente, igual nos dois). Não há arquivo de exemplo para as demais importações.

## 7. Lacunas (não cobertas)

- Carnê, recibo, boleto, certidão e etiqueta de biblioteca com dados reais (barras e QR dos `impmodelos`): a base não tem débitos,
  recibos, empenhos, exemplares; coberto só pelo dublê (3).
- Word/Excel "por cabeçalho" (`emp4_empageconflay001`, `pre1_leis001`, `pla2_*`): ou gravam (descartados), ou exigem dados que não há.
- PhpWord com modelo de documento (ata, edital, minuta, contrato de água, ITBI): modelo vem de *large object* do banco e as telas gravam.
- Importações de planilha (6).
- A comparação é estrutural (texto, páginas, hash dos vetores e das imagens); não compara rasterização nem fontes embutidas.

## 8. Como repetir

Pré-requisitos: dois containers sobre a mesma árvore `ecidade/` e o mesmo banco, PHP 5.6 (porta P) e PHP 8.5 (porta P+1); uma sessão
autenticada (arquivo de sessão PHP + arquivo `.sid` ao lado, como cria `sessao.sh` em `ecidade/tests/sistema/relatorios-kernel/`);
e, para rodar em container que grava, um script de vigia do banco que aceite `antes <foto>` e `depois <foto>`, compare
`pg_stat_user_tables` e saia 0 (só `db_logsacessa*`, `db_usuariosonline`, tokens OAuth mudaram) ou 3 (outra tabela mudou).
Requer no host `pdftotext`, `pdfinfo`, `pdfimages`, `python3` com `pypdf` e `openpyxl`.

```bash
# containers nomeados ecidade_doc_56 / ecidade_doc_85 nas portas 8130 / 8131 (ou passe --c56 --p56 --c85 --p85)
export VIGIA=<script do vigia do banco>
# 1. captura com o vigia em volta de cada pedido (rc 3 = escrita fora do permitido: parar e investigar, nada e limpo)
python3 ecidade/tests/sistema/documentos/documentos.py captura --sessao /tmp/sessao.dat --saida /tmp/docs --vigia
# 2. 5.6 x 8.5 e repeticao x linha de base guardada
python3 ecidade/tests/sistema/documentos/documentos.py compara --dir /tmp/docs
python3 ecidade/tests/sistema/documentos/documentos.py confere --dir /tmp/docs --base ecidade/tests/sistema/documentos/base
# 3. inventario (opcional: --menu com a lista de db_itensmenu.funcao)
python3 ecidade/tests/sistema/documentos/inventario.py --menu /tmp/menu.txt --json /tmp/inv.json
```
