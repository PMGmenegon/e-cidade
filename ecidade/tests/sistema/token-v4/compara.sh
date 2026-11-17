#!/bin/bash
# Compara duas rodadas (pastas criadas por captura.sh) caso a caso. Uso: bash compara.sh <rodadaA> <rodadaB>
diff -r "${1:?rodadaA}/casos" "${2:?rodadaB}/casos" && echo "IGUAIS: $(ls "$1/casos"/*.out | wc -l) casos"
