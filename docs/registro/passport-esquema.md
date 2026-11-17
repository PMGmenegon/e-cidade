# Passport sobre o esquema atual de `oauth_*`, sem migration (T-006)

> Spike de 12/11/2026. Pergunta da decisão **(a)**: existe Passport para o Laravel 13 (ou 12) que rode
> no esquema atual de `oauth_clients`, `oauth_access_tokens` etc., sem migration nem coluna nova?
> Parte de `docs/registro/laravel.md` (token do Passport 4 aceito pelo `league/oauth2-server` novo; "usar Passport 12.4").
> Matriz de versões: T-005 (`docs/migracao-laravel/matriz-versoes.md`, branch `laravel/T-005-matriz-versoes`).
>
> **Nada foi escrito no banco.** O esquema foi lido por `information_schema`/`pg_catalog`; o protótipo abre a sessão com
> `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY` antes de qualquer consulta (a saída confirma `read only: on`).
> Nenhum segredo aparece aqui: do segredo só se registra o formato e o tamanho.

## Resposta (para a decisão a — apresentar, não decidir)

**Para o Laravel 13: não existe Passport que rode "de fábrica" no esquema atual.** O Laravel 13 só aceita o Passport 13.x
(o 12.4.3 exige `illuminate/* ≤ ^12`; T-005). O Passport 13.10.0 **lê** o esquema atual sem migration (as colunas antigas são
tratadas no próprio model), mas quebra em **dois caminhos que o e-Cidade usa**, provados em execução:

| Caminho | Quem usa | Passport 13.10.0 no esquema atual |
|---|---|---|
| Login: `POST /v4/oauth/token` (password grant, cliente `9999999` com segredo) | `login.php` | **falha**: `RuntimeException: This password does not use the Bcrypt algorithm.` (com `hashing.bcrypt.verify=false`, só recusa). Os 8 segredos estão em texto puro e o 13 **sempre** confere com `Hash::check`. |
| `createToken()` (token pessoal) | `App\Domain\Client\Controllers\ClientController` → `ClientRepository::getAccessTokenUser()` | **falha**: `SQLSTATE[42703] … não existe a coluna "provider"` |

As duas falhas **têm contorno sem migration**, só com código da aplicação (sobrescritas no container), também provado em
execução (alternativa A abaixo). Então a resposta para a condição da decisão (a) é:

- "Passport para Laravel 13 sem migration, sem mexer no código do Passport": **não**.
- "Passport 13 sem migration, com 2 sobrescritas na aplicação": **sim, com os riscos da seção 4** (o principal: o login
  continua aceitando segredo em texto puro, contra a intenção do Passport 13; e o caso #1912 de id de usuário igual ao id de
  cliente).
- "Passport para Laravel 12 sem migration": **sim, de fábrica** — Passport 12.4.3 passou em todos os caminhos medidos.

## 1. Esquema atual (só leitura)

```sql
-- tabelas
select table_schema||'.'||table_name from information_schema.tables where table_name like 'oauth%' order by 1;
-- colunas
select table_name, ordinal_position, column_name, data_type, character_maximum_length, is_nullable, column_default
  from information_schema.columns where table_name like 'oauth%' order by table_name, ordinal_position;
-- restrições e índices
select conrelid::regclass, conname, pg_get_constraintdef(oid) from pg_constraint where conrelid::regclass::text like 'oauth%';
select tablename, indexname, indexdef from pg_indexes where tablename like 'oauth%';
-- clientes, SEM o segredo (só o tamanho)
select id, user_id, name, length(secret), left(redirect,30), personal_access_client, password_client, revoked
  from oauth_clients order by id;
```

Cinco tabelas em `public`, criadas pelo Passport 4 (sem chaves estrangeiras; só PK e índices):

| Tabela | Colunas (tipo, nulo) | Linhas em 12/11/2026 |
|---|---|---|
| `oauth_clients` | `id` integer serial; `user_id` integer null; `name` varchar(255); `secret` varchar(100) **not null**; `redirect` text; `personal_access_client` bool; `password_client` bool; `revoked` bool; `created_at`, `updated_at` timestamp null | 8 |
| `oauth_access_tokens` | `id` varchar(100) PK; `user_id` integer null; `client_id` integer; `name` varchar(255) null; `scopes` text null; `revoked` bool; `created_at`, `updated_at`, `expires_at` timestamp null | 58 (68 no fim do dia: logins de teste) |
| `oauth_refresh_tokens` | `id` varchar(100) PK; `access_token_id` varchar(100); `revoked` bool; `expires_at` timestamp null | 57 |
| `oauth_auth_codes` | `id` varchar(100) PK; `user_id` integer; `client_id` integer; `scopes` text null; `revoked` bool; `expires_at` timestamp null | 0 |
| `oauth_personal_access_clients` | `id` integer serial; `client_id` integer; `created_at`, `updated_at` timestamp null | 3 |

