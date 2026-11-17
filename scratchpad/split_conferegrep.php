<?php
/**
 * T-040: confere o que o grep acha e o tokenizador nao: para cada "arquivo<TAB>linha" (relativo a
 * raiz), o tipo do token que contem "split" naquela linha (comentario, string, outro nome...).
 * Uso (no container, cwd na raiz): php split_conferegrep.php <so_grep.tsv>
 */
foreach (file($argv[1], FILE_IGNORE_NEW_LINES) as $l) {
    list($f, $n) = explode("\t", $l);
    $tipo = '?';
    foreach (token_get_all(file_get_contents($f)) as $x) {
        if (!is_array($x)) continue;
        $ini = $x[2]; $fim = $ini + substr_count($x[1], "\n");
        if ($ini <= $n && $fim >= $n) {
            $linhas = explode("\n", $x[1]);
            if (stripos($linhas[$n - $ini], 'split') !== false) { $tipo = token_name($x[0]); break; }
        }
    }
    echo $tipo, "\n";
}
