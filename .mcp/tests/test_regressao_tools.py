import json
import os
import subprocess
import sys

import pytest

from servidor.docker_exec import DockerExec
from servidor.seguranca import ErroFerramenta
from servidor.tools.regressao import ler_resultado_regressao, ler_triagem, rodar_regressao


def docker_ok(argv, **kw):
    return subprocess.CompletedProcess(argv, 0, "true\n", "")


def docker_sem(nome):
    def run(argv, **kw):
        if argv[-1] == nome:
            return subprocess.CompletedProcess(argv, 1, "", "Error: No such object")
        return subprocess.CompletedProcess(argv, 0, "true\n", "")
    return run


class FakePopen:
    chamadas = []

    def __init__(self, argv, **kw):
        FakePopen.chamadas.append((argv, kw))
        self.pid = 999999


@pytest.fixture
def cfg(config):
    py = config.raiz / "regressao" / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("")
    FakePopen.chamadas = []
    return config


def roda(cfg, runner=docker_ok, **kw):
    return rodar_regressao(cfg, docker=DockerExec(cfg, runner=runner), popen=FakePopen, **kw)


def test_rodar_php_por_prefixo_destacado(cfg):
    r = roda(cfg, bateria="php", prefixo=["^arr1_grupotaxa001\\.php$"], quem="ana")
    assert r["status"] == "iniciada" and r["id"].endswith(r["id"][-4:])
    argv, kw = FakePopen.chamadas[0]
    assert argv[0] == sys.executable and argv[1].endswith("executor.py")
    assert kw["start_new_session"] is True and kw["stdin"] == subprocess.DEVNULL
    assert kw["cwd"] == str(cfg.raiz)
    meta = json.loads((cfg.dir_rodadas / r["id"] / "meta.json").read_text())
    assert meta["argv"][0] == str(cfg.raiz / "regressao/.venv/bin/python")
    assert meta["argv"][1:4] == ["-m", "regressao.php.bateria", "--saida"]
    assert meta["argv"][4] == str(cfg.dir_rodadas / r["id"] / "saida")
    assert meta["argv"][5:] == ["--prefixo=^arr1_grupotaxa001\\.php$"]
    assert meta["quem"] == "ana" and meta["pid"] == 999999


def test_laravel_so_compara_nunca_grava(cfg):
    r = roda(cfg, bateria="laravel")
    meta = json.loads((cfg.dir_rodadas / r["id"] / "meta.json").read_text())
    assert meta["argv"][2:4] == ["regressao.laravel.bateria", "comparar"]
    assert "gravar" not in meta["argv"] and "--confirmo-sobrescrever" not in meta["argv"]


def test_fluxos_e_completa(cfg):
    r = roda(cfg, bateria="fluxos", fluxo=["navegacao"])
    meta = json.loads((cfg.dir_rodadas / r["id"] / "meta.json").read_text())
    assert meta["argv"][2:4] == ["regressao.completa.fluxos", "comparar"] and "--fluxo=navegacao" in meta["argv"]
    (cfg.dir_rodadas / r["id"] / "fim.json").write_text('{"codigo_saida": 0}')
    r = roda(cfg, bateria="completa", area=["tributario"], sem_fluxos=True)
    meta = json.loads((cfg.dir_rodadas / r["id"] / "meta.json").read_text())
    assert meta["argv"][2] == "regressao.completa.orquestra"
    assert "--area=tributario" in meta["argv"] and "--sem-fluxos" in meta["argv"]


def test_rodada_inteira_exige_confirmacao(cfg):
    with pytest.raises(ErroFerramenta) as e:
        roda(cfg, bateria="php")
    assert e.value.codigo == "confirmacao_necessaria"
    assert roda(cfg, bateria="php", confirmo_rodada_longa=True)["status"] == "iniciada"


@pytest.mark.parametrize("kw,codigo", [
    ({"bateria": "shell"}, "parametro_invalido"),
    ({"bateria": "php", "area": ["inexistente"]}, "parametro_invalido"),
    ({"bateria": "php", "prefixo": ["("]}, "regex_invalida"),
    ({"bateria": "fluxos", "fluxo": ["a; rm -rf /"]}, "parametro_invalido"),
    ({"bateria": "php", "prefixo": ["--sem-restaurar"]}, None),
])
def test_validacao_de_argumentos(cfg, kw, codigo):
    if codigo is None:
        r = roda(cfg, **kw)  # vira --prefixo=--sem-restaurar: nunca uma opcao solta
        meta = json.loads((cfg.dir_rodadas / r["id"] / "meta.json").read_text())
        assert "--sem-restaurar" not in meta["argv"] and "--prefixo=--sem-restaurar" in meta["argv"]
        return
    with pytest.raises(ErroFerramenta) as e:
        roda(cfg, **kw)
    assert e.value.codigo == codigo


def test_conteiner_ausente_nao_dispara(cfg):
    with pytest.raises(ErroFerramenta) as e:
        roda(cfg, runner=docker_sem("ecidade74_database"), bateria="php", prefixo=["^a"])
    assert e.value.codigo == "conteiner_indisponivel"
    assert FakePopen.chamadas == []


def test_venv_da_regressao_ausente(config):
    with pytest.raises(ErroFerramenta) as e:
        rodar_regressao(config, bateria="php", prefixo=["^a"], docker=DockerExec(config, runner=docker_ok),
                        popen=FakePopen)
    assert e.value.codigo == "venv_regressao_ausente"


