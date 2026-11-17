<?php
// T-065: roda o Template/Parser.php do sistema (loadXLS + parse + save .xlsx) em cada planilha-modelo da lista, sem
// dados (as variaveis e secoes ficam sem colecao, como num relatorio sem movimento). Uma linha por modelo: status e
// memoria de pico. Os .xlsx saem em <saida>/ para o t065_dump.php descrever.
// Uso (no container, /var/www/html = ecidade/): php -d memory_limit=512M t065_parser.php <lista> <saida>
chdir('/var/www/html');
require 'vendor/autoload.php';
require_once 'src/Library/SpreadSheet/Template/Parser.php';   // ECidade\ vem do autoloader do bootstrap.php, nao do Composer
error_reporting(E_ALL & ~E_DEPRECATED & ~E_WARNING & ~E_NOTICE);
register_shutdown_function(function () {
    $e = error_get_last();
    if ($e && ($e['type'] & (E_ERROR | E_CORE_ERROR | E_COMPILE_ERROR))) echo "FATAL\t", $e['message'], "\n";
});
$saida = rtrim($argv[2], '/');
@mkdir($saida, 0777, true);
foreach (file($argv[1], FILE_IGNORE_NEW_LINES) as $a) {
    $a = preg_replace('#^ecidade/#', '', $a);
    if ($a === '') continue;
    echo $a, "\t";
    try {
        $p = new ECidade\Library\SpreadSheet\Template\Parser();
        $p->loadXLS($a);
        $p->parse();
        $p->save($saida . '/' . str_replace('/', '__', $a) . '.out.xlsx');
        echo "ok\n";
    } catch (Throwable $e) {
        echo get_class($e), ': ', $e->getMessage(), "\n";
    }
}
