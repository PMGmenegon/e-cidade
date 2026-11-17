# Laboratório :8087: Laravel 5.4 sob PHP 8.5 (17/11/2026)

Primeira rodada real da bateria Laravel contra um alvo que não é a referência. **Não é Laravel 12**: não existe
código do e-Cidade em Laravel 12 (todas as branches do upstream usam `laravel/framework 5.4.*`). O laboratório
(`regressao/lab/docker-compose.lar12.yml`) roda o runtime do `ecidade_php85` sobre o `./ecidade` atual. A baseline
Laravel gravada no 5.4 não foi alterada.

## Comandos

```bash
docker compose -f regressao/lab/docker-compose.lar12.yml up -d        # container ecidade_lar12, PHP 8.5.12
REGRESSAO_LARAVEL_CONSOLE_CONTAINER=ecidade_lar12 \
  regressao/.venv/bin/python -m regressao.laravel.bateria comparar \
  --saida ~/rodadas/lar12-sobre-php85 --alvo http://localhost:8087    # saída 2, 0,9 s
```

Rodada arquivada em `~/rodadas/lar12-sobre-php85/` (commit `6248e399d`, dump `af43b090…`).

## Resultado

| IDENTICO | DIVERGE | INCONCLUSIVO | ERRO_AMBIENTE |
|---|---|---|---|
| 0 | 0 | 0 | **1** (`laravel:boot`: HTTP 500 em `/v4/oauth/token`) |

A bateria para no portão de boot, como foi desenhada: o banco não foi restaurado e nenhum dos 389 casos rodou.

O que responde em :8087:

- `/` → 302 para `login.php`, e `login.php` → 200 (12 009 bytes, igual ao :8085). O PHP legado funciona.
- `/v4/oauth/token` e `/v4/api/financeiro/contabilidade/sistemas` (a rota de controle) → **HTTP 500 com corpo
  vazio**. Na referência (:8080), sem token, elas dão 405 (JSON `{"error":true,…}` do `RouteCollection`) e
  500 com JSON `{"error":true,"message":"Unauthenticated."…}`.
- Varredura sem autenticação das 108 rotas GET da baseline: **as 106 `/v4` dão 500 com corpo vazio**. As 2 Silex
  `/api/v1` respondem com o mesmo status e a mesma mensagem do 5.4 (500 "Sem permissão para acessar a API." e
  403 "Sessão inválida ou expirada."); só o `stacktrace` muda (nome de closure no PHP 8).
- `php artisan --version` no container: saída 255, nada no stdout.

**O Laravel 5.4 não sobe sob PHP 8.5.**

## Causa exata (de `/var/log/php_errors.log` do `ecidade_lar12`)

1. No boot, `HandleExceptions` do Laravel 5.4 chama `error_reporting(-1)` e transforma **qualquer** aviso, inclusive
   `E_DEPRECATED`, em `ErrorException`. O PHP 8.4+ emite deprecations ao carregar classes do próprio framework. A
   primeira, no console (verificada com um script de boot pelo stdin, sem gravar nada):
   `Illuminate\Http\Request::duplicate(): Implicitly marking parameter $query as nullable is deprecated`
   (`vendor/laravel/framework/src/Illuminate/Http/Request.php:369`, ao carregar `Request` em `SetRequestForConsole`).
2. Para renderizar essa exceção, o Laravel resolve o `App\Exceptions\Handler` pelo container, e
   `Container::resolveDependencies` usa `ReflectionParameter::getClass()`, depreciado desde o PHP 8.0
   (`Illuminate/Container/Container.php:788`). Isso vira outra `ErrorException` dentro do handler, que acaba em
   **`PHP Fatal error: Uncaught ErrorException: Method ReflectionParameter::getClass() is deprecated`**.
3. O shutdown handler do e-Cidade (`src/V3/Error/Handler/Shutdown.php`) tenta disparar `app.error` e carrega
   `Zend\Stdlib\PriorityQueue`, cujo `count()` não declara `: int`. Terceiro fatal:
   `Return type of Zend\Stdlib\PriorityQueue::count() should either be compatible with Countable::count(): int`.
   O Apache devolve 500 com corpo vazio.

O resto do log são deprecations do PHP 8.4/8.5 em `vendor/` (guzzle/promises, psysh, zend-diactoros, helpers do
Laravel) e em código próprio (`ECidade\V3\Extension\ParameterBag::getIterator()/count()` sem tipo de retorno e
`E_STRICT` em `config/application*.php`). Elas só não derrubam o legado porque lá ninguém as converte em exceção.

## O que falta para um Laravel 12 de verdade

- **Código**: subir a escada do framework (5.4 → … → 12) num branch próprio, com PHP ≥ 8.2, `composer.json` novo
  e um `vendor/` compatível. Isso inclui trocar ou atualizar os pacotes que travam no PHP 8 (zendframework → laminas,
  guzzle 6 → 7, Passport compatível e as demais dependências abandonadas), corrigir as assinaturas próprias
  (`ParameterBag`, `E_STRICT`) e revisar a ponte `FrontController`/`src/V3` → Laravel. Nada disso existe hoje.
- **Laboratório**: já está pronto. É só apontar `LAR12_CODIGO` para esse código (com `vendor/` e `.env`) e recriar o
  container (`regressao/lab/README.md`).
- **Bateria**: rodar `comparar` como acima. Só quando o boot passar a rodada restaura o banco e avalia os 389 casos.
  Então os `DIVERGE` serão os achados reais do 5.4 → 12. O console (`list`, `env`, `migrate:status`) vai divergir
  por natureza (lista de comandos e versão do framework) e pede triagem.
