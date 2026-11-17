<?php
// T-065: emite o ProgramaGestaoXls (relatorio POST /v4/api/financeiro/planejamento/programa-gestao) com dados fixos
// (2 programas, orgaos, iniciativas com metas, 4 exercicios), sem banco e sem HTTP. O .xlsx sai em <pasta>/tmp/.
// Uso (no container, /var/www/html = ecidade/): php t065_programa_gestao.php <pasta>
require '/var/www/html/vendor/autoload.php';
error_reporting(E_ALL & ~E_DEPRECATED);
define('ECIDADE_REQUEST_PATH', '/');
@mkdir($argv[1] . '/tmp', 0777, true);
chdir($argv[1]);
$ex = [2022, 2023, 2024, 2025];
$valores = function ($b) use ($ex) { $r = []; foreach ($ex as $i => $e) { $r[] = ['pl10_valor' => $b + $i * 1000.5]; } return $r; };
$metas = function ($b) use ($ex) { $r = []; foreach ($ex as $i => $e) { $r[] = ['meta_financeira' => $b * ($i + 1), 'unidade' => 'UN', 'meta_fisica' => $i + 2]; } return $r; };
$programas = [];
foreach ([1, 2] as $n) {
    $programas[] = [
        'formatado' => sprintf('%04d', $n), 'o54_descr' => "Programa $n gest\xe3o", 'valores' => $valores($n * 10000),
        'orgaos' => [['formatado' => "0$n", 'descricao' => "Secretaria $n"], ['formatado' => "1$n", 'descricao' => "Fundo $n"]],
        'iniciativas' => [
            ['acao' => 100 + $n, 'descricao_acao' => "A\xe7\xe3o $n", 'descricao_produto' => "Produto $n",
             'regionalizacoes' => [['o11_descricao' => 'Norte'], ['o11_descricao' => 'Sul']], 'metas' => $metas($n * 500)],
            ['acao' => 200 + $n, 'descricao_acao' => "Sem meta $n", 'descricao_produto' => '', 'regionalizacoes' => [], 'metas' => []],
        ],
    ];
}
$r = new App\Domain\Financeiro\Planejamento\Relatorios\ProgramaGestaoXls();
$r->setDados(['planejamento' => ['pl2_titulo' => 'PPA', 'pl2_ano_inicial' => 2022, 'pl2_ano_final' => 2025, 'exercicios' => $ex], 'programas' => $programas]);
try {
    print_r($r->emitir());
} catch (Throwable $e) {
    echo get_class($e), ': ', $e->getMessage(), "\n";
}
