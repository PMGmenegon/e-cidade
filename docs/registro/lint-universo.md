
## Depois — porte residual das bibliotecas (T-021, 12/11/2026)

10 dos 27 "só 8.5": `php -l` limpo no 5.6 **e** no 8.5 em todos. Conteúdo trocado só onde o 8 não aceita; ISO-8859-1 preservado
(os 4 `mod_imprime*` são ISO-8859; edição por byte). Nenhum tem cópia em `extension/modification/`. T-004 (Rector) não tinha
resultado e T-017 não tinha cobertura de branch quando foi feito: nenhum arquivo está em outra branch (conferência do PO, 12/11/2026).

| Arquivo | Classe | O que foi feito | Por que reproduz o 5.6 |
|---|---|---|---|
| `ext/php/Michelf/Markdown.php`, `MarkdownExtra.php` | manual (mecânico) | `$s{i}` → `$s[i]` (5 + 16 trocas), por `scratchpad/chaves_offset.php` (tokenizador, só troca `{`/`}` de deslocamento) | deslocamento de string com `{}` e com `[]` é a mesma operação no 5.6 |
| `fpdf151/impmodelos/mod_imprime10, 12, 13, 1333.php` | manual (mecânico) | idem, 1 linha cada (`$sObsItem{$iInd}`, `$descricaoitem{$iInd}`, `$resumo{$iInd}` ×2), laço limitado por `strlen()` | idem |
| `securimage/securimage.php`, `WavFile.php` | manual (mecânico) | idem (1 + 2 trocas) | idem |
| `libs/jpgraph/jpgraph_pie.php` | manual | `PiePlotC::Stroke(&$img,…)` e `PieGraph::Add(&$aObj)` (o pai manda na referência); construtores PHP 4 → `__construct`, `parent::PiePlot()` e `$this->Graph()` → `parent::__construct()` | ver abaixo |
| `libs/jpgraph/jpgraph_radar.php` | manual | `= & new` → `= new` (6); construtores PHP 4 → `__construct`, `parent::Axis()`/`$this->Graph()` → `parent::__construct()`; parâmetros extras tornados opcionais (`Stroke` ×4, `SetTickLabels`, `SetScale`, `SetTickDensity`, `GetPlotsYMinMax`) | ver abaixo |

**jpgraph: o 5.6 de hoje já estava quebrado nestes dois arquivos.** A porta anterior (`7591c88a6`) renomeou o construtor
`Graph()` para `__construct()` em `libs/jpgraph/jpgraph.php` (e `Axis`, `Ticks`…), mas `jpgraph_pie.php` e `jpgraph_radar.php`
não compilavam no 8.5 e ficaram de fora do Rector. Resultado medido antes da correção, **no 5.6**: `new PieGraph()` →
`Call to undefined method PieGraph::Graph()`. Com o porte completo dos dois arquivos o 5.6 volta ao comportamento da biblioteca
original (gráfico renderiza) e o 8.5 faz o mesmo — é a regra "o pai manda" do `catalogo-e-metodo.md` (LSP) e o conserto dos
construtores PHP 4 já aplicado ao resto da biblioteca; construtor vazio no filho (`RadarGrid() {}`) continua sombreando o do pai
(por isso converter, e não apagar). Os parâmetros extras tornados opcionais só relaxam a assinatura (o corpo continua o mesmo).

### Verificação (T-021)

`scratchpad/bateria_t021.php` (sem banco), rodada nos dois runtimes sobre a mesma árvore:

| Item | 5.6 | 8.5 |
|---|---|---|
| Michelf `Markdown` / `MarkdownExtra` (HTML de um texto com títulos, listas, código, tabela, notas) | md5 igual | md5 igual |
| jpgraph `RadarGraph` (PNG 300×250) | md5 dos pixels `830986be…` | idêntico |
| jpgraph `PiePlotC` (PNG 300×250) | renderiza | **diverge**: `TypeError imagefilledarc(): Argument #8 ($color) must be of type int, string given` em `libs/jpgraph/jpgraph.php:6484` (`CakeSlice` passa `$this->current_color_name`, um nome) |
| `WavFile` ramo "replace" (`_samples[…]`) | md5 igual | md5 igual |
| `securimage` carrega e instancia; áudio do captcha (`getAudibleCode`, ramo `['display'][$i]`) | `WavFileException: Sample rate … does not match` | **mesma exceção** (falha igual: áudio de ruído do repositório; pré-existente) |
| captcha da tela de login (`carregaCaptcha.php`) | PNG 215×80 | PNG 215×80 |

