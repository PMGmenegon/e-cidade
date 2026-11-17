# `split()` no PHP 8.5: o polyfill do vendor faz `explode` (T-040, 13/11/2026)

Pergunta: `split()` não existe no PHP 7+; no 8.5 ele vem de um polyfill do vendor que faz
`explode()`. Quantas chamadas mudam de sentido, quais pontos de entrada nem chegam ao polyfill, e o polyfill cobre
mais alguma função trocando regex por texto? **Só medição** — nenhum arquivo do sistema nem o polyfill foi alterado.
Medido sobre a `laravel/integracao` em `1f1b8258d`.

**Resposta curta:** **2.309 chamadas** a `split()` fora de `vendor/` (em 675 arquivos). **2.261 são iguais** nos dois
runtimes (padrão literal sem metacaractere: 25 valores distintos, saída idêntica conferida), **41 divergem em silêncio**
(7 padrões regex distintos; no 8.5 a string não é separada) e **7 têm padrão em variável**. Das 48, só uma já
roda no 8.5: a do resumo da Solicitação de Compra (`fpdf151/impmodelos/mod_imprime11.php:151`), que duas telas servidas
pelo 8.5 usam com o modelo fixo no código; ela foi corrigida à parte (`preg_split`, uma linha; registro em
`split-mod-imprime11.md`). As outras 47 estão em telas servidas pelo 5.6, janelas `func_*` ou dependências: **40 das 41
divergentes ainda não estão no ar**; aparecem quando essas telas forem para o 8.5. Pela web todo pedido carrega o
autoload; fora dela, o único ponto de entrada com `split` é `bin/dbportal_help.php` (CLI), que morre no 8.5.
O polyfill só define `split`; `spliti`, `ereg*`, `eregi*` e `sql_regcase` não existem no 8.5 (fatal, não silencioso).
A lista completa está em `split-polyfill-t040-chamadas.tsv` (ao lado deste arquivo).

## O polyfill

`vendor/dbseller/legacy` **v1.1.1** (`205b87f316`), exigido por `ecidade/composer.json` (`"dbseller/legacy": "^1.0"`) e
carregado pelo `autoload.files` do composer (`vendor/composer/autoload_files.php`), em quatro arquivos:

| Arquivo | Condição | Define |
|---|---|---|
| `bootstrap/PHP_53.php` | PHP ≥ 5.4 | `session_register`, `session_unregister`, `session_is_registered`; emula `$_ENV`, os `$HTTP_*_VARS`, `register_globals` e `magic_quotes_gpc` |
| `bootstrap/PHP_54.php`, `PHP_55.php` | — | nada (arquivo vazio) |
| `bootstrap/PHP_56.php` | PHP ≥ 7.0 e `split` inexistente | `function split($pattern, $string) { return Emulate::split(...); }` → `src/PHP56/Emulate.php`: `return explode($pattern, $string);` |

Consequências do código do polyfill: (1) o padrão é tratado como **texto**, não como regex POSIX; (2) a assinatura tem
**2 parâmetros** — o 3º (`limit`) do `split` original seria descartado em silêncio (medido: **nenhuma** chamada passa 3
argumentos); (3) só existe com o autoload do composer carregado.

Medido nos dois runtimes, com o autoload carregado (`function_exists`):

| Função | 5.6 | 8.5 |
|---|---|---|
| `split` | nativa | polyfill (`explode`) |
| `spliti`, `ereg`, `eregi`, `ereg_replace`, `eregi_replace`, `sql_regcase` | nativas | **não existem** (fatal ao chamar) |
| `session_register`, `session_unregister`, `session_is_registered` | nativas | polyfill (PHP_53) |

Das funções que o polyfill cobre, **só `split` troca regex por texto**. As de sessão não envolvem regex.
`ereg*`/`spliti`/`sql_regcase` não são cobertas: no 8.5 param com `Call to undefined function` (é a regra
`EregToPregMatchRector` da T-004, `rector-varredura-t004.md`). Nenhum arquivo versionado define `split`, `spliti`,
`ereg*` ou `sql_regcase` (`git grep "function +(split|spliti|ereg|...) *\("` = 0).

## Como reproduzir

```bash
# dois containers (PHP 5.6 e 8.5) que montam ecidade/ em /var/www/html; nada aqui usa o banco
bash scratchpad/split_t040.sh <container_56> <container_85>
```

