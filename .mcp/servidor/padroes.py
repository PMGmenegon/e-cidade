"""Catalogo de padroes legados (PHP 7.4 -> 8.5 e Laravel 8 -> 12) usados por `buscar_codigo_legado`,
`proximo_trabalho` e `padroes_ja_corrigidos`.

Cada padrao e uma regex (ou um detector em Python, quando regex nao basta) sobre o TEXTO do arquivo. E
heuristica estatica: acha candidatos, nao prova bug. Comentarios e strings tambem casam. A ordem de
`prioridade` segue `regressao/baseline/decisoes-migracao.md` (parse_str -> construtor PHP4 -> split/each/ereg ...).
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# chamada de FUNCAO global: nao metodo (->, ::), nao variavel, nao sufixo de outro nome, nao definicao
FN = r"(?<![\w$>:\\.])(?<!function )"


@dataclass(frozen=True)
class Padrao:
    nome: str
    titulo: str
    alvo: str          # php | laravel
    origem: str        # em que versao quebrou/depreciou
    correcao: str
    exemplo_antes: str
    exemplo_depois: str
    mecanico: str      # sim | semi | nao
    confianca: str     # alta | media | baixa (taxa de falso positivo)
    prioridade: int    # menor = antes
    regex: str | None = None
    flags: int = 0
    detector: Callable[[str], list[int]] | None = field(default=None, compare=False)
    filtro: tuple[str, ...] = ()  # substrings: arquivo sem nenhuma delas e pulado (velocidade)
    ruidoso: bool = False  # fora de 'todos' (milhares de ocorrencias ou muito falso positivo)

    def como_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome, "titulo": self.titulo, "alvo": self.alvo, "origem": self.origem,
            "correcao": self.correcao, "exemplo_antes": self.exemplo_antes, "exemplo_depois": self.exemplo_depois,
            "mecanico": self.mecanico, "confianca": self.confianca, "prioridade": self.prioridade,
            "ruidoso": self.ruidoso,
        }


# ---------- detectores ----------

def _conta_args(texto: str, i: int, limite: int = 5000) -> int | None:
    """Numero de argumentos da chamada cujo '(' termina em i-1 (respeita strings e parenteses)."""
    prof, n, vazio, j, fim = 0, 1, True, i, min(len(texto), i + limite)
    while j < fim:
        ch = texto[j]
        if ch in "'\"":
            vazio = False
            j += 1
            while j < fim and texto[j] != ch:
                j += 2 if texto[j] == "\\" else 1
        elif ch in "([{":
            prof += 1
            vazio = False
        elif ch in ")]}":
            if prof == 0:
                return 0 if vazio else n
            prof -= 1
        elif ch == "," and prof == 0:
            n += 1
        elif not ch.isspace():
            vazio = False
        j += 1
    return None


_PARSE_STR = re.compile(FN + r"(?:mb_)?parse_str\s*\(")


def _parse_str_1_arg(texto: str) -> list[int]:
    return [m.start() for m in _PARSE_STR.finditer(texto) if _conta_args(texto, m.end()) == 1]


_CLASSE = re.compile(r"(?m)^[ \t]*(?:(?:abstract|final)\s+)?class\s+([A-Za-z_]\w*)")
_FUNCAO = re.compile(r"function\s+&?\s*([A-Za-z_]\w*)\s*\(")


def _construtor_php4(texto: str) -> list[int]:
    classes = list(_CLASSE.finditer(texto))
    achados = []
    for k, m in enumerate(classes):
        fim = classes[k + 1].start() if k + 1 < len(classes) else len(texto)
        metodos: dict[str, int] = {}
        for f in _FUNCAO.finditer(texto, m.end(), fim):
            metodos.setdefault(f.group(1).lower(), f.start())
        nome = m.group(1).lower()
        if nome in metodos and "__construct" not in metodos:
            achados.append(metodos[nome])
    return achados


# ---------- catalogo ----------

CATALOGO: tuple[Padrao, ...] = (
    Padrao(
        "parse_str_1_arg", "parse_str()/mb_parse_str() com 1 argumento", "php",
        "depreciado no 7.2, REMOVIDO no 8.0: ArgumentCountError (tela 500). Causa n.1 da triagem antiga (~560 telas, "
        "~2.500 func_*)",
        "Use a forma de 2 argumentos e jogue as variaveis no escopo, como os ~3.800 arquivos ja corrigidos do "
        "repositorio. Filtre 'this' e 'GLOBALS' antes do extract (no 8.x `?this=1` vira erro fatal). "
        "`parse_str(x, $_GET)` NAO serve: as telas leem as variaveis locais.",
        "parse_str(base64_decode($HTTP_SERVER_VARS['QUERY_STRING']));",
        "parse_str(base64_decode($HTTP_SERVER_VARS['QUERY_STRING']), $__qs);\n"
        "unset($__qs['this'], $__qs['GLOBALS']);\nextract($__qs);",
        "sim", "alta", 10, detector=_parse_str_1_arg, filtro=("parse_str",),
    ),
    Padrao(
        "construtor_php4", "construtor estilo PHP 4 (metodo com o nome da classe, sem __construct)", "php",
        "depreciado no 7.0; no 8.0 deixa de ser construtor: propriedades ficam nulas "
        "(`Call to a member function label() on null` nos forms). Causa n.2 (~600 classes db_*_classe.php)",
        "Renomeie o metodo para __construct (mesmo corpo). Se algum codigo chamar o nome antigo "
        "(`parent::cl_x()`, `$this->cl_x()`), troque por `parent::__construct()`.",
        "class cl_tabela {\n  function cl_tabela() {\n    $this->rotulo = new rotulo('tabela');\n  }\n}",
        "class cl_tabela {\n  function __construct() {\n    $this->rotulo = new rotulo('tabela');\n  }\n}",
        "sim", "alta", 20, detector=_construtor_php4, filtro=("class",),
    ),
    Padrao(
        "split", "split() (extensao ereg)", "php",
        "REMOVIDO no 7.0 (ja quebra na referencia 7.4: `Call to undefined function split()`). 2a camada escondida "
        "em ~190 telas e nos 5 balancetes",
        "Separador literal (\"-\", \"#\", \",\", \"/\"): `explode`. Separador que e regex (\"\\?\", \"\\|\", "
        "classes []): `preg_split` com delimitador. Mantenha o limite (3o argumento) se houver.",
        "$partes = split(\"-\", $db_selinstit);", "$partes = explode(\"-\", $db_selinstit);",
        "semi", "alta", 30, regex=FN + r"split\s*\(", filtro=("split",),
    ),
    Padrao(
        "each", "each()", "php",
        "depreciado no 7.2, REMOVIDO no 8.0 (Call to undefined function each())",
        "Troque o `while (list($k, $v) = each($arr))` por `foreach ($arr as $k => $v)`. Cuidado se o laco depende "
        "do ponteiro interno (reset/next) ou altera o array durante o laco.",
        "while (list($k, $v) = each($arr)) { ... }", "foreach ($arr as $k => $v) { ... }",
        "semi", "alta", 31, regex=FN + r"each\s*\(", filtro=("each",),
    ),
    Padrao(
        "ereg", "ereg*/eregi*/spliti/sql_regcase", "php",
        "REMOVIDOS no 7.0 (ja quebram na referencia 7.4)",
        "Use preg_* com delimitador e o modificador i quando era eregi; escape o delimitador dentro do padrao.",
        "if (ereg('^[0-9]+$', $x)) { ... }", "if (preg_match('/^[0-9]+$/', $x)) { ... }",
        "semi", "alta", 32, regex=FN + r"(?:eregi?_replace|eregi?|spliti|sql_regcase)\s*\(",
        filtro=("ereg", "spliti", "sql_regcase"),
    ),
    Padrao(
        "create_function", "create_function()", "php",
        "depreciado no 7.2, REMOVIDO no 8.0",
        "Troque por closure (`function (...) use (...) { ... }`); o codigo em string vira codigo de verdade.",
        "$f = create_function('$a', 'return $a * 2;');", "$f = function ($a) { return $a * 2; };",
        "semi", "alta", 33, regex=FN + r"create_function\s*\(", filtro=("create_function",),
    ),
    Padrao(
        "removidas_php8", "funcoes removidas (money_format, magic_quotes, fgetss, mysql_*, mcrypt_*, ...)", "php",
        "removidas no 7.0 (mysql_*), 7.2 (mcrypt_*) ou 8.0 (money_format, get_magic_quotes_*, fgetss, hebrevc, "
        "convert_cyr_string, restore_include_path, ezmlm_hash, image2wbmp, is_real, __autoload)",
        "money_format -> NumberFormatter/number_format; get_magic_quotes_gpc() -> false; fgetss -> "
        "strip_tags(fgets()); is_real -> is_float; mysql_* -> pg_*/PDO; __autoload -> spl_autoload_register.",
        "if (get_magic_quotes_gpc()) { $x = stripslashes($x); }", "// magic quotes nao existem desde o 5.4: remova",
        "semi", "alta", 34,
        regex=FN + r"(?:money_format|get_magic_quotes_(?:gpc|runtime)|set_magic_quotes_runtime|fgetss|gzgetss|"
                   r"hebrevc|convert_cyr_string|restore_include_path|ezmlm_hash|image2wbmp|is_real|mysql_\w+|"
                   r"mcrypt_\w+)\s*\(|\bfunction\s+__autoload\s*\(",
    ),
    Padrao(
        "chaves_offset_string", "acesso a offset com chaves ($str{0})", "php",
        "depreciado no 7.4, REMOVIDO no 8.0: erro de COMPILACAO (php -l falha)",
        "Use colchetes: $str[0].", "$c = $str{0};", "$c = $str[0];",
        "sim", "media", 35, regex=r"(?<![\w\"'{$\\])\$[A-Za-z_]\w*\{(?:\d+|\$[A-Za-z_]\w*)\}",
    ),
    Padrao(
        "pg_resultado_false", "pg_num_rows/pg_numrows/pg_fetch_* direto sobre db_query()/pg_query()", "php",
        "no 8.0 pg_* com `false` (consulta que falhou) levanta TypeError: `pg_numrows(): Argument #1 must be of "
        "type PgSql\\Result, false given`. No 7.4 era so warning e a tela seguia vazia",
        "Guarde o resultado e teste antes: `$rs = db_query($sql); if ($rs === false) { ...mensagem/relatorio "
        "vazio... }`. Decisao de negocio (decisoes-migracao.md, causa 4): reproduzir o silencio ou mostrar erro.",
        "$n = pg_numrows(db_query($sql));",
        "$rs = db_query($sql);\nif ($rs === false) {\n  db_redireciona('db_erros.php?db_erro=...');\n}\n"
        "$n = pg_num_rows($rs);",
        "nao", "media", 40,
        regex=FN + r"pg_(?:num_?rows|num_?fields|fetch_\w+|result|affected_rows|free_result)\s*\(\s*@?\s*"
                   r"(?:db_query|pg_query|pg_exec|pg_query_params)\s*\(",
        filtro=("pg_",),
    ),
    Padrao(
        "is_resource_pgsql", "is_resource() sobre resultado/conexao do PostgreSQL", "php",
        "no 8.1 as funcoes pg_* devolvem objetos (PgSql\\Connection, PgSql\\Result): is_resource() passa a dar "
        "false e o codigo toma o caminho de erro. Tambem casa com arquivos (fopen), que continuam resource",
        "Para pgsql: troque `is_resource($rs)` por `$rs !== false` (ou `$rs instanceof \\PgSql\\Result`). "
        "Para fopen/curl, confira caso a caso.",
        "if (!is_resource($rs)) { return false; }", "if ($rs === false) { return false; }",
        "semi", "media", 41, regex=FN + r"is_resource\s*\(", filtro=("is_resource",),
    ),
    Padrao(
        "reflection_getclass", "ReflectionParameter::getClass()", "php",
        "depreciado no 8.0 (a triagem antiga achou a mensagem em con2_anexovirgf_002)",
        "Use getType(): `$t = $p->getType(); $classe = ($t instanceof ReflectionNamedType && !$t->isBuiltin()) ? "
        "new ReflectionClass($t->getName()) : null;`",
        "$classe = $parametro->getClass();",
        "$t = $parametro->getType();\n$classe = ($t instanceof ReflectionNamedType && !$t->isBuiltin())\n"
        "    ? new ReflectionClass($t->getName()) : null;",
        "semi", "media", 42, regex=r"->getClass\s*\(\s*\)", filtro=("getClass",),
    ),
    Padrao(
        "nulo_implicito", "parametro tipado com default null sem `?` (nulo implicito)", "php",
        "depreciado no 8.4",
        "Declare o tipo como anulavel: `?Foo $x = null` (ou `Foo|null`).",
        "function f(Foo $x = null) {}", "function f(?Foo $x = null) {}",
        "sim", "media", 50, flags=re.IGNORECASE,
        regex=r"function\b[^(]*\([^)]*?(?<![?|\w\\])(?!mixed\b|null\b)[A-Za-z_\\][\w\\]*\s+&?(?:\.\.\.)?\$\w+\s*=\s*null\b",
    ),
    Padrao(
        "pg_aliases", "apelidos antigos de pg_* (pg_numrows, pg_exec, pg_result, pg_fieldname...)", "php",
        "depreciados desde o 8.0; o 8.5 emite `Function pg_numrows() is deprecated since 8.0` (verificado no "
        "ecidade74_php85). Ainda funcionam: e aviso, nao quebra",
        "Troque pelo nome atual: pg_numrows->pg_num_rows, pg_numfields->pg_num_fields, pg_fieldname->pg_field_name, "
        "pg_result->pg_fetch_result, pg_exec->pg_query, pg_freeresult->pg_free_result, pg_cmdtuples->"
        "pg_affected_rows, pg_errormessage->pg_last_error, pg_getlastoid->pg_last_oid (mesma assinatura).",
        "$n = pg_numrows($rs); $v = pg_result($rs, 0, 'codigo');",
        "$n = pg_num_rows($rs); $v = pg_fetch_result($rs, 0, 'codigo');",
        "sim", "alta", 57,
        regex=FN + r"pg_(?:numrows|numfields|fieldname|fieldsize|fieldtype|fieldnum|fieldprtlen|fieldisnull|"
                   r"freeresult|getlastoid|cmdtuples|errormessage|exec|result|clientencoding|setclientencoding|"
                   r"loreadall|lounlink|loread|lowrite|locreate|loopen|loclose|loimport|loexport)\s*\(",
        filtro=("pg_",), ruidoso=True,
    ),
    Padrao(
        "utf8_encode_decode", "utf8_encode()/utf8_decode()", "php",
        "depreciadas no 8.2 (base LATIN1 usa muito)",
        "mb_convert_encoding($s, 'UTF-8', 'ISO-8859-1') no lugar de utf8_encode; invertido para utf8_decode.",
        "$s = utf8_decode($x);", "$s = mb_convert_encoding($x, 'ISO-8859-1', 'UTF-8');",
        "sim", "alta", 51, regex=FN + r"utf8_(?:en|de)code\s*\(", filtro=("utf8_",),
    ),
    Padrao(
        "strftime", "strftime()/gmstrftime()", "php",
        "depreciadas no 8.1",
        "date()/DateTime::format() para formatos numericos; IntlDateFormatter para nomes de mes/dia em portugues.",
        "echo strftime('%d/%m/%Y');", "echo date('d/m/Y');",
        "semi", "alta", 52, regex=FN + r"(?:gm)?strftime\s*\(", filtro=("strftime",),
    ),
    Padrao(
        "filter_sanitize_string", "FILTER_SANITIZE_STRING", "php", "depreciado no 8.1",
        "htmlspecialchars() na saida, ou FILTER_SANITIZE_SPECIAL_CHARS/FILTER_UNSAFE_RAW conforme o uso.",
        "filter_var($x, FILTER_SANITIZE_STRING);", "htmlspecialchars($x, ENT_QUOTES, 'ISO-8859-1');",
        "semi", "alta", 53, regex=r"\bFILTER_SANITIZE_STRING\b",
    ),
    Padrao(
        "e_strict", "constante E_STRICT", "php", "depreciada no 8.4 (E_STRICT nao e mais emitido desde o 8.0)",
        "Remova E_STRICT das mascaras de error_reporting.", "error_reporting(E_ALL & ~E_STRICT);",
        "error_reporting(E_ALL);", "sim", "alta", 54, regex=r"\bE_STRICT\b",
    ),
    Padrao(
        "interpolacao_dolar_chave", "interpolacao \"${var}\" em string", "php", "depreciada no 8.2",
        "Use \"{$var}\".", "echo \"valor ${nome}\";", "echo \"valor {$nome}\";",
        "sim", "media", 55, regex=r"\$\{[A-Za-z_]\w*\}",
    ),
    Padrao(
        "casts_nao_canonicos", "casts (integer)/(boolean)/(double)/(binary)", "php", "depreciados no 8.5",
        "Use (int), (bool), (float), (string).", "$i = (integer) $x;", "$i = (int) $x;",
        "sim", "media", 56, regex=r"\(\s*(?:integer|boolean|double|binary)\s*\)",
    ),
    Padrao(
        "count_null", "count()/sizeof() sobre variavel (pode ser null)", "php",
        "no 8.0 count(null)/count(nao-contavel) levanta TypeError (no 7.4 era warning e devolvia 0/1)",
        "Se a variavel pode ser null/false/escalar: `count($x ?? [])` ou `is_countable($x) ? count($x) : 0`. "
        "Nao troque as que ja sao sempre array (a busca acha TODAS: muitos falsos positivos).",
        "$n = count($linhas);", "$n = is_countable($linhas) ? count($linhas) : 0;",
        "nao", "baixa", 90, regex=FN + r"(?:count|sizeof)\s*\(\s*@?\$", filtro=("count", "sizeof"), ruidoso=True,
    ),
    # ---------------- Laravel 8 -> 12 ----------------
    Padrao(
        "laravel_helpers_globais", "helpers globais array_*/str_* do Laravel (array_get, str_slug, starts_with...)",
        "laravel",
        "removidos do framework no Laravel 6 (so existem com o pacote laravel/helpers). Atencao: o PHP 8.5 criou "
        "array_first()/array_last() NATIVOS com outra assinatura",
        "Use Illuminate\\Support\\Arr e Illuminate\\Support\\Str: array_get -> Arr::get, str_slug -> Str::slug, "
        "starts_with -> Str::startsWith.",
        "$v = array_get($dados, 'a.b'); $s = str_slug($titulo);",
        "$v = Arr::get($dados, 'a.b'); $s = Str::slug($titulo);",
        "sim", "alta", 60,
        regex=FN + r"(?:array_(?:add|collapse|divide|dot|except|first|flatten|forget|get|has|last|only|pluck|"
                   r"prepend|pull|random|set|sort_recursive|sort|where|wrap)|str_(?:after|before|finish|is|limit|"
                   r"plural|random|replace_array|replace_first|replace_last|singular|slug|start)|studly_case|"
                   r"camel_case|snake_case|kebab_case|title_case|starts_with|ends_with)\s*\(",
    ),
    Padrao(
        "laravel_dates_property", "propriedade $dates em Model", "laravel", "REMOVIDA no Laravel 10",
        "Mova para $casts com 'datetime' (ou 'date').", "protected $dates = ['dt_inicio'];",
        "protected $casts = ['dt_inicio' => 'datetime'];", "sim", "alta", 61,
        regex=r"(?:protected|public)\s+\$dates\s*=", filtro=("$dates",),
    ),
    Padrao(
        "laravel_dispatch_now", "dispatchNow()/dispatch_now()", "laravel",
        "depreciado no Laravel 8, REMOVIDO no 9", "Use dispatchSync()/dispatch_sync().",
        "Bus::dispatchNow(new GeraRelatorio($id));", "Bus::dispatchSync(new GeraRelatorio($id));",
        "sim", "alta", 62, regex=r"\bdispatch(?:_now|Now)\s*\(", filtro=("ispatch",),
    ),
    Padrao(
        "passport_routes", "Passport::routes()", "laravel",
        "REMOVIDO no Passport 11 (as rotas passam a ser registradas sozinhas)",
        "Apague a chamada; para customizar, Passport::ignoreRoutes() + rotas proprias.",
        "Passport::routes();", "// rotas do Passport sao registradas automaticamente",
        "sim", "alta", 63, regex=r"Passport::routes\s*\(", filtro=("Passport",),
    ),
    Padrao(
        "doctrine_dbal", "metodos Doctrine DBAL do Laravel (getDoctrineSchemaManager, getDoctrineColumn...)",
        "laravel", "integracao com Doctrine DBAL REMOVIDA no Laravel 11",
        "Use os metodos nativos do Schema Builder (Schema::getColumns, getIndexes, getTables). Em migrations, "
        "->change() precisa repetir TODOS os modificadores da coluna.",
        "$cols = DB::connection()->getDoctrineSchemaManager()->listTableColumns('t');",
        "$cols = Schema::getColumns('t');", "semi", "alta", 64,
        regex=r"getDoctrine(?:SchemaManager|Column|Connection|Driver)\s*\(", filtro=("getDoctrine",),
    ),
    Padrao(
        "carbon_diff_in", "Carbon ->diffIn*()", "laravel",
        "Laravel 12 exige Carbon 3: diffIn* devolve float e COM SINAL (antes int absoluto)",
        "Se o codigo espera inteiro positivo: `(int) abs($a->diffInDays($b))`, ou inverta a ordem; reveja "
        "comparacoes e divisoes.", "$dias = $inicio->diffInDays($fim);", "$dias = (int) abs($inicio->diffInDays($fim));",
        "semi", "media", 65, regex=r"->diffIn[A-Z]\w*\s*\(", filtro=("diffIn",),
    ),
    Padrao(
        "request_get", "$request->get() (Symfony Request::get)", "laravel",
        "Laravel 12 roda sobre Symfony 7.x, que marca Request::get() como depreciado (confira o UPGRADE da versao "
        "instalada do symfony/http-foundation)",
        "Prefira $request->input('x') (body+query) ou $request->query('x')/$request->route('x').",
        "$id = $request->get('id');", "$id = $request->input('id');",
        "sim", "baixa", 91, regex=r"\$request->get\s*\(|\brequest\(\)->get\s*\(", filtro=("->get",), ruidoso=True,
    ),
)

PADROES: dict[str, Padrao] = {p.nome: p for p in CATALOGO}
_COMPILADAS: dict[str, re.Pattern[str]] = {p.nome: re.compile(p.regex, p.flags) for p in CATALOGO if p.regex}


def ocorrencias(padrao: Padrao, texto: str) -> list[int]:
    """Offsets (inicio) das ocorrencias do padrao no texto."""
    if padrao.filtro and not any(f in texto for f in padrao.filtro):
        return []
    if padrao.detector is not None:
        return padrao.detector(texto)
    return [m.start() for m in _COMPILADAS[padrao.nome].finditer(texto)]


def padroes_para(nome: str, incluir_ruidosos: bool = False) -> list[Padrao]:
    """`todos` -> catalogo (sem os ruidosos, a menos que pedidos); senao o padrao pelo nome."""
    if nome == "todos":
        return [p for p in sorted(CATALOGO, key=lambda p: p.prioridade) if incluir_ruidosos or not p.ruidoso]
    if nome not in PADROES:
        from servidor.seguranca import ErroFerramenta
        raise ErroFerramenta("padrao_desconhecido", f"padrao {nome!r}; validos: todos, {', '.join(PADROES)}")
    return [PADROES[nome]]
