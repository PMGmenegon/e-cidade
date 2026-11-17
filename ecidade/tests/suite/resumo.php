<?php
// Resume resultados JUnit de uma execucao da suite num relatorio de texto.
// Roda dentro do runtime (PHP 5.6 e 8.x): sintaxe compativel com os dois.
//
// Uso: php resumo.php <runtime> <saida.txt> <camada>:<junit.xml>:<codigo-phpunit> ...
// Saida do processo: 0 = tudo passou; 1 = algum falho/erro de execucao, ou nenhum teste executado.

if ($argc < 4) {
    fwrite(STDERR, "uso: php resumo.php <runtime> <saida.txt> <camada>:<junit.xml>:<codigo> ...\n");
    exit(2);
}

$runtime = $argv[1];
$saida = $argv[2];
$porCamada = array();
$erros = array();

for ($i = 3; $i < $argc; $i++) {
    $partes = explode(':', $argv[$i]);
    $camada = $partes[0];
    $xml = isset($partes[1]) ? $partes[1] : '';
    $codigo = isset($partes[2]) ? (int) $partes[2] : 0;

    if (!isset($porCamada[$camada])) {
        $porCamada[$camada] = array('total' => 0, 'aprovados' => 0, 'falhos' => 0, 'pulados' => 0, 'tempo' => 0.0);
    }
    $c = &$porCamada[$camada];

    if ($xml === '' || !is_file($xml)) {
        $erros[] = "$camada: sem relatorio JUnit (codigo do PHPUnit: $codigo)";
        unset($c);
        continue;
    }

    $antes = libxml_use_internal_errors(true);
    $doc = simplexml_load_file($xml);
    libxml_use_internal_errors($antes);
    if ($doc === false) {
        $erros[] = "$camada: JUnit ilegivel ($xml)";
        unset($c);
        continue;
    }

    $falhosAqui = 0;
    foreach ($doc->xpath('//testcase') as $caso) {
        $c['total']++;
        $c['tempo'] += (float) $caso['time'];
        if (count($caso->failure) > 0 || count($caso->error) > 0) {
            $c['falhos']++;
            $falhosAqui++;
        } elseif (count($caso->skipped) > 0) {
            $c['pulados']++;
        } else {
            $c['aprovados']++;
        }
    }
    if ($codigo !== 0 && $falhosAqui === 0) {
        $erros[] = "$camada: PHPUnit saiu com codigo $codigo sem teste falho no JUnit ($xml)";
    }
    unset($c);
}

$t = array('total' => 0, 'aprovados' => 0, 'falhos' => 0, 'pulados' => 0, 'tempo' => 0.0);
foreach ($porCamada as $c) {
    foreach ($t as $k => $v) {
        $t[$k] += $c[$k];
    }
}

$linhas = array();
$linhas[] = "runtime: PHP " . PHP_VERSION . " (alvo $runtime)";
$linhas[] = "total: " . $t['total'];
$linhas[] = "aprovados: " . $t['aprovados'];
$linhas[] = "falhos: " . $t['falhos'];
$linhas[] = "pulados: " . $t['pulados'];
$linhas[] = "erros_de_execucao: " . count($erros);
$linhas[] = sprintf("tempo: %.3fs", $t['tempo']);
foreach ($porCamada as $nome => $c) {
    $linhas[] = sprintf(
        "camada %s: total=%d aprovados=%d falhos=%d pulados=%d tempo=%.3fs",
        $nome, $c['total'], $c['aprovados'], $c['falhos'], $c['pulados'], $c['tempo']
    );
}
foreach ($erros as $e) {
    $linhas[] = "erro: $e";
}

$ok = ($t['falhos'] === 0 && count($erros) === 0 && $t['total'] > 0);
$linhas[] = "resultado: " . ($ok ? "APROVADO" : "REPROVADO");

file_put_contents($saida, implode("\n", $linhas) . "\n");
echo implode("\n", $linhas) . "\n";
exit($ok ? 0 : 1);
