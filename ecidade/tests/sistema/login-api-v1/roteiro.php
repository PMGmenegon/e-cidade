<?php
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; } // so linha de comando
// Linha de base do login da API V1 (POST /api/v1/auth/login) com entradas invalidas e incompletas.
// Roda DENTRO do container do runtime (PHP 5.6 ou 8.x): php tests/sistema/login-api-v1/roteiro.php <url-base> <pasta-saida>
// Um arquivo .out por caso (status, tipo, nomes de cookie, Location, corpo normalizado) + resumo.tsv.
// Usa o cliente HTTP da camada de sistema (../Cliente.php). So documenta o comportamento atual; nada e corrigido.
//
// SEGREDO: id e chave do cliente da API sao lidos do banco aqui, so em memoria, para montar o hash dos casos A05/A14/A15
// (AES, como o HashGenerator). Nunca sao impressos nem gravados.
// SO CASOS QUE NAO GRAVAM: com cliente valido o sistema grava configuracoes.api_clients.db172_ultima_utilizacao e a trilha de
// auditoria db_acount* (medido: docs/registro/testes-login-api-v1.md), entao esses casos nao fazem parte deste roteiro.
// O A15 (hash com time antigo) so e enviado se ja houver uma ultima utilizacao gravada; sem ela o sistema o aceitaria e gravaria.
require __DIR__ . '/../Cliente.php';

$base = isset($argv[1]) ? rtrim($argv[1], '/') : null;
$saida = isset($argv[2]) ? rtrim($argv[2], '/') : null;
if (!$base || !$saida) { fwrite(STDERR, "uso: php roteiro.php <url-base> <pasta-saida>\n"); exit(2); }
if (!is_dir($saida)) { mkdir($saida, 0755, true); }

const ROTA = '/api/v1/auth/login';
const ALG = 'aes-256-cfb';
const IV = 'ECI-CRYP-999-666';

$pg = pg_connect('host=' . getenv('DB_HOST') . ' port=' . (getenv('DB_PORT') ?: '5432') . ' dbname=' . getenv('DB_DATABASE')
    . ' user=' . getenv('DB_USERNAME') . ' password=' . getenv('DB_PASSWORD'));
$r = $pg ? pg_query($pg, 'select db172_sequencial, db172_chave from configuracoes.api_clients order by 1 limit 1') : false;
$cli = $r ? pg_fetch_row($r) : false;
if (!$cli) { fwrite(STDERR, "sem cliente da API no banco\n"); exit(2); }
$clienteId = $cli[0];
$chave = $cli[1];

function hashCliente($dados, $chave) { return openssl_encrypt(json_encode($dados), ALG, $chave, 0, IV); }

/**
 * Caso: id, categoria, descricao, e a requisicao.
 * 'cv' = 'sem-time' / 'replay': hash valido, mas sem 'time' / com 'time' antigo (rejeitado antes de gravar).
 * 'cv' = 'hash-ruim': id existente com hash invalido.
 */
$casos = array();
function caso($id, $origem, $desc, $extra = array())
{
    global $casos;
    $casos[] = array_merge(array('id' => $id, 'origem' => $origem, 'desc' => $desc, 'metodo' => 'POST', 'campos' => array(),
        'cv' => false, 'cab' => array(), 'cookie' => '', 'corpo' => null, 'tipo' => null, 'caminho' => ROTA), $extra);
}

// --- Casos sem cliente valido (nao gravam) ---
caso('A01', 'entrada', 'POST sem corpo');
caso('A02', 'entrada', 'user e password sem id/hash', array('campos' => array('user' => 'dbseller', 'password' => 'dbseller')));
caso('A03', 'entrada', 'id nao numerico', array('campos' => array('id' => 'abc', 'hash' => 'x', 'user' => 'dbseller', 'password' => 'dbseller')));
caso('A04', 'entrada', 'id numerico inexistente', array('campos' => array('id' => '999999', 'hash' => 'x', 'user' => 'dbseller', 'password' => 'dbseller')));
caso('A05', 'hash', 'id existente com hash invalido', array('cv' => 'hash-ruim', 'campos' => array('user' => 'dbseller', 'password' => 'dbseller')));
caso('A06', 'metodo', 'GET (metodo errado)', array('metodo' => 'GET'));
caso('A07', 'metodo', 'PUT (metodo errado)', array('metodo' => 'PUT', 'campos' => array('user' => 'dbseller', 'password' => 'dbseller')));
caso('A08', 'metodo', 'GET com user/password na query', array('metodo' => 'GET', 'caminho' => ROTA . '?user=dbseller&password=dbseller'));
caso('A09', 'entrada', 'corpo JSON (Content-Type application/json)', array('tipo' => 'application/json', 'corpo' => '{"user":"dbseller","password":"dbseller"}'));
caso('A10', 'entrada', 'id como array (id[]=1)', array('corpo' => 'id[]=1&hash=x&user=dbseller&password=dbseller', 'tipo' => 'application/x-www-form-urlencoded'));
caso('A11', 'entrada', 'entrada longa (1 MB) sem cliente valido', array('campos' => array('user' => str_repeat('A', 1048576), 'password' => 'x')));
caso('A12', 'cabecalho', "X-Forwarded-For com aspa, sem cliente valido", array('cab' => array("X-Forwarded-For: 10.0.0.1'"), 'campos' => array('user' => 'dbseller', 'password' => 'dbseller')));
caso('A13', 'cookie', 'cookie de sessao ja existente, sem cliente valido', array('cookie' => 'ECIDADEWINDOWMAIN=cookieexistente123', 'campos' => array('user' => 'dbseller', 'password' => 'dbseller')));
caso('A14', 'hash', 'hash valido sem o campo time', array('cv' => 'sem-time', 'campos' => array('user' => 'dbseller', 'password' => 'dbseller')));
caso('A15', 'hash', 'hash valido com time antigo', array('cv' => 'replay', 'campos' => array('user' => 'dbseller', 'password' => 'dbseller')));

