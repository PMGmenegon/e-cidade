# Varredura da sintaxe uniforme de variáveis (`$$a[...]` e formas parecidas) — T-037, 13/11/2026

**Só medição; nada foi corrigido.** `$$a[$i]` no 5.6 é `${$a[$i]}`; no PHP 7+ é `${$a}[$i]` (sintaxe uniforme). Compila nos dois,
`php -l` não pega, e o resultado muda em silêncio (regressão silenciosa: o código compila e roda nos dois, com resultado diferente). Esta varredura cobre o que o
`php -l` da T-003 não vê.

## Como reproduzir

```bash
bash scratchpad/varre_variaveis.sh <container-php85> <pasta-saida>     # ~3 min; usa scratchpad/varre_variaveis.php
```

`varre_variaveis.php` usa o **tokenizador** (`token_get_all`, ignora comentários e strings) em todo `*.php` sob `ecidade/` fora de
`vendor/` (**32.855 arquivos** no master; a árvore da integração é parecida) e emite `arquivo<TAB>linha<TAB>forma<TAB>trecho`.
Formas (as 4 que mudam de sentido + as reescritas do Rector):

| Forma | Código | 5.6 | 7+ |
|---|---|---|---|
| `VV` | `$$a[..]` / `$$a{..}` (também `global $$a[..]`) | `${$a[..]}` | `${$a}[..]` — **muda** |
| `OBJ` / `OBJC` | `$o->$p[..]` / `$o->$p[..](..)` | `$o->{$p[..]}` | `($o->$p)[..]` — **muda** |
| `STC` | `Cls::$p[..](..)` | método estático de nome `$p[..]` | `($p)[..]()` — **muda** |
| `VVB` / `OBJB` / `STB` | `${expr}[..]` / `$o->{expr}[..]` / `Cls::${expr}[..]` | igual ao 7+ | igual — **só importa se era `VV`/`OBJ` no master** |

Teste do próprio scanner: arquivo com as 11 formas (+ `"$$a[0]"` em string e `// $$a[1]` em comentário, que não contam) devolve as
mesmas linhas nos tokenizadores do 5.6 e do 8.5. Dados: `varredura-variaveis-ocorrencias.tsv` (150 da integração + 174 do master).

## Resultado na integração (`laravel/integracao`, 13/11)

Zero aparece como zero: **`$$a{..}`: 0; `Cls::$p[..]()` (STC): 0; `$o->$p[..]()` (OBJC): 0**. Restam:

| Forma | Ocorrências | Arquivos |
|---|---|---|
| `VV` (`$$a[..]`) | 51 (50 linhas) | 10 |
| `OBJ` (`$o->$p[..]`) | 51 | 10 |
| `VVB` (`${$a}[..]`) / `OBJB` | 38 / 10 | 8 / 6 |

`php -l` **nos dois runtimes: 34/34 arquivos com ocorrência compilam** (por isso o lint não os acusa).

### `VV` — muda de sentido (10 arquivos)

| Arquivo (linhas) | Qtd | Dono (provável, pelo prefixo) | Alcançável? |
|---|---|---|---|
| `duplos.php` (1473-1532), `duploscgs.php` (483-543) | 12+12 | Tributário (CGM duplicado) | CLI (não é tela). `db_fieldsmemory1`; tratado na T-020 |
| `func_consbens001.php` (140-210) | 8 | Patrimonial (bens) | incluído por `func_consbens.php`/`func_consbensdepart.php` (lookups de menu) |
| `libs/db_stdlib.php` (880, 1361-1407) | 6 | núcleo | só nos `echo` de depuração (`$mostravar`/`$verNomeIndices == 2`); **as atribuições do núcleo já usam `${$matriz[$i]}`** (874-875) |
| `dbforms/db_classes_criaiframe.php` (166, 173) | 2 | núcleo | sem referência (órfão) |
| `dbforms/db_classes_iframe_alterar_excluir.php` (277, 292, 306) | 3 | núcleo | incluído por `db_classesgenericas.php` (telas com grade A/E) |
| `dbforms/db_classes_iframe_seleciona_2005.php` (180, 204) | 2 | núcleo | sem referência (órfão) |
| `ate2_confereatend002.php` (280, 283) | 2 | Configuração (`ate`) | incluído por `ate2_confereatendaba1.php` |
| `con2_lrfimpostossaude002_2007.php` (778, 976) | 2 | Financeiro (LRF) | sem referência (versão 2007 órfã) |
| `con3_acount.php` (197, 199) | 2 | Configuração (área concluída; não alterado) | **tela de menu** (`db_itensmenu.funcao`) |

### `OBJ` — `$o->$p[..]`: 10 arquivos, nenhum mudou desde o master

