import hashlib
import re

# (motivo, padrao, marcador) -- sempre sobre bytes, nunca decodificar.
REGRAS: list[tuple[str, re.Pattern[bytes], bytes]] = [
    # Id de sessao PHP vaza em URLs/links e muda a cada requisicao (falso positivo).
    ("sid de sessao", re.compile(rb"sid=[^&\"'\s<>]*"), b"sid=X"),
    # Relatorios geram PDFs em tmp/ com nome aleatorio; o nome muda entre execucoes.
    ("pdf temporario", re.compile(rb"tmp/[^\"'\s<>]*\.pdf"), b"tmp/X.pdf"),
    # Metadado /Date dentro do PDF carrega o horario de geracao.
    ("data de geracao do pdf", re.compile(rb"/Date\S*"), b"/DateX"),
]


def normaliza(corpo: bytes, regras=REGRAS) -> bytes:
    for _motivo, padrao, marcador in regras:
        corpo = padrao.sub(marcador, corpo)
    return corpo


def hash_corpo(corpo: bytes, regras=REGRAS) -> str:
    return hashlib.sha256(normaliza(corpo, regras)).hexdigest()
