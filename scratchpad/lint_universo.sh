#!/bin/bash
# php -l em todo *.php de ecidade/ (exceto vendor/) nos runtimes 5.6 e 8.5 de um agente.
# Uso: lint_universo.sh <agente> <saida-dir>   (containers ecidade_<agente>_56 / _85, ver sobe-ambiente.sh)
# Nao aborta no 1o erro: cada arquivo roda em processo proprio (xargs -n1) e o status e ignorado.
A=${1:?agente}; O=${2:?saida}; mkdir -p "$O"
for v in 56 85; do
  C=ecidade_${A}_$v
  docker exec $C sh -c 'cd /var/www/html && find . -name vendor -prune -o -type f -name "*.php" -print0 | sort -z' > "$O/lista_$v.bin" </dev/null
  tr '\0' '\n' < "$O/lista_$v.bin" | wc -l > "$O/total_$v.txt"
  docker exec $C sh -c 'cd /var/www/html && find . -name vendor -prune -o -type f -name "*.php" -print0 | xargs -0 -n1 -P8 sh -c '"'"'r=$(php -l "$1" 2>&1); case "$r" in "No syntax errors"*) ;; *) echo "$1 :: $(echo "$r" | head -1)";; esac'"'"' _' </dev/null | sort > "$O/falhas_$v.txt"
  echo "$v: total=$(cat $O/total_$v.txt) falhas=$(wc -l < $O/falhas_$v.txt)"
done
