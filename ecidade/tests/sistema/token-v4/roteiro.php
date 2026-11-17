<?php
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; } // so linha de comando
// Linha de base do token /v4 (Passport): emissao em /v4/oauth/token, uso do token numa rota protegida e casos de borda.
// Roda DENTRO do container do runtime: php tests/sistema/token-v4/roteiro.php <url-base> <pasta-saida> [arquivo-do-token-anterior]
// Um .out por caso + resumo.tsv. Usa o cliente HTTP da camada de sistema (../Cliente.php). So documenta o comportamento atual.
//
// SEGREDO: id/secret do cliente OAuth vem de ../credenciais.php (nunca impressos); tokens e CPF ficam so em memoria
// (o token valido e gravado em /tmp do container, modo 0600, para a rodada seguinte; nunca vai para a pasta de saida).
// GRAVACAO: emitir token grava oauth_access_tokens/oauth_refresh_tokens (permitido); nada alem disso deve mudar (o vigia confere).
require __DIR__ . '/../Cliente.php';

$base = isset($argv[1]) ? rtrim($argv[1], '/') : null;
$saida = isset($argv[2]) ? rtrim($argv[2], '/') : null;
$arqAnterior = isset($argv[3]) ? $argv[3] : null;
if (!$base || !$saida) { fwrite(STDERR, "uso: php roteiro.php <url-base> <pasta-saida> [arquivo-do-token-anterior]\n"); exit(2); }
if (!is_dir($saida)) { mkdir($saida, 0755, true); }

const ROTA_USO = '/v4/api/educacao/escola/vacinas';
$cred = json_decode((string) shell_exec('php ' . escapeshellarg(__DIR__ . '/../credenciais.php') . ' 2>/dev/null'), true);
if (!$cred) { fwrite(STDERR, "sem credenciais do cliente OAuth\n"); exit(2); }

function emite($base, $cred, array $troca = array(), $metodo = 'POST', $corpoBruto = null, $tipo = null)
{
    $campos = array_merge(array('grant_type' => 'password', 'client_id' => $cred['id'], 'client_secret' => $cred['secret'],
        'username' => 'dbseller', 'password' => 'dbseller'), $troca);
    foreach ($campos as $k => $v) { if ($v === null) { unset($campos[$k]); } }
    $op = array('corpo' => $corpoBruto !== null ? $corpoBruto : http_build_query($campos), 'cabecalhos' => array('Accept: application/json'));
    if ($tipo) { $op['cabecalhos'][] = 'Content-Type: ' . $tipo; }
    return SistemaCliente::requisita($base, $metodo, '/v4/oauth/token', $op);
}

function jwtPartes($t) { return $t ? explode('.', $t) : array(); }

function normaliza($r, $segredos)
{
    $c = $r['corpo'];
    foreach ($segredos as $s) { if ($s !== '' && $s !== null) { $c = str_replace($s, '<segredo>', $c); } }
    $j = json_decode($c, true);
    if (is_array($j)) {
        foreach (array('access_token', 'refresh_token') as $k) {
            if (isset($j[$k])) { $j[$k] = '<' . $k . ' len=' . strlen($j[$k]) . '>'; }
        }
        // expires_in = validade restante em segundos (31536000 menos o atraso entre emitir e responder): varia de 1 s entre rodadas
        if (isset($j['expires_in']) && is_int($j['expires_in']) && $j['expires_in'] >= 31535900 && $j['expires_in'] <= 31536000) { $j['expires_in'] = '<~1 ano>'; }
        foreach (array('trace', 'stacktrace', 'file', 'line') as $k) { if (isset($j[$k])) { $j[$k] = '<omitido>'; } }
        return json_encode($j);
    }
    $t = preg_replace('/\s+/', ' ', trim($c));
    return 'len=' . strlen($c) . ' md5=' . substr(md5($t), 0, 12) . ' ' . substr($t, 0, 200);
}

