"""Task 11b: arquivo gerado por conteudo, console, e-mail (SMTP de teste) e stub PIX."""
import json
import smtplib
from email.message import EmailMessage
from types import SimpleNamespace

import pytest
import requests

from regressao.laravel import caso as mod_caso
from regressao.laravel import integracao
from regressao.laravel.caso import CasoHttp
from regressao.laravel.stubs.pix_stub import PixStub
from regressao.laravel.stubs.smtp_stub import SmtpStub
from regressao.nucleo.veredito import Veredito


# ---------------------------------------------------------------- stub PIX

def test_stub_pix_registra_chamada_recebida_e_redige_segredos():
    pix = PixStub().inicia()
    try:
        tok = requests.post(pix.url + "/oauth/token", data="grant_type=client_credentials&client_secret=SEGREDO123",
                            headers={"Authorization": "Basic abc"}, timeout=5)
        qr = requests.post(pix.url + "/pix-bb/v1/arrecadacao-qrcodes?gw-dev-app-key=K", json={"valor": "10.00"}, timeout=5)
    finally:
        pix.para()
    assert tok.status_code == 200 and tok.json()["access_token"] == "stub-token"
    assert qr.status_code == 201 and qr.json()["estadoSolicitacao"] == "ATIVA"
    assert [(c["metodo"], c["caminho"]) for c in pix.chamadas] == [
        ("POST", "/oauth/token"), ("POST", "/pix-bb/v1/arrecadacao-qrcodes")]
    assert "SEGREDO123" not in json.dumps(pix.chamadas) and "<redigido>" in pix.chamadas[0]["corpo"]
    assert pix.chamadas[0]["tem_autorizacao"] is True
    assert json.loads(pix.chamadas[1]["corpo"]) == {"valor": "10.00"}


# ---------------------------------------------------------------- SMTP + e-mail

def _envia(porta: int, assunto="Ola", corpo="Texto do e-mail", para="a@x.com"):
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = assunto, "sistema@x.com", para
    m.set_content(corpo)
    m.add_alternative(f"<p>{corpo}</p>", subtype="html")
    with smtplib.SMTP("127.0.0.1", porta, timeout=5) as s:
        s.send_message(m)
    return m


def test_smtp_stub_captura_a_mensagem_com_remetente_e_destinatarios():
    smtp = SmtpStub().inicia()
    try:
        _envia(smtp.porta, "Protocolo 1", "Seu protocolo", "a@x.com")
    finally:
        smtp.para()
    assert len(smtp.mensagens) == 1
    msg = smtp.mensagens[0]
    assert msg["de"] == "sistema@x.com" and msg["para"] == ["a@x.com"]
    assert b"Subject: Protocolo 1" in msg["dados"] and b"Seu protocolo" in msg["dados"]


def test_email_normaliza_date_e_message_id_e_fronteiras():
    smtp = SmtpStub().inicia()
    try:
        _envia(smtp.porta)
        _envia(smtp.porta)  # Date/Message-ID/boundary diferentes por construcao
    finally:
        smtp.para()
    a, b = (m["dados"] for m in smtp.mensagens)
    assert a != b
    c = integracao.compara_email(a, b, "email:x")
    assert c.veredito == Veredito.IDENTICO
    n = integracao.normaliza_email(a)
    assert "date" not in n["cabecalhos"] and "message-id" not in n["cabecalhos"]
    assert "<BOUNDARY>" in n["cabecalhos"]["content-type"]
    assert [p["tipo"] for p in n["partes"]] == ["text/plain", "text/html"]


def test_email_diverge_se_assunto_destinatario_ou_corpo_mudam():
    smtp = SmtpStub().inicia()
    try:
        _envia(smtp.porta, "A", "corpo 1", "a@x.com")
        _envia(smtp.porta, "B", "corpo 1", "a@x.com")
        _envia(smtp.porta, "A", "corpo 2", "a@x.com")
        _envia(smtp.porta, "A", "corpo 1", "outro@x.com")
    finally:
        smtp.para()
    base, assunto, corpo, dest = (m["dados"] for m in smtp.mensagens)
    assert integracao.compara_email(base, assunto).veredito == Veredito.DIVERGE
    assert integracao.compara_email(base, corpo).veredito == Veredito.DIVERGE
    assert integracao.compara_email(base, dest).veredito == Veredito.DIVERGE


def test_com_stubs_sobe_e_para_os_dois_servidores_mesmo_com_excecao():
    portas = None
    try:
        with integracao.com_stubs() as (smtp, pix):
            portas = (smtp.porta, pix.porta)
            assert requests.post(pix.url + "/oauth/token", timeout=5).status_code == 200
            raise RuntimeError("falha no meio")
    except RuntimeError:
        pass
    for porta in portas:
        try:
            requests.get(f"http://127.0.0.1:{porta}/", timeout=1)
            parou = False
        except requests.RequestException:
            parou = True
        assert parou


