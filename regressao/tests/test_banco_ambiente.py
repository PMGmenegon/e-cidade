import hashlib

import pytest

from regressao.nucleo import ambiente, banco


def test_confere_baseline_rejeita_dump_alterado(tmp_path, monkeypatch):
    sha = tmp_path / "baseline.dump.sha256"
    monkeypatch.setattr(banco, "ARQ_SHA256", sha)
    sha.write_text(hashlib.sha256(b"original").hexdigest() + "\n")
    dump = tmp_path / "baseline.dump"
    dump.write_bytes(b"alterado")
    with pytest.raises(banco.BancoDiferente):
        banco.confere_baseline(dump)


def test_confere_baseline_aceita_dump_igual(tmp_path, monkeypatch):
    sha = tmp_path / "baseline.dump.sha256"
    monkeypatch.setattr(banco, "ARQ_SHA256", sha)
    sha.write_text(hashlib.sha256(b"original").hexdigest() + "\n")
    dump = tmp_path / "baseline.dump"
    dump.write_bytes(b"original")
    banco.confere_baseline(dump)


def test_alvos_usam_variaveis_de_ambiente(monkeypatch):
    for v in ("REF", "PHP_NOVO", "LARAVEL_NOVO", "PROXY"):
        monkeypatch.delenv(f"REGRESSAO_{v}_URL", raising=False)
    padrao = ambiente.alvos_do_ambiente()
    assert padrao.ref == "http://localhost:8080"
    assert padrao.php_novo == "http://localhost:8085"
    assert padrao.laravel_novo == "http://localhost:8087"
    assert padrao.proxy == "http://localhost:8090"
    monkeypatch.setenv("REGRESSAO_REF_URL", "http://x:1")
    monkeypatch.setenv("REGRESSAO_PROXY_URL", "http://y:2")
    alvos = ambiente.alvos_do_ambiente()
    assert alvos.ref == "http://x:1"
    assert alvos.proxy == "http://y:2"
    assert alvos.php_novo == "http://localhost:8085"


def test_verifica_reporta_alvo_fora(monkeypatch):
    monkeypatch.setattr(ambiente, "containers_ativos", lambda: None)
    alvos = ambiente.Alvos(
        ref="http://127.0.0.1:1",
        php_novo="http://127.0.0.1:1/php",
        laravel_novo="http://127.0.0.1:1/lv",
        proxy="http://127.0.0.1:1/px",
    )
    problemas = ambiente.verifica(alvos)
    assert any("http://127.0.0.1:1" in p for p in problemas)


def test_verifica_reporta_container_ausente(monkeypatch):
    monkeypatch.setattr(ambiente, "containers_ativos", lambda: {"outro"})
    monkeypatch.setattr(ambiente, "_responde", lambda url: True)
    alvos = ambiente.Alvos("http://a", "http://b", "http://c", "http://d")
    problemas = ambiente.verifica(alvos)
    assert any("ecidade_database" in p for p in problemas)


def test_com_log_statement_reseta_mesmo_com_excecao(monkeypatch):
    chamadas = []
    monkeypatch.setattr(banco, "_psql", lambda sql, db="ecidade": chamadas.append(sql) or "")
    with pytest.raises(RuntimeError):
        with banco.com_log_statement():
            raise RuntimeError("falha")
    assert chamadas == [
        "ALTER DATABASE ecidade SET log_statement='all'",
        "ALTER DATABASE ecidade RESET log_statement",
    ]


def test_hash_tabelas_usa_psql(monkeypatch):
    sqls = []

    def falso(sql, db="ecidade"):
        sqls.append(sql)
        return "abc123\n"

    monkeypatch.setattr(banco, "_psql", falso)
    assert banco.hash_tabelas(["db_usuarios"]) == {"db_usuarios": "abc123"}
    assert "db_usuarios" in sqls[0] and "order by 1" in sqls[0]
