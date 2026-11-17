<?php
// T-041: soma e variancia do AgataReport com celula nao numerica dao o mesmo resultado no 5.6 e no 8.5.
// Esperado = o que o 5.6 produz com a expressao ORIGINAL ($s = 0; $s += $celula; pow($celula - 2.5, 2)), tipo incluido.
use PHPUnit\Framework\TestCase;

class AgataReportSomaTest extends TestCase
{
    // celula, tipo da soma, soma, variancia (pow($celula - 2.5, 2))
    public function casos()
    {
        return array(
            array('12', 'integer', 12, 90.25),
            array('1.5', 'double', 1.5, 1.0),
            array('abc', 'integer', 0, 6.25),
            array('', 'integer', 0, 6.25),
            array(null, 'integer', 0, 6.25),
            array('12abc', 'integer', 12, 90.25),
            array(' 3', 'integer', 3, 0.25),
            array('3 ', 'integer', 3, 0.25),
            array('1e3x', 'double', 1000.0, 995006.25),
            array('-4.5kg', 'double', -4.5, 49.0),
            array('.5', 'double', 0.5, 4.0),
            array('5.', 'double', 5.0, 6.25),
            array('+7z', 'integer', 7, 20.25),
            array('1.5e2', 'double', 150.0, 21756.25),
            array('0x1A', 'integer', 26, 552.25),
            array('-0x1A', 'integer', 0, 6.25),
            array('abc12', 'integer', 0, 6.25),
            array('1e', 'integer', 1, 2.25),
            array('012', 'integer', 12, 90.25),
        );
    }

    private function relatorio()
    {
        require_once __DIR__ . '/../../../dbagata/classes/reports/AgataReport.class';
        $r = new ReflectionClass('AgataReport');
        return $r->newInstanceWithoutConstructor();
    }

    public function testSomaEVarianciaIgualAoCinco6()
    {
        $ar = $this->relatorio();
        foreach ($this->casos() as $c) {
            list($celula, $tipo, $soma, $var) = $c;
            $nome = var_export($celula, true);
            $s = 0;
            $s += $ar->CellNumber($celula);          // linha 'sum' do PreProcessBreaks
            $v = pow($ar->CellNumber($celula) - 2.5, 2); // linha 'sum_var' do ProcessBreaks
            $this->assertSame($tipo, gettype($s), "tipo da soma de $nome");
            $this->assertEquals($soma, $s, "soma de $nome");
            $this->assertEquals($var, $v, "variancia de $nome", 0.0000001);
        }
    }
}
