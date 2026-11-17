# API V1 (Silex) no PHP 8.5 com `vendor/` separado — medição para a decisão (j) (T-033)

> 13/11/2026. Parte da T-007 (`silex-caminhos-e-suporte.md`: 7 rotas, opções A/B/C1/C2) e da linha de base
> da T-012 (`docs/registro/testes-sistema-rotas.md`, branch `testes/T-012-sistema-rotas`: 4 GET, 2 × 200 e 2 × 500 iguais
> 5.6 × 8.5). Nada do projeto foi alterado: o `vendor/` da API foi montado num diretório descartável e sobreposto num
> container 8.5 próprio. Regra da decisão (cliente): **Silex isolado roda no 8.5 com resposta igual à do 5.6 →
> manter (A); senão → passar as 7 rotas ao Laravel 13 (C1).**

## Resultado (rota a rota)

| # | Rota | 5.6 (gabarito) | 8.5, vendor de hoje (Silex 2.2.4 + Symfony 3.4) | 8.5, vendor só da API (Silex 2.3.0 + Symfony 4.4), **sem** a T-026 | 8.5, vendor só da API, **com** a T-026 |
|---|---|---|---|---|---|
| 1 | `GET /api/v1/configuracao/formulario/1/instituicao/1` | 500 JSON "Formulário de código 1 não existe no cadastro do e-cidade." | **igual** | **diferente**: 200 `text/html` corpo vazio | **igual** |
| 2 | `GET /api/v1/matriculaonline/emissaoProtocolo` | 500 JSON "Sem permissão para acessar a API." | **igual** | **diferente**: 200 `text/html` corpo vazio | **igual** |
| 3 | `GET /api/v1/protocolo/cgm` | 200 JSON | **igual** (corpo idêntico byte a byte) | **igual** (idem) | **igual** (idem) |
| 4 | `GET /api/v1/protocolo/cgm/1` | 200 JSON | **igual** (idem) | **igual** (idem) | **igual** (idem) |
| 5 | `POST /api/v1/auth/login` | não chamada (grava token/sessão própria) | — | — | — |
| 6 | `POST /api/v1/tributario/recibo` | não chamada (grava recibo) | — | — | — |
| 7 | `POST /api/v1/matriculaonline/inscricao` | não chamada (grava inscrição) | — | — | — |

"Igual" = critério da T-012: mesmo status, mesmo `Content-Type` e mesmo corpo depois de tirar `access_token`,
`refresh_token`, `expires_in`, `trace`, `stacktrace`, `file`, `line`. Nas rotas 1 e 2 o único campo que difere é o
`stacktrace` (o `$app['debug'] = true` do `api/api.php:39` devolve a pilha): ele já difere entre 5.6 e 8.5 com o **mesmo**
vendor (5.6: 9 e 13 linhas; 8.5: 8 e 12 — o 5.6 lista o `call_user_func_array` interno), e no Symfony 4.4 os quadros e
linhas de `HttpKernel.php` são outros. É diferença de ambiente, a mesma que a T-012 já exclui.

As duas variantes do vendor da API (tags estáveis e `4.4.x-dev`, ver abaixo) responderam igual entre si nas 4 rotas.

**Leitura para a regra da decisão:** a API V1 isolada **roda no 8.5 e responde igual ao 5.6 nas 4 rotas GET medidas,
desde que a correção da T-026 (handler de erro V3) esteja no código**. Sem ela, as 2 rotas que respondem com erro mudam
(200 vazio no lugar do 500 JSON). A T-026 é correção do núcleo exigida pelo sistema inteiro no PHP 8 (não é específica da
API) e está em Revisão. As 3 rotas POST não foram medidas (gravam) — lacuna, igual à da T-012. Pela regra: **A (manter)**,
condicionada à integração da T-026.

## 1. Resolvedor do Composer no 8.5 (critério 1)

