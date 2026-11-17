# Dependências do Laravel 13 só do runtime novo (T-043, 13–14/11/2026)

**Resumo:** o runtime novo (PHP 8.5, `docker-compose.runtime-novo.yml`) ganhou o próprio conjunto de dependências,
resolvido e travado no 8.5: `ecidade/composer-runtime-novo.json` e `ecidade/composer-runtime-novo.lock`, com
**Laravel 13.42.0** e **Passport 13.10.0** (136 pacotes + 29 de desenvolvimento). O `composer install` limpo num
container novo instala os 165 em 44 s, dentro do `vendor/` próprio do runtime novo. O `composer.json`/`composer.lock`
do 5.6 não mudaram (sha256 igual antes e depois). O runtime novo sobe com esse `vendor/`: as telas legadas e o login
respondem igual ao 8.5 de hoje; o kernel do Laravel 13 para no primeiro provider da aplicação (registrado abaixo, não
corrigido aqui).

## Arquivos

| Arquivo | O que é |
|---|---|
| `ecidade/composer-runtime-novo.json` | lista do runtime novo: as restrições são as versões resolvidas (`^<versão>`) |
| `ecidade/composer-runtime-novo.lock` | trava do runtime novo (`content-hash` `afcb4340e2a6a7d210d81d3f24ba6702`) |
| `scratchpad/composer_runtime_novo.py` | gera o `.json` a partir do `composer.json` do 5.6 e, depois do resolvedor, troca as restrições pelas versões resolvidas (`--travar`) |

