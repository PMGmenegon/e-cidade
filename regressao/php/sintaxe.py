import subprocess

from regressao.nucleo.banco import ErroAmbienteBanco, _docker
from regressao.nucleo.veredito import Caso, Veredito

AREA = "php-sintaxe"
CONTAINERS = ("ecidade_php56", "ecidade_php85")
TIMEOUT_LINT = 60
_OK = "No syntax errors detected"


def _lint(container: str, arquivo: str) -> tuple[bool, str]:
    # stdin de /dev/null: sem isso o php consome o resto de uma lista lida em loop.
    # 2>&1 + `|| true`: php -l sai com 255 e escreve a mensagem em stdout/stderr.
    saida = _docker(
        ["exec", container, "sh", "-c",
         'cd /var/www/html && php -l "$1" 2>&1 </dev/null || true', "sh", arquivo],
        TIMEOUT_LINT, stdin=subprocess.DEVNULL,
    ).decode("utf-8", errors="replace").strip()
    return _OK in saida, saida


def roda_lint(arquivos: list[str]) -> list[Caso]:
    casos = []
    for arq in arquivos:
        try:
            ok56, msg56 = _lint(CONTAINERS[0], arq)
            ok85, msg85 = _lint(CONTAINERS[1], arq)
        except ErroAmbienteBanco as e:
            casos.append(Caso(arq, AREA, Veredito.ERRO_AMBIENTE, str(e)))
            continue
        if ok56 and ok85:
            casos.append(Caso(arq, AREA, Veredito.IDENTICO))
        elif ok56 != ok85:
            falha = f"php8.5: {msg85}" if ok56 else f"php5.6: {msg56}"
            casos.append(Caso(arq, AREA, Veredito.DIVERGE, falha))
        else:
            casos.append(Caso(arq, AREA, Veredito.INCONCLUSIVO,
                              f"nao compila em nenhum runtime. php5.6: {msg56} | php8.5: {msg85}"))
    return casos
