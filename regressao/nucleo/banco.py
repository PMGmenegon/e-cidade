import hashlib
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path

CONTAINER = "ecidade_database"
BASE = "ecidade"
DIR_BASELINE = Path(__file__).resolve().parent.parent / "baseline"
ARQ_DUMP = DIR_BASELINE / "baseline.dump"
ARQ_SHA256 = DIR_BASELINE / "baseline.dump.sha256"


class BancoDiferente(Exception):
    """Banco/dump difere do baseline registrado. Orquestradores mapeiam para ERRO_AMBIENTE."""


class ErroAmbienteBanco(Exception):
    """Falha ao executar docker/psql/pg_dump/pg_restore. Orquestradores mapeiam para ERRO_AMBIENTE."""


TIMEOUT_PSQL = 60
TIMEOUT_DUMP = 900
_NOME_TABELA = re.compile(r"[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?")


def _sha256(arquivo: Path) -> str:
    h = hashlib.sha256()
    with open(arquivo, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _docker(args: list[str], timeout: int, stdin=None, stdout=None) -> bytes:
    """Unico ponto de chamada ao docker (mockavel nos testes)."""
    cmd = ["docker", *args]
    try:
        r = subprocess.run(
            cmd, stdin=stdin, stdout=stdout if stdout is not None else subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=timeout,
        )
    except FileNotFoundError as e:
        raise ErroAmbienteBanco(f"docker ausente: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise ErroAmbienteBanco(f"timeout de {timeout}s: {' '.join(cmd)}") from e
    if r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", errors="replace").strip()
        raise ErroAmbienteBanco(f"codigo de saida {r.returncode}: {' '.join(cmd)}: {err}")
    return r.stdout or b""


def _psql(sql: str, db: str = BASE) -> str:
    saida = _docker(
        ["exec", CONTAINER, "psql", "-U", "postgres", "-d", db,
         "-At", "-v", "ON_ERROR_STOP=1", "-c", sql],
        TIMEOUT_PSQL,
    )
    return saida.decode("utf-8", errors="replace")


def gera_dump(destino: Path) -> str:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        _docker(["exec", CONTAINER, "pg_dump", "-U", "postgres", "-Fc", "--create", BASE],
                TIMEOUT_DUMP, stdout=f)
    sha = _sha256(destino)
    ARQ_SHA256.parent.mkdir(parents=True, exist_ok=True)
    ARQ_SHA256.write_text(sha + "\n")
    return sha


def restaura_dump(dump: Path) -> None:
    """Recria o banco `ecidade` a partir do dump (gerado com --create).

    Derruba as conexoes, executa DROP DATABASE e restaura em banco novo (sem
    --clean/--single-transaction, que esgotam a tabela de locks). Uma falha
    deixa o banco inutilizavel: o orquestrador deve rejeitar a execucao
    (ERRO_AMBIENTE) e simplesmente repetir a restauracao, que comeca por DROP.
    """
    _psql(f"select pg_terminate_backend(pid) from pg_stat_activity "
          f"where datname='{BASE}' and pid<>pg_backend_pid()", db="postgres")
    _psql(f"DROP DATABASE IF EXISTS {BASE}", db="postgres")
    with open(dump, "rb") as f:
        _docker(["exec", "-i", CONTAINER, "pg_restore", "-U", "postgres",
                 "--create", "--exit-on-error", "-d", "postgres"],
                TIMEOUT_DUMP, stdin=f)


def confere_baseline(dump: Path) -> None:
    dump = Path(dump)
    if not ARQ_SHA256.is_file():
        raise BancoDiferente(f"hash registrado ausente: {ARQ_SHA256}")
    partes = ARQ_SHA256.read_text().split()
    if not partes:
        raise BancoDiferente(f"arquivo de hash vazio ou invalido: {ARQ_SHA256}")
    if not dump.is_file():
        raise BancoDiferente(f"dump inexistente: {dump}")
    esperado = partes[0]
    atual = _sha256(dump)
    if atual != esperado:
        raise BancoDiferente(f"sha256 do dump {atual} != registrado {esperado}")


def hash_tabelas(tabelas: list[str]) -> dict[str, str]:
    saida = {}
    for t in tabelas:
        if not _NOME_TABELA.fullmatch(t):
            raise ValueError(f"nome de tabela invalido: {t!r}")
        sql = (f"select md5(coalesce(string_agg(t::text, E'\\n' order by t::text), '')) "
               f"from {t} t")
        saida[t] = _psql(sql).strip()
    return saida


@contextmanager
def com_log_statement():
    _psql(f"ALTER DATABASE {BASE} SET log_statement='all'")
    try:
        yield
    finally:
        _psql(f"ALTER DATABASE {BASE} RESET log_statement")
