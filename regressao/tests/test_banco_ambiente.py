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
    monkeypatch.setattr(ambiente, "containers_ativos", lambda: {"ecidade_database"})
    alvos = ambiente.Alvos(
        ref="http://127.0.0.1:1",
        php_novo="http://127.0.0.1:1/php",
        laravel_novo="http://127.0.0.1:1/lv",
        proxy="http://127.0.0.1:1/px",
    )
    problemas = ambiente.verifica(alvos)
    assert len(problemas) == 4
    for url in (alvos.ref, alvos.php_novo, alvos.laravel_novo, alvos.proxy):
        assert any(url in p for p in problemas)


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
    assert "db_usuarios" in sqls[0] and "order by t::text" in sqls[0]


def test_confere_baseline_sem_sha256_levanta(tmp_path, monkeypatch):
    sha = tmp_path / "baseline.dump.sha256"
    monkeypatch.setattr(banco, "ARQ_SHA256", sha)
    dump = tmp_path / "baseline.dump"
    dump.write_bytes(b"x")
    with pytest.raises(banco.BancoDiferente, match="baseline.dump.sha256"):
        banco.confere_baseline(dump)


def test_confere_baseline_sem_dump_levanta(tmp_path, monkeypatch):
    sha = tmp_path / "baseline.dump.sha256"
    monkeypatch.setattr(banco, "ARQ_SHA256", sha)
    sha.write_text("abc\n")
    with pytest.raises(banco.BancoDiferente, match="inexistente.dump"):
        banco.confere_baseline(tmp_path / "inexistente.dump")


def test_confere_baseline_sha256_vazio_levanta(tmp_path, monkeypatch):
    sha = tmp_path / "baseline.dump.sha256"
    monkeypatch.setattr(banco, "ARQ_SHA256", sha)
    sha.write_text("  \n")
    dump = tmp_path / "baseline.dump"
    dump.write_bytes(b"x")
    with pytest.raises(banco.BancoDiferente, match="baseline.dump.sha256"):
        banco.confere_baseline(dump)


class _Res:
    def __init__(self, rc=0, out=b"", err=b""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def test_erro_do_docker_inclui_stderr(monkeypatch):
    monkeypatch.setattr(
        banco.subprocess, "run", lambda *a, **k: _Res(3, b"", "falha ".encode() + bytes([0xe7]))
    )
    with pytest.raises(banco.ErroAmbienteBanco) as e:
        banco._psql("select 1")
    assert "falha" in str(e.value) and "3" in str(e.value)


def test_docker_ausente_vira_erro_ambiente_banco(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(banco.subprocess, "run", boom)
    with pytest.raises(banco.ErroAmbienteBanco):
        banco._psql("select 1")


def test_timeout_vira_erro_ambiente_banco(monkeypatch):
    def boom(*a, **k):
        raise banco.subprocess.TimeoutExpired("docker", 60)

    monkeypatch.setattr(banco.subprocess, "run", boom)
    with pytest.raises(banco.ErroAmbienteBanco):
        banco._psql("select 1")


def test_hash_tabelas_usa_ordenacao_por_texto_da_linha(monkeypatch):
    sqls = []
    monkeypatch.setattr(banco, "_psql", lambda sql, db="ecidade": sqls.append(sql) or "h\n")
    banco.hash_tabelas(["db_usuarios"])
    assert "order by t::text" in sqls[0]
    assert "order by 1" not in sqls[0]


def test_hash_tabelas_rejeita_nome_invalido(monkeypatch):
    monkeypatch.setattr(banco, "_psql", lambda sql, db="ecidade": "h")
    with pytest.raises(ValueError):
        banco.hash_tabelas(["x; drop table y"])


def test_restaura_dump_recria_banco_e_restaura_com_create(tmp_path, monkeypatch):
    chamadas = []

    def falso(*a, **k):
        chamadas.append((a[0], k))
        return _Res()

    monkeypatch.setattr(banco.subprocess, "run", falso)
    dump = tmp_path / "d.dump"
    dump.write_bytes(b"x")
    banco.restaura_dump(dump)
    assert len(chamadas) == 3
    (a1, _), (a2, _), (a3, k3) = chamadas
    assert "pg_terminate_backend" in a1[-1] and "postgres" in a1
    assert "datname='ecidade'" in a1[-1] and "pg_backend_pid()" in a1[-1]
    assert a2[-1] == "DROP DATABASE IF EXISTS ecidade" and "postgres" in a2
    assert "pg_restore" in a3 and "--create" in a3 and "--exit-on-error" in a3
    assert "--clean" not in a3 and "--single-transaction" not in a3
    assert a3[a3.index("-d") + 1] == "postgres"
    assert k3["timeout"] == 900


def test_restaura_dump_falha_vira_erro_ambiente_banco(tmp_path, monkeypatch):
    monkeypatch.setattr(banco.subprocess, "run", lambda *a, **k: _Res(1, b"", b"boom"))
    dump = tmp_path / "d.dump"
    dump.write_bytes(b"x")
    with pytest.raises(banco.ErroAmbienteBanco, match="boom"):
        banco.restaura_dump(dump)


def test_gera_dump_usa_create(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(banco, "ARQ_SHA256", tmp_path / "x.sha256")

    def falso(*a, **k):
        chamadas.append(a[0])
        return _Res()

    monkeypatch.setattr(banco.subprocess, "run", falso)
    banco.gera_dump(tmp_path / "d.dump")
    assert "--create" in chamadas[0] and "-Fc" in chamadas[0]


def test_hash_tabelas_aceita_schema_qualificado(monkeypatch):
    sqls = []
    monkeypatch.setattr(banco, "_psql", lambda sql, db="ecidade": sqls.append(sql) or "h")
    banco.hash_tabelas(["configuracoes.db_usuarios"])
    assert "from configuracoes.db_usuarios t" in sqls[0]


@pytest.mark.parametrize("nome", ["a.b.c", "x; drop table y", "A.b", "a."])
def test_hash_tabelas_rejeita_nomes_invalidos_com_schema(monkeypatch, nome):
    monkeypatch.setattr(banco, "_psql", lambda sql, db="ecidade": "h")
    with pytest.raises(ValueError):
        banco.hash_tabelas([nome])