# ---------------------------------------------------------------- arquivo por conteudo

def test_valor_json_caminho_pontilhado():
    assert integracao.valor_json({"data": {"path": "tmp/a.pdf"}}, "data.path") == "tmp/a.pdf"
    assert integracao.valor_json({"data": 1}, "data.path") is None
    assert integracao.valor_json([], "a") is None


def test_segue_arquivo_csv_compara_o_texto_e_nao_os_bytes():
    resp = SimpleNamespace(content=b"Recurso;Descricao\n1;Livre\n", status_code=200,
                           headers={"content-type": "text/csv; charset=ISO-8859-1"})
    chamadas = []
    texto = integracao.segue_arquivo("http://h:8080/", "tmp/de-para.csv", {"Authorization": "Bearer x"},
                                     get=lambda url, **k: chamadas.append(url) or resp)
    assert chamadas == ["http://h:8080/tmp/de-para.csv"]
    assert texto.startswith("[arquivo csv status=200 ct=text/csv]\n") and "Recurso" in texto and "Livre" in texto


def test_segue_arquivo_pdf_extrai_texto():
    from pathlib import Path
    pdf = (Path(__file__).parent / "fixtures" / "relatorio_a.pdf").read_bytes()
    resp = SimpleNamespace(content=pdf, status_code=200, headers={"content-type": "application/pdf"})
    texto = integracao.segue_arquivo("http://h", "tmp/x.pdf", {}, get=lambda *a, **k: resp)
    assert texto.startswith("[arquivo pdf status=200 ct=application/pdf]\n=== pagina 1 ===")


def test_segue_arquivo_ausente_na_resposta():
    assert integracao.segue_arquivo("http://h", None, {}) == "[arquivo ausente na resposta]"


class _Resp:
    def __init__(self, dados, status=200):
        self._d, self.status_code, self.headers = dados, status, {"content-type": "application/json"}
        self.text = json.dumps(dados)

    def json(self):
        return self._d


def test_executa_com_arquivo_guarda_o_conteudo_no_texto(monkeypatch):
    monkeypatch.setattr(mod_caso.requests, "request", lambda *a, **k: _Resp({"data": {"path": "tmp/r_123.pdf"}}))
    monkeypatch.setattr(integracao, "segue_arquivo", lambda base, rel, h, get=None: f"[arquivo pdf]\nconteudo de {rel}")
    c = CasoHttp(id="rota:POST:/x", metodo="POST", caminho="/x", corpo={}, arquivo="data.path",
                 campos_volateis=["data.path"])
    r = mod_caso.executa(c, "http://h:8080", "tok", banco=False)
    assert r.texto == "[arquivo pdf]\nconteudo de tmp/r_123.pdf"
    assert r.json == {"data": {"path": "<X>"}}  # o nome do arquivo (timestamp) e mascarado


# ---------------------------------------------------------------- console

def test_normaliza_saida_console_ansi_caminhos_e_modo_nomes():
    bruto = "\x1b[32mLaravel Framework 5.4.36\x1b[0m em /var/www/html/vendor/x.php:12  \n"
    assert integracao.normaliza_saida_console(bruto) == "Laravel Framework 5.4.36 em <caminho>\n"
    lista = "migrate   Run the migrations\nclear-compiled  Remove\n  \nmigrate   dup\n"
    assert integracao.normaliza_saida_console(lista, "nomes") == "clear-compiled\nmigrate\n"


def test_roda_console_usa_o_container_do_ambiente(monkeypatch):
    monkeypatch.setenv("REGRESSAO_LARAVEL_CONSOLE_CONTAINER", "lab12")
    vistos = []

    def fake(cmd):
        vistos.append(cmd)
        return SimpleNamespace(returncode=0, stdout=b"ok\n", stderr=b"")
    assert integracao.roda_console(["list", "--raw"], runner=fake) == (0, "ok\n")
    assert vistos[0][:5] == ["docker", "exec", "-w", "/var/www/html", "lab12"] and vistos[0][-3:] == ["artisan", "list", "--raw"]


def test_executa_console_devolve_codigo_e_saida_normalizada(monkeypatch):
    monkeypatch.setattr(integracao, "roda_console", lambda args, modo=None, runner=None: (0, f"saida de {args} {modo}\n"))
    c = CasoHttp(id="console-env", metodo="CONSOLE", caminho="artisan", corpo=None, console=["env"], console_modo="nomes")
    r = mod_caso.executa(c, "http://h:8080", "tok", banco=False)
    assert r.status == 0 and r.json is None and r.texto == "saida de ['env'] nomes\n"


