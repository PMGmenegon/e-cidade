#!/usr/bin/env bash
# Teste do roda-isolado.sh num clone limpo (sem ecidade/.env, ecidade/vendor nem runtime-85).
# Uso: bash docker/composer-85/testa-roda-isolado.sh
# O caso do kernel do Laravel precisa dos vendors: TESTA_VENDOR74 (composer install do ecidade/composer.lock, padrao
# runtime-85/referencia-74/vendor) e TESTA_VENDOR85 (padrao runtime-85/vendor) do repositorio que roda o teste.
set -uo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
V74="${TESTA_VENDOR74:-$R/runtime-85/referencia-74/vendor}"; V85="${TESTA_VENDOR85:-$R/runtime-85/vendor}"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
git clone -q --local "$R" "$W/clone" || { echo "FALHOU: clone"; exit 1; }
cp "$R/docker/composer-85/roda-isolado.sh" "$W/clone/docker/composer-85/"   # versao em teste (pode ainda nao estar no commit)
S="$W/clone/docker/composer-85/roda-isolado.sh"
mkdir "$W/t"; echo '<?php echo PHP_MAJOR_VERSION, ".", PHP_MINOR_VERSION, PHP_EOL;' > "$W/t/ok.php"
echo '<?php exit(3);' > "$W/t/erro.php"; echo '<?php // nada' > "$W/t/vazio.php"
cat > "$W/t/kernel.php" <<'PHP'
<?php
// sobe o kernel do Laravel do PR: precisa de bootstrap/cache e storage gravaveis e das variaveis de ambiente de teste
require '/app/vendor/autoload.php';
$app = require '/app/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
echo get_class($app), ' env=', $app->environment(), ' php=', PHP_MAJOR_VERSION, '.', PHP_MINOR_VERSION, PHP_EOL;
PHP
n=0; f=0
ok()   { n=$((n+1)); if "$@" >"$W/o" 2>"$W/e"; then echo "ok   $*"; else f=$((f+1)); echo "FALHOU (esperava rc=0): $*"; cat "$W/e"; fi; }
quebra() { n=$((n+1)); if "$@" >"$W/o" 2>"$W/e"; then f=$((f+1)); echo "FALHOU (esperava rc!=0): $*"; else echo "ok   rc=$? $*"; grep -q "roda-isolado: ERRO" "$W/e" || { f=$((f+1)); echo "FALHOU: sem mensagem"; }; fi; }
ok bash "$S" 7.4 "$W/t/ok.php"; grep -q '^7\.4' "$W/o" || { f=$((f+1)); echo "FALHOU: saida 7.4: $(cat "$W/o")"; }
ok bash "$S" 8.5 "$W/t/ok.php"; grep -q '^8\.5' "$W/o" || { f=$((f+1)); echo "FALHOU: saida 8.5: $(cat "$W/o")"; }
[ ! -e "$W/clone/ecidade/.env" ] && [ "$(stat -c %U "$W/clone/ecidade/vendor")" = "$(id -un)" ] && echo "ok   sem ecidade/.env na arvore; ecidade/vendor do usuario" || { f=$((f+1)); echo "FALHOU: .env criado ou vendor de root"; }
for v in 7.4 8.5; do
  ven="$V74"; [ "$v" = 8.5 ] && ven="$V85"
  ok env VENDOR="$ven" bash "$S" "$v" "$W/t/kernel.php"
  grep -q "^App.Application env=local php=$v" "$W/o" || { f=$((f+1)); echo "FALHOU: kernel $v: $(head -c 300 "$W/o")"; }
  grep -q "Deprecated" "$W/o" && { f=$((f+1)); echo "FALHOU: Deprecated no stdout ($v)"; }
done
quebra bash "$S" 7.4 "$W/t/erro.php"
quebra bash "$S" 8.5 "$W/t/vazio.php"
quebra env IMAGEM=nao-existe-xyz bash "$S" 7.4 "$W/t/ok.php"
printf '#!/usr/bin/env bash\n[ "$1" = image ] && exit 0\necho "docker: Error response: mountpoint read-only" >&2; exit 125\n' > "$W/dockerquebrado"; chmod +x "$W/dockerquebrado"
quebra env DOCKER="$W/dockerquebrado" bash "$S" 8.5 "$W/t/ok.php"
quebra bash "$S" 5.6 "$W/t/ok.php"
quebra bash "$S" 7.4 "$W/t/nao-existe.php"
echo "$((n-f))/$n"; [ "$f" -eq 0 ]
