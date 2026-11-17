<?php
// T-012: roteiro do login 5.6 x novo (login legado, regra 3): tela, token Passport, abrir.php, inicio.php, senha errada.
// O que o sistema grava ao logar (db_logsacessa, oauth_access_tokens, sessao) e permitido; nada alem disso.
// Regra 3 do cliente (13/11): o login fica IGUAL ao legado; este roteiro compara o comportamento atual, sem bateria de seguranca.
use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/Cliente.php';

class SistemaLoginTest extends TestCase
{
    private $alvos;

    private function prepara()
    {
        $this->alvos = SistemaCliente::alvos();
        if (!$this->alvos) {
            $this->markTestSkipped('defina SISTEMA_AGENTE (ou SISTEMA_URL_56 e SISTEMA_URL_85)');
        }
    }

    private function roteiro($base)
    {
        $res = array();
        $tela = SistemaCliente::requisita($base, 'GET', '/login.php');
        $res['tela de login'] = SistemaCliente::resumo($tela);
        $sid = isset($tela['cookies']['ECIDADEWINDOWMAIN']) ? $tela['cookies']['ECIDADEWINDOWMAIN'] : '';
        $res['cookie de sessao'] = $sid !== '' ? 'sim' : 'nao';

        $tok = SistemaCliente::requisita($base, 'POST', '/v4/oauth/token', array('corpo' => 'grant_type=password'));
        $res['token sem credenciais'] = $tok['status'] . ' ' . $tok['tipo'];

        $ok = SistemaCliente::requisita($base, 'POST', '/abrir.php', array(
            'corpo' => http_build_query(array('DB_login' => 'dbseller', 'DB_senha' => md5('dbseller'), 'conteudoCaptcha' => '')),
            'cookie' => 'ECIDADEWINDOWMAIN=' . $sid,
        ));
        $res['abrir.php senha certa'] = $ok['status'] . ' ' . (preg_match('/inicio\.php\?uso=/', $ok['corpo']) ? 'entra' : 'nao entra');

        $cs = isset($ok['cookies']['ECIDADEWINDOWMAIN']) ? $ok['cookies']['ECIDADEWINDOWMAIN'] : $sid;
        $ini = SistemaCliente::requisita($base, 'GET', '/inicio.php', array('cookie' => 'ECIDADEWINDOWMAIN=' . $cs));
        $res['inicio.php com a sessao'] = $ini['status'] . ' ' . $ini['tipo'] . ' ' . ($ini['local'] !== '' ? 'redireciona' : 'sem redirecionamento');

        $erro = SistemaCliente::requisita($base, 'POST', '/abrir.php', array(
            'corpo' => http_build_query(array('DB_login' => 'dbseller', 'DB_senha' => md5('errada'))),
            'cookie' => 'ECIDADEWINDOWMAIN=' . $sid,
        ));
        $res['abrir.php senha errada'] = $erro['status'] . ' ' . (preg_match('/inicio\.php\?uso=/', $erro['corpo']) ? 'entra' : 'nao entra');
        return $res;
    }

    public function testRoteiroDoLoginIgualNosDoisRuntimes()
    {
        $this->prepara();
        $r56 = $this->roteiro($this->alvos['56']);
        $r85 = $this->roteiro($this->alvos['85']);
        $dif = array();
        foreach ($r56 as $passo => $v) {
            if ($v !== $r85[$passo]) {
                $dif[] = $passo . ': 5.6=[' . $v . '] novo=[' . $r85[$passo] . ']';
            }
        }
        $this->assertSame(array(), $dif, "login difere entre 5.6 e o novo:\n" . implode("\n", $dif));
    }

    public function testTokenPassportEmitidoNoNovo()
    {
        $this->prepara();
        $this->assertNotNull(SistemaCliente::token($this->alvos['56'], true), 'baseline: o 5.6 emite token');
        $this->assertNotNull(SistemaCliente::token($this->alvos['85'], true), 'o runtime novo nao emite token (linha de base de hoje: /v4/oauth/token = 500)');
    }
}