def test_console_que_nao_carrega_vira_codigo_nao_zero_e_diverge_da_baseline():
    base = {"status": 0, "cabecalhos": {}, "json": None, "texto": "ok\n", "tipos": {}, "sql_negocio": [], "tabelas": {}}
    c = CasoHttp(id="console-env", metodo="CONSOLE", caminho="artisan", corpo=None, console=["env"])
    r = mod_caso.Resposta(1, {}, None, [], texto="PHP Fatal error: Class not found\n")
    assert mod_caso._veredito(c, {"id": "x", **base}, r).veredito == Veredito.DIVERGE


# ---------------------------------------------------------------- gravar --apenas-novos

def _prepara_baseline(tmp_path, monkeypatch, antigos=("a", "b")):
    for i in antigos:
        mod_caso._grava_registro(tmp_path / mod_caso.nome_arquivo(i), {"id": i, "status": 200})
    mod_caso._grava_meta(tmp_path, {"dump_sha256": "SHA", "ids": list(antigos), "n_casos": len(antigos)})
    monkeypatch.setattr(mod_caso, "laravel_sobe", lambda url: None)
    monkeypatch.setattr(mod_caso, "confere_baseline", lambda d: None)
    monkeypatch.setattr(mod_caso, "_sha_dump_atual", lambda: "SHA")
    monkeypatch.setattr(mod_caso, "_commit", lambda: "c0ffee")


def _c(i):
    return CasoHttp(id=i, metodo="GET", caminho="/" + i, corpo=None)


def test_gravar_novos_acrescenta_so_o_que_nao_tem_registro_e_nao_toca_nos_antigos(tmp_path, monkeypatch):
    _prepara_baseline(tmp_path, monkeypatch)
    antes = {p.name: p.read_bytes() for p in tmp_path.glob("[!_]*.json")}
    rodados = []

    def fake(casos, url, erros=None, info=None, restaurar=True):
        rodados.extend(c.id for c in casos)
        return {c.id: mod_caso.Resposta(200, {}, {"ok": 1}, []) for c in casos}
    monkeypatch.setattr(mod_caso, "_roda", fake)
    assert mod_caso.gravar_novos([_c("a"), _c("n1"), _c("b"), _c("n2")], "http://h", tmp_path) == ["n1", "n2"]
    assert rodados == ["n1", "n2"]
    for nome, conteudo in antes.items():
        assert (tmp_path / nome).read_bytes() == conteudo
    meta = json.loads((tmp_path / "_meta.json").read_text())
    assert meta["ids"] == ["a", "n1", "b", "n2"] and meta["n_casos"] == 4 and meta["novos_gravados"] == ["n1", "n2"]
    assert (tmp_path / mod_caso.nome_arquivo("n1")).is_file()


def test_gravar_novos_recusa_outro_dump_e_nada_novo(tmp_path, monkeypatch):
    _prepara_baseline(tmp_path, monkeypatch)
    with pytest.raises(mod_caso.ErroGravacao, match="nenhum caso novo"):
        mod_caso.gravar_novos([_c("a"), _c("b")], "http://h", tmp_path)
    monkeypatch.setattr(mod_caso, "_sha_dump_atual", lambda: "OUTRO")
    with pytest.raises(mod_caso.ErroGravacao, match="outro dump"):
        mod_caso.gravar_novos([_c("a"), _c("n1")], "http://h", tmp_path)


def test_gravar_novos_recusa_espera_status_que_a_referencia_nao_confirma(tmp_path, monkeypatch):
    _prepara_baseline(tmp_path, monkeypatch)
    monkeypatch.setattr(mod_caso, "_roda", lambda casos, url, erros=None, info=None, restaurar=True:
                        {c.id: mod_caso.Resposta(200, {}, None, []) for c in casos})
    novo = CasoHttp(id="n1", metodo="GET", caminho="/n1", corpo=None, espera_status=500)
    with pytest.raises(mod_caso.ErroGravacao, match="espera_status"):
        mod_caso.gravar_novos([_c("a"), _c("b"), novo], "http://h", tmp_path)
    assert not (tmp_path / mod_caso.nome_arquivo("n1")).exists()


def test_bateria_apenas_novos_exige_confirmo_sobrescrever(tmp_path):
    from regressao.laravel import bateria
    with pytest.raises(bateria.RecusaBaseline, match="apenas-novos"):
        bateria.roda_bateria_laravel(tmp_path, "gravar", apenas_novos=True)
    with pytest.raises(ValueError, match="so vale para gravar"):
        bateria.roda_bateria_laravel(tmp_path, "comparar", apenas_novos=True)


def test_casos_novos_do_yaml_carregam():
    casos = {c.id: c for c in mod_caso.carrega_casos(mod_caso.DIR_CASOS)}
    assert casos["console-list"].console == ["list", "--raw"] and casos["console-list"].console_modo == "nomes"
    assert any(c.arquivo for c in casos.values()) and any(c.console for c in casos.values())
