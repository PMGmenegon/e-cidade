<?php
// T-037: varredura por TOKENIZADOR das formas de variavel-variavel que mudam de sentido do PHP 5 para o 7+.
// Uso: php varre_variaveis.php <raiz> [<lista-de-arquivos>]   (sem lista: todo *.php sob <raiz>, fora vendor/)
// Saida TSV: arquivo<TAB>linha<TAB>forma<TAB>trecho. Formas:
//   VV   $$a[..] / $$a{..}              (5.6: ${$a[..]}; 7+: ${$a}[..])
//   OBJ  $o->$p[..]                      (5.6: $o->{$p[..]}; 7+: ($o->$p)[..])
//   OBJC $o->$p[..](..)                  (idem, chamada)
//   STC  Cls::$p[..](..)                 (5.6: metodo estatico de nome $p[..]; 7+: elemento da propriedade estatica, chamado)
//   VVB  ${expr}[..]                     (mesmo sentido nos dois; so interessa se era $$a[..] no 5.6: reescrita do Rector)
//   OBJB $o->{expr}[..] / STB Cls::${expr}[..]   (idem)
error_reporting(0);
$raiz = rtrim($argv[1], '/');
if (isset($argv[2])) { $arqs = array_filter(array_map('trim', file($argv[2]))); }
else {
    $arqs = array();
    $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($raiz, FilesystemIterator::SKIP_DOTS));
    foreach ($it as $f) {
        $p = $f->getPathname();
        if (substr($p, -4) !== '.php' || strpos($p, '/vendor/') !== false) continue;
        $arqs[] = substr($p, strlen($raiz) + 1);
    }
    sort($arqs);
}
function toks($src) {
    $o = array();
    foreach (token_get_all($src) as $t) {
        if (is_array($t)) { if (in_array($t[0], array(T_WHITESPACE, T_COMMENT, T_DOC_COMMENT), true)) continue; $o[] = array($t[0], $t[1], $t[2]); }
        else $o[] = array(null, $t, null);
    }
    return $o;
}
function fim($t, $i, $abre, $fecha) { // indice do token que fecha o grupo aberto em $i
    $n = 0;
    for ($j = $i; $j < count($t); $j++) {
        if ($t[$j][1] === $abre && $t[$j][0] === null) $n++;
        elseif ($t[$j][1] === $fecha && $t[$j][0] === null) { $n--; if ($n === 0) return $j; }
    }
    return $i;
}
// linha do primeiro token com linha a partir de $i (o '$' solto nao tem linha: olhar para tras pegaria a linha de cima)
function linha($t, $i) { for ($j = $i; $j < count($t); $j++) if ($t[$j][2]) return $t[$j][2]; return 0; }
foreach ($arqs as $a) {
    $src = @file_get_contents($raiz . '/' . $a);
    if ($src === false) continue;
    $t = toks($src); $n = count($t);
    for ($i = 0; $i < $n; $i++) {
        $x = $t[$i];
        $em = function ($forma, $ini, $fimi) use (&$t, $a) {
            $s = ''; for ($k = $ini; $k <= $fimi; $k++) $s .= $t[$k][1];
            echo $a, "\t", linha($t, $ini), "\t", $forma, "\t", str_replace(array("\t", "\r", "\n"), ' ', substr($s, 0, 80)), "\n";
        };
        // $ ... : $$a[ , ${expr}[
        if ($x[0] === null && $x[1] === '$' && !($i > 0 && $t[$i-1][0] === null && $t[$i-1][1] === '$')
            && !($i > 0 && $t[$i-1][0] === T_OBJECT_OPERATOR) && !($i > 0 && $t[$i-1][0] === T_DOUBLE_COLON)) {
            $j = $i; while ($j < $n && $t[$j][0] === null && $t[$j][1] === '$') $j++;
            if ($j < $n && $t[$j][0] === T_VARIABLE && $j + 1 < $n && $t[$j+1][0] === null && ($t[$j+1][1] === '[' || $t[$j+1][1] === '{')) {
                $f = $t[$j+1][1] === '[' ? fim($t, $j+1, '[', ']') : fim($t, $j+1, '{', '}');
                $em('VV', $i, $f);
            } elseif ($j < $n && $t[$j][0] === T_CURLY_OPEN) { // nao ocorre fora de string
            } elseif ($j < $n && $t[$j][0] === null && $t[$j][1] === '{') {
                $f = fim($t, $j, '{', '}');
                if ($f + 1 < $n && $t[$f+1][0] === null && $t[$f+1][1] === '[') { $g = fim($t, $f+1, '[', ']'); $em('VVB', $i, $g); }
            } elseif ($j < $n && $t[$j][0] === T_DOLLAR_OPEN_CURLY_BRACES) { }
        }
        // $o->$p[..]   /   $o->{expr}[..]
        if ($x[0] === T_OBJECT_OPERATOR || $x[0] === T_NULLSAFE_OBJECT_OPERATOR) {
            if ($i + 2 < $n && $t[$i+1][0] === T_VARIABLE && $t[$i+2][0] === null && $t[$i+2][1] === '[') {
                $g = fim($t, $i+2, '[', ']');
                while ($g + 1 < $n && $t[$g+1][0] === null && $t[$g+1][1] === '[') $g = fim($t, $g+1, '[', ']');
                $chamada = $g + 1 < $n && $t[$g+1][0] === null && $t[$g+1][1] === '(';
                $em($chamada ? 'OBJC' : 'OBJ', $i - 1 >= 0 ? $i - 1 : $i, $g);
            } elseif ($i + 1 < $n && $t[$i+1][0] === null && $t[$i+1][1] === '{') {
                $f = fim($t, $i+1, '{', '}');
                if ($f + 1 < $n && $t[$f+1][0] === null && $t[$f+1][1] === '[') $em('OBJB', $i - 1, fim($t, $f+1, '[', ']'));
            }
        }
        // Cls::$p[..](..)   /   Cls::${expr}[..]
        if ($x[0] === T_DOUBLE_COLON) {
            if ($i + 2 < $n && $t[$i+1][0] === T_VARIABLE && $t[$i+2][0] === null && $t[$i+2][1] === '[') {
                $g = fim($t, $i+2, '[', ']');
                while ($g + 1 < $n && $t[$g+1][0] === null && $t[$g+1][1] === '[') $g = fim($t, $g+1, '[', ']');
                if ($g + 1 < $n && $t[$g+1][0] === null && $t[$g+1][1] === '(') $em('STC', $i - 1, $g);
            } elseif ($i + 2 < $n && $t[$i+1][0] === null && $t[$i+1][1] === '$' && $t[$i+2][0] === null && $t[$i+2][1] === '{') {
                $f = fim($t, $i+2, '{', '}');
                if ($f + 1 < $n && $t[$f+1][0] === null && $t[$f+1][1] === '[') $em('STB', $i - 1, fim($t, $f+1, '[', ']'));
            }
        }
    }
}
