# Ambiente `e74` (base PHP 7.4)

`docker-compose.e74.yml` (projeto `-p e74`) sobe a referência PHP 7.4/Laravel 8 (`ecidade74_php74`, :8074), o PHP 8.5
(`ecidade74_php85`, :8185, Dockerfile em `php85/` + `php85/paridade-74.ini`), o proxy (`ecidade74_proxy`, :8190,
`proxy/nginx-e74.conf` + `proxy/map-e74.conf`) e o banco (`ecidade74_database`, sem porta publicada), com rede e
volumes próprios. Instalação passo a passo: `regressao/README.md`, seção 1.

O laboratório abaixo ainda descreve a pilha antiga (`ecidade_*`, :8087); ele passa para o `e74` (:8187) na
adaptação da bateria Laravel.

# Laboratório "Laravel 12" (:8087)

`docker-compose.lar12.yml` sobe o container `ecidade_lar12` em **http://localhost:8087**, o alvo padrão da bateria
Laravel (`REGRESSAO_LARAVEL_NOVO_URL`).

**Ainda não existe Laravel 12 do e-Cidade.** Todas as branches do upstream (inclusive `laravel-upgrade` e as
`*-migrado`) usam `laravel/framework 5.4.*`. Então o laboratório roda o **mesmo runtime do `ecidade_php85`** (a
imagem `e-cidade-ecidade_php85`, reusada sem rebuild, com os mesmos volumes e o mesmo `paridade-56.ini`) sobre o
código apontado por `LAR12_CODIGO`. O padrão é o `./ecidade` atual, ou seja: **hoje ele mede o Laravel 5.4 sob
PHP 8.5**, não um Laravel 12. O resultado está em `regressao/baseline/lab-lar12-resultado.md`.

```bash
# da raiz do repositório; requer a pilha de referência no ar e a imagem do php85 já construída
docker compose -f regressao/lab/docker-compose.lar12.yml up -d
docker compose -f regressao/lab/docker-compose.lar12.yml down

# quando houver o Laravel 12 migrado (caminho absoluto, ou relativo a regressao/lab/)
LAR12_CODIGO=/home/kauab/ecidade-laravel12 docker compose -f regressao/lab/docker-compose.lar12.yml up -d --force-recreate

# rodada (o console artisan precisa do container do alvo)
REGRESSAO_LARAVEL_CONSOLE_CONTAINER=ecidade_lar12 \
  regressao/.venv/bin/python -m regressao.laravel.bateria comparar --saida ~/rodadas/X --alvo http://localhost:8087
```

`LAR12_IMAGEM` troca a imagem (padrão `e-cidade-ecidade_php85`). O container usa o banco `ecidade_database`,
a rede `e-cidade_ecidade` e os volumes `ecidade_sessions`/`ecidade_tmp`, como o `ecidade_php85`. O código Laravel 12
precisa trazer o próprio `vendor/` e o `.env` (o container não roda `composer install`). Logs:
`docker exec ecidade_lar12 cat /var/log/php_errors.log` e `docker logs ecidade_lar12`.
