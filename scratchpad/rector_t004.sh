#!/bin/bash
# T-004: dry-run do Rector (config do projeto) sobre o recorte fora das areas ja portadas.
# Rodar da raiz do repositorio, com um container PHP 8.5 que monte ecidade/ em /var/www/html:
#   bash scratchpad/rector_t004.sh <container_85> <saida.json>
# Rector 2.6.7 com PHPStan 2.2.17 fixado em ecidade/tmp/rector22 (com o 2.3.5 que o composer
# escolhe sozinho, 121 arquivos derrubam o PHPStan; ver docs/registro/rector-varredura-t004.md).
# NAO altera arquivo nenhum do sistema (--dry-run); escreve so em ecidade/tmp/ (gitignored) e na saida.
set -e
C=${1:?container 8.5}; OUT=${2:?saida.json}; R=tmp/rector22
python3 scratchpad/rector_recorte.py ecidade/tmp/t004_alvos.txt
cp scratchpad/rector-curado.php scratchpad/rector-t004-timeout.php ecidade/$R/
mkdir -p ecidade/$R/rector-rules && cp scratchpad/rector-rules/*.php ecidade/$R/rector-rules/
docker exec -i "$C" php -l /var/www/html/$R/rector-t004-timeout.php </dev/null
python3 scratchpad/rector_t004_lotes.py "$C" ecidade/tmp/t004_alvos.txt "$OUT" 500 $R
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('totais', d.get('totals'))" "$OUT"