| Arquivo (linhas) | Qtd | Dono (pelo prefixo) | Alcançável? |
|---|---|---|---|
| `edu2_listaoficial002.php` (401) | 2 | Educação | **tela de menu** via `edu2_listaoficial001.php` |
| `edu4_censoescolar.RPC.php` (127, 144, 178, 224) | 8 | Educação (censo) | chamado por JavaScript a partir de `edu1_turmacenso001.php`, `edu4_exportarcensolayout001.php`, `edu4_verificaexportacaocenso001.php` |
| `hip2_criticadados002.php` (139-143) | 4 | Saúde (Hiperdia) | **tela de menu** via `hip2_criticadados001.php` |
| `model/educacao/censo/censo2015/DadosCensoDocente2015.model.php` (737, 746, 755) | 3 | Educação (censo 2015) | classe carregada por nome, sem referência ao arquivo |
| `model/pessoal/arquivos/siprev/ArquivoSiprevEscritorXML.model.php` (146, 171, 172, 179) | 4 | Recursos Humanos (SIPREV) | classe carregada por nome, sem referência ao arquivo |
| `db_libconversao.php` em 5 cópias de `integracao_externa/{gissonline,iptu2agua,portal_transparencia,sigcorp,webiss}/` (6 por cópia) | 30 | integração externa | scripts de conversão fora do menu |

Soma: 2 + 8 + 4 + 3 + 4 + 30 = 51. Mesma forma no master. Efeito medido em 2 trechos (próxima seção): os dois mudam de resultado.

## Diferença medida entre 5.6 e 8.5 (trechos isolados das linhas reais)

| Trecho | 5.6 | 8.5 |
|---|---|---|
| `func_consbens001.php:140-141`: `$$var[$i] = substr(...)` e leitura | `cla0=12 cla1=345` (variáveis criadas) | `NAO_DEFINIDA` nas duas |
| `db_classes_criaiframe.php:166`: `$$quais_chaves[$ww]` (chaves do botão A/E) | `,"A","B"` (valores das chaves) | `,"12","345"` (lê a variável errada) |
| Rector, `prot1_cadcgm001.php:120`: master `$$camp[$f]` × integração `${$camp}[$f]` | master `FULANO`; integração **vazio** | os dois **vazios** |
| `OBJ`, `edu4_censoescolar.RPC.php:127`: `isset($oArquivo->$aPropriedade[4]) ? urlencode(...) : ''` com `$aPropriedade[4] = 'nome_aluno'` e `$oArquivo->nome_aluno = 'FULANO'` | `'FULANO'` | `''` (lê a propriedade `Array`, que não existe) |
| `OBJ`, `hip2_criticadados002.php:142`: `$oDados->$aCampos[0]` com `$aCampos[0] = 'codigo'`, `$oDados->codigo = '42'` | `'42'` | `NULL` |

(O terceiro mostra que a reescrita do Rector troca o sentido já no 5.6; ver abaixo.) A réplica de `db_fieldsmemory1` inteira está
em `lint-universo.md` (T-020).

## O que as branches de área já corrigiram

Contado com o mesmo scanner nas 7 `origin/*-migrado` e `origin/base-php84`: **nenhuma corrigiu um `VV`**; elas só *reescreveram* (Rector).
A única correção real está na **integração**: `calculoiptu.php` e `calculoissqnfixo.php` (12 `VV` cada no master, 0 hoje; T-019).
`tests/suite/amostra/VariavelVariavelMatrizTest.php` existe (amostra da suíte), mas é só teste.

## Reescritas do Rector `$$x[..]` → `${$x}[..]` (mudam de sentido nos **dois** runtimes)

Comparado com `origin/master` (5.6 original): arquivo a arquivo, `VV` no master e `VVB` na integração:

| Arquivo | Ocorrências | Entrou na branch | Alcançável? |
|---|---|---|---|
| `prot1_cadcgm001.php`, `prot1_cadcgm002.php` | 2 + 2 (`$$camp[$f]`) | `1tributario-migrado` | **menu** (`db_itensmenu`) e `forms/db_frmcgm.php` |
| `pro2_duploscgm002.php` | 13 (`$$campos_where[$ii]`) | `4patrimonial-migrado` | acionado por `pro2_duploscgm001.php` (menu) |
| `con2_lrfimpostossaude002.php` | 2 (`$$desp_p[1]`) | `5financeiro-migrado` | incluído por `con2_lrfimpostossaude011.php`/`lrfresumido002*` |
| `sau1_cgm001.php`, `sau1_cgm002.php` | 2 + 2 | `6saude-migrado` | `sau1_cgm001` incluído por `sau1_cgs000/001/002` |
| `sau2_cgsduplos002.php` | 13 (`$$campos_where[$ii]`) | `6saude-migrado` | acionado por `sau2_cgsduplos001.php` (menu) |

**7 arquivos** (o relatório do Rector em simulação, T-004, listava 6; o sétimo é `sau2_cgsduplos002.php`). `model/relatorioContabil.model.php` tem 2 `${$sVarNome}[$iCodigoLinha]` mas **já era assim no master**: não é
reescrita. Os `OBJB` (10, em 6 arquivos) também são idênticos ao master (nenhum virou outra coisa). A bateria 5.6 × 8.5 **não pega**
essas reescritas, porque as duas execuções leem o mesmo código.

