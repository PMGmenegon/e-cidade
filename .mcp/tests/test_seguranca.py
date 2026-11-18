import os
from pathlib import Path

import pytest

from servidor.config import Config, carregar_config
from servidor.seguranca import (
    ErroFerramenta,
    eh_segredo,
    limitar,
    relativo,
    resolver_caminho,
    validar_regex,
)


def test_config_padroes_do_ambiente_e74(raiz):
    c = carregar_config({"ECIDADE_MCP_RAIZ": str(raiz)})
    assert c.raiz == raiz.resolve()
    assert c.container_ref == "ecidade74_php74"
    assert c.container_alvo == "ecidade74_php85"
    assert c.container_banco == "ecidade74_database"
    assert c.expira_horas == 4.0
    assert c.arquivo_estado == raiz.resolve() / ".mcp" / "estado" / "trabalho.json"


def test_config_nomes_de_conteiner_por_env(raiz):
    c = carregar_config({
        "ECIDADE_MCP_RAIZ": str(raiz),
        "REGRESSAO_CONTAINER_REF": "outro74",
        "REGRESSAO_CONTAINER_PHP_NOVO": "outro85",
        "ECIDADE_MCP_EXPIRA_HORAS": "1.5",
    })
    assert (c.container_ref, c.container_alvo, c.expira_horas) == ("outro74", "outro85", 1.5)


def test_config_raiz_padrao_e_o_repositorio():
    c = carregar_config({})
    assert (c.raiz / ".mcp" / "servidor" / "config.py").is_file()


def test_config_env_invalida_vira_erro_estruturado(raiz):
    with pytest.raises(ErroFerramenta) as e:
        carregar_config({"ECIDADE_MCP_RAIZ": str(raiz), "ECIDADE_MCP_EXPIRA_HORAS": "abc"})
    assert e.value.codigo == "config_invalida"


def test_resolve_relativo_dentro_da_raiz(config):
    p = resolver_caminho(config.raiz, "ecidade/tela001.php")
    assert p == config.raiz / "ecidade" / "tela001.php"
    assert relativo(config.raiz, p) == "ecidade/tela001.php"


@pytest.mark.parametrize("caminho", ["../fora.txt", "ecidade/../../fora.txt", "ecidade/../ecidade/tela001.php"])
def test_bloqueia_ponto_ponto(config, caminho):
    with pytest.raises(ErroFerramenta) as e:
        resolver_caminho(config.raiz, caminho)
    assert e.value.codigo == "caminho_fora_da_raiz"


def test_bloqueia_absoluto_fora(config, tmp_path):
    fora = tmp_path / "fora.txt"
    fora.write_text("x")
    with pytest.raises(ErroFerramenta) as e:
        resolver_caminho(config.raiz, str(fora))
    assert e.value.codigo == "caminho_fora_da_raiz"


def test_aceita_absoluto_dentro(config):
    p = resolver_caminho(config.raiz, str(config.raiz / "ecidade" / "tela001.php"))
    assert p.name == "tela001.php"


def test_symlink_para_fora_e_bloqueado(config, tmp_path):
    fora = tmp_path / "segredo.txt"
    fora.write_text("x")
    os.symlink(fora, config.raiz / "ecidade" / "atalho.php")
    with pytest.raises(ErroFerramenta) as e:
        resolver_caminho(config.raiz, "ecidade/atalho.php")
    assert e.value.codigo == "caminho_fora_da_raiz"


def test_diretorio_symlink_para_fora_e_bloqueado(config, tmp_path):
    d = tmp_path / "outro"
    d.mkdir()
    (d / "a.php").write_text("<?php")
    os.symlink(d, config.raiz / "ecidade" / "dir")
    with pytest.raises(ErroFerramenta):
        resolver_caminho(config.raiz, "ecidade/dir/a.php")


@pytest.mark.parametrize("caminho", [".git/config", "ecidade/.env", "ecidade/storage/oauth-private.key",
                                     "ecidade/libs/db_conn.php"])
def test_bloqueia_git_e_segredos(config, caminho):
    alvo = config.raiz / caminho
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text("segredo")
    with pytest.raises(ErroFerramenta) as e:
        resolver_caminho(config.raiz, caminho)
    assert e.value.codigo == "caminho_proibido"


def test_env_example_nao_e_segredo():
    assert not eh_segredo(Path("ecidade/.env.example"))
    assert eh_segredo(Path("ecidade/.env"))


def test_inexistente_e_tipo(config):
    with pytest.raises(ErroFerramenta) as e:
        resolver_caminho(config.raiz, "ecidade/nao_existe.php")
    assert e.value.codigo == "caminho_inexistente"
    with pytest.raises(ErroFerramenta) as e:
        resolver_caminho(config.raiz, "ecidade", tipo="arquivo")
    assert e.value.codigo == "tipo_invalido"
    assert resolver_caminho(config.raiz, "ecidade/novo.php", deve_existir=False).name == "novo.php"


@pytest.mark.parametrize("caminho", ["", "a\x00b", "x" * 2000])
def test_caminho_malformado(config, caminho):
    with pytest.raises(ErroFerramenta) as e:
        resolver_caminho(config.raiz, caminho)
    assert e.value.codigo == "caminho_invalido"


def test_regex_validada():
    assert validar_regex(r"parse_str\(").search("parse_str(")
    with pytest.raises(ErroFerramenta) as e:
        validar_regex("(")
    assert e.value.codigo == "regex_invalida"
    with pytest.raises(ErroFerramenta):
        validar_regex("a" * 500)


def test_limitar():
    assert limitar("abc", 10) == ("abc", False)
    texto, cortado = limitar("x" * 100, 10)
    assert cortado and texto.startswith("x" * 10) and "truncado" in texto


def test_erro_como_dict():
    e = ErroFerramenta("codigo_x", "mensagem", detalhe=1)
    assert e.como_dict() == {"codigo": "codigo_x", "mensagem": "mensagem", "detalhes": {"detalhe": 1}}
