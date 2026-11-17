<?php
// Camada sistema: POST da API V1 (Silex) em /tributario/recibo e /matriculaonline/inscricao, SO caminhos de erro que nao gravam.
// Todos param antes do PersistUserDataServiceProvider (ApiClienteRepository::save grava db172_ultima_utilizacao), no AuthMiddleware:
// sem id/hash, id nao numerico, cliente inexistente e hash que nao decifra com a chave do cliente existente.
// O caminho de sucesso grava (cliente da API, recibo, inscricao) e fica como lacuna; ver docs/registro/testes-sistema-api-v1-post.md.
use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/Cliente.php';

class SistemaApiV1PostTest extends TestCase
{
    private $alvos;

    private function prepara()
    {
        $this->alvos = SistemaCliente::alvos();
        if (!$this->alvos) {
            $this->markTestSkipped('defina SISTEMA_AGENTE (ou SISTEMA_URL_56 e SISTEMA_URL_85)');
        }
    }

    /** Codigo de um cliente da API ja cadastrado (so leitura do codigo; a chave nunca e lida). */
    private function idClienteExistente()
    {
        if (getenv('SISTEMA_API_CLIENTE_ID')) {
            return getenv('SISTEMA_API_CLIENTE_ID');
        }
        if (!function_exists('pg_connect') || !getenv('DB_HOST')) {
            return null;
        }
        $c = @pg_connect('host=' . getenv('DB_HOST') . ' port=' . (getenv('DB_PORT') ?: 5432) . ' dbname=' . getenv('DB_DATABASE')
            . ' user=' . getenv('DB_USERNAME') . ' password=' . getenv('DB_PASSWORD'));
        $r = $c ? @pg_query($c, 'select min(db172_sequencial) from configuracoes.api_clients') : false;
        $v = $r ? pg_fetch_row($r) : null;
        return ($v && $v[0] !== null) ? $v[0] : null;
    }

    private function casos()
    {
        $form = array('Content-Type: application/x-www-form-urlencoded');
        $json = array('Content-Type: application/json');
        $casos = array(
            'corpo vazio' => array(null, array()),
            'json vazio' => array('{}', $json),
            'json invalido' => array('{', $json),
            'so id, sem hash' => array('id=1', $form),
            'so hash, sem id' => array('hash=abc', $form),
            'id nao numerico' => array('id=abc&hash=abc', $form),
            'cliente inexistente' => array('id=2147483647&hash=abc', $form),
        );
        $id = $this->idClienteExistente();
        if ($id !== null) {
            $casos['hash invalido, cliente existente'] = array('id=' . $id . '&hash=' . str_repeat('A', 24), $form);
        }
        return $casos;
    }

    private function detalhe(array $r)
    {
        $j = json_decode($r['corpo'], true);
        $msg = is_array($j) && isset($j['message']) ? ' msg=' . (is_scalar($j['message']) ? $j['message'] : json_encode($j['message'])) : '';
        $cod = is_array($j) && isset($j['statusCode']) ? ' statusCode=' . (is_scalar($j['statusCode']) ? $j['statusCode'] : json_encode($j['statusCode'])) : '';
        return $r['status'] . ' ' . $r['tipo'] . $cod . $msg;
    }

    public function testPostErrosDaApiV1IguaisNosDoisRuntimes()
    {
        $this->prepara();
        $rotas = array('/api/v1/tributario/recibo', '/api/v1/matriculaonline/inscricao');
        $dif = array();
        $rel = array();
        foreach ($rotas as $rota) {
            foreach ($this->casos() as $nome => $c) {
                $op = array('cabecalhos' => $c[1]);
                if ($c[0] !== null) {
                    $op['corpo'] = $c[0];
                }
                $r56 = SistemaCliente::requisita($this->alvos['56'], 'POST', $rota, $op);
                $r85 = SistemaCliente::requisita(SistemaCliente::alvoApi($this->alvos), 'POST', $rota, $op);
                $a = SistemaCliente::resumo($r56);
                $b = SistemaCliente::resumo($r85);
                $rel[] = $rota . "\t" . $nome . "\t" . $this->detalhe($r56) . "\t" . $a . "\t" . $b . "\t" . ($a === $b ? 'igual' : 'DIFERENTE');
                if ($a !== $b) {
                    $dif[] = $rota . ' [' . $nome . '] 5.6=[' . $a . '] novo=[' . $b . ']';
                }
                $this->assertNotSame(0, $r56['status'], 'sem resposta do 5.6 em ' . $rota . ' [' . $nome . ']');
                $this->assertNotSame(0, $r85['status'], 'sem resposta do novo em ' . $rota . ' [' . $nome . ']');
            }
        }
        $dir = __DIR__ . '/../suite/relatorios';
        if (is_dir($dir) && is_writable($dir)) {
            file_put_contents($dir . '/sistema-api-v1-post.tsv', "rota\tcaso\t5.6 (status, tipo, mensagem)\tresumo 5.6\tresumo novo\tresultado\n" . implode("\n", $rel) . "\n");
        }
        $this->assertSame(array(), $dif, count($dif) . " casos POST da API V1 diferem entre 5.6 e o novo:\n" . implode("\n", $dif));
    }
}
