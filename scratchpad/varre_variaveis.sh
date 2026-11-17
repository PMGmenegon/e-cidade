#!/bin/bash
# T-037: roda a varredura (scratchpad/varre_variaveis.php) na arvore atual e em origin/master, e compara com as branches de area.
# Uso: varre_variaveis.sh <container-php85> <pasta-saida>   (rodar na raiz do repositorio; o container monta a worktree em /var/www/html)
# Saida: <saida>/integracao.tsv, master.tsv, <branch>.tsv  (arquivo<TAB>linha<TAB>forma<TAB>trecho)
C=${1:?container}; O=${2:?saida}; mkdir -p "$O"
docker cp scratchpad/varre_variaveis.php $C:/tmp/varre_variaveis.php
scan(){ docker exec $C php -d memory_limit=1G /tmp/varre_variaveis.php "$1"; }
scan /var/www/html > "$O/integracao.tsv"
# candidatos no master (5.6 original): so os arquivos com forma suspeita, extraidos sem checkout
PAT='\$\$[A-Za-z_][A-Za-z0-9_]* ?[[{]|->\$[A-Za-z_][A-Za-z0-9_]* ?\[|::\$[A-Za-z_][A-Za-z0-9_]* ?\[|\$\{[^}]*\} ?\[|->\{[^}]*\} ?\['
git grep -alE "$PAT" origin/master -- 'ecidade/*.php' ':!ecidade/vendor' | sed 's#^origin/master:##' > "$O/candidatos.txt"
extrai(){ rm -rf "$O/_x"; mkdir -p "$O/_x"; while read f; do git cat-file -e "$1:$f" 2>/dev/null && { mkdir -p "$O/_x/$(dirname $f)"; git show "$1:$f" > "$O/_x/$f"; }; done < "$2"
  docker exec $C rm -rf /tmp/_x; docker cp "$O/_x/ecidade" $C:/tmp/_x; scan /tmp/_x; }
extrai origin/master "$O/candidatos.txt" > "$O/master.tsv"
cut -f1 "$O/master.tsv" "$O/integracao.tsv" | sort -u | sed 's#^#ecidade/#' > "$O/arquivos.txt"
for b in 1tributario-migrado 2educacao-migrado 3recursoshumanos-migrado 4patrimonial-migrado 5financeiro-migrado 6saude-migrado 7configuracao-migrado base-php84; do
  extrai origin/$b "$O/arquivos.txt" > "$O/$b.tsv"; done
rm -rf "$O/_x"
