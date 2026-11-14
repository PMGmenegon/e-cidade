import copy
import http.server
import json
import threading
from pathlib import Path

import pytest

from regressao.laravel import rotas, token
from regressao.laravel.mascara import mascara_json
from regressao.nucleo.veredito import Veredito

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _sem_docker(monkeypatch):
    monkeypatch.setattr(token, "_cauda_php_errors", lambda linhas=5: "")


def test_mascara_troca_volateis_e_ordena_chaves():
    obj = {"z": 1, "a": {"criado_em": "2024-01-01", "b": 2, "id": 7}, "m": [3, 1]}
    r = mascara_json(obj, ["a.criado_em", "a.id", "nao.existe"])
    assert r == {"a": {"b": 2, "criado_em": "<X>", "id": "<X>"}, "m": [3, 1], "z": 1}
    assert list(r) == ["a", "m", "z"]
    assert list(r["a"]) == ["b", "criado_em", "id"]


def test_mascara_lista_com_asterisco():
    obj = {"itens": [{"id": 1, "n": "a"}, {"id": 2, "n": "b"}], "total": 2}
    r = mascara_json(obj, ["itens.*.id"])
    assert r == {"itens": [{"id": "<X>", "n": "a"}, {"id": "<X>", "n": "b"}], "total": 2}
    assert mascara_json([{"t": 1}, {"t": 2}], ["*.t"]) == [{"t": "<X>"}, {"t": "<X>"}]


def test_mascara_nao_muta_a_entrada():
    obj = {"b": [{"id": 1}], "a": {"id": 2}}
    copia = copy.deepcopy(obj)
    mascara_json(obj, ["b.*.id", "a.id"])
    assert obj == copia
    assert list(obj) == ["b", "a"]


def test_inventario_parseia_tabela_route_list():
    texto = (FIXTURES / "route_list.txt").read_text(encoding="utf-8")
    lista = rotas.parseia_route_list(texto)
    assert len(lista) == 12
    r0 = lista[0]
    assert (r0.metodo, r0.caminho, r0.middleware, r0.origem) == (
        "GET|HEAD", "/rest/v1/enderecopessoa/{cgm}", ["AuthSim"], "rest")
    assert r0.controller.endswith("PessoasController@pesquisaEndereco")
    assert {r.origem for r in lista} == {"rest", "laravel"}
    clos = [r for r in lista if r.controller == "Closure"][0]
    assert clos.middleware == ["api", "auth:api"] and clos.caminho.startswith("/v4/api/")
    assert [r for r in lista if "assinantes" in r.caminho][0].middleware == []


def test_inventario_silex_varre_providers(tmp_path):
    prov = tmp_path / "ecidade/api/V1/Providers/Controller"
    prov.mkdir(parents=True)
    (tmp_path / "ecidade/api/V1/APIServiceProvider.php").write_text(
        '$app->mount($prefix . "/tributario", new TributarioControllerProvider());', encoding="utf-8")
    (prov / "TributarioControllerProvider.php").write_text(
        "$controllers->post('recibo', \"recibo.controller:geraRecibo\");\n"
        "$controllers->get('/x/{id}', \"x:y\")->assert('id', '\\d+');", encoding="utf-8")
    lista = rotas.varre_silex(tmp_path)
    assert [(r.metodo, r.caminho, r.controller, r.origem) for r in lista] == [
        ("POST", "/api/v1/tributario/recibo", "recibo.controller:geraRecibo", "silex"),
        ("GET", "/api/v1/tributario/x/{id}", "x:y", "silex"),
    ]


def test_grava_tsv_deterministico_e_contagem(tmp_path):
    texto = (FIXTURES / "route_list.txt").read_text(encoding="utf-8")
    lista = rotas.parseia_route_list(texto)
    a, b = tmp_path / "a.tsv", tmp_path / "b.tsv"
    rotas.grava_tsv(lista, a)
    rotas.grava_tsv(list(reversed(lista)), b)
    assert a.read_bytes() == b.read_bytes()
    assert rotas.contagem(lista) == {"laravel": 9, "rest": 3, "silex": 0}


class _Servidor:
    def __init__(self, status, corpo):
        corpo_b = json.dumps(corpo).encode()
        self.pedidos = []
        pedidos = self.pedidos

        class H(http.server.BaseHTTPRequestHandler):
            def _r(self):
                n = int(self.headers.get("Content-Length") or 0)
                pedidos.append((self.command, self.path, self.rfile.read(n).decode()))
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo_b)))
                self.end_headers()
                self.wfile.write(corpo_b)
            do_GET = do_POST = _r

            def log_message(self, *a):
                pass

        self.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fecha(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def servidor_factory():
    abertos = []

    def f(status, corpo):
        s = _Servidor(status, corpo)
        abertos.append(s)
        return s
    yield f
    for s in abertos:
        s.fecha()


def test_laravel_que_nao_sobe_e_um_so_erro_ambiente(servidor_factory):
    s = servidor_factory(500, {"message": "boom"})
    r = token.laravel_sobe(s.url)
    assert r is not None and r.veredito == Veredito.ERRO_AMBIENTE
    assert r.area == "laravel"


def test_laravel_fora_do_ar_e_erro_ambiente():
    r = token.laravel_sobe("http://127.0.0.1:9")
    assert r is not None and r.veredito == Veredito.ERRO_AMBIENTE


def test_laravel_que_sobe_devolve_none(servidor_factory):
    s = servidor_factory(405, {"message": "Method Not Allowed"})
    assert token.laravel_sobe(s.url) is None


def test_obtem_token_devolve_access_token(servidor_factory, monkeypatch):
    monkeypatch.setattr(token, "_segredo_cliente", lambda: "SEGREDO-XYZ")
    s = servidor_factory(200, {"access_token": "tok123", "token_type": "Bearer"})
    assert token.obtem_token(s.url) == "tok123"
    metodo, caminho, corpo = s.pedidos[0]
    assert (metodo, caminho) == ("POST", "/v4/oauth/token")
    assert "grant_type=password" in corpo and "client_id=9999999" in corpo


def test_obtem_token_nao_vaza_o_segredo_na_excecao(servidor_factory, monkeypatch):
    monkeypatch.setattr(token, "_segredo_cliente", lambda: "SEGREDO-XYZ")
    s = servidor_factory(401, {"error": "invalid_client", "echo": "SEGREDO-XYZ"})
    with pytest.raises(token.ErroToken) as e:
        token.obtem_token(s.url, senha="SENHA-ABC")
    msg = str(e.value) + repr(e.value)
    assert "SEGREDO-XYZ" not in msg and "SENHA-ABC" not in msg
    assert "401" in msg