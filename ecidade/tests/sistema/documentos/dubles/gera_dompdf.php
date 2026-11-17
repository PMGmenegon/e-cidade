<?php
/** Duble: Dompdf (HTML -> PDF, como em src/Tributario/Grm/WebService/BoletoGrm.php), HTML fixo, sem banco. */
chdir(__DIR__ . '/../../../..');   // ecidade/
require_once 'vendor/autoload.php';
error_reporting(E_ALL & ~E_DEPRECATED);
$html = '<html><head><meta charset="utf-8"><style>body{font-family:sans-serif;font-size:11pt} table{border-collapse:collapse} td,th{border:1px solid #000;padding:3px}</style></head><body>'
      . '<h2>Boleto de teste</h2><p>Valor: R$ 1.234,56 &mdash; Vencimento 31/12/2026 &mdash; a&ccedil;&atilde;o &eacute; &uacute;nica</p>'
      . '<table><tr><th>Item</th><th>Valor</th></tr><tr><td>Taxa A</td><td>100,00</td></tr><tr><td>Taxa B</td><td>1.134,56</td></tr></table></body></html>';
$d = new Dompdf\Dompdf();
$d->loadHtml($html);
$d->setPaper('A4', 'portrait');
$d->render();
echo $d->output();