def test_uma_rodada_por_vez(cfg):
    r = roda(cfg, bateria="php", prefixo=["^a"])
    meta = cfg.dir_rodadas / r["id"] / "meta.json"
    m = json.loads(meta.read_text())
    m["pid"] = os.getpid()  # processo vivo
    meta.write_text(json.dumps(m))
    with pytest.raises(ErroFerramenta) as e:
        roda(cfg, bateria="php", prefixo=["^b"], _cmdline_executor=lambda pid: True)
    assert e.value.codigo == "rodada_em_andamento"


# ---------- leitura ----------

def _rodada(cfg, rid="20261117-120000-php-abcd", fim=1, casos=None):
    d = cfg.dir_rodadas / rid
    (d / "saida").mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"id": rid, "bateria": "php", "inicio": "2026-11-17T12:00:00Z",
                                             "pid": 999999, "argv": []}))
    (d / "execucao.log").write_text("linha 1\nlinha 2\n")
    if fim is not None:
        (d / "fim.json").write_text(json.dumps({"codigo_saida": fim, "fim": "2026-11-17T12:10:00Z"}))
    casos = casos if casos is not None else [
        {"id": "php:tela:a.php", "area": "php-telas", "veredito": "DIVERGE", "detalhe": "200 x 500", "conhecida": False},
        {"id": "php:tela:b.php", "area": "php-telas", "veredito": "DIVERGE", "detalhe": "x", "conhecida": True},
        {"id": "php:tela:c.php", "area": "php-telas", "veredito": "INCONCLUSIVO", "detalhe": "500 nos dois lados",
         "conhecida": False},
        {"id": "php:tela:d.php", "area": "php-telas", "veredito": "IDENTICO", "detalhe": "", "conhecida": False},
        {"id": "php:amb", "area": "php", "veredito": "ERRO_AMBIENTE", "detalhe": "sessao invalida", "conhecida": False},
    ]
    (d / "saida" / "resultado.json").write_text(json.dumps({"meta": {"comparavel": True}, "casos": casos}))
    (d / "saida" / "resumo.md").write_text("# Resumo\n")
    return rid


def test_ler_resultado(cfg):
    rid = _rodada(cfg)
    r = ler_resultado_regressao(cfg, id=rid)
    assert r["status"] == "concluida" and r["codigo_saida"] == 1
    assert r["totais"] == {"IDENTICO": 1, "DIVERGE": 2, "INCONCLUSIVO": 1, "ERRO_AMBIENTE": 1}
    assert [c["id"] for c in r["divergencias_novas"]] == ["php:tela:a.php"]
    assert r["erros_ambiente"][0]["detalhe"] == "sessao invalida"
    assert r["inconclusivo_por_motivo"] == {"500 nos dois lados": 1}
    assert "INCONCLUSIVO" in r["aviso"] and "aprovacao" in r["aviso"]
    assert "linha 2" in r["log_final"] and r["resumo_md"].startswith("# Resumo")


def test_ler_em_andamento_e_interrompida(cfg):
    rid = _rodada(cfg, fim=None)
    r = ler_resultado_regressao(cfg, id=rid, _cmdline_executor=lambda pid: True)
    assert r["status"] == "em_andamento"
    r = ler_resultado_regressao(cfg, id=rid, _cmdline_executor=lambda pid: False)
    assert r["status"] == "interrompida"


def test_listar_rodadas(cfg):
    _rodada(cfg, "20261117-120000-php-abcd")
    _rodada(cfg, "20261117-130000-laravel-beef", fim=0, casos=[])
    r = ler_resultado_regressao(cfg)
    assert [x["id"] for x in r["rodadas"]] == ["20261117-130000-laravel-beef", "20261117-120000-php-abcd"]


@pytest.mark.parametrize("rid", ["../../etc", "20261117-120000-php-zzzz", "x"])
def test_id_invalido(cfg, rid):
    with pytest.raises(ErroFerramenta) as e:
        ler_resultado_regressao(cfg, id=rid)
    assert e.value.codigo in ("parametro_invalido", "rodada_inexistente")


def test_ler_pasta_dentro_do_repo(cfg):
    d = cfg.raiz / "regressao" / "rodada-manual"
    d.mkdir()
    (d / "resultado.json").write_text(json.dumps({"meta": {}, "casos": []}))
    r = ler_resultado_regressao(cfg, pasta="regressao/rodada-manual")
    assert r["totais"] == {"IDENTICO": 0, "DIVERGE": 0, "INCONCLUSIVO": 0, "ERRO_AMBIENTE": 0}
    with pytest.raises(ErroFerramenta):
        ler_resultado_regressao(cfg, pasta="/tmp")


# ---------- triagem ----------

TRIAGEM = """# Triagem dos DIVERGE (7.4 x 8.5)

Intro.

## Categoria parse_str

parse_str de 1 argumento em ~460 telas.

## Construtor PHP4

classes sem __construct.

### Detalhe

sub.

## Outra
fim
"""


def test_ler_triagem(cfg):
    (cfg.raiz / "regressao" / "baseline" / "triagem-divergencias.md").write_text(TRIAGEM)
    r = ler_triagem(cfg)
    assert [s["titulo"] for s in r["secoes"]][:3] == ["Triagem dos DIVERGE (7.4 x 8.5)", "Categoria parse_str",
                                                      "Construtor PHP4"]
    assert r["base"] == "7.4 x 8.5"
    r = ler_triagem(cfg, secao="construtor")
    assert "classes sem __construct" in r["texto"] and "sub." in r["texto"] and "fim" not in r["texto"]
    r = ler_triagem(cfg, busca="460")
    assert r["linhas"] == [{"linha": 7, "texto": "parse_str de 1 argumento em ~460 telas."}]


def test_triagem_inexistente(cfg):
    with pytest.raises(ErroFerramenta) as e:
        ler_triagem(cfg, documento="como_usar")
    assert e.value.codigo == "documento_inexistente"
