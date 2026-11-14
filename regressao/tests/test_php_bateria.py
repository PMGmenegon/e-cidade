import json
from pathlib import Path

import pytest

from regressao.nucleo.ambiente import Alvos
from regressao.nucleo.banco import BancoDiferente, ErroAmbienteBanco
from regressao.nucleo.veredito import Caso, Veredito, codigo_saida
from regressao.php import bateria
from regressao.php.posts import PostCaso
from regressao.php.relatorios import RelCaso

V = Veredito


@pytest.fixture
def amb(monkeypatch, tmp_path):
    """Todos os passos substituidos por dubles; `chamadas` registra a ordem."""
    chamadas: list[str] = []

    def reg(nome, retorno):
        def f(*a, **k):
            chamadas.append(nome)
            return retorno(*a) if callable(retorno) else retorno
        return f

    conhecidas = tmp_path / "conhecidas.tsv"
    conhecidas.write_text("# id\tmotivo\n", encoding="utf-8")
    posts = [PostCaso("rec1_a001.php", ["a"], "x=1", "rh", True),
             PostCaso("rec1_b001.php", ["b"], "x=1", "rh", False),
             PostCaso("orc1_c001.php", ["c"], "x=1", "orcamento", True)]
    rels = [RelCaso("pro2_r002.php", "", "pdf", "protocolo", True),
            RelCaso("con2_r002.php", "", "pdf", "contabilidade", False)]
    m = monkeypatch
    m.setattr(bateria, "CONHECIDAS", conhecidas)
    m.setattr(bateria, "alvos_do_ambiente", lambda: Alvos("a", "b", "c", "d"))
    m.setattr(bateria, "verifica", reg("verifica", []))
    m.setattr(bateria, "confere_baseline", reg("confere_baseline", None))
    m.setattr(bateria, "restaura_dump", reg("restaura_dump", None))
    m.setattr(bateria, "obtem_sid", reg("obtem_sid", "sid123"))
    m.setattr(bateria, "sessao_autenticada", reg("sessao_autenticada", True))
    m.setattr(bateria, "lista_telas", lambda p: [f"{p[1:4]}_x.php"])
    m.setattr(bateria, "_classes_das_telas", lambda t: ["classes/db_a_classe.php"])
    m.setattr(bateria, "_metadados_ambiente", lambda: {"php_56": "5.6.40", "php_85": "8.5.0",
                                                       "git_commit": "abc", "baseline_sha256": "ff"})
    m.setattr(bateria, "roda_lint", reg("lint", lambda arqs: [Caso(a, "php-sintaxe", V.IDENTICO) for a in arqs]))
    m.setattr(bateria, "roda_classes", reg("classes", lambda l: [Caso(c, "php-classes", V.IDENTICO) for c in l]))
    m.setattr(bateria, "roda_telas", reg("telas", lambda sid, p, a: ([Caso(f"t{p}", a, V.IDENTICO)], {f"t{p}": b"<td>1</td>"})))
    m.setattr(bateria, "carrega_catalogo", lambda c: posts)
    m.setattr(bateria, "carrega_catalogo_relatorios", lambda c: rels)
    m.setattr(bateria, "roda_post", reg("post", lambda sid, c: Caso(c.tela, c.area, V.IDENTICO)))
    m.setattr(bateria, "roda_relatorio", reg("relatorio", lambda sid, c: Caso(c.url, c.area, V.IDENTICO)))
    return chamadas


def le(saida: Path) -> dict:
    return json.loads((saida / "resultado.json").read_text(encoding="utf-8"))


def ids(saida: Path) -> dict[str, str]:
    return {c["id"]: c["veredito"] for c in le(saida)["casos"]}


def test_fluxo_completo_na_ordem(amb, tmp_path):
    assert bateria.roda_bateria_php(tmp_path, ["tributario"]) == 0
    ordem = [c for i, c in enumerate(amb) if c not in amb[:i]]
    assert ordem[:6] == ["verifica", "confere_baseline", "restaura_dump", "obtem_sid", "sessao_autenticada", "lint"]
    assert ordem[-3:] == ["telas", "post", "relatorio"] or ordem[-1] == "relatorio"
    assert amb.count("restaura_dump") == 1
    meta = le(tmp_path)["meta"]
    assert meta["php_56"] == "5.6.40" and meta["areas"] == ["tributario"]
    assert "restauracao_s" in meta and "sintaxe_s" in meta["tempos_s"]
    assert any(p.name.startswith("hashes_") for p in tmp_path.iterdir())
    assert (tmp_path / "cobertura.json").is_file()


