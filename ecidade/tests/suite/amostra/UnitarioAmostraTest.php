<?php
// Amostra da camada unitaria. Escrita para rodar igual em PHPUnit 5.7 (PHP 5.6) e 12 (PHP 8.5):
// classe base com namespace, sem setUp() tipado, sem anotacoes de metadados.
use PHPUnit\Framework\TestCase;

class UnitarioAmostraTest extends TestCase
{
    public function testSomaDeInteiros()
    {
        $this->assertSame(4, 2 + 2);
    }

    public function testZeroNaoEhStringVazia()
    {
        // 5.6 e 8.x discordam em "0 == ''"; a comparacao estrita e a mesma nos dois.
        $this->assertFalse(0 === '');
    }
}
