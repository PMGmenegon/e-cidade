<?php
// T-027: DBLargeObject::leitura() com OID invalido devolve false como o PHP 5.6 (no 8.x o pg_lo_export lanca ValueError).
// So le do banco (begin/rollback e a leitura de um large object existente); nao grava nada.
// Uma transacao por OID: no 5.6 o pg_lo_export que falha aborta a transacao.
// Sem setUp()/tearDown(): o PHPUnit 9 exige ': void', que nao compila no 5.6.
use PHPUnit\Framework\TestCase;

class DBLargeObjectLeituraTest extends TestCase
{
    public function testOidInvalidoDevolveFalse()
    {
        $destino = $this->destino();
        foreach (array(0, null, -1, 'abc', '12x', '00') as $oid) {
            $this->emTransacao(function () use ($oid, $destino) {
                $this->assertFalse(DBLargeObject::leitura($oid, $destino), 'OID ' . var_export($oid, true));
            });
        }
        $this->assertFalse(file_exists($destino));
    }

    public function testOidVazioOuInexistenteDevolveFalse()
    {
        $destino = $this->destino();
        foreach (array('', '999999999') as $oid) {
            $this->emTransacao(function () use ($oid, $destino) {
                $this->assertFalse(@DBLargeObject::leitura($oid, $destino), 'OID ' . var_export($oid, true));
            });
        }
    }

    public function testOidValidoContinuaExportando()
    {
        $this->assertExporta(function ($oid) { return $oid; });
    }

    // O 5.6 aceita o OID com espaco antes, com '+' e com espaco depois; a guarda so troca o ValueError por false.
    public function testOidQueOCincoSeisAceitaContinuaExportando()
    {
        $this->assertExporta(function ($oid) { return ' ' . $oid; });
        $this->assertExporta(function ($oid) { return '+' . $oid; });
        $this->assertExporta(function ($oid) { return $oid . ' '; });
        $this->assertExporta(function ($oid) { return (int) $oid; });
    }

    private function assertExporta($forma)
    {
        $destino = $this->destino();
        $this->emTransacao(function () use ($forma, $destino) {
            global $conn;
            $oid = pg_fetch_result(pg_query($conn, 'select min(oid) from pg_largeobject_metadata'), 0, 0);
            if (!$oid) {
                $this->markTestSkipped('banco sem large object para ler');
            }
            $this->assertTrue(DBLargeObject::leitura($forma($oid), $destino));
            $this->assertTrue(file_exists($destino));
        });
        if (file_exists($destino)) {
            unlink($destino);
        }
    }

    private function destino()
    {
        $destino = tempnam(sys_get_temp_dir(), 'lo027');
        unlink($destino);
        return $destino;
    }

    private function emTransacao($corpo)
    {
        global $conn;
        if (!getenv('DB_HOST')) {
            $this->markTestSkipped('DB_HOST ausente: runtime sem acesso ao banco');
        }
        require_once __DIR__ . '/../../../libs/db_utils.php';
        require_once __DIR__ . '/../../../std/DBLargeObject.php';
        $conn = pg_connect('host=' . getenv('DB_HOST') . ' port=' . (getenv('DB_PORT') ?: '5432')
            . ' dbname=' . getenv('DB_DATABASE') . ' user=' . getenv('DB_USERNAME') . ' password=' . getenv('DB_PASSWORD'));
        pg_query($conn, 'begin');
        try {
            $corpo();
        } finally {
            pg_query($conn, 'rollback');
        }
    }
}
