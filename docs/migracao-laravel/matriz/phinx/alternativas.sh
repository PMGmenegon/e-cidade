#!/bin/bash
# Monta e mede as alternativas do Phinx com o conjunto do Laravel 13 (A0, A1, A2, B, C, C2), em copia descartavel.
# uso (na raiz da worktree):  bash docs/migracao-laravel/matriz/phinx/alternativas.sh <pasta de trabalho, ex.: /tmp/phinx>
# precisa de: docker com a imagem ecidade-login-php85 (PHP 8.5 + Composer), ecidade/vendor/dbseller/{session,phinx_postgres} (worktree preparada),
# e rede para o Composer (--network host). Os comandos Phinx rodam com --network none, sem variavel de banco. Nada do repositorio e alterado.
set -e
R=$PWD; T=$(mkdir -p "${1:?pasta de trabalho}" && cd "$1" && pwd); O=$R/ecidade; Q=$R/docs/migracao-laravel/matriz; P=$Q/phinx
IMG=ecidade-login-php85
cp "$Q"/gera.py "$T"/ && rm -rf "$T/session-src" && cp -r "$O/vendor/dbseller/session" "$T/session-src"   # commit f3020b4 do Session (o repo do composer.json e SSH)
# adaptador: fork = original com "robmorgan/phinx": "^0.16" (A1); fork2 = fork + o diff do A2
rm -rf "$T/fork" "$T/fork2" && mkdir "$T/fork" && cp -r "$O"/vendor/dbseller/phinx_postgres/{classes,composer.json,README.md} "$T/fork/"
python3 - "$T" <<'PY'
import json, sys
p = sys.argv[1] + '/fork/composer.json'; c = json.load(open(p)); c['require'] = {"php": ">=8.4", "robmorgan/phinx": "^0.16"}; json.dump(c, open(p, 'w'), indent=2)
PY
cp -r "$T/fork" "$T/fork2" && (cd "$T/fork2" && patch -p1 < "$P/adaptador-a2.patch" >/dev/null)
# composer.json de cada alternativa: Laravel 13 + Passport 13, sem os pacotes que travam por outro motivo
B="-dbseller/sdk-api-pix-bb -silex/silex -proner/phppimaco laravel/passport=^13.0"
"$T/gera.py" "$O/composer.json" "$T/altB"  13 8.5 $B -dbseller/phinx_postgres robmorgan/phinx=^0.16       # B: adaptador padrao
"$T/gera.py" "$O/composer.json" "$T/altA0" 13 8.5 $B                                                     # A0: adaptador como esta
for n in altA1:fork altA2:fork2; do "$T/gera.py" "$O/composer.json" "$T/${n%%:*}" 13 8.5 $B -dbseller/phinx_postgres
  python3 - "$T/${n%%:*}" "/${n##*:}" <<'PY'
import json, sys
p = sys.argv[1] + '/composer.json'; c = json.load(open(p))
c['repositories'].append({"type": "path", "url": sys.argv[2], "options": {"versions": {"dbseller/phinx_postgres": "1.4.0"}}})
c['require']['dbseller/phinx_postgres'] = '^1.4'; json.dump(c, open(p, 'w'), indent=4)
PY
done
mkdir -p "$T/altC" "$T/altC2"   # C: Phinx isolado com o adaptador original; C2 = C sem o bloqueio de alertas de seguranca
echo '{"name":"ecidade/phinx-isolado","require":{"php":">=8.4","dbseller/phinx_postgres":"^1.3"},"config":{"sort-packages":true,"platform":{"php":"8.5.12"}}}' > "$T/altC/composer.json"
echo '{"name":"ecidade/phinx-isolado","require":{"php":">=8.4","dbseller/phinx_postgres":"^1.3"},"config":{"sort-packages":true,"platform":{"php":"8.5.12"},"policy":{"advisories":{"block":false}}}}' > "$T/altC2/composer.json"

compor() {   # compor <alternativa> <update|install>
  timeout 900 docker run --rm --init --network host -u "$(id -u):$(id -g)" -v "$T/$1":/w -v "$T/session-src":/sess:ro -v "$T/fork":/fork:ro -v "$T/fork2":/fork2:ro \
    -v "$HOME/.cache/composer":/cc -e COMPOSER_HOME=/tmp/ch -e COMPOSER_CACHE_DIR=/cc -w /w $IMG \
    composer $2 $( [ "$2" = update ] && echo --no-install ) --no-scripts --no-plugins --no-interaction --no-progress -v > "$T/$1/saida-$2.txt" 2>&1 || true
}
php_sem_rede() {   # php_sem_rede <alternativa> <args php...>: sem rede e sem variavel de conexao
  local a=$1; shift
  docker run --rm --network none -v "$T/$a":/w:ro -v "$T/fork":/fork:ro -v "$T/fork2":/fork2:ro -v "$P/teste-adaptador.php":/t.php:ro -w /w $IMG php -d error_reporting=-1 -d display_errors=1 "$@" 2>&1
}
for a in altB altA0 altA1 altA2 altC altC2; do compor $a update; [ -f "$T/$a/composer.lock" ] && echo "$a: RESOLVEU" || echo "$a: NAO RESOLVEU"; done
for a in altB altA1 altA2 altC2; do compor $a install
  for c in --help list; do php_sem_rede $a vendor/bin/phinx $c > "$T/$a/out-${c#--}.txt" || true
    echo "$a phinx $c: $(wc -l < "$T/$a/out-${c#--}.txt") linhas, avisos Deprecated/Fatal/Warning: $(grep -ciE 'deprecated|fatal|warning:' "$T/$a/out-${c#--}.txt")"; done
done
echo "--- A1: o adaptador original no Phinx 0.16 nao carrega:"; for c in PostgresMigration Table; do php_sem_rede altA1 -r "require 'vendor/autoload.php'; class_exists('Classes\\\\$c');" | grep -E 'Fatal|Deprecated' | cut -c1-200; done
echo "--- A2: Table sem banco (adaptador simulado):"; php_sem_rede altA2 /t.php
