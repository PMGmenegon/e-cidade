<?php
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; } // so linha de comando
/**
 * T-012: leitura ESTATICA dos controllers das rotas GET: "leitura" ou "grava/duvidosa", com o trecho que justifica.
 * Roda no 5.6 (Reflection sobre a classe da rota): docker exec -w /var/www/html ecidade_<agente>_56 php tests/sistema/classifica-get.php
 * Escreve dados/get-classificacao.tsv (rota, acao, classe, trecho). Limite honesto: olha o CORPO do metodo do controller;
 * o que ele delega a servicos/repositorios nao e seguido -- por isso a trava SOMENTE_LEITURA=1 (trava-leitura.sh) e a segunda prova.
 */
chdir(dirname(dirname(__DIR__)));
require 'bootstrap/autoload.php';
$gravacao = '/(->\s*(save|create|firstOrCreate|updateOrCreate|update|delete|forceDelete|insert|insertGetId|increment|decrement|attach|detach|sync|push|store|commit|restore)\s*\(|DB::\s*(insert|update|delete|statement|unprepared)|db_query\s*\(|pg_query\s*\(|pg_exec|file_put_contents|fwrite|unlink\s*\(|->put\s*\(|Mail::|dispatch\s*\(|Artisan::|->\s*(executar|processar|gerar|salvar|incluir|alterar|excluir|encerrar|sincronizar|importar|enviar|cancelar|baixar|reprocessar)\w*\s*\()/i';
$nome = '/(processar|exclu|delet|gerar|salvar|encerr|inativar|importar|enviar|atualiz|cancel|baixa|assin|migr|reprocess|emitir|sincroniz|abrir|fechar|iniciar|finalizar|liberar|bloquear)/i';
$saida = array();
foreach (file('tests/sistema/dados/rotas-v4.tsv', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) {
    $c = explode("\t", $l);
    if ($c[0] !== 'GET') { continue; }
    list($classe, $metodo) = strpos($c[2], "@") ? explode("@", ltrim($c[2], "\\")) : array($c[2], "");
    $classe_ = 'leitura'; $trecho = '';
    if ($c[2] === 'Closure' || !class_exists($classe) || !method_exists($classe, $metodo)) {
        $classe_ = 'duvidosa'; $trecho = 'acao nao localizavel (' . $c[2] . ')';
    } else {
        $rm = new ReflectionMethod($classe, $metodo);
        $src = file($rm->getFileName());
        $corpo = implode('', array_slice($src, $rm->getStartLine() - 1, $rm->getEndLine() - $rm->getStartLine() + 1));
        if (preg_match($gravacao, $corpo, $m, PREG_OFFSET_CAPTURE)) {
            $classe_ = 'duvidosa';
            $ini = strrpos(substr($corpo, 0, $m[0][1]), "\n"); $ini = $ini === false ? 0 : $ini + 1;
            $trecho = trim(preg_replace('/\s+/', ' ', substr($corpo, $ini, strpos($corpo . "\n", "\n", $m[0][1]) - $ini)));
        } elseif (preg_match($nome, $c[1], $m)) {
            $classe_ = 'duvidosa'; $trecho = 'verbo "' . $m[1] . '" na rota; corpo sem escrita direta, delega a servico';
        } else {
            $ret = preg_match('/return\s+[^;]+;/s', $corpo, $m) ? trim(preg_replace('/\s+/', ' ', $m[0])) : trim(preg_replace('/\s+/', ' ', substr($corpo, 0, 120)));
            $trecho = substr($ret, 0, 160);
        }
    }
    $saida[] = $c[1] . "\t" . $c[2] . "\t" . $classe_ . "\t" . str_replace("\t", ' ', $trecho);
}
file_put_contents('tests/sistema/dados/get-classificacao.tsv', implode("\n", $saida) . "\n");
$n = array_count_values(array_map(function ($l) { $x = explode("\t", $l); return $x[2]; }, $saida));
echo json_encode($n) . "\n";
