#!/bin/bash
# Suite unica de testes (esqueleto, T-008): roda as camadas escolhidas nos runtimes 5.6 e 8.5.
#
# Uso (da raiz do repositorio):
#   node <quadro>/ferramentas/suite.mjs bash ecidade/tests/suite/rodar.sh [opcoes]
#
# Opcoes:
#   --camada LISTA   unitario,integracao,sistema ou "todas" (padrao: unitario,integracao)
#   --runtime R      56 | 85 | ambos (padrao: ambos)
#   --agente NOME    quem sobe os containers ecidade_<nome>_56/_85 (padrao: derivado do nome da worktree)
#   --saida PASTA    onde gravar os relatorios (padrao: ecidade/tests/suite/relatorios)
#   SISTEMA_URL_API=<url> (ambiente) aponta os testes da API V1 ao container proprio da API (padrao: o 8.5)
# Saida: 0 = tudo passou nos runtimes pedidos; 1 = algum teste falhou; 2 = uso/ambiente.
#
# PHPUnit vem de um phar por runtime (fora do vendor/), fixado por versao e sha256 em ferramentas.sha256.
# Camadas e lacunas: arquivos em camadas/*.lista. Nada aqui grava no banco.

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ECIDADE="$(cd "$AQUI/../.." && pwd)"
CACHE="${SUITE_CACHE:-$HOME/.cache/ecidade-suite}"
CAMADAS="unitario,integracao"; RUNTIMES="ambos"; SAIDA="$AQUI/relatorios"
AGENTE="$(basename "$(git -C "$ECIDADE" rev-parse --show-toplevel 2>/dev/null)" | sed 's/.*-//')"

while [ $# -gt 0 ]; do
  case "$1" in
    --camada)  CAMADAS="$2"; shift 2;;
    --runtime) RUNTIMES="$2"; shift 2;;
    --agente)  AGENTE="$2"; shift 2;;
    --saida)   SAIDA="$2"; shift 2;;
    -h|--help) sed -n '2,16p' "$0"; exit 0;;
    *) echo "opcao desconhecida: $1" >&2; exit 2;;
  esac
done

[ "$CAMADAS" = "todas" ] && CAMADAS="unitario,integracao,sistema"
IFS=',' read -r -a LISTA_CAMADAS <<< "$CAMADAS"
for c in "${LISTA_CAMADAS[@]}"; do
  [ -f "$AQUI/camadas/$c.lista" ] || { echo "camada invalida: $c (use unitario|integracao|sistema|todas)" >&2; exit 2; }
done
case "$RUNTIMES" in ambos) RUNTIMES="56 85";; 56|85) ;; *) echo "runtime invalido: $RUNTIMES" >&2; exit 2;; esac
mkdir -p "$SAIDA"

# phar do runtime: baixa se faltar e confere o sha256 fixado
phar_do_runtime() {
  local rt="$1" sha arq
  read -r sha arq < <(awk -v rt="$rt" '$1 !~ /^#/ && $3 == rt {print $1, $2}' "$AQUI/ferramentas.sha256")
  [ -n "$arq" ] || { echo "sem phar fixado para o runtime $rt" >&2; return 1; }
  mkdir -p "$CACHE"
  if [ ! -f "$CACHE/$arq" ]; then
    echo "baixando $arq" >&2
    curl -fsSL -o "$CACHE/$arq.tmp" "https://phar.phpunit.de/$arq" && mv "$CACHE/$arq.tmp" "$CACHE/$arq" \
      || { rm -f "$CACHE/$arq.tmp"; echo "falha ao baixar $arq" >&2; return 1; }
  fi
  echo "$sha  $CACHE/$arq" | sha256sum -c --status - || { echo "sha256 do $arq nao confere" >&2; return 1; }
  echo "$CACHE/$arq"
}

# entradas de uma camada para um runtime (uma por linha)
entradas() {
  awk -F'|' -v rt="$2" '
    /^[[:space:]]*(#|$)/ {next}
    { gsub(/^[[:space:]]+|[[:space:]]+$/, "", $1); rts = ($2 == "" ? "56,85" : $2)
      if (index("," rts ",", "," rt ",")) print $1 }' "$AQUI/camadas/$1.lista"
}

STATUS=0; NADA_RODOU=1
for RT in $RUNTIMES; do
  C="ecidade_${AGENTE}_${RT}"
  if [ "$(docker inspect -f '{{.State.Running}}' "$C" 2>/dev/null)" != "true" ]; then
    echo "container $C parado. Suba com: bash <quadro>/ferramentas/sobe-ambiente.sh <Agente> <worktree> <porta-base>" >&2
    exit 2
  fi
  PHAR="$(phar_do_runtime "$RT")" || exit 2
  docker exec "$C" sh -c 'rm -rf /tmp/suite && mkdir -p /tmp/suite/out'
  docker cp "$PHAR" "$C:/tmp/suite/phpunit.phar" >/dev/null
  docker cp "$AQUI/resumo.php" "$C:/tmp/suite/resumo.php" >/dev/null

  echo "=== runtime $RT ($C) ==="
  ARGS_RESUMO=()
  for CAM in "${LISTA_CAMADAS[@]}"; do
    N=0
    while IFS= read -r ENTRADA; do
      N=$((N+1)); NADA_RODOU=0
      XML="/tmp/suite/out/$CAM-$N.xml"
      echo "--- $CAM: $ENTRADA"
      docker exec -w /var/www/html ${SISTEMA_URL_API:+-e SISTEMA_URL_API="$SISTEMA_URL_API"} "$C" php /tmp/suite/phpunit.phar --no-configuration --colors=never \
        --bootstrap tests/suite/bootstrap.php --log-junit "$XML" "$ENTRADA" </dev/null
      ARGS_RESUMO+=("$CAM:$XML:$?")
    done < <(entradas "$CAM" "$RT")
    [ "$N" -eq 0 ] && { echo "--- $CAM: camada vazia neste runtime"; ARGS_RESUMO+=("$CAM::0"); }
  done

  # camada vazia sozinha nao e erro de execucao: so conta se nada rodou em nenhuma camada (abaixo)
  ARGS_OK=()
  for A in "${ARGS_RESUMO[@]}"; do [ "${A#*:}" = ":0" ] || ARGS_OK+=("$A"); done
  if [ "${#ARGS_OK[@]}" -eq 0 ]; then continue; fi

  docker exec -w /var/www/html "$C" php /tmp/suite/resumo.php "$RT" /tmp/suite/relatorio.txt "${ARGS_OK[@]}" </dev/null || STATUS=1
  docker cp "$C:/tmp/suite/relatorio.txt" "$SAIDA/relatorio-$RT.txt" >/dev/null
  rm -rf "$SAIDA/junit-$RT"; docker cp "$C:/tmp/suite/out" "$SAIDA/junit-$RT" >/dev/null
  {
    echo "gerado_em: $(date -Is)"
    echo "camadas: $CAMADAS"
    echo "lacunas:"
    awk '/^[[:space:]]*(#|$)/ {next} {print "  " $0}' "$AQUI/camadas/lacunas.lista"
  } >> "$SAIDA/relatorio-$RT.txt"
  echo "relatorio: $SAIDA/relatorio-$RT.txt"
done

if [ "$NADA_RODOU" -eq 1 ]; then echo "nenhum teste selecionado nas camadas '$CAMADAS'" >&2; exit 1; fi
[ "$STATUS" -eq 0 ] && echo "SUITE APROVADA" || echo "SUITE REPROVADA"
exit "$STATUS"
