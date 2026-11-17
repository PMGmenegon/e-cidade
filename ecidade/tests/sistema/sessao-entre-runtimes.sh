#!/bin/bash
# T-032: mede HOJE se a sessao aberta num runtime vale no outro (5.6 x 8.5 legado) e se o token OAuth do /v4 cruza.
# So mede e imprime; nao altera sistema, sessao, proxy nem banco alem do que o proprio login grava
# (db_logsacessa, db_usuariosonline, oauth_access_tokens/refresh_tokens): rode dentro do vigia-banco.sh.
# Uso: sessao-entre-runtimes.sh <agente>        (containers ecidade_<agente>_56/_85; portas pelo docker port)
# Sai 1 se a porta do container nao for achada, se o login nao devolver ECIDADEWINDOWMAIN ou se algum HTTP vier 000.
# Saida: uma linha por passo, TAB: cenario<TAB>passo<TAB>http<TAB>redireciona<TAB>logado<TAB>tamanho
# "logado" = o corpo NAO e a mensagem "Sessao invalida (12)" de libs/db_conecta.php. Sem segredos na saida.
A=${1:?agente}; C56=ecidade_${A}_56; C85=ecidade_${A}_85
P56=$(docker port $C56 80 2>/dev/null | head -1 | sed 's/.*://'); P85=$(docker port $C85 80 2>/dev/null | head -1 | sed 's/.*://')
[ -n "$P56" ] && [ -n "$P85" ] || { echo "falha: porta de $C56/$C85 nao encontrada (containers no ar?)" >&2; exit 1; }
U56=http://localhost:$P56; U85=http://localhost:$P85
FALHA=0; falha(){ echo "falha: $*" >&2; FALHA=1; }
TELAS="sau2_cgsduplos001.php cai3_gerfinanc001.php pro4_canarquiv001.php"   # saude, tributario/financeiro, patrimonial
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
base(){ [ "$1" = 56 ] && echo $U56 || echo $U85; }
SENHA=$(printf dbseller | md5sum | cut -d' ' -f1)

# login legado CONTORNANDO a tela: login.php (cookie) -> POST abrir.php direto. O navegador faz antes POST v4/oauth/token
# (templates/template_login_e-cidade.php:199) e so abre abrir.php?sAuth=... (GET) se o token vier 200; senao alerta e nao abre sessao.
# Aqui o abrir.php recebe os mesmos DB_login/DB_senha por POST (equivalente pelas globais). Imprime imprime o id da sessao (ECIDADEWINDOWMAIN)
login(){ local b; b=$(base $1); rm -f $T/jar
  curl -s -c $T/jar -b $T/jar -o /dev/null "$b/login.php"
  curl -s -c $T/jar -b $T/jar -o /dev/null -d "DB_login=dbseller&DB_senha=$SENHA&conteudoCaptcha=" "$b/abrir.php"
  awk '$6=="ECIDADEWINDOWMAIN"{print $7}' $T/jar | tail -1; }

# tela(cenario, runtime, cookie|"")
tela(){ local cen=$1 rt=$2 sid=$3 t b arg=(); b=$(base $rt); [ -n "$sid" ] && arg=(-b "ECIDADEWINDOWMAIN=$sid")
  for t in $TELAS; do
    code=$(curl -s "${arg[@]}" -o $T/corpo -w '%{http_code}|%{redirect_url}|%{size_download}' "$b/$t")
    IFS='|' read h loc tam <<< "$code"
    [ "$h" = 000 ] && falha "HTTP 000 em $t@$rt"
    if LC_ALL=C grep -aqE 'Sess.o inv.lida' $T/corpo; then lg=NAO; else lg=SIM; fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$cen" "$t@$rt" "$h" "${loc:--}" "$lg" "$tam"
  done; }

for par in "56 85" "85 56"; do set -- $par; de=$1; para=$2
  sid=$(login $de)
  [ -z "$sid" ] && { falha "login no $de sem cookie ECIDADEWINDOWMAIN"; continue; }
  tela "login $de, controle no $de" $de $sid
  tela "login $de, mesmo cookie no $para" $para $sid
  tela "sem cookie no $para" $para ""
done

# token OAuth do /v4: credenciais do config lidas dentro do container e nunca impressas
cred=$(docker exec -w /var/www/html $C56 php -r 'error_reporting(0);require "bootstrap.php";$c=ECidade\V3\Extension\Registry::get("app.config");echo $c->get("api.client.id")," ",$c->get("api.client.secret");' 2>/dev/null)
read cid csec <<< "$cred"
pega(){ curl -s -o $T/tk -w '%{http_code}' --data-urlencode grant_type=password --data-urlencode client_id=$cid --data-urlencode client_secret=$csec \
  --data-urlencode username=dbseller --data-urlencode password=dbseller "$(base $1)/v4/oauth/token"; }
usa(){ curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $2" -H 'Accept: application/json' "$(base $1)/v4/api/configuracao/banco-pix/listar"; }
for de in 56 85; do
  h=$(pega $de); [ "$h" = 000 ] && falha "HTTP 000 ao emitir token no $de"; tk=$(sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p' $T/tk)
  printf 'token\temitir no %s\t%s\t-\t%s\t-\n' $de "$h" "$([ -n "$tk" ] && echo emitiu || echo nao-emitiu)"
  if [ -n "$tk" ]; then for para in 56 85; do h=$(usa $para $tk); [ "$h" = 000 ] && falha "HTTP 000 ao usar token no $para"; printf 'token\ttoken do %s usado no %s\t%s\t-\t-\t-\n' $de $para "$h"; done; fi
done
exit $FALHA
