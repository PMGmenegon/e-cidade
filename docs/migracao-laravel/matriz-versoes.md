# Matriz de versões e resolução do Composer — Laravel 12 e 13, PHP 8.4 e 8.5

> T-005 (PB-002, critérios 1, 2 e 7), medido em 12/11/2026. Atualiza a medição de 14/10/2026 de
> `docs/registro/laravel.md` ("Laravel 12: 4 pacotes travados"). Não repete aquela medição: refaz a resolução para os quatro
> alvos com o Composer atual, separa conflito de versão de bloqueio por alerta de segurança e testa as alternativas.
>
> **Medido aqui:** só a resolução de dependências (metadados). "Resolve" **não** quer dizer que funciona: nenhum pacote foi
> instalado, nenhuma tela ou rota foi exercitada. O `composer.json`/`composer.lock` versionados e o `vendor/` dos runtimes não
> foram tocados.

## Resultado em uma linha por alvo

| Alvo | Resolve como está? | Pacotes que impedem | Pacotes no lock sem eles | Laravel escolhido |
|---|---|---|---|---|
| Laravel 12 / PHP 8.4 | não | 4 | 137 + 29 dev | v12.72.0 |
| Laravel 12 / PHP 8.5 | não | 4 | 137 + 29 dev | v12.72.0 |
| Laravel 13 / PHP 8.4 | não | 4 | 136 + 29 dev | v13.42.0 |
| Laravel 13 / PHP 8.5 | não | 4 | 136 + 29 dev | v13.42.0 |

Os quatro são os mesmos em todos os alvos e os mesmos de 14/10/2026: `dbseller/sdk-api-pix-bb`, `silex/silex`,
`dbseller/phinx_postgres`, `proner/phppimaco`.

- **PHP 8.4 × 8.5 não muda nada:** os locks de 8.4 e de 8.5 são idênticos, pacote a pacote, nos dois Laravel.
- **Laravel 12 × 13:** a diferença no conjunto resolvido é o próprio framework, a família Guzzle (L12: `guzzle` 7.16.1; L13:
  `guzzle` 8.4.0, `psr7` 3.3, `promises` 3.1, `uri-template` 2.0), `brick/math` 0.14 → 1.0 e Symfony 7.4 → 8.1 em
  `console`/`process`. Com o Laravel 13, o Symfony 8 exige **PHP ≥ 8.4.1**, então o 13 fica restrito a 8.4 e 8.5 (8.4.14 e
  8.5.12 resolvem).
- **Passport (critério 0):** o resolvedor dá Passport 12.4.3 e 13.10.0 com o Laravel 12, e **só o 13.x com o Laravel 13**
  (ver *Alternativas medidas*). Se o Passport 13 roda no esquema atual de `oauth_*` sem migration é a pergunta da **T-006**,
  que ainda não foi entregue (está na fila, depois desta). Esta matriz não responde a isso. Fato já registrado em `laravel.md`:
  a migration do Passport 13 apaga colunas de `oauth_clients` que o Passport 4 usa.

## 1. Matriz por pacote direto

Colunas: restrição do `composer.json` versionado; versão travada hoje no `composer.lock`; versão que o resolvedor escolheu
(com `*` no lugar da restrição) para cada Laravel e o `php` que ela declara; e se o pacote entra no conjunto resolvido em cada
alvo. "não" = é um dos 4 que impedem a resolução (seção 2). Gerada por `matriz/tabela.py` a partir dos quatro locks.

