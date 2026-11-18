# Decisões da migração PHP 5.6 → 8.5: os 11 PDFs e as 941 divergências

Para: dono de produto / gestor técnico. Base: rodada "antes" consolidada (`~/rodadas/antes-consolidado.md`,
`triagem-divergencias.md`), reprodução ao vivo em 17/11/2026 (sessão autenticada por login HTTP, como a bateria faz em
`regressao/php/relatorios.py`; GET no `ecidade_php85` e no `ecidade_php56`; causa lida em `ecidade/extension/log/error.log`)
e varredura estática do código. Nada foi alterado no código de produção nem nas baselines.

## Resumo executivo

1. **Os 11 PDFs não quebram por biblioteca de PDF**: a FPDF (`fpdf151`) funciona no 8.5 (cerca de 25 outros PDFs do catálogo saem idênticos). **10 dos 11 quebram numa única linha**: `parse_str()` com 1 argumento, removido no PHP 8. O 11º (`cad2_loteam002`) quebra porque a consulta SQL falha no banco de desenvolvimento e o PHP 8 deixou de ignorar o erro.
2. **Corrigir os 11 custa cerca de 1 dia** (com teste). Os 5 balancetes/relatórios da Contabilidade têm uma **2ª quebra escondida** logo abaixo (`split()`, removido no PHP 7): são 2 linhas por arquivo, não 1.
3. **"Aceitar" significa colocar em produção** balancetes da receita e da despesa que mostram "Erro interno" ao contador e só silenciar o alarme da suíte. Isso bloqueia a conferência do fechamento mensal e da prestação de contas. **Não recomendado.**
4. Das 941 divergências, **cerca de 85% vêm de 2 causas mecânicas**: `parse_str` de 1 argumento (559 telas + 10 PDFs) e construtor no estilo PHP4 (84 telas só com ela, 128 junto com `parse_str`, 147 classes). A 3ª (`split`/`each`/`ereg`) está escondida atrás das duas.
5. **As mesmas correções já foram aplicadas a mais da metade do código**: 3.826 arquivos já usam `parse_str(..., $__qs); extract($__qs);` e 3.425 classes já têm `__construct`. É terminar uma migração em andamento, com o padrão do próprio repositório.
6. **Maior risco fora do radar**: as **2.525 janelas de pesquisa `func_*.php`** (as "lupas", chamadas por cerca de 4.300 telas) têm o mesmo `parse_str` e **a suíte não as testa**. Nas 6 sorteadas, as 6 dão 500 no 8.5 e 200 no 5.6.
7. Restam **cerca de 130 a 200 telas com causas não mecânicas**: consulta SQL que falha, `count(null)`, `int + string`… Quase todas aparecem porque a suíte abre a tela sem parâmetros. **Decisão de negócio**: reproduzir o silêncio do 5.6 (relatório vazio) ou mostrar um erro claro.
8. **Ordem recomendada**: (1) `parse_str` em todo o código, incluindo `func_*`; (2) construtores PHP4; (3) `split`/`each`/`ereg`; (4) 4 erros de compilação + 2 classes; (5) triagem caso a caso do restante, com parâmetros reais.
9. Pôr as 941 em `conhecidas.tsv` **contraria a regra do próprio arquivo**, que aceita só divergência que já existia antes da migração. Nenhuma das 941 é pré-existente.
10. **Incertezas**: as contagens vêm de varredura estática mais amostra ao vivo (cerca de 75 telas e relatórios). Cada correção pode revelar a quebra seguinte da mesma tela (efeito "cebola"), por isso os ganhos abaixo são faixas, não números exatos.

---

## A. Os 11 relatórios PDF (5.6 = 200 com PDF, 8.5 = 500 "Erro interno")

Reproduzidos ao vivo, os 11 com o mesmo resultado da bateria. Causa exata lida no log do 8.5:

