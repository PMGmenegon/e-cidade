# Handler de erro e Logger do V3 no PHP 8 (T-026)

> 13/11/2026. Origem: achados da T-009 (`testes-inventario.md`): dois testes do handler falhavam só no 8.5
> (`ErrorTest::testHandleWithoutReporting`, `ShutdownTest::testHandleExpectNothing`) e o `LoggerTest` estava em
> `lacunas.lista`. Defeito de migração (passa no 5.6, quebra no 8.5); a correção reproduz o comportamento do 5.6.

## Achado

| # | Onde | No 5.6 | No PHP 8 |
|---|---|---|---|
| 1 | `src/V3/Error/Handler/Error.php`, `_handle($type, $message, $file, $line, $context)` | o callback do `set_error_handler` recebe 5 argumentos | o `$errcontext` saiu do PHP 8: o callback recebe 4 → `ArgumentCountError` dentro do handler, e o erro vira fatal |
| 2 | `Error::handle()`, `$suppress = error_reporting() === 0` | dentro do `@` o `error_reporting()` é `0` → suprimido | dentro do `@` o `error_reporting()` mantém os bits fatais (`E_ERROR \| E_CORE_ERROR \| E_COMPILE_ERROR \| E_USER_ERROR \| E_RECOVERABLE_ERROR \| E_PARSE` = 4437): todo erro suprimido com `@` deixaria de ser suprimido e iria para o evento `app.error` (gravado no `error.log`) |
| 3 | `src/V3/Extension/Logger.php`, `setFile()` cria `$this->filePath` | propriedade dinâmica, silenciosa | `Deprecated` a partir do 8.2 |

## Correção (commit `PHP8-T026: Torna opcional o $context…`)

1. `_handle(…, $context = null)`: o parâmetro que o PHP 8 não passa ficou opcional. Nada mais muda.
2. `$suppress = (error_reporting() & ~(E_ERROR | E_CORE_ERROR | E_COMPILE_ERROR | E_USER_ERROR | E_RECOVERABLE_ERROR |
   E_PARSE)) === 0`: suprimido quando não sobra nenhum bit além dos que o PHP 8 mantém sob `@`. No 5.6 o `@` dá `0`, que
   continua suprimido. Decisão de 13/11 (restaura o comportamento antigo; Regra 3 permite).
3. `Logger` declara `protected $filePath;` (sem mudar lógica).

**Caso-limite (registrado, decisão de 13/11):** um `error_reporting` posto de propósito **só** com bits fatais, fora de
`@`, passaria a contar como suprimido. Não acontece no projeto: `config/application.default.php:27` (e a cópia local
`config/application.php:27`, não versionada) define `php.error_reporting => E_ALL & ~E_NOTICE & ~E_WARNING &
~E_DEPRECATED & ~E_STRICT` = 22517; tirados os bits fatais sobra 18080 (`E_CORE_WARNING`, `E_COMPILE_WARNING`,
`E_USER_WARNING`, `E_USER_NOTICE`, `E_USER_DEPRECATED`) ≠ 0, então fora do `@` nada é tratado como suprimido.

Sem cópia em `extension/modification/` para esses arquivos (conferido).

## Testes (commit `PHP8-T026: Adapta os testes…`)

- `ErrorTest::testHandleWithoutReporting`: preparo `error_reporting(null)` → `error_reporting(0)` (no PHP 8 `null` não
  zera, devolve o nível atual; no 5.6 zerava). Asserção igual (adaptação mecânica da T-009).
- `ErrorTest::testHandleSuppressedByAt` (novo): `@Error::handle(E_USER_WARNING, …)` devolve `false` e a mesma chamada sem
  `@` devolve uma `Entity`, nos dois runtimes.
- `LoggerTest`: classe base `PHPUnit\Framework\TestCase`, `@before`/`@after` no lugar de `setUp()`/`tearDown()`,
  `expectException()` no lugar das anotações removidas no PHPUnit 9. Asserções iguais. Saiu de `lacunas.lista`; em
  `unitario.lista` deixou de ser `|56`.

Suíte (`suite.mjs bash ecidade/tests/suite/rodar.sh --agente back1`, 13/11/2026): **5.6 280/280** (unitário 278/278),
**8.5 81/81** (unitário 79/79), 0 falhos, 0 pulados. `ErrorTest` 3/3, `ShutdownTest` 1/1 e `LoggerTest` 5/5 nos dois.
`php -l` limpo nos dois runtimes nos 4 arquivos tocados.

## Telas (critério 3)

