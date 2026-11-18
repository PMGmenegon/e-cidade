#!/bin/bash
# Uma rodada do roteiro do token /v4 num runtime, com o vigia do banco em volta.
# Uso: bash captura.sh <agente> <56|85> <pasta-saida> [<arquivo-com-token-anterior>]   (containers ecidade_<agente>_56/_85 no ar, SEM SOMENTE_LEITURA)
# Se TOKEN_NOVO=<arquivo> estiver definido, o token valido emitido nesta rodada e copiado para la (modo 0600) para a rodada seguinte.
# O vigia usa a lista padrao (db_logsacessa, db_usuariosonline, oauth_*): qualquer outra tabela alterada => exit 3 (interrompa e investigue).
set -u
AG=${1:?agente}; RT=${2:?56|85}; DEST=${3:?pasta}; ANT=${4:-}
C=ecidade_${AG}_${RT}; V=${VIGIA:?defina VIGIA com o caminho do vigia-banco.sh}
FOTO=$(mktemp); trap 'rm -f $FOTO' EXIT
mkdir -p "$DEST"
docker exec $C rm -rf /tmp/token-v4-out /tmp/token-v4-ant /tmp/token-v4-ant.novo
ARGANT=""
if [ -n "$ANT" ] && [ -f "$ANT" ]; then
  docker cp "$ANT" $C:/tmp/token-v4-ant >/dev/null; docker exec -u root $C sh -c 'chown www-data:www-data /tmp/token-v4-ant; chmod 600 /tmp/token-v4-ant'
  ARGANT=/tmp/token-v4-ant
elif [ -n "${TOKEN_NOVO:-}" ]; then ARGANT=/tmp/token-v4-ant; fi
bash $V antes $FOTO >/dev/null
docker exec -u www-data -w /var/www/html $C php tests/sistema/token-v4/roteiro.php http://localhost /tmp/token-v4-out $ARGANT | tee "$DEST/.roteiro.log"
rm -rf "$DEST/casos"; docker cp $C:/tmp/token-v4-out "$DEST/casos"
if [ -n "${TOKEN_NOVO:-}" ]; then
  docker cp $C:/tmp/token-v4-ant.novo "$TOKEN_NOVO" 2>/dev/null && chmod 600 "$TOKEN_NOVO"
fi
docker exec $C rm -f /tmp/token-v4-ant /tmp/token-v4-ant.novo
bash $V depois $FOTO | tee "$DEST/vigia.txt"; RC=${PIPESTATUS[0]}
echo "runtime: $RT  vigia rc=$RC" | tee "$DEST/banco.txt"
exit $RC