| Script (`scratchpad/`) | Papel |
|---|---|
| `split_varredura.php` | tokenizador do PHP (`token_get_all`): cada chamada `split(`/`spliti(` que não é método (`->`, `::`), definição (`function`) nem `new`; separa os argumentos no nível de cima, lê o valor do literal com a semântica de aspas do PHP e classifica |
| `split_compara.php` | o mesmo `split()` nos dois runtimes, com o autoload carregado como numa tela: 5.6 = POSIX nativo, 8.5 = polyfill |
| `split_iguais.php` | cada valor "igual" distinto contra 4 entradas (`a<p>b<p><p>c`, `<p>`, vazio, sem o padrão), nos dois runtimes |
| `split_conferegrep.php` | o tipo do token das linhas que o grep de partida acha e o tokenizador não |
| `split_t040.sh` | roda tudo; saídas em `ecidade/tmp/t040/` |

Coluna `valor` do `.tsv`: o valor real do literal, escapado com `addcslashes` (barra invertida aparece dobrada:
`\\.` é o padrão `\.`; quebra de linha aparece como `\n`).

## Toda chamada, classificada

| Classe | Regra | Chamadas | Arquivos |
|---|---|---|---|
| igual | literal sem nenhum de `. \| \ [ ] ( ) * + ? ^ $ { }` (e não vazio) | **2.261** | 629 |
| diverge | literal com metacaractere | **41** | 40 |
| desconhecido | padrão não literal | **7** | 6 |
| — | `spliti(` | 0 | 0 |
| — | `split` com 3º argumento | 0 | 0 |

Tokenização idêntica no 5.6 e no 8.5 (`split56.tsv` = `split85.tsv`, byte a byte).

**Igual:** 25 valores distintos; os mais comuns `#` (1.778), `-` (285), `_` (57), `,` (27), `/` (17), `P` (13),
`\n` (11), `N` (10). Conferência: os 25 × 4 entradas = 100 casos com saída **idêntica** no 5.6 (`split` POSIX) e no
8.5 (`explode`).

**Desconhecido (7):** resolvidos pela leitura do código —
- `bin/dbportal_help.php:263` e `:315`, `split("$br", …)` com `$br = '<br>'` (linha 5): sem metacaractere, seria igual —
  mas o arquivo é CLI e não carrega o autoload (ver "Pontos de entrada sem autoload").
- `integracao_externa/{gissonline/lib,iptu2agua/libs,portal_transparencia/libs,sigcorp/libs,webiss/libs}/db_libconversao.php:37`,
  `split($matriz[0], $texto)`, onde `$matriz[0]` é o casamento de `ereg(',[ ][0-9]*[ ]', …)` (vírgula, espaços e dígitos:
  sem metacaractere). Mas a linha anterior chama `ereg()`, que no 8.5 não existe: a função morre antes do `split`.
  Nenhum arquivo versionado inclui esses 5 `db_libconversao.php` (só `gissonline/lib/db_inicio_script.php` cita o seu,
  e ninguém inclui esse `db_inicio_script.php`).

**Diverge (41), por padrão:**

| Padrão (fonte) | Chamadas | Onde |
|---|---|---|
| `"\?"` | 17 | `dbforms/db_*.php` (17 telas de lista `db_lov`: `db_cgm`, `db_iptubase`, `db_arrecad`, `db_caixa`, …) |
| `"\|"` | 11 | 8 `func_*` (`func_cgmrechumano`, `func_cgmtipo`, `func_cgs`, `func_conplanoexelanc`, `func_contarefa`, `func_dependete`, `func_nomealt`, `func_veicnomealt`), `cad3_consultaitbi002`, `cad3_consultaitbinew002`, `classes/db_db_consultacep_classe.php` |
| `'\.'` / `"\."` | 8 | `cad4_geracarneiptutxt{,_arapiraca,_cli,_eldorado,_guaiba}.php` (`$j40_refant`, a mesma linha já corrigida em `EmissaoTXT.php`), `con4_processaconsistencia.php`, `func_consbens001.php`, `reciboitbinovo.php` |
| `'[/.-]'` | 2 | `func_empempenhoaut001.php:171,177` (datas) |
| `"[\n\r]"` | 1 | `fpdf151/impmodelos/mod_imprime11.php:151` |
| `"\("` | 1 | `con5_verificaclasse001.php:92` |
| `"[\|]"` | 1 | `func_interval.php:54` |

## Cada padrão que diverge, 5.6 × 8.5

`split_compara.php` com o autoload carregado (como numa tela). Saída literal (`json_encode`):

