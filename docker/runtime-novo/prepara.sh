#!/bin/bash
# Prepara a pasta do runtime novo (docker-compose.runtime-novo.yml): vendor/, bootstrap-cache/ e storage/ proprios.
# Uso: bash docker/runtime-novo/prepara.sh <pasta ecidade/> <pasta destino>      (ex.: ecidade runtime-novo)
#
# - vendor/: COPIA de verdade do vendor atual (nao hardlink). O composer do runtime novo reescreve arquivos no
#   lugar (ex.: vendor/composer/autoload_*.php); com hardlink isso alteraria o vendor do 5.6.
# - storage/: a arvore de <ecidade>/storage SEM as chaves OAuth (*.key, montadas somente leitura pelo compose) e
#   sem o que o Laravel gera (cache, views, sessoes, logs). Os modelos .xlsx de storage/financeiro vao junto.
# - bootstrap-cache/: vazio (o Laravel gera services.php/packages.php no formato da versao dele).
# - Marcadores .runtime-novo em cada pasta: provam de que lado o arquivo esta (ver docs/registro/runtime-novo.md).
# Nao sobrescreve: se o destino ja existe, para.
set -e
E=${1:?pasta ecidade}; D=${2:?pasta destino}
[ -e "$D" ] && { echo "ja existe: $D (apague antes de preparar de novo)"; exit 1; }
[ -d "$E/vendor" ] || { echo "sem $E/vendor"; exit 1; }
mkdir -p "$D/bootstrap-cache"
cp -a "$E/vendor" "$D/vendor"
tar -C "$E" --exclude='*.key' --exclude='framework/cache/data' --exclude='framework/views/*.php' \
    --exclude='framework/sessions/*' --exclude='logs/*.log' -cf - storage | tar -C "$D" -xf -
touch "$D/storage/oauth-private.key" "$D/storage/oauth-public.key"   # pontos de montagem vazios (o conteudo vem do compose)
for p in vendor storage bootstrap-cache; do echo "runtime novo: $p proprio" > "$D/$p/.runtime-novo"; done
chmod -R a+rwX "$D/storage" "$D/bootstrap-cache"
echo "pronto: $D (vendor $(du -sh "$D/vendor" | cut -f1))"
