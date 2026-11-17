<?php
// T-028: gera um grafico de pizza do jpgraph e imprime "LxA md5-dos-pixels" (ou "ERRO ..."). Uso: php gera_pizza.php <c|pie|3d|rreq>
// Roda em processo proprio: o jpgraph guarda estado global e o resultado dependia da ordem dos testes no PHPUnit.
error_reporting(E_ALL & ~E_WARNING & ~E_NOTICE & ~E_DEPRECATED & ~E_STRICT);
ini_set('display_errors', '0');
require_once __DIR__ . '/../bootstrap.php';
$raiz = __DIR__ . '/../../../libs/jpgraph/';
$tipo = isset($argv[1]) ? $argv[1] : '';
$arq = tempnam(sys_get_temp_dir(), 'pizza') . '.png';
try {
    require_once $raiz . 'jpgraph.php';
    require_once $raiz . 'jpgraph_pie.php';
    $legendas = array('a', 'b', 'c', 'd');
    if ($tipo === 'c') {
        $g = new PieGraph(300, 250, '');
        $g->SetShadow(false);
        $p = new PiePlotC(array(40, 30, 20, 10));
        $p->SetSliceColors(array('red', 'green', 'blue', 'orange'));
        $p->SetMidSize(0.4);
        $p->SetLegends($legendas);
    } elseif ($tipo === 'pie') {
        $g = new PieGraph(300, 250, '');
        $p = new PiePlot(array(40, 30, 20, 10));
        $p->SetSliceColors(array('red', 'green', 'blue', 'orange'));
        $p->SetLegends($legendas);
    } elseif ($tipo === 'rreq') {
        // configuracao do grafico "Total Por Bairro" de libs/jpgraph/ass_rreqtotais002.php, com dados de exemplo, sem o cache 'auto' e sem as fontes TTF (nao instaladas nos containers)
        require_once $raiz . 'jpgraph_pie3d.php';
        $dados = array(12, 7, 5, 3);
        $legend = array('Centro', 'Norte', 'Sul', 'Leste');
        $g = new PieGraph(350, 280, '');
        $g->SetShadow();
        $g->title->Set('Total Por Bairro');
        $g->title->SetColor('darkblue');
        $g->legend->Pos(0.0, 0.1);
        $g->legend->SetFillColor('#FFFFFF@1');
        $g->img->SetAntiAliasing();
        $g->SetFrame(false);
        $p = new PiePlot3d($dados);
        $p->SetTheme('sand');
        $p->SetEdge('white');
        $p->SetCenter(0.32);
        $p->SetAngle(45);
        $p->SetSize(88);
        $p->SetLegends($legend);
    } else {
        require_once $raiz . 'jpgraph_pie3d.php';
        $g = new PieGraph(350, 280, '');
        $dados = array(40, 30, 20, 10);
        $p = new PiePlot3d($dados);
        $p->SetTheme('sand');
        $p->SetEdge('white');
        $p->SetCenter(0.32);
        $p->SetAngle(45);
        $p->SetSize(88);
        $p->SetLegends($legendas);
    }
    $g->Add($p);
    $g->Stroke($arq);
    $im = imagecreatefrompng($arq);
    $acc = '';
    for ($y = 0; $y < imagesy($im); $y++) {
        for ($x = 0; $x < imagesx($im); $x++) {
            $acc .= pack('N', imagecolorat($im, $x, $y));
        }
    }
    echo imagesx($im) . 'x' . imagesy($im) . ' ' . md5($acc), "\n";
} catch (Exception $e) {
    echo 'ERRO ', get_class($e), ': ', substr($e->getMessage(), 0, 120), "\n";
} catch (Throwable $e) {
    echo 'ERRO ', get_class($e), ': ', substr($e->getMessage(), 0, 120), "\n";
}
if (is_file($arq)) {
    unlink($arq);
}
