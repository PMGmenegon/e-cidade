import os
import re
import shlex
import subprocess
from pathlib import Path

from regressao.nucleo.banco import ErroAmbienteBanco, _docker
from regressao.nucleo.normaliza import normaliza
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


_ENV_PROIBIDO = ("ONLY", "PORTA_B", "NORM_MENU")
TIMEOUT_CORPO = 90


def _roda_cmp(sid: str, prefixo: str) -> str:
    """Unico ponto que executa cmp.py (mockavel nos testes). cmp.py fala com o docker por
    conta propria; aqui so se captura a saida. ONLY/PORTA_B/NORM_MENU do ambiente de quem
    chama mudariam a selecao/lado B/normalizacao do cmp.py, entao sao removidos."""
    env = {k: v for k, v in os.environ.items() if k not in _ENV_PROIBIDO}
    r = subprocess.run(["python3", str(SCRATCH / "cmp.py"), sid, prefixo],
                       capture_output=True, timeout=TIMEOUT_CMP, env=env)
    return r.stdout.decode("utf-8", errors="replace")


def restaura_sessao(sid: str) -> None:
    """Restaura a sessao a partir de /tmp/_sess.bak (backup que o proprio cmp.py deixa em
    ecidade_php56; o volume de sessoes e compartilhado com o php85), pois cada requisicao
    consome/reescreve a sessao."""
    sess = f"/var/lib/php/sessions/sess_{sid}"
    # `[ -f ]`: so restaura sobre uma sessao que existe; senao um SID qualquer ganharia, a
    # partir de um backup velho, uma sessao autenticada forjada.
    _docker(["exec", "-u", "root", "ecidade_php56", "sh", "-c",
             f"[ -f {sess} ] && cp /tmp/_sess.bak {sess} && chown www-data:www-data {sess} "
             f"&& chmod 600 {sess}"],
            TIMEOUT_CORPO)


def busca_corpo(sid: str, tela: str) -> bytes:
    """Corpo cru da tela no lado 5.6 (o lado ja sabido identico ao 8.5). Espelha o fetch do
    cmp.py: restaura a sessao antes da requisicao; depois curl com o cookie
    ECIDADEWINDOWMAIN, -m 60 e teto de 5 MB. A requisicao parte de dentro do container (porta
    80 do apache), via banco._docker."""
    restaura_sessao(sid)
    return _requisita(sid, tela)


def _requisita(sid: str, tela: str, container: str = "ecidade_php56") -> bytes:
    return _docker(["exec", container, "sh", "-c",
                    f"curl -s -m 60 -b 'ECIDADEWINDOWMAIN={sid}' "
                    f"{shlex.quote(f'http://localhost/{tela}')} | head -c 5000000"],
                   TIMEOUT_CORPO)


def _requisita_status(sid: str, tela: str, container: str = "ecidade_php56") -> tuple[int, bytes]:
    """Como _requisita, mas devolve (codigo HTTP, corpo cru). O codigo vem num trailer
    `\n@@<codigo>` (como no cmp.py), removido do corpo sem perder bytes. Teto de 5 MB no
    pipe: se o corpo estourar, o trailer se perde e o codigo e 0 (resposta truncada)."""
    saida = _docker(["exec", container, "sh", "-c",
                     f"curl -s -m 60 -b 'ECIDADEWINDOWMAIN={sid}' -w '\n@@%{{http_code}}' "
                     f"{shlex.quote(f'http://localhost/{tela}')} | head -c 5000000"],
                    TIMEOUT_CORPO)
    i = saida.rfind(b"\n@@")
    if i < 0 or not saida[i + 3:].strip().isdigit():
        return 0, saida
    return int(saida[i + 3:]), saida[:i]


