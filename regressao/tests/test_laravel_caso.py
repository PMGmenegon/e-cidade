import base64
import contextlib
import http.server
import json
import socket
import threading
from pathlib import Path

import pytest

from regressao.laravel import caso as mod
from regressao.laravel import token as token_mod
from regressao.laravel.caso import CasoHttp, carrega_casos, comparar, gravar
from regressao.nucleo.banco import ErroAmbienteBanco
from regressao.nucleo.veredito import Veredito

REAL_CASOS = Path(mod.__file__).resolve().parent / "casos"


def _jwt(jti: str) -> str:
    def b(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b({'alg': 'RS256'})}.{b({'jti': jti})}.assinatura"


class Fake:
    """Servidor HTTP falso + estado compartilhado com o banco falso."""

    def __init__(self):
        self.v = 1
        self.pedidos: list[tuple[str, str, str | None]] = []
        self.log: list[str] = []
        self.n_token = 0
        self.statements = ["insert into foo(a,b) values (1, '2026-11-14 10:20:30.123')"]

    def linha(self, sql: str):
        self.log.append(f"2026-11-14 10:20:30.123 -03 [9] LOG:  instrucao: {sql}")


@pytest.fixture
def fake(monkeypatch, tmp_path):
    f = Fake()

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _envia(self, status, corpo=b"", extra=None):
            self.send_response(status)
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, status, obj, extra=None):
            h = {"Content-Type": "application/json", "Set-Cookie": "sessao=segredo123",
                 "X-Debug": "interno"}
            h.update(extra or {})
            self._envia(status, json.dumps(obj).encode(), h)

        def _trata(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
            f.pedidos.append((self.command, self.path, self.headers.get("Authorization")))
            if self.path == "/v4/oauth/token":
                if self.command == "GET":
                    return self._json(405, {"error": "metodo"})
                f.n_token += 1
                return self._json(200, {"token_type": "Bearer", "expires_in": 1000 + f.n_token,
                                        "access_token": _jwt(f"jti{f.n_token}"),
                                        "refresh_token": "r" * 20})
            if self.path == "/protegido":
                if self.headers.get("Authorization") != "Bearer VALIDO":
                    return self._json(401, {"message": "Unauthenticated."})
                return self._json(200, {"v": f.v})
            if self.path == "/vazio":
                return self._envia(200)
            if self.path == "/quebra":
                return self._json(500, {"message": "Server Error"})
            if self.path == "/escreve":
                for s in f.statements:
                    f.linha(s)
                f.linha("insert into db_acount(x) values (1)")
                f.linha("select * from foo")
                return self._json(200, {"ok": True})
            return self._json(404, {"message": "nao existe"})

        do_GET = do_POST = do_PUT = do_DELETE = _trata

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    f.url = f"http://127.0.0.1:{srv.server_address[1]}"
    f.chamadas = []
    f.psql = []
    f.hashes = {}

    sha = tmp_path / "dump.sha256"
    sha.write_text("abc123\n")
    monkeypatch.setattr(mod, "ARQ_SHA256", sha)
    monkeypatch.setattr(mod, "restaura_dump", lambda d: f.chamadas.append("restaura"))
    monkeypatch.setattr(mod, "confere_baseline", lambda d: None)
    monkeypatch.setattr(mod, "hash_tabelas",
                        lambda ts: {t: f.hashes.get(t, "h0") for t in ts})
    monkeypatch.setattr(mod, "com_log_statement", contextlib.nullcontext)

    def psql(sql, db="ecidade"):
        f.psql.append(sql)
        if "REGRESSAO_" in sql:
            f.linha(sql)
        return ""
    monkeypatch.setattr(mod, "_psql", psql)
    monkeypatch.setattr(mod, "_logs_banco", lambda desde: "\n".join(f.log).encode())
    monkeypatch.setattr(mod, "obtem_token", lambda base_url, *a, **k: "VALIDO")
    monkeypatch.setattr(mod, "_segredo_cliente", lambda: "segredo-de-teste")
    monkeypatch.setattr(token_mod, "_docker", lambda *a, **k: (_ for _ in ()).throw(
        ErroAmbienteBanco("sem docker (teste)")))
    f.baseline = tmp_path / "baseline"
    yield f
    srv.shutdown()


def _caso(id, caminho="/protegido", metodo="GET", **kw):
    kw.setdefault("corpo", None)
    return CasoHttp(id=id, metodo=metodo, caminho=caminho, **kw)


def test_gravar_e_comparar_mesma_resposta_e_identico(fake):
    casos = [_caso("protegido"),
             _caso("escreve", "/escreve", "POST", corpo={"a": 1}, tabelas=["foo"],
                   espera_escrita=True)]
    gravar(casos, fake.url, fake.baseline)
    res = comparar(casos, fake.url, fake.baseline)
    assert [(c.id, c.veredito) for c in res] == [("protegido", Veredito.IDENTICO),
                                                 ("escreve", Veredito.IDENTICO)]
    assert fake.chamadas == ["restaura", "restaura"]
    reg = json.loads((fake.baseline / "escreve.json").read_text(encoding="utf-8"))
    assert reg["sql_negocio"] == ["insert into foo(a,b) values (1, '<TS>')"]
    assert reg["tabelas"] == {"foo": "h0"}
    meta = json.loads((fake.baseline / "_meta.json").read_text(encoding="utf-8"))
    assert meta["dump_sha256"] == "abc123" and meta["n_casos"] == 2


def test_comparar_json_diferente_diverge_com_diff(fake):
    casos = [_caso("protegido")]
    gravar(casos, fake.url, fake.baseline)
    fake.v = 2
    res = comparar(casos, fake.url, fake.baseline)
    assert res[0].veredito == Veredito.DIVERGE
    assert '-    "v": 1' in res[0].diff and '+    "v": 2' in res[0].diff


def test_comparar_sql_ou_hash_diferente_diverge(fake):
    casos = [_caso("escreve", "/escreve", "POST", corpo={}, tabelas=["foo"])]
    gravar(casos, fake.url, fake.baseline)
    fake.hashes["foo"] = "h1"
    res = comparar(casos, fake.url, fake.baseline)
    assert res[0].veredito == Veredito.DIVERGE and "h1" in res[0].diff
    fake.hashes.clear()
    fake.statements = ["insert into foo(a,b) values (2, 'x')"]
    res = comparar(casos, fake.url, fake.baseline)
    assert res[0].veredito == Veredito.DIVERGE and "values (2" in res[0].diff


def test_sem_token_e_401_gravado_e_comparado(fake):
    casos = [_caso("sem-token", token="")]
    gravar(casos, fake.url, fake.baseline)
    reg = json.loads((fake.baseline / "sem-token.json").read_text(encoding="utf-8"))
    assert reg["status"] == 401
    assert comparar(casos, fake.url, fake.baseline)[0].veredito == Veredito.IDENTICO
    assert all(p[2] is None for p in fake.pedidos if p[1] == "/protegido")


def test_token_invalido_e_401(fake):
    casos = [_caso("invalido", token="lixo")]
    gravar(casos, fake.url, fake.baseline)
    reg = json.loads((fake.baseline / "invalido.json").read_text(encoding="utf-8"))
    assert reg["status"] == 401
    assert comparar(casos, fake.url, fake.baseline)[0].veredito == Veredito.IDENTICO
    assert ("GET", "/protegido", "Bearer lixo") in fake.pedidos


def test_baseline_ausente_e_erro_ambiente(fake):
    res = comparar([_caso("x")], fake.url, fake.baseline)
    assert [c.veredito for c in res] == [Veredito.ERRO_AMBIENTE]
    assert res[0].id == "x" and "baseline" in res[0].detalhe.lower()
    assert fake.chamadas == []
    # arquivo de um caso ausente com meta presente
    gravar([_caso("a")], fake.url, fake.baseline)
    res = comparar([_caso("a"), _caso("b")], fake.url, fake.baseline)
    assert [(c.id, c.veredito) for c in res] == [("b", Veredito.ERRO_AMBIENTE)]
    assert fake.chamadas == ["restaura"]  # so o do gravar


def test_resposta_vazia_nos_dois_lados_e_inconclusiva(fake):
    casos = [_caso("vazio", "/vazio")]
    gravar(casos, fake.url, fake.baseline)
    assert comparar(casos, fake.url, fake.baseline)[0].veredito == Veredito.INCONCLUSIVO


def test_5xx_nos_dois_lados_e_escrita_esperada_sem_escrita_sao_inconclusivos(fake):
    casos = [_caso("quebra", "/quebra"),
             _caso("nada", "/protegido", "GET", espera_escrita=True)]
    gravar(casos, fake.url, fake.baseline)
    res = comparar(casos, fake.url, fake.baseline)
    assert [c.veredito for c in res] == [Veredito.INCONCLUSIVO, Veredito.INCONCLUSIVO]


def test_comparar_recusa_baseline_de_outro_dump(fake):
    casos = [_caso("protegido")]
    gravar(casos, fake.url, fake.baseline)
    (fake.baseline / "_meta.json").write_text(
        json.dumps({"dump_sha256": "outro", "n_casos": 1}), encoding="utf-8")
    fake.chamadas.clear()
    n = len(fake.pedidos)
    res = comparar(casos, fake.url, fake.baseline)
    assert len(res) == 1 and res[0].veredito == Veredito.ERRO_AMBIENTE
    assert "dump" in res[0].detalhe.lower()
    assert fake.chamadas == []
    assert not [p for p in fake.pedidos[n:] if p[1] == "/protegido"]


def test_laravel_fora_do_ar_nao_restaura_banco(fake):
    gravar([_caso("protegido")], fake.url, fake.baseline)
    fake.chamadas.clear()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    morta = f"http://127.0.0.1:{s.getsockname()[1]}"
    s.close()
    res = comparar([_caso("protegido")], morta, fake.baseline)
    assert len(res) == 1 and res[0].veredito == Veredito.ERRO_AMBIENTE
    assert res[0].id == "laravel:boot"
    assert fake.chamadas == []


def test_token_nunca_e_gravado_na_baseline(fake):
    casos = [_caso("token-valido", "/v4/oauth/token", "POST", autenticado=False, form=True,
                   corpo={"grant_type": "password", "client_secret": "${CLIENT_SECRET}"},
                   campos_volateis=["access_token", "refresh_token", "expires_in"]),
             _caso("protegido")]
    gravar(casos, fake.url, fake.baseline)
    texto = "".join(p.read_text(encoding="utf-8") for p in fake.baseline.glob("*.json"))
    assert "eyJ" not in texto and "jti1" not in texto and "VALIDO" not in texto
    assert "segredo-de-teste" not in texto and "rrrrrrrr" not in texto
    reg = json.loads((fake.baseline / "token-valido.json").read_text(encoding="utf-8"))
    assert reg["json"]["access_token"] == "<X>" and reg["json"]["token_type"] == "Bearer"
    assert reg["tipos"]["access_token"] == ["str"] and reg["tipos"]["expires_in"] == ["int"]
    # outro token / outro expires_in na comparacao: ainda IDENTICO
    assert comparar(casos, fake.url, fake.baseline)[0].veredito == Veredito.IDENTICO


def test_estrutura_do_token_diferente_diverge(fake):
    casos = [_caso("tok", "/v4/oauth/token", "POST", autenticado=False, form=True,
                   campos_volateis=["access_token", "expires_in"])]
    gravar(casos, fake.url, fake.baseline)
    reg = json.loads((fake.baseline / "tok.json").read_text(encoding="utf-8"))
    reg["tipos"]["expires_in"] = ["str"]
    reg.pop("sha256")
    mod._grava_registro(fake.baseline / "tok.json", reg)
    assert comparar(casos, fake.url, fake.baseline)[0].veredito == Veredito.DIVERGE


def test_baseline_adulterada_e_erro_ambiente(fake):
    gravar([_caso("protegido")], fake.url, fake.baseline)
    p = fake.baseline / "protegido.json"
    p.write_text(p.read_text(encoding="utf-8").replace('"v": 1', '"v": 9'), encoding="utf-8")
    assert comparar([_caso("protegido")], fake.url, fake.baseline)[0].veredito == Veredito.ERRO_AMBIENTE


def test_cabecalhos_fora_da_lista_nao_sao_gravados(fake):
    gravar([_caso("protegido")], fake.url, fake.baseline)
    reg = json.loads((fake.baseline / "protegido.json").read_text(encoding="utf-8"))
    assert set(reg["cabecalhos"]) <= {"content-type", "www-authenticate", "cache-control"}
    assert "content-type" in reg["cabecalhos"]
    assert "segredo123" not in json.dumps(reg)


def test_token_expirado_forcado_por_sql_no_caso(fake):
    caso = _caso("expirado", token="@novo",
                 sql_antes=["update oauth_access_tokens set expires_at = now() where id = '{jti}'"])
    gravar([caso], fake.url, fake.baseline)
    assert any("where id = 'jti1'" in s for s in fake.psql)
    assert any(p[2] and p[2].startswith("Bearer eyJ") for p in fake.pedidos if p[1] == "/protegido")


def test_ordem_dos_casos_e_fixa(fake, tmp_path):
    d = tmp_path / "casos"
    d.mkdir()
    (d / "b.yml").write_text(
        "- id: b1\n  metodo: GET\n  caminho: /protegido\n- id: b2\n  metodo: GET\n  caminho: /vazio\n",
        encoding="utf-8")
    (d / "a.yml").write_text(
        "- id: a1\n  metodo: GET\n  caminho: /quebra\n- id: a2\n  metodo: get\n  caminho: /protegido\n"
        "  token: ''\n", encoding="utf-8")
    casos = carrega_casos(d)
    assert [c.id for c in casos] == ["a1", "a2", "b1", "b2"]
    assert casos[1].metodo == "GET" and casos[1].token == ""
    gravar(casos, fake.url, fake.baseline)
    ordem_gravar = [p[1] for p in fake.pedidos if p[1] != "/v4/oauth/token"]
    fake.pedidos.clear()
    comparar(casos, fake.url, fake.baseline)
    ordem_comparar = [p[1] for p in fake.pedidos if p[1] != "/v4/oauth/token"]
    assert ordem_gravar == ordem_comparar == ["/quebra", "/protegido", "/protegido", "/vazio"]


def test_carrega_auth_yml_real_tem_os_casos_exigidos():
    casos = {c.id: c for c in carrega_casos(REAL_CASOS)}
    for obrigatorio in ("auth-token-valido", "auth-client-secret-errado", "auth-senha-errada",
                        "auth-usuario-inexistente", "auth-sem-grant-type", "auth-sem-token",
                        "auth-token-invalido", "auth-token-expirado", "auth-refresh-token"):
        assert obrigatorio in casos, obrigatorio
    assert casos["auth-token-valido"].campos_volateis == ["access_token", "refresh_token", "expires_in"]
    assert casos["auth-sem-token"].token == ""
