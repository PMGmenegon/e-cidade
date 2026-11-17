# Dependências só da API V1 (Silex), nas versões de hoje

> 13/11/2026 (rótulo: T-046). A API V1 (`ecidade/api/V1`, Silex) fica com as versões de hoje — Silex 2.2.4 e
> Symfony 3.4 — num `vendor/` só dela. Motivo: o Laravel novo usa outro Symfony, e as duas versões não convivem no mesmo
> processo (mesmos namespaces `Symfony\Component\*`); a API passa a ter um container próprio, e este é o `vendor/` dele.
> O `ecidade/composer.json` e o `ecidade/composer.lock` (vendor do 5.6) não mudam.

## Arquivos

| Arquivo | Papel |
|---|---|
| `docker/api-v1/composer.json` | lista da API: os 7 pacotes que a API carrega de fato, com a versão exata de hoje; mesmo bloco `autoload` do `ecidade/composer.json` |
| `docker/api-v1/composer.lock` | trava da API: 23 pacotes, **todos** na versão e na referência do `ecidade/composer.lock` de hoje |
| `runtime-api/vendor/` | onde o comando abaixo instala (fora do versionamento, `.gitignore`) |

## Quais pacotes

Medido em 13/11/2026 no PHP 8.5, com o vendor de hoje: os arquivos de `vendor/` incluídos pelos pedidos às rotas GET de
`/api/v1/` (função de encerramento registrando `get_included_files()`, só no container de medição). Com classe carregada:
Silex, Pimple, Symfony (`http-foundation`, `http-kernel`, `routing`, `event-dispatcher`, `finder`), `league/fractal`,
`zendframework/zend-eventmanager` (núcleo V3), `dbseller/session`, `dbseller/legacy` e `cakephp/utility`. Nenhum
`laravel/*`. Os outros pacotes aparecem só pelos arquivos `files` do autoload geral e não são usados pela API.

A lista pede só os 7 diretos; os demais entram como dependência deles:

| Pacote | Versão (= `ecidade/composer.lock`) | Na lista da API |
|---|---|---|
| `silex/silex` | v2.2.4 | direto |
| `league/fractal` | 0.11.0 | direto |
| `zendframework/zend-eventmanager` | 2.2.10 | direto |
| `symfony/finder` | v3.4.47 | direto |
| `cakephp/utility` | 3.10.5 | direto |
| `dbseller/legacy` | v1.1.1 | direto |
| `dbseller/session` | dev-master `f3020b4630fd29051afab65c75ffa1eec6e1f1a0` | direto (fixado na referência de hoje) |
| `cakephp/core` | 3.10.5 | dependência |
| `paragonie/random_compat` | v2.0.21 | dependência |
| `pimple/pimple` | v3.2.3 | dependência |
| `psr/container` | 1.0.0 | dependência |
| `psr/log` | 1.1.4 | dependência |
| `symfony/debug` | v3.4.47 | dependência |
| `symfony/event-dispatcher` | v3.4.47 | dependência |
| `symfony/http-foundation` | v3.4.47 | dependência |
| `symfony/http-kernel` | v3.4.49 | dependência |
| `symfony/routing` | v3.4.47 | dependência |
| `symfony/polyfill-ctype` | v1.19.0 | dependência |
| `symfony/polyfill-mbstring` | v1.19.0 | dependência |
| `symfony/polyfill-php56` | v1.19.0 | dependência |
| `symfony/polyfill-php70` | v1.19.0 | dependência |
| `symfony/polyfill-util` | v1.19.0 | dependência |
| `zendframework/zend-stdlib` | 2.2.10 | dependência |

`dbseller/session` vem do repositório Git público `https://github.com/DBSeller/Session.git` (o `ecidade/composer.json`
usa o endereço SSH do mesmo repositório); nenhuma credencial é necessária. Abandonados pelo autor: `silex/silex`,
`symfony/debug`, `zendframework/zend-eventmanager`, `zendframework/zend-stdlib` (como hoje).

## Como a trava foi gerada

Partindo de uma **cópia** do `ecidade/composer.lock` ao lado do `composer.json` da API, uma atualização parcial de um
pacote só remove da trava o que a lista da API não pede e mantém todo o resto travado:

```bash
cp ecidade/composer.lock <pasta>/composer.lock            # junto do docker/api-v1/composer.json
composer update dbseller/session --no-install --ignore-platform-req=php    # no PHP 8.5; 117 remocoes, 0 instalacoes, 0 atualizacoes
```

Resultado: 23 pacotes; comparados com o `ecidade/composer.lock` por nome, versão e referência do código-fonte: 0
diferenças. O `sha256` do `ecidade/composer.json` (`f3cd4ba6…`) e do `ecidade/composer.lock` (`d5246a26…`) é o mesmo
antes e depois.

## PHP < 8: `--ignore-platform-req=php` só no comando da API

`cakephp/core` 3.10.5 e `cakephp/utility` 3.10.5 declaram `php >=5.6.0,<8.0.0`. Sem a opção, no PHP 8.5:

```
Your lock file does not contain a compatible set of packages. Please run composer update.
  - cakephp/core 3.10.5 requires php >=5.6.0,<8.0.0 -> your php version (8.5.12) does not satisfy that requirement.
  - cakephp/utility 3.10.5 requires php >=5.6.0,<8.0.0 -> your php version (8.5.12) does not satisfy that requirement.
```

A opção `--ignore-platform-req=php` vai **só** no comando de instalação da API e vale para todos os pacotes dela. Conferido
nos 23: só esses dois dependem dela. Os outros declaram limites abertos (`>=5.3`, `>=5.5.9`, `^5.5.9|>=7.0.8`) que o 8.5
satisfaz. Não se usa `config.platform` (mentiria a versão do PHP para todo o resolvedor). A API só carrega o
`cakephp/utility` pelo `bootstrap.php` do próprio pacote; a medição no 8.5 com essas versões deu as mesmas respostas do 5.6.

## Como instalar

Num container 8.5 (a imagem `ecidade-login-php85`, a mesma do runtime 8.5), com o Composer 2.10.3, a partir da raiz do
repositório:

```bash
API_DIR=runtime-api; mkdir -p $API_DIR/vendor
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp \
  -v ~/.local/bin/composer:/usr/local/bin/composer:ro \
  -v $PWD/docker/api-v1/composer.json:/proj/composer.json:ro \
  -v $PWD/docker/api-v1/composer.lock:/proj/composer.lock:ro \
  -v $PWD/$API_DIR/vendor:/proj/vendor \
  -v $PWD/ecidade/app:/proj/app:ro -v $PWD/ecidade/database:/proj/database:ro -v $PWD/ecidade/fpdf:/proj/fpdf:ro \
  -w /proj --entrypoint php ecidade-login-php85 /usr/local/bin/composer install --no-interaction --no-scripts --ignore-platform-req=php
```

As pastas `app/`, `database/` e `fpdf/` entram só leitura para o autoload do projeto (o mesmo bloco do
`ecidade/composer.json`); os caminhos gerados são relativos e valem em `/var/www/html` dentro do container da API.
Medido: 23 pacotes instalados, 8,7 MB (o vendor do 5.6 tem 247 MB), idênticos ao vendor da medição.

## O que isto não prova

- As respostas da API com este vendor no container próprio e pelo proxy: é o passo seguinte (container da API).
- As 3 rotas POST da API (gravam no banco).
