from unittest.mock import patch

from regressao.nucleo.veredito import Veredito
from regressao.php.classes import compara_classes
from regressao.php import sintaxe
from regressao.php.sintaxe import roda_lint


def test_compara_classes_iguais_sao_identicas():
    s = "cgm\tz01_nome\t'ANA'\ncgm\tz01_numcgm\t'1012'\n"
    casos = compara_classes(s, s)
    assert [c.veredito for c in casos] == [Veredito.IDENTICO]


def test_compara_classes_detecta_zero_vs_valor():
    casos = compara_classes("cgm z01_numcgm='1012'\n", "cgm z01_numcgm=0\n")
    assert len(casos) == 1
    assert casos[0].veredito == Veredito.DIVERGE
    assert "z01_numcgm" in casos[0].detalhe


def test_compara_classes_sem_saida_nos_dois_lados_e_inconclusiva():
    s = "SEM_SAIDA classes/db_x.php\n"
    casos = compara_classes(s, s)
    assert [c.veredito for c in casos] == [Veredito.INCONCLUSIVO]


def _fake(resp):
    def f(args, timeout, stdin=None, stdout=None):
        assert stdin is not None  # php -l precisa de stdin fechado
        return resp[args[1]].encode()
    return f


def test_lint_ambos_compilam():
    ok = "No syntax errors detected in a.php\n"
    with patch.object(sintaxe, "_docker", _fake({"ecidade_php56": ok, "ecidade_php85": ok})):
        assert roda_lint(["a.php"])[0].veredito == Veredito.IDENTICO


def test_lint_so_85_falha_diverge():
    with patch.object(sintaxe, "_docker", _fake({
            "ecidade_php56": "No syntax errors detected in a.php\n",
            "ecidade_php85": "PHP Parse error: syntax error in a.php on line 3\n"})):
        c = roda_lint(["a.php"])[0]
    assert c.veredito == Veredito.DIVERGE and "Parse error" in c.detalhe


def test_lint_ambos_falham_e_inconclusivo():
    err = "PHP Parse error: syntax error in a.php on line 3\n"
    with patch.object(sintaxe, "_docker", _fake({"ecidade_php56": err, "ecidade_php85": err})):
        c = roda_lint(["a.php"])[0]
    assert c.veredito == Veredito.INCONCLUSIVO and "Parse error" in c.detalhe
