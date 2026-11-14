import json
from pathlib import Path

from regressao.nucleo.relatorio import compara_rodadas, escreve_rodada
from regressao.nucleo.veredito import Caso, Veredito


def test_resumo_conta_por_area_e_veredito(tmp_path: Path):
    casos = [
        Caso("a1", "login", Veredito.IDENTICO),
        Caso("a2", "login", Veredito.DIVERGE),
        Caso("b1", "tributario", Veredito.DIVERGE, conhecida=True),
        Caso("b2", "tributario", Veredito.INCONCLUSIVO, detalhe="sem dados"),
    ]
    escreve_rodada(tmp_path, casos, {"php": "8.2", "commit": "abc"})

    dados = json.loads((tmp_path / "resultado.json").read_text(encoding="utf-8"))
    assert dados["meta"] == {"php": "8.2", "commit": "abc"}
    assert len(dados["casos"]) == 4
    resumo = (tmp_path / "resumo.md").read_text(encoding="utf-8")
    assert "login" in resumo and "tributario" in resumo
    assert "DIVERGE" in resumo and "INCONCLUSIVO" in resumo
    assert "a2" in resumo and "b1" in resumo and "b2" in resumo


def test_diff_vai_para_arquivo_do_caso(tmp_path: Path):
    casos = [Caso("x1", "a", Veredito.DIVERGE, diff="-um\n+dois\n")]
    escreve_rodada(tmp_path, casos, {})
    assert (tmp_path / "diffs" / "x1.diff").read_text(encoding="utf-8") == "-um\n+dois\n"


def test_compara_rodadas_lista_so_o_que_mudou(tmp_path: Path):
    antes, depois = tmp_path / "antes", tmp_path / "depois"
    escreve_rodada(antes, [Caso("A", "a", Veredito.IDENTICO), Caso("B", "a", Veredito.DIVERGE)], {})
    escreve_rodada(depois, [Caso("A", "a", Veredito.DIVERGE), Caso("B", "a", Veredito.DIVERGE)], {})
    assert compara_rodadas(antes, depois) == [("A", Veredito.IDENTICO, Veredito.DIVERGE)]