Índices além das PKs: `oauth_access_tokens(user_id)`, `oauth_clients(user_id)`, `oauth_personal_access_clients(client_id)`,
`oauth_refresh_tokens(access_token_id)`.

Clientes: ids 1–7 e **9999999** (o do login), todos com `user_id` nulo, `redirect = http://localhost`, não revogados.
1, 2, 4, 6 são de acesso pessoal (1 = `MatriculaOnline`); 3, 5, 7, 9999999 são de password grant. **Segredo: texto puro,
40 caracteres, nos 8.** Todos os tokens de acesso gravados foram emitidos pelo cliente 9999999.

O que **não** existe e as versões novas conhecem: `oauth_clients.provider` (12 e 13), `owner_type`/`owner_id`,
`redirect_uris`, `grant_types` (13), tabela `oauth_device_codes` (13).

## 2. O que cada versão lê e escreve (código-fonte da versão)

Fonte: tags `v12.4.3`, `v13.10.0` (a que o resolvedor escolhe) e `v13.11.0` (a mais nova) de `github.com/laravel/passport`.
As migrations da 13.10.0 e da 13.11.0 são idênticas (`diff -r database/`). Nas duas versões as migrations são só
**publicadas** (`publishesMigrations`), não rodam sozinhas.

| Ponto | Passport 4.0.3 (hoje, 5.6) | Passport 12.4.3 | Passport 13.10/13.11 |
|---|---|---|---|
| Esquema que a migration própria criaria | o atual | `bigIncrements`, `secret` **nullable**, `provider` novo | `uuid` no id, `owner` morph, `redirect_uris`, `grant_types`, sem `user_id`/`redirect`/`personal_access_client`/`password_client` |
| Precisa dessa migration para ler `oauth_clients`? | — | não | **não**: `Client::redirectUris()` cai para `redirect`; `Client::grantTypes()` monta a lista a partir de `password_client`/`personal_access_client`; `firstParty()` usa `user_id` se a coluna existir (`src/Client.php`). Guia oficial: *"fully backward compatible, no action is required"* |
| Id do cliente | integer | integer | UUID por padrão; `Passport::$clientUuids = false` mantém integer (configuração, sem migration) |
| Segredo do cliente | `hash_equals($record->secret, $clientSecret)` (texto puro) | `Passport::$hashesClientSecrets` falso por padrão → `hash_equals` (texto puro) | **sempre** `Hasher::check()` (`src/Bridge/ClientRepository.php::validateClient`); o guia manda rodar `passport:hash` = **escrita no banco** |
| Coluna `provider` | não usa | lê como atributo (nulo se não existe); só grava em `create()` | lê como atributo **e usa em SQL**: `ClientRepository::personalAccessClient()` e `HasApiTokens::tokens()` (`orWhereNull('provider')`) |
| `oauth_personal_access_clients` | lê (cliente pessoal mais recente) | lê (idem) | **não usa mais** (escolhe o cliente por `grant_types` + `provider`) |
| Grava em `oauth_access_tokens` | `id, user_id, client_id, scopes, revoked, created_at, updated_at, expires_at` | as mesmas | as mesmas (`created_at`/`updated_at` pelo Eloquent) — todas existem |
| Grava em `oauth_refresh_tokens` / `oauth_auth_codes` | `id, access_token_id, revoked, expires_at` / `id, user_id, client_id, scopes, revoked, expires_at` | as mesmas | as mesmas |
| Password grant | ligado | desligado por padrão: `Passport::enablePasswordGrant()` | idem |
| Rotas | `Passport::routes()` (o e-Cidade usa, prefixo `v4/oauth`) | `Passport::routes()` não existe mais (removido no 11) | idem |

As duas últimas linhas são mudança de **código** da aplicação (`app/Providers/AuthServiceProvider.php`), não de esquema.

## 3. Prova em execução (protótipo descartável, só leitura)

Vendors mínimos instalados fora da árvore versionada (`laravel/framework` + `laravel/passport`): Laravel 12.72.0 +
Passport 12.4.3, e Laravel 13.42.0 + Passport 13.10.0. Script `prova.php` (no fim deste arquivo), rodado no container do
PHP 8.5.12 na rede do banco:

