import os
import re
import subprocess
from pathlib import Path

from regressao.nucleo.banco import ErroAmbienteBanco, _docker
from regressao.nucleo.veredito import Caso, Veredito

RAIZ = Path(__file__).resolve().parents[2]
SCRATCH = RAIZ / "scratchpad"
DIR_TELAS = RAIZ / "ecidade"
# Telas que cmp.py nunca requisita (contatam servico externo); espelha PULAR de cmp.py.
PULAR = {"iss4_siss002.php"}
TIMEOUT_SID = 30
TIMEOUT_CMP = 6 * 3600

_DIVERGE = re.compile(r"^\s*DIVERGE\s+(\S+)\s+(56=\S+)\s+(85=\S+)")
_TIMEOUT = re.compile(r"^\s*TIMEOUT\s+(\S+)\s+(56=\S+)\s+(85=\S+)")
_PULADA = re.compile(r"^\s*PULADA\s+(\S+)")
_RESUMO = re.compile(r"^=== (\d+)/(\d+) identicas, (\d+) divergentes, (\d+) timeout ===")


def parse_cmp(saida: str, area: str, telas: list[str] | None = None,
              corpos: dict[str, bytes] | None = None) -> list[Caso]:
    """Interpreta o que cmp.py REALMENTE imprime: so imprime as telas DIVERGE, TIMEOUT e
    PULADA, mais o resumo '=== N/M identicas, X divergentes, Y timeout ===' (nao ha
    linha por tela identica). Por isso:
    - `telas` (lista que cmp.py percorreu, ver lista_telas) permite gerar um Caso IDENTICO
      por tela; sem ela, as identicas viram um unico Caso 'identicas' com a contagem.
    - `corpos` opcional: tela identica com corpo vazio vira INCONCLUSIVO (cmp.py nao
      informa tamanho das identicas; so o chamador que tem o corpo sabe).
    Sem a linha de resumo a saida e considerada truncada: ERRO_AMBIENTE."""
    casos: list[Caso] = []
    vistas: set[str] = set()
    resumo = None
    for linha in saida.splitlines():
        if m := _DIVERGE.match(linha):
            tela, a, b = m.groups()
            vistas.add(tela)
            casos.append(Caso(tela, area, Veredito.DIVERGE, f"{a}  {b}"))
        elif m := _TIMEOUT.match(linha):
            tela, a, b = m.groups()
            vistas.add(tela)
            casos.append(Caso(tela, area, Veredito.ERRO_AMBIENTE, f"timeout: {a}  {b}"))
        elif m := _PULADA.match(linha):
            tela = m.group(1)
            vistas.add(tela)
            casos.append(Caso(tela, area, Veredito.INCONCLUSIVO, "pulada (contata servico externo)"))
        elif m := _RESUMO.match(linha):
            resumo = tuple(int(x) for x in m.groups())
    if resumo is None:
        return [Caso("cmp", area, Veredito.ERRO_AMBIENTE, "cmp.py sem linha de resumo (saida truncada?)")]
    identicas, total, ndiv, ntout = resumo
    if telas is not None:
        for tela in telas:
            if tela in vistas:
                continue
            if corpos is not None and corpos.get(tela) == b"":
                casos.append(Caso(tela, area, Veredito.INCONCLUSIVO, "resposta de 0 bytes nos dois lados"))
            else:
                casos.append(Caso(tela, area, Veredito.IDENTICO))
    else:
        casos.append(Caso("identicas", area, Veredito.IDENTICO, f"{identicas}/{total} telas identicas"))
    return sorted(casos, key=lambda c: c.id)


def lista_telas(prefixo: str, diretorio: Path = DIR_TELAS) -> list[str]:
    """Mesma selecao de cmp.py: re.match(prefixo, IGNORECASE) e .php, menos PULAR."""
    return sorted(f for f in os.listdir(diretorio)
                  if re.match(prefixo, f, re.IGNORECASE) and f.endswith(".php") and f not in PULAR)


def obtem_sid() -> str:
    """Sessao autenticada mais recente (a que contem DB_modulo) no container 5.6."""
    saida = _docker(
        ["exec", "ecidade_php56", "sh", "-c",
         "ls -t $(grep -la DB_modulo /var/lib/php/sessions/sess_*) | head -1"],
        TIMEOUT_SID,
    ).decode("utf-8", errors="replace").strip()
    nome = saida.rsplit("/", 1)[-1]
    if not nome.startswith("sess_"):
        raise ErroAmbienteBanco(f"nenhuma sessao autenticada encontrada: {saida!r}")
    return nome[len("sess_"):]


def _roda_cmp(sid: str, prefixo: str) -> str:
    """Unico ponto que executa cmp.py (mockavel nos testes). cmp.py fala com o docker por
    conta propria; aqui so se captura a saida."""
    r = subprocess.run(["python3", str(SCRATCH / "cmp.py"), sid, prefixo],
                       capture_output=True, timeout=TIMEOUT_CMP)
    return r.stdout.decode("utf-8", errors="replace")


def roda_telas(sid: str, prefixo: str, area: str) -> list[Caso]:
    try:
        telas = lista_telas(prefixo)
        saida = _roda_cmp(sid, prefixo)
    except (ErroAmbienteBanco, OSError, subprocess.TimeoutExpired) as e:
        return [Caso("telas", area, Veredito.ERRO_AMBIENTE, str(e))]
    return parse_cmp(saida, area, telas)
