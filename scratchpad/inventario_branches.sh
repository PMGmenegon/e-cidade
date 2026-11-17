#!/usr/bin/env bash
# T-017: inventario somente leitura de todas as branches (locais e origin/*)
# contra laravel/integracao e origin/base-php84.
# Uso: bash scratchpad/inventario_branches.sh [--fetch]
# Saida (TSV): ref  atras_int  frente_int  atras_base  frente_base  data  no_github  ultimo_commit
#   atras_X  = commits que X tem e a branch NAO tem
#   frente_X = commits que a branch tem e X NAO tem
# Exclui equipe/*, testes/rodada, origin/HEAD e o ref simbolico "origin".
# A coluna no_github cruza cada origin/* com `git ls-remote --heads origin`: 'nao' = o ref local e tracking velho
# (a branch foi apagada no GitHub; um fetch sem --prune nao remove o ref local). Refs locais: '-'.
set -u
[ "${1:-}" = "--fetch" ] && git fetch origin
INT=laravel/integracao
BASE=origin/base-php84
REMOTAS=$(git ls-remote --heads origin | sed 's#.*refs/heads/##')
printf 'ref\tatras_int\tfrente_int\tatras_base\tfrente_base\tdata\tno_github\tultimo_commit\n'
git for-each-ref --format='%(refname:short)|%(committerdate:short)|%(subject)' refs/heads refs/remotes \
  | grep -v -e '^equipe/' -e 'testes/rodada' -e '^origin|' -e '^origin/HEAD|' \
  | while IFS='|' read -r ref data assunto; do
      read -r ai fi < <(git rev-list --left-right --count "$INT...$ref")
      read -r ab fb < <(git rev-list --left-right --count "$BASE...$ref")
      gh=-
      case "$ref" in origin/*) if echo "$REMOTAS" | grep -qxF "${ref#origin/}"; then gh=sim; else gh=nao; fi;; esac
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$ref" "$ai" "$fi" "$ab" "$fb" "$data" "$gh" "${assunto:0:70}"
    done
