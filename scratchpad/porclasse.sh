# uso: docker cp scratchpad/porclasse.sh <container>:/tmp/pc.sh; docker exec -i <container> sh /tmp/pc.sh /tmp/<harness>.php < lista
# A bateria (regressao/php/classes.py) copia este script e escrita.php para ecidade/tmp/ (= /var/www/html/tmp nos dois
# runtimes) e o roda no container da referencia (PHP 7.4) e no do alvo (PHP 8.5); os nomes vem de
# regressao/nucleo/ambiente.py (REGRESSAO_CONTAINER_REF / REGRESSAO_CONTAINER_PHP_NOVO).
# uma classe por processo (um fatal nao mata o resto da lista); marca quem nao produziu saida
h=$1; n=0; v=0
while read c; do n=$((n+1)); echo "$c" > /tmp/_um.txt
  o=$(cd /var/www/html && php -d display_errors=0 "$h" /tmp/_um.txt 2>/dev/null </dev/null)
  if [ -n "$o" ]; then v=$((v+1)); echo "$o"; else echo "SEM_SAIDA $c"; fi
done
echo "#TOTAL $n COM_SAIDA $v" >&2
