# Boot do Laravel 13 no runtime novo: inicialização e providers

Medido em 14/11/2026 no runtime novo (PHP 8.5.12, `vendor/` do Laravel 13.42.0 de `composer-runtime-novo.json`, ver `dependencias-laravel13.md`),
banco somente leitura. Escopo: inicialização (`bootstrap/app.php`, `public/index.php`, `app/Application.php`, `app/Http/Kernel.php`,
`app/Console/Kernel.php`, `app/Exceptions/Handler.php`) e providers (`app/Providers/*`, `BaseDeferredProvider`, lista de providers de
`configuration/app.php`), cada ponto ligado ao item do inventário do código próprio (`docs/migracao-laravel/inventario-codigo-proprio.md`, seção 6,
grupos 1 e 3). Configuração, middlewares, Passport, rotas e models são etapas seguintes.

## Resultado

| Pedido no runtime novo | Antes (só o `vendor/` do 13) | Depois |
|---|---|---|
| `php artisan --version` | sai com 255, sem mensagem | `Laravel Framework 13.42.0` |
| `php artisan list` | idem | lista os comandos (`artisan route:list --json`: 556 linhas, **557** pares método + URI; o 5.6 tem 562) |
| `GET /v4/api/configuracao/instituicao` (rota sem middleware) | 500 | **200** com os dados da instituição |
| `GET /v4/api/configuracao/relatorios-legais/lrf` (grupo `api`) | 500 | 500: `Não existe conexão com o banco de dados.` (`src/Lib/Session/DatabaseSession.php:86`, middleware de sessão: etapa dos middlewares) |
| `GET /v4/api/configuracao/bancos` (`api` + `auth:api`) | 500 | 500: `Key file ".../storage/oauth-public.key" permissions are not correct, recommend changing to 600 or 660 instead of 777` (`league/oauth2-server` 9 recusa chave com modo 777; o ambiente deixa `storage/` em 777: etapa do Passport) |
| rota inexistente | 500 | 404 JSON `{"error":true,"message":"The route ... could not be found."}` (o `Handler` do projeto responde) |

Onde parou o boot, em ordem (cada parada corrigida com o mínimo e o `artisan --version` repetido):

| # | Parada | Item do inventário | Correção |
|---|---|---|---|
| 1 | `Cannot make non abstract method Illuminate\Support\ServiceProvider::register() abstract in class App\Domain\Core\Base\Providers\BaseDeferredProvider` | grupo 3: `BaseDeferredProvider` (`$defer`, `register` abstrato) | `app-runtime-novo/Domain/Core/Base/Providers/BaseDeferredProvider.php`: sem o `abstract register()` (no 13 o método existe) e `implements DeferrableProvider` no lugar de `$defer = true` (o `$defer` foi removido no 6), mantendo o provider adiado |
| 2 | `Declaration of App\Exceptions\Handler::report(Exception $exception) must be compatible with ...Handler::report(Throwable $e)` | grupo 1: `Exceptions/Handler.php` (`report`, `render`) | `app-runtime-novo/Exceptions/Handler.php`: cópia com `Throwable` em `report`, `render` e `getStatusCode`; corpo igual |
| 3 | `Class "Intervention\Image\ImageServiceProvider" not found` | grupo 3 / `configuration/app.php` (lista de providers) | `app-runtime-novo/Application.php`: antes de registrar os providers, retira da lista `Intervention\Image\ImageServiceProvider` (constante `PROVIDERS_FORA`, explícita: qualquer outro provider ausente continua falhando no boot). O pacote do 13 é `intervention/image` 4, sem esse provider; o alias `Image` só falha quando usado: 1 arquivo, `AssinadorAPI.php` |
| 4 | `Call to undefined method Laravel\Passport\Passport::routes()` (`AuthServiceProvider.php:29`) | grupo 3: `AuthServiceProvider` (`Passport::routes`) | `app-runtime-novo/Providers/AuthServiceProvider.php`: cópia sem a chamada (o Passport 13 registra as rotas sozinho) |

Sem mudança, e funcionando no 13: `bootstrap/app.php` (`new Application(...)` e os três `singleton`), `public/index.php`, `app/Application.php`
(`configPath` aponta para `configuration/`), `app/Http/Kernel.php` (o 13 ainda lê `$middleware`, `$middlewareGroups` e `$routeMiddleware`, e
`CheckForMaintenanceMode` ainda existe), `app/Console/Kernel.php`, `AppServiceProvider`, `EventServiceProvider`, `RouteServiceProvider` (o `$namespace` não é usado
pelos grupos de rotas do projeto), `QueueServiceProvider`. `BroadcastServiceProvider` não está na lista de providers.

## Como o 5.6 fica igual

Os dois runtimes montam os mesmos arquivos de `app/` e `configuration/`, e o 5.6 exige a assinatura exata dos métodos herdados (medido: com um
parâmetro sem o tipo do pai o PHP 5.6 emite `Strict Standards`, e o Laravel 5.4 converte erro em exceção). Por isso **nenhum arquivo compartilhado foi alterado**:

