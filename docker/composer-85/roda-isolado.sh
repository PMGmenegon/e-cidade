#!/usr/bin/env bash
# Roda um trecho PHP isolado no 7.4 ou no 8.5, sem rede e sem banco, e FALHA ALTO.
# Uso (qualquer pasta):  bash docker/composer-85/roda-isolado.sh <7.4|8.5> <trecho.php> [args do trecho]
# Variaveis: IMAGEM (imagem a usar), VENDOR (vendor montado em /app/vendor), DOCKER (comando docker; padrao docker)
# - imagem = a do runtime, construida do Dockerfile do repositorio (docker/php74-apache -> ecidade-php74-apache;
#   docker/php85-apache -> ecidade-php85-apache): mesmas extensoes e php.ini do runtime. Se faltar, e construida (1x, precisa de rede)
# - ecidade/ em /app somente leitura; vendor: 7.4 = ecidade/vendor (ou VENDOR); 8.5 = runtime-85/vendor (ou VENDOR)
# - gravavel so em memoria (tmpfs): /app/bootstrap/cache, /app/storage/logs, /app/storage/framework, /tmp
# - variaveis de ambiente de teste so no conteiner (--env-file gerado de ecidade/.env.example, host de banco inexistente,
#   APP_KEY de teste): nenhum ecidade/.env e criado na arvore; um ecidade/.env que ja exista nao e alterado
# - --network none; o trecho fica em /trecho (somente leitura)
# - sai com erro se: argumento invalido, imagem ausente e sem build, docker run falhar, trecho sair com rc != 0 ou a saida vier vazia
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
if [ "$V" = 7.4 ]; then PADRAO=ecidade-php74-apache; DF=php74-apache; else PADRAO=ecidade-php85-apache; DF=php85-apache; fi
IMG="${IMAGEM:-$PADRAO}"
if ! "$DOCKER" image inspect "$IMG" >/dev/null 2>&1; then
  [ -z "${IMAGEM:-}" ] || falha "imagem $IMG ausente" 65
  echo "roda-isolado: construindo $IMG de docker/$DF (uma vez; precisa de rede)" >&2
  "$DOCKER" build -q -t "$IMG" "$R/docker/$DF" >/dev/null || falha "build de $IMG falhou" 65
fi
[ -f "$R/ecidade/.env.example" ] || falha "falta ecidade/.env.example" 64
for d in ecidade/vendor ecidade/bootstrap/cache ecidade/storage/logs ecidade/storage/framework; do
  mkdir -p "$R/$d" || falha "nao criou $d"
done
if [ -n "${VENDOR:-}" ]; then VEN="$VENDOR"; elif [ "$V" = 8.5 ]; then mkdir -p "$R/runtime-85/vendor" && VEN="$R/runtime-85/vendor"; else VEN="$R/ecidade/vendor"; fi
[ -e "$VEN/autoload.php" ] || echo "roda-isolado: aviso: $VEN sem autoload.php (instale o vendor; so roda trecho que nao usa o autoload)" >&2
MONTA=(-v "$R/ecidade:/app:ro")
[ "$VEN" = "$R/ecidade/vendor" ] || MONTA+=(-v "$VEN:/app/vendor:ro")
TD="$(cd "$(dirname "$T")" && pwd)"; TN="$(basename "$T")"
OUT="$(mktemp)"; ERR="$(mktemp)"; ENVF="$(mktemp)"; trap 'rm -f "$OUT" "$ERR" "$ENVF"' EXIT
{ grep -E '^[A-Z_]+=' "$R/ecidade/.env.example" | grep -vE '^(APP_KEY|DB_HOST|APP_ENV)='
  echo APP_ENV=local; echo APP_KEY=base64:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=; echo DB_HOST=banco.invalido; } > "$ENVF"
"$DOCKER" run --rm --network none -u "$(id -u):$(id -g)" --env-file "$ENVF" "${MONTA[@]}" -v "$TD:/trecho:ro" \
  --tmpfs /tmp --tmpfs /app/bootstrap/cache:mode=1777 --tmpfs /app/storage/logs:mode=1777 --tmpfs /app/storage/framework:mode=1777 \
  -w /app "$IMG" php "/trecho/$TN" "$@" >"$OUT" 2>"$ERR"
RC=$?
cat "$OUT"; cat "$ERR" >&2
[ "$RC" -eq 0 ] || falha "docker run/trecho saiu com rc=$RC (php $V, $TN)" "$RC"
[ -s "$OUT" ] || falha "saida vazia (php $V, $TN): nao compare vazio com vazio" 66
