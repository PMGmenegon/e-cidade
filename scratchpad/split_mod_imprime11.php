<?php
/**
 * T-052: a linha do resumo de fpdf151/impmodelos/mod_imprime11.php (Solicitacao de Compra), isolada.
 *   antes:  array_unique(split("[\n\r]", $resumo))      -- 5.6: regex POSIX; 8.5: polyfill explode
 *   depois: array_unique(preg_split("/[\n\r]/", $resumo)) -- PCRE nos dois
 * Carrega o autoload do composer como a tela (no 8.5 e ele que define o split do polyfill).
 *
 * Uso (no container): php split_mod_imprime11.php /var/www/html/vendor/autoload.php
 */
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', 'stderr');
require $argv[1];

// O resumo vem de um <textarea> (pc10_resumo): o navegador envia as quebras como CRLF.
$casos = array(
    'vazio'               => '',
    'uma linha'           => 'Aquisicao de material de expediente',
    'CRLF'                => "Aquisicao de material\r\nPara a secretaria X\r\nEntrega em 30 dias",
    'CRLF com repetidas'  => "Item A\r\nItem A\r\nItem B\r\n\r\nItem B",
    'so LF'               => "Linha 1\nLinha 2\nLinha 1",
    'CR sozinho'          => "Linha 1\rLinha 2",
);
echo 'PHP ', PHP_VERSION, "\n";
foreach ($casos as $nome => $resumo) {
    $antes  = implode("\n", array_unique(split("[\n\r]", $resumo)));
    $depois = implode("\n", array_unique(preg_split("/[\n\r]/", $resumo)));
    printf("%-20s antes=%s depois=%s\n", $nome, json_encode($antes), json_encode($depois));
}
