"""Bateria Laravel: casos HTTP, gravar a baseline (5.4) e comparar (alvo novo).

Modelo de estado: SEM snapshot por caso. `gravar` e `comparar` restauram o dump UMA vez e
rodam os casos numa ordem FIXA sobre esse unico estado; as duas execucoes percorrem a mesma
sequencia, entao ids e sequencias evoluem igual. Efeitos de escrita saem de (a) o SQL de
negocio do log do PostgreSQL entre marcadores por caso e (b) o hash das `tabelas` do caso.
"""
import base64
import datetime
import difflib
import hashlib
import json
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import requests
import yaml

from regressao.laravel.mascara import mascara_json
from regressao.laravel.token import (CLIENT_ID, _RE_JWT, ErroToken, _segredo_cliente,
                                     laravel_sobe, obtem_token, redige)
from regressao.nucleo.ambiente import alvos_do_ambiente
from regressao.nucleo.banco import (ARQ_DUMP, ARQ_SHA256, CONTAINER, BancoDiferente,
                                    ErroAmbienteBanco, _psql, com_log_statement,
                                    confere_baseline, hash_tabelas, restaura_dump)
from regressao.nucleo.veredito import Caso, Veredito

DIR_CASOS = Path(__file__).resolve().parent / "casos"
DIR_BASELINE = Path(__file__).resolve().parents[1] / "baseline" / "laravel"
RAIZ_REPO = Path(__file__).resolve().parents[2]
AREA = "laravel"
TIMEOUT_HTTP = 60
TIMEOUT_SETUP = 30
CABECALHOS_GRAVADOS = ("content-type", "www-authenticate", "cache-control")
LIMITE_TEXTO = 4000
LIMITE_DIFF_LINHAS = 80
ESPERA_MARCADOR = 8.0  # s para o marcador final aparecer no log do banco
TOKEN_NOVO = "@novo"


class ErroRequisicao(Exception):
    """Falha de transporte/ambiente ao exercitar um caso. A mensagem nunca leva segredo."""


class ErroGravacao(Exception):
    """gravar nao pode produzir uma baseline confiavel."""


@dataclass
class CasoHttp:
    id: str
    metodo: str
    caminho: str
    corpo: dict | None
    autenticado: bool = True
    token: str | None = None  # None = usar o valido; "" = ausente; "@novo" = token recem-emitido; outro = invalido
    campos_volateis: list[str] = field(default_factory=list)
    tabelas: list[str] = field(default_factory=list)
    form: bool = False  # corpo como application/x-www-form-urlencoded (senao JSON)
    sql_antes: list[str] = field(default_factory=list)  # preparacao no banco; `{jti}` = id do token @novo
    espera_escrita: bool = False  # INCONCLUSIVO se nao escrever nada nos dois lados


@dataclass
class Resposta:
    status: int
    cabecalhos: dict[str, str]
    json: object
    sql_negocio: list[str]
    texto: str = ""
    tipos: dict[str, list[str]] = field(default_factory=dict)
    hashes: dict[str, str] = field(default_factory=dict)


_CAMPOS = {f for f in CasoHttp.__dataclass_fields__}


def carrega_casos(diretorio: Path) -> list[CasoHttp]:
    """YAML em ordem alfabetica de arquivo e, dentro dele, ordem do arquivo."""
    casos: list[CasoHttp] = []
    vistos: set[str] = set()
    for arq in sorted(Path(diretorio).glob("*.yml")):
        dados = yaml.safe_load(arq.read_text(encoding="utf-8")) or []
        if not isinstance(dados, list):
            raise ValueError(f"{arq.name}: esperava uma lista de casos")
        for d in dados:
            extra = set(d) - _CAMPOS
            if extra:
                raise ValueError(f"{arq.name}: campos desconhecidos {sorted(extra)}")
            for obrig in ("id", "metodo", "caminho"):
                if obrig not in d:
                    raise ValueError(f"{arq.name}: caso sem '{obrig}'")
            if d["id"] in vistos or not re.fullmatch(r"[\w.-]+", str(d["id"])):
                raise ValueError(f"{arq.name}: id repetido ou invalido: {d['id']!r}")
            vistos.add(d["id"])
            d = dict(d)
            d["metodo"] = str(d["metodo"]).upper()
            d.setdefault("corpo", None)
            casos.append(CasoHttp(**d))
    return casos


