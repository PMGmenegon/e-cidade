<?php
// T-065: descreve um .xlsx lido SEMPRE pelo PhpSpreadsheet do 5.6 (1.8.2): por aba, titulo, celulas com valor
// (coordenada=valor), celulas mescladas e, por celula com valor, negrito/borda/alinhamento. Assim a saida gerada
// pelo 5.6 e a gerada pelo runtime novo sao descritas pelo mesmo leitor.
// Uso (no container 5.6): php t065_dump.php <arquivo.xlsx> [--sem-estilo]
chdir('/var/www/html');
require 'vendor/autoload.php';
error_reporting(E_ALL & ~E_DEPRECATED & ~E_WARNING & ~E_NOTICE);
$wb = PhpOffice\PhpSpreadsheet\IOFactory::load($argv[1]);
$estilo = !in_array('--sem-estilo', $argv);
foreach ($wb->getAllSheets() as $ws) {
    echo '== aba ', $ws->getTitle(), "\n";
    $m = array_keys($ws->getMergeCells()); sort($m);
    echo 'mescladas: ', implode(' ', $m), "\n";
    foreach ($ws->getCellCollection()->getCoordinates() as $c) {
        $cel = $ws->getCell($c); $v = $cel->getValue();
        if ($v === null || $v === '') continue;
        $l = $c . '=' . (is_object($v) ? $v->getPlainText() : var_export($v, true));
        if ($estilo) {
            $s = $ws->getStyle($c);
            $l .= ' b=' . (int) $s->getFont()->getBold() . ' borda=' . $s->getBorders()->getTop()->getBorderStyle()
                . ' alin=' . $s->getAlignment()->getHorizontal() . '/' . $s->getAlignment()->getVertical();
        }
        echo $l, "\n";
    }
}
