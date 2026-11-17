<?php
// T-028: graficos de pizza do jpgraph geram a mesma imagem no 5.6 e no 8.5.
// Hashes = md5 dos pixels medidos no PHP 5.6 (gabarito) antes da correcao. Sem banco, sem rede.
use PHPUnit\Framework\TestCase;

class JpgraphPizzaTest extends TestCase
{
    private function gera($tipo)
    {
        $cmd = escapeshellarg(PHP_BINARY) . ' ' . escapeshellarg(__DIR__ . '/gera_pizza.php') . ' ' . escapeshellarg($tipo) . ' 2>&1';
        return trim(shell_exec($cmd));
    }

    public function testPiePlotCImagemIgualAoGabarito56()
    {
        $this->assertSame('300x250 7992ae1f7f2fec81d95d3b42fbb748be', $this->gera('c'));
    }

    public function testPiePlotImagemIgualAoGabarito56()
    {
        $this->assertSame('300x250 08a324986e0db11851bd0264d6d27bc2', $this->gera('pie'));
    }

    public function testPiePlot3DImagemIgualAoGabarito56()
    {
        $this->assertSame('350x280 aedf7d12255f9828fb2a5f6269ee868c', $this->gera('3d'));
    }

    public function testGraficoDoRelatorioRreqTotaisImagemIgualAoGabarito56()
    {
        $this->assertSame('350x280 b7b3717d27f5817b8454caab390c518c', $this->gera('rreq'));
    }
}