# ---------------------------------------------------------------- execucao

def _limpa(obj):
    """Rede de seguranca: nenhum JWT sobrevive em nada que va para a baseline/relatorio."""
    if isinstance(obj, str):
        return _RE_JWT.sub("<jwt>", obj)
    if isinstance(obj, list):
        return [_limpa(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _limpa(v) for k, v in obj.items()}
    return obj


def _jti(jwt: str) -> str:
    try:
        p = jwt.split(".")[1]
        dados = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
        jti = str(dados["jti"])
    except (IndexError, ValueError, KeyError, TypeError):
        raise ErroRequisicao("token emitido sem jti legivel") from None
    if not re.fullmatch(r"[\w-]+", jti):
        raise ErroRequisicao("jti do token com formato inesperado")
    return jti


def _grant_senha(base_url: str) -> dict:
    """Password grant de setup (fora da janela de captura). Devolve o JSON completo."""
    url = base_url.rstrip("/") + "/v4/oauth/token"
    try:
        r = requests.post(url, data={"grant_type": "password", "client_id": CLIENT_ID,
                                     "client_secret": _segredo_cliente(),
                                     "username": "dbseller", "password": "dbseller"},
                          timeout=TIMEOUT_SETUP)
        dados = r.json()
    except (requests.RequestException, ValueError, ErroToken) as e:
        raise ErroRequisicao(f"setup do token falhou: {type(e).__name__}") from None
    if r.status_code != 200 or not isinstance(dados, dict) or "access_token" not in dados:
        raise ErroRequisicao(f"setup do token: HTTP {r.status_code} sem access_token")
    return dados


class _Contexto:
    """Valores dos marcadores `${...}` dos casos; os caros/sigilosos sao resolvidos sob demanda."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._cache: dict[str, str] = {}

    def valor(self, nome: str) -> str:
        if nome in self._cache:
            return self._cache[nome]
        if nome == "CLIENT_ID":
            v = CLIENT_ID
        elif nome == "CLIENT_SECRET":
            try:
                v = _segredo_cliente()
            except ErroToken as e:
                raise ErroRequisicao(str(e)) from None
        elif nome == "USUARIO" or nome == "SENHA":
            v = "dbseller"
        elif nome == "REFRESH_TOKEN":
            v = str(_grant_senha(self.base_url).get("refresh_token", ""))
        else:
            raise ErroRequisicao(f"marcador desconhecido: ${{{nome}}}")
        self._cache[nome] = v
        return v

    def aplica(self, obj):
        if isinstance(obj, str):
            return re.sub(r"\$\{(\w+)\}", lambda m: self.valor(m.group(1)), obj)
        if isinstance(obj, list):
            return [self.aplica(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.aplica(v) for k, v in obj.items()}
        return obj


def _tipos(obj, partes: list[str]) -> list[str]:
    if not partes:
        return [type(obj).__name__]
    p, resto = partes[0], partes[1:]
    if p == "*":
        return [t for x in obj for t in _tipos(x, resto)] if isinstance(obj, list) else []
    if isinstance(obj, dict) and p in obj:
        return _tipos(obj[p], resto)
    return []


def tipos_mascarados(obj, campos: list[str]) -> dict[str, list[str]]:
    """Estrutura dos campos mascarados (tipo/presenca), ja que o valor nao e comparado."""
    return {c: sorted(set(_tipos(obj, c.split(".")))) or ["ausente"] for c in campos}


_RE_ESCRITA = re.compile(r"^\s*(insert|update|delete)\b", re.I)
_RE_INFRA = re.compile(
    r"\b(db_acount\w*|db_usuariosonline|db_logsacessa|db_menu\w*|db_sessao\w*|oauth_\w+)\b", re.I)
_RE_PREFIXO = re.compile(r"^\d{4}-\d{2}-\d{2} [\d:.]+ [^ ]+ \[\d+\] LOG:\s+[^:]*:\s*")
_RE_LINHA_LOG = re.compile(r"^\d{4}-\d{2}-\d{2} [\d:.]+ [^ ]+ \[\d+\] ")
_RE_PARAMS = re.compile(r"^\d{4}-\d{2}-\d{2} [\d:.]+ [^ ]+ \[\d+\] DETAIL:\s+(parameters:.*)$")
_RE_TS = re.compile(r"'\d{4}-\d{2}-\d{2}[ T][\d:.]+(?:[+-]\d{2}(?::?\d{2})?|Z)?'")
_RE_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_RE_HEX = re.compile(r"\b[0-9a-f]{40,}\b", re.I)


def normaliza_sql(sql: str) -> str:
    """Timestamps -> '<TS>'; a data de hoje -> '<HOJE>'; uuids/hex longos; espacos colapsados.
    Ids sequenciais ficam: com o mesmo dump e a mesma ordem de casos eles evoluem igual."""
    sql = _RE_TS.sub("'<TS>'", sql)
    hoje = {datetime.date.today().isoformat(),
            datetime.datetime.now(datetime.timezone.utc).date().isoformat()}
    for d in hoje:
        sql = sql.replace(f"'{d}'", "'<HOJE>'")
    sql = _RE_UUID.sub("<UUID>", sql)
    sql = _RE_HEX.sub("<HEX>", sql)
    return re.sub(r"\s+", " ", sql).strip()


def _logs_banco(desde: datetime.datetime) -> bytes:
    """`docker logs` do banco desde `desde` (stderr incluso: o postgres loga la)."""
    try:
        r = subprocess.run(["docker", "logs", "--since", desde.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            CONTAINER], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise ErroAmbienteBanco(f"docker logs falhou: {type(e).__name__}") from None
    if r.returncode != 0:
        raise ErroAmbienteBanco(f"docker logs saiu com {r.returncode}")
    return r.stdout


def _statements(bruto: bytes) -> list[str]:
    """Statements do log, sem prefixo, com continuacoes juntadas (so elas) e a linha
    `DETAIL: parameters:` do protocolo estendido anexada ao statement anterior."""
    out: list[str] = []
    aberto = False
    for l in bruto.decode("utf-8", errors="replace").split("\n"):
        l = l.rstrip("\r")
        m = _RE_PREFIXO.match(l)
        if m:
            out.append(l[m.end():])
            aberto = True
            continue
        p = _RE_PARAMS.match(l)
        if p:
            if out:
                out[-1] += " " + p.group(1)
            aberto = False
        elif _RE_LINHA_LOG.match(l):
            aberto = False
        elif aberto and l.strip():
            out[-1] += " " + l.strip()
    return out


def _sql_entre(desde: datetime.datetime, ini: str, fim: str) -> list[str]:
    limite = time.monotonic() + ESPERA_MARCADOR
    while True:
        stm = _statements(_logs_banco(desde))
        i = next((k for k, s in enumerate(stm) if ini in s), None)
        j = next((k for k, s in enumerate(stm) if fim in s), None)
        if i is not None and j is not None and j > i:
            break
        if time.monotonic() > limite:
            raise ErroAmbienteBanco("marcadores do caso nao apareceram no log do banco "
                                    "(log_statement ligado?)")
        time.sleep(0.25)
    negocio = [s for s in stm[i + 1:j] if _RE_ESCRITA.match(s) and not _RE_INFRA.search(s)]
    return [normaliza_sql(s) for s in negocio]


def executa(caso: CasoHttp, base_url: str, token: str, banco: bool = True) -> Resposta:
    """Exercita um caso. Setup (placeholders, token novo, sql_antes) acontece ANTES do
    marcador inicial, entao nao entra no SQL capturado. `token` = o token valido compartilhado."""
    ctx = _Contexto(base_url)
    corpo = ctx.aplica(caso.corpo) if caso.corpo is not None else None
    usado = None
    if caso.autenticado:
        if caso.token is None:
            usado = token
        elif caso.token == TOKEN_NOVO:
            usado = str(_grant_senha(base_url)["access_token"])
        elif caso.token != "":
            usado = caso.token
    if banco:
        for sql in caso.sql_antes:
            if "{jti}" in sql:
                if caso.token != TOKEN_NOVO or usado is None:
                    raise ErroRequisicao("sql_antes usa {jti} sem token '@novo'")
                sql = sql.replace("{jti}", _jti(usado))
            _psql(sql)
    marca = uuid.uuid4().hex[:16]
    ini, fim = f"REGRESSAO_{marca}_ini", f"REGRESSAO_{marca}_fim"
    desde = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=5)
    if banco:
        _psql(f"select '{ini}'")
    headers = {"Accept": "application/json"}
    if usado:
        headers["Authorization"] = "Bearer " + usado
    kw: dict = {"headers": headers, "timeout": TIMEOUT_HTTP, "allow_redirects": False}
    if corpo is not None:
        kw["data" if caso.form else "json"] = corpo
    url = base_url.rstrip("/") + caso.caminho
    try:
        r = requests.request(caso.metodo, url, **kw)
    except requests.RequestException as e:
        raise ErroRequisicao(f"{caso.metodo} {caso.caminho} sem resposta: {type(e).__name__}") from None
    sql: list[str] = []
    hashes: dict[str, str] = {}
    if banco:
        _psql(f"select '{fim}'")
        sql = _sql_entre(desde, ini, fim)
        if caso.tabelas:
            hashes = hash_tabelas(caso.tabelas)
    try:
        bruto = r.json()
    except ValueError:
        bruto = None
    texto = "" if bruto is not None else _limpa(r.text or "")[:LIMITE_TEXTO]
    cab = {k.lower(): v for k, v in r.headers.items() if k.lower() in CABECALHOS_GRAVADOS}
    return Resposta(
        status=r.status_code, cabecalhos=_limpa(cab),
        json=_limpa(mascara_json(bruto, caso.campos_volateis)) if bruto is not None else None,
        sql_negocio=_limpa(sql), texto=texto,
        tipos=tipos_mascarados(bruto, caso.campos_volateis) if bruto is not None else {},
        hashes=hashes)


# ---------------------------------------------------------------- baseline

def _nucleo(r: Resposta) -> dict:
    return {"status": r.status, "cabecalhos": r.cabecalhos, "json": r.json, "texto": r.texto,
            "tipos": r.tipos, "sql_negocio": r.sql_negocio, "tabelas": r.hashes}


def _canonico(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha(registro: dict) -> str:
    return hashlib.sha256(_canonico(registro).encode("utf-8")).hexdigest()


def _grava_registro(arq: Path, registro: dict) -> None:
    completo = dict(registro)
    completo.pop("sha256", None)
    completo["sha256"] = _sha(completo)
    arq.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(completo, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    arq.write_bytes(texto.encode("utf-8"))


def _le_registro(arq: Path) -> dict:
    """Levanta ValueError se ilegivel ou adulterado."""
    try:
        reg = json.loads(arq.read_text(encoding="utf-8"))
        sha = reg.pop("sha256")
    except (OSError, ValueError, KeyError, AttributeError):
        raise ValueError(f"baseline ilegivel: {arq.name}") from None
    if sha != _sha(reg):
        raise ValueError(f"baseline adulterada (sha256 nao confere): {arq.name}")
    return reg


def _sha_dump_atual() -> str | None:
    try:
        partes = ARQ_SHA256.read_text().split()
    except OSError:
        return None
    return partes[0] if partes else None


def _tipo_alvo(base_url: str) -> str:
    a = alvos_do_ambiente()
    u = base_url.rstrip("/")
    for nome in ("ref", "php_novo", "laravel_novo", "proxy"):
        if u == getattr(a, nome).rstrip("/"):
            return nome
    return "outro"


def _commit() -> str:
    try:
        r = subprocess.run(["git", "-C", str(RAIZ_REPO), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or "desconhecido"
    except (OSError, subprocess.SubprocessError):
        return "desconhecido"


def _roda(casos: list[CasoHttp], base_url: str, erros: dict | None = None) -> dict[str, Resposta]:
    """Restaura o dump uma vez e roda os casos em ordem. Com `erros` (dict), falha por caso
    vira entrada ali; sem ele, a primeira falha propaga."""
    restaura_dump(ARQ_DUMP)
    try:
        token = obtem_token(base_url)
    except ErroToken as e:
        raise ErroRequisicao(str(e)) from None
    respostas: dict[str, Resposta] = {}
    with com_log_statement():
        for c in casos:
            try:
                respostas[c.id] = executa(c, base_url, token)
            except (ErroRequisicao, ErroAmbienteBanco) as e:
                if erros is None:
                    raise
                erros[c.id] = redige(str(e))
    return respostas


def gravar(casos: list[CasoHttp], base_url: str, diretorio: Path) -> None:
    """Restaura o dump, roda os casos contra `base_url` e grava `<id>.json` + `_meta.json`."""
    diretorio = Path(diretorio)
    boot = laravel_sobe(base_url)
    if boot is not None:
        raise ErroGravacao(f"alvo nao sobe, nada foi restaurado: {boot.detalhe}")
    confere_baseline(ARQ_DUMP)
    sha = _sha_dump_atual()
    if sha is None:
        raise ErroGravacao(f"hash do dump ausente: {ARQ_SHA256}")
    respostas = _roda(casos, base_url)
    for c in casos:
        _grava_registro(diretorio / f"{c.id}.json", {"id": c.id, **_nucleo(respostas[c.id])})
    meta = {"dump_sha256": sha, "commit": _commit(),
            "data": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "n_casos": len(casos), "alvo": _tipo_alvo(base_url), "ids": [c.id for c in casos]}
    (diretorio / "_meta.json").write_bytes(
        (json.dumps(meta, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _erro(id: str, detalhe: str) -> Caso:
    return Caso(id, AREA, Veredito.ERRO_AMBIENTE, redige(detalhe))


def _diff(base: dict, novo: dict) -> str:
    def pp(x):
        return json.dumps(x, sort_keys=True, ensure_ascii=False, indent=2).splitlines()
    linhas = list(difflib.unified_diff(pp(base), pp(novo), "baseline", "atual", lineterm="", n=2))
    if len(linhas) > LIMITE_DIFF_LINHAS:
        linhas = linhas[:LIMITE_DIFF_LINHAS] + [f"... (diff truncado, {len(linhas)} linhas)"]
    return _RE_JWT.sub("<jwt>", "\n".join(linhas))


def _veredito(caso: CasoHttp, reg: dict, r: Resposta) -> Caso:
    base, novo = {k: v for k, v in reg.items() if k != "id"}, _nucleo(r)
    if base != novo:
        dif = [k for k in novo if base.get(k) != novo[k]]
        return Caso(caso.id, AREA, Veredito.DIVERGE, "difere em: " + ", ".join(dif),
                    _diff(base, novo))
    if r.status >= 500:
        return Caso(caso.id, AREA, Veredito.INCONCLUSIVO,
                    f"HTTP {r.status} nos dois lados: o caso nao foi exercitado")
    if r.json is None and not r.texto:
        return Caso(caso.id, AREA, Veredito.INCONCLUSIVO, "resposta sem conteudo nos dois lados")
    if caso.espera_escrita and not r.sql_negocio:
        return Caso(caso.id, AREA, Veredito.INCONCLUSIVO,
                    "esperava escrita e nada foi gravado nos dois lados")
    return Caso(caso.id, AREA, Veredito.IDENTICO)


def comparar(casos: list[CasoHttp], base_url: str, diretorio: Path) -> list[Caso]:
    """Ordem: boot do alvo -> baseline/meta -> restauracao -> casos (fixos, mesma ordem do gravar).
    Nada e restaurado se uma das verificacoes iniciais falhar."""
    diretorio = Path(diretorio)
    boot = laravel_sobe(base_url)
    if boot is not None:
        return [boot]
    meta_arq = diretorio / "_meta.json"
    if not meta_arq.is_file():
        return [_erro(c.id, f"baseline ausente: {meta_arq.name} em {diretorio}") for c in casos]
    try:
        meta = json.loads(meta_arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [_erro("laravel:baseline", "baseline/_meta.json ilegivel")]
    atual = _sha_dump_atual()
    if atual is None:
        return [_erro("laravel:baseline", f"hash do dump ausente: {ARQ_SHA256}")]
    if meta.get("dump_sha256") != atual:
        return [_erro("laravel:baseline",
                      f"baseline gravada com outro dump (sha256 {str(meta.get('dump_sha256'))[:12]} "
                      f"!= atual {atual[:12]}): grave a baseline de novo; nada foi restaurado")]
    registros: dict[str, dict] = {}
    faltando: list[Caso] = []
    for c in casos:
        arq = diretorio / f"{c.id}.json"
        if not arq.is_file():
            faltando.append(_erro(c.id, f"baseline ausente: {arq.name}"))
            continue
        try:
            registros[c.id] = _le_registro(arq)
        except ValueError as e:
            faltando.append(_erro(c.id, str(e)))
    if faltando:
        return faltando
    try:
        confere_baseline(ARQ_DUMP)
    except BancoDiferente as e:
        return [_erro("laravel:baseline", f"dump local diferente do registrado: {e}")]
    erros: dict[str, str] = {}
    try:
        respostas = _roda(casos, base_url, erros)
    except (ErroRequisicao, ErroAmbienteBanco) as e:
        return [_erro("laravel:banco", f"preparo do banco/token falhou: {e}")]
    res: list[Caso] = []
    for c in casos:
        if c.id in erros:
            res.append(_erro(c.id, erros[c.id]))
        else:
            res.append(_veredito(c, registros[c.id], respostas[c.id]))
    return res


def _main(argv: list[str]) -> int:
    """python -m regressao.laravel.caso gravar|comparar [url]  (padrao: alvo `ref`, :8080 para gravar;
    laravel_novo para comparar)."""
    import sys
    modo = argv[0] if argv else ""
    if modo not in ("gravar", "comparar"):
        print("uso: python -m regressao.laravel.caso gravar|comparar [url]", file=sys.stderr)
        return 2
    alvos = alvos_do_ambiente()
    url = argv[1] if len(argv) > 1 else (alvos.ref if modo == "gravar" else alvos.laravel_novo)
    casos = carrega_casos(DIR_CASOS)
    t0 = time.monotonic()
    if modo == "gravar":
        gravar(casos, url, DIR_BASELINE)
        print(f"gravados {len(casos)} casos em {DIR_BASELINE} ({time.monotonic() - t0:.0f} s)")
        return 0
    res = comparar(casos, url, DIR_BASELINE)
    for c in res:
        print(f"{c.veredito.value:14} {c.id}  {c.detalhe.splitlines()[0] if c.detalhe else ''}")
        if c.diff:
            print(c.diff)
    print(f"({time.monotonic() - t0:.0f} s)")
    from regressao.nucleo.veredito import codigo_saida
    return codigo_saida(res)


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
