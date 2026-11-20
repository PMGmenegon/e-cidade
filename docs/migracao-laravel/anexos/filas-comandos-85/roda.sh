#!/bin/bash
# PHP8-51: console (comandos e agendamento), payload de fila e funcoes removidas, 7.4 x 8.5,
# sem banco (host inexistente) e sem rede (--network none). ecidade/ montado so leitura;
# .env de teste gerado do .env.example por cima; bootstrap/cache em tmpfs e storage/ numa pasta da saida.
# Uso: roda.sh <ecidade> <vendor 7.4> <vendor 8.5> <img 7.4> <img 8.5> <saida>
#   vendor 7.4 = composer install do ecidade/composer.lock do PR; vendor 8.5 = runtime-85/vendor (docker/composer-85/composer-85.sh install)
#   img 7.4 = construida de docker/php74-apache; img 8.5 = construida de docker/php85-apache
set -u
E=$(realpath "$1"); V74=$(realpath "$2"); V85=$(realpath "$3"); I74=$4; I85=$5; O=$(realpath -m "$6"); T=$(dirname "$(realpath "$0")")
mkdir -p "$O"; python3 "$T/gera_env.py" "$E/.env.example" "$O/env"
r() {   # r <74|85> <script> [args]
  local v=$1 img=$I74 ven=$V74; shift; [ $v = 85 ] && img=$I85 && ven=$V85
  mkdir -p "$O/storage$v"; (cd "$E/storage" && find . -type d -exec mkdir -p "$O/storage$v/{}" \;)
  docker run --rm --network none -u "$(id -u):$(id -g)" -v "$E:/e:ro" -v "$ven:/e/vendor:ro" -v "$O/env:/e/.env:ro" \
    --tmpfs "/e/bootstrap/cache:uid=$(id -u)" -v "$O/storage$v:/e/storage" -v "$T:/s:ro" -v "$O:/o:ro" -w /e "$img" \
    php -d error_reporting='E_ALL&~E_DEPRECATED&~E_NOTICE&~E_WARNING' "$@"
}
grep -l -a -r 'implements ShouldQueue' "$E/app" | sed "s#^$E/app/#App/#; s#\.php\$##; s#/#\\\\#g" | sort > "$O/jobs.lista"
for v in 74 85; do
  r $v /s/console.php > "$O/console$v.txt" 2>&1
  r $v artisan list --raw > "$O/list$v.txt" 2>&1
  r $v /s/funcoes.php > "$O/funcoes$v.txt" 2>&1
  : > "$O/jobs$v.txt"; while read -r c; do r $v /s/jobs.php "$c" >> "$O/jobs$v.txt" 2>&1 </dev/null; done < "$O/jobs.lista"
done
for de in 74 85; do for em in 74 85; do r $em /s/cruzado.php /o/jobs$de.txt > "$O/cruzado_${de}_lido_no_$em.txt" 2>&1; done; done
c() { cmp -s "$O/$1" "$O/$2" && echo "igual" || echo "DIFERE"; }
echo "artisan list:          $(c list74.txt list85.txt) ($(wc -l < "$O/list74.txt") linhas)"
echo "comandos e agenda:     $(c console74.txt console85.txt) ($(grep -c "'classe' =>" "$O/console74.txt") comandos, $(grep -c "'cron' =>" "$O/console74.txt") eventos)"
echo "jobs (payload):        $(diff <(grep -v '^command:' "$O/jobs74.txt") <(grep -v '^command:' "$O/jobs85.txt") >/dev/null && echo igual || echo DIFERE) ($(grep -c '^== ' "$O/jobs74.txt") classes; command serializado diferente em $(diff <(grep '^command' "$O/jobs74.txt") <(grep '^command' "$O/jobs85.txt") | grep -c '^<'))"
echo "jobs (estado cruzado): $(md5sum "$O"/cruzado_* | awk '{print $1}' | sort -u | wc -l) estado(s) distinto(s) em 4 leituras (1 = igual)"
echo "funcoes:               $(diff "$O/funcoes74.txt" "$O/funcoes85.txt" | grep -c '^<') linha(s) diferente(s) de $(wc -l < "$O/funcoes74.txt")"