- Tudo o que muda fica em `ecidade/app-runtime-novo/` (`Application.php`, `Exceptions/Handler.php`, `Providers/AuthServiceProvider.php`,
  `Domain/Core/Base/Providers/BaseDeferredProvider.php`), que só o `composer-runtime-novo.json` põe antes de `app/` no PSR-4
  (`"App\\": ["app-runtime-novo/", "app/"]`). O `composer.json` do 5.6 não muda; o `vendor/` do 5.6 nunca vê a pasta. Depois de criar ou mudar um arquivo lá, é preciso
  regenerar o autoload do runtime novo (`composer dump-autoload` com `COMPOSER=composer-runtime-novo.json`).
- No 5.4 o `ServiceProvider` nem declara `register()`, então remover o `abstract` de `BaseDeferredProvider` no arquivo compartilhado teria mudado o 5.6: foi descartado.
- **Bateria dirigida de telas de menu no 5.6** (um conjunto pequeno por área, `scratchpad/cmp.py --vigia`, container que grava; 5.6 × 8.5 com os arquivos desta branch): **135 de 136 idênticas, 1 divergência já conhecida
  (`bib1_emprestimo002.php`, `area-educacao.md`), 0 novas**; o vigia do banco viu só `db_usuariosonline` e `db_logsacessa*` (`OK: so tabelas permitidas`). Prefixos: `itb2_`/`itb3_` (Tributário), `bib1_` (Educação),
  `eso1_`/`eso2_` (RH), `pat3_`/`com3_` (Patrimonial), `tes1_`/`tes2_`/`cus2_`/`pla1_` (Financeiro), `fum1_` (Saúde), `sys1_` (Configuração).
- `git diff laravel/integracao -- ecidade/app ecidade/configuration` é vazio; `tests/sistema/gera-rotas.php` rodado no 5.6 regenera as **562 rotas** de
  `tests/sistema/dados/rotas-v4.tsv` sem diferença (`git status` limpo); suíte `rodar.sh` no 5.6 igual à anterior.

## Rotas: o que já existe no runtime novo

Das 562 rotas do 5.6, **547 estão registradas** no runtime novo (543 de `/v4/api` e 4 de `/rest/v1`, mesmo método e URI). Faltam as **15 `/v4/oauth/*`**: com a
`Passport::routes` removida (Passport 13 registra as rotas sozinho), o Passport 13 registrou **10** rotas no prefixo padrão `/oauth/*` (`/oauth/token`, `/oauth/authorize`...).
Mudar o prefixo para `v4/oauth` e o conjunto de rotas é o item do Passport (grupo 5), não do boot.

## Diferenças achadas fora do boot (para as etapas seguintes)

- **Tipo numérico do banco:** o mesmo `GET /v4/api/configuracao/instituicao` devolve `"tx_banc":"0"` (texto) no 5.6 e `"tx_banc":0` (inteiro) no runtime novo (o `pdo_pgsql`
  do PHP 8.1+ devolve inteiros e decimais já convertidos). O corpo tem 2.579 bytes no 5.6 e 2.575 no novo; o resto é igual. É uma "mudança de comportamento sem erro" do salto de PHP,
  não do boot; a comparação 5.6 × novo das rotas vai precisar tratá-la.
- **Modo das chaves do Passport:** `storage/oauth-*.key` com modo 777 é recusado pelo `league/oauth2-server` 9 (exige 600 ou 660).

## Como reproduzir

```bash
# runtime novo (passos 1 a 4 de dependencias-laravel13.md e subir pelo docker-compose.runtime-novo.yml, banco somente leitura)
bash docker/runtime-novo/prepara.sh ecidade runtime-novo && rm -rf runtime-novo/vendor && mkdir runtime-novo/vendor
docker run --rm --init --network host -u 1000:1000 -v $PWD/ecidade:/app -v $PWD/runtime-novo/vendor:/app/vendor -w /app \
  -e COMPOSER=composer-runtime-novo.json -e COMPOSER_HOME=/app/tmp/composer-home ecidade-login-php85 composer install --no-scripts --no-plugins --no-interaction
RN_PGOPTIONS='-c default_transaction_read_only=on' docker compose -p rn -f docker-compose.runtime-novo.yml up -d
docker exec -w /var/www/html <container> php artisan --version        # Laravel Framework 13.42.0
docker exec -w /var/www/html <container> php artisan route:list --json  # 556 linhas (557 pares método + URI)
```

O bootstrap do projeto silencia a saída de erro fatal: para ver onde o boot para, rode o `artisan` com um `auto_prepend_file` que registre
`register_shutdown_function` com `error_get_last()` e `set_exception_handler`.

## Lacunas

- Nenhuma tela de menu foi rodada no runtime novo; só `artisan` e GETs a rotas `/v4` (que só leem).
- Os 5 relatórios que sobem o kernel do Laravel na página não foram exercitados no runtime novo.
- Middlewares (`SessionMiddleware`, `DatabaseMiddleware`, `DBRequestMiddleware`...), configuração, Passport (rotas `v4/oauth`, chaves), models e rotas por
  grupo seguem como etapas próprias; o `Handler` do projeto responde o JSON de erro, mas `render` com o `config('app.debug')` não foi exercitado.