**O que a API carrega de fato.** Medido no 8.5 com o vendor de hoje (`auto_prepend_file` só no container de teste, gravando
`get_included_files()` dos pedidos a `/api/v1/`; retirado depois). Dos 101 arquivos `files` do autoload, a API não precisa
de nenhum pacote só por eles; com classe carregada pelas 4 rotas: `silex/silex`, `pimple/pimple`,
`symfony/http-foundation`, `symfony/http-kernel`, `symfony/routing`, `symfony/event-dispatcher`, `symfony/finder`,
`league/fractal`, `zendframework/zend-eventmanager` (núcleo V3), `dbseller/session`, `dbseller/legacy` (funções de
compatibilidade em `bootstrap/PHP_5x.php`) e `cakephp/utility` (só pelo `bootstrap.php` do próprio pacote — dispensável).
Nenhum `laravel/*`.

**`composer.json` descartável** (no 8.5: container `ecidade-login-php85`, PHP 8.5.12, Composer 2.10.3). Os dois pacotes
`dbseller/*` vêm por repositório `path` (cópia do vendor de hoje), porque o `dbseller/session` está num repositório Git
privado:

```json
{
    "name": "t033/api-v1-vendor",
    "repositories": [
        {"type": "path", "url": "pkgs/legacy", "options": {"symlink": false, "versions": {"dbseller/legacy": "1.1.1"}}},
        {"type": "path", "url": "pkgs/session", "options": {"symlink": false, "versions": {"dbseller/session": "dev-master"}}}
    ],
    "require": {
        "silex/silex": "*", "league/fractal": "0.11.0", "zendframework/zend-eventmanager": "2.2.10",
        "symfony/finder": "*", "cakephp/utility": "*", "dbseller/legacy": "1.1.1", "dbseller/session": "dev-master"
    },
    "minimum-stability": "dev", "prefer-stable": true,
    "autoload": { "files": ["app/Helpers/... (os 7 do ecidade/composer.json)"], "classmap": ["database"],
                  "psr-4": {"App\\": "app/", "Fpdf\\": "fpdf/"} },
    "config": {"sort-packages": true}
}
```

```bash
P=<pasta descartavel>; W=<worktree>/ecidade            # pkgs/legacy e pkgs/session = cp -a $W/vendor/dbseller/{legacy,session}
mkdir -p $P/app $P/database $P/fpdf
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e COMPOSER_CACHE_DIR=/cache -v $HOME/.cache/composer:/cache \
  -v ~/.local/bin/composer:/usr/local/bin/composer:ro -v $P:/proj -v $W/app:/proj/app:ro -v $W/database:/proj/database:ro \
  -v $W/fpdf:/proj/fpdf:ro -w /proj --entrypoint php ecidade-login-php85 /usr/local/bin/composer update --no-interaction --no-scripts
```

**Resolve.** 31 pacotes, 8,6 MB (o vendor do projeto tem 247 MB). Versões:

| Pacote | Hoje (lock do projeto) | Vendor da API no 8.5 |
|---|---|---|
| `silex/silex` | 2.2.4 | **2.3.0** (último release; abandonado desde 2018) |
| `symfony/http-foundation` | 3.4.47 | **4.4.49** (variante estável) / `4.4.x-dev` (padrão) |
| `symfony/http-kernel` | 3.4.49 | **4.4.51** / `4.4.x-dev` |
| `symfony/routing` | 3.4.47 | **4.4.44** / `4.4.x-dev` |
| `symfony/event-dispatcher` | 3.4.47 | 4.4.44 |
| `symfony/debug` / `error-handler` | 3.4 / — | 4.4.44 / 4.4.44 |
| `pimple/pimple` | 3.2.3 | 3.6.2 |
| `league/fractal` | 0.11.0 | 0.11.0 (fixo, como no projeto) |
| `zendframework/zend-eventmanager` (+ `zend-stdlib`) | 2.2.10 | 2.2.10 (abandonado) |
| `cakephp/utility` (+ `core`) | 3.10.5 (exige PHP `<8.0`) | 5.4.4 |
| `symfony/finder` | 3.4.47 | 8.1.11 |
| `dbseller/legacy` / `dbseller/session` | 1.1.1 / dev-master | os mesmos (cópia) |

