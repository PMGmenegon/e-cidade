"""Mascara de erro na COMPARACAO: file/line/trace e caminhos absolutos nao viram DIVERGE falso."""
from regressao.laravel.caso import CasoHttp, Resposta, _veredito
from regressao.laravel.mascara import MARCA, normaliza_erro
from regressao.nucleo.veredito import Veredito

ERRO_54 = {
    "message": "Call to undefined method Query\\Builder::all()",
    "exception": "BadMethodCallException",
    "file": "/var/www/html/vendor/laravel/framework/src/Illuminate/Database/Query/Builder.php",
    "line": 2445,
    "trace": [{"file": "/var/www/html/app/Http/Controllers/X.php", "line": 12, "function": "all"}],
}


def test_file_line_trace_de_erro_sao_mascarados_mas_exception_e_message_ficam():
    n = normaliza_erro(ERRO_54)
    assert n["file"] == MARCA and n["line"] == MARCA and n["trace"] == MARCA
    assert n["exception"] == "BadMethodCallException" and "undefined method" in n["message"]
    assert ERRO_54["line"] == 2445  # entrada intacta


def test_stacktrace_aninhado_e_alias_stack_trace():
    n = normaliza_erro({"data": {"error": {"message": "x", "stacktrace": ["a"], "stack_trace": "b", "file": "/a", "line": 1}}})
    e = n["data"]["error"]
    assert e["stacktrace"] == MARCA and e["stack_trace"] == MARCA and e["file"] == MARCA


def test_campo_de_negocio_line_ou_file_sem_cara_de_erro_nao_e_mascarado():
    assert normaliza_erro({"id": 1, "line": 3, "file": "a.txt"}) == {"id": 1, "line": 3, "file": "a.txt"}


def test_caminhos_absolutos_de_vendor_e_app_em_texto_sao_normalizados():
    a = normaliza_erro({"message": "Class X not found in /var/www/html/vendor/a/b.php:41 on line 41"})
    b = normaliza_erro({"message": "Class X not found in /srv/novo/vendor/a/b.php:99 on line 99"})
    assert a == b
    assert "<caminho>" in a["message"] and "/var/www" not in a["message"]
    assert normaliza_erro("em /var/www/html/app/Foo.php") == "em <caminho>"


def test_texto_que_nao_e_caminho_fica_intacto():
    assert normaliza_erro({"message": "Token invalido", "n": [1, "a/b"]}) == {"message": "Token invalido", "n": [1, "a/b"]}


def _caso():
    return CasoHttp(id="rota:GET:/x", metodo="GET", caminho="/x", corpo=None)


def _reg(json):
    return {"id": "rota:GET:/x", "status": 500, "cabecalhos": {}, "json": json, "texto": "", "tipos": {},
            "sql_negocio": [], "tabelas": {}}


def test_veredito_ignora_diferenca_so_de_file_line_trace():
    novo = dict(ERRO_54, file="/srv/l12/vendor/laravel/framework/Builder.php", line=77,
                trace=[{"file": "/srv/l12/app/Z.php", "line": 3, "function": "all"}])
    r = Resposta(500, {}, novo, [])
    c = _veredito(_caso(), _reg(ERRO_54), r)
    assert c.veredito != Veredito.DIVERGE


def test_veredito_continua_divergindo_se_a_excecao_ou_a_mensagem_mudam():
    novo = dict(ERRO_54, exception="ErrorException", message="outra coisa")
    c = _veredito(_caso(), _reg(ERRO_54), Resposta(500, {}, novo, []))
    assert c.veredito == Veredito.DIVERGE and "json" in c.detalhe


def test_registro_bruto_nao_e_alterado_pela_comparacao():
    reg = _reg(ERRO_54)
    _veredito(_caso(), reg, Resposta(500, {}, ERRO_54, []))
    assert reg["json"]["line"] == 2445 and reg["json"]["file"].startswith("/var/www/html")