def test_ambiente_fora_gera_erro_ambiente_e_codigo_2(amb, monkeypatch, tmp_path):
    monkeypatch.setattr(bateria, "verifica", lambda a: ["ref: sem resposta em 5s: x", "docker ps indisponivel"])
    assert bateria.roda_bateria_php(tmp_path) == 2
    assert ids(tmp_path) == {"ambiente": "ERRO_AMBIENTE"}
    assert "restaura_dump" not in amb and "lint" not in amb


@pytest.mark.parametrize("exc", [BancoDiferente("sha diferente"), ErroAmbienteBanco("docker caiu")])
def test_banco_diferente_rejeita_rodada(amb, monkeypatch, tmp_path, exc):
    def explode(*a):
        raise exc
    monkeypatch.setattr(bateria, "confere_baseline", explode)
    assert bateria.roda_bateria_php(tmp_path, ["gestor"]) == 2
    assert ids(tmp_path) == {"banco": "ERRO_AMBIENTE"}
    for passo in ("restaura_dump", "obtem_sid", "lint", "classes", "telas", "post", "relatorio"):
        assert passo not in amb


def test_falha_na_restauracao_tambem_rejeita(amb, monkeypatch, tmp_path):
    def explode(*a):
        raise ErroAmbienteBanco("pg_restore falhou")
    monkeypatch.setattr(bateria, "restaura_dump", explode)
    assert bateria.roda_bateria_php(tmp_path, ["gestor"]) == 2
    assert "lint" not in amb and "telas" not in amb


def test_sessao_invalida_para_tudo(amb, monkeypatch, tmp_path):
    monkeypatch.setattr(bateria, "sessao_autenticada", lambda s: False)
    assert bateria.roda_bateria_php(tmp_path, ["gestor"]) == 2
    assert ids(tmp_path) == {"sessao": "ERRO_AMBIENTE"}
    assert "lint" not in amb


def test_diverge_conhecida_nao_quebra_rodada(amb, monkeypatch, tmp_path):
    (bateria.CONHECIDAS).write_text("# id\tmotivo\npro2_r002.php\tpreexistente, provado\n", encoding="utf-8")
    monkeypatch.setattr(bateria, "roda_relatorio",
                        lambda sid, c: Caso(c.url, c.area, V.DIVERGE, "dif"))
    # nao-verificado fica de fora; so o pro2 (conhecido) diverge
    assert bateria.roda_bateria_php(tmp_path, ["assistenciasocial"]) == 0
    casos = {c["id"]: c for c in le(tmp_path)["casos"]}
    assert casos["pro2_r002.php"]["veredito"] == "DIVERGE" and casos["pro2_r002.php"]["conhecida"] is True


def test_diverge_nova_da_codigo_1(amb, monkeypatch, tmp_path):
    monkeypatch.setattr(bateria, "roda_relatorio", lambda sid, c: Caso(c.url, c.area, V.DIVERGE, "HTTP 500"))
    assert bateria.roda_bateria_php(tmp_path, ["assistenciasocial"]) == 1


def test_nao_verificadas_nao_rodam_por_padrao_e_sao_contadas(amb, tmp_path):
    bateria.roda_bateria_php(tmp_path)  # todas as areas
    resultado = ids(tmp_path)
    assert "rec1_b001.php" not in resultado and "con2_r002.php" not in resultado
    cat = le(tmp_path)["meta"]["catalogo_posts"]
    assert cat["nao_verificado_pulados"] == 1 and cat["nao_verificado_pulados_ids"] == ["rec1_b001.php"]
    assert le(tmp_path)["meta"]["catalogo_relatorios"]["nao_verificado_pulados"] == 1
    assert "nao_verificado_pulados" in (tmp_path / "resultado.json").read_text(encoding="utf-8")


def test_incluir_nao_verificados_roda_todas(amb, tmp_path):
    bateria.roda_bateria_php(tmp_path, incluir_nao_verificados=True)
    resultado = ids(tmp_path)
    assert "rec1_b001.php" in resultado and "con2_r002.php" in resultado


