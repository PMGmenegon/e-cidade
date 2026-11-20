# Filas, comandos, agendamento e funções removidas no PHP 8.5 (PHP8-51)

Medido em 20/11/2026, sem banco, sem rede e sem fila de verdade. O 7.4 é o do PR: a imagem construída de
`docker/php74-apache` (PHP 7.4.33) com o `vendor/` instalado do `ecidade/composer.lock`. O 8.5 é a imagem de
`docker/php85-apache` (PHP 8.5.12) com o `runtime-85/vendor` instalado do `ecidade/composer-85.lock`
(`docker/composer-85/composer-85.sh install`). Os dois lados têm o mesmo Laravel 8.73.2 e sobem o kernel de console
como o `artisan` faz (`bootstrap.php`, depois `bootstrap/app.php`). O `.env` de teste é o `.env.example` com chave e
endereços fictícios e banco num host que não existe (`anexos/filas-comandos-85/gera_env.py`).

**Resultado:** tudo igual. Nenhum arquivo do sistema muda nesta tarefa. A parte de e-mail e notificações da PHP8-51
fica em tarefa própria.

| O quê | Casos | 7.4 × 8.5 |
|---|---|---|
| `artisan list --raw` | 111 linhas | igual byte a byte |
| comandos: nome, classe, descrição, oculto, apelidos, argumentos e opções com padrão | 112 comandos (15 do e-cidade, em `app/Console/Commands`) | igual byte a byte |
| agendamento (`app/Console/Kernel.php`): comando, cron, fuso, descrição, `withoutOverlapping`, `onOneServer`, `runInBackground`, `evenInMaintenanceMode` e as 3 próximas execuções a partir de 01/01/2026 | 10 eventos | igual byte a byte |
| payload de fila (`createPayload` do Laravel): `displayName`, `job`, `maxTries`, `maxExceptions`, `failOnTimeout`, `backoff`, `timeout`, `retryUntil`, `commandName` e o `unserialize` de volta | 16 classes `ShouldQueue` (14 jobs e 2 notificações) | igual |
| objeto da fila gravado num runtime e lido no outro (estado de todas as propriedades, recursivo) | 16 classes × 4 combinações (7.4→7.4, 7.4→8.5, 8.5→7.4, 8.5→8.5) | 1 estado só nas 4 |
| `array_pluck` (`ComissaoController.php:75`) e `str_random` (`ModelFactory.php:22`) | 2 | igual: `Error: Call to undefined function` nos dois |
| `str_contains`: polyfill `symfony/polyfill-php80` no 7.4, nativa no 8.5 | 14 entradas | 12 iguais; as 2 com array dão `TypeError` nos dois, só o texto da mensagem muda |

## Fila: o que muda e o que não muda

O `command` serializado sai igual byte a byte em 14 das 16 classes. Nas 2 notificações enfileiradas
(`EmissaoRelatorioLegalNotification`, `UserNotificationAcordoVencimento`, embrulhadas em `SendQueuedNotifications`,
como o Laravel faz), muda a **ordem** das propriedades na string. O `SerializesModels::__serialize` percorre
`ReflectionClass::getProperties()`. No 7.4, essa lista traz as propriedades herdadas (`id`, `locale` de
`Notification`) antes das do trait (`middleware` de `Queueable`); no 8.x, depois. As chaves e os valores são os
mesmos, e o `unserialize` monta o objeto por nome. A leitura cruzada prova isso: um job gravado pelo 7.4 e lido pelo
8.5, ou o contrário, chega ao mesmo estado. Por isso a fila pode ser gravada por um runtime e consumida pelo outro
durante a migração.

Como o objeto foi montado (`anexos/filas-comandos-85/jobs.php`): primeiro o construtor real, com argumentos fixos
(classe tipada recebe instância sem construtor; `datausu` e `filtros` recebem o tipo que o código espera). Se o
construtor precisa de banco ou de serviço, vai sem construtor e cada propriedade da classe recebe um valor fixo. Os
dois runtimes seguiram o mesmo caminho nas 16 classes: 6 pelo construtor, 7 sem construtor por `QueryException` (banco
inexistente) e 3 sem construtor por `Exception` dos serviços do BNAFAR. Model vai como `ModelIdentifier`, e a
restauração, que consultaria o banco, não é feita.

O `ProcessPayrollDataJob` encerra no construtor com `die()` quando falta `API_DATA_AVAILABLE_TOKEN`/`_URL`, igual nos
dois. Com os dois valores fictícios no `.env` de teste, o payload sai.

## Agendamento e lista de comandos: como foi lido

O `artisan schedule:list` e o `artisan list --format=json` do PR não servem para comparar, porque falham do mesmo
jeito no 7.4 e no 8.5 (registro da PHP8-49). Por isso `anexos/filas-comandos-85/console.php` lê direto do kernel: os
comandos registrados e os eventos do `Schedule`, com a próxima execução calculada pela `CronExpression` a partir de uma
data fixa. A saída é `var_export`, porque as descrições estão em ISO-8859-1.

## Como reproduzir

```bash
bash docs/migracao-laravel/anexos/filas-comandos-85/roda.sh ecidade <vendor do 7.4> runtime-85/vendor <imagem 7.4> <imagem 8.5> <saída>
```

O script monta `ecidade/` só para leitura, o `vendor/` de cada lado em `ecidade/vendor`, o `.env` de teste por cima,
`bootstrap/cache` em `tmpfs` e `storage/` numa pasta da saída. Ele roda tudo com `--network none` e imprime o resumo
da tabela acima.

## Lacunas

- Nenhum job é executado (`handle()`), porque quase todos gravam no banco ou chamam serviço externo. Aqui se prova o
  que vai para a fila e volta dela, não o trabalho do job.
- Nenhum comando é executado além do `list`. A definição (assinatura, argumentos, opções) e o agendamento são os
  mesmos; o corpo de cada comando usa banco.
- O `composer-85.lock` desta medição ainda é a cópia do lock do PR (só ignora o teto de versão do PHP). As trocas de
  pacotes do 8.5 que vêm depois (`lcobucci/jwt` e os 9 pacotes) não mexem em fila, console nem agendamento. Ainda
  assim, o `roda.sh` deve ser rodado de novo sobre o lock final.