function normaliza($r, $chave)
{
    $c = $r['corpo'];
    $j = json_decode($c, true);
    if (is_array($j)) {
        if (isset($j['stacktrace'])) { $j['stacktrace'] = '<stacktrace omitido>'; }
        return json_encode($j);
    }
    $t = trim($c);
    if ($t !== '' && preg_match('/^[A-Za-z0-9+\/=]{16,}$/', $t)) {
        $d = json_decode((string) openssl_decrypt($t, ALG, $chave, 0, IV), true);
        return '<hash cifrado len=' . strlen($t) . ' idUsuario=' . (is_array($d) && isset($d['idUsuario']) ? $d['idUsuario'] : '?') . '>';
    }
    $t = preg_replace('/\s+/', ' ', preg_replace('/sid=[0-9a-f]{32}/', 'sid=X', $t));
    return 'len=' . strlen($c) . ' md5=' . substr(md5($t), 0, 12) . ' ' . substr($t, 0, 300);
}

$resumo = array();
foreach ($casos as $k) {
    $campos = $k['campos'];
    $corpo = $k['corpo'];
    $tipo = $k['tipo'];
    if ($k['cv'] !== false) {
        $dados = array('time' => time());
        if ($k['cv'] === 'sem-time') { $dados = array('x' => 1); }
        if ($k['cv'] === 'replay') {
            // so e rejeitado se ja houver ultima utilizacao maior que o time antigo; senao o sistema aceitaria e GRAVARIA
            $u = pg_fetch_row(pg_query($pg, 'select extract(epoch from db172_ultima_utilizacao) from configuracoes.api_clients where db172_sequencial = ' . (int) $clienteId));
            if (empty($u[0]) || $u[0] <= 1000000000) {
                file_put_contents($saida . '/' . $k['id'] . '.out', '# ' . $k['id'] . ' [' . $k['origem'] . '] ' . $k['desc'] . "\nPULADO: sem ultima utilizacao gravada, o caso gravaria\n");
                $resumo[] = $k['id'] . "\t-\t-\t" . $k['origem'] . "\t" . $k['desc'] . ' (PULADO)';
                continue;
            }
            $dados = array('time' => 1000000000);
        }
        $hash = $k['cv'] === 'hash-ruim' ? 'hash-invalido' : hashCliente($dados, $chave);
        $auth = array('id' => $clienteId, 'hash' => $hash);
        if ($corpo !== null) { $corpo = http_build_query($auth) . '&' . $corpo; } else { $campos = array_merge($auth, $campos); }
    }
    $op = array('cabecalhos' => $k['cab']);
    if ($k['cookie'] !== '') { $op['cookie'] = $k['cookie']; }
    if ($k['metodo'] !== 'GET') {
        $op['corpo'] = $corpo !== null ? $corpo : http_build_query($campos);
        if ($tipo !== null) { $op['cabecalhos'][] = 'Content-Type: ' . $tipo; }
    }
    $r = SistemaCliente::requisita($base, $k['metodo'], $k['caminho'], $op);
    $cookies = empty($r['cookies']) ? '(nenhum)' : implode(',', array_keys($r['cookies']));
    $plantado = (!empty($r['cookies']['ECIDADEWINDOWMAIN']) && $r['cookies']['ECIDADEWINDOWMAIN'] === 'cookieexistente123') ? ' (valor enviado mantido)' : '';
    $txt = '# ' . $k['id'] . ' [' . $k['origem'] . '] ' . $k['desc'] . "\n"
        . 'status: ' . $r['status'] . "\n"
        . 'tipo: ' . ($r['tipo'] !== '' ? $r['tipo'] : '(nenhum)') . "\n"
        . 'set-cookie: ' . $cookies . $plantado . "\n"
        . 'location: ' . ($r['local'] !== '' ? $r['local'] : '(nenhum)') . "\n"
        . 'corpo: ' . normaliza($r, $chave) . "\n";
    file_put_contents($saida . '/' . $k['id'] . '.out', $txt);
    $resumo[] = $k['id'] . "\t" . $r['status'] . "\t" . ($r['tipo'] !== '' ? $r['tipo'] : '-') . "\t" . $k['origem'] . "\t" . $k['desc'];
}
file_put_contents($saida . '/resumo.tsv', "caso\tstatus\ttipo\torigem\tdescricao\n" . implode("\n", $resumo) . "\n");
echo count($resumo) . " casos\n";