**O que impede a versão estável por padrão.** Toda a série 4.x de `http-foundation`, `http-kernel` e `routing` tem alerta
de segurança aberto **sem correção na 4.x** (correções só em 5.4.5x+, 6.4.4x+, 7.4.2x+, 8.1.11): `composer audit` lista 8
alertas em 3 pacotes (ex.: CVE-2025-64500 `PATH_INFO` — alta; CVE-2026-118516, CVE-2026-48784, CVE-2026-45065 em
`routing`; CVE-2026-123339 em `http-kernel`). O Composer 2.10 bloqueia versões com alerta (`audit.block-insecure`, padrão
ligado) e cai no ramo `4.4.x-dev` (código não lançado, sem suporte). Com `"config": {"audit": {"block-insecure": false}}`
resolve com as tags estáveis acima. As duas variantes foram medidas e responderam igual. Os mesmos alertas já valem para o
Symfony 3.4 do vendor de hoje (alertas herdados, já presentes no 5.6).

## 2. Rotas no 8.5 com esse vendor (critério 2)

Containers de teste (5.6 `:8110`, 8.5 `:8111`) e dois 8.5 com o vendor da API **no lugar** do
`vendor/` (`:8113` = `4.4.x-dev`, `:8114` = tags estáveis), todos gravando, com o vigia em volta de cada rodada:

```bash
docker run -d --name ecidade_back1_apiest --network e-cidade_ecidade -p 8114:80 -e DB_HOST=ecidade_database -e DB_PORT=5432 \
  -e DB_DATABASE=ecidade -e DB_USERNAME=postgres -e DB_PASSWORD=postgres -v $W:/var/www/html -v $P/vendor:/var/www/html/vendor:ro \
  -v <quadro>/../docker/php85-apache/paridade-56.ini:/usr/local/etc/php/conf.d/zz-paridade-56.ini:ro ecidade-login-php85
docker exec ecidade_back1_apiest sh -c 'mkdir -p /var/lib/php/sessions && chmod 1733 /var/lib/php/sessions'
bash <quadro>/ferramentas/vigia-banco.sh antes foto
docker exec -u root ecidade_back1_56 php /root/t033/api.php /root/t033/out 56=http://ecidade_back1_56 85=http://ecidade_back1_85 \
  apidev=http://ecidade_back1_apidev apiest=http://ecidade_back1_apiest
bash <quadro>/ferramentas/vigia-banco.sh depois foto
```

O instrumento (`api.php`, anexo) usa o `tests/sistema/Cliente.php` da T-012 sem mudança: token do password grant pedido ao
5.6 e enviado a todos, sessão legada (`login.php` + `abrir.php`) feita em cada runtime, `{param}` → `1`, e o `resumo()` da
T-012 para comparar. Cada rodada: 1 token + 4 logins + 4 × 4 GET.

**Causa da diferença sem a T-026 (rotas 1 e 2).** Reproduzido em linha de comando no container descartável:

```
ArgumentCountError: Too few arguments to function ECidade\V3\Error\Handler\Error::_handle(), 4 passed and exactly 5 expected
#0 [internal function]: ECidade\V3\Error\Handler\Error::_handle(16384, 'The "Symfony\\Co...', ...)
#1 vendor/symfony/http-kernel/Event/GetResponseForExceptionEvent.php(57): trigger_error('The "Symfony\\Co...', 16384)
#2 vendor/silex/silex/src/Silex/ExceptionListenerWrapper.php(44): ...GetResponseForExceptionEvent->getException()
```

