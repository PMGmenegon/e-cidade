<?php
// Mede SuperClosure (usado por src/Task/Closure.php): serializa e desserializa uma closure e a task ECidade\Task\Closure.
// Uso: php scratchpad/superclosure_medida.php <vendor/autoload.php> <pasta src/Task> [arquivo-de-payload-para-ler]
// Sem o 3o argumento imprime o resultado e o payload serializado; com ele desserializa um payload de outro runtime e executa.
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '1');
require $argv[1];
foreach (array('TaskInterface', 'Base', 'Closure') as $c) { require $argv[2] . '/' . $c . '.php'; }
echo PHP_VERSION, "\n";
if (isset($argv[3])) {
    $u = unserialize(file_get_contents($argv[3]));
    echo 'payload de outro runtime: ', get_class($u), ' => ', call_user_func($u, 5), "\n";
    exit;
}
$y = 8;
$f = function ($a) use ($y) { return $a * $y + 2; };
$s = serialize(new SuperClosure\SerializableClosure($f));
echo 'serializado: len=', strlen($s), "\n";
$u = unserialize($s);
echo 'desserializado: ', is_object($u) ? get_class($u) . ' => ' . call_user_func($u, 5) : 'FALHOU', "\n";
$t = unserialize(serialize(new ECidade\Task\Closure(function () { return 'ok-' . (6 * 7); })));
echo 'task desserializada: ', get_class($t), ' => ', $t->doRun(), "\n";
file_put_contents('php://stderr', $s . "\n");