| Padrão | Entrada | 5.6 (`split` POSIX) | 8.5 (polyfill `explode`) |
|---|---|---|---|
| `\?` | `con2_relatorio.php?ano=2026&mes=11` | `["con2_relatorio.php","ano=2026&mes=11"]` | `["con2_relatorio.php?ano=2026&mes=11"]` |
| `\?` | `sem interrogacao` | `["sem interrogacao"]` | `["sem interrogacao"]` |
| `\|` | `10\|20\|30` | `["10","20","30"]` | `["10\|20\|30"]` |
| `\.` | `1.234.567` | `["1","234","567"]` | `["1.234.567"]` |
| `\.` | `01.02` | `["01","02"]` | `["01.02"]` |
| `[/.-]` | `13/11/2026` | `["13","11","2026"]` | `["13/11/2026"]` |
| `[/.-]` | `2026-11-13` | `["2026","11","13"]` | `["2026-11-13"]` |
| `[/.-]` | `13.11.2026` | `["13","11","2026"]` | `["13.11.2026"]` |
| `[\n\r]` | `linha1\r\nlinha2\nlinha3` | `["linha1","","linha2","linha3"]` | `["linha1\r\nlinha2\nlinha3"]` |
| `\(` | `funcao(arg)` | `["funcao","arg)"]` | `["funcao(arg)"]` |
| `[\|]` | `a\|b\|c` | `["a","b","c"]` | `["a\|b\|c"]` |
| `\|` sem barra (sem uso no PHP) | `a\|b\|c` | `false` (regex vazia: `REG_EMPTY`) | `["a","b","c"]` |
| `.` sem barra (sem uso no PHP) | `a.b.c` | `["","","","","",""]` (`.` casa qualquer caractere) | `["a","b","c"]` |

Em todos os 7 padrões reais o 8.5 **não separa**: devolve a string inteira num elemento só, sem erro nem aviso. O
código seguinte recebe outra coisa: `func_conplanoexelanc.php:79` separa `$funcao_js` e usa `$funcao_js[0]` como nome
da função JavaScript que devolve o resultado à tela que abriu a janela; no 8.5 o `[0]` é a string inteira, com os
`|`, e a chamada JavaScript gerada quebra. `"|"` e `"."` sem barra não aparecem em
nenhuma chamada PHP: uma contagem inicial com grep (`"|"` 37, `"."` 10) vinha do grep, que pega `.split("|")` de
JavaScript dentro das telas; medidos assim mesmo, e o 8.5 diverge também neles.

## Pontos de entrada sem autoload

**Pela web, todos carregam.** `ecidade/.htaccess` reescreve **todo** pedido (sem `!-f`) para `FrontController.php`,
que despacha para `api/api.php`, `public/index.php` ou `app.php`; o `app.php:21` faz `require_once bootstrap.php`
**antes** do `require_once($filePath)` da tela (linha 173), e o `bootstrap.php:26` carrega `vendor/autoload.php`. Os
arquivos versionados que carregam o autoload: `api/api.php`, `app.php`, `bootstrap.php`, `bootstrap/autoload.php`,
`cli.php`, `phinx.php`, `public/index.php`, `tests/suite/bootstrap.php`.

**Fora da web** (CLI, cron, `.sh`), dos 675 arquivos com `split`:

| Arquivo | Como roda | Autoload | Alcançável |
|---|---|---|---|
| `bin/dbportal_help.php` (2 chamadas) | CLI à mão (`<?` + `include("vihelp.conf")`, grava `/tmp/dbportal_help.html`); nenhum `.sh` nem arquivo versionado o chama | não | só à mão. Medido: `php -r 'split("#","a#b");'` no 8.5 sem autoload → `Call to undefined function split()`; no 5.6 roda |
| `integracao_externa/*/db_libconversao.php` (5) | bibliotecas das integrações (o `webiss/executa.sh` roda `php -q integracao_externa/webiss/iss4_webiss001.php`, que **não** carrega o autoload) | não | nenhum arquivo versionado as inclui: `git grep -n "db_libconversao\|db_inicio_script" -- 'ecidade/*.php'` só acha os `include` das pastas `auditoria/lib` e `debitos/lib` (cópias próprias delas, sem `split`) e os `include_once` de `gissonline/lib/db_inicio_script.php` e de `db_inicio_script.php` da raiz, que ninguém inclui (e na raiz não há `db_libconversao.php`); e o `ereg()` da linha anterior já para no 8.5 |

Os demais 668 arquivos (raiz, `classes/`, `dbforms/`, `forms/`, `model/`, `libs/`, `fpdf151/`, `imagens/`) rodam pela
web e recebem o polyfill. Ressalva: dois geradores de código escrevem `split("#", …)` em arquivos que serão executados
depois — `sys4_criaclasse001.php` (classes `db_*_classe.php`) e `con2_gerelatorio005.php` (relatórios gerados);
padrão `#`, igual nos dois.

