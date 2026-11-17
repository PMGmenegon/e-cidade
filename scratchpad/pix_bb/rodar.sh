#!/bin/bash
# Roda o exercicio do SDK Pix do BB contra o duble, sem rede (--network none), em 3 combinacoes:
#   56  : PHP 5.6 + vendor de hoje (Guzzle 6.5.8)           -> referencia
#   g7  : PHP 8.5 + SDK de hoje + Guzzle 7.16.1 (Laravel 12) -> $G7 = pasta com vendor/ do composer (guzzlehttp/guzzle 7.16.1)
#   g8  : PHP 8.5 + SDK de hoje + Guzzle 8.5.0 + psr7 3.4.0 (trava do Laravel 13) -> $G8 = idem, 8.5.0
# SDKLIB=<pasta lib/> troca o SDK (ex.: copia com a unica troca de build_query).
# Uso: bash scratchpad/pix_bb/rodar.sh <56|g7|g8> <pasta-de-saida>   (da raiz do repositorio; G7 e G8 no ambiente)
set -u
C=${1:?56|g7|g8}; OUT=${2:?pasta}; mkdir -p "$OUT"; P=$PWD/scratchpad/pix_bb
CMD='DUBLE_LOG=/tmp/duble.jsonl php -S 127.0.0.1:8099 /pix/double.php >/tmp/server.log 2>&1 & sleep 1; php /pix/exercicio.php "$AUTOLOAD" "$SDK" 8099; echo "---PEDIDOS"; cat /tmp/duble.jsonl'
if [ "$C" = 56 ]; then
  docker run --rm --network none -e AUTOLOAD=/var/www/html/vendor/autoload.php -e SDK=- -v $P:/pix:ro -v $PWD/ecidade:/var/www/html:ro e-cidade-ecidade_php56 sh -c "$CMD" > "$OUT/$C.txt" 2>&1
else
  V=${C^^}; V=${!V:?defina G7 ou G8}; SDKDIR=${SDKLIB:-$PWD/ecidade/vendor/dbseller/sdk-api-pix-bb/lib}
  docker run --rm --network none -e AUTOLOAD=/g/vendor/autoload.php -e SDK=/sdk -v $P:/pix:ro -v $V:/g:ro -v $SDKDIR:/sdk:ro ecidade-login-php85 sh -c "$CMD" > "$OUT/$C.txt" 2>&1
fi
echo "$C: $(wc -l < "$OUT/$C.txt") linhas"
