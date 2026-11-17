<?php
// T-019 (reaberta): $$matriz[$i] e ${$matriz[$i]} no 5.6, mas ($$matriz)[$i] no PHP 7+ (a variavel nao e criada).
// calculoiptu.php e calculoissqnfixo.php usam a forma com chaves, igual nos dois runtimes (11 trocadas + 1 que ja era assim, por arquivo).
use PHPUnit\Framework\TestCase;

class VariavelVariavelMatrizTest extends TestCase
{
    public function testTrechoIsoladoCriaAVariavelDoNome()
    {
        $matriz = array('abc');
        $i = 0;
        ${$matriz[$i]} = 'X';
        $this->assertSame('X', $abc);
    }

    public function testCalculosUsamAFormaComChaves()
    {
        foreach (array('calculoiptu.php', 'calculoissqnfixo.php') as $arquivo) {
            $fonte = file_get_contents(__DIR__ . '/../../../' . $arquivo);
            $this->assertSame(0, substr_count($fonte, '$$matriz['), $arquivo);
            $this->assertSame(12, substr_count($fonte, '${$matriz[$i]}'), $arquivo);
        }
    }
}
