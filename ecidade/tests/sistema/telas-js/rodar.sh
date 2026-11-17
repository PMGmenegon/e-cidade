#!/bin/bash
# T-030: uma rodada da bateria JS de UM runtime, dentro do vigia do banco (telas rodam em container que grava; so db_logsacessa*,
# db_usuariosonline e oauth_* podem mudar). Uso: rodar.sh <agente> <porta-base> <56|85> <saida.json> [casos.tsv]
#   containers ecidade_<agente>_56 (porta-base) e ecidade_<agente>_85 (porta-base+1), subidos por sobe-ambiente.sh SEM SOMENTE_LEITURA.
# Saida: 0 ok / 3 o vigia acusou escrita fora do permitido (PARE e avise o Lider) / outro = falha da ferramenta.
# QUADRO: pasta do .quadro (vigia-banco.sh); padrao /home/gustavo/git/ecidade-laravel/.quadro
AGENTE=${1:?agente}; BASE=${2:?porta-base}; RT=${3:?56|85}; SAIDA=${4:?saida.json}; CASOS=${5:-}
QUADRO=${QUADRO:-/home/gustavo/git/ecidade-laravel/.quadro}
AQUI=$(cd "$(dirname "$0")" && pwd)
case "$RT" in 56) PORTA=$BASE;; 85) PORTA=$((BASE+1));; *) echo "runtime: 56 ou 85" >&2; exit 2;; esac
FOTO=$(mktemp); trap 'rm -f "$FOTO"' EXIT
bash "$QUADRO/ferramentas/vigia-banco.sh" antes "$FOTO" || exit 1
node "$AQUI/bateria.mjs" capturar --base "http://localhost:$PORTA" --container "ecidade_${AGENTE}_${RT}" --runtime "$RT" --saida "$SAIDA" ${CASOS:+--casos "$CASOS"}
RC=$?
bash "$QUADRO/ferramentas/vigia-banco.sh" depois "$FOTO"; VRC=$?
echo "vigia rc=$VRC bateria rc=$RC"
[ $VRC -ne 0 ] && exit $VRC
exit $RC