| Relatório | Onde fica no menu (módulo) | Causa no 8.5 (arquivo:linha) | 2ª quebra escondida |
|---|---|---|---|
| `mat2_cadunidade002` | Material > Relatórios Cadastrais > Cadastro de Unidades | `ArgumentCountError: parse_str() expects exactly 2 arguments, 1 given`, `mat2_cadunidade002.php:38` | nenhuma achada |
| `prot2_cadcgm002` | Protocolo > Consulta CGM (`prot3_conscgm002`) > imprimir ficha | idem, `prot2_cadcgm002.php:34` | nenhuma achada |
| `con2_relinstituicoes002` | Configuração > Relatórios > Instituições | idem, `con2_relinstituicoes002.php:35` | nenhuma achada |
| `con2_conhist002` | Contabilidade > Cadastrais > Histórico de Lançamentos | idem, `con2_conhist002.php:39` | nenhuma achada |
| `con2_conhistdoc002` | Contabilidade > Cadastrais > Documentos de Lançamentos | idem, `con2_conhistdoc002.php:39` | nenhuma achada |
| `con2_balancrece002` | Contabilidade > Balancetes > Balancete da Receita | idem, `con2_balancrece002.php:47` | `split("-", $db_selinstit)`, linha 50 |
| `con2_balancdespele002` | Contabilidade > Balancetes > Balancete da Despesa por Elemento | idem, `con2_balancdespele002.php:38` | `split`, linha 46 |
| `con2_balancrecu002` | Contabilidade > Balancetes > Balancete da Receita por Recurso | idem, `con2_balancrecu002.php:48` | `split`, linha 51 |
| `con2_contasrecdesp002` | Contabilidade > Relatórios de Conferência > Conferência Despesa/Receita | idem, `con2_contasrecdesp002.php:32` | `split`, linha 34 |
| `con2_relrec002` | Contabilidade > Relatório da Receita (`con2_relrec001`/`con2_relplano001`) | idem, `con2_relrec002.php:41` | `split`, linha 44 |
| `cad2_loteam002` | Cadastro (imobiliário) > Financeiros > Débitos por Matrículas | `TypeError: pg_numrows(): Argument #1 must be of type PgSql\Result, false given`, `cad2_loteam002.php:180` | (é a causa) |

A coluna "2ª quebra" vem de varredura estática do arquivo e dos seus `include` até 3 níveis, procurando APIs removidas.
`split()` não existe no 8.5 (`function_exists('split')` dá `false` e não há polyfill no repositório): corrigida só a
linha do `parse_str`, esses 5 relatórios continuam em 500, agora com `Call to undefined function split()`.

### Agrupados por causa raiz

**Grupo 1: `parse_str` de 1 argumento (5 relatórios cadastrais: unidades, CGM, instituições, históricos e documentos contábeis).**
No PHP 5.6, `parse_str($querystring)` criava uma variável para cada parâmetro da URL. O PHP 8 removeu esse modo.
- Correção típica: `parse_str($HTTP_SERVER_VARS['QUERY_STRING'], $__qs); extract($__qs);`. É o padrão já usado em 3.826 arquivos (incluindo `cad2_loteam002.php:38`, já corrigido).
- Esforço: 15 min por arquivo, mais teste. **Cerca de 2 h para os 5.**
- Risco: baixo. A equivalência foi testada no 5.6 e no 8.5 (ver C.1).

**Grupo 2: `parse_str` + `split()` (5 relatórios da Contabilidade: 3 balancetes, conferência e relatório da receita).**
- Correção: a mesma linha do grupo 1, mais `split("-", $db_selinstit)` → `explode("-", $db_selinstit)`. O separador é literal, então o comportamento é idêntico.
- Esforço: **cerca de 2 h para os 5**, mais **cerca de 4 h de validação com parâmetros reais** (instituição, período, nível).
- Atenção: chamados sem parâmetros, como no catálogo, **o PDF do 5.6 só traz o cabeçalho** (12 linhas, "INSTITUIÇÕES :" vazio). A suíte prova hoje que o relatório "abre", não que os valores do balancete batem. Antes de confiar no verde, o catálogo precisa de uma linha com parâmetros reais (é uma mudança na suíte, fora deste documento).
- Risco: baixo para o código e médio para os números. As bibliotecas de cálculo (`libs/db_libcontabilidade.php` e outras) nunca rodaram no 8.5 por este caminho.