- **Divergência que sobra (fora do escopo desta tarefa):** `libs/jpgraph/jpgraph.php:6484` — o PHP 8 não aceita nome de cor onde
  espera inteiro. Fica para tarefa própria (é arquivo fora da lista; a spec proíbe tocar). Nenhuma tela chama `jpgraph_pie`
  (grep: só o `dbagata/classes/jpgraph`, outra cópia).
- **Lacuna — `impmodelos`:** `mod_imprime12` (`emp2_anulemp002.php`) e `mod_imprime1333` (`lic2_planilhavalores002.php`) são
  alcançados por relatório, mas `empanulado`, `empempenho` e `liclicita` estão **vazias** na base de exemplo — o relatório não chega ao
  `include`; popular exigiria gravar no banco (proibido). `mod_imprime10`/`13` só têm chamador comentado (`com2_*`). A troca é
  uma linha por arquivo, em laço limitado por `strlen()`, sem diferença de semântica; fica sem comparação de PDF.
- **Michelf** não é incluído por nenhuma tela (só testado pela bateria). **securimage:** captcha da tela de login igual nos dois
  runtimes; bateria do login na árvore da T-013 (não integrada ainda) deve ser repetida depois da integração.

## Depois — T-019: cálculo de IPTU, ISSQN fixo e lote (4 arquivos, 12/11/2026)

Branch `1tributario/T-019-calculos-lote`, a partir de `laravel/integracao`. Conferência de branches (METODOLOGIA 4.1): nenhuma
branch local ou remota altera estes 4 arquivos (`git diff laravel/integracao...<branch>` em todas); a T-004 (Rector em simulação)
e a T-017 (inventário) ainda não tinham terminado, então a classe é "manual" pela natureza do defeito (nenhum é caso do Rector
do projeto). Não existem cópias em `extension/modification/`.

| Arquivo | Defeito no 8.5 | Classe | Correção (reproduz o 5.6) | `php -l` 5.6 / 8.5 |
|---|---|---|---|---|
| `calculoiptu.php:65` | `global $$matriz[$i];` — no PHP 7+ vira `${$matriz}[$i]` e não compila; no 5.6 é `${$matriz[$i]}` | manual | `global ${$matriz[$i]};` (mesma forma já usada em `libs/db_stdlib.php:874`). Medido: nos dois runtimes torna global a variável de nome `$matriz[$i]` | ok / ok |
| `calculoissqnfixo.php:130` | idem | manual | idem | ok / ok |
| `cad1_lote002.php:198, 213, 229` | `break` fora de laço/`switch` (3 pontos): erro de compilação no 8; no 5.6 é fatal **de execução** (`Cannot break/continue 1 level`) | manual | `exit;` (decisão do projeto, `area-tributario.md` "CORREÇÃO ao catálogo"): os 3 são caminhos de erro de `incluir()/excluir()` alcançáveis, e o 5.6 morre ali; `exit` também interrompe o script sem chegar a gravar mais nada. Os demais `break` do arquivo estão dentro de laços e não foram tocados | ok / ok |
| `cad1_lote003.php:196` | idem (1 ponto, depois de `db_msgbox("Impossível excluir…")`) | manual | `exit;` | ok / ok |

Diff: 4 arquivos, 6 linhas trocadas (ISO-8859-1 preservado; edição em bytes).

### Verificação

- `php -l` limpo no 5.6 e no 8.5 nos 4 arquivos (antes: os mesmos 4 falhavam no 8.5 — ver `lint-universo-falhas.txt` da T-003).
- Telas `cad1_lote001/002/003` (GET), 5.6 × 8.5, mesma sessão: **3/3 idênticas**. O 8.5 não as carregava antes (erro de compilação).
- `calculoiptu.php` e `calculoissqnfixo.php` **não são alcançáveis por tela**: são scripts de linha de comando que se conectam a uma base `simula` e
  executam SQL de cálculo (`fc_calculoiptu(...)` no IPTU; `create temporary table` e consultas no ISSQN fixo); nenhum `.php` do código os inclui (só migrations citam o nome). Executados nos dois runtimes param igual em
  `Call to undefined function modification()` (dependem de um bootstrap que a linha de comando não carrega), ou seja, **nem o 5.6 os executa hoje** — defeito pré-existente, fora da migração.