```bash
docker run --rm --init --network e-cidade_ecidade -u "$(id -u):$(id -g)" -v $PWD:/p:ro ecidade-login-php85 \
  php /p/prova.php /p/proto13/vendor/autoload.php 13          # idem com proto12 ... 12
```

| Verificação | Passport 12.4.3 | Passport 13.10.0 (`$clientUuids = false`) |
|---|---|---|
| Ler os 8 clientes pelo model | ok (`password_client`, `personal_access_client` lidos) | ok: `redirect_uris = ["http://localhost"]`; clientes de password grant com `password` em `grant_types`, os pessoais com `personal_access`; todos `confidential` e `firstParty` |
| `Bridge\ClientRepository::validateClient('9999999', <segredo correto>, 'password')` | **sim** | **exceção** `RuntimeException: This password does not use the Bcrypt algorithm.` (`hashing.bcrypt.verify=true`, padrão do `config/hashing.php` do Laravel 13: `env('HASH_VERIFY', true)`); **não** com `verify=false` |
| `ClientRepository::personalAccessClient()` | id 6 (o mais recente de `oauth_personal_access_clients`, igual ao Passport 4) | **exceção** `QueryException: SQLSTATE[42703] … não existe a coluna "provider"` |
| Ler `oauth_access_tokens` pelo model | ok | ok (`scopes` como array, `expires_at`) |
| **Alternativa A1**: hasher de texto puro (`hash_equals`) só para `Bridge\ClientRepository` | — | segredo correto **sim**, segredo errado **não** |
| **Alternativa A2**: `personalAccessClient()` lendo `oauth_personal_access_clients` (sem `provider`) | — | id 6, `hasGrantType('personal_access')` sim |

Já medido antes (não repetido): o `league/oauth2-server` 8.5.5 (Passport 12.4) e o 9.4.1 (Passport 13) aceitam o token
emitido pelo Passport 4 do 5.6 (`laravel.md`, 16/10/2026).

O que o protótipo **não** cobre: o fluxo HTTP completo (`/v4/oauth/token` e rotas `auth:api` com o Laravel novo
inicializado — o `app/` ainda não sobe no Laravel 12/13) e a emissão de token (grava em `oauth_access_tokens`; fica para a
tarefa do login, dentro da exceção "token OAuth do login").

## 4. Alternativas (se a decisão for Laravel 13) e risco de cada uma

| # | Alternativa | Toca no banco? | Risco |
|---|---|---|---|
| **A** | **Passport 13 + duas sobrescritas no container da aplicação**: (A1) `$this->app->when(Laravel\Passport\Bridge\ClientRepository::class)->needs(Hasher::class)->give(<hasher de texto puro>)`; (A2) subclasse de `Laravel\Passport\ClientRepository` com `personalAccessClient()` lendo `oauth_personal_access_clients`, ligada no container. Mais `Passport::$clientUuids = false`, `Passport::enablePasswordGrant()` e o prefixo `v4/oauth` | não | (1) Contraria o Passport 13 (segredo com hash é o padrão de segurança dele); o comportamento fica **igual ao de hoje** (Passport 4 e 12 comparam texto puro), e a exposição do segredo é a decisão **(c)**. (2) Código próprio no caminho de autenticação: precisa de teste (login, segredo errado, cliente revogado) e revisão a cada atualização do Passport (as classes sobrescritas são internas). (3) Caso **#1912** (abaixo). (4) Qualquer outro uso de `provider` em SQL quebra: hoje só `HasApiTokens::tokens()`, que o `app/` não chama (busca por `->tokens(`) |
| B | Laravel **12** + Passport 12.4.3 | não | Funciona de fábrica (seção 3). O Laravel 12 está **sem correção de bugs desde 13/08/2026**; segurança até 24/02/2027 (`decisoes-pendentes.md`). Um segundo salto 12 → 13 fica para depois, com este mesmo problema |
| C | Rodar `passport:hash` (segredos com hash) e a migration do 13 | **sim** | Proibido pela regra do cliente. Além disso quebra o 5.6: o Passport 4 compara texto puro (`hash_equals`), e o gabarito deixaria de logar |
| D | Tabelas/visões novas para o Passport 13 (`Passport::useClientModel` com outra tabela) | **sim** | Proibido (esquema novo) |
| E | Sem Passport: validar o *bearer* direto com `league/oauth2-server` (já provado que aceita o token do 5.6) e emitir token por código próprio | não | Reescrever a parte do Passport que o e-Cidade usa (emissão no login, `createToken`, guard `auth:api`, `clientCredential`); maior esforço e mais código de segurança próprio |