**Grupo 3: consulta SQL que falha (`cad2_loteam002`).**
- Causa verificada: a tabela `debitos` está **vazia no banco de desenvolvimento**. `$ult_data` fica vazio, a consulta vira `k22_data = ''` e o PostgreSQL recusa (`sintaxe de entrada é inválida para tipo date: ""`).
- No 5.6, `pg_numrows(false)` só emitia um aviso: o PDF saía **vazio**, com o erro escondido. No 8.5 o mesmo erro aborta a página.
- Com uma data válida, a mesma consulta roda sem erro (testado no banco). **Em produção, com débitos calculados, o relatório provavelmente funciona no 8.5.** Ele quebra quando a instituição não tem débitos calculados.
- Correção típica: tratar o caso sem débitos (mensagem "não há débitos calculados" ou relatório vazio) e testar `db_query` antes de `pg_numrows`. **1 a 2 h.** Risco baixo.

### Para quem cada relatório importa

Avaliação funcional pelo menu e pelo conteúdo. Não há dados de uso de produção, então a frequência é estimada.

| Relatório | Quem usa | Frequência (estimada) | Bloqueia fechamento ou prestação de contas? |
|---|---|---|---|
| Balancete da Receita, Balancete da Receita por Recurso, Balancete da Despesa por Elemento | Contador / setor contábil | mensal (fechamento) e sob demanda em auditorias | **Sim, na prática**: são os documentos de conferência da execução antes do envio ao Tribunal de Contas e dos demonstrativos LRF; o "por Recurso" confere fontes vinculadas (mínimos de saúde e educação) |
| Conferência Despesa/Receita | Contabilidade | mensal (fechamento) | **Sim, na prática**: é um relatório de conferência |
| Relatório da Receita (`con2_relrec002`) | Contabilidade / Orçamento | ocasional | não diretamente |
| Ficha do CGM (`prot2_cadcgm002`) | Atendimento, Protocolo, Tributário | diária em prefeituras com balcão de atendimento | não, mas afeta o atendimento ao público |
| Débitos por Matrícula / loteamento (`cad2_loteam002`) | Cadastro imobiliário, cobrança, dívida ativa | ocasional, campanhas de cobrança | não |
| Histórico e Documentos de Lançamentos | Contabilidade (configuração do plano / eventos) | rara (implantação, auditoria) | não |
| Instituições | Configuração (TI / administrador) | rara | não |
| Cadastro de Unidades (almoxarifado) | Almoxarifado | rara | não |

---

## B. As decisões concretas

**O que cada opção significa:**

- **Corrigir**: alterar o código (linhas citadas acima). A bateria passa a **verde** nesses casos (IDENTICO) e o usuário recebe o relatório.
- **Aceitar**: acrescentar `relatorio:<tela>.php<TAB>motivo` em `regressao/conhecidas.tsv`. A bateria **deixa de ficar vermelha** (saída 0), mas **a funcionalidade vai quebrada para produção**: o usuário clica em Imprimir e vê "Notificação do Sistema / Erro interno". Aceitar não conserta nada, só silencia o alarme. Também contraria a regra do cabeçalho do `conhecidas.tsv` ("só entra divergência PREEXISTENTE com prova"): estas divergências nasceram na migração.
- **Adiar**: não mexer agora. A bateria **continua vermelha** (saída 1) e não serve como critério de "pode ir para produção" enquanto isso. Faz sentido só se a virada para o 8.5 não for iminente.

| Grupo | Recomendação | Bateria depois | Risco de produção se aceito | Custo se corrigir |
|---|---|---|---|---|
| 1. `parse_str` (5 cadastrais) | **Corrigir** (de carona na correção em massa da seção C) | 5 vermelhos → verdes | baixo a médio: relatórios de consulta param; o CGM afeta o balcão | cerca de 2 h, ou zero extra se entrar na correção em massa |
| 2. `parse_str` + `split` (5 contábeis) | **Corrigir já**, com teste de valores | 5 vermelhos → verdes (e, com linha de catálogo com parâmetros, prova de valores) | **alto**: contador sem balancetes no fechamento mensal; tende a virar chamado urgente no 1º fechamento após a virada | cerca de 2 h de código + cerca de 4 h de validação |
| 3. SQL que falha (`cad2_loteam002`) | **Corrigir** (guarda de 1 a 2 h). Adiar é aceitável se a cobrança confirmar que toda instituição tem débitos calculados | 1 vermelho → verde | baixo: só quebra quando não há débitos calculados | 1 a 2 h |

