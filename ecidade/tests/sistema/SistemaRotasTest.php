<?php
// T-012: camada sistema - rotas /v4 (Laravel) e API V1 (Silex) comparadas 5.6 x novo, com token valido.
// Roda nos dois runtimes (PHPUnit 5.7 e 12). So GET sem efeito colateral aparente; as demais ficam em dados/nao-cobertas.tsv.
use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/Cliente.php';

class SistemaRotasTest extends TestCase
{
    private $alvos;

    private function prepara()
    {
        $this->alvos = SistemaCliente::alvos();
        if (!$this->alvos) {
            $this->markTestSkipped('defina SISTEMA_AGENTE (ou SISTEMA_URL_56 e SISTEMA_URL_85)');
        }
    }

    private function compara($arquivo, $prefixo, $nomeRelatorio, $comSessao = false)
    {
        list($rotas, $puladas) = SistemaCliente::rotasGet(__DIR__ . '/dados/' . $arquivo, $prefixo);
        $this->assertNotEmpty($rotas, 'lista de rotas vazia: ' . $arquivo);
        // token valido: pedido ao 5.6 (unico que emite hoje) e usado nos dois, o banco e a chave sao compartilhados
        $token = SistemaCliente::token($this->alvos['56']);
        $this->assertNotNull($token, 'sem token valido no 5.6 (POST /v4/oauth/token)');
        $ck = array('56' => null, '85' => null);
        if ($comSessao) {
            foreach ($ck as $k => $_) {
                $ck[$k] = SistemaCliente::sessao($this->alvos[$k]);
            }
        }
        $novo = $prefixo === '/api/v1/' ? SistemaCliente::alvoApi($this->alvos) : $this->alvos['85'];
        $dif = array();
        $rel = array();
        foreach ($rotas as $modelo => $uri) {
            $r56 = SistemaCliente::resumo(SistemaCliente::requisita($this->alvos['56'], 'GET', $uri, array('token' => $token, 'cookie' => $ck['56'])));
            $r85 = SistemaCliente::resumo(SistemaCliente::requisita($novo, 'GET', $uri, array('token' => $token, 'cookie' => $ck['85'])));
            $rel[] = $modelo . "\t" . $r56 . "\t" . $r85 . "\t" . ($r56 === $r85 ? 'igual' : 'DIFERENTE');
            if ($r56 !== $r85) {
                $dif[] = $modelo . '  5.6=[' . $r56 . ']  8.5=[' . $r85 . ']';
            }
        }
        foreach ($puladas as $u => $m) {
            $rel[] = $u . "\t-\t-\tnao coberta: " . $m;
        }
        $dir = __DIR__ . '/../suite/relatorios';
        if (is_dir($dir) && is_writable($dir)) {
            file_put_contents($dir . '/' . $nomeRelatorio . '.tsv', "rota\t5.6\t8.5\tresultado\n" . implode("\n", $rel) . "\n");
        }
        $this->assertSame(array(), $dif, count($dif) . ' de ' . count($rotas) . " rotas diferem entre 5.6 e o novo:\n" . implode("\n", array_slice($dif, 0, 15)));
    }

    public function testRotasLaravelV4IguaisNosDoisRuntimes()
    {
        $this->prepara();
        $this->compara('rotas-v4.tsv', '/v4/', 'sistema-rotas-v4');
    }

    public function testRotasRestV1IguaisNosDoisRuntimes()
    {
        $this->prepara();
        $this->compara('rotas-v4.tsv', '/rest/v1/', 'sistema-rotas-rest-v1');
    }

    public function testRotasApiV1SilexIguaisNosDoisRuntimes()
    {
        $this->prepara();
        $this->compara('rotas-api-v1.tsv', '/api/v1/', 'sistema-rotas-api-v1', true);
    }
}
