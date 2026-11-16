# Triagem dos 781 DIVERGE da rodada "antes" (bateria PHP, ~/rodadas/antes)

Fonte: `resultado.json` da rodada (21 100 casos PHP: 19 623 IDENTICO, 781 DIVERGE, 639 INCONCLUSIVO, 57 ERRO_AMBIENTE).
Causa lida no log do PHP 8.5 (`extension/log/error.log`) em amostra ao vivo; contagem por categoria estimada por
varredura estatica dos arquivos (includes ate 3 niveis). **Nada aqui entrou em `conhecidas.tsv`: sao achados reais da migracao.**

| # | Categoria | Casos | Causa provavel |
|---|---|---|---|
| 1 | tela 200 (5.6) x 500 (8.5), `parse_str()` com 1 argumento | ~460 | `ArgumentCountError: parse_str() expects exactly 2 arguments, 1 given`: PHP 8 removeu o modo de 1 argumento (variaveis no escopo). Padrao `parse_str(base64_decode($_SERVER['QUERY_STRING']))` em dezenas de telas (hab*, pro*, con*, mat*) |
| 2 | tela 500 por classe `db_*_classe.php` sem construtor | ~73 (+125 junto da 1) | construtor PHP4 (`function cl_x()`): PHP 7+ nao o chama; `rotulo`/`pagina_retorno` ficam nulos e o form quebra: `Call to a member function label() on null` (forms/db_frm*.php) |
| 3 | tela 500 outras causas | ~89 | amostra viva: `Unsupported operand types: int + string` (AgataReport.class:122), `rsort(): Argument #1 must be of type array, null given`, `pg_numrows(): Argument #1 must be PgSql\Result, false given` (consulta falhou), e mais construtor PHP4 por include indireto |
| 4 | classe `db_*_classe.php` instanciada: propriedades 5.6 = codigos (`'1012'`), 8.5 = `0`/NULL | 147 | mesmo construtor PHP4 (nenhum `__construct`): confirmado por varredura (147 de 149 so tem `function <classe>()`) |
| 5 | classe com `ParameterException` no 8.5 | 2 | `db_obrasalvara_classe.php`, `db_obrasender_classe.php`: ja tem `__construct`, mas levantam `ParameterException` ao instanciar |
| 6 | `php -l` do 8.5 falha | 4 | erro de compilacao PHP 8: `con1_contrib007.php`: `'break' not in the 'loop' or 'switch' context` (linha 53); `cad1_lote002/003.php`, `pro4_canarquiv002.php`: parse error |
| 7 | tela 200 x 200, PDF diferente so em bytes | 3 | RUIDO (corrigido): streams do FPDF comprimidos/metadados (`/Length 636` x `609`) com o mesmo texto: `con4_gerrrelatorio`, `orc2_orcprevmensalrec002`, `sys3_modulos002` |
| 8 | tela 200 x 200, intermitente | 1 | `mer_subitem004.php` (1269 x 1113 B na rodada; identico ao repetir): estado/horario, nao reproduzivel |
| 9 | tela 200 x 200, pagina de erro com mensagem diferente | 1 | `con2_anexovirgf_002.php`: 5.6 `Undefined property: stdClass::$db_selinstit`; 8.5 `ReflectionParameter::getClass() is deprecated` (alem do mesmo erro-base): API removida |
| 10 | tela 200 x 200, dado diferente | 1 | `con4_pesquisarecursosigfis.RPC.php`: 5.6 devolve `[]`, 8.5 devolve a lista de recursos (verificar qual lado esta certo) |
| 11 | tela 500 x 500 com paginas de erro diferentes | 22 (dentro de 1-3) | os dois falham (tela exige parametros); a pagina do 5.6 e maior (~4,5 KB) que a do 8.5 (~3,7 KB): nao indica regressao por si so |

Totais: 622 telas com 500 no 8.5 (1+2+3 e 11) + 6 telas 200x200 (7-10) + 149 classes (4-5) + 4 lint (6) = 781.

## Exemplos (10 por categoria)

- **1 parse_str**: `hab1_cadastroavaliacao001.php`, `hab2_inscricoes002.php`, `pro1_certidao002.php`, `pro1_certidao003.php`, `pro1_certidaocgm002.php`, `pro1_certidaocgm003.php`, `pro1_certidaoinscr002.php`, `pro1_certidaoinscr003.php`, `pro1_certidaomatric002.php`, `pro1_certidaomatric003.php`
- **2 construtor PHP4**: `hab1_formaavaliacao005.php`, `hab1_formaavaliacaousuario001.php`, `hab1_habitprograma005.php`, `hab1_habitprograma006.php`, `hab1_habitprogramalistacompra001.php`, `hab1_tipogrupoprograma005.php`, `hab1_tipogrupoprogramaformaavaliacao001.php`, `hab4_inscricaodadesistencia001.php`, `pro1_proctranferint001.php`, `pro1_proctranferintand001.php`
- **3 outras**: `hab1_habitprograma004.php`, `pro1_relcgm002.php`, `pro1_relduploscgm002.php`, `pro3_inconsistenciaInss.php`, `pro4_canarquiv002.php`, `pro4_canceltransintlist.php`, `pro4_canceltranslist.php`, `pro4_consusuariodeptoRPC.php`, `pro4_mandespacho002.php`, `pro4_recebinterinfo.php`
- **4 classes**: `classes/db_arquivo_classe.php`, `classes/db_atendarea_classe.php`, `classes/db_atendareatec_classe.php`, `classes/db_atendemail_classe.php`, `classes/db_atendimento_classe.php`, `classes/db_atendimento_top_classe.php`, `classes/db_atendimentocadsituacao_classe.php`, `classes/db_atendimentolanc_classe.php`, `classes/db_atendimentomod_classe.php`, `classes/db_atendimentoorigem_classe.php`
- **6 lint**: `cad1_lote002.php`, `cad1_lote003.php`, `con1_contrib007.php`, `pro4_canarquiv002.php`

## O que NAO estava nesta rodada (por causa da sessao)

57 ERRO_AMBIENTE: 40+ prefixos de telas (`tela-run:*`) e os passos de POST/relatorio ficaram sem rodar porque a sessao
autenticada morreu no meio ("Sessao invalida"); 12 telas deram timeout no 5.6 (`rec2_espelhoponto002`, `edu4_*`,
`mer3_mer_nutriitem002`, `con4_gerenciadortarefas002`). **Por isso os 11 PDFs com 500 no 8.5 (catalogo de relatorios) nao
aparecem acima.** A bateria agora renova a sessao por login HTTP e retenta timeout 1 vez (commit `feat(regressao): bateria PHP
renova a sessao...`); os prefixos precisam ser re-rodados.

## Ruido corrigido
`roda_telas` reavalia DIVERGE 200x200: se os dois lados sao PDF e o TEXTO extraido e igual, vira IDENTICO (item 7). Nao
mascara nada que mude texto, status HTTP ou tamanho de pagina de erro.
