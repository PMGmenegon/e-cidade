# Ambiente `e74` (base PHP 7.4)

`docker-compose.e74.yml` (projeto `-p e74`) sobe a referência PHP 7.4/Laravel 8 (`ecidade74_php74`, :8074), o PHP 8.5
(`ecidade74_php85`, :8185, Dockerfile em `php85/` + `php85/paridade-74.ini`), o proxy (`ecidade74_proxy`, :8190,
`proxy/nginx-e74.conf` + `proxy/map-e74.conf`) e o banco (`ecidade74_database`, sem porta publicada), com rede e
volumes próprios. Instalação passo a passo: `regressao/README.md`, seção 1.

# Laboratório "Laravel 12" (:8187)

`docker-compose.lar12.yml` (projeto próprio `e74-lar12`) sobe o container `ecidade74_lar12` em
**http://localhost:8187**, o alvo padrão da bateria Laravel (`REGRESSAO_LARAVEL_NOVO_URL`; container em
`REGRESSAO_CONTAINER_LARAVEL_NOVO`, ambos em `regressao/nucleo/ambiente.py`).

**Ainda não existe Laravel 12 do e-Cidade.** A base desta branch é PHP 7.4 / Laravel 8.73 / Passport 10.4. O
laboratório roda o **mesmo runtime do `ecidade74_php85`** (a imagem `ecidade74-php85:latest`, reusada sem rebuild,
com os mesmos volumes `e74_sessions`/`e74_tmp` e o mesmo `php85/paridade-74.ini`) sobre o código apontado por
`LAR12_CODIGO`. O padrão é o `./ecidade` atual, ou seja: **hoje ele mede o Laravel 8 da base 7.4 sob PHP 8.5**, não
um Laravel 12. O resultado está em `regressao/baseline/lab-lar12-resultado.md`.

```bash
# da raiz do repositório; requer o ambiente e74 no ar (rede, volumes, banco) e a imagem ecidade74-php85:latest
docker compose -p e74-lar12 -f regressao/lab/docker-compose.lar12.yml up -d
docker compose -p e74-lar12 -f regressao/lab/docker-compose.lar12.yml stop

# quando houver o Laravel 12 migrado (caminho absoluto, ou relativo a regressao/lab/)
LAR12_CODIGO=/home/kauab/ecidade-laravel12 docker compose -p e74-lar12 -f regressao/lab/docker-compose.lar12.yml up -d --force-recreate

# rodada: o console artisan usa o ecidade74_lar12 sozinho (o alvo e REGRESSAO_LARAVEL_NOVO_URL)
regressao/.venv/bin/python -m regressao.laravel.bateria comparar --saida ~/rodadas/X --alvo http://localhost:8187
```

`LAR12_IMAGEM` troca a imagem (padrão `ecidade74-php85:latest`). O container usa o banco `ecidade74_database` e a
rede `e74_ecidade74` (externos: `down` deste projeto não os remove). O código Laravel 12 precisa trazer o próprio
`vendor/` e o `.env` (o container não roda `composer install`). Logs: `docker exec ecidade74_lar12 tail
/var/log/php_errors.log`; o Laravel escreve em `storage/logs/laravel.log` do código montado (com o padrão, o mesmo
arquivo da referência). O `ecidade_lar12` (:8087) da pilha antiga não é usado nem tocado.
