import os

import pytest

from servidor.busca import buscar, iterar_arquivos
from servidor.seguranca import ErroFerramenta


@pytest.fixture
def repo(config):
    e = config.raiz / "ecidade"
    (e / "tela002.php").write_text("<?php\n$a = split('-', $b);\nparse_str($x, $__qs);\n")
    (e / "classes" / "db_x_classe.php").write_text("<?php\nclass cl_x {\n  function cl_x() {}\n}\n")
    (e / "latin1.php").write_bytes("<?php\n// Situa\xe7\xe3o\nparse_str($q);\n".encode("latin-1").replace(b"\\xe7", b"\xe7"))
    (e / "vendor" / "pkg").mkdir(parents=True)
    (e / "vendor" / "pkg" / "v.php").write_text("<?php parse_str($q);")
    (e / ".env").write_text("parse_str($senha);")
    (e / "js.js").write_text("parse_str($q);")
    return config


def test_padrao_nomeado(repo):
    r = buscar(repo, padrao="parse_str_1_arg")
    arquivos = sorted({o["arquivo"] for o in r["ocorrencias"]})
    assert arquivos == ["ecidade/latin1.php", "ecidade/tela001.php"]
    o = [x for x in r["ocorrencias"] if x["arquivo"] == "ecidade/tela001.php"][0]
    assert o["linha"] == 2 and o["padrao"] == "parse_str_1_arg" and "parse_str" in o["trecho"]
    assert r["totais_por_padrao"] == {"parse_str_1_arg": 2}
    assert r["truncado"] is False


def test_latin1_nao_quebra(repo):
    r = buscar(repo, padrao="parse_str_1_arg", caminho="ecidade/latin1.php")
    assert r["ocorrencias"][0]["linha"] == 3


def test_pula_vendor_segredos_e_extensoes(repo):
    r = buscar(repo, padrao="parse_str_1_arg")
    nomes = {o["arquivo"] for o in r["ocorrencias"]}
    assert not any("vendor" in n or n.endswith(".env") or n.endswith(".js") for n in nomes)


def test_todos(repo):
    r = buscar(repo, padrao="todos")
    assert r["totais_por_padrao"]["split"] == 1
    assert r["totais_por_padrao"]["construtor_php4"] == 1
    assert "count_null" not in r["totais_por_padrao"]


def test_regex_livre(repo):
    r = buscar(repo, regex=r"\$__qs")
    assert [(o["arquivo"], o["linha"]) for o in r["ocorrencias"]] == [("ecidade/tela002.php", 3)]
    assert r["ocorrencias"][0]["padrao"] == "regex"


def test_limite_trunca(repo):
    for i in range(5):
        (repo.raiz / "ecidade" / f"m{i}.php").write_text("<?php\nparse_str($a);\nparse_str($b);\n")
    r = buscar(repo, padrao="parse_str_1_arg", limite=3)
    assert len(r["ocorrencias"]) == 3 and r["truncado"] is True and "limite" in r["motivo_truncado"]


def test_sem_padrao_nem_regex_lista_catalogo(repo):
    r = buscar(repo)
    assert any(p["nome"] == "parse_str_1_arg" for p in r["catalogo"])


def test_padrao_e_regex_juntos_e_erro(repo):
    with pytest.raises(ErroFerramenta) as e:
        buscar(repo, padrao="split", regex="x")
    assert e.value.codigo == "parametro_invalido"


def test_padrao_desconhecido(repo):
    with pytest.raises(ErroFerramenta) as e:
        buscar(repo, padrao="nao_existe")
    assert e.value.codigo == "padrao_desconhecido"


def test_caminho_confinado(repo):
    with pytest.raises(ErroFerramenta) as e:
        buscar(repo, padrao="split", caminho="../")
    assert e.value.codigo == "caminho_fora_da_raiz"


def test_symlink_para_fora_e_ignorado_na_varredura(repo, tmp_path):
    fora = tmp_path / "fora"
    fora.mkdir()
    (fora / "x.php").write_text("<?php parse_str($q);")
    os.symlink(fora / "x.php", repo.raiz / "ecidade" / "link.php")
    nomes = {o["arquivo"] for o in buscar(repo, padrao="parse_str_1_arg")["ocorrencias"]}
    assert "ecidade/link.php" not in nomes


def test_prazo_esgotado_devolve_parcial(repo):
    r = buscar(repo, padrao="parse_str_1_arg", prazo_s=0)
    assert r["truncado"] is True and "tempo" in r["motivo_truncado"]


def test_iterar_ignora_git(repo):
    (repo.raiz / ".git").mkdir()
    (repo.raiz / ".git" / "a.php").write_text("x")
    todos = [p.relative_to(repo.raiz).as_posix() for p in iterar_arquivos(repo, repo.raiz, (".php",))]
    assert not any(t.startswith(".git") for t in todos)
