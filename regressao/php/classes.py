import subprocess
import tempfile
from pathlib import Path

from regressao.nucleo.banco import ErroAmbienteBanco, _docker
from regressao.nucleo.veredito import Caso, Veredito

AREA = "php-classes"
CONTAINERS = ("ecidade_php56", "ecidade_php85")
RAIZ = Path(__file__).resolve().parents[2]
SCRATCH = RAIZ / "scratchpad"
DESTINO = RAIZ / "ecidade" / "tmp"
TIMEOUT_CLASSES = 900


def _parse(saida: str) -> dict[str, dict[str, str]]:
    """Uma linha 'classe campo=valor' (ou 'classe<TAB>campo<TAB>valor') por campo.
    Classe so com SEM_SAIDA/<ERRO> fica com dict vazio ou marcador."""
    classes: dict[str, dict[str, str]] = {}
    for linha in saida.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if linha.startswith("SEM_SAIDA"):
            classes.setdefault(linha.split(None, 1)[1] if " " in linha else "?", {})
            continue
        if "\t" in linha:
            cls, campo, valor = (linha.split("\t", 2) + [""])[:3]
        else:
            cls, _, resto = linha.partition(" ")
            campo, _, valor = resto.partition("=")
        classes.setdefault(cls, {})[campo] = valor
    return classes


def compara_classes(saida56: str, saida85: str) -> list[Caso]:
    a, b = _parse(saida56), _parse(saida85)
    casos = []
    for cls in sorted(set(a) | set(b)):
        ca, cb = a.get(cls, {}), b.get(cls, {})
        if not ca and not cb:
            casos.append(Caso(cls, AREA, Veredito.INCONCLUSIVO, "sem saida nos dois lados"))
            continue
        difs = [f"{k}: 5.6={ca.get(k, '<ausente>')} 8.5={cb.get(k, '<ausente>')}"
                for k in sorted(set(ca) | set(cb)) if ca.get(k) != cb.get(k)]
        if difs:
            casos.append(Caso(cls, AREA, Veredito.DIVERGE, "; ".join(difs), "\n".join(difs)))
        else:
            casos.append(Caso(cls, AREA, Veredito.IDENTICO))
    return casos


def roda_classes(lista: list[str]) -> list[Caso]:
    try:
        DESTINO.mkdir(parents=True, exist_ok=True)
        for nome in ("escrita.php", "porclasse.sh"):
            (DESTINO / nome).write_bytes((SCRATCH / nome).read_bytes())
        saidas = []
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8") as f:
            f.write("\n".join(lista) + "\n")
            f.flush()
            for c in CONTAINERS:
                with open(f.name, "rb") as entrada:
                    saidas.append(_docker(
                        ["exec", "-i", c, "sh", "/var/www/html/tmp/porclasse.sh",
                         "/var/www/html/tmp/escrita.php"],
                        TIMEOUT_CLASSES, stdin=entrada,
                    ).decode("utf-8", errors="replace"))
    except (ErroAmbienteBanco, OSError) as e:
        return [Caso("classes", AREA, Veredito.ERRO_AMBIENTE, str(e))]
    return compara_classes(*saidas)
