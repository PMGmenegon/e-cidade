<?php
// Camada sistema: login da API V1 (POST /api/v1/auth/login), grupo A = 15 casos SEM cliente valido (nao gravam).
// Roda o roteiro de login-api-v1/roteiro.php contra o 5.6 e contra o alvo novo (container da API V1 ou 8.5 de hoje, ver
// SistemaCliente::alvoApi) e compara os 15 arquivos de resultado entre si e com a linha de base do 5.6 versionada em
// login-api-v1/base-5.6/. Casos com cliente valido gravam api_clients e a trilha db_acount*: ficam como lacuna.
use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/Cliente.php';

class SistemaLoginApiV1Test extends TestCase
{
    private $alvos;

    private function prepara()
    {
        $this->alvos = SistemaCliente::alvos();
        if (!$this->alvos) {
            $this->markTestSkipped('defina SISTEMA_AGENTE (ou SISTEMA_URL_56 e SISTEMA_URL_85)');
        }
        if (!getenv('DB_HOST')) {
            $this->markTestSkipped('o roteiro monta os hashes dos casos com o cliente da API lido do banco: precisa de DB_HOST/DB_* (rodar no container)');
        }
    }

    private function rodada($base)
    {
        $dir = sys_get_temp_dir() . '/login-api-v1-' . getmypid() . '-' . md5($base);
        shell_exec('rm -rf ' . escapeshellarg($dir));
        $saida = shell_exec(escapeshellarg(PHP_BINARY) . ' ' . escapeshellarg(__DIR__ . '/login-api-v1/roteiro.php') . ' '
            . escapeshellarg($base) . ' ' . escapeshellarg($dir) . ' 2>&1');
        $this->assertTrue(strpos((string) $saida, 'casos') !== false, 'roteiro nao terminou: ' . substr((string) $saida, 0, 200));
        $res = array();
        foreach (glob($dir . '/*.out') as $f) {
            $res[basename($f)] = file_get_contents($f);
        }
        shell_exec('rm -rf ' . escapeshellarg($dir));
        return $res;
    }

    private function diferencas(array $a, array $b)
    {
        $dif = array();
        foreach (array_unique(array_merge(array_keys($a), array_keys($b))) as $k) {
            if (!isset($a[$k]) || !isset($b[$k]) || $a[$k] !== $b[$k]) {
                $dif[] = basename($k, '.out');
            }
        }
        return $dif;
    }

    public function testLoginGrupoAIgualNosDoisRuntimesEABaseVersionada()
    {
        $this->prepara();
        $r56 = $this->rodada($this->alvos['56']);
        $novo = $this->rodada(SistemaCliente::alvoApi($this->alvos));
        $base = array();
        foreach (glob(__DIR__ . '/login-api-v1/base-5.6/*.out') as $f) {
            $base[basename($f)] = file_get_contents($f);
        }
        $this->assertCount(15, $base, 'linha de base versionada: 15 casos');
        $this->assertSame(array(), $this->diferencas($base, $r56), 'o 5.6 de hoje difere da linha de base versionada');
        $dif = $this->diferencas($r56, $novo);
        $this->assertSame(array(), $dif, count($dif) . ' de 15 casos do login da API V1 diferem entre 5.6 e o novo: ' . implode(', ', $dif));
    }
}
