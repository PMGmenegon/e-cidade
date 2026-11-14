from pathlib import Path
from unittest.mock import patch

from regressao.nucleo.banco import ErroAmbienteBanco
from regressao.nucleo.veredito import Veredito
from regressao.php import telas
from regressao.php.cobertura import cobertura_telas
from regressao.php.hashes import compara_hashes, grava_hashes
from regressao.php.telas import parse_cmp

SAIDA = """3 telas

  DIVERGE cem1_cadastro001.php  56=200/18668B  85=500/4558B
  TIMEOUT cem1_lento002.php  56=000  85=200  (nao conta como identica)

=== 1/3 identicas, 1 divergentes, 1 timeout ===
"""
TELAS = ["cem1_cadastro001.php", "cem1_lento002.php", "cem1_ok003.php"]


def _por_id(casos):
    return {c.id: c for c in casos}


def test_parse_cmp_divergente_vira_diverge():
    c = _por_id(parse_cmp(SAIDA, "configuracao", TELAS))["cem1_cadastro001.php"]
    assert c.veredito == Veredito.DIVERGE
    assert "56=200/18668B" in c.detalhe and "85=500/4558B" in c.detalhe
    assert c.area == "configuracao"


def test_parse_cmp_timeout_nao_conta_como_igual():
    casos = _por_id(parse_cmp(SAIDA, "configuracao", TELAS))
    assert casos["cem1_lento002.php"].veredito == Veredito.ERRO_AMBIENTE
    assert casos["cem1_ok003.php"].veredito == Veredito.IDENTICO


def test_parse_cmp_sem_lista_de_telas_resume_as_identicas():
    casos = parse_cmp(SAIDA, "configuracao")
    resumo = [c for c in casos if c.id == "identicas"]
    assert len(resumo) == 1 and resumo[0].veredito == Veredito.IDENTICO
    assert "1" in resumo[0].detalhe


def test_parse_cmp_resumo_inconsistente_e_erro_ambiente():
    casos = parse_cmp("", "configuracao", TELAS)
    assert [c.veredito for c in casos] == [Veredito.ERRO_AMBIENTE]


def test_resposta_vazia_nos_dois_lados_e_inconclusiva():
    casos = _por_id(parse_cmp(SAIDA, "configuracao", TELAS, corpos={"cem1_ok003.php": b""}))
    assert casos["cem1_ok003.php"].veredito == Veredito.INCONCLUSIVO


def test_tela_pulada_e_inconclusiva():
    saida = "  PULADA iss4_siss002.php  (contata servico externo)\n2 telas\n\n=== 2/2 identicas, 0 divergentes, 0 timeout ===\n"
    casos = _por_id(parse_cmp(saida, "x", ["a.php", "b.php"]))
    assert casos["iss4_siss002.php"].veredito == Veredito.INCONCLUSIVO
    assert casos["a.php"].veredito == Veredito.IDENTICO


def test_compara_hashes_lista_telas_alteradas(tmp_path):
    a = grava_hashes(tmp_path / "a", {"t1": b"x", "t2": b"y", "t3": b"z"}, rodada="a")
    b = grava_hashes(tmp_path / "b", {"t1": b"x", "t2": b"mudou", "t4": b"w"}, rodada="b")
    assert a.name == "hashes_a.tsv"
    assert compara_hashes(a, b) == ["t2", "-t3", "+t4"]


def test_grava_hashes_ordenado_e_normalizado(tmp_path):
    p = grava_hashes(tmp_path, {"b": b"sid=0123456789abcdef", "a": b"sid=fedcba9876543210"}, rodada="r")
    linhas = p.read_text().splitlines()
    assert [l.split("\t")[0] for l in linhas] == ["a", "b"]
    assert linhas[0].split("\t")[1] == linhas[1].split("\t")[1]


def test_cobertura_distingue_tabela_vazia():
    corpos = {
        "cheia": b"<table><thead><tr><th>a</th></tr></thead><tr><td>1</td></tr></table>",
        "vazia": b"<table><thead><tr><td>cab</td></tr></thead></table>",
        "sem": b"<html>nada</html>",
    }
    r = cobertura_telas([], corpos)
    assert r["com_dados"] == ["cheia"]
    assert r["tabela_vazia"] == ["sem", "vazia"]


def test_roda_telas_erro_de_docker_vira_erro_ambiente():
    with patch.object(telas, "lista_telas", return_value=["a.php"]), \
         patch.object(telas, "_roda_cmp", side_effect=OSError("sem python3")):
        casos = telas.roda_telas("abc", "^cem", "configuracao")
    assert [c.veredito for c in casos] == [Veredito.ERRO_AMBIENTE]


def test_roda_telas_junta_lista_de_telas_e_saida_do_cmp():
    saida = ("2 telas\n\n  DIVERGE cem1_a.php  56=200/1B  85=200/2B\n"
             "\n=== 1/2 identicas, 1 divergentes, 0 timeout ===\n")
    with patch.object(telas, "lista_telas", return_value=["cem1_a.php", "cem1_b.php"]), \
         patch.object(telas, "_roda_cmp", return_value=saida):
        casos = {c.id: c.veredito for c in telas.roda_telas("s", "^cem", "x")}
    assert casos == {"cem1_a.php": Veredito.DIVERGE, "cem1_b.php": Veredito.IDENTICO}


def test_lista_telas_espelha_selecao_do_cmp(tmp_path):
    for n in ("cem1_a.php", "CEM2_b.php", "cem3.txt", "outra.php", "iss4_siss002.php"):
        (tmp_path / n).write_text("")
    assert telas.lista_telas("^cem", tmp_path) == ["CEM2_b.php", "cem1_a.php"]
    assert telas.lista_telas("^iss4", tmp_path) == []


def test_obtem_sid_extrai_nome_da_sessao():
    with patch.object(telas, "_docker", return_value=b"/var/lib/php/sessions/sess_abc123\n"):
        assert telas.obtem_sid() == "abc123"
