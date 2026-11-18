#!/bin/bash
# T-012: roda as GET da camada sistema contra containers SOMENTE_LEITURA=1 (PGOPTIONS default_transaction_read_only=on:
# toda conexao desses containers recusa escrita, ate CREATE TEMP TABLE; o banco nao e alterado) e compara com a rodada normal.
# Rota cuja resposta no 5.6 muda entre as duas rodadas tentou gravar -> vai para dados/get-fora-da-cobertura.tsv.
# Uso (da raiz da worktree): bash ecidade/tests/sistema/trava-leitura.sh <Agente> <porta-base> <pasta-saida>
set -e
A=$(echo ${1:?agente} | tr 'A-Z' 'a-z'); P=${2:?porta-base}; OUT=${3:?saida}; W="$(cd "$(dirname "$0")/../../.." && pwd)"
Q=${QUADRO:?defina QUADRO com a pasta que contem ferramentas/vigia-banco.sh}/ferramentas; N=$(command -v node)
S="$N $Q/suite.mjs bash ecidade/tests/suite/rodar.sh --camada sistema --runtime 85 --agente $A"
mkdir -p "$OUT/normal" "$OUT/ro"
bash $Q/sobe-ambiente.sh $A "$W" $P >/dev/null
echo "$A" > "$W/ecidade/tests/sistema/.agente"
docker exec -w /var/www/html ecidade_${A}_85 php tests/sistema/prepara.php
# segredos (token/sessoes) saem do container so para sobreviver a recriacao e sao apagados no fim
mkdir -p "$OUT/seg"; chmod 700 "$OUT" "$OUT/seg"; docker cp ecidade_${A}_85:/tmp/ecidade-sistema-segredos/. "$OUT/seg/"
# sessoes legadas vivem no filesystem do container: levar as duas para os containers travados
for RT in 56 85; do
  SID=$(docker exec ecidade_${A}_85 sed 's/.*=//' /tmp/ecidade-sistema-segredos/sessao-$RT); mkdir -p "$OUT/sess$RT"
  docker cp ecidade_${A}_$RT:/var/lib/php/sessions/sess_$SID "$OUT/sess$RT/" >/dev/null 2>&1 || docker cp ecidade_${A}_$RT:/tmp/sess_$SID "$OUT/sess$RT/"
done
(cd "$W" && $S >/dev/null 2>&1 || true); cp "$W"/ecidade/tests/suite/relatorios/sistema-rotas-*.tsv "$OUT/normal/"
SOMENTE_LEITURA=1 bash $Q/sobe-ambiente.sh $A "$W" $P >/dev/null
docker exec ecidade_${A}_85 mkdir -p -m 700 /tmp/ecidade-sistema-segredos; docker cp "$OUT/seg/." ecidade_${A}_85:/tmp/ecidade-sistema-segredos/
for RT in 56 85; do
  SID=$(docker exec ecidade_${A}_85 sed 's/.*=//' /tmp/ecidade-sistema-segredos/sessao-$RT)
  docker cp "$OUT/sess$RT/sess_$SID" ecidade_${A}_$RT:/var/lib/php/sessions/sess_$SID
  docker exec ecidade_${A}_$RT chmod 600 /var/lib/php/sessions/sess_$SID; docker exec ecidade_${A}_$RT chown www-data /var/lib/php/sessions/sess_$SID
done
(cd "$W" && $S >/dev/null 2>&1 || true); cp "$W"/ecidade/tests/suite/relatorios/sistema-rotas-*.tsv "$OUT/ro/"
bash $Q/sobe-ambiente.sh $A "$W" $P parar >/dev/null
rm -rf "$OUT/seg" "$OUT"/sess56 "$OUT"/sess85   # token e sessoes nao ficam em disco
for f in rotas-v4 rotas-rest-v1 rotas-api-v1; do
  echo "== $f (5.6, normal x somente leitura): linhas que mudaram"
  diff <(cut -f1,2 "$OUT/normal/sistema-$f.tsv") <(cut -f1,2 "$OUT/ro/sistema-$f.tsv") || true
done
