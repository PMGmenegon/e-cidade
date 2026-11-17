<?php
// Bateria dirigida da T-021: exercita as bibliotecas portadas e imprime um resumo comparavel entre runtimes.
// Uso (dentro do container, em /var/www/html): php /tmp/bateria_t021.php <pasta-de-saida>
// Nao toca no banco. Saida: uma linha "item: valor" por verificacao.
error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED & ~E_STRICT & ~E_WARNING);
ini_set('display_errors', '1');
$saida = isset($argv[1]) ? $argv[1] : '/tmp/t021';
@mkdir($saida, 0777, true);
chdir('/var/www/html');

function linha($k, $v) { echo str_pad($k . ':', 34) . $v . "\n"; }

// pixels do PNG (independe da versao do libgd na compressao): md5 dos valores RGBA
function hashPixels($arq) {
    $im = @imagecreatefrompng($arq);
    if (!$im) return 'PNG ilegivel';
    $w = imagesx($im); $h = imagesy($im); $acc = '';
    for ($y = 0; $y < $h; $y++) for ($x = 0; $x < $w; $x++) $acc .= pack('N', imagecolorat($im, $x, $y));
    return "{$w}x{$h} " . md5($acc);
}

// 1. Michelf (Markdown / MarkdownExtra)
require_once 'ext/php/Michelf/MarkdownInterface.php';
require_once 'ext/php/Michelf/Markdown.php';
require_once 'ext/php/Michelf/MarkdownExtra.php';
$md = "Titulo\n======\n\nSub\n---\n\n*em* **forte** `codigo` &amp; <b>html</b>\n\n* a\n* b\n\n    bloco\n\n[link](http://x.y \"t\")\n\n<div>cru</div>\n\nTexto com _sublinhado_ e ***tudo***.\n";
linha('michelf Markdown', md5(\Michelf\Markdown::defaultTransform($md)));
$extra = $md . "\n| a | b |\n|---|---|\n| 1 | 2 |\n\nTermo\n:   definicao\n\n# Cab {#idx .cls}\n\nNota[^1].\n\n[^1]: rodape\n\n*[HTML]: Hyper Text\n\nHTML aqui\n";
linha('michelf MarkdownExtra', md5(\Michelf\MarkdownExtra::defaultTransform($extra)));

// 2. jpgraph pie (PiePlotC) e radar -- cada um isolado: o que falhar, falha so ele
if (!function_exists('modification')) { function modification($f) { return $f; } } // o bootstrap do e-cidade define; aqui basta o identico
function tenta($rotulo, $f) {
    try { linha($rotulo, $f()); }
    catch (Exception $e) { linha($rotulo, 'EXCECAO ' . get_class($e) . ': ' . substr($e->getMessage(), 0, 90)); }
    catch (Error $e) { linha($rotulo, 'EXCECAO ' . get_class($e) . ': ' . substr($e->getMessage(), 0, 90)); } // 7+/8; no 5.6 a classe nem existe
}
tenta('jpgraph carga pie+radar', function () {
    require_once 'libs/jpgraph/jpgraph.php';
    require_once 'libs/jpgraph/jpgraph_pie.php';
    require_once 'libs/jpgraph/jpgraph_radar.php';
    return 'ok';
});
tenta('jpgraph PiePlotC', function () use ($saida) {
    $g = new PieGraph(300, 250, '');
    $g->SetShadow(false);
    $p = new PiePlotC(array(40, 30, 20, 10));
    $p->SetSliceColors(array('red', 'green', 'blue', 'orange'));
    $p->SetMidSize(0.4);
    $g->Add($p);
    @unlink("$saida/pie.png");
    $g->Stroke("$saida/pie.png");
    return is_file("$saida/pie.png") ? hashPixels("$saida/pie.png") : 'sem arquivo';
});
tenta('jpgraph RadarGraph', function () use ($saida) {
    $r = new RadarGraph(300, 250, '');
    $r->SetScale('lin');
    $r->SetTitles(array('A', 'B', 'C', 'D', 'E'));
    $rp = new RadarPlot(array(10, 20, 15, 5, 12));
    $rp->SetColor('blue');
    $r->Add($rp);
    @unlink("$saida/radar.png");
    $r->Stroke("$saida/radar.png");
    return is_file("$saida/radar.png") ? hashPixels("$saida/radar.png") : 'sem arquivo';
});

// 3. securimage: classe carrega; WavFile troca amostra ja existente (ramo "replace"); audio do captcha com codigo fixo
require_once 'securimage/securimage.php';
require_once 'securimage/WavFile.php';
tenta('securimage instancia', function () { $si = new Securimage(); return get_class($si); });
tenta('WavFile replace', function () {
    $w = new WavFile(1, 8000, 16);
    $w->setSampleValue(0.25, 0, 1);
    $w->setSampleValue(0.50, 1, 1);
    $w->setSampleValue(-0.5, 0, 1);   // ramo "replace": usa $this->_samples[...] = $sampleBinary[...]
    return $w->getNumBlocks() . ' blocos, bloco0=' . round($w->getSampleValue(0, 1), 4) . ' md5=' . md5($w->__toString());
});
tenta('securimage audio (codigo fixo)', function () {
    $si = new Securimage(array('display_value' => 'AB3', 'no_exit' => true, 'no_session' => true)); // getAudibleCode(): ramo $code['display'][$i]
    $m = new ReflectionMethod('Securimage', 'getAudibleCode');
    $m->setAccessible(true);
    $wav = $m->invoke($si);
    return get_class($wav) . ' ' . md5($wav->__toString());
});
