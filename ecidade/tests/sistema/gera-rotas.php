<?php
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; } // so linha de comando: nunca servir por HTTP
/**
 * T-012: gera as listas de rotas A PARTIR DO CODIGO. Roda no 5.6 (o Laravel 5.4 nao sobe no 8.x).
 *   docker exec -w /var/www/html ecidade_<agente>_56 php tests/sistema/gera-rotas.php
 * Escreve tests/sistema/dados/rotas-v4.tsv (Laravel: routes/) e rotas-api-v1.tsv (Silex: api/V1/Providers).
 * Colunas: metodo, uri, acao, middleware. Ordenado, para o diff ser estavel.
 */
chdir(dirname(dirname(__DIR__)));
require 'bootstrap/autoload.php';
$app = require 'bootstrap/app.php';
$app->make('Illuminate\Contracts\Console\Kernel')->bootstrap();

$linhas = array();
foreach ($app->make('router')->getRoutes() as $r) {
    $acao = $r->getActionName();
    $mw = $r->middleware();
    foreach ($r->methods() as $m) {
        if ($m === 'HEAD') {
            continue;
        }
        $linhas[] = $m . "\t/" . ltrim($r->uri(), '/') . "\t" . ($acao === 'Closure' ? 'Closure' : $acao) . "\t" . implode(',', $mw);
    }
}
sort($linhas);
file_put_contents('tests/sistema/dados/rotas-v4.tsv', implode("\n", $linhas) . "\n");
echo count($linhas) . " rotas Laravel\n";

// API V1 (Silex): prefixo do mount em APIServiceProvider + $controllers->verbo('rota', ...) de cada provider
$prefixo = '/api/v1';
$sv = file_get_contents('api/V1/APIServiceProvider.php');
preg_match_all('#mount\(\$prefix \. "(/[^"]+)", new (\w+)\(\)#', $sv, $mounts, PREG_SET_ORDER);
$v1 = array();
foreach ($mounts as $m) {
    $arq = 'api/V1/Providers/Controller/' . $m[2] . '.php';
    $src = file_get_contents($arq);
    preg_match_all('#\$controllers->(get|post|put|delete|patch)\(\s*[\'"]([^\'"]*)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]#', $src, $rs, PREG_SET_ORDER);
    foreach ($rs as $r) {
        $v1[] = strtoupper($r[1]) . "\t" . $prefixo . $m[1] . '/' . ltrim($r[2], '/') . "\t" . $r[3] . "\t";
    }
}
sort($v1);
file_put_contents('tests/sistema/dados/rotas-api-v1.tsv', implode("\n", $v1) . "\n");
echo count($v1) . " rotas API V1\n";
