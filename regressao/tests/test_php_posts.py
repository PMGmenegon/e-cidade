import subprocess
from pathlib import Path

import pytest

from regressao.nucleo.banco import ErroAmbienteBanco
from regressao.nucleo.veredito import Veredito
from regressao.php import posts
from regressao.php.posts import PostCaso, carrega_catalogo, parse_post, roda_post

CASO = PostCaso("hrs1_assenta001.php", ["assentamentofuncional", "assenta"], "db_opcao=Incluir", "rh")

IDENTICO = """  snapshot: assentamentofuncional=0 linhas  assenta=0 linhas  | sequencias=1
  statements: 5.6=9  8.5=9
  destes, INSERT/UPDATE/DELETE: 5.6=5  8.5=5
  destes, escrita de NEGOCIO: 5.6=3  8.5=3
    5.6> insert into assenta( h16_codigo ) values ( 4 )
    8.5> insert into assenta( h16_codigo ) values ( 4 )
  == SQL de escrita de NEGOCIO IDENTICO nos dois runtimes ==
"""
DIVERGE = """  destes, escrita de NEGOCIO: 5.6=1  8.5=1
  == DIVERGE ==
    5.6: insert into x(a) values ( 'v' )
    8.5: insert into x(a) values ( 0 )
"""
INCONCLUSIVO = """  == INCONCLUSIVO: nenhuma escrita de negocio nos DOIS runtimes ==
     o POST nao chegou a gravar.
"""
ABORTADO = ('ABORTADO: nao consegui restaurar assenta: ERROR:  update or delete on table "assenta" '
            'violates foreign key constraint "fk" on table "assentaextra"\n')


def test_parse_post_identico():
    c = parse_post(IDENTICO, CASO)
    assert c.veredito == Veredito.IDENTICO
    assert c.id == "hrs1_assenta001.php" and c.area == "rh"


def test_parse_post_diverge_traz_o_sql_dos_dois_lados():
    c = parse_post(DIVERGE, CASO)
    assert c.veredito == Veredito.DIVERGE
    assert "values ( 0 )" in c.diff and "values ( 'v' )" in c.diff


def test_parse_post_inconclusivo_nao_aprova():
    c = parse_post(INCONCLUSIVO, CASO)
    assert c.veredito == Veredito.INCONCLUSIVO


def test_parse_post_abortado_vira_erro_ambiente():
    c = parse_post(ABORTADO, CASO)
    assert c.veredito == Veredito.ERRO_AMBIENTE
    assert "assentaextra" in c.detalhe  # tabela a acrescentar (filha antes da mae)


def test_parse_post_sql_com_a_palavra_identico_nao_engana():
    saida = "    5.6> insert into t values ('SQL de escrita de NEGOCIO IDENTICO')\n  == DIVERGE ==\n"
    assert parse_post(saida, CASO).veredito == Veredito.DIVERGE


def test_parse_post_identico_com_tabela_nao_restaurada_avisa():
    saida = IDENTICO + "  ATENCAO: a tela gravou tambem em foo, que NAO e restaurada.\n"
    c = parse_post(saida, CASO)
    assert c.veredito == Veredito.IDENTICO and "foo" in c.detalhe


def test_parse_post_saida_irreconhecivel_e_erro_ambiente():
    assert parse_post("", CASO).veredito == Veredito.ERRO_AMBIENTE
    assert parse_post("Traceback (most recent call last):\n", CASO).veredito == Veredito.ERRO_AMBIENTE


def test_catalogo_ordena_filhas_antes_da_mae(tmp_path):
    tsv = tmp_path / "c.tsv"
    tsv.write_text("# comentario\n\nt1.php\tfilha,mae\tcampo=1\tarea\n", encoding="utf-8")
    casos = carrega_catalogo(tsv)
    assert casos == [PostCaso("t1.php", ["filha", "mae"], "campo=1", "area")]


def test_catalogo_linha_malformada_nomeia_a_linha(tmp_path):
    tsv = tmp_path / "c.tsv"
    tsv.write_text("ok.php\ta\tc=1\tarea\nruim.php\tsó_duas\n", encoding="utf-8")
    with pytest.raises(ValueError, match="linha 2"):
        carrega_catalogo(tsv)


def test_catalogo_semeado_carrega():
    casos = carrega_catalogo(posts.CATALOGO)
    assert casos and all(c.tela.endswith(".php") and c.tabelas and c.campos for c in casos)
    assert any(c.tela == "pes1_rhpessoal004.php" and c.tabelas == ["registrapontoeletronicohistorico", "rhpessoal"]
               for c in casos)


def _grava_docker(monkeypatch):
    chamadas = []

    def falso(args, timeout, stdin=None, stdout=None):
        chamadas.append(args)
        return b""
    monkeypatch.setattr("regressao.nucleo.banco._docker", falso)
    return chamadas


def _sqls(chamadas):
    return [a[-1] for a in chamadas]


def test_roda_post_liga_e_desliga_log_statement(monkeypatch):
    chamadas = _grava_docker(monkeypatch)
    monkeypatch.setattr(posts, "_roda_escrita", lambda sid, caso: IDENTICO)
    c = roda_post("SID", CASO)
    assert c.veredito == Veredito.IDENTICO
    s = _sqls(chamadas)
    assert "log_statement='all'" in s[0] and "RESET log_statement" in s[-1]


def test_log_statement_e_resetado_mesmo_com_falha(monkeypatch):
    chamadas = _grava_docker(monkeypatch)

    def quebra(sid, caso):
        raise subprocess.TimeoutExpired("escrita_post.py", 1)
    monkeypatch.setattr(posts, "_roda_escrita", quebra)
    c = roda_post("SID", CASO)
    assert c.veredito == Veredito.ERRO_AMBIENTE and "timeout" in c.detalhe.lower()
    assert "RESET log_statement" in _sqls(chamadas)[-1]


def test_log_statement_e_resetado_com_excecao_inesperada(monkeypatch):
    chamadas = _grava_docker(monkeypatch)

    def quebra(sid, caso):
        raise RuntimeError("boom")
    monkeypatch.setattr(posts, "_roda_escrita", quebra)
    with pytest.raises(RuntimeError):
        roda_post("SID", CASO)
    assert "RESET log_statement" in _sqls(chamadas)[-1]


def test_falha_ao_ligar_log_statement_e_erro_ambiente(monkeypatch):
    def falso(args, timeout, stdin=None, stdout=None):
        raise ErroAmbienteBanco("docker ausente")
    monkeypatch.setattr("regressao.nucleo.banco._docker", falso)
    chamou = []
    monkeypatch.setattr(posts, "_roda_escrita", lambda s, c: chamou.append(1) or IDENTICO)
    c = roda_post("SID", CASO)
    assert c.veredito == Veredito.ERRO_AMBIENTE and not chamou