---

## C. Impacto nas 941 divergências PHP consolidadas

### Composição (cada divergência contada uma vez, pela primeira quebra provável)

| Etapa | DIVERGE | Primeira causa |
|---|---|---|
| telas (GET) | 777 | 559 `parse_str` (431 só ela, 128 também com construtor PHP4) · 84 só construtor PHP4 · 134 outras causas |
| classes instanciadas | 149 | 147 construtor PHP4 · 2 `ParameterException` |
| relatórios | 11 | 10 `parse_str` · 1 SQL que falha |
| sintaxe (`php -l`) | 4 | erro de compilação PHP 8 |
| **Total** | **941** | |

Status das 777 telas: 738 são 200 no 5.6 e 500 no 8.5; 29 são 500 nos dois lados com páginas de erro diferentes;
9 são 200 nos dois lados com conteúdo diferente; 1 tem resposta truncada.

### Causa por causa

| # | Causa | Divergências afetadas | Verificação ao vivo (log do 8.5) | Correção padrão | Busca-e-troca mecânica? | Risco (o comportamento muda?) | Esforço | Se corrigir: somem | Se aceitar: linhas em `conhecidas.tsv` |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `parse_str()` com 1 argumento | 559 telas + 10 PDFs (+ 2.525 `func_*` fora da suíte) | **32 de 32**: 8 só `parse_str`, 8 combinadas, 10 PDFs, 6 `func_*` (`ArgumentCountError`, linha do `parse_str`) | `parse_str(X);` → `parse_str(X, $__qs); extract($__qs);` | **Sim**, por regex, em cerca de 3.290 arquivos (3.223 telas na raiz, 30 `forms/`, 25 `dbforms/`, 2 `libs/`, 2 `fpdf151/`, poucos outros) | baixo. Teste no 5.6 e no 8.5: mesmo resultado para chaves comuns, arrays (`b[]`, `h[k]`), `.` e espaço (viram `_`), sobrescrita de variável existente e escopo de função. Diferenças só em chaves patológicas (ver nota) | 1 a 2 dias (script, revisão do diff por amostra, bateria por área) | 431 telas no teto, mais 5 PDFs. **Realista: 300 a 430**, porque 66 delas usam `split` no próprio arquivo e outras podem revelar erro de tipo. As 128 combinadas mudam de sintoma (passam a quebrar no construtor). Os 5 balancetes exigem também a causa 3 | 569 |
| 2 | Construtor estilo PHP4 (`function cl_x()` sem `__construct`): o PHP 8 não o chama, e `rotulo`/`pagina_retorno` ficam nulos | 147 classes + 212 telas (84 só ela, 128 com `parse_str`) | **7 de 8** telas: `Call to a member function label() on null` em `forms/db_frm*.php:28-32` (a 8ª quebrou antes, em `pg_num_rows(false)`). Classes: varredura (147 de 149 só têm o construtor antigo) | renomear `function cl_x(` → `function __construct(` | **Sim** em `classes/` (600 `db_*_classe.php` com o problema, 147 medidos pela suíte e 453 não instanciados por ela). Revisar à mão cerca de 47 classes em `libs/`, 5 em `dbagata/` e uns 6 avulsos | baixo: devolve o comportamento do 5.6 (o construtor volta a rodar). Nenhuma chamada explícita ao nome antigo (`->cl_x(`, `parent::cl_x(`) achada | 0,5 a 1 dia + bateria | 147 classes + cerca de 74 telas (7/8 de 84); com a causa 1 também corrigida, mais até 128 → **até cerca de 350** | 359 |
| 3 | APIs removidas no PHP 7: `split()`, `each()`, `ereg*()`, `create_function()` | **0 divergências próprias hoje** (2ª camada): 192 telas da raiz com uso ativo (76 já DIVERGE por outra causa, 58 INCONCLUSIVO, **17 IDENTICO só porque a linha não roda sem parâmetros**, 41 fora da suíte) + os 5 balancetes | estática (`split` inexistente no 8.5). Ao vivo, 4 telas com `split` quebraram antes por outra causa | `split("-", x)` → `explode("-", x)` quando o separador é literal (a maioria: `#`, `-`, `_`, `,`, `/`); regex (`\?`, `\|`) → `preg_split`; `each` → `foreach`; `ereg*` → `preg_*` | **Semi**: separador literal sim, regex à mão | baixo a médio: `split` usa regex; com separador literal o resultado é idêntico ao `explode` | 1 a 2 dias | não reduz a contagem sozinha, mas evita que cerca de 70 telas e 5 PDFs voltem a vermelho depois das causas 1 e 2 | — |
| 4 | Consulta SQL que falha e o resultado `false` vai para `pg_num_rows`/`pg_numrows`/`pg_fetch_*` (`TypeError`) | estimativa **45 a 65 telas** + `cad2_loteam002` (20 contadas no complemento; 10 de 28 na amostra das "outras") | 12 casos, ex.: `pro1_relduploscgm002.php:59`, `pro4_mandespacho002.php:57` (SQL com `$p58_codproc` vazio), `cad2_relaverbacao002.php:155`, `classes/materialestoque.model.php:1024` | **não há troca única**. (a) *shim* de paridade: devolver 0 linhas quando a consulta falha, reproduzindo o 5.6; (b) tratar cada tela com mensagem clara | (a) sim; (b) não | (a) mantém o 5.6, mas o usuário continua vendo **relatório vazio sem saber que houve erro**; (b) muda o comportamento para melhor | (a) cerca de 1 dia; (b) 1 a 3 h por tela, ou 1 a 3 semanas | quase todas | 45 a 65 |
| 5 | Biblioteca Agata: `Unsupported operand types: int + string` em `dbagata/classes/reports/AgataReport.class:122` (`+=` sobre total não inicializado) | poucas diretas (1 confirmada: `pro1_relcgm002`), mas a biblioteca é usada por 76 telas. Junto: `Class "Agata" not found` (`cad1_reliptuender002`) | 2 de 2 | inicializar o acumulador (`?? 0`, cast numérico) **em 1 lugar da biblioteca** | sim (1 linha) | baixo | 2 a 4 h | as diretas (2 a 5) | 2 a 5 |
| 6 | Funções de array/contagem com `null` (`count`, `sizeof`, `rsort`, `array_chunk`, `array_key_exists`) | cerca de 10 a 20 telas | 5 de 5 (ex.: `libs/db_libtributario.php:366`, `cad2_emissaobic_002.php:43`, `bib2_comprovantemodelo_a4.php:96`) | `(array) $x` ou guarda; nas `libs/` a correção vale para várias telas | semi | baixo | 1 a 2 h por ponto | quase todas | 10 a 20 |
| 7 | Outros tipos: `mktime()` com string, `Path must not be empty`, `fgets(false)`, `No PostgreSQL connection opened yet`, propriedade em `null`, `Requires N arguments`, 500 sem log (`con2_lrf*_2018`) | cerca de 15 a 25 telas | 4 de 4 na amostra (`lab2_mapacoletaconsulta.php:22`, `sau2_bpa001.php:43`, `std/label/RotuloCampoDB.php:37`, `forms/db_frmorcsuplem.php:90`) + 2 dos timeouts; 2 sem log | caso a caso | não | variável | 1 a 3 h por tela | quase todas | 15 a 25 |
| 8 | Erro de compilação no PHP 8 (`php -l`) | 4 arquivos | 2 de 2 ao vivo: `cad1_lote002.php:198`, `cad1_lote003.php:196` (`'break' not in the 'loop' or 'switch' context`); também `con1_contrib007.php:53`, `pro4_canarquiv002.php` (parse error) | à mão | não | baixo | 1 a 2 h no total | 4 (+ as telas) | 4 |
| 9 | Classe levanta `ParameterException` ao instanciar | 2 (`db_obrasalvara`, `db_obrasender`) | triagem | investigar | não | ? | 2 a 4 h | 2 | 2 |
| 10 | 200 × 200 com conteúdo diferente | 9 | triagem: `cad4_constr002` (o 8.5 mostra um `<select>` a mais), `cad2_carlote002` (SQL impresso), `con4_pesquisarecursosigfis.RPC` (5.6 `[]`, 8.5 lista), `con2_anexovirgf_002` (`ReflectionParameter::getClass()` removido) | caso a caso; decidir qual lado está certo | não | ? | 1 a 2 h cada | 9 | 9 |