# Pagina que o e-cidade devolve a uma sessao invalida/expirada (observada com um SID
# inexistente, ISO-8859-1, 66 bytes): "Sessão inválida (12). Feche seu navegador e faça login
# novamente." Identica nos dois runtimes, logo cmp.py a daria como IDENTICA.
TELA_SONDA = "cem1_cemiterio001.php"
# Letras acentuadas nas duas codificacoes (Latin-1 e UTF-8) e nas duas caixas; IGNORECASE em
# bytes so dobra ASCII, por isso a caixa dos acentos e listada a mao.
_A_TIL = rb"(?:\xe3|\xc3\xa3|\xc3\x83|\xc3|a)"      # ã / Ã
_A_AGUDO = rb"(?:\xe1|\xc1|\xc3\xa1|\xc3\x81|a)"    # á / Á
_INVALIDA = re.compile(
    rb"sess" + _A_TIL + rb"o inv" + _A_AGUDO + rb"lida"   # libs/db_conecta.php:43 e db_sessoes.php:41 (sessao invalida (12)/(14))
    rb"|sess" + _A_TIL + rb"o terminada"                  # libs/db_conecta.php:76 e :309 (conexao invalida / sistema desativado); db_conecta_cli.php:48, db_conecta_plugin.php:49
    rb"|feche seu navegador",                             # frase comum a todas as variantes acima; cobre texto reescrito no db_erros.php?fechar=true
    re.IGNORECASE,
)


def corpo_de_sessao_invalida(corpo: bytes) -> bool:
    """Pagina curta (< 1000 B apos normalizar) com alguma mensagem de sessao morta. Todas sao
    identicas nos dois runtimes, logo cmp.py as daria como IDENTICAS. O teto de tamanho
    evita acusar uma tela real que apenas cite a frase."""
    c = normaliza(corpo)
    return len(c) < 1000 and _INVALIDA.search(c) is not None


def sessao_autenticada(sid: str) -> bool:
    """Sonda barata: uma tela conhecida com esta sessao (sem restaurar nada, para nao
    transformar um SID inexistente em sessao valida). Falha fechado: corpo vazio (ex.: o
    redirect para db_erros.php, que o curl sem -L nao segue) ou minusculo e sem HTML
    (< 50 B sem '<') conta como NAO autenticado."""
    corpo = _requisita(sid, TELA_SONDA)
    if len(corpo) < 50 and b"<" not in corpo:
        return False
    return not corpo_de_sessao_invalida(corpo)


def roda_telas(sid: str, prefixo: str, area: str) -> tuple[list[Caso], dict[str, bytes]]:
    """Roda cmp.py e devolve (casos, corpos). Um IDENTICO vindo so do cmp.py nunca significou
    "exercitada": uma tela vazia ou que falha igual nos dois lados tambem e "identica". Este
    passo busca UM corpo (lado 5.6) de cada tela que cmp.py nao acusou e, se o corpo
    normalizado tem 0 bytes, rebaixa a INCONCLUSIVO. `corpos` mapeia tela -> corpo cru dessas
    telas (entrada de grava_hashes/cobertura_telas); telas DIVERGE/TIMEOUT/PULADA nao tem corpo.
    Falha ao buscar corpo ou total do resumo != len(telas) -> um unico ERRO_AMBIENTE."""
    try:
        telas = lista_telas(prefixo)
        if not sessao_autenticada(sid):
            return [Caso("telas", area, Veredito.ERRO_AMBIENTE,
                         "sessao nao autenticada (pagina 'Sessao invalida')")], {}
        saida = _roda_cmp(sid, prefixo)
    except (ErroAmbienteBanco, OSError, subprocess.TimeoutExpired) as e:
        return [Caso("telas", area, Veredito.ERRO_AMBIENTE, str(e))], {}
    resumo = next((m for m in map(_RESUMO.match, saida.splitlines()) if m), None)
    if resumo is not None and int(resumo.group(2)) != len(telas):
        return [Caso("telas", area, Veredito.ERRO_AMBIENTE,
                     f"resumo do cmp.py tem {resumo.group(2)} telas, lista_telas tem {len(telas)}")], {}
    casos = parse_cmp(saida, area, telas)
    corpos: dict[str, bytes] = {}
    try:
        for c in casos:
            if c.veredito != Veredito.IDENTICO or c.id not in telas:
                continue
            corpos[c.id] = busca_corpo(sid, c.id)
    except (ErroAmbienteBanco, OSError, subprocess.TimeoutExpired) as e:
        return [Caso("telas", area, Veredito.ERRO_AMBIENTE, f"falha ao buscar corpo: {e}")], corpos
    for c in casos:
        if c.id not in corpos:
            continue
        if corpo_de_sessao_invalida(corpos[c.id]):
            c.veredito = Veredito.ERRO_AMBIENTE
            c.detalhe = "sessao expirou durante a rodada (pagina 'Sessao invalida')"
        elif normaliza(corpos[c.id]) == b"":
            c.veredito = Veredito.INCONCLUSIVO
            c.detalhe = "resposta vazia (0 bytes) nos dois lados"
    return casos, corpos
