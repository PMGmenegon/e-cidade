#!/bin/bash
# T-068: telas que carregam o .env pelo Dotenv, no 5.6 (gabarito) e no runtime novo (ou outros runtimes), com a
# mesma sessao (login feito no 5.6) restaurada antes de cada pedido.
# Para cada pedido: HTTP, tamanho, md5 do corpo, quantas linhas e md5 das linhas que o pedido acrescentou ao extension/log/error.log
# (o arquivo e o mesmo nos tres: mesmo codigo montado), com o caminho do container trocado por <raiz> e sem a hora.
# O md5 e do corpo normalizado: a porta de cada runtime (localhost:NNNN) e o sid aleatorio do captcha do login.
#   bash scratchpad/t068_telas.sh <pasta> <sid> <sess.bak> <lista> c56:porta crn:porta [...]
# <lista>: um caminho por linha (sem a barra inicial). Rodar com o vigia do banco em volta.
set -u
OUT=${1:?pasta}; SID=${2:?sid}; SESS=${3:?sess.bak}; LISTA=${4:?lista}; shift 4
LOG=ecidade/extension/log/error.log
mkdir -p "$OUT"; : > "$OUT/resumo.tsv"
while read -r tela; do
  [ -z "$tela" ] && continue
  nome=$(echo "$tela" | tr '/?&=' '____')
  for alvo in "$@"; do
    c=${alvo%%:*}; p=${alvo##*:}; r=${c##*_}
    docker cp "$SESS" "$c:/var/lib/php/sessions/sess_$SID" </dev/null
    docker exec "$c" sh -c "chown www-data /var/lib/php/sessions/sess_$SID 2>/dev/null; chmod 600 /var/lib/php/sessions/sess_$SID" </dev/null
    antes=$(stat -c %s $LOG)
    res=$(curl -s -m 120 -b "PHPSESSID=$SID; ECIDADEWINDOWMAIN=$SID" -o "$OUT/$nome.$r.html" -w '%{http_code}\t%{size_download}' "http://localhost:$p/$tela" </dev/null)
    sleep 1
    tail -c +$((antes + 1)) $LOG | sed -E 's#/var/www/html/#<raiz>/#g; s/^\[[0-9: -]+\] //' > "$OUT/$nome.$r.log"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$tela" "$r" "$res" "$(sed -E 's/localhost:[0-9]+/localhost:PORTA/g; s/sid=[0-9a-f]{32}/sid=X/g' "$OUT/$nome.$r.html" | md5sum | cut -c1-12)" "$(grep -c . "$OUT/$nome.$r.log")" "$(md5sum < "$OUT/$nome.$r.log" | cut -c1-12)" >> "$OUT/resumo.tsv"
  done
done < "$LISTA"
column -t -s $'\t' "$OUT/resumo.tsv"