Notas:

- **`cad1_lote002`/`003` (alteração e exclusão de lote, Cadastro imobiliário) não compilam no 8.5.** É rotina de cadastro, não relatório, e o custo de corrigir é pequeno.
- **Nota sobre `extract`** (causa 1): no 8.5, uma URL com `?this=1` faz `extract()` lançar `Error: Cannot re-assign $this`, e a página dá 500 (testado). Isso **já vale para os 3.826 arquivos convertidos**. Ao converter em massa, vale filtrar antes: `unset($__qs['this'], $__qs['GLOBALS']); extract($__qs);`. Também diferem chaves que começam com dígito (`1g=4`): o 5.6 criava `${'1g'}`, que o código não consegue ler de qualquer forma.
- **Por que a correção mecânica é a mesma do repositório**: nos 3.826 arquivos com `parse_str(..., $__qs)`, todos chamam `extract($__qs)`. As variáveis precisam ir para o escopo local, porque as telas leem `$ordem`, `$db_selinstit` etc. diretamente. `parse_str(x, $_GET)` **não** serve: não cria as variáveis locais.

### O que a suíte mostraria depois (faixas, por causa da "cebola")

| Cenário | DIVERGE restantes (de 941) | O que sobra |
|---|---|---|
| hoje | 941 | — |
| só causa 1 (`parse_str`) | cerca de 500 a 640 | as 128 combinadas passam a falhar no construtor; telas com `split` voltam a falhar |
| causas 1 + 2 + 3 (todas mecânicas) | **cerca de 150 a 270** | 134 "outras" + `cad2_loteam002` + 4 lint + 2 `ParameterException` + as que revelarem 2ª camada |
| 1 + 2 + 3 + 5 + 6 + 8 (mecânicas + 1 linha na Agata + guardas de `null` + lint) | cerca de 100 a 200 | sobretudo a causa 4 (SQL que falha sem parâmetros): **decisão de negócio (a) ou (b)** |
| tudo aceito em `conhecidas.tsv` | 0 (saída 0) | **todas as funcionalidades continuam quebradas em produção**; 941 linhas de justificativa, contra a regra do arquivo |

