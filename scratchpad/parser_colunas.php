<?php
// T-065: em cada planilha-modelo, por aba: coluna mais alta (getHighestColumn, o fim padrao do getCellIterator do
// Template/Parser.php) x coluna mais alta com celula (getHighestDataColumn), mais a ultima coluna com valor nao vazio.
// Uso (dentro do container, /var/www/html = ecidade/): php parser_colunas.php <lista de caminhos relativos a ecidade/>
chdir('/var/www/html');
require 'vendor/autoload.php';
error_reporting(E_ALL & ~E_DEPRECATED & ~E_WARNING);
use PhpOffice\PhpSpreadsheet\Cell\Coordinate;
foreach (file($argv[1], FILE_IGNORE_NEW_LINES) as $a) {
    $a = preg_replace('#^ecidade/#', '', $a);
    if ($a === '') continue;
    try { $wb = PhpOffice\PhpSpreadsheet\IOFactory::load($a); }
    catch (Throwable $e) { echo "$a\tERRO\t" . get_class($e) . "\n"; continue; }
    foreach ($wb->getAllSheets() as $i => $ws) {
        $max = 0;
        foreach ($ws->getCellCollection()->getCoordinates() as $c) {
            $v = $ws->getCell($c)->getValue();
            if (str_replace(' ', '', (string) (is_object($v) ? $v->getPlainText() : $v)) !== '') {
                $max = max($max, Coordinate::columnIndexFromString(preg_replace('/\d+/', '', $c)));
            }
        }
        printf("%s\t%d\t%s\t%s\t%s\n", $a, $i, $ws->getHighestColumn(), $ws->getHighestDataColumn(), $max ? Coordinate::stringFromColumnIndex($max) : '-');
    }
}