**Caso #1912 (vale para A):** com ids inteiros, o `TokenGuard` do 13 recusa o usuário quando `id do usuário == id do cliente`
e o cliente tem `client_credentials` em `grant_types` (`src/Guards/TokenGuard.php::authenticateViaBearerToken`). Pelas colunas
antigas, os 8 clientes recebem `client_credentials` (todos têm segredo e `user_id` nulo). Em 12/11/2026 todos os tokens
gravados eram do cliente 9999999 e nenhum tinha `user_id = client_id` (a contagem de linhas muda a cada login: 58 → 68 no
dia, 82 na revisão); mas existem 6 usuários em `configuracoes.db_usuarios` com id entre 1 e 7 (1, 3, 4, 5, 6, 7).
**Risco concreto:** o `createToken()` usa o cliente pessoal 6 — o usuário de id 6 receberia um token que o guard do 13
recusa. Contorno sem migration: model de cliente próprio (`Passport::useClientModel`) tirando `client_credentials` dos
clientes que não o usam. Pendente: saber quais clientes os sistemas externos usam com `client_credentials`. Escopo do risco:
as rotas com o middleware `clientCredential` estão em **8 arquivos** (`grep -rlaF clientCredential ecidade/routes`):

| Área | Arquivo de rotas |
|---|---|
| Educação | `routes/api/educacao/central-de-matriculas.php` |
| Patrimonial | `routes/api/patrimonial/ouvidoria.php`, `routes/api/patrimonial/protocolo.php` |
| Saúde | `routes/api/saude/ambulatorial.php`, `routes/api/saude/laboratorio.php` |
| Tributário | `routes/api/tributario/arrecadacao.php`, `routes/api/tributario/cadastro.php`, `routes/api/tributario/itbi.php` |

## 5. Correção ao registro de 14/10/2026 (`laravel.md`)

`laravel.md` diz que "a migração [do Passport 13] apaga `user_id`, `redirect`, `personal_access_client`, `password_client`".
É a migration **opcional** do guia de upgrade; o Passport 13 roda sem ela. O que de fato impede o 13 no esquema atual, sem
código próprio, é o segredo com hash obrigatório e o uso da coluna `provider` em SQL (seção 3). A recomendação "usar Passport
12.4" continua valendo para o Laravel 12.

## Anexo: `prova.php`

Precisa de PHP ≥ 8.2 (roda só no runtime novo, com o vendor do Laravel 12/13; não faz parte da árvore do e-Cidade).

