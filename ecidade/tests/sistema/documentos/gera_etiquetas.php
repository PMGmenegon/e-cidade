<?php
// Etiquetas Pimaco do Patrimonio (EtiquetaModelo01/02Builder + EtiquetasPimacoPDF reais) e QR Code (PHPQRCode, como ArrecadacaoPixService e mod_imprime2).
require __DIR__ . '/lib.php';

use App\Domain\Patrimonial\Patrimonio\Builders\EtiquetaModelo01Builder;
use App\Domain\Patrimonial\Patrimonio\Builders\EtiquetaModelo02Builder;
use App\Domain\Patrimonial\Patrimonio\Relatorios\EtiquetasPimacoPDF;

class EtiquetasParaTeste extends EtiquetasPimacoPDF
{
    private $tags;

    public function __construct($tags, $template, $path = null)
    {
        parent::__construct($tags, $template, $path);
        $this->tags = $tags;
    }

    public function pdfEmString()
    {
        foreach ($this->tags as $tag) {
            $this->addTag($tag);
        }
        $this->pdf->WriteHTML($this->render());
        return $this->pdf->Output('', 'S');
    }
}

foreach ([1 => EtiquetaModelo01Builder::class, 2 => EtiquetaModelo02Builder::class] as $n => $classe) {
    $tags = [];
    for ($i = 1; $i <= 12; $i++) {
        $b = new $classe();
        $b->setInstituicao('PREFEITURA MUNICIPAL DE EXEMPLO');
        $b->setCodigo(1000 + $i);
        $b->setPlaca(sprintf('%06d', 5000 + $i));
        $b->setDescricao("Cadeira giratoria modelo $i com descricao longa");
        $b->setBarcode(sprintf('%06d', 5000 + $i));
        $b->create();
        $tags[] = $b->getEtiqueta();
    }
    $dir = ECIDADE_PATH . 'app/Domain/Patrimonial/Patrimonio/Relatorios/TemplatesEtiquetas/';
    $e = new EtiquetasParaTeste($tags, "A4351_MODELO0$n", $dir);
    emitir("pimaco-modelo0$n.pdf", $e->pdfEmString());
}

foreach (['L' => 4, 'M' => 5] as $nivel => $tam) {
    \PHPQRCode\QRcode::png('https://exemplo.gov.br/pix/00020126580014br.gov.bcb.pix0136123e4567-e89b-12d3-a456-426655440000', "/tmp/qr_$nivel.png", $nivel, $tam, 2);
    emitir("qr-$nivel.png", file_get_contents("/tmp/qr_$nivel.png"));
}