$resumo = array();
$segredos = array($cred['secret']);
function grava($saida, &$resumo, $id, $desc, $r, $segredos)
{
    $cookies = empty($r['cookies']) ? '(nenhum)' : implode(',', array_keys($r['cookies']));
    $txt = '# ' . $id . ' ' . $desc . "\n"
        . 'status: ' . $r['status'] . "\n"
        . 'tipo: ' . ($r['tipo'] !== '' ? $r['tipo'] : '(nenhum)') . "\n"
        . 'set-cookie: ' . $cookies . "\n"
        . 'corpo: ' . normaliza($r, $segredos) . "\n";
    file_put_contents($saida . '/' . $id . '.out', $txt);
    $resumo[] = $id . "\t" . $r['status'] . "\t" . ($r['tipo'] !== '' ? $r['tipo'] : '-') . "\t" . $desc;
}
function uso($base, $token, $cabecalho = null)
{
    $op = array('cabecalhos' => array('Accept: application/json'));
    if ($cabecalho !== null) { $op['cabecalhos'][] = $cabecalho; } elseif ($token !== null) { $op['cabecalhos'][] = 'Authorization: Bearer ' . $token; }
    return SistemaCliente::requisita($base, 'GET', ROTA_USO, $op);
}
function troca1($s)  // troca 1 caractere preservando o alfabeto base64url
{
    $i = strlen($s) - 2;
    $novo = $s[$i] === 'A' ? 'B' : 'A';
    return substr($s, 0, $i) . $novo . substr($s, $i + 1);
}

// --- emissao ---
$e01 = emite($base, $cred);
grava($saida, $resumo, 'E01', 'senha certa (dbseller)', $e01, $segredos);
$j01 = json_decode($e01['corpo'], true);
$token = isset($j01['access_token']) ? $j01['access_token'] : null;
if ($token) { $segredos[] = $token; }
grava($saida, $resumo, 'E03', 'usuario inexistente', emite($base, $cred, array('username' => 'nao_existe_t045')), $segredos);
grava($saida, $resumo, 'E04', 'username vazio', emite($base, $cred, array('username' => '')), $segredos);
grava($saida, $resumo, 'E06', 'client_secret errado', emite($base, $cred, array('client_secret' => 'segredo-errado')), $segredos);
grava($saida, $resumo, 'E07', 'client_id inexistente', emite($base, $cred, array('client_id' => '987654')), $segredos);
grava($saida, $resumo, 'E08', 'grant_type invalido', emite($base, $cred, array('grant_type' => 'invalido')), $segredos);
grava($saida, $resumo, 'E09', 'grant_type ausente', emite($base, $cred, array('grant_type' => null)), $segredos);
grava($saida, $resumo, 'E10', 'scope inexistente', emite($base, $cred, array('scope' => 'escopo-inexistente')), $segredos);
grava($saida, $resumo, 'E11', 'GET (metodo errado)', emite($base, $cred, array(), 'GET', ''), $segredos);
grava($saida, $resumo, 'E12', 'corpo JSON', emite($base, $cred, array(), 'POST', json_encode(array('grant_type' => 'password', 'client_id' => $cred['id'], 'client_secret' => $cred['secret'], 'username' => 'dbseller', 'password' => 'dbseller')), 'application/json'), $segredos);
grava($saida, $resumo, 'E13', 'username com 10 mil caracteres', emite($base, $cred, array('username' => str_repeat('A', 10000))), $segredos);

// --- uso do token ---
grava($saida, $resumo, 'U01', 'token valido recem emitido', uso($base, $token), $segredos);
$p = jwtPartes($token);
if (count($p) === 3) {
    grava($saida, $resumo, 'U02', 'token adulterado: 1 caractere da assinatura', uso($base, $p[0] . '.' . $p[1] . '.' . troca1($p[2])), $segredos);
    grava($saida, $resumo, 'U03', 'token adulterado: 1 caractere do payload', uso($base, $p[0] . '.' . troca1($p[1]) . '.' . $p[2]), $segredos);
    grava($saida, $resumo, 'U04', 'token sem assinatura (2 partes)', uso($base, $p[0] . '.' . $p[1]), $segredos);
} else {
    foreach (array('U02', 'U03', 'U04') as $c) { $resumo[] = $c . "\t-\t-\tPULADO: sem token emitido"; }
}