O Composer escolhe o arquivo pela variável `COMPOSER` (`COMPOSER=composer-runtime-novo.json` → lê esse `.json` e grava o
`.lock` de mesmo nome). Os dois ficam ao lado do `composer.json` do 5.6 para que `autoload` (arquivos de `app/Helpers`,
`classmap` de `database`, `psr-4` `App\`/`Fpdf\`/`Tests\`) use os mesmos caminhos relativos. Dentro do container do
runtime novo, `/var/www/html/vendor` é o `vendor/` próprio dele (`$RN_DIR/vendor`, ver `runtime-novo.md`): o
`ecidade/vendor` do 5.6 não é tocado.

## O que entra e o que fica de fora

Partida: o cenário "Laravel 13 + Passport ^13.0" da matriz de versões (`docs/migracao-laravel/matriz-versoes.md`,
"Alternativas medidas no resolvedor"), que resolve no 8.5. Regras do `composer_runtime_novo.py`:

- `laravel/framework` e `laravel/passport` em `^13`; todo outro requisito direto (não `php`/`ext-*`) livre para o
  resolvedor; depois do resolvedor, cada um vira `^<versão resolvida>` (o `composer bump` daria `>=` sem teto a partir de
  `*`). `dbseller/session` fica `dev-master`, como no 5.6.
- **Fora do conjunto** (não resolvem com o Laravel 13; cada substituto é etapa própria): `silex/silex`,
  `proner/phppimaco`, `dbseller/phinx_postgres`, `dbseller/sdk-api-pix-bb`. O Phinx direto (`robmorgan/phinx`), que a
  matriz usou como alternativa, **também não entra**: a escolha do substituto do adaptador da DBSeller é etapa própria.
- `php` `^8.5`; as 12 `ext-*` iguais às do 5.6.
- `dbseller/session`: mesmo repositório e mesmo commit do 5.6 (`f3020b4`), por **https** com `no-api` (o 5.6 usa
  `git@github.com`, que pede chave SSH; o repositório é público; `no-api` clona por git, sem a API do GitHub, que pede
  token).
- **Sem `scripts`**: os de hoje chamam `php5.6` e o `artisan` do Laravel 5.4. Quando o Laravel 13 subir de verdade, o
  `package:discover` (gera `bootstrap/cache/packages.php`/`services.php`) e o `artisan` vão ser precisos no boot — etapa
  seguinte, junto com o porte dos providers.
- `secure-http: false`, que no 5.6 está fora de `config` (sem efeito), não foi copiado.
- `autoload`, `autoload-dev`, `minimum-stability: dev`, `prefer-stable: true` e `config` iguais aos do 5.6.

Versões travadas dos pacotes diretos:

| Pacote | 5.6 | runtime novo |
|---|---|---|
| `laravel/framework` | v5.4.36 | v13.42.0 |
| `laravel/passport` | v4.0.3 | v13.10.0 (`league/oauth2-server` 9.4.1) |
| `laravel/tinker` | v1.0.10 | v3.1.0 |
| `guzzlehttp/guzzle` | 6.5.8 | 8.5.0 (a matriz de 12/11 tinha 8.4.0: saiu versão nova) |
| `symfony/console`, `filesystem`, `validator`, `yaml` / `process` | v3.4.47 | v8.1.11 / v8.1.10 |
| `lcobucci/jwt` | 3.3.3 | 5.6.1 |
| `phpoffice/phpspreadsheet` / `phpword` | 1.8.2 / 0.17.0 | 5.11.0 / 1.4.0 |
| `dompdf/dompdf` / `mpdf/mpdf` | v0.8.3 / v7.1.9 | v3.1.6 / v8.3.1 |
| `intervention/image` | 2.7.2 | 4.4.1 |
| `league/fractal` | 0.11.0 | 0.21 |
| `phpmailer/phpmailer` | v6.9.1 | v7.2.0 |
| `mormat/php-formula-interpreter` | v1.0.0 | v2.0.1 |
| `nfephp-org/sped-common` | v5.0.40 | v5.1.17 |
| `zendframework/zend-eventmanager` | 2.2.10 | 2.6.2 (+ `zend-stdlib` 2.7.4, `zend-hydrator` 1.0.0) |
| `doctrine/dbal` | (fora do lock) | 4.5.1 |
| demais (`aferrandini/phpqrcode`, `dbseller/legacy`, `jeremeamia/superclosure`, `michelf/php-markdown`, `ncjoes/office-converter`, `pusher/pusher-php-server`, `symfony/polyfill-php56`/`70`, `vlucas/valitron`, `barryvdh/laravel-ide-helper`) | | as da coluna "Candidata L13" da matriz |
| dev: `phpunit/phpunit`, `mockery/mockery`, `filp/whoops`, `squizlabs/php_codesniffer`, `fzaninotto/faker` | 5.7.27, 1.3.0, 2.15.4, 3.9.0, v1.9.2 | 10.5.66, 1.6.15, 2.19.3, 4.0.4, v1.5.0 |

O Composer avisa que 6 estão abandonados: `aferrandini/phpqrcode`, `fzaninotto/faker`, `jeremeamia/superclosure`,
`zendframework/zend-eventmanager`, `zend-hydrator` e `zend-stdlib` (substitutos sugeridos: `opis/closure`,
`laminas/*`; o `faker` sem substituto). Ficam como estão: trocá-los é etapa própria (a matriz já lista onde cada um é
usado).

## Como reproduzir

```bash
# 1) lista (só lê o composer.json do 5.6)
python3 scratchpad/composer_runtime_novo.py ecidade/composer.json ecidade/composer-runtime-novo.json
# 2) resolver no 8.5 (imagem do runtime novo: PHP 8.5.12, Composer 2.11.1); --network host porque a rede bridge
#    desta máquina não resolve DNS, --init para o timeout derrubar o PHP (ver matriz-versoes.md, armadilhas)
C="docker run --rm --init --network host -u 1000:1000 -v $PWD/ecidade:/app -w /app \
   -e COMPOSER=composer-runtime-novo.json -e COMPOSER_HOME=/app/tmp/composer-home ecidade-login-php85"
$C composer update --no-install --no-scripts --no-plugins --no-interaction
# 3) restrições = versões resolvidas, e só o content-hash do lock atualizado (versões iguais, conferido)
python3 scratchpad/composer_runtime_novo.py --travar ecidade/composer-runtime-novo.lock ecidade/composer-runtime-novo.json
$C composer update --lock --no-install --no-scripts --no-plugins --no-interaction
$C composer validate --no-check-publish     # válido; só o aviso de licença, como o do 5.6
# 4) instalação limpa no vendor/ do runtime novo
bash docker/runtime-novo/prepara.sh ecidade runtime-novo
rm -rf runtime-novo/vendor && mkdir runtime-novo/vendor
docker run --rm --init --network host -u 1000:1000 -v $PWD/ecidade:/app -v $PWD/runtime-novo/vendor:/app/vendor -w /app \
   -e COMPOSER=composer-runtime-novo.json -e COMPOSER_HOME=/app/tmp/composer-home ecidade-login-php85 \
   composer install --no-scripts --no-plugins --no-interaction
```

## Medidas

**Lista e trava do 5.6 intocadas** (sha256 antes da tarefa e depois da instalação):

```
f3cd4ba68604259d2e5e45f6cd97e3404d1a61a67cbf9e89ded3b8ee2f2ad36b  ecidade/composer.json
d5246a26bcb39062778d3d8244754955266883bd156f44e191829bf98d3e616c  ecidade/composer.lock
```

**Instalação limpa:** `rc=0`, 165 pacotes instalados em 44 s, `vendor/` de 211 MB (o do 5.6 tem 247 MB).
`vendor/laravel/framework/.../Application.php` diz `VERSION = '13.42.0'` no runtime novo e `'5.4.36'` no `ecidade/vendor`.
O `composer install` avisa 33 classes de `app/` que não seguem o PSR-4 (pasta e namespace com grafias diferentes, por
exemplo `App\Core\Base\Model\BaseModel` em `app/Domain/Core/Base/Model/`); as mesmas já ficam fora do classmap do
`vendor/` do 5.6 (conferido por nome em `autoload_classmap.php`): é o código de hoje, não efeito da troca.

**O runtime novo sobe com esse `vendor/`** (`docker-compose.runtime-novo.yml`, container de teste na porta 8172, banco
somente leitura com `RN_PGOPTIONS='-c default_transaction_read_only=on'`; só pedidos que não gravam):

| Pedido | 8.5 de hoje (vendor do 5.6) | runtime novo (vendor do Laravel 13) |
|---|---|---|
| `GET /login.php` | 200 | 200, **mesmo corpo** (md5 igual, tirados os tokens aleatórios da página) |
| `GET /index.php` | 302 → `login.php` | 302 → `login.php` |
| `GET /v4/oauth/token` | 500 (Laravel 5.4 não roda no PHP 8) | 500 (abaixo) |
| `GET /api/v1/` | — | 200 com corpo vazio: o Silex está fora do conjunto novo |
| `php artisan --version` | — | sai com código 255, sem mensagem |

O que quebra no Laravel 13 (subindo o kernel de console com um script que captura o último erro do PHP):

```
Cannot make non abstract method Illuminate\Support\ServiceProvider::register() abstract in class
App\Domain\Core\Base\Providers\BaseDeferredProvider em app/Domain/Core/Base/Providers/BaseDeferredProvider.php:19
```

É o primeiro provider da aplicação: o mesmo ponto em que o Laravel 12 parou na medição de 14/10/2026 (`laravel.md`).
Não foi corrigido aqui: o porte dos providers e do resto de `app/` é a etapa seguinte. No `/api/v1/` o último aviso do PHP
é um `Deprecated` do `zend-stdlib` (`SplPriorityQueue::insert` sem tipo de retorno), da troca `zend-*` → `laminas-*`.

## Lacunas

- Nada do Laravel 13 foi exercitado além do boot: o kernel para no primeiro provider.
- Telas de menu não foram rodadas no runtime novo com este `vendor/` (exigem container que grava, com o vigia do banco);
  só `login.php` e `index.php`, que não gravam.
- O `vendor/` do runtime novo não é versionado (fica em `runtime-novo/`, ignorado pelo git): quem for usar refaz o passo 4.
