import pytest

from servidor.padroes import CATALOGO, PADROES, ocorrencias


def acha(nome: str, codigo: str) -> int:
    return len(ocorrencias(PADROES[nome], "<?php\n" + codigo + "\n"))


@pytest.mark.parametrize("nome,positivo,negativo", [
    ("parse_str_1_arg", "parse_str(base64_decode($_SERVER['QUERY_STRING']));", "parse_str($qs, $__qs);"),
    ("parse_str_1_arg", "parse_str($HTTP_SERVER_VARS[\"QUERY_STRING\"]);", "parse_str(substr($a, 1), $saida);"),
    ("parse_str_1_arg", "parse_str(substr($x, 1));", "$o->parse_str($x);"),
    ("parse_str_1_arg", "parse_str(\n  $x\n);", "function parse_str($x) {}"),
    ("parse_str_1_arg", "mb_parse_str($q);", "mb_parse_str($q, $saida);"),
    ("parse_str_1_arg", "parse_str(\"a=1,b\");", "parse_str(\"a=)1\", $s);"),
    ("split", "$a = split(\"-\", $x);", "$a = preg_split('/-/', $x);"),
    ("split", "list($d, $m) = split('/', $data);", "$a = str_split($x); $b = mb_split(',', $y);"),
    ("split", "$p = split('#',$b);", "$x->split(','); var s = 'a'.split('-');"),
    ("each", "while (list($k, $v) = each($arr)) {}", "$.each(lista, function(){}); $col->each(fn() => 1);"),
    ("ereg", "if (ereg('^[0-9]+$', $x)) {}", "preg_match('/^a/', $x);"),
    ("ereg", "$s = eregi_replace('a', 'b', $s);", "$s = preg_replace('/a/i', 'b', $s);"),
    ("create_function", "$f = create_function('$a', 'return $a;');", "$f = function ($a) { return $a; };"),
    ("pg_resultado_false", "$n = pg_numrows(db_query($sql));", "$rs = db_query($sql); if ($rs) { $n = pg_num_rows($rs); }"),
    ("pg_resultado_false", "$l = pg_fetch_object(pg_query($c, $s));", "$l = pg_fetch_object($rs);"),
    ("is_resource_pgsql", "if (!is_resource($rs)) { return; }", "if ($rs === false) { return; }"),
    ("reflection_getclass", "$c = $param->getClass();", "$c = $obj->getClassName();"),
    ("removidas_php8", "$v = money_format('%i', $x); get_magic_quotes_gpc();", "$v = number_format($x, 2);"),
    ("removidas_php8", "mysql_query($sql); mcrypt_encrypt($a);", "my_money_format(1); pg_query($s);"),
    ("chaves_offset_string", "$c = $str{0};", "$c = \"{$str}\"; $d = $str[0];"),
    ("utf8_encode_decode", "$s = utf8_decode($x);", "$s = mb_convert_encoding($x, 'ISO-8859-1', 'UTF-8');"),
    ("strftime", "echo strftime('%d/%m/%Y');", "echo date('d/m/Y');"),
    ("filter_sanitize_string", "filter_var($x, FILTER_SANITIZE_STRING);", "filter_var($x, FILTER_SANITIZE_SPECIAL_CHARS);"),
    ("e_strict", "error_reporting(E_ALL & ~E_STRICT);", "error_reporting(E_ALL);"),
    ("casts_nao_canonicos", "$i = (integer) $x; $b = (boolean)$y; $d = (double) $z;", "$i = (int) $x; $f = (float) $z;"),
    ("nulo_implicito", "function f(Foo $x = null) {}", "function f(?Foo $x = null) {} function g($x = null) {}"),
    ("nulo_implicito", "public function g(array $a = NULL, $b = 1) {}", "public function g(Foo|null $a = null) {}"),
    ("interpolacao_dolar_chave", "echo \"valor ${nome}\";", "echo \"valor {$nome}\"; $v = ${'x'};"),
    ("laravel_dates_property", "protected $dates = ['created_at'];", "protected $casts = ['x' => 'datetime'];"),
    ("laravel_helpers_globais", "$v = array_get($a, 'x'); $s = str_slug($t);", "$v = Arr::get($a, 'x'); array_merge($a, $b);"),
    ("laravel_dispatch_now", "dispatch_now(new Job); Bus::dispatchNow($j); $this->dispatchNow($j);", "dispatch_sync(new Job);"),
    ("passport_routes", "Passport::routes();", "Passport::tokensExpireIn(now());"),
    ("carbon_diff_in", "$d = $a->diffInDays($b);", "$d = $a->diffForHumans($b);"),
    ("doctrine_dbal", "$sm = $conn->getDoctrineSchemaManager();", "$sm = Schema::getColumnListing('t');"),
    ("request_get", "$x = $request->get('id');", "$x = $request->input('id');"),
    ("count_null", "$n = count($lista);", "$n = count([1, 2]);"),
])
def test_padrao_positivo_e_negativo(nome, positivo, negativo):
    assert acha(nome, positivo) >= 1, f"{nome} nao achou: {positivo}"
    assert acha(nome, negativo) == 0, f"{nome} falso positivo: {negativo}"


def test_construtor_php4():
    antigo = "class cl_tabela {\n  var $rotulo = null;\n  function cl_tabela() {\n    $this->rotulo = 1;\n  }\n}"
    novo = "class cl_tabela {\n  function __construct() {}\n  function cl_tabela() {}\n}"
    outra_classe = "class A {\n function __construct() {}\n}\nclass B {\n function b() {}\n}"
    assert acha("construtor_php4", antigo) == 1
    assert acha("construtor_php4", novo) == 0
    assert acha("construtor_php4", outra_classe) == 1
    assert acha("construtor_php4", "<td class=\"x\">texto class teste</td>") == 0


def test_linha_da_ocorrencia():
    p = PADROES["parse_str_1_arg"]
    texto = "<?php\n\n\nparse_str($x);\n"
    assert [texto.count("\n", 0, o) + 1 for o in ocorrencias(p, texto)] == [4]


def test_catalogo_completo_e_documentado():
    nomes = [p.nome for p in CATALOGO]
    assert len(nomes) == len(set(nomes))
    obrigatorios = {"parse_str_1_arg", "construtor_php4", "split", "each", "ereg", "create_function",
                    "count_null", "pg_resultado_false", "reflection_getclass"}
    assert obrigatorios <= set(nomes)
    for p in CATALOGO:
        assert p.titulo and p.origem and p.correcao and p.exemplo_antes and p.exemplo_depois
        assert p.mecanico in {"sim", "semi", "nao"} and p.confianca in {"alta", "media", "baixa"}
        assert p.alvo in {"php", "laravel"}
        assert (p.regex is None) != (p.detector is None)
