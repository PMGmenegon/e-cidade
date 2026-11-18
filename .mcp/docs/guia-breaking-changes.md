# Guia de quebras: PHP 7.4 → 8.5 e Laravel 8 → 12

Para quem migra o e-Cidade (gente e IA). A IA lê este guia pelo resource `ecidade://docs/breaking-changes`. Cada
item diz **o que quebra**, **em que versão**, **como achar** (padrão do `buscar_codigo_legado`) e **a correção
padrão**. O que está marcado **(verificado)** foi conferido nos contêineres `ecidade74_php74` (7.4.33) e
`ecidade74_php85` (8.5.12) em 17/11/2026.

## 0. O que a migração anterior ensinou (5.6 → 8.5, branch `regressao`)

A suíte já mediu uma migração deste mesmo código (gabarito PHP 5.6). Detalhes em `ecidade://regressao/triagem` e
`ecidade://regressao/decisoes`. O que vale levar:

1. **Duas causas mecânicas explicavam ~85% das 941 divergências**: `parse_str()` com 1 argumento e construtor
   estilo PHP 4. A terceira (`split`/`each`/`ereg`) ficava **escondida** atrás delas.
2. **Efeito cebola**: cada correção revela a próxima quebra da mesma tela. Uma tela que vira de "500" para "500 com
   outra mensagem" não é regressão nova: é a suíte enxergando mais. Rode a regressão **depois de cada passo**.
3. **Ordem que deu certo**: (1) `parse_str` em todo o código, inclusive as janelas `func_*`; (2) construtores PHP 4;
   (3) `split`/`each`/`ereg`; (4) erros de compilação e casos isolados; (5) triagem caso a caso com parâmetros reais.
4. **As janelas de pesquisa `func_*.php` (as "lupas") não entram na bateria PHP** e tinham o mesmo `parse_str`. A
   suíte pode ficar verde com as pesquisas quebradas: rode `--prefixo '^func_'` quando mexer nelas.
5. **"Aceitar" em `conhecidas.tsv` não conserta nada**: só silencia o alarme e manda funcionalidade quebrada para
   produção. Divergência nascida na migração se corrige.
6. **SQL que falha** (`pg_*` recebendo `false`): no 5.6/7.4 a tela seguia vazia em silêncio; no 8.x aborta. A
   correção é decisão de negócio (reproduzir o vazio ou mostrar erro claro).
7. A bateria abre as telas **sem parâmetros**: ela prova que a tela "abre igual", não que os números batem.

## 1. O que muda partindo do 7.4 (e não mais do 5.6)

- **Já quebrado no 7.4** (`split`, `ereg*`, `mysql_*`, `mcrypt_*` não existem no 7.4, **verificado**): o código que
  ainda os usa quebra **na referência também**. Na regressão aparece como erro igual dos dois lados
  (INCONCLUSIVO), não como DIVERGE. Corrigir é conserto de bug antigo; faça mesmo assim (comportamento novo =
  confira com o usuário).
- **Depreciado no 7.4 e fatal no 8.0** (o 7.4 avisa e segue; o 8.5 para): `parse_str` com 1 argumento, construtor
  PHP 4, `each`, `create_function`, `money_format`, `get_magic_quotes_*`, `$str{0}`, ternário aninhado sem
  parênteses, `implode($array, $sep)`, `array_key_exists` em objeto, `mktime()` sem argumentos. **Estes viram
  DIVERGE** na bateria 7.4 × 8.5. São a maior parte do trabalho.
- **A base 7.4 já veio com boa parte corrigida**: na varredura de 17/11/2026 há só ~256 construtores PHP 4 (eram
  ~600 classes na base 5.6), mas o `parse_str` de 1 argumento continua em milhares de telas. Números atuais: seção 7.

## 2. PHP 8.0 (o grosso das quebras)

