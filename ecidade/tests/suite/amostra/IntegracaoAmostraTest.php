<?php
// Amostra da camada de integracao: autoload do composer + leitura no banco (so SELECT).
use PHPUnit\Framework\TestCase;

class IntegracaoAmostraTest extends TestCase
{
    public function testAutoloadDoComposerCarrega()
    {
        $this->assertTrue(class_exists('Composer\Autoload\ClassLoader'));
    }

    public function testBancoResponde()
    {
        if (!getenv('DB_HOST')) {
            $this->markTestSkipped('DB_HOST ausente: runtime sem acesso ao banco');
        }
        $dsn = 'pgsql:host=' . getenv('DB_HOST') . ';port=' . (getenv('DB_PORT') ?: '5432')
             . ';dbname=' . getenv('DB_DATABASE');
        $pdo = new PDO($dsn, getenv('DB_USERNAME'), getenv('DB_PASSWORD'));
        $this->assertSame('1', (string) $pdo->query('SELECT 1')->fetchColumn());
    }
}
