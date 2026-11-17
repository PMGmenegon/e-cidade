<?php
/**
 * Duble: exercita o que os emissores de boleto/carne/empenho usam e a base de exemplo nao tem dados para acionar.
 *  - codigo de barras intercalado 2 de 5 (FPDF::int25, fpdf151/fpdf.php) desenhado num PDF sem compressao;
 *  - QR do documento (\PHPQRCode\QRcode::png, aferrandini/phpqrcode, como em fpdf151/impmodelos/mod_imprime6.php).
 * Roda por CLI nos dois runtimes (documentos.py, caso "cli:"), sem HTTP e sem banco; imprime o PDF em stdout. O PNG do QR
 * e gravado em /tmp e embutido na pagina; a matriz de pixels vai como texto na 2a pagina para ser comparada.
 */
chdir(__DIR__ . '/../../../..');   // ecidade/ (dirname com nivel nao existe no 5.6)
require_once 'vendor/autoload.php';
function modification($c) { return $c; }
define('FPDF_FONTPATH', 'fpdf151/font/');
require_once 'fpdf151/fpdf.php';

$pdf = new FPDF();
$pdf->SetCompression(false);
$pdf->Open();
$pdf->AddPage('P');
$pdf->SetFont('Arial', '', 9);
$pdf->SetFillColor(0);
foreach (['000000000012345', '827700000015432100010015310020011000122299', '34191790010104351004791020150008291070026000'] as $i => $cod) {
    $y = 20 + $i * 30;
    $pdf->text(13, $y - 3, $cod);
    $pdf->int25(13, $y, $cod, 12, 0.341);
}
$arq = '/tmp/t024_qr.png';
\PHPQRCode\QRcode::png('https://exemplo.invalid/autenticidade/00000000-0000-0000-0000-000000000000', $arq, 'L', 5, 1);
$pdf->Image($arq, 150, 15, 40);
$pdf->AddPage('P');
$im = imagecreatefrompng($arq);
$w = imagesx($im); $h = imagesy($im);
$linhas = [];
for ($y = 0; $y < $h; $y++) {
    $l = '';
    for ($x = 0; $x < $w; $x++) { $l .= (imagecolorat($im, $x, $y) & 0xFF) < 128 ? 'X' : '.'; }
    $linhas[] = $l;
}
$pdf->SetFont('Courier', '', 3);
foreach ($linhas as $n => $l) { $pdf->text(5, 10 + $n * 1.4, $l); }
$pdf->SetFont('Arial', '', 9);
$pdf->text(5, 280, "QR {$w}x{$h} sha=" . substr(hash_file('sha256', $arq), 0, 16));
unlink($arq);
$pdf->Output();
