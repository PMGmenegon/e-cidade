<?php
/** Duble: PhpOffice\PhpWord gera .docx (texto, tabela, quebra de pagina), conteudo fixo, sem banco; imprime o docx em stdout. */
chdir(__DIR__ . '/../../../..');   // ecidade/
require_once 'vendor/autoload.php';
error_reporting(E_ALL & ~E_DEPRECATED);
$w = new PhpOffice\PhpWord\PhpWord();
$s = $w->addSection();
$s->addText('Ata de teste - acentuacao: ação, é, ü', ['bold' => true, 'size' => 14]);
$s->addText('Paragrafo com valor R$ 1.234,56.');
$t = $s->addTable();
foreach ([['Item', 'Valor'], ['Taxa A', '100,00'], ['Taxa B', '1.134,56']] as $l) {
    $t->addRow(); foreach ($l as $c) { $t->addCell(3000)->addText($c); }
}
$s->addPageBreak();
$s->addText('Segunda pagina.');
$arq = tempnam(sys_get_temp_dir(), 't024');
PhpOffice\PhpWord\IOFactory::createWriter($w, 'Word2007')->save($arq);
echo file_get_contents($arq);
unlink($arq);