- **Lacunas (nada gravado, regra do cliente):** (1) o comportamento do cálculo em si (`fc_calculoiptu` na base `simula`, que não existe aqui) não foi exercitado; (2) os 4 `exit;`
  ficam em ramos de erro de gravação (POST de `incluir`/`excluir` de lote), que só se alcançam gravando no banco — a equivalência com o 5.6 se apoia na medição
  registrada em `area-tributario.md` (fatal de execução no 5.6) e no `php -l`.

### Reaberta em 13/11/2026: `$$matriz[$i]` em 22 pontos (achado do QA)

A correção acima só tratou o `global $$matriz[$i];` (que **não compila** no 8). Os outros 22 usos de `$$matriz[$i]`
(11 em cada arquivo) **compilam nos dois**, mas mudam de significado: no 5.6 é `${$matriz[$i]}` (variável cujo nome é
`$matriz[$i]`); no PHP 7+ é `(${$matriz})[$i]` — o `php -l` não acusa e o 8.x deixa de criar a variável (regressão silenciosa;
a data e os valores calculados ficariam vazios).

| Arquivo | Linhas | Correção |
|---|---|---|
| `calculoiptu.php` | 72, 73, 78, 80, 82, 85, 86, 105, 106, 109, 110 | `$$matriz[$i]` → `${$matriz[$i]}` (mesma forma válida nos dois) |
| `calculoissqnfixo.php` | 137, 138, 143, 145, 147, 150, 151, 170, 171, 174, 175 | idem |

Prova: trecho isolado `$matriz = array('abc'); $i = 0; ${$matriz[$i]} = 'X';` dá `$abc === 'X'` no 5.6 e no 8.5; a forma antiga
dava `X` no 5.6 e variável não criada no 8.5 (medido pelo QA). Teste `tests/suite/amostra/VariavelVariavelMatrizTest.php`
(camada unitária, os dois runtimes): trecho isolado + os dois arquivos sem `$$matriz[` e com 12 `${$matriz[$i]}` cada (11 trocados + 1
que já era assim). Visto falhar sem a correção (`testCalculosUsamAFormaComChaves`) e passar com ela nos dois runtimes; `php -l` limpo
nos dois. Diff: 22 linhas em 2 arquivos (ASCII).

Mesma forma `$$nome[...]` existe em outros arquivos (`grep -rn '\$\$[a-zA-Z_]*\[' ecidade --include=*.php`): `ate2_confereatend002.php`,
`con3_acount.php`, `con2_lrfimpostossaude002_2007.php`, `duplos.php`, `func_consbens001.php`, `dbforms/db_classes_criaiframe.php`,
`dbforms/db_classes_iframe_alterar_excluir.php`, `libs/db_stdlib.php` — **fora do escopo desta tarefa; não corrigidos**.
## Depois da T-020 — 7 legados residuais (nenhum Rector, nenhuma outra branch)

Os 7 arquivos compilavam no 5.6 e não no 8.5. T-004 (Rector em simulação) e T-017 (branches) ainda não tinham fechado quando
isto foi feito; a conferência do PO de 12/11 diz que nenhuma branch os toca. Todos são correção **manual** de uma linha (ou 4, no
`pro4_canarquiv002`), e nenhuma é transformação que o Rector já faça. Reconferir quando a T-004/T-017 saírem.

| Arquivo | Defeito no 8.5 | Correção | Por que reproduz o 5.6 |
|---|---|---|---|
| `con1_contrib007.php:53` | `break` fora de laço | `exit` | o 8.5 não compila `break` fora de laço; `exit` mantém o script parando ali (ver "Divergência medida" abaixo: **não é idêntico ao 5.6**) |
| `dbforms/db_virafolha.php:1058` | idem | `exit` | idem; mesma divergência |
| `pro4_canarquiv002.php:118,133,147,162` | idem (4 ocorrências; o lint só acusa a 1ª) | `exit` | idem; mesma divergência |
| `duplos.php` (12 usos: 1473 `global` + 1480…1532), `duploscgs.php` (12 usos: 483 + 490…543) — todos em `db_fieldsmemory1` | `$$matriz[$i]` (8.x lê `($$matriz)[$i]`; compila nos dois, o lint não acusa) | `${$matriz[$i]}` em **todos** (global, atribuição e leitura), como `libs/db_stdlib.php:874-875` | o 5.6 lê `${$matriz[$i]}`; medido sobre a função inteira (abaixo) |
| `integracao_externa/auditoria/auditoria_migracao_cursor.php:271` | `08` literal inválido (octal) | `0` | no 5.6 `08` vale 0; `substr(x, 11, 0)` devolve `""` nos dois |
| `integracao_externa/gissonline/iss4_gissonline002.php:1767` | `$string {$tm}` removido no 8.0 | `$string[$tm]` | mesma leitura do caractere |