| Pacote direto | Restrição atual | Travada hoje | Candidata L12 | PHP exigido (L12) | Candidata L13 | PHP exigido (L13) | L12 8.4 | L12 8.5 | L13 8.4 | L13 8.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| `aferrandini/phpqrcode` | `^1.0` | 1.0.1 | `1.0.1` | `>=5.3.0` | `1.0.1` | `>=5.3.0` | sim | sim | sim | sim |
| `barryvdh/laravel-ide-helper` | `^2.4` | v2.4.3 | `v3.8.0` | `^8.2` | `v3.8.0` | `^8.2` | sim | sim | sim | sim |
| `dbseller/legacy` | `^1.0` | v1.1.1 | `v1.1.1` | (não declara) | `v1.1.1` | (não declara) | sim | sim | sim | sim |
| `dbseller/phinx_postgres` | `^1.3` | v1.3.0 | — | — | — | — | não | não | não | não |
| `dbseller/sdk-api-pix-bb` | `^1.0` | 1.0.0 | — | — | — | — | não | não | não | não |
| `dbseller/session` | `dev-master` | dev-master | `dev-master` | (não declara) | `dev-master` | (não declara) | sim | sim | sim | sim |
| `doctrine/dbal` | `2.*` | (ausente do lock) | `4.5.1` | `^8.2` | `4.5.1` | `^8.2` | sim | sim | sim | sim |
| `dompdf/dompdf` | `^0.8.3` | v0.8.3 | `v3.1.6` | `^7.1 \|\| ^8.0` | `v3.1.6` | `^7.1 \|\| ^8.0` | sim | sim | sim | sim |
| `guzzlehttp/guzzle` | `^6.2` | 6.5.8 | `7.16.1` | `^7.2.5 \|\| ^8.0` | `8.4.0` | `^7.4 \|\| ^8.0` | sim | sim | sim | sim |
| `intervention/image` | `^2.7` | 2.7.2 | `4.4.1` | `^8.3` | `4.4.1` | `^8.3` | sim | sim | sim | sim |
| `jeremeamia/superclosure` | `^2.0` | 2.4.0 | `2.4.0` | `>=5.4` | `2.4.0` | `>=5.4` | sim | sim | sim | sim |
| `laravel/framework` | `5.4.*` | v5.4.36 | `v12.72.0` | `^8.2` | `v13.42.0` | `^8.3` | sim | sim | sim | sim |
| `laravel/passport` | `^4.0` | v4.0.3 | `v13.10.0` | `^8.2` | `v13.10.0` | `^8.2` | sim | sim | sim | sim |
| `laravel/tinker` | `~1.0` | v1.0.10 | `v3.1.0` | `^8.1` | `v3.1.0` | `^8.1` | sim | sim | sim | sim |
| `lcobucci/jwt` | `3.3.3` | 3.3.3 | `5.6.1` | `~8.2.0 \|\| … \|\| ~8.5.0` | `5.6.1` | `~8.2.0 \|\| … \|\| ~8.5.0` | sim | sim | sim | sim |
| `league/fractal` | `0.11.0` | 0.11.0 | `0.21` | `>=7.4` | `0.21` | `>=7.4` | sim | sim | sim | sim |
| `michelf/php-markdown` | `^1.6` | 1.9.1 | `2.0.0` | `>=7.4` | `2.0.0` | `>=7.4` | sim | sim | sim | sim |
| `mormat/php-formula-interpreter` | `1.0.0` | v1.0.0 | `v2.0.1` | `>=8.1` | `v2.0.1` | `>=8.1` | sim | sim | sim | sim |
| `mpdf/mpdf` | `v7.1.9` | v7.1.9 | `v8.3.1` | `^5.6 \|\| … \|\| ~8.5.0` | `v8.3.1` | `^5.6 \|\| … \|\| ~8.5.0` | sim | sim | sim | sim |
| `ncjoes/office-converter` | `^1.0` | v1.0.3 | `1.0.8` | `^7.3\|^8.0` | `1.0.8` | `^7.3\|^8.0` | sim | sim | sim | sim |
| `nfephp-org/sped-common` | `~5.0.40` | v5.0.40 | `v5.1.17` | `>= 7.4` | `v5.1.17` | `>= 7.4` | sim | sim | sim | sim |
| `phpmailer/phpmailer` | `^6.5` | v6.9.1 | `v7.2.0` | `>=5.5.0` | `v7.2.0` | `>=5.5.0` | sim | sim | sim | sim |
| `phpoffice/phpspreadsheet` | `^1.08` | 1.8.2 | `5.11.0` | `^8.2` | `5.11.0` | `^8.2` | sim | sim | sim | sim |
| `phpoffice/phpword` | `v0.17.*` | 0.17.0 | `1.4.0` | `^7.1\|^8.0` | `1.4.0` | `^7.1\|^8.0` | sim | sim | sim | sim |
| `proner/phppimaco` | `1.3.0` | v1.3.0 | — | — | — | — | não | não | não | não |
| `pusher/pusher-php-server` | `~2.6` | 2.6.4 | `7.3.0` | `^7.3\|^8.0` | `7.3.0` | `^7.3\|^8.0` | sim | sim | sim | sim |
| `silex/silex` | `^2.0` | v2.2.4 | — | — | — | — | não | não | não | não |
| `symfony/console` | `~3.2` | v3.4.47 | `v7.4.23` | `>=8.2` | `v8.1.11` | `>=8.4.1` | sim | sim | sim | sim |
| `symfony/filesystem` | `~3.2` | v3.4.47 | `v8.1.11` | `>=8.4.1` | `v8.1.11` | `>=8.4.1` | sim | sim | sim | sim |
| `symfony/polyfill-php56` | `^1.1` | v1.19.0 | `v1.20.0` | `>=7.1` | `v1.20.0` | `>=7.1` | sim | sim | sim | sim |
| `symfony/polyfill-php70` | `^1.1` | v1.19.0 | `v1.20.0` | `>=7.1` | `v1.20.0` | `>=7.1` | sim | sim | sim | sim |
| `symfony/process` | `~3.2` | v3.4.47 | `v7.4.22` | `>=8.2` | `v8.1.10` | `>=8.4.1` | sim | sim | sim | sim |
| `symfony/validator` | `~3.2` | v3.4.47 | `v8.1.11` | `>=8.4.1` | `v8.1.11` | `>=8.4.1` | sim | sim | sim | sim |
| `symfony/yaml` | `~3.2` | v3.4.47 | `v8.1.11` | `>=8.4.1` | `v8.1.11` | `>=8.4.1` | sim | sim | sim | sim |
| `vlucas/valitron` | `^1.4` | v1.4.11 | `v1.4.11` | `>=5.3.2` | `v1.4.11` | `>=5.3.2` | sim | sim | sim | sim |
| `zendframework/zend-eventmanager` | `2.2.10` | 2.2.10 | `2.6.2` | `>=5.5` | `2.6.2` | `>=5.5` | sim | sim | sim | sim |
| `filp/whoops` (dev) | `^2.5` | 2.15.4 | `2.19.3` | `^7.1 \|\| ^8.0` | `2.19.3` | `^7.1 \|\| ^8.0` | sim | sim | sim | sim |
| `fzaninotto/faker` (dev) | `^1.9` | v1.9.2 | `v1.5.0` | `>=5.3.3` | `v1.5.0` | `>=5.3.3` | sim | sim | sim | sim |
| `mockery/mockery` (dev) | `1.3.0` | 1.3.0 | `1.6.15` | `>=7.3` | `1.6.15` | `>=7.3` | sim | sim | sim | sim |
| `phpunit/phpunit` (dev) | `^5.7` | 5.7.27 | `10.5.66` | `>=8.1` | `10.5.66` | `>=8.1` | sim | sim | sim | sim |
| `squizlabs/php_codesniffer` (dev) | `^3.5` | 3.9.0 | `4.0.4` | `>=7.2.0` | `4.0.4` | `>=7.2.0` | sim | sim | sim | sim |