| Quebra | Sintoma no 8.5 | Padrão MCP | Correção padrão |
|---|---|---|---|
| `parse_str($qs)` / `mb_parse_str($qs)` com 1 argumento | `ArgumentCountError: parse_str() expects exactly 2 arguments, 1 given` **(verificado)** → tela 500 | `parse_str_1_arg` | `parse_str($qs, $__qs); unset($__qs['this'], $__qs['GLOBALS']); extract($__qs);` |
| Construtor PHP 4 (`function cl_x()` na classe `cl_x`) | não é mais chamado **(verificado: `ok=0` no 8.5, `ok=1` no 7.4)** → propriedades nulas, `Call to a member function label() on null` | `construtor_php4` | renomear para `__construct`; `parent::cl_x()` → `parent::__construct()` |
| `each()`, `create_function()`, `money_format()`, `get_magic_quotes_*()`, `is_real()`, `fgetss()`, `hebrevc()`, `restore_include_path()`, `__autoload()` | `Call to undefined function` **(verificado)** | `each`, `create_function`, `removidas_php8` | `foreach`; closure; `NumberFormatter`/`number_format`; remover magic quotes; `is_float`; `strip_tags(fgets())`; `spl_autoload_register` |
| `$str{0}` | **erro de compilação** (`ParseError`, verificado): o arquivo inteiro para | `chaves_offset_string` | `$str[0]` |
| Ternário aninhado sem parênteses `a ? b : c ? d : e` | **erro de compilação** (o 7.4 só avisava) | — (use `validar_arquivo_php`, o `php -l` do 8.5 acusa) | parênteses explícitos, mantendo a associatividade do 7.4: `(a ? b : c) ? d : e` |
| `count(null)` / `sizeof` de não contável | `TypeError` **(verificado)** (7.4: warning e seguia) | `count_null` (baixa confiança: acha todos os `count($x)`) | `is_countable($x) ? count($x) : 0` ou `count($x ?? [])` só onde pode ser null |
| `pg_*` recebendo `false` (consulta que falhou) | `TypeError: pg_numrows(): Argument #1 ($result) must be of type PgSql\Result, false given` **(verificado)** | `pg_resultado_false` (só o caso aninhado `pg_numrows(db_query(...))`) | guardar o resultado e testar `=== false` antes; decisão de negócio sobre a mensagem |
| Comparação número × string | `0 == ""` e `0 == "abc"` passam a ser **false** (eram true) **(verificado)** | — (não dá para achar por regex) | revisar `==` entre número e texto em regras de negócio; a regressão é a rede de proteção |
| Aritmética com texto não numérico | `"abc" + 1` → `TypeError: Unsupported operand types: string + int` **(verificado)**; `"10abc" + 1` só avisa | — | converter/validar a entrada (`(int)`, `is_numeric`); em biblioteca (Agata: acumulador não inicializado) corrigir 1 vez na origem |
| `implode($array, ',')` (ordem invertida) | `TypeError` **(verificado)** | regex livre: `implode\(\s*\$\w+\s*,\s*['"]` | `implode(',', $array)` |
| `array_key_exists($k, $objeto)` | `TypeError` **(verificado)** | regex livre | `property_exists`/`isset` |
| `mktime()` sem argumentos | `ArgumentCountError` **(verificado)** | regex livre: `mktime\(\s*\)` | `time()` |
| `ReflectionParameter::getClass()` | depreciado **(verificado)** | `reflection_getclass` | `getType()` + `ReflectionNamedType` |
| `@` não silencia mais erro fatal; `match`/`mixed` viram palavras reservadas | fatal/compilação | — | `php -l` no 8.5 acusa nomes reservados |

## 3. PHP 8.1 a 8.4

