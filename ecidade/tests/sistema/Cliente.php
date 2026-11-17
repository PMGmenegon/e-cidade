<?php
/**
 * T-012: cliente HTTP da camada de sistema. Compativel com PHP 5.6 e 8.x.
 * Um "alvo" e a URL base de um runtime; os testes comparam os dois (5.6 x novo).
 * Hosts: SISTEMA_AGENTE=<nome> => http://ecidade_<nome>_56 e _85 (rede docker), ou SISTEMA_URL_56 / SISTEMA_URL_85.
 */
class SistemaCliente
{
    /** Token e sessoes pre-obtidos ficam FORA do docroot (nunca sob ecidade/), modo 0600. */
    public static function segredos()
    {
        return getenv('SISTEMA_SEGREDOS') ?: sys_get_temp_dir() . '/ecidade-sistema-segredos';
    }

    public static function alvos()
    {
        $u56 = getenv('SISTEMA_URL_56');
        $u85 = getenv('SISTEMA_URL_85');
        $agente = getenv('SISTEMA_AGENTE');
        if (!$agente && is_file(__DIR__ . '/.agente')) {
            $agente = trim(file_get_contents(__DIR__ . '/.agente'));
        }
        if ((!$u56 || !$u85) && $agente) {
            $u56 = $u56 ?: 'http://ecidade_' . strtolower($agente) . '_56';
            $u85 = $u85 ?: 'http://ecidade_' . strtolower($agente) . '_85';
        }
        return ($u56 && $u85) ? array('56' => rtrim($u56, '/'), '85' => rtrim($u85, '/')) : null;
    }

    /**
     * Alvo "novo" dos testes da API V1: o container proprio da API (SISTEMA_URL_API, ex.: o proxy com a regra /api/v1/)
     * ou, sem a variavel, o 8.5 de hoje.
     */
    public static function alvoApi(array $alvos)
    {
        $u = getenv('SISTEMA_URL_API');
        return $u ? rtrim($u, '/') : $alvos['85'];
    }

