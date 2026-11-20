#!/usr/bin/env bash
# Teste do roda-isolado.sh num clone limpo (sem ecidade/.env, ecidade/vendor nem runtime-85). Uso: bash docker/composer-85/testa-roda-isolado.sh
set -uo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
git clone -q --local "$R" "$W/clone" || { echo "FALHOU: clone"; exit 1; }
git -C "$R" diff HEAD --quiet -- docker/composer-85 2>/dev/null || cp "$R"/docker/composer-85/roda-isolado.sh "$W/clone/docker/composer-85/"
S="$W/clone/docker/composer-85/roda-isolado.sh"
mkdir "$W/t"; echo '<?php echo PHP_MAJOR_VERSION, ".", PHP_MINOR_VERSION, PHP_EOL;' > "$W/t/ok.php"
echo '<?php exit(3);' > "$W/t/erro.php"; echo '<?php // nada' > "$W/t/vazio.php"
n=0; f=0
ok()   { n=$((n+1)); if "$@" >"$W/o" 2>"$W/e"; then echo "ok   $*"; else f=$((f+1)); echo "FALHOU (esperava rc=0): $*"; cat "$W/e"; fi; }
quebra() { n=$((n+1)); if "$@" >"$W/o" 2>"$W/e"; then f=$((f+1)); echo "FALHOU (esperava rc!=0): $*"; else echo "ok   rc=$? $*"; grep -q "roda-isolado: ERRO" "$W/e" || { f=$((f+1)); echo "FALHOU: sem mensagem"; }; fi; }
ok bash "$S" 7.4 "$W/t/ok.php"; grep -q '^7\.4' "$W/o" || { f=$((f+1)); echo "FALHOU: saida 7.4: $(cat "$W/o")"; }
ok bash "$S" 8.5 "$W/t/ok.php"; grep -q '^8\.5' "$W/o" || { f=$((f+1)); echo "FALHOU: saida 8.5: $(cat "$W/o")"; }
[ -f "$W/clone/ecidade/.env" ] && [ "$(stat -c %U "$W/clone/ecidade/vendor")" = "$(id -un)" ] && echo "ok   .env e vendor criados como $(id -un)" || { f=$((f+1)); echo "FALHOU: .env/vendor"; }
quebra bash "$S" 7.4 "$W/t/erro.php"
quebra bash "$S" 8.5 "$W/t/vazio.php"
quebra env DOCKER=/nao/existe bash "$S" 7.4 "$W/t/ok.php"
printf '#!/usr/bin/env bash\n[ "$1" = image ] && exit 0\necho "docker: Error response: mountpoint read-only" >&2; exit 125\n' > "$W/dockerquebrado"; chmod +x "$W/dockerquebrado"
quebra env DOCKER="$W/dockerquebrado" bash "$S" 8.5 "$W/t/ok.php"
quebra bash "$S" 5.6 "$W/t/ok.php"
quebra bash "$S" 7.4 "$W/t/nao-existe.php"
echo "$((n-f))/$n"; [ "$f" -eq 0 ]