// --- token emitido por rodada anterior (ou por outro runtime) ---
if ($arqAnterior && is_file($arqAnterior)) {
    $ant = trim(file_get_contents($arqAnterior));
    $segredos[] = $ant;
    grava($saida, $resumo, 'U09', 'token emitido antes (rodada anterior ou outro runtime) reaproveitado', uso($base, $ant), $segredos);
} else {
    $resumo[] = "U09\t-\t-\tPULADO: sem token anterior";
}

// --- createToken de App\Domain\Client (rota POST /v4/api/client/auth/usuario, por CPF/CNPJ) ---
grava($saida, $resumo, 'C01', 'client/auth/usuario com cpfcnpj inexistente', SistemaCliente::requisita($base, 'POST', '/v4/api/client/auth/usuario', array('corpo' => 'cpfcnpj=00000000000', 'cabecalhos' => array('Accept: application/json'))), $segredos);
grava($saida, $resumo, 'C02', 'client/auth/usuario sem cpfcnpj', SistemaCliente::requisita($base, 'POST', '/v4/api/client/auth/usuario', array('corpo' => '', 'cabecalhos' => array('Accept: application/json'))), $segredos);
$pg = pg_connect('host=' . getenv('DB_HOST') . ' port=' . (getenv('DB_PORT') ?: '5432') . ' dbname=' . getenv('DB_DATABASE') . ' user=' . getenv('DB_USERNAME') . ' password=' . getenv('DB_PASSWORD'));
$cpf = null;
if ($pg) {
    $r = pg_query($pg, "select c.z01_cgccpf from configuracoes.db_usuarios u join configuracoes.db_usuacgm uc on uc.id_usuario = u.id_usuario join protocolo.cgm c on c.z01_numcgm = uc.cgmlogin where u.id_usuario = 1 and c.z01_cgccpf <> '' limit 1");
    $l = $r ? pg_fetch_row($r) : false;
    $cpf = $l ? trim($l[0]) : null;
}
if ($cpf) {
    $segredos[] = $cpf;
    $c03 = SistemaCliente::requisita($base, 'POST', '/v4/api/client/auth/usuario', array('corpo' => 'cpfcnpj=' . urlencode($cpf), 'cabecalhos' => array('Accept: application/json')));
    $jc = json_decode($c03['corpo'], true);
    if (isset($jc['data']['access_token'])) { $segredos[] = $jc['data']['access_token']; }
    // o corpo traz dados do usuario: so a estrutura (chaves e tipos) e gravada
    $c03n = $c03;
    if (is_array($jc)) {
        $mascara = function ($v) use (&$mascara) { return is_array($v) ? array_map($mascara, $v) : (is_string($v) ? '<string len=' . strlen($v) . '>' : (is_bool($v) || $v === null ? $v : '<' . gettype($v) . '>')); };
        $c03n['corpo'] = json_encode($mascara($jc));
    }
    grava($saida, $resumo, 'C03', 'client/auth/usuario com o cpf do usuario 1 (estrutura da resposta; valores mascarados)', $c03n, $segredos);
    $tc = isset($jc['data']['access_token']) ? $jc['data']['access_token'] : null;
    grava($saida, $resumo, 'C04', 'uso do token gerado por createToken', uso($base, $tc), $segredos);
} else {
    $resumo[] = "C03\t-\t-\tPULADO: usuario 1 sem cpf/cnpj";
    $resumo[] = "C04\t-\t-\tPULADO: usuario 1 sem cpf/cnpj";
}

// guarda o token valido para a rodada seguinte
if ($token && $arqAnterior) {
    $novo = $arqAnterior . '.novo';
    file_put_contents($novo, $token);
    chmod($novo, 0600);
}
file_put_contents($saida . '/resumo.tsv', "caso\tstatus\ttipo\tdescricao\n" . implode("\n", $resumo) . "\n");
echo count($resumo) . " casos\n";