O Silex 2.3 chama `getException()`, que no Symfony 4.4 avisa `E_USER_DEPRECATED` com `@trigger_error`; o handler V3 é
chamado com 4 argumentos e quebra, e a resposta de erro nunca é montada (o pedido termina com status 200, corpo vazio e um
`ob` aberto, sem nada no `error.log`). Com a T-026 (`$context = null` e o `@` reconhecido no PHP 8) o aviso é tratado como
suprimido, como no 5.6, e o `$app->error()` devolve o mesmo 500 JSON. A medição "com a T-026" usou uma branch temporária
(`laravel/T-033-…` + merge de `nucleo/T-026-handler-erro-php8`, commit `de84284af`), apagada depois; nada dela ficou.

**Vigia (critério 5).** Todas as rodadas com `rc=0`. A das 4 rotas × 4 runtimes com a T-026:

```
foto: 4230 tabelas
mudaram: 3 tabela(s)
  configuracoes.db_logsacessa_202611_0 1
  public.oauth_access_tokens 1
  public.oauth_refresh_tokens 1
OK: so tabelas permitidas
vigia rc=0
```

## 3. O que precisaria mudar para ficar igual (critério 3) — nada foi mudado

| Onde | O quê | Por quê |
|---|---|---|
| `ecidade/src/V3/Error/Handler/Error.php:20` e `:27` | a correção da **T-026** (`$context = null`; suprimido = só bits fatais em `error_reporting()`) | sem ela, rotas 1 e 2 diferem (acima). Já feita, em Revisão — nada novo a fazer na API |
| `ecidade/bootstrap.php:26` (`require_once(ECIDADE_PATH . 'vendor/autoload.php')`) e `ecidade/bootstrap/autoload.php` (`require __DIR__.'/../vendor/autoload.php'`) | **só se** a API rodar no **mesmo** processo/container do Laravel novo: escolher o autoload da API quando a entrada é `FrontController.php:4-5` (`api/vN/` → `api/api.php`) | Silex 2.3 exige Symfony 4.4; o Laravel 13 usa Symfony 7. Os dois não convivem no mesmo processo (mesmos namespaces `Symfony\Component\*`). **Alternativa sem mudar código:** um runtime só para `/api/v1/*` com o vendor da API montado no lugar do `vendor/` (o mecanismo da T-022, `docker-compose.runtime-novo.yml`) e a regra de rota no proxy — foi o que esta medição fez |
| `ecidade/api/composer.json` (novo, fora do código do sistema) ou equivalente | o `composer.json` acima, com decisão explícita sobre `audit.block-insecure` (ou aceitar `4.4.x-dev`) | o Composer recusa as tags estáveis da 4.4 por padrão |

Não exigem mudança para ficar igual hoje (avisos `E_DEPRECATED`, fora da máscara do handler, sem efeito na saída; ficam
como risco de versão futura do PHP): `ecidade/std/DBString.php:793` (`utf8_encode`, deprecado desde 8.2, usado pelo
`$app->error()` em `api/api.php:100`), `ecidade/src/V3/Extension/ParameterBag.php:133,142` (tipos de retorno),
`vendor/zendframework/zend-stdlib/src/SplPriorityQueue.php:37` (tipo de retorno), `config/application.default.php:27`
(`E_STRICT` deprecado desde 8.4).

## 4. Esforço das duas opções com base na medição (critério 4)

| | **A. Manter o Silex em vendor separado** | **C1. Passar as 7 rotas ao Laravel 13** |
|---|---|---|
| Medido aqui | roda no 8.5 e responde igual nas 4 GET (com a T-026) | — (T-007; depende de o Laravel novo inicializar, o que hoje não acontece) |
| Tarefas **[estimativa]** | **2–3**: (1) `composer.json`/lock da API versionados, com a decisão do `block-insecure`; (2) runtime da API (container com o vendor dela, regra `/api/v1/` no proxy) ou a troca de autoload em `bootstrap.php:26` + `bootstrap/autoload.php`; (3) testes de contrato das 4 GET (já existem na T-012) e das 3 POST com dublê. Depende só da T-026 | **5–7** (T-007, inalterado): rotas + controllers + middleware das duas autenticações + formato de erro idêntico (`{statusCode, message, stacktrace}`, inclusive o `statusCode` que hoje sai como o objeto Request, defeito herdado do 5.6) + testes de contrato + despacho |
| Risco | **Alto em suporte/segurança**: Silex abandonado (2018), Symfony 4.4 fora de suporte e com 8 alertas sem correção na 4.x, `zend-eventmanager` abandonado; dois `vendor/` a manter; o Composer bloqueia por padrão | Médio: depende do Laravel 13 inicializar; consumidores externos desconhecidos (T-007) |

