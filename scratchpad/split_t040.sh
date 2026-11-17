#!/bin/bash
# T-040: mede split() no 8.5 (polyfill dbseller/legacy = explode) contra o 5.6, sem alterar o sistema.
# Rodar da raiz do repositorio com dois containers (PHP 5.6 e 8.5) que montem ecidade/ em /var/www/html
# (nada aqui usa o banco):  bash scratchpad/split_t040.sh <container_56> <container_85>
# Saidas em ecidade/tmp/t040/ (gitignored): split56.tsv/split85.tsv (chamadas), compara56/85.txt
# (padroes que divergem), iguais56/85.txt (padroes iguais), so_grep.tsv + so_grep_tipo.txt (conferencia do grep).
set -e
C56=${1:?container 5.6}; C85=${2:?container 8.5}; T=ecidade/tmp/t040; W=/var/www/html
mkdir -p $T
cp scratchpad/split_varredura.php scratchpad/split_compara.php scratchpad/split_iguais.php scratchpad/split_conferegrep.php $T/
git ls-files -- 'ecidade/*.php' | sed 's#^ecidade/##' > $T/lista.txt
for v in 56 85; do
  c=$C56; [ $v = 85 ] && c=$C85
  docker exec -w $W $c php -d memory_limit=1G tmp/t040/split_varredura.php $W tmp/t040/lista.txt </dev/null > $T/split$v.tsv
done
cmp $T/split56.tsv $T/split85.tsv && echo "varredura: tokenizacao igual no 5.6 e no 8.5"
awk -F'\t' 'NR>1{n[$7]++} END{for(k in n) print "  " k, n[k]}' $T/split85.tsv
awk -F'\t' 'NR>1 && $7=="igual"{print $6}' $T/split85.tsv | sort -u > $T/iguais.txt
for v in 56 85; do
  c=$C56; [ $v = 85 ] && c=$C85
  docker exec $c php $W/tmp/t040/split_compara.php $W/vendor/autoload.php </dev/null > $T/compara$v.txt 2>&1
  docker exec $c php $W/tmp/t040/split_iguais.php $W/vendor/autoload.php $W/tmp/t040/iguais.txt </dev/null > $T/iguais$v.txt 2>&1
done
diff -q $T/iguais56.txt $T/iguais85.txt && echo "padroes 'igual': $(wc -l < $T/iguais.txt) valores, saida identica nos dois"
diff $T/compara56.txt $T/compara85.txt | grep -c '^>' | sed 's/^/padroes "diverge": linhas diferentes = /' || true
# o que o grep de partida acha e o tokenizador nao (excluindo JS: ".split(")
git grep -n -a -E '(^|[^_a-zA-Z>:$.])split *\(' -- 'ecidade/*.php' | sed 's#^ecidade/##' | awk -F: '{print $1"\t"$2}' | sort -u > $T/grep_linhas.tsv
awk -F'\t' 'NR>1{print $1"\t"$2}' $T/split85.tsv | sort -u > $T/tok_linhas.tsv
LC_ALL=C comm -23 <(LC_ALL=C sort $T/grep_linhas.tsv) <(LC_ALL=C sort $T/tok_linhas.tsv) > $T/so_grep.tsv
docker exec -w $W $C85 php tmp/t040/split_conferegrep.php tmp/t040/so_grep.tsv </dev/null > $T/so_grep_tipo.txt
echo "so no grep: $(wc -l < $T/so_grep.tsv) linhas"; sort $T/so_grep_tipo.txt | uniq -c