```php
<?php
/**
 * T-006: o Passport 12/13 sobre o esquema ATUAL de oauth_* (sem migration). SO LEITURA:
 * a sessao do PostgreSQL e posta em READ ONLY antes de qualquer consulta; nenhum segredo e impresso.
 * uso: php prova.php <vendor/autoload.php> <12|13>
 */
[$self, $autoload, $versao] = $argv;
require $autoload;

use Illuminate\Container\Container;
use Illuminate\Config\Repository;
use Illuminate\Database\Capsule\Manager as Capsule;
use Illuminate\Hashing\BcryptHasher;
use Laravel\Passport\Passport;
use Laravel\Passport\ClientRepository;

$app = new Container;
Container::setInstance($app);
$app->instance('config', new Repository([
    'auth' => ['guards' => ['api' => ['driver' => 'passport', 'provider' => 'users']],
               'providers' => ['users' => ['driver' => 'eloquent', 'model' => 'App\\User']]],
    'passport' => [],
]));

$db = new Capsule($app);
$db->addConnection(['driver' => 'pgsql', 'host' => 'ecidade_database', 'port' => 5432, 'database' => 'ecidade',
    'username' => 'postgres', 'password' => 'postgres', 'charset' => 'latin1']);
$db->setAsGlobal();
$db->bootEloquent();
$db->getConnection()->statement('SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY');
$ro = $db->getConnection()->selectOne('show transaction_read_only')->transaction_read_only;
echo "sessao read only: $ro\n";

if ($versao === '13') {
    Passport::$clientUuids = false;   // ids inteiros do esquema atual
}

$repo = $app->make(ClientRepository::class);
$sim = fn ($b) => $b ? 'sim' : 'nao';

echo "\n## clientes lidos pelo model do Passport $versao\n";
foreach (Passport::client()->newQuery()->orderBy('id')->get() as $c) {
    $linha = "id={$c->getKey()} confidential={$sim($c->confidential())} firstParty={$sim($c->firstParty())}";
    if ($versao === '13') {
        $linha .= ' redirect_uris=' . json_encode($c->redirect_uris) . ' grant_types=' . json_encode($c->grant_types);
    } else {
        $linha .= " password_client={$sim($c->password_client)} personal_access_client={$sim($c->personal_access_client)}";
    }
    echo $linha, "\n";
}

echo "\n## validacao do segredo do cliente do login (9999999) com o segredo CORRETO (o proprio valor gravado)\n";
$c = $repo->findActive(9999999);
$gravado = $c->getAttributes()['secret'];
echo 'formato gravado: ', (str_starts_with($gravado, '$2y$') ? 'bcrypt' : 'texto puro'), ', ', strlen($gravado), " caracteres\n";
if ($versao === '13') {
    foreach ([true, false] as $verify) {
        $bridge = new Laravel\Passport\Bridge\ClientRepository($repo, new BcryptHasher(['verify' => $verify]));
        $rotulo = "Bridge\\ClientRepository::validateClient(password) [hashing.bcrypt.verify=" . var_export($verify, true) . "]: ";
        try {
            $r = $sim($bridge->validateClient('9999999', $gravado, 'password'));
        } catch (Throwable $e) {
            $r = 'EXCECAO ' . get_class($e) . ': ' . $e->getMessage();
        }
        echo $rotulo, $r, "\n";
    }
} else {
    $bridge = new Laravel\Passport\Bridge\ClientRepository($repo);
    echo 'Bridge\\ClientRepository::validateClient(password): ', $sim($bridge->validateClient('9999999', $gravado, 'password')), "\n";
}

echo "\n## cliente de token pessoal (createToken, usado em App\\Domain\\Client\\Controllers\\ClientController)\n";
try {
    $pac = $versao === '13' ? $repo->personalAccessClient('users') : $repo->personalAccessClient();
    echo 'personalAccessClient: id=', $pac->getKey(), "\n";
} catch (Throwable $e) {
    echo 'personalAccessClient: EXCECAO ', get_class($e), ': ', strtok($e->getMessage(), "\n"), "\n";
}

echo "\n## leitura de oauth_access_tokens pelo model do Passport $versao\n";
$t = Passport::token()->newQuery()->orderBy('created_at', 'desc')->first();
echo 'ultimo token: client_id=', $t->client_id, ' revoked=', $sim($t->revoked), ' scopes=', json_encode($t->scopes),
    ' expires_at=', $t->expires_at, "\n";

if ($versao !== '13') {
    exit(0);
}

echo "\n## alternativa A (sem migration): sobrescritas no container, so codigo da aplicacao\n";
// A1: hasher do Bridge\ClientRepository que compara texto puro, como o Passport 4 (hash_equals) e o 12 (hashesClientSecrets=false)
$texto = new class implements Illuminate\Contracts\Hashing\Hasher {
    public function info($hashedValue) { return []; }
    public function make($value, array $options = []) { throw new LogicException('nao gera segredo'); }
    public function check($value, $hashedValue, array $options = []) { return is_string($hashedValue) && hash_equals($hashedValue, (string) $value); }
    public function needsRehash($hashedValue, array $options = []) { return false; }
};
$bridge = new Laravel\Passport\Bridge\ClientRepository($repo, $texto);
echo 'A1 validateClient(password) com hasher de texto puro: segredo correto=', $sim($bridge->validateClient('9999999', $gravado, 'password')),
    ' segredo errado=', $sim($bridge->validateClient('9999999', $gravado . 'x', 'password')), "\n";
// A2: ClientRepository sem a coluna provider: cliente pessoal mais recente de oauth_personal_access_clients (o que o Passport 4 e o 12 fazem)
$repoA2 = new class extends Laravel\Passport\ClientRepository {
    public function personalAccessClient(string $provider): Laravel\Passport\Client
    {
        $id = Illuminate\Database\Capsule\Manager::table('oauth_personal_access_clients')->orderBy('id', 'desc')->value('client_id');
        return $this->findActive($id) ?? throw new RuntimeException('Personal access client not found.');
    }
};
$pac = $repoA2->personalAccessClient('users');
echo 'A2 personalAccessClient sem a coluna provider: id=', $pac->getKey(), ' hasGrantType(personal_access)=', $sim($pac->hasGrantType('personal_access')), "\n";
```

Instalação dos vendors do protótipo (fora da árvore; `composer.json` só com `laravel/framework ^13.0` + `laravel/passport
^13.0`, ou `^12.0` + `^12.4`, `config.platform.php = 8.5.12`):

```bash
docker run --rm --init --network host -u "$(id -u):$(id -g)" -v $PWD/proto13:/w -w /w -e COMPOSER_HOME=/tmp/ch \
  ecidade-login-php85 composer update --no-scripts --no-plugins --no-interaction
```