    /** @return array status, tipo, corpo, cookies */
    public static function requisita($base, $metodo, $caminho, array $opcoes = array())
    {
        $ch = curl_init($base . $caminho);
        $cab = isset($opcoes['cabecalhos']) ? $opcoes['cabecalhos'] : array();
        if (!empty($opcoes['token'])) {
            $cab[] = 'Authorization: Bearer ' . $opcoes['token'];
            $cab[] = 'Accept: application/json';
        }
        curl_setopt_array($ch, array(
            CURLOPT_CUSTOMREQUEST => $metodo,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER => true,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_TIMEOUT => 60,
            CURLOPT_HTTPHEADER => $cab,
        ));
        if (isset($opcoes['corpo'])) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $opcoes['corpo']);
        }
        if (!empty($opcoes['cookie'])) {
            curl_setopt($ch, CURLOPT_COOKIE, $opcoes['cookie']);
        }
        $r = curl_exec($ch);
        if ($r === false) {
            $erro = curl_error($ch);
            curl_close($ch);
            return array('status' => 0, 'tipo' => '', 'corpo' => $erro, 'cookies' => '', 'local' => '');
        }
        $tam = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        $cabecalho = substr($r, 0, $tam);
        $tipo = preg_match('/^Content-Type:\s*([^;\r\n]+)/mi', $cabecalho, $m) ? strtolower(trim($m[1])) : '';
        $local = preg_match('/^Location:\s*(\S+)/mi', $cabecalho, $m) ? $m[1] : '';
        preg_match_all('/^Set-Cookie:\s*([^=]+)=([^;\r\n]*)/mi', $cabecalho, $cs, PREG_SET_ORDER);
        $cookies = array();
        foreach ($cs as $c) {
            $cookies[trim($c[1])] = $c[2];
        }
        return array('status' => $status, 'tipo' => $tipo, 'corpo' => (string) substr($r, $tam), 'cookies' => $cookies, 'local' => $local);
    }

    /** Token Passport (password grant) do usuario de teste; credenciais lidas do config, nunca impressas. */
    public static function token($base, $novo = false)
    {
        // pre-obtido por prepara.php (bateria em containers SOMENTE_LEITURA=1, onde o login nao grava token)
        if (!$novo && getenv('SISTEMA_TOKEN')) {
            return getenv('SISTEMA_TOKEN');
        }
        if (!$novo && is_file(self::segredos() . '/token')) {
            return trim(file_get_contents(self::segredos() . '/token'));
        }
        $cred = json_decode((string) shell_exec('php ' . escapeshellarg(__DIR__ . '/credenciais.php') . ' 2>/dev/null'), true);
        if (!$cred) {
            return null;
        }
        $r = self::requisita($base, 'POST', '/v4/oauth/token', array('corpo' => http_build_query(array(
            'grant_type' => 'password', 'client_id' => $cred['id'], 'client_secret' => $cred['secret'],
            'username' => 'dbseller', 'password' => 'dbseller',
        ))));
        $j = json_decode($r['corpo'], true);
        return ($r['status'] == 200 && isset($j['access_token'])) ? $j['access_token'] : null;
    }

    /** Sessao legada (login.php + abrir.php, como o navegador); grava so o que o login grava. Devolve o cookie ou null. */
    public static function sessao($base)
    {
        $rt = substr($base, -2) === '85' ? '85' : '56';
        if (is_file(self::segredos() . '/sessao-' . $rt)) {
            return trim(file_get_contents(self::segredos() . '/sessao-' . $rt));
        }
        $tela = self::requisita($base, 'GET', '/login.php');
        if (empty($tela['cookies']['ECIDADEWINDOWMAIN'])) {
            return null;
        }
        $c = 'ECIDADEWINDOWMAIN=' . $tela['cookies']['ECIDADEWINDOWMAIN'];
        $r = self::requisita($base, 'POST', '/abrir.php', array(
            'corpo' => http_build_query(array('DB_login' => 'dbseller', 'DB_senha' => md5('dbseller'), 'conteudoCaptcha' => '')),
            'cookie' => $c,
        ));
        if (!preg_match('/inicio\.php\?uso=/', $r['corpo'])) {
            return null;
        }
        return isset($r['cookies']['ECIDADEWINDOWMAIN']) ? 'ECIDADEWINDOWMAIN=' . $r['cookies']['ECIDADEWINDOWMAIN'] : $c;
    }

    /** Resumo comparavel: status, tipo e conteudo normalizado (JSON decodificado ou HTML com espacos colapsados). */
    public static function resumo(array $r)
    {
        $corpo = $r['corpo'];
        $j = json_decode($corpo, true);
        if ($j !== null) {
            $corpo = json_encode(self::semVolateis($j));
        } else {
            $corpo = preg_replace('/\s+/', ' ', preg_replace('/sid=[0-9a-f]{32}/', 'sid=X', $corpo));
        }
        return $r['status'] . ' ' . $r['tipo'] . ' ' . substr(md5($corpo), 0, 12);
    }

    private static function semVolateis($v)
    {
        if (!is_array($v)) {
            return $v;
        }
        $o = array();
        foreach ($v as $k => $x) {
            if (in_array($k, array('access_token', 'refresh_token', 'expires_in', 'trace', 'stacktrace', 'file', 'line'), true)) {
                continue;
            }
            $o[$k] = self::semVolateis($x);
        }
        return $o;
    }

    /** Rotas GET sem escrita aparente. Devolve array(testaveis, puladas[uri => motivo]). */
    public static function rotasGet($arquivo, $prefixo)
    {
        $nego = '/(processar|exclu|delet|gerar|salvar|encerr|inativar|importar|enviar|atualiz|cancel|baixa|assin|migr|reprocess)/i';
        $ok = array();
        $puladas = array();
        $fora = array();
        $arqFora = __DIR__ . '/dados/get-fora-da-cobertura.tsv';
        if (is_file($arqFora)) {
            foreach (file($arqFora, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) {
                $c = explode("\t", $l);
                if ($c[0][0] !== '#' && isset($c[1])) {
                    $fora[$c[0]] = $c[1];
                }
            }
        }
        foreach (file($arquivo, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) {
            $c = explode("\t", $l);
            if ($c[0] !== 'GET' || strpos($c[1], $prefixo) !== 0) {
                continue;
            }
            if (preg_match($nego, $c[1])) {
                $puladas[$c[1]] = 'nome sugere escrita/efeito colateral';
                continue;
            }
            if (isset($fora[$c[1]])) {
                $puladas[$c[1]] = $fora[$c[1]];
                continue;
            }
            $ok[$c[1]] = preg_replace(array('#/\{[^}]*\?\}#', '#\{[^}]*\}#'), array('', '1'), $c[1]);
        }
        return array($ok, $puladas);
    }
}
