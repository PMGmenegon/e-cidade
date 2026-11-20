<?php
// PhpWord TemplateProcessor sobre os modelos .docx do codigo (Contrato.php: contrato de agua; certidoes do cadastro).
require __DIR__ . '/lib.php';

use PhpOffice\PhpWord\Settings;
use PhpOffice\PhpWord\TemplateProcessor;

Settings::setTempDir('/tmp');
$modelos = array_merge(
    [ECIDADE_PATH . 'documentos/templates/agua/contrato.docx'],
    glob(ECIDADE_PATH . 'documentos/templates/cadastro/*.docx')
);
sort($modelos);
foreach ($modelos as $m) {
    $t = new TemplateProcessor($m);
    foreach ($t->getVariables() as $v) {
        $t->setValue($v, 'Valor de ' . $v . ' & acentuação');
    }
    $saida = '/tmp/saida_' . basename($m);
    $t->saveAs($saida);
    emitir('docx-' . basename($m), file_get_contents($saida));
}