## O que isto não prova

- As 3 rotas POST (gravam): nem 5.6 nem 8.5. Também não medidas na T-012.
- Parâmetros reais: as rotas foram chamadas com `1` (como a T-012); as 2 de erro exercitam o caminho de erro, as 2 de
  `cgm` o de sucesso com Fractal.
- O vendor da API foi medido **sozinho** num container; a convivência com o Laravel novo no mesmo processo não foi testada
  (e não é possível, ver critério 3).

## Anexo: `api.php` (instrumento; roda dentro do container 5.6, ao lado do `Cliente.php` da T-012)

```php
<?php
// T-033: as 4 GET da API V1 (rotas-api-v1.tsv da T-012, {param} -> 1) em cada alvo, com token do 5.6 e sessao legada
// de cada runtime; resumo igual ao da T-012 (status, tipo, md5 do corpo sem token/stacktrace/file/line).
// uso (dentro do container 5.6): php api.php <saida> nome=url [nome=url ...]
require __DIR__ . '/Cliente.php';
$saida = $argv[1]; @mkdir($saida, 0700, true);
$alvos = array();
foreach (array_slice($argv, 2) as $a) { list($n, $u) = explode('=', $a, 2); $alvos[$n] = $u; }
$rotas = array('/api/v1/configuracao/formulario/1/instituicao/1', '/api/v1/matriculaonline/emissaoProtocolo',
  '/api/v1/protocolo/cgm', '/api/v1/protocolo/cgm/1');
$cred = json_decode((string) shell_exec('php ' . escapeshellarg(__DIR__ . '/creds.php') . ' 2>/dev/null'), true);
$base56 = reset($alvos);
$r = SistemaCliente::requisita($base56, 'POST', '/v4/oauth/token', array('corpo' => http_build_query(array(
  'grant_type' => 'password', 'client_id' => $cred['id'], 'client_secret' => $cred['secret'], 'username' => 'dbseller', 'password' => 'dbseller'))));
$j = json_decode($r['corpo'], true); $token = isset($j['access_token']) ? $j['access_token'] : null;
echo 'token do 5.6: ' . ($token ? 'obtido' : 'FALHOU (' . $r['status'] . ')') . "\n";
$ck = array();
foreach ($alvos as $n => $u) { $ck[$n] = SistemaCliente::sessao($u); echo "sessao $n: " . ($ck[$n] ? 'ok' : 'FALHOU') . "\n"; }
foreach ($rotas as $i => $rota) {
  $lin = array();
  foreach ($alvos as $n => $u) {
    $x = SistemaCliente::requisita($u, 'GET', $rota, array('token' => $token, 'cookie' => $ck[$n]));
    file_put_contents("$saida/$i-$n.txt", $x['status'] . ' ' . $x['tipo'] . "\n" . $x['corpo']);
    $msg = ''; $jj = json_decode($x['corpo'], true);
    if (is_array($jj) && isset($jj['message'])) { $msg = ' msg=' . substr(preg_replace('/\s+/', ' ', $jj['message']), 0, 150); }
    elseif ($jj === null) { $msg = ' corpo=' . substr(preg_replace('/\s+/', ' ', strip_tags($x['corpo'])), 0, 150); }
    $lin[$n] = SistemaCliente::resumo($x) . $msg;
  }
  echo "\n$rota\n";
  foreach ($lin as $n => $l) { echo "  $n: $l\n"; }
}
```

`creds.php` é o `tests/sistema/credenciais.php` da T-012 com `chdir('/var/www/html')` (lê o cliente OAuth do config; a
saída nunca é impressa).
