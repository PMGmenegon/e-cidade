<?php
/**
 * Duble: etiquetas Pimaco do Patrimonial (Proner\PhpPimaco + mPDF + picqer/php-barcode-generator, codigo 128).
 * Usa as classes REAIS do sistema (EtiquetaModelo01/02Builder, EtiquetasPimacoPDF) com 4 bens inventados: a base de
 * exemplo nao tem bens (tabela bens vazia). Roda por CLI, sem HTTP e sem banco; imprime o PDF em stdout.
 */
chdir(__DIR__ . '/../../../..');   // ecidade/
require_once 'vendor/autoload.php';
function modification($c) { return $c; }
error_reporting(E_ALL & ~E_DEPRECATED);

use App\Domain\Patrimonial\Patrimonio\Builders\EtiquetaModelo01Builder;
use App\Domain\Patrimonial\Patrimonio\Builders\EtiquetaModelo02Builder;
use App\Domain\Patrimonial\Patrimonio\Relatorios\EtiquetasPimacoPDF;

$dir = 'app/Domain/Patrimonial/Patrimonio/Relatorios/TemplatesEtiquetas/';
foreach ([['A4351_MODELO01', EtiquetaModelo01Builder::class], ['A4351_MODELO02', EtiquetaModelo02Builder::class]] as list($tpl, $classe)) {
    $dados = [];
    foreach ([[1, '000123', 'MESA DE ESCRITORIO EM MADEIRA'], [2, '000124', 'CADEIRA GIRATORIA'], [3, '000125', 'ARMARIO DE ACO 2 PORTAS'], [4, '000126', 'COMPUTADOR DESKTOP']] as list($cod, $placa, $desc)) {
        $b = new $classe();
        $b->setInstituicao('PREFEITURA DBSELLER'); $b->setCodigo($cod); $b->setPlaca($placa); $b->setDescricao($desc); $b->setBarcode($placa);
        $b->create();
        $dados[] = $b->getEtiqueta();
    }
    $arq = (new EtiquetasPimacoPDF($dados, $tpl, $dir))->gerar();
    if ($tpl === 'A4351_MODELO01') { $primeiro = file_get_contents($arq); }
    @unlink($arq);
    $ultimo = $tpl;
}
// um PDF por modelo seria 2 casos; aqui o modelo 01 e a saida (o 02 so precisa gerar sem erro)
echo $primeiro;
