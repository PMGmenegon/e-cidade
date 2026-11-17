# SuperClosure (`src/Task/Closure.php`) no PHP 8.5 e com as dependências do Laravel 13

Medido em 14/11/2026. `ecidade/src/Task/Closure.php` usa `SuperClosure\SerializableClosure` (`jeremeamia/superclosure` 2.4.0, abandonado) para tornar uma closure serializável.

## Quem usa

| Onde | O quê |
|---|---|
| `ecidade/src/Task/Executor/Background.php:6,31` | `new TaskClosure($task)`: só quando `add()` recebe um *callable* que não é uma task (`Background::add`, linha 24) |
| `ecidade/rec4_processamentopontoeletronico.RPC.php:31,117,159,175` | **único chamador** de `Executor\Background` no código (tela de processamento do ponto eletrônico): `new BackgroundProcess()`, `add($processoSegundoPlano)`, `start()` |
| `ecidade/bin/background-worker:62` | o processo de linha de comando (`Symfony\Process`) que desserializa a task gravada por `Background::createData` (linha 137) e a executa; filtra rastros com `vendor/jeremeamia/SuperClosure` (linha 24) |

O que o chamador passa a `add()` é um `ProcessamentoPontoSegundoPlano` (uma task, `Base`), **não** uma closure: o ramo que cria `ECidade\Task\Closure` **não é alcançado por nenhum código existente**. Só seria se alguém passasse uma closure a `Background::add()`. A serialização das tasks (com `serialize`) acontece nesse caminho por tela (RPC) e fila de processos (CLI), mas sem SuperClosure.

## Medida

Mesmo trecho (`scratchpad/superclosure_medida.php`): serializa e desserializa `function ($a) use ($y) { return $a * $y + 2; }` (com `$y = 8`, chamada com 5) e a task `ECidade\Task\Closure`.

| Ambiente | php-parser | Resultado |
|---|---|---|
| PHP 5.6, vendor de hoje | 3.1.5 | serializa (202 bytes), desserializa, executa: **42**; task: `ok-42` |
| PHP 8.5, vendor de hoje | 3.1.5 | **falha**: `Notice: Serialization of closure failed: There was an error analyzing the closure code` (o `Lexer` do php-parser 3.1.5 não conhece os tokens do PHP 8: `Undefined array key 410`); `serialize()` devolve `N;` e a desserialização não devolve objeto |
| PHP 8.5, conjunto do Laravel 13 (`composer-runtime-novo.lock`: `jeremeamia/superclosure` 2.4.0, `nikic/php-parser` v4.19.5) | 4.19.5 | serializa (201 bytes), desserializa, executa: **42**; task: `ok-42` |

Compatibilidade entre runtimes (payload gravado por um e lido pelo outro, a closure e a task executam): payload do 5.6 lido no 8.5 com o conjunto do 13: **42**; payload do 8.5 lido no 5.6: **42**. A única diferença no texto serializado é 1 caractere: o código da closure termina em `};` (php-parser 3.1.5) e em `}` (4.19.5); a execução é a mesma.

## Conclusão

`jeremeamia/superclosure` 2.4.0 **resolve e funciona no 8.5 com o conjunto do Laravel 13** (o `nikic/php-parser` v4.19.5 que esse conjunto já traz). O que quebra no 8.5 é o `php-parser` 3.1.5 do vendor de hoje, e isso some com o vendor novo sem mudar nada. **`src/Task/Closure.php` não muda** (arquivo compartilhado com o 5.6, que segue igual): nenhuma troca por `opis/closure` é necessária. O pacote continua abandonado; se for trocado um dia, é decisão à parte.

Limite: o conjunto do 13 foi instalado só como `vendor/` descartável (`composer install` do `composer-runtime-novo.lock`, `--no-scripts`); o boot do Laravel 13 completo não foi exercitado aqui.