| Versão | Mudança | Sintoma | Padrão MCP / correção |
|---|---|---|---|
| 8.1 | **pgsql devolve objetos** (`PgSql\Connection`, `PgSql\Result`) **(verificado)** | `is_resource($rs)` dá `false` e o código toma o caminho de erro | `is_resource_pgsql`: trocar por `$rs !== false` |
| 8.1 | **null em parâmetro não anulável de função nativa** (`strlen(null)`, `trim(null)`, `str_replace(..., null)`) | `Deprecated: Passing null to parameter...` **(verificado)**; vira erro numa versão futura e enche o log | `?? ''` na origem do valor; não silencie com `@` |
| 8.1 | `htmlspecialchars()`/`htmlentities()` escapam aspas simples por padrão (`'` → `&#039;`) **(verificado)** | HTML/valores de input diferentes | passe as flags explícitas se o 7.4 não escapava: `htmlspecialchars($s, ENT_COMPAT, 'ISO-8859-1')` |
| 8.1 | `strftime`/`gmstrftime`, `FILTER_SANITIZE_STRING` depreciados **(verificado)** | Deprecated | `strftime`, `filter_sanitize_string` |
| 8.1 | classes que implementam `ArrayAccess`/`Iterator`/`Countable` sem tipos de retorno | Deprecated ("Return type ... should be compatible") | declarar o tipo de retorno (compatível com 7.4 quando possível) ou `#[\ReturnTypeWillChange]` |
| 8.2 | **propriedades dinâmicas** (`$obj->campo_novo = 1` sem declarar) **(verificado)** | Deprecated em massa nas classes legadas | declarar a propriedade; em classe de dados genérica, `#[\AllowDynamicProperties]` |
| 8.2 | **`strtolower`/`strtoupper`/`ucfirst`/`ucwords` ignoram o locale** **(verificado: `ção` → `ÇãO` no 7.4 com locale pt_BR, `çãO` no 8.5)** | maiúsculas com acento **mudam** em telas, relatórios e chaves de busca da base LATIN1 | `mb_strtoupper($s, 'ISO-8859-1')` (o 7.4 com locale dava o mesmo) |
| 8.2 | `utf8_encode`/`utf8_decode` depreciados **(verificado)**; `"${var}"` depreciado **(verificado)** | Deprecated | `utf8_encode_decode` (`mb_convert_encoding`), `interpolacao_dolar_chave` (`{$var}`) |
| 8.3 | `get_class()`/`get_parent_class()` sem argumento depreciados **(verificado)** | Deprecated | `get_class($this)` / `static::class` |
| 8.4 | **nulo implícito** (`function f(Foo $x = null)`) **(verificado)** | Deprecated (vendor antigo também: Guzzle, lcobucci/jwt, PHPStan 1.x emitem isto no 8.5) | `nulo_implicito`: `?Foo $x = null` |
| 8.4 | `E_STRICT` depreciado **(verificado)**; `trigger_error(..., E_USER_ERROR)` depreciado | Deprecated | `e_strict`; lançar exceção no lugar de `E_USER_ERROR` |

## 4. PHP 8.5

| Mudança | Sintoma | Padrão MCP / correção |
|---|---|---|
| casts `(integer)`, `(boolean)`, `(double)`, `(binary)` depreciados **(verificado)** | Deprecated | `casts_nao_canonicos`: `(int)`, `(bool)`, `(float)`, `(string)` |
| operador crase `` `cmd` `` depreciado **(verificado)** | Deprecated | `shell_exec()` (e reveja: executar shell a partir de tela é risco) |
| apelidos `pg_numrows`, `pg_exec`, `pg_result`, `pg_fieldname`... emitem `deprecated since 8.0` **(verificado)** | Deprecated (funciona) | `pg_aliases`: nome atual com a mesma assinatura |
| novas funções nativas `array_first()`/`array_last()` **(verificado)** | o helper do Laravel de mesmo nome tem outra assinatura (`array_first($arr, $callback)`) | `laravel_helpers_globais`: use `Arr::first()` |

> Depreciação não quebra a tela, mas **enche o log** e vira erro na próxima major. A bateria PHP compara a saída:
> se o `display_errors` do alvo mostrar o aviso na página, vira DIVERGE. A paridade de ini está em
> `regressao/lab/php85/paridade-74.ini`.

## 5. Laravel 8 → 12 (suba uma major por vez)

Faça **9 → 10 → 11 → 12**, lendo o guia de upgrade oficial de cada uma, rodando a bateria `laravel` (golden master
gravado no Laravel 8) a cada passo. Depois de cada `composer update`, rode `analisar_composer`.