**Quando o handler é chamado.** `ErrorHandler::register()` (`bootstrap.php:142`, com `app.error.handler = 'Default'`)
passa a máscara `php.error_reporting` ao `set_error_handler`. Com ela, `E_WARNING`/`E_NOTICE`/`E_DEPRECATED` do PHP **não**
chegam ao handler; no PHP 8 só chegam `trigger_error` `E_USER_*` (o core quase não emite mais `E_RECOVERABLE_ERROR`). Na
bateria da T-022 (233 telas de menu, 7 prefixos, 8.5 sem esta correção) o handler não foi chamado nenhuma vez: o
`error.log` tem só `E_ERROR` e nenhum `ArgumentCountError`.

**Os `trigger_error` do sistema que chegariam ao handler** (fora de `vendor/`, `dbagata/`, `jpgraph`) — nenhum entra na
bateria de tela; o caminho do handler em si fica provado pelos testes unitários acima (inclusive o `@`). **Lacuna:**

| `trigger_error` | Por que não entra na bateria |
|---|---|
| `libs/db_stdlibwebseller.php:4316,4321` `arraySumValues()` (`E_USER_WARNING`) | só dispara com argumento que não é vetor; o único chamador, `sau2_consultageral002.php:1513`, é **relatório** (sem triagem por leitura de código, só em container somente leitura) e sempre passa vetores |
| `std/Polyfill/PHP54Polyfill.php:106,111,115` `hex2bin()` (`E_USER_WARNING`) | código morto: `hex2bin` é nativo no 5.6 e no 8.5, o polyfill não é usado |
| `pes4_gerafolha002.php:427` (`E_USER_ERROR`) | no `catch` do cálculo da folha: **grava no banco — não rodar** |
| `securimage/securimage.php` (vários `E_USER_WARNING`/`E_USER_NOTICE`) | quase todos só com o banco do captcha ligado (`use_database`/`use_sqlite_db`); o projeto usa `new Securimage()` sem opções (`abrir.php:152`, `carregaCaptcha.php:30`), com os dois `false`. O de `:1897` é do áudio do captcha sem código na sessão: login, não tela de menu |

**Bateria dirigida (opção aceita em 13/11):** 3 telas de menu que emitem aviso do PHP nos dois runtimes (passam
pelo `bootstrap.php` com o handler registrado, fora da máscara), 5.6 (`:8110`) × 8.5 (`:8111`) em containers **que
gravam**, com o vigia do banco antes/depois.

Como as telas foram achadas: medição à parte, com `auto_prepend_file` só nos containers da medição (função de shutdown que
grava `error_get_last()` em `/tmp`, sem imprimir nada), sobre as 233 telas de menu da T-022; depois o arquivo foi retirado
e o Apache recarregado antes da comparação (conferido: nenhum `.ini` com `t026` nos dois).

| Tela | Área | Aviso no 5.6 | Aviso no 8.5 | 5.6 × 8.5 |
|---|---|---|---|---|
| `bib1_acervo000.php` | Educação | `E_WARNING` `db_stdlib.php:101` `pg_query(): Query failed: ERRO: erro de sintaxe em ou próximo a "and"` | o mesmo | idêntica (HTTP 200) |
| `eso01_agendamentoenvio.php` | RH | `E_NOTICE` `db_funcoes.php:256` `Undefined index: Ur44_descr` | `E_WARNING` `Undefined global variable $Ur44_descr` | idêntica (HTTP 200) |
| `ouv4_solicitacaoprocessoeletronico.php` | Patrimonial | `E_NOTICE` `db_funcoes.php:1153` `Undefined index: UdataFinal` | `E_WARNING` `Undefined global variable $UdataFinal` | idêntica (HTTP 200) |

Resultado: **3/3 idênticas**, 0 divergentes, 0 timeout (instrumento `cmp_rn.py` da T-022, `docs/registro/runtime-novo.md`:
sessão restaurada antes de cada pedido, mesmas normalizações do `cmp.py`). Saída do vigia:

```
foto: 4230 tabelas
mudaram: 1 tabela(s)
  configuracoes.db_usuariosonline 6
OK: so tabelas permitidas
```

A medição instrumentada (233 telas × 2 runtimes) não teve vigia próprio; o vigia aberto antes da última etapa da bateria
da T-022 e fechado depois dela acusou só tabelas permitidas (`db_logsacessa_202611_*`, `db_usuariosonline`, e
`oauth_access_tokens`/`oauth_refresh_tokens` de logins de outros agentes no mesmo intervalo).

## O que isto não prova

- Uma tela real chamando o handler por `trigger_error` (lacuna acima): o caminho é coberto só pelos testes unitários.
- Que essas 3 telas quebrariam sem a correção: o aviso delas fica fora da máscara, então não passa pelo handler.