Corrigir também pode **mover** casos de INCONCLUSIVO para DIVERGE: telas que hoje falham igual nos dois lados podem
passar a mostrar a próxima quebra só no 8.5. Isso é a suíte enxergando mais, não regressão nova.

### Cobertura: o que a suíte NÃO enxerga

- **3.255 arquivos `.php` da raiz não rodam na bateria** (12.439 de 15.694 rodam). São 2.993 janelas `func_*.php`, excluídas de propósito em `regressao/php/bateria.py` porque não estão em nenhum prefixo de área, e 262 de prefixos sem área (`tra` 62, `ipa` 24, `db` 23, `tel` 15, `fim` 14, `sam` 11…).
- **2.525 das `func_*` têm `parse_str` de 1 argumento.** Ao vivo, `func_grupotaxa`, `func_cadtipo`, `func_db_menu`, `func_conciliaextrato`, `func_cadtipodocumento` e `func_progressaoparcialalunoturmaregencia` dão 200 no 5.6 e 500 no 8.5; as já convertidas (`func_cgm`, `func_nome`, `func_iptubase`) saem idênticas.
- As `func_*` são as janelas de pesquisa ("lupa") de quase todos os formulários: 4.299 telas citam uma. **Ignorar isso faz a suíte ficar verde com as pesquisas quebradas.** Recomenda-se uma rodada de fumaça `--prefixo '^func_'` (é decisão sobre a suíte; aqui não foi alterada).
- **INCONCLUSIVO 919** (nenhum é aprovação):
  - 589 telas com "página de erro idêntica nos dois lados": exigem parâmetros e o 5.6 também falha. O que o 8.5 faria depois não foi exercitado; 78 telas com `parse_str` de 1 argumento estão aqui.
  - 195 telas vazias nos dois lados.
  - 45 classes sem saída.
  - 86 arquivos que **não compilam em nenhum dos dois runtimes** (ex.: `con2_lrf*`): código já quebrado no 5.6.
  - Mais alguns isolados (1 relatório, 2 telas puladas por destruir a sessão).
