import os
import subprocess
from dataclasses import dataclass

import requests


@dataclass
class Alvos:
    ref: str
    php_novo: str
    laravel_novo: str
    proxy: str


def alvos_do_ambiente() -> Alvos:
    return Alvos(
        ref=os.environ.get("REGRESSAO_REF_URL", "http://localhost:8080"),
        php_novo=os.environ.get("REGRESSAO_PHP_NOVO_URL", "http://localhost:8085"),
        laravel_novo=os.environ.get("REGRESSAO_LARAVEL_NOVO_URL", "http://localhost:8087"),
        proxy=os.environ.get("REGRESSAO_PROXY_URL", "http://localhost:8090"),
    )


def containers_ativos() -> set[str] | None:
    """Nomes em `docker ps`; None se o docker nao puder ser consultado."""
    try:
        r = subprocess.run(["docker", "ps", "--format", "{{.Names}}"],
                           capture_output=True, text=True, timeout=15, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return set(r.stdout.split())


def _responde(url: str) -> bool:
    try:
        requests.get(url, timeout=5, allow_redirects=False)
        return True
    except requests.RequestException:
        return False


def verifica(alvos: Alvos) -> list[str]:
    problemas = []
    for nome, url in (("ref", alvos.ref), ("php_novo", alvos.php_novo),
                      ("laravel_novo", alvos.laravel_novo), ("proxy", alvos.proxy)):
        if not _responde(url):
            problemas.append(f"{nome}: sem resposta em 5s: {url}")
    ativos = containers_ativos()
    if ativos is None:
        problemas.append("docker ps indisponivel")
    elif "ecidade_database" not in ativos:
        problemas.append("container ausente em docker ps: ecidade_database")
    return problemas
