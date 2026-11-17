<?php
/**
 * Duble (importacao de planilha): le os arquivos de exemplo que existem no repositorio com a mesma
 * biblioteca do sistema (PhpOffice\PhpSpreadsheet IOFactory, como em src/Library/SpreadSheet/Template/Parser.php) e com
 * fgetcsv (como as telas de importacao CSV). Imprime abas, dimensoes e um resumo dos valores; sem HTTP, sem banco.
 * Arquivos: config/templates/IN22/*.xlsx (modelos TCE-RO) e config/financeiro/siconfi/recursos/recurso_*.csv.
 */
chdir(__DIR__ . '/../../../..');   // ecidade/
require_once 'vendor/autoload.php';
error_reporting(E_ALL & ~E_DEPRECATED);

$arqs = glob('config/templates/IN22/*.xlsx');
sort($arqs);
foreach ($arqs as $a) {
    $wb = PhpOffice\PhpSpreadsheet\IOFactory::load($a);
    echo "== $a (abas: " . implode(',', $wb->getSheetNames()) . ")\n";
    foreach ($wb->getAllSheets() as $ws) {
        $n = 0; $h = hash_init('sha256');
        // mesmo fim de linha do Template/Parser.php (ultimaColuna): a mais alta, salvo XFD (PhpSpreadsheet 2+ com
        // <col max="16384">), quando vai ate a ultima coluna com celula; com a 1.8.2 e o mesmo que getCellIterator()
        $fim = $ws->getHighestColumn() === 'XFD' ? $ws->getHighestDataColumn() : $ws->getHighestColumn();
        foreach ($ws->getRowIterator() as $row) {
            foreach ($row->getCellIterator('A', $fim) as $c) {
                $v = $c->getValue();
                if ($v !== null && $v !== '') { $n++; hash_update($h, $c->getCoordinate() . '=' . $v . "\n"); }
            }
        }
        echo '   ' . $ws->getTitle() . ' ' . $ws->calculateWorksheetDimension() . " celulas=$n sha=" . substr(hash_final($h), 0, 12) . "\n";
    }
}
$csvs = glob('config/financeiro/siconfi/recursos/recurso_*.csv');
sort($csvs);
foreach ($csvs as $a) {
    $f = fopen($a, 'r'); $linhas = 0; $campos = 0; $h = hash_init('sha256');
    while (($d = fgetcsv($f, 0, ',')) !== false) { $linhas++; $campos += count($d); hash_update($h, implode('|', $d) . "\n"); }
    fclose($f);
    echo "== $a linhas=$linhas campos=$campos sha=" . substr(hash_final($h), 0, 12) . "\n";
}