## `str_contains` e `setcookie` com opções

- **`str_contains(`**: 8 usos em 7 arquivos (`con4_dbhelp.RPC.php:36`, `extension/package/Desktop/Model/Menu.php:347`,
  `forms/db_frmrhcedencia.php:84,176,195`, `func_lab_setorexame.php:44`, `src/RecursosHumanos/ESocial/Integracao/ESocialEnvio.php:461,471`,
  `src/RecursosHumanos/Pessoal/Repository/SagresRepository.php:1041`). **Todos já estão no `origin/master`: não são do Rector.**
  `str_contains` não existe nativo no 5.6; ele funciona porque o **vendor do Laravel 5.4 define o helper**
  (`vendor/laravel/framework/src/Illuminate/Support/helpers.php`; medido: `function_exists('str_contains')` = não antes do autoload, sim depois).
  No 8.5 de hoje o **nativo vence**: `helpers.php:765` só define o helper se `function_exists('str_contains')` for falso (medido: origem
  `helper Laravel` no 5.6, `nativo` no 8.5). A diferença entre os dois está na agulha vazia ou nula:

  | `str_contains('Matricula(s): 123, ', …)` | 5.6 (helper) | 8.5 (nativo) |
  |---|---|---|
  | `''` | `false` | `true` |
  | `null` | `false` | `true` (com aviso de depreciação) |
  | `'123'` / `'9'` | `true` / `false` | `true` / `false` |

  Classificação por uso: `ESocialEnvio.php:461` e `:471` usam agulha variável (`$remunPerAnt->matricula`, `$remunPerApur->matricula`), mas só
  depois de `!empty(...)`; `empty('')`, `empty(null)` e `empty('0')` são `true` nos dois runtimes, então **a agulha vazia ou nula nunca chega**
  e esses dois usos dão o mesmo resultado. Os outros 6 usos têm agulha literal não vazia (`'http'`, `'web/'`, `'-'` ×3, `'la23_i_codigo'`, `'.'`):
  mesmo resultado. Ou seja, **nenhum dos 8 usos difere hoje**; a diferença só voltaria se alguém passar agulha vazia ou nula sem o `!empty`.
- **`setcookie(` com array de opções**: **0** (os 8 usos em `login.rpc.php`, `SkinService.service.php` e `src/V3/Window/Session.php` passam
  argumentos escalares). Nada da regra `SetCookieRector` ficou no código.

## Classificação

Tudo o que a varredura lista como `VV`, `OBJ` e reescrita do Rector **funciona no 5.6 e muda de resultado no runtime novo**, inclusive o
que já vem do `origin/master`. Portanto são **defeitos da migração** (nenhum já quebrava no 5.6), e cada grupo precisa de correção no
arquivo do dono:

| Grupo | Arquivos (ocorrências) | Dono | Problema |
|---|---|---|---|
| `$$a[..]` do master, ainda não corrigidos | `func_consbens001.php` (8), `ate2_confereatend002.php` (2), `con2_lrfimpostossaude002_2007.php` (2), `dbforms/db_classes_criaiframe.php` (2), `dbforms/db_classes_iframe_alterar_excluir.php` (3), `dbforms/db_classes_iframe_seleciona_2005.php` (2), `libs/db_stdlib.php` (6, só `echo` de depuração) | Patrimonial / Configuração / Financeiro / núcleo | lê `${$a}[..]` em vez de `${$a[..]}`; o núcleo já usa a forma certa nas atribuições (`db_stdlib.php:874-875`) |
| `$$a[..]` em tela de menu de área concluída | `con3_acount.php` (2) | Configuração | idem; área entregue, não alterada nesta etapa |
| `$$a[..]` em CLI | `duplos.php` (12), `duploscgs.php` (12) | Tributário | tratado na T-020 |
| Reescritas do Rector `${$x}[..]` (7 arquivos, 36 ocorrências) | `prot1_cadcgm001/002` (2+2), `pro2_duploscgm002` (13), `con2_lrfimpostossaude002` (2), `sau1_cgm001/002` (2+2), `sau2_cgsduplos002` (13) | Tributário / Patrimonial / Financeiro / Saúde (branch que introduziu) | o resultado mudou **também no 5.6**; a bateria 5.6 × 8.5 não pega |
| `$o->$p[..]` (51 em 10 arquivos) | tabela da seção `OBJ` | Educação / Saúde / RH / integração externa | lê `($o->$p)[..]` em vez de `$o->{$p[..]}` |
| `str_contains` (8 usos) | seção acima | — | nenhum dos 8 difere hoje (agulha literal ou protegida por `!empty`) |

## Lacunas

- Efeito medido em 5 trechos (3 de `$$a[..]`/Rector e 2 de `$o->$p[..]`); os outros usos de `OBJ` e as telas de `ate2`/`con2_lrf…_2007` não foram executados.
- O scanner não olha `eval`, strings de código nem `.inc`/`.phtml`; só `*.php`.
- Dono = pelo prefixo e pela branch onde a forma apareceu; não consultei autoria por pessoa.