**Onde as 48 não iguais rodam hoje:** nenhuma está num arquivo do `location`/`map` do proxy, mas uma é alcançada por
telas dele (abaixo). As telas da raiz
(`cad*`, `con*`, `reciboitbinovo`) e as `func_*` são servidas pelo 5.6; os `dbforms/db_*.php` são listas abertas pela
própria URL (`db_lov(..., "db_cgm.php?..."`), também pelo 5.6. Dependências: `classes/db_db_consultacep_classe.php` é
incluída só por `func_cep.php` (5.6); `fpdf151/impmodelos/mod_imprime11.php` é carregada **dinamicamente** por
`fpdf151/impcarne.php:1370` (`mod_imprime".$this->impmodelo.".php"`), e o modelo 11 é **fixo no código** em duas telas
que o 8.5 serve (prefixos `com` e `pes` no `location`): `new db_impcarne($pdf, '11')` em `com2_emitesolicita002.php:347`
e `pes1_rhempemitesolfolha002.php:127`. Essa chamada **já está no ar** no 8.5; foi corrigida à parte (registro em
`split-mod-imprime11.md`).

## Outra branch já tratou?

- Nenhuma branch local ou do `origin` (`*-migrado`, `base-php84`, tarefas, `nucleo/correcoes-transversais`) altera
  algum dos 48 arquivos com chamada não igual (`git diff --name-only laravel/integracao...<branch>` = 0 em todas; a
  Assistência Social revertida também não os toca).
- Precedente já integrado: `src/Tributario/Cadastro/Iptu/EmissaoTXT.php:768` (Patrimonial, `area-patrimonial.md`,
  "Dado errado em silêncio"): `split('\.', …)` → `explode('.', …)`, idêntico ao 5.6 em 7 casos. É o mesmo trecho das 5
  cópias `cad4_geracarneiptutxt*.php`, que ficaram de fora porque não são telas roteadas.
- Nas áreas portadas, o Rector (`EregToPregMatchRector`) converteu `split` → `preg_split` (281 só no `arr`), por isso
  sobram só 15 chamadas em arquivos do `location`, todas iguais.
- As chamadas `split` de `duplos.php`, `duploscgs.php`, `con1_contrib007.php` e `dbforms/db_virafolha.php` (arquivos
  que ainda não compilam no 8.5, `lint-universo.md`) têm padrões `-` e `_`: são iguais nos dois runtimes. Num script
  que não carrega o autoload, como um harness de teste, elas morrem no 8.5 com `Call to undefined function split()`.

## Conferência à mão (5 ocorrências)

| `.tsv` | Linha do fonte | Confere |
|---|---|---|
| `classes/db_workflowativexecucaoatributovalor_classe.php:401` `"#"` igual | `$campos_sql = split("#",$campos);` | sim |
| `cad4_geracarneiptutxt_guaiba.php:630` `'\.'` diverge | `$sqlsub = split('\.', $j40_refant);` | sim |
| `classes/db_tarefaparam_classe.php:336` `"#"` igual | `$campos_sql = split("#",$campos);` | sim |
| `func_conplanoexelanc.php:79` `"\|"` diverge | `$funcao_js = split("\|",$funcao_js);` | sim |
| `func_interval.php:54` `"[\|]"` diverge | `$arr_valorvariavel = split("[\|]",$valorvariavel);` | sim |

E o grep de partida (`git grep -nE '(^|[^_a-zA-Z>:])split *\('`, sem `.split(` de JS) contra o tokenizador: o grep acha 2.375 linhas (sem `.split(` de JS), o tokenizador
2.309; as 66 a mais são 50 comentários, 15 strings (o código gerado acima) e 1 `preg_split`. Nenhuma chamada real
fora da lista; nenhuma linha do tokenizador fora do grep.

## Classificação: defeito de migração, não herdado

A divergência **não existe no 5.6**: é defeito de migração do runtime novo (o polyfill), não comportamento herdado do
legado. Caminhos possíveis, para decisão (nada foi aplicado):
corrigir as 41 chamadas como o `EmissaoTXT.php` (`explode` do separador literal ou `preg_split`, compatível com os dois
runtimes), ou trocar o polyfill por um que traduza a regex POSIX (é `vendor/`, área laravel).

## Lacunas

- O tokenizador não vê `split` chamado por nome dinâmico (`$f = 'split'; $f(...)`, `call_user_func('split', …)`):
  `git grep "['\"]split['\"]"` não acha nenhum caso fora de JS, mas não foi provado para toda forma.
- Arquivos não `.php` com código PHP (`*.phpant`, `*.php_certa`, `*.phpxx`, cópias antigas) ficaram de fora: o Apache
  não os executa como PHP.
- "Alcançável" é estático (quem inclui quem, quais telas o proxy manda ao 8.5); só o `mod_imprime11.php` foi seguido
  até a tela que o usa.
