#!/bin/bash
# Cria uma sessao autenticada (login do e-Cidade pelo 5.6) e grava o arquivo de sessao no host.
# Uso: sessao.sh <porta-5.6> <container-5.6> <arquivo-saida> [ano]
# Roda em container NORMAL (nao SOMENTE_LEITURA): o login grava so o que o sistema grava (log de acesso, token, sessao).
# Depois da sessao pronta, os containers podem ser recriados com SOMENTE_LEITURA=1 e a sessao reenviada pela captura.
# A sessao do login nao traz instituicao/modulo/exercicio (o navegador os escolhe nas telas seguintes): sao acrescentados aqui
# na propria sessao, sem escrever no banco. Usuario de teste: dbseller/dbseller. O segredo do cliente e lido da pagina de login
# em tempo de execucao e nunca e impresso nem gravado.
set -e
PORTA=${1:?porta}; C=${2:?container}; SAIDA=${3:?arquivo}; ANO=${4:-2018}
B=http://localhost:$PORTA; J=$(mktemp); trap 'rm -f $J' EXIT
PG=$(curl -s -L -c $J -b $J $B/)
CID=$(echo "$PG" | grep -a "formData.append('client_id'" | sed -E "s/.*'client_id', '([^']*)'.*/\1/")
CSE=$(echo "$PG" | grep -a "formData.append('client_secret'" | sed -E "s/.*'client_secret', '([^']*)'.*/\1/")
curl -s -c $J -b $J -d exec=destroyCookieDatabase $B/login.rpc.php >/dev/null
curl -s -c $J -b $J -F username=dbseller -F password=dbseller -F client_id="$CID" -F client_secret="$CSE" -F grant_type=password $B/v4/oauth/token | grep -aq access_token || { echo "token falhou" >&2; exit 1; }
MD=$(printf dbseller | md5sum | cut -d' ' -f1)
AUTH=$(printf "DB_login=dbseller&DB_senha=$MD" | base64 -w0 | tr '+/' '-_' | tr -d '=')
curl -s -c $J -b $J -o /dev/null "$B/abrir.php?sAuth=$AUTH"
SID=$(awk '$6=="ECIDADEWINDOWMAIN"{print $7}' $J)
[ -n "$SID" ] || { echo "sem sessao" >&2; exit 1; }
T=$(date +%s)
EXTRA="DB_instit|s:1:\"1\";DB_modulo|s:4:\"9318\";DB_nome_modulo|s:6:\"Social\";DB_anousu|i:$ANO;DB_datausu|i:$T;DB_uol_hora|i:$T;DB_coddepto|s:1:\"1\";DB_nomedepto|s:8:\"CADASTRO\";DB_itemmenu_acessado|s:1:\"0\";DB_use_pcasp|b:0;DB_Area|s:1:\"9\";"
docker exec -u www-data "$C" sh -c "cat /var/lib/php/sessions/sess_$SID" > "$SAIDA"
sed -i 's/DB_acessado|N;/DB_acessado|s:1:"0";/' "$SAIDA"
printf '%s' "$EXTRA" >> "$SAIDA"
echo "$SID" > "$SAIDA.sid"
echo "sessao em $SAIDA (sid em $SAIDA.sid)"