Os 13 `ext-*` e o `php` raiz ficam fora da tabela: todas as extensões exigidas estão no runtime 8.5 (`php -m` da imagem
`ecidade-login-php85`) e o resolvedor não as acusou.

### "Resolve, mas…" — pacotes que entram no lock e ainda são problema

O resolvedor só lê metadados. Estes entram no conjunto resolvido e mesmo assim precisam de decisão ou de teste:

| Pacote | O que o resolvedor escolheu | Por que não basta |
|---|---|---|
| `zendframework/zend-eventmanager` | 2.6.2 + `zend-stdlib` 2.7.4 (abandonados → `laminas/*`) | `zend-stdlib` é o que dá `PriorityQueue::count() return type` sob o PHP 8 (`laravel.md`, bloqueador do login). Declara `>=5.5`, sem teto. Alternativa: `laminas/laminas-eventmanager` 3.16 (`~8.3–8.6`); uso em 6 arquivos (`src/V3/Event`, `src/V3/Error`, 2 extensões, 1 teste). |
| `fzaninotto/faker` (dev) | **v1.5.0** — volta para uma versão mais velha que a travada (1.9.2), só porque ela não declara teto de PHP | Abandonado. Alternativa: `fakerphp/faker` 1.24 (`^7.4 \|\| ^8.0`). |
| `jeremeamia/superclosure` | 2.4.0 (abandonado → `opis/closure`) | Declara `>=5.4`; serializa closures por Reflection. Uso: `src/Task/Closure.php` e `bin/background-worker`. Testar ou trocar. |
| `aferrandini/phpqrcode` | 1.0.1 (abandonado → `endroid/qr-code`) | Declara `>=5.3.0`. Uso: 6 modelos em `fpdf151/impmodelos/`. Testar os QR codes. |
| `dbseller/legacy`, `dbseller/session` | v1.1.1, dev-master (`f3020b4`) | Não declaram PHP. Legacy: `app.php`, `src/V3/Extension/Front.php`; Session: `api/V1/Middleware/Session/SessionMiddleware.php`, `src/Lib/Session/DefaultSession.php`. Testar. |
| `phpunit/phpunit` (dev) | 10.5.66 | A suíte (`tests/`) é escrita para PHPUnit 5. Adaptar testes (PB-003). |
| Saltos de major em uso real | `phpspreadsheet` 1.8 → 5.11 (25 arquivos), `phpword` 0.17 → 1.4 (11), `dompdf` 0.8 → 3.1 (2), `mpdf` 7 → 8 (2), `intervention/image` 2 → 4 (2), `fractal` 0.11 → 0.21 (10), `phpmailer` 6 → 7 (2), `formula-interpreter` 1 → 2 (3), `symfony/console` 3 → 7/8 (20) | Resolvem; o código que os usa precisa de porte e teste (PB-012 para PDF/planilha/Word). |

