#!/usr/bin/env bash
# Roda um trecho PHP isolado no 7.4 ou no 8.5, sem rede e sem banco, e FALHA ALTO.
# Uso (qualquer pasta):  bash docker/composer-85/roda-isolado.sh <7.4|8.5> <trecho.php> [args do trecho]
# - cria ecidade/.env (de ecidade/.env.test, sem segredo) e ecidade/vendor como o usuario, se nao existirem
#   (sem eles o Docker cria o ponto de montagem como root:root, e o docker run quebra com "mountpoint ... read-only")
# - 7.4: ecidade/ em /app (somente leitura), com o vendor/ do PR; 8.5: o mesmo, com runtime-85/vendor em /app/vendor
# - --network none; o trecho fica em /trecho (somente leitura); /tmp e tmpfs
# - sai com erro se: argumento invalido, imagem ausente, docker run falhar, trecho sair com rc != 0 ou a saida vier vazia
#   (saida vazia contra saida vazia vira "igual" falso numa comparacao 7.4 x 8.5)
# - stdout e stderr do trecho passam para o chamador; rc do trecho e preservado. Codigos: 64 uso, 65 imagem, 66 saida vazia
# Registro: docs/registro/estrutura-85.md
set -uo pipefail
falha() { echo "roda-isolado: ERRO: $1" >&2; exit "${2:-1}"; }
[ $# -ge 2 ] || falha "uso: roda-isolado.sh <7.4|8.5> <trecho.php> [args]" 64
V="$1"; T="$2"; shift 2
case "$V" in 7.4|8.5) ;; *) falha "versao '$V' invalida (use 7.4 ou 8.5)" 64 ;; esac
[ -f "$T" ] || falha "trecho '$T' nao existe" 64
R="$(cd "$(dirname "$0")/../.." && pwd)"
DOCKER="${DOCKER:-docker}"
IMG="php:$V-cli"
"$DOCKER" image inspect "$IMG" >/dev/null 2>&1 || falha "imagem $IMG ausente (docker pull $IMG)" 65
[ -f "$R/ecidade/.env" ] || { [ -f "$R/ecidade/.env.test" ] || falha "falta ecidade/.env.test" 64; cp "$R/ecidade/.env.test" "$R/ecidade/.env" || falha "nao criou ecidade/.env"; }
mkdir -p "$R/ecidade/vendor" || falha "nao criou ecidade/vendor"
MONTA=(-v "$R/ecidade:/app:ro")
if [ "$V" = 8.5 ]; then
  mkdir -p "$R/runtime-85/vendor" || falha "nao criou runtime-85/vendor"
  [ -e "$R/runtime-85/vendor/autoload.php" ] || echo "roda-isolado: aviso: runtime-85/vendor sem autoload.php (rode composer-85.sh install)" >&2
  MONTA+=(-v "$R/runtime-85/vendor:/app/vendor:ro")
fi
TD="$(cd "$(dirname "$T")" && pwd)"; TN="$(basename "$T")"
OUT="$(mktemp)"; ERR="$(mktemp)"; trap 'rm -f "$OUT" "$ERR"' EXIT
"$DOCKER" run --rm --network none -u "$(id -u):$(id -g)" "${MONTA[@]}" -v "$TD:/trecho:ro" --tmpfs /tmp \
  -w /app "$IMG" php "/trecho/$TN" "$@" >"$OUT" 2>"$ERR"
RC=$?
cat "$OUT"; cat "$ERR" >&2
[ "$RC" -eq 0 ] || falha "docker run/trecho saiu com rc=$RC (php $V, $TN)" "$RC"
[ -s "$OUT" ] || falha "saida vazia (php $V, $TN): nao compare vazio com vazio" 66
