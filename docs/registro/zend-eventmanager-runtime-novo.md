# zend-eventmanager no runtime novo: funciona, só com Deprecated (T-054, 14/11/2026)

**Resumo:** o conjunto do runtime novo (`ecidade/composer-runtime-novo.json`/`.lock`, 165 pacotes, ver
`dependencias-laravel13.md`) mantém o `zendframework/zend-eventmanager` 2.6.2, que puxa `zend-stdlib` 2.7.4 e
`zend-hydrator` 1.0.0. Medido no PHP 8.5: o gerenciador de eventos do sistema (`ECidade\V3\Event\Manager`) se comporta
igual ao do 5.6 (`zend-eventmanager` 2.2.10), e as telas que passam por ele saem iguais nos três runtimes. O PHP 8.5 só
emite 4 `Deprecated` do `zend-stdlib`. Pela regra de não mexer no que funciona igual, **não houve troca** pelo
`laminas-eventmanager`: a lista e a trava ficam como estão. Os três pacotes estão abandonados; isso fica só registrado.

## O "fatal" do `PriorityQueue::count()`

O registro do Laravel (`laravel.md`) tinha o `Zend\Stdlib\PriorityQueue::count() return type` entre os fatais do PHP 8 em
`/v4/*`. Não é fatal do `zend-stdlib`: é `Deprecated`, e o handler de erros do **Laravel 5.4** transformava qualquer aviso,
`Deprecated` inclusive, em `ErrorException`. Com o handler do próprio sistema (`config/application.default.php:27` exclui
`E_DEPRECATED`) nada acontece.

`Deprecated` do `zend-stdlib` 2.7.4 no PHP 8.5 (ao registrar e disparar um evento):

| Arquivo:linha (`vendor/zendframework/zend-stdlib/src/`) | Aviso |
|---|---|
| `PriorityQueue.php:28` | a classe implementa `Serializable` sem `__serialize()`/`__unserialize()` |
| `PriorityQueue.php:128` | `count()` sem o tipo de retorno `int` de `Countable::count()` |
| `PriorityQueue.php:165` | `getIterator()` sem o tipo de retorno `Traversable` de `IteratorAggregate::getIterator()` |
| `SplPriorityQueue.php:37` | `insert()` sem o tipo de retorno `true` de `SplPriorityQueue::insert()` |

Abandonados (o próprio Composer avisa na instalação e sugere `laminas/*`): `zend-eventmanager`, `zend-stdlib`,
`zend-hydrator`. O `zend-stdlib` e o `zend-hydrator` não são usados direto pelo sistema, só pelo `zend-eventmanager`.

## Onde o sistema usa `zend-*` (fora de `vendor/`)

| Arquivo:linha | Uso | Alcançado neste ambiente |
|---|---|---|
| `ecidade/src/V3/Event/Manager.php:5,17,18,26,30,34` | `new EventManager()`, `setIdentifiers()`, `attach()`, `detach()`, `trigger()` | sim: `bootstrap.php:148` cria o gerenciador em todo pedido |
| `ecidade/src/V3/Event/Handler.php:5,9` | tipo `Event` no `execute()` da classe base dos ouvintes | sim |
| `ecidade/src/V3/Error/EventHandler.php:7,19` | ouvinte do `app.error` (`config/application.default.php:116`): grava `extension/log/error.log` | sim |
| `ecidade/src/V3/Config/Data.php:60,66` | `register()` dos eventos da configuração e das extensões instaladas | sim |
| `ecidade/src/V3/Error/Handler/Error.php:45`, `Exception.php:31` | `trigger('app.error', null, [$entity])` | sim |
| `ecidade/extension/package/Desktop/Controller/Desktop.php:85` | `trigger('extension.desktop.bootstrap', $this, [$this])` | sim: `/extension/desktop/` |
| `ecidade/rec2_processamentoespelhoponto.php:40` | `register('app.error', function ($event) {...})` | não rodado (processa o ponto; pode gravar) |
| `ecidade/extension/package/DBug/Event/Bootstrap.php:11`, `ErrorLog/Event/Handler.php:11` | `execute(\Zend\EventManager\Event $event)` | não: extensões não instaladas (`extension/data/config.data` sem eventos) |
| `ecidade/iss4_isscalc.RPC.php:2` | `use Zend\Stdlib\DateTime;` | importação morta (o arquivo só usa `new \DateTime()`, linha 181) |
| `ecidade/tests/Unit/V3/Error/EventHandlerTest.php:8` | `use \Zend\EventManager\Event as ZendEvent;` | teste unitário |

