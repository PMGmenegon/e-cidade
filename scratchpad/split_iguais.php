<?php
/**
 * T-040: confere os padroes classificados "igual" pela split_varredura.php: cada valor distinto
 * (coluna valor, escapada por addcslashes) contra entradas que o contem, nos dois runtimes.
 * Uso (no container): php split_iguais.php /var/www/html/vendor/autoload.php <iguais.txt>
 */
error_reporting(E_ALL & ~E_DEPRECATED);
require $argv[1];
foreach (file($argv[2], FILE_IGNORE_NEW_LINES) as $esc) {
    $p = stripcslashes($esc);
    foreach (array("a{$p}b{$p}{$p}c", "{$p}", "", "sem") as $s) {
        echo json_encode(array($p, $s, @split($p, $s))), "\n";
    }
}