| Versão | Mudança | Como achar | Correção |
|---|---|---|---|
| 9 | PHP mínimo 8.0; Symfony 6; **Flysystem 3** (`Storage::put` etc. não lançam exceção por padrão; métodos do adapter mudaram) | `Storage::`, `getAdapter(`, `getDriver(` | testar upload/download; `'throw' => true` no disco se o código dependia de exceção |
| 9 | SwiftMailer → Symfony Mailer | `Swift_`, `->withSwiftMessage` | `->withSymfonyMessage` |
| 9 | `dispatchNow` removido | `laravel_dispatch_now` | `dispatchSync` |
| 9 | `fideloper/proxy` e `fruitcake/laravel-cors` embutidos | `analisar_composer` | middleware nativo `TrustProxies`/`HandleCors` |
| 10 | PHP mínimo 8.1; `$dates` removido | `laravel_dates_property` | `$casts` com `datetime` |
| 10 | `Bus::dispatchNow`, `Redirect::home()` e outros métodos depreciados removidos | guia oficial | — |
| 11 | PHP mínimo 8.2; **Doctrine DBAL removido**; `->change()` em migration exige repetir todos os modificadores | `doctrine_dbal` | `Schema::getColumns()`/`getIndexes()`; migration com a definição completa |
| 11 | Carbon 3 suportado; estrutura enxuta opcional (manter `app/Http/Kernel.php` é permitido) | — | não reestruture a aplicação na mesma tarefa |
| 12 | **Carbon 3 obrigatório**: `diffIn*` devolve `float` e **com sinal** | `carbon_diff_in` | `(int) abs($a->diffInDays($b))` onde o código esperava inteiro positivo |
| 12 | Symfony 7.x por baixo | `request_get` (baixa confiança) | `$request->input()`/`query()` |
| todas | helpers globais `array_*`/`str_*` (fora do framework desde o 6) | `laravel_helpers_globais` | `Arr::`/`Str::` |
| Passport | 10 → 11 removeu `Passport::routes()`; majors seguintes mudam tabelas/hashing de segredos | `passport_routes` | ler o UPGRADE.md do Passport a cada major; a bateria `laravel` cobre o fluxo de token (`casos/auth.yml`) |

## 6. Como verificar uma correção (sempre)

1. `validar_arquivo_php(caminho, versao="ambas")` — **até a virada o mesmo código roda no 7.4 e no 8.5**: a
   correção precisa compilar e funcionar nos dois (nada de sintaxe só do PHP 8 em `ecidade/`).
2. `validar_arquivo_php(caminho, ferramentas=["phpstan"], versao="alvo")` — o PHPStan no 8.5 já acusa, por exemplo,
   `Function parse_str invoked with 1 parameter, 2 required` **(verificado)**.
3. `rodar_regressao` no recorte da tela/rota e `ler_resultado_regressao`. IDENTICO = mesma resposta que o 7.4.
   INCONCLUSIVO/ERRO_AMBIENTE não aprovam nada.

## 7. Quanto ainda existe na base 7.4 (varredura estática de `ecidade/`, 17/11/2026)

Gerado com o catálogo do MCP (`buscar_codigo_legado`); conte de novo com `padroes_ja_corrigidos(contar_em="ecidade")`.
Número de ocorrências é teto (comentários e strings também casam).

| Padrão | Ocorrências | Arquivos | Efeito no 8.5 |
|---|---:|---:|---|
| `parse_str_1_arg` | 7.645 | 7.560 | **fatal** (tela 500) |
| `construtor_php4` | 256 | 205 | **comportamento** (construtor não roda) |
| `split` | 368 | 86 | já quebrado no 7.4 |
| `each` | 85 | 28 | **fatal** |
| `ereg` | 23 | 7 | já quebrado no 7.4 |
| `create_function` | 2 | 2 | **fatal** |
| `removidas_php8` | 30 | 7 | **fatal** (ou já quebrado no 7.4: `mysql_*`, `mcrypt_*`) |
| `chaves_offset_string` | 95 | 23 | **compilação** |
| `pg_resultado_false` | 183 | 110 | **fatal se a consulta falhar** |
| `is_resource_pgsql` | 253 | 87 | **comportamento** (só os de pgsql; o resto é arquivo) |
| `reflection_getclass` | 0 | 0 | — |
| `nulo_implicito` | 285 | 206 | depreciado |
| `utf8_encode_decode` | 1.800 | 376 | depreciado |
| `strftime` | 55 | 12 | depreciado |
| `filter_sanitize_string` | 8 | 3 | depreciado |
| `e_strict` | 9 | 6 | depreciado |
| `interpolacao_dolar_chave` | 1.286 | 340 | depreciado |
| `casts_nao_canonicos` | 483 | 174 | depreciado |
| `pg_aliases` (ruidoso) | 88.914 | 5.684 | depreciado |
| `count_null` (ruidoso, teto) | 24.117 | 6.105 | **fatal só onde o valor for null** |
| `laravel_helpers_globais` | 2 | 2 | Laravel |
| `laravel_dates_property` | 21 | 21 | Laravel 10 |
| `passport_routes` | 1 | 1 | Passport 11 |
| `carbon_diff_in` | 1 | 1 | Laravel 12 (Carbon 3) |
| `request_get` (ruidoso) | 920 | 147 | Symfony 7 (confira) |
| `laravel_dispatch_now`, `doctrine_dbal` | 0 | 0 | — |