`Manager::unregister()` (`detach`) não tem chamador no sistema.

## Medidas

**Trecho:** um script que usa o `ECidade\V3\Event\Manager` como o sistema usa — ouvinte de objeto, `Closure` e handler
de classe com `execute(\Zend\EventManager\Event $e)`, dois ouvintes no mesmo evento (ordem), alvo nulo, string e objeto,
evento sem ouvinte, exceção dentro do ouvinte, e por fim `unregister()` e a classe do evento recebido. Saída do 5.6
(`zend-eventmanager` 2.2.10) × runtime novo (2.6.2): **iguais nas 10 linhas**, inclusive a exceção
`Zend\EventManager\Exception\InvalidArgumentException` do `unregister()` com `callable` (as duas versões só aceitam
`CallbackHandler` no `detach()`).

**Telas:** 5.6 (`:8170`) × 8.5 de hoje (`:8171`, `vendor/` do 5.6) × runtime novo (`:8172`, `vendor/` do conjunto
novo), containers que gravam, a mesma sessão (login no 5.6) restaurada antes de cada pedido, corpo normalizado (porta da
URL e `sid` aleatório do captcha) e as linhas que cada pedido acrescenta ao `extension/log/error.log` (sem a hora):

| Tela | Uso | 5.6 | 8.5 | novo | `error.log` |
|---|---|---|---|---|---|
| `login.php` | bootstrap: cria o `Manager` e registra `app.error` | 200 | 200 | 200 | nada nos três |
| `bib1_acervo000.php` | idem, tela de menu | 200 | 200 | 200 | nada nos três |
| `sys4_criafontes.php` | erro tratado pelo handler V3: `trigger('app.error')` → `EventHandler::execute()` | 500 | 500 | 500 | 2 linhas no 5.6; 3 no 8.5 e no novo, iguais entre si |
| `extension/desktop/` | `trigger('extension.desktop.bootstrap', ...)` | 200 | 200 | 200 | nada nos três |

Corpo normalizado com o **mesmo md5 nos três runtimes** nas 4 telas. A diferença do `error.log` do
`sys4_criafontes.php` entre o 5.6 e os dois PHP 8 é a já registrada para essa tela (arquivo com erro de sintaxe: `E_PARSE`
no 5.6, `ParseError` capturado pelo handler de exceção no 8.x). Vigia do banco: **rc=0** (só `db_usuariosonline` e
`db_logsacessa_*`, escritas do login).

**Composer do 5.6:** sha256 do `composer.json` e do `composer.lock` iguais (nada foi instalado nem trocado).

## Se um dia trocar

Medido à parte, sem ficar no conjunto: o `laminas/laminas-eventmanager` 3.16.0 resolve no 8.5 sem dependências e tira os
três `zend-*` (165 → 163 pacotes). O código, comum ao 5.6, usa os nomes `Zend\EventManager\*`: sem apelidos para os
nomes Laminas o bootstrap morre em `src/V3/Event/Manager.php:17` (`Class "Zend\EventManager\EventManager" not found`).
Com dois `class_alias` (`EventManager` e `Event`) carregados só pelo autoload do runtime novo, as mesmas 4 telas saíram
iguais. Duas diferenças da 3.x que o sistema hoje não alcança: `unregister($callable)` passa a desregistrar (na 2.x lança
exceção) e a classe do evento passa a ser `Laminas\EventManager\Event`. O `laminas/laminas-zendframework-bridge`
(apelidos de todo `Zend\*`) está abandonado e declara `php ~8.1.0 || ~8.2.0 || ~8.3.0`.

## Lacunas

- `rec2_processamentoespelhoponto.php` não foi rodado; seu uso (`Closure` em `app.error`) é o do trecho medido.
- DBug e ErrorLog não estão instaladas aqui; a assinatura dos seus ouvintes é a do trecho medido.
- Os 4 `Deprecated` continuam no runtime novo; viram erro só se algum handler converter `E_DEPRECATED` (o do Laravel 13
  registra, não converte; medir quando o boot do Laravel 13 passar).
