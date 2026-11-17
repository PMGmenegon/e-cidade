<?php
// Converte o deslocamento de string/array com chaves ($s{0}) em colchetes ($s[0]), removido no PHP 8.
// Equivalente no 5.6 (mesma semantica). Preserva os bytes do resto do arquivo (ISO-8859-1 inclusive).
// Rodar no PHP 5.6 (o tokenizador do 8 ja nao aceita o fonte): php chaves_offset.php < entrada > saida
// Uso tipico: docker exec -i ecidade_<agente>_56 php /tmp/chaves_offset.php < arq.php > novo.php
// Conta no stderr quantas chaves foram trocadas.

$src = stream_get_contents(STDIN);
$tok = token_get_all($src);
$n = count($tok);
$out = '';
$pilha = array();   // para cada '{' aberta: true se for deslocamento (fecha como ']')
$trocas = 0;
$ultimo = null;     // ultimo token significativo (texto) e o seu tipo
$ultimoTipo = null;
$ultimoAntes = null; // tipo do significativo anterior ao ultimo
$abreCurly = array(T_CURLY_OPEN, T_DOLLAR_OPEN_CURLY_BRACES);

for ($i = 0; $i < $n; $i++) {
    $t = $tok[$i];
    $tipo = is_array($t) ? $t[0] : $t;
    $txt = is_array($t) ? $t[1] : $t;

    if ($tipo === T_WHITESPACE || $tipo === T_COMMENT || $tipo === T_DOC_COMMENT) {
        $out .= $txt;
        continue;
    }

    if ($txt === '{' && !is_array($t)) {
        // abertura em codigo: e deslocamento se o significativo anterior termina uma expressao com valor
        // indexavel: variavel, propriedade ($o->p), outro deslocamento ($a[0]{1}) ou chamada/variavel-variavel.
        $ehOffset = ($ultimoTipo === T_VARIABLE)
            || ($ultimoTipo === T_STRING && $ultimoAntes === T_OBJECT_OPERATOR)
            || ($ultimo === ']');   // inclui o fecho de um deslocamento anterior: $a{0}{1}
        $pilha[] = $ehOffset;
        if ($ehOffset) {
            $out .= '[';
            $trocas++;
        } else {
            $out .= '{';
        }
    } elseif (is_array($t) && in_array($tipo, $abreCurly, true)) {
        $pilha[] = false;
        $out .= $txt;
    } elseif ($txt === '}' && !is_array($t)) {
        $eraOffset = array_pop($pilha);
        $txt = $eraOffset ? ']' : '}';
        $out .= $txt;
    } else {
        $out .= $txt;
    }

    $ultimoAntes = $ultimoTipo;
    $ultimo = ($txt === '{' && !is_array($t) && end($pilha)) ? '[' : $txt;
    $ultimoTipo = $tipo;
}

fwrite(STDERR, "trocas: $trocas\n");
echo $out;