Candidatos a **remoção com prova de não uso** (busca estática em `ecidade/`, sem `vendor/`, `tmp/`, `storage/`; precisa de
confirmação em execução antes de remover):

| Pacote | Uso encontrado | Observação |
|---|---|---|
| `doctrine/dbal` | 0 referências a `Doctrine\DBAL`; nenhuma das 452 migrations em `database/migrations` usa `->change()`/`renameColumn` | Laravel 11+ não depende mais do DBAL para alterar colunas. Também explica a ausência no lock (era requisito sem uso). |
| `pusher/pusher-php-server` | 0 usos; só `configuration/broadcasting.php` declara o driver; `BROADCAST_DRIVER=log` no `.env.example`; `App\Providers\BroadcastServiceProvider` comentado em `configuration/app.php` | — |
| `symfony/filesystem` | 0 referências a `Symfony\Component\Filesystem` | Pode continuar como dependência indireta. |
| `lcobucci/jwt` | 0 referências diretas a `Lcobucci\JWT` | Vem pelo Passport/`league/oauth2-server`; o pin direto `3.3.3` só serve para travar. |

## 2. O que impede a resolução e a alternativa de cada pacote

Cada conflito foi conferido de duas formas: com o padrão do Composer 2.11.1 (bloqueia versões com alerta de segurança,
`policy.advisories.block`) e com esse bloqueio **desligado** (`@semblock` em `matriz/gera.py`), para separar "versão
incompatível" de "versão insegura".