- **ERRO_AMBIENTE 11**: telas que estouram o tempo no 5.6. No 8.5, 9 delas respondem 500 em segundos. Exemplos: `rec2_espelhoponto002.php:38` (`fgets(false)`) e `edu4_importarcodigoinep002.php:38` (`Path must not be empty`). Abertas sem o arquivo de importação, o 5.6 entra em laço e o 8.5 aborta: é mudança de comportamento, não perda de função no uso real, mas vale um teste com o arquivo.
- **Classes**: 453 das 600 classes com construtor PHP4 nunca foram instanciadas pela etapa de classes.
- **Profundidade**: a bateria faz GET sem parâmetros. Ela prova que a tela "abre" igual, não que os números batem; os balancetes são o exemplo (PDF de referência só com cabeçalho).

---

## D. Recomendação priorizada

1. **`parse_str` em massa** (causa 1), incluindo `func_*`, `forms/` e `dbforms/`, com o filtro de `this`/`GLOBALS`. É mecânico, segue o padrão do repositório e dá o maior retorno: cerca de 570 divergências e cerca de 2.500 lupas fora do radar. **1 a 2 dias.**
2. **Construtores PHP4** (causa 2) em `classes/` (600 arquivos) e revisão das 47 classes de `libs/`. Mecânico, cerca de 360 divergências. **0,5 a 1 dia.**
3. **`split`/`each`/`ereg`** (causa 3): semi-mecânico, evita a "cebola" nos balancetes e em cerca de 190 telas. **1 a 2 dias.**
4. **Os 5 relatórios contábeis com validação de valores**: catálogo com parâmetros reais (instituição, período) e conferência do PDF do 5.6 contra o do 8.5. **Cerca de 0,5 dia.** É o que importa para o fechamento.
5. **Pequenos de alto valor**: os 4 erros de compilação (incluindo alteração e exclusão de lote), a linha da `AgataReport`, `cad2_loteam002` e as guardas de `null` em `libs/`. **1 a 2 dias.**
6. **Decidir com o negócio** (causa 4, SQL que falha): (a) paridade, com relatório vazio silencioso como no 5.6 e cerca de 1 dia; ou (b) mensagem de erro clara, tela por tela, em 1 a 3 semanas. Sugestão: (a) agora para não bloquear a virada e (b) para relatórios financeiros e de fechamento.
7. **Não aceitar em `conhecidas.tsv`** nada das causas 1 a 3: são baratas e aceitá-las enviaria funcionalidade quebrada. Aceitar só o que for comprovadamente preexistente ou irrelevante após a triagem do item 6.
8. **Rodar a suíte por área depois de cada passo**, porque cada correção revela a camada seguinte.

### Incertezas (seja qual for a decisão)

- As contagens por causa vêm de **varredura estática** (regex sobre o arquivo e os `include` até 3 níveis), confirmada por **amostra ao vivo**: 11 PDFs, 16 telas `parse_str`, 8 PHP4, 28 "outras", 9 `func_*` e 4 telas com `split`. O log mostra só a **primeira** quebra de cada página.
- As faixas de "somem se corrigir" assumem que a 2ª camada se comporta como na amostra; as causas 4 a 7 só aparecem executando.
- Frequência de uso e impacto no fechamento são avaliação funcional, sem estatística de produção.
- Esforços são de desenvolvedor familiarizado com o e-Cidade, sem contar as rodadas da bateria (horas de máquina: cerca de 3 h para todas as telas).
