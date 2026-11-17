#!/bin/bash
# T-030: lista, a partir do CODIGO, os arquivos que chamam a API /v4/ (por JavaScript ou PHP). Mesmo comando do registro
# docs/registro/laravel.md (ponto 4), com ordem fixa (LC_ALL=C) para dividir em metades. Uso: lista.sh [raiz-do-repo]
cd "${1:-$(git rev-parse --show-toplevel)}" || exit 2
grep -rlaE "['\"/]v4/" --include=*.php --include=*.js ecidade --exclude-dir=vendor --exclude-dir=app --exclude-dir=tmp --exclude-dir=routes \
  | LC_ALL=C sort | sed 's#^ecidade/##'