| Pacote | Por que não resolve (saída do resolvedor) | Sem o bloqueio por alerta | Uso no código | Alternativas |
|---|---|---|---|---|
| `dbseller/sdk-api-pix-bb` | 1.0.0 exige `guzzle ^6.2`; 2.0.0, 3.0.0 (12/10/2026) e os ramos `dev-master`/`dev-php8`/`dev-php74` exigem `guzzle 7.5.0` exato. Laravel 12 e 13 exigem `guzzle ^7.8.2` (13: `\|\| ^8.0`). | **continua travado** (conflito de versão, não só alerta) | 1 arquivo: `app/Domain/Tributario/Arrecadacao/Pix/Bancos/BancoDoBrasil.php` (5 classes `Swagger\Client`) | (a) versão do SDK com `guzzle ^7.8` (pedir à DBSeller, ou fork mudando a restrição: é cliente Swagger gerado); (b) trocar por chamadas diretas com o Guzzle do Laravel em `BancoDoBrasil.php`; (c) isolar o Pix em processo separado. Remover: não (em uso). Decisão **g** (PB-013); teste só em sandbox/dublê. |
| `silex/silex` | 2.0–2.2.4 exigem Symfony `~2.8\|^3.0`; 2.3.0 e `dev-master` exigem Symfony `^4.0`; não há 3.x. Laravel 12/13 exigem Symfony 7/8. | **continua travado** | 22 arquivos citam `Silex\`: **19 em `api/V1` + `api/api.php` = 20 com uso real** (mesma conta da T-007); mais `app.php` (`use Silex\Application`, import sem uso) e `model/agendaPagamento.model.php:2792` (só um `@param` em docblock) | Substituir o Silex na `api/V1` — escopo da **T-007** (Back3, spike do Silex) e do PB-011. Remover: não (em uso). |
| `dbseller/phinx_postgres` | Todas as versões exigem `robmorgan/phinx v0.4.6` (Symfony `~2.7`) ou `^0.10` (`cakephp/database ^3.6`, Symfony ≤ 4). | **continua travado** | **1.510** migrations de `db/migrations` estendem `Classes\PostgresMigration` (o 1.511º arquivo da pasta é `db/migrations/index.php`); o pacote são 2 classes, 185 linhas (`PostgresMigration`, `Table`) | (a) **`robmorgan/phinx` 0.16.12 direto** (Symfony `^6\|^7\|^8`) — **resolve** com L12 e L13 (*Alternativas medidas*) — mais as 2 classes portadas (fork do pacote ou classe própria com o mesmo nome); (b) manter as migrations fora do vendor do runtime novo (rodam pelo 5.6). Remover: não. Não testável executando migrations (regra "não tocar no banco"): só carga das classes e `--dry-run`, se houver. PB-014. |
| `proner/phppimaco` | 1.3.x exige `mpdf ^7.1` (PHP ≤ 7.3); 1.4.x exige `endroid/qr-code ^2.5` → `bacon/bacon-qr-code` 1.0.3 (PHP `^5.4\|^7.0`); ≤ 1.2.3 exige `mpdf ^6.1` (alerta PKSA-7967-nbfd-sbj6). | **resolve**, com `phppimaco` 1.2.3 + `mpdf` 6.1.3 — versão com alerta de segurança e mPDF 6 (declara só `>=5.4.0`). **Não é saída.** | 4 arquivos em `app/Domain/Patrimonial/Patrimonio` (etiquetas Pimaco); pacote 759 linhas | (a) fork com `endroid/qr-code` atual e `mpdf ^8`; (b) refazer o layout de etiqueta direto sobre o `mpdf` 8.3.1 (já resolvido). Remover: não. PB-012. |

### Alternativas medidas no resolvedor (PHP 8.5, sem os 4 acima, com `robmorgan/phinx` direto)

| Cenário | Resultado | Versões |
|---|---|---|
| Laravel 12 + `laravel/passport ^12.4` | **resolve** (173 pacotes no lock, com dev) | Passport 12.4.3, `league/oauth2-server` 8.5.5, `lcobucci/jwt` 5.6.1, Phinx 0.16.12, Guzzle 7.16.1 |
| Laravel 13 + `laravel/passport ^12.4` | **não resolve** | 12.4.3 exige `illuminate/* ^9.21\|^10\|^11\|^12`; 12.4.0–12.4.2 exigem `firebase/php-jwt ^6.4`, bloqueado por alerta (PKSA-y2cr-5h3j-g3ys) |
| Laravel 13 + `laravel/passport ^13.0` | **resolve** (174) | Passport 13.10.0, `league/oauth2-server` 9.4.1, Phinx 0.16.12, Guzzle 8.4.0 |

Consequência para a decisão **a** (Laravel 12 × 13): com o Laravel 13, a única opção de Passport é a 13.x. Se ela roda sobre o
esquema atual sem migration é a **T-006**. Os dois `league/oauth2-server` (8.5.5 e 9.4.1) já aceitaram o token do
Passport 4 (`laravel.md`, teste de 16/10/2026).

## 3. Diferenças em relação à medição de 14/10/2026

| | 14/10/2026 (`laravel.md`) | 12/11/2026 (esta) |
|---|---|---|
| Alvos | Laravel 12, PHP 8.5 | Laravel 12 e 13 × PHP 8.4 e 8.5 |
| Composer | — | 2.11.1, que **bloqueia por padrão** versões com alerta de segurança |
| Travados | os mesmos 4 | os mesmos 4, nos 4 alvos |
| Resolvidos | 135 pacotes; Laravel 12.70, Passport 13.10 | 137 + 29 dev (L12), 136 + 29 dev (L13); Laravel 12.72.0 / 13.42.0; Passport 13.10.0 |
| Pimaco | "mpdf 7, PHP ≤ 7.3" | 1.4.x trava por `bacon/bacon-qr-code` (PHP 7); sem bloqueio por alerta resolve com 1.2.3 + mPDF 6.1.3 (inseguro) |
| Pix BB | "guzzle 6, ou 7.5.0 com alertas" | até a 3.0.0 de 12/10/2026 exige `guzzle 7.5.0` exato; conflita com `^7.8.2` mesmo sem o bloqueio |
| Phinx | — | `robmorgan/phinx` 0.16.12 direto resolve com L12 e L13 |

## 4. Como reproduzir

Scripts em [`matriz/`](matriz/) (cópia descartável fora da árvore versionada; o `vendor/` dos runtimes não é usado):

```bash
T=/tmp/t005; mkdir -p $T && cp docs/migracao-laravel/matriz/* $T/
cp -r ecidade/vendor/dbseller/session $T/session-src      # commit travado f3020b4 do Session (o repo do composer.json é SSH)
# ^ precisa de vendor/: worktree preparada (prepara-worktree.sh) ou ~/git/e-cidade/ecidade/vendor/dbseller/session
O=$PWD/ecidade/composer.json; cd $T
./elimina.py $O l12-84 12 8.4      # idem: l12-85 12 8.5 | l13-84 13 8.4 | l13-85 13 8.5
./elimina.py $O x12-85-semblock 12 8.5 @semblock          # mesmo laço sem o bloqueio por alerta de segurança
B="-dbseller/sdk-api-pix-bb -silex/silex -dbseller/phinx_postgres -proner/phppimaco robmorgan/phinx=*"
./gera.py $O alt12-p124 12 8.5 $B 'laravel/passport=^12.4' && ./resolve.sh alt12-p124
./gera.py $O alt13-p124 13 8.5 $B 'laravel/passport=^12.4' && ./resolve.sh alt13-p124
./gera.py $O alt13-p13  13 8.5 $B 'laravel/passport=^13.0' && ./resolve.sh alt13-p13
./tabela.py $O ${O%.json}.lock l12-84 l12-85 l13-84 l13-85 > matriz.md
```

- `gera.py`: copia o `composer.json`, põe `laravel/framework ^N.0` e `*` em todo outro requisito direto, troca o repositório
  SSH do Session por `path`, fixa o PHP do alvo em `config.platform.php` (8.4.14 ou 8.5.12).
- `resolve.sh`: `composer update --no-install --no-scripts --no-plugins` no container `ecidade-login-php85` (PHP 8.5.12,
  Composer 2.11.1). Sucesso = existir `composer.lock` (lição de 14/10: erro de clone não pode contar como "resolveu").
- `elimina.py`: resolve; se falhar, tira o pacote raiz citado no primeiro problema e repete. Cada rodada fica em
  `<alvo>/rodada-N.txt`.
- O PHP 8.4 é simulado com `config.platform.php` no container 8.5 (mecanismo do próprio Composer); as extensões são as reais
  do container. Nenhuma imagem 8.4 foi baixada.

**Armadilhas do instrumento** (custaram 40 min nesta medição):
1. A rede `bridge` do Docker desta máquina não resolve DNS: o Composer fica parado em "Loading composer repositories" com 0%
   de CPU, sem erro. Solução: `--network host`.
2. `timeout` não derruba o `docker run`: o PHP é PID 1 no container e ignora SIGTERM. Solução: `--init`.
3. `pkill -f <padrão>` mata o próprio shell que o chamou se o padrão aparecer na linha de comando dele.

## 5. O que esta matriz não prova

- Que os pacotes resolvidos funcionam no PHP 8.4/8.5 ou com o código do e-Cidade: nada foi instalado nem executado.
- Que o Passport 13 roda sem migration: **T-006**.
- O caminho do Silex: **T-007**.
- O resultado com o lock de verdade: a matriz usa `*` para achar o teto de cada pacote; a restrição final de cada um é
  decisão das tarefas de upgrade (PB-007/PB-008).
