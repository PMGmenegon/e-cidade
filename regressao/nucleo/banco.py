import hashlib
import subprocess
from contextlib import contextmanager
from pathlib import Path

CONTAINER = "ecidade_database"
BASE = "ecidade"
DIR_BASELINE = Path(__file__).resolve().parent.parent / "baseline"
ARQ_DUMP = DIR_BASELINE / "baseline.dump"
ARQ_SHA256 = DIR_BASELINE / "baseline.dump.sha256"


class BancoDiferente(Exception):
    pass


def _sha256(arquivo: Path) -> str:
    h = hashlib.sha256()
    with open(arquivo, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _psql(sql: str, db: str = BASE) -> str:
    """Unico ponto de chamada ao psql no container (mockavel nos testes)."""
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", "postgres", "-d", db,
         "-At", "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True, text=True, check=True,
    )
    return r.stdout


def gera_dump(destino: Path) -> str:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        subprocess.run(
            ["docker", "exec", CONTAINER, "pg_dump", "-U", "postgres", "-Fc", BASE],
            stdout=f, check=True,
        )
    sha = _sha256(destino)
    ARQ_SHA256.parent.mkdir(parents=True, exist_ok=True)
    ARQ_SHA256.write_text(sha + "\n")
    return sha


def restaura_dump(dump: Path) -> None:
    with open(dump, "rb") as f:
        subprocess.run(
            ["docker", "exec", "-i", CONTAINER, "pg_restore", "-U", "postgres",
             "--clean", "--if-exists", "-d", BASE],
            stdin=f, check=True,
        )


def confere_baseline(dump: Path) -> None:
    dump = Path(dump)
    if not ARQ_SHA256.exists():
        raise BancoDiferente(f"hash registrado ausente: {ARQ_SHA256}")
    esperado = ARQ_SHA256.read_text().split()[0]
    atual = _sha256(dump)
    if atual != esperado:
        raise BancoDiferente(f"sha256 do dump {atual} != registrado {esperado}")


def hash_tabelas(tabelas: list[str]) -> dict[str, str]:
    saida = {}
    for t in tabelas:
        sql = f"select md5(coalesce(string_agg(x::text, E'\\n'), '')) from (select * from {t} order by 1) x"
        saida[t] = _psql(sql).strip()
    return saida


@contextmanager
def com_log_statement():
    _psql(f"ALTER DATABASE {BASE} SET log_statement='all'")
    try:
        yield
    finally:
        _psql(f"ALTER DATABASE {BASE} RESET log_statement")
