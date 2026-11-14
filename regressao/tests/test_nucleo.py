from pathlib import Path

from regressao.nucleo.conhecidas import carregar_conhecidas, marcar
from regressao.nucleo.normaliza import hash_corpo, normaliza
from regressao.nucleo.veredito import Caso, Veredito, codigo_saida


def c(id, v):
    return Caso(id=id, area="a", veredito=v)


def test_codigo_saida_zero_sem_divergencia_nova():
    assert codigo_saida([c("1", Veredito.IDENTICO), c("2", Veredito.INCONCLUSIVO)]) == 0


def test_codigo_saida_um_com_diverge_novo():
    assert codigo_saida([c("1", Veredito.IDENTICO), c("2", Veredito.DIVERGE)]) == 1


def test_codigo_saida_ignora_diverge_conhecida():
    k = c("2", Veredito.DIVERGE)
    k.conhecida = True
    assert codigo_saida([c("1", Veredito.IDENTICO), k]) == 0


def test_codigo_saida_dois_com_erro_ambiente():
    casos = [c("1", Veredito.DIVERGE), c("2", Veredito.ERRO_AMBIENTE)]
    assert codigo_saida(casos) == 2


def test_normaliza_troca_sid_nos_dois_lados():
    assert normaliza(b"x?sid=abc123") == normaliza(b"x?sid=zzz999")


def test_normaliza_nao_decodifica_latin1():
    assert normaliza(b"a\xe7\xe3o") == b"a\xe7\xe3o"


def test_hash_estavel_e_sensivel_a_um_byte():
    assert hash_corpo(b"abc") == hash_corpo(b"abc")
    assert hash_corpo(b"abc") != hash_corpo(b"abd")
    assert len(hash_corpo(b"abc")) == 64


def test_marcar_so_marca_diverge_listada():
    casos = [c("a", Veredito.DIVERGE), c("b", Veredito.DIVERGE), c("a2", Veredito.IDENTICO)]
    out = marcar(casos, {"a": "motivo", "a2": "x"})
    assert [x.conhecida for x in out] == [True, False, False]


def test_carregar_conhecidas_ignora_comentarios_e_vazias(tmp_path: Path):
    p = tmp_path / "k.tsv"
    p.write_text("# id\tmotivo\n\nx1\tbug antigo\n", encoding="utf-8")
    assert carregar_conhecidas(p) == {"x1": "bug antigo"}
