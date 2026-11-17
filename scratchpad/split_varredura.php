<?php
/**
 * T-040: acha toda chamada split()/spliti() pelo tokenizador do PHP e classifica o padrao.
 *
 * No PHP 8.5 split() vem do polyfill dbseller/legacy (vendor/dbseller/legacy/bootstrap/PHP_56.php),
 * que faz explode($pattern, $string): nao trata regex e ignora o 3o argumento (limite).
 * spliti() nao tem polyfill.
 *
 * Uso (no container, a lista com caminhos relativos a raiz):
 *   php split_varredura.php <raiz> <lista.txt> > split.tsv
 * Saida TSV: arquivo, linha, funcao, nargs, padrao (fonte), valor (escapado), classe, motivo
 * Classes:
 *   igual         literal sem metacaractere de regex: explode() devolve o mesmo
 *   diverge       literal com . | \ [ ] ( ) * + ? ^ $ { }, vazio, spliti() ou 3o argumento (limite)
 *   desconhecido  padrao nao literal (variavel, constante, expressao, string com interpolacao)
 */
$raiz = rtrim($argv[1], '/') . '/';
$arqs = file($argv[2], FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);

/** Valor de um T_CONSTANT_ENCAPSED_STRING, com a semantica de aspas do PHP. */
function valor_literal($s) {
    $q = $s[0];
    $c = substr($s, 1, -1);
    if ($q === "'") {
        return preg_replace('/\\\\([\\\\\'])/', '$1', $c);
    }
    return preg_replace_callback('/\\\\(?:([nrtvef\\\\$"])|([0-7]{1,3})|x([0-9A-Fa-f]{1,2}))/', function ($m) {
        if (isset($m[3]) && $m[3] !== '') return chr(hexdec($m[3]));
        if (isset($m[2]) && $m[2] !== '') return chr(octdec($m[2]) & 255);
        $t = array('n' => "\n", 'r' => "\r", 't' => "\t", 'v' => "\v", 'e' => "\x1b", 'f' => "\f",
                   '\\' => '\\', '$' => '$', '"' => '"');
        return $t[$m[1]];
    }, $c);
}

function visivel($v) {
    return addcslashes($v, "\0..\37\\\t\177..\377");
}

$ignorar = array(T_WHITESPACE, T_COMMENT, T_DOC_COMMENT);
echo "arquivo\tlinha\tfuncao\tnargs\tpadrao\tvalor\tclasse\tmotivo\n";
foreach ($arqs as $a) {
    $src = @file_get_contents($raiz . $a);
    if ($src === false) { fwrite(STDERR, "nao li $a\n"); continue; }
    $t = token_get_all($src);
    $n = count($t);
    for ($i = 0; $i < $n; $i++) {
        if (!is_array($t[$i])) continue;
        $id = $t[$i][0];
        $nome = strtolower(ltrim($t[$i][1], '\\'));
        $ok = $id === T_STRING || (defined('T_NAME_FULLY_QUALIFIED') && $id === T_NAME_FULLY_QUALIFIED);
        if (!$ok || ($nome !== 'split' && $nome !== 'spliti')) continue;
        // anterior significativo: nao pode ser ->, ::, function, new, nem fazer parte de nome qualificado
        $p = $i - 1;
        while ($p >= 0 && is_array($t[$p]) && in_array($t[$p][0], $ignorar)) $p--;
        if ($p >= 0 && is_array($t[$p]) && in_array($t[$p][0], array(T_OBJECT_OPERATOR, T_DOUBLE_COLON, T_FUNCTION, T_NEW, T_NS_SEPARATOR, T_CONST))) continue;
        if (defined('T_NULLSAFE_OBJECT_OPERATOR') && $p >= 0 && is_array($t[$p]) && $t[$p][0] === T_NULLSAFE_OBJECT_OPERATOR) continue;
        $j = $i + 1;
        while ($j < $n && is_array($t[$j]) && in_array($t[$j][0], $ignorar)) $j++;
        if ($j >= $n || $t[$j] !== '(') continue;
        // argumentos no nivel de cima
        $prof = 0; $args = array(array()); $k = $j + 1;
        for (; $k < $n; $k++) {
            $x = $t[$k];
            $s = is_array($x) ? $x[1] : $x;
            if (in_array($s, array('(', '[', '{')) || (is_array($x) && in_array($x[0], array(T_CURLY_OPEN, T_DOLLAR_OPEN_CURLY_BRACES)))) $prof++;
            if (in_array($s, array(')', ']', '}'))) { if ($prof === 0) break; $prof--; }
            if ($s === ',' && $prof === 0) { $args[] = array(); continue; }
            if (is_array($x) && in_array($x[0], $ignorar)) continue;
            $args[count($args) - 1][] = $x;
        }
        $nargs = count($args[0]) ? count($args) : 0;
        $pt = $args[0];
        $fonte = implode('', array_map(function ($x) { return is_array($x) ? $x[1] : $x; }, $pt));
        $fonte = str_replace(array("\t", "\n", "\r"), ' ', $fonte);
        $valor = ''; $classe = 'desconhecido'; $motivo = 'padrao nao literal';
        if (count($pt) === 1 && is_array($pt[0]) && $pt[0][0] === T_CONSTANT_ENCAPSED_STRING) {
            $valor = valor_literal($pt[0][1]);
            if ($valor === '') {
                $classe = 'diverge'; $motivo = 'padrao vazio';
            } elseif (preg_match('/[.|\\\\\\[\\]()*+?^${}]/', $valor)) {
                $classe = 'diverge'; $motivo = 'metacaractere de regex';
            } else {
                $classe = 'igual'; $motivo = 'literal sem metacaractere';
            }
        }
        if ($nome === 'spliti') { $classe = 'diverge'; $motivo = 'spliti sem polyfill no 8.5'; }
        elseif ($nargs >= 3) {
            $motivo = ($motivo === 'literal sem metacaractere' ? '' : $motivo . '; ') . 'limite (3o argumento) ignorado pelo polyfill';
            $classe = 'diverge';
        }
        echo implode("\t", array($a, $t[$i][2], $nome, $nargs, $fonte, visivel($valor), $classe, $motivo)), "\n";
    }
}