Arquivos em ISO-8859-1 editados por `sed` na linha; `git diff` mostra só as linhas acima. Sem cópia em `extension/modification/`.
`php -l` limpo no 5.6 e no 8.5 nos 7 arquivos.

**Verificação (sem banco, função inteira):** réplica de `db_fieldsmemory1` (extraída de cada arquivo, sem rede; `select 42 as z01_numcgm,
'FULANO' as z01_nome, '1980-02-03'::date as z01_nasc, 3.5 as z01_valor, 'x' as z01_obs`, com e sem `$formatar`) e leitura das globais de
volta. Saída (md5 dos 5 pares nome=valor): original no 5.6 = nova no 5.6 = nova no 8.5, nos dois arquivos e nos dois modos (`z01_numcgm='42'`,
`z01_nome='FULANO'`…). Contraste: com só a linha `global` corrigida (versão anterior desta branch), no 8.5 as 5 globais ficam `NAO_DEFINIDA`.
Os trechos `substr(…, 11, 0)`, `$s[$i]` foram medidos isolados e dão o mesmo nos dois runtimes.
- **Achado fora do escopo:** `split()` (removido no PHP 7) aparece em `duplos.php` (2), `duploscgs.php` (2), `con1_contrib007.php` (1) e
  `dbforms/db_virafolha.php` (2) — contagem do `grep`, pode incluir comentário. No 8.5 `db_fieldsmemory1` com coluna de data morre com
  `Call to undefined function split()`; a réplica acima definiu um `split` só no harness para medir o resto. A spec cobre apenas os erros de
  compilação; pendência: varredura do universo por `split(` (o `php -l` não pega função removida).

**Divergência medida — `break` fora de laço → `exit` (6 pontos: `con1_contrib007` 1, `db_virafolha` 1, `pro4_canarquiv002` 4):**
a troca **não reproduz o 5.6 byte a byte**. Decisão mantida: `exit`, porque o 8.5 nem compila o arquivo com `break` fora de laço.

| | HTTP | Corpo | Registro de erros |
|---|---|---|---|
| 5.6 com `break` | **500** | saída parcial + página V3 "Erro interno" (Notificação do Sistema) | `E_ERROR` (`Cannot break/continue 1 level`) no `error.log` |
| 5.6 e 8.5 com `exit` | **200** | saída parcial até o ponto do `exit` | nada |

Medido com um arquivo de teste de 4 linhas nos dois runtimes (`break` dentro de `if`: 5.6 devolve 500 com `antes` seguido da página de
erro; 8.5 devolve 500 por erro de compilação; `exit`: 200 com `antes` nos dois). O fluxo (script para no caminho de erro, transação
sem fim) é o mesmo; muda o status HTTP, a página de erro e o log. Os dois defeitos de origem continuam como estão no código (o
`break` fora de laço e o `08` octal de `auditoria_migracao_cursor.php:271`, que grava hora vazia).

**Lacuna — bateria de tela:** nenhum dos 7 é exercitável sem gravar além do log de acesso. `con1_contrib007`
(só chega ao `exit` com `confirma=ok`, que exclui contribuinte), `pro4_canarquiv002` (desarquivamento grava `procandam`/`arqandam`),
`db_virafolha` (apaga a folha), `duplos.php`/`duploscgs.php` (unificação de CGM em linha de comando, não é tela),
`auditoria_migracao_cursor.php` (script de migração da auditoria) e `iss4_gissonline002` (processa arquivo da integração
externa, que não pode ser contatada). Os trechos alterados ficam atrás dos `if` de erro/confirmação.
### T-028: pizza do jpgraph no PHP 8 (13/11/2026)

Achados do QA ao validar a T-021: a pizza não rodava no 8.5. Medido (`PiePlot`, `PiePlotC`, `PiePlot3d`, PNG, md5 dos pixels, 5.6 como gabarito); **quatro** defeitos de migração em cadeia, todos corrigidos reproduzindo o 5.6:

| # | Arquivo | Defeito no 8.5 | O que o 5.6 fazia | Correção |
|---|---|---|---|---|
| 1 | `libs/jpgraph/jpgraph.php` (`CakeSlice`, `imagefilledarc` da borda) | `TypeError`: nome de cor (string) onde o GD pede inteiro | `imagefilledarc()` só dava warning e **não desenhava** | `if( is_numeric($this->current_color_name) )` antes da chamada: nome de cor não desenha (como no 5.6); cor numérica continua desenhando |
| 2 | `libs/jpgraph/jpgraph_pie3d.php` `AddSliceToCSIM` | fatal "must be compatible" com `PiePlot::AddSliceToCSIM` | E_STRICT | `$sa=null,$ea=null` (opcionais); lógica e chamada (8 argumentos) iguais |
| 3 | idem, `Stroke` | fatal "must be compatible": o pai recebe `&$img` | E_STRICT | `Stroke(&$img,…)` |
| 4 | idem, construtor `PiePlot3d(&$data)` (estilo PHP 4) | no 8.x deixa de ser construtor: rodava o de `PiePlot`, a pizza saía **diferente** (rótulos `40.0%`, fatias em outra ordem) sem erro nenhum | era o construtor | `__construct(&$data)` |

Os defeitos 3 e 4 não estavam na spec: apareceram ao fazer a imagem sair igual (critério 2). Nenhum desenho mudou: no 5.6, o código **antes** e **depois** da correção gera as mesmas imagens.

**Verificação** (containers `ecidade_front1_56/85`, `gera_pizza.php`, sem banco): PNG igual byte a byte nos pixels (md5) nos dois runtimes:

| Gráfico | 5.6 antes | 5.6 depois | 8.5 antes | 8.5 depois |
|---|---|---|---|---|
| `PiePlotC` (300×250) | `7992ae1f…` | `7992ae1f…` | TypeError (1) | `7992ae1f…` |
| `PiePlot` (300×250) | `08a32498…` | `08a32498…` | TypeError (1) | `08a32498…` |
| `PiePlot3d` (350×280) | `aedf7d12…` | `aedf7d12…` | fatal (2, 3) | `aedf7d12…` |
| Gráfico "Total Por Bairro" de `ass_rreqtotais002.php` | n/m | `b7b3717d…` | fatal | `b7b3717d…` |

Testes: `ecidade/tests/suite/jpgraph/JpgraphPizzaTest.php` (camada integração, 4 testes, hashes fixados no gabarito 5.6; cada gráfico em processo próprio, porque o jpgraph guarda estado global e o resultado dependia da ordem dos testes). Suíte completa (unitário + integração) medida no commit `eb059695b` (código e testes da branch; o commit seguinte só muda docs), sobre a base `d46b684c6`: 5.6 **283/283** (277 unitário + 6 integração); 8.5 **77/79** (73 + 6; as 2 falhas são as da T-026, `docs/registro/suite-testes.md`). Os 4 testes novos passam nos dois; a linha de base (`suite-testes.md`: 5.6 279, 8.5 75) mais 4 dá 283 e 79.

**Limites (registrados, não corrigidos):**
- `ass_rreqtotais002.php` inteiro **não** roda nesta base: usa as tabelas `req_mudancas` e `Bairros`, que não existem no banco de exemplo (falha no SQL igual nos dois runtimes, antes do gráfico). O gráfico foi reproduzido com a mesma configuração e dados de exemplo (sem o cache `'auto'` e sem as fontes TTF `FF_VERDANA`/`FF_ARIAL`, que não estão instaladas nos containers: com elas o jpgraph devolve a imagem de erro, igual nos dois).
- O warning do `imagefilledarc` (item 1) que o 5.6 emitia deixa de ser emitido. O desenho é o mesmo. Em PHP 8 há ainda warnings de `Trying to access array offset on null` (`jpgraph_pie.php:260/280`, `csimalts` nulo) que o 5.6 não emitia; são só mensagens, não alteram a imagem, e ficam fora do porte mínimo.
- Gráficos de pizza sem `SetLegends` quebram no 8.5 com `count(): Argument #1 must be of type Countable|array, null given` (`jpgraph_pie.php:251`); o 5.6 contava `null` como 0. Nenhum chamador do repositório deixa de chamar `SetLegends` (`ass_rreqtotais002.php` chama). Fica registrado como defeito de migração para tarefa própria, se aparecer uso.
- A cópia `dbagata/classes/jpgraph` não foi tocada (fora do escopo).
- Imagens geradas com a base em `SOMENTE_LEITURA` não se aplicam: o gerador não abre conexão com o banco.