def test_sem_restaurar_marca_o_resumo(amb, tmp_path):
    bateria.roda_bateria_php(tmp_path, ["gestor"], restaurar=False)
    assert "restaura_dump" not in amb
    resumo = (tmp_path / "resumo.md").read_text(encoding="utf-8")
    assert "banco NAO restaurado: resultado nao comparavel" in resumo
    assert le(tmp_path)["meta"]["aviso"] == "banco NAO restaurado: resultado nao comparavel"
    assert le(tmp_path)["meta"]["restauracao_s"] is None


def test_area_desconhecida_falha_antes_de_rodar(amb, tmp_path):
    with pytest.raises(bateria.AreaDesconhecida, match="nao-existe"):
        bateria.roda_bateria_php(tmp_path, ["gestor", "nao-existe"])
    assert amb == [] and not (tmp_path / "resultado.json").exists()
    assert bateria.main(["--saida", str(tmp_path), "--area", "xyz"]) == 2
    assert amb == []


def test_aliases_e_acentos_das_areas():
    assert bateria.resolve_areas(["Tributário"])[0] == ["tributario"]
    assert bateria.resolve_areas(["Recursos Humanos", "rh"])[0] == ["recursoshumanos"]
    assert bateria.resolve_areas(["Educação"])[0] == ["educacao"]
    assert bateria.resolve_areas(["configuracao"])[1][:2] == ["amb", "ate"]


def test_um_passo_que_falha_nao_derruba_os_outros(amb, monkeypatch, tmp_path):
    def explode(arqs):
        raise RuntimeError("php -l quebrou")
    monkeypatch.setattr(bateria, "roda_lint", explode)
    assert bateria.roda_bateria_php(tmp_path, ["assistenciasocial"]) == 2
    resultado = ids(tmp_path)
    assert resultado["passo:sintaxe"] == "ERRO_AMBIENTE"
    assert "telas" in amb and "post" in amb and "relatorio" in amb  # continuaram


def test_post_que_levanta_vira_erro_so_dessa_linha(amb, monkeypatch, tmp_path):
    def explode(sid, c):
        if c.tela == "rec1_a001.php":
            raise OSError("boom")
        return Caso(c.tela, c.area, V.IDENTICO)
    monkeypatch.setattr(bateria, "roda_post", explode)
    bateria.roda_bateria_php(tmp_path)
    r = ids(tmp_path)
    assert r["rec1_a001.php"] == "ERRO_AMBIENTE" and r["orc1_c001.php"] == "IDENTICO"


def test_filtra_catalogo_pela_area(amb, tmp_path):
    bateria.roda_bateria_php(tmp_path, ["assistenciasocial"])  # prefixos hab, pro, rec, soc
    r = ids(tmp_path)
    assert "rec1_a001.php" in r and "pro2_r002.php" in r and "orc1_c001.php" not in r
    assert le(tmp_path)["meta"]["catalogo_posts"]["fora_da_area"] == 1


def test_sem_normalizar_esvazia_regras_so_durante_a_rodada(amb, monkeypatch, tmp_path):
    from regressao.nucleo.normaliza import REGRAS, normaliza
    antes = len(REGRAS)
    vistas = []
    monkeypatch.setattr(bateria, "roda_lint", lambda arqs: vistas.append(normaliza(b"sid=" + b"a" * 10)) or [])
    bateria.roda_bateria_php(tmp_path, ["gestor"], normalizar=False)
    assert vistas == [b"sid=" + b"a" * 10] and len(REGRAS) == antes
    assert normaliza(b"sid=" + b"a" * 10) == b"sid=X"


@pytest.mark.parametrize("veredito,conhecida,esperado", [
    (V.IDENTICO, False, 0), (V.INCONCLUSIVO, False, 0), (V.DIVERGE, True, 0),
    (V.DIVERGE, False, 1), (V.ERRO_AMBIENTE, False, 2)])
def test_mapeamento_do_codigo_de_saida(veredito, conhecida, esperado):
    assert codigo_saida([Caso("x", "a", veredito, conhecida=conhecida)]) == esperado
    assert codigo_saida([Caso("x", "a", V.DIVERGE), Caso("y", "a", V.ERRO_AMBIENTE)]) == 2
