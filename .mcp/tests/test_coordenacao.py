import subprocess

import pytest

from servidor.seguranca import ErroFerramenta
from servidor.tools import coordenacao as co


@pytest.fixture
def repo(config):
    e = config.raiz / "ecidade"
    for i in range(4):
        (e / f"t{i}.php").write_text("<?php\nparse_str($HTTP_SERVER_VARS['QUERY_STRING']);\n")
    (e / "s.php").write_text("<?php\n$a = split('-', $b);\n")
    return config


def git_falso(saida="", cod=0):
    def run(argv, **kw):
        assert argv[0] == "git" and "-C" in argv
        return subprocess.CompletedProcess(argv, cod, saida, "")
    return run


def test_reivindicar_e_liberar(repo):
    r = co.reivindicar_arquivo(repo, "ecidade/t1.php", "parse_str", quem="ana")
    assert r["quem"] == "ana" and r["caminho"] == "ecidade/t1.php"
    assert "git add .mcp/estado/trabalho.json" in r["sugestao_commit"]
    with pytest.raises(ErroFerramenta) as e:
        co.reivindicar_arquivo(repo, "ecidade/t1.php", "x", quem="bruno")
    assert e.value.codigo == "ja_reivindicado"
    r = co.liberar_arquivo(repo, "ecidade/t1.php", quem="ana", concluido=True, padroes_corrigidos=["parse_str_1_arg"])
    assert r["concluido"] is True


def test_sugestoes_de_commit_com_aspas_de_shell(repo):
    import shlex
    r = co.reivindicar_arquivo(repo, "ecidade/t1.php", "x", quem="ana")
    partes = shlex.split(r["sugestao_commit"])
    assert partes[-2:] == ["-m", "estado: reivindica ecidade/t1.php"]
    r = co.liberar_arquivo(repo, "ecidade/t1.php", quem="ana", concluido=True, padroes_corrigidos=["split"])
    assert shlex.split(r["commit_do_codigo"]) == ["git", "add", "--", "ecidade/t1.php", "&&", "git", "commit", "-m",
                                                  "migra(split): ecidade/t1.php"]


@pytest.mark.parametrize("nome", ["a;rm -rf ~.php", "a$(id).php", "a`id`.php", "a'b.php", "a|b.php"])
def test_caminho_com_metacaractere_de_shell_e_recusado(repo, nome):
    (repo.raiz / "ecidade" / nome).write_text("<?php")
    with pytest.raises(ErroFerramenta) as e:
        co.reivindicar_arquivo(repo, f"ecidade/{nome}", "x", quem="ana")
    assert e.value.codigo == "caminho_invalido"


def test_quem_cooperativo_normalizado(repo):
    co.reivindicar_arquivo(repo, "ecidade/t1.php", "x", quem="Ana")
    r = co.reivindicar_arquivo(repo, "ecidade/t1.php", "x", quem=" ana ")
    assert r["renovada"] is True
    assert co.quem_sou(repo, "  bia\x1b[31m\r\n") == "bia"


def test_reivindicar_caminho_confinado_e_existente(repo):
    with pytest.raises(ErroFerramenta) as e:
        co.reivindicar_arquivo(repo, "../x.php", "x", quem="ana")
    assert e.value.codigo == "caminho_fora_da_raiz"
    with pytest.raises(ErroFerramenta) as e:
        co.reivindicar_arquivo(repo, "ecidade/nao.php", "x", quem="ana")
    assert e.value.codigo == "caminho_inexistente"


def test_liberar_com_padrao_desconhecido(repo):
    co.reivindicar_arquivo(repo, "ecidade/t1.php", "x", quem="ana")
    with pytest.raises(ErroFerramenta) as e:
        co.liberar_arquivo(repo, "ecidade/t1.php", quem="ana", concluido=True, padroes_corrigidos=["inventado"])
    assert e.value.codigo == "padrao_desconhecido"


def test_quem_vem_do_env_ou_git(repo, monkeypatch):
    assert co.quem_sou(repo, None, git_runner=git_falso("Ana Dev\n")) == "Ana Dev"
    with pytest.raises(ErroFerramenta) as e:
        co.quem_sou(repo, None, git_runner=git_falso("", 1))
    assert e.value.codigo == "quem_desconhecido"
    from dataclasses import replace
    assert co.quem_sou(replace(repo, usuario="env-user"), None) == "env-user"


def test_quadro(repo):
    co.reivindicar_arquivo(repo, "ecidade/t1.php", "parse_str", quem="ana")
    q = co.quadro(repo)
    assert q["reivindicacoes_ativas"][0]["caminho"] == "ecidade/t1.php"
    assert "rodadas_recentes" in q and q["expiracao_horas"] == 4.0


def test_proximo_trabalho_pula_reivindicados_e_concluidos(repo):
    co.reivindicar_arquivo(repo, "ecidade/t0.php", "x", quem="bruno")
    co.reivindicar_arquivo(repo, "ecidade/t1.php", "x", quem="ana")
    co.liberar_arquivo(repo, "ecidade/t1.php", quem="ana", concluido=True, padroes_corrigidos=["parse_str_1_arg"])
    r = co.proximo_trabalho(repo, quem="ana", limite=10)
    assert r["padrao"]["nome"] == "parse_str_1_arg"
    assert [a["arquivo"] for a in r["arquivos"]] == ["ecidade/t2.php", "ecidade/t3.php", "ecidade/tela001.php"]
    assert r["arquivos"][0]["linhas"] == [2]


def test_proximo_trabalho_reivindica_o_lote(repo):
    r = co.proximo_trabalho(repo, padrao="split", quem="ana", reivindicar=True)
    assert [a["arquivo"] for a in r["arquivos"]] == ["ecidade/s.php"]
    assert r["reivindicados"] == ["ecidade/s.php"]
    assert co.quadro(repo)["reivindicacoes_ativas"][0]["quem"] == "ana"


def test_proximo_trabalho_sem_nada(repo):
    r = co.proximo_trabalho(repo, padrao="create_function", quem="ana")
    assert r["arquivos"] == [] and "nenhum" in r["mensagem"]


def test_padroes_ja_corrigidos(repo):
    co.reivindicar_arquivo(repo, "ecidade/t1.php", "x", quem="ana")
    co.liberar_arquivo(repo, "ecidade/t1.php", quem="ana", concluido=True, padroes_corrigidos=["parse_str_1_arg"])
    log = "abc123\tAna\tmigra(parse_str_1_arg): 12 telas de arrecadacao\nabd456\tBia\tmigra(split): balancetes\n"
    r = co.padroes_ja_corrigidos(repo, contar_em="ecidade", git_runner=git_falso(log))
    p = {x["nome"]: x for x in r["padroes"]}
    assert p["parse_str_1_arg"]["registrados_no_estado"] == 1
    assert p["parse_str_1_arg"]["commits"][0]["assunto"].startswith("migra(parse_str_1_arg)")
    assert p["split"]["commits"][0]["hash"] == "abd456"
    assert p["parse_str_1_arg"]["restantes_em_contar_em"] == 5  # contagem e do codigo, nao do estado
    assert p["parse_str_1_arg"]["forma_canonica"].startswith("parse_str(")


def test_padroes_ja_corrigidos_git_falha_vira_aviso(repo):
    r = co.padroes_ja_corrigidos(repo, git_runner=git_falso("", 128))
    assert any("git" in a for a in r["avisos"])
