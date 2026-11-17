<?php
/**
 * T-040: mesmo split() nos dois runtimes. No 5.6 e o split() POSIX nativo; no 8.5 e o polyfill
 * do vendor (dbseller/legacy, bootstrap/PHP_56.php: explode). Carrega o autoload do composer como
 * toda tela carrega (bootstrap.php). Cada padrao e um dos que a varredura classificou "diverge",
 * mais "|" e "." (sem uso no PHP, so em JavaScript), cada um com entradas do tipo que o codigo trata.
 *
 * Uso (no container): php split_compara.php /var/www/html/vendor/autoload.php
 */
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', 'stderr');
require $argv[1];

$casos = array(
    array('\?', 'con2_relatorio.php?ano=2026&mes=11'),
    array('\?', 'sem interrogacao'),
    array('\|', '10|20|30'),
    array('\.', '1.234.567'),
    array('\.', '01.02'),
    array('[/.-]', '13/11/2026'),
    array('[/.-]', '2026-11-13'),
    array('[/.-]', '13.11.2026'),
    array("[\n\r]", "linha1\r\nlinha2\nlinha3"),
    array('\(', 'funcao(arg)'),
    array('[|]', 'a|b|c'),
    array('|', 'a|b|c'),
    array('.', 'a.b.c'),
);
echo 'PHP ', PHP_VERSION, ' split ', (function_exists('split') ? 'definido' : 'AUSENTE'), "\n";
foreach ($casos as $c) {
    $r = @split($c[0], $c[1]);
    printf("%-10s %-40s => %s\n", json_encode($c[0]), json_encode($c[1]), json_encode($r));
}
