<?php
// T-068: carrega o .env da raiz como as 9 telas fazem e mostra, para cada chave do .env, o que ficou em getenv(),
// $_ENV e $_SERVER (so presenca e 8 caracteres do sha1 do valor: o .env tem segredos). Pedido pelo Apache.
//   ?modo=antigo  new \Dotenv\Dotenv('./') + load()            (a linha de hoje)
//   ?modo=novo    a linha nova (escolhe pela API disponivel) + load()
//   &pre=putenv|env|server   antes de carregar, define APP_NAME=pre-definido nesse lugar (o .env tambem tem APP_NAME)
//   &duas=1       carrega duas vezes (telas que incluem outra tela que carrega de novo)
chdir(__DIR__);   // ecidade/ (a sonda fica na raiz, como as telas) (o './' do Dotenv e relativo a ela)
require_once 'vendor/autoload.php';
header('Content-Type: text/plain');
$pre = isset($_GET['pre']) ? $_GET['pre'] : '';
if ($pre === 'putenv') putenv('APP_NAME=pre-definido');
if ($pre === 'env') $_ENV['APP_NAME'] = 'pre-definido';
if ($pre === 'server') $_SERVER['APP_NAME'] = 'pre-definido';
$h = function ($v) { return $v === false || $v === null ? '-' : substr(sha1($v), 0, 8); };
$chaves = array();
foreach (file('.env') as $l) {
    if (preg_match('/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*=/', $l, $m)) $chaves[] = $m[1];
}
$antes = array();
foreach ($chaves as $k) $antes[$k] = $h(getenv($k)) . ' ' . $h(isset($_ENV[$k]) ? $_ENV[$k] : null) . ' ' . $h(isset($_SERVER[$k]) ? $_SERVER[$k] : null);
try {
    for ($i = 0; $i < (empty($_GET['duas']) ? 1 : 2); $i++) {
        if ($_GET['modo'] === 'antigo') {
            $dotenv = new \Dotenv\Dotenv('./');
        } else {
            $dotenv = method_exists('Dotenv\Dotenv', 'createUnsafeImmutable') ? \Dotenv\Dotenv::createUnsafeImmutable('./') : new \Dotenv\Dotenv('./');
        }
        $dotenv->load();
    }
    echo "carregou\n";
} catch (Throwable $e) {
    echo 'ERRO ', get_class($e), ': ', $e->getMessage(), "\n";
} catch (Exception $e) {
    echo 'ERRO ', get_class($e), ': ', $e->getMessage(), "\n";
}
echo "chave antes(getenv env server) -> depois(getenv env server)\n";
foreach ($chaves as $k) {
    echo $k, ' ', $antes[$k], ' -> ', $h(getenv($k)), ' ', $h(isset($_ENV[$k]) ? $_ENV[$k] : null), ' ', $h(isset($_SERVER[$k]) ? $_SERVER[$k] : null), "\n";
}
