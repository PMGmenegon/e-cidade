"""Token Passport (password grant) e deteccao de Laravel fora do ar."""
import re
from pathlib import Path

import requests

from regressao.nucleo.banco import ErroAmbienteBanco, _docker
from regressao.nucleo.veredito import Caso, Veredito

RAIZ_REPO = Path(__file__).resolve().parents[2]
ARQ_CONFIG = RAIZ_REPO / "ecidade" / "config" / "application.php"
CLIENT_ID = "9999999"
CONTAINER_PHP = "ecidade_php56"
LOG_ERROS = "/var/log/php_errors.log"
TIMEOUT = 15


class ErroToken(Exception):
    """Falha ao obter o token. A mensagem nunca contem segredo, senha ou token."""


def _segredo_cliente() -> str:
    try:
        texto = ARQ_CONFIG.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise ErroToken(f"nao foi possivel ler {ARQ_CONFIG.name}: {type(e).__name__}") from None
    m = re.search(r"""['"]api\.client\.secret['"]\s*=>\s*(['"])(.*?)\1""", texto)
    if not m:
        raise ErroToken("chave api.client.secret nao encontrada em application.php")
    return m.group(2)


def obtem_token(base_url: str, usuario: str = "dbseller", senha: str = "dbseller") -> str:
    dados = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": _segredo_cliente(),
        "username": usuario,
        "password": senha,
    }
    url = base_url.rstrip("/") + "/v4/oauth/token"
    try:
        r = requests.post(url, data=dados, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ErroToken(f"sem resposta de {url}: {type(e).__name__}") from None
    if r.status_code != 200:
        raise ErroToken(f"POST {url} devolveu HTTP {r.status_code}")
    try:
        tok = r.json()["access_token"]
    except (ValueError, KeyError, TypeError):
        raise ErroToken(f"POST {url} sem access_token na resposta (HTTP 200)") from None
    if not isinstance(tok, str) or not tok:
        raise ErroToken(f"POST {url} devolveu access_token vazio")
    return tok


def _cauda_php_errors(linhas: int = 5) -> str:
    try:
        saida = _docker(["exec", CONTAINER_PHP, "tail", "-n", str(linhas), LOG_ERROS], 15)
    except ErroAmbienteBanco:
        return ""
    return saida.decode("utf-8", errors="replace").strip()


def laravel_sobe(base_url: str) -> Caso | None:
    """None se o Laravel responde (qualquer status < 500); senao UM Caso ERRO_AMBIENTE."""
    url = base_url.rstrip("/") + "/v4/oauth/token"
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=False)
    except requests.RequestException as e:
        return Caso("laravel:boot", "laravel", Veredito.ERRO_AMBIENTE,
                    f"Laravel fora do ar em {base_url}: {type(e).__name__}")
    if r.status_code >= 500:
        detalhe = f"Laravel em {base_url} devolveu HTTP {r.status_code} no boot"
        log = _cauda_php_errors()
        if log:
            detalhe += f"\nphp_errors.log:\n{log}"
        return Caso("laravel:boot", "laravel", Veredito.ERRO_AMBIENTE, detalhe)
    return None