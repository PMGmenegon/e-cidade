#!/bin/bash
# uso: resolve.sh <dir>  -> roda o resolvedor (sem instalar) no container do PHP 8.5; sucesso = existir composer.lock
# --network host: a rede bridge desta maquina nao resolve DNS (medido em 12/11/2026)
# pre-requisito: copia do commit travado do Session ao lado deste script:
#   cp -r ecidade/vendor/dbseller/session <pasta do script>/session-src
d=$(cd "$1" && pwd); s=$(cd "$(dirname "$0")/session-src" && pwd)
timeout 600 docker run --rm --init --network host -u "$(id -u):$(id -g)" -v "$d":/w -v "$s":/sess:ro -v "$HOME/.cache/composer":/cc \
  -e COMPOSER_HOME=/tmp/ch -e COMPOSER_CACHE_DIR=/cc -w /w ecidade-login-php85 \
  composer update --no-install --no-scripts --no-plugins --no-interaction --no-progress -v >"$d/saida.txt" 2>&1
[ -f "$d/composer.lock" ] && echo "RESOLVEU $1" || echo "NAO RESOLVEU $1"
