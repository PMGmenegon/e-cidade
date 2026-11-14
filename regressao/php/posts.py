import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from regressao.nucleo.banco import ErroAmbienteBanco, com_log_statement
from regressao.nucleo.veredito import Caso, Veredito

RAIZ = Path(__file__).resolve().parents[2]
SCRATCH = RAIZ / "scratchpad"
CATALOGO = Path(__file__).resolve().parent / "catalogo_posts.tsv"
TIMEOUT_POST = 900  # dois POSTs + snapshot/restore de tabelas

# O que escrita_post.py REALMENTE imprime (verificado no codigo, nao so na doc):
#   "  == SQL de escrita de NEGOCIO IDENTICO nos dois runtimes ==" (exit 0)
#   "  == DIVERGE ==" seguido de pares "    5.6: <sql>" / "    8.5: <sql>" (exit 1)
#   "  == INCONCLUSIVO: nenhuma escrita de negocio nos DOIS runtimes ==" (exit 2)
#   "ABORTADO: <motivo>" via sys.exit(str): vai para STDERR, exit 1
#   "  ATENCAO: a tela gravou tambem em <t1, t2>, que NAO e restaurada." (informativo)
# Os marcadores sao ancorados no inicio da linha: as linhas de SQL ("    5.6> ...") podem
# conter qualquer texto, inclusive essas frases.
_IDENTICO = re.compile(r"^\s*== SQL de escrita de NEGOCIO IDENTICO nos dois runtimes ==\s*$", re.M)
_DIVERGE = re.compile(r"^\s*== DIVERGE ==\s*$", re.M)
_INCONCLUSIVO = re.compile(r"^\s*== INCONCLUSIVO\b", re.M)
_ABORTADO = re.compile(r"^ABORTADO:\s*(.*)$", re.M)
_ATENCAO = re.compile(r"^\s*ATENCAO: a tela gravou tambem em (.+?), que NAO e restaurada", re.M)
_PAR_SQL = re.compile(r"^\s{4}(5\.6|8\.5): .*$", re.M)
_TABELA_FK = re.compile(r'on table "([^"]+)"')


@dataclass
class PostCaso:
    tela: str
    tabelas: list[str]  # filhas ANTES da mae
    campos: str
    area: str


def carrega_catalogo(tsv: Path) -> list[PostCaso]:
    """TSV `tela<TAB>tabelas(,)<TAB>campos<TAB>area[<TAB>comentario]`; ignora linhas
    em branco e as que comecam com '#'. A ordem das tabelas e a declarada."""
    casos = []
    for n, linha in enumerate(Path(tsv).read_text(encoding="utf-8").splitlines(), 1):
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        col = linha.split("\t")
        tela, tabelas, campos, area = (c.strip() for c in col[:4]) if len(col) >= 4 else ("",) * 4
        lista = [t.strip() for t in tabelas.split(",") if t.strip()]
        if not (tela and lista and campos and area) or not tela.endswith(".php"):
            raise ValueError(f"{tsv}: linha {n} malformada (esperado tela.php<TAB>tabelas<TAB>campos<TAB>area): {linha[:80]!r}")
        casos.append(PostCaso(tela, lista, campos, area))
    return casos


def parse_post(saida: str, caso: PostCaso) -> Caso:
    atencao = _ATENCAO.search(saida)
    nota = f"tabela(s) gravada(s) e NAO restaurada(s): {atencao.group(1)}" if atencao else ""
    if m := _ABORTADO.search(saida):
        motivo = m.group(1).strip()
        filhas = _TABELA_FK.findall(motivo)
        dica = (f"; acrescentar a tabela filha {filhas[-1]!r} ao catalogo (antes da mae) e conferir "
                f"se o POST do 5.6 deixou linha de teste") if filhas else \
               "; conferir o banco: o POST do 5.6 pode ter gravado antes do abort"
        return Caso(caso.tela, caso.area, Veredito.ERRO_AMBIENTE, f"ABORTADO: {motivo}{dica}")
    if _DIVERGE.search(saida):
        diff = "\n".join(l.strip() for l in saida.splitlines() if _PAR_SQL.match(l))
        return Caso(caso.tela, caso.area, Veredito.DIVERGE, nota or "SQL de escrita diverge", diff)
    if _INCONCLUSIVO.search(saida):
        return Caso(caso.tela, caso.area, Veredito.INCONCLUSIVO,
                    "nenhuma escrita de negocio nos dois runtimes (payload/validacao); nao aprovado")
    if _IDENTICO.search(saida):
        return Caso(caso.tela, caso.area, Veredito.IDENTICO, nota)
    return Caso(caso.tela, caso.area, Veredito.ERRO_AMBIENTE,
                f"saida irreconhecivel de escrita_post.py: {saida.strip()[-200:]!r}")


def _roda_escrita(sid: str, caso: PostCaso) -> str:
    """Unico ponto que executa escrita_post.py (mockavel nos testes). stdout+stderr: o
    ABORTADO sai em stderr."""
    r = subprocess.run(
        ["python3", str(SCRATCH / "escrita_post.py"), sid, caso.tela, ",".join(caso.tabelas), caso.campos],
        capture_output=True, timeout=TIMEOUT_POST, cwd=RAIZ,
    )
    return (r.stdout + b"\n" + r.stderr).decode("utf-8", errors="replace")


def roda_post(sid: str, caso: PostCaso) -> Caso:
    """Liga log_statement='all' (com_log_statement, que sempre faz RESET em finally), roda
    escrita_post.py e interpreta a saida. Excecoes que nao sejam de ambiente se propagam,
    mas so depois do RESET."""
    try:
        with com_log_statement():
            saida = _roda_escrita(sid, caso)
    except subprocess.TimeoutExpired as e:
        return Caso(caso.tela, caso.area, Veredito.ERRO_AMBIENTE,
                    f"timeout de {e.timeout}s em escrita_post.py; tabelas podem nao ter sido restauradas")
    except (ErroAmbienteBanco, OSError) as e:
        return Caso(caso.tela, caso.area, Veredito.ERRO_AMBIENTE, str(e))
    return parse_post(saida, caso)
