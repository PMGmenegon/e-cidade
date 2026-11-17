#!/bin/bash
# Uma rodada do roteiro do login da API V1 num runtime, com o vigia do banco em volta.
# Uso: bash captura.sh <agente> <56|85> <pasta-saida>      (containers ecidade_<agente>_56/_85 no ar, SEM SOMENTE_LEITURA)
# BASE=<url> manda os pedidos a outro endereco (ex.: o proxy com a regra /api/v1/); padrao: o proprio container.
# So casos que NAO gravam. O vigia usa a lista padrao (db_logsacessa, db_usuariosonline, oauth_*); api_clients e db_acount*
# NAO sao permitidos: qualquer alteracao => exit 3: interrompa e investigue. 'db172_ultima_utilizacao' e lida so para provar que nao mudou.
set -u
AG=${1:?agente}; RT=${2:?56|85}; DEST=${3:?pasta}
C=ecidade_${AG}_${RT}; V=/home/gustavo/git/ecidade-laravel/.quadro/ferramentas/vigia-banco.sh
FOTO=$(mktemp); trap 'rm -f $FOTO' EXIT
ult(){ docker exec ecidade_database psql -U postgres -d ecidade -tAc "select db172_ultima_utilizacao from configuracoes.api_clients order by db172_sequencial limit 1"; }
mkdir -p "$DEST"
bash $V antes $FOTO >/dev/null
U0=$(ult)
docker exec -w /var/www/html $C rm -rf /tmp/login-api-v1-out
docker exec -w /var/www/html $C php tests/sistema/login-api-v1/roteiro.php ${BASE:-http://localhost} /tmp/login-api-v1-out | tee "$DEST/.roteiro.log"
rm -rf "$DEST/casos"; docker cp $C:/tmp/login-api-v1-out "$DEST/casos"
U1=$(ult)
bash $V depois $FOTO | tee "$DEST/vigia.txt"; RC=${PIPESTATUS[0]}
{ echo "runtime: $RT"; echo "db172_ultima_utilizacao antes : $U0"; echo "db172_ultima_utilizacao depois: $U1"; echo "vigia rc=$RC"; } | tee "$DEST/banco.txt"
exit $RC
