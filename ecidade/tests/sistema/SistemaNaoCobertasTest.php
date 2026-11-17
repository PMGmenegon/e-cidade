<?php
// T-012: o que a bateria de sistema NAO cobre, com o motivo, conferido contra o codigo (a lista nao pode envelhecer).
use PHPUnit\Framework\TestCase;

class SistemaNaoCobertasTest extends TestCase
{
    private function raiz()
    {
        return dirname(dirname(__DIR__));
    }

    private function arquivos($pasta, $regex, array $exclui)
    {
        $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($pasta, FilesystemIterator::SKIP_DOTS));
        $saida = array();
        foreach ($it as $f) {
            $p = str_replace($this->raiz() . '/', '', (string) $f);
            if (!preg_match('/\.(php|js)$/', $p)) {
                continue;
            }
            $pula = false;
            foreach ($exclui as $e) {
                if (strpos($p, $e . '/') === 0 || strpos($p, '/' . $e . '/') !== false) {
                    $pula = true;
                }
            }
            if (!$pula && preg_match($regex, file_get_contents((string) $f))) {
                $saida[] = $p;
            }
        }
        sort($saida);
        return $saida;
    }

    public function testListaRegistradaConfereComOCodigo()
    {
        $kernel = array();
        foreach (glob($this->raiz() . '/*.php') as $f) {
            if (preg_match('/Illuminate\\\\Contracts\\\\Http\\\\Kernel/', file_get_contents($f))) {
                $kernel[] = basename($f);
            }
        }
        sort($kernel);
        $js = $this->arquivos($this->raiz(), '#[\'"/]v4/#', array('vendor', 'app', 'tmp', 'routes', 'node_modules', 'tests', 'storage', 'bootstrap'));
        $esperado = array();
        foreach (file(__DIR__ . '/dados/nao-cobertas.tsv', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) {
            $c = explode("\t", $l);
            $esperado[$c[0]][] = $c[1];
        }
        sort($esperado['kernel']);
        sort($esperado['v4-js']);
        $this->assertSame($esperado['kernel'], $kernel, 'relatorios que sobem o kernel mudaram');
        $this->assertSame($esperado['v4-js'], $js, 'arquivos que chamam /v4 mudaram');
        $this->assertCount(5, $kernel);
        $this->assertCount(30, $js);
    }
}
