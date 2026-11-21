#!/usr/bin/env python3
"""Confere HTTP, formulario e proxy da base-php74; nao autentica nem migra o banco."""

import hashlib
import http.client
import re


def requisita(porta, caminho):
    conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=20)
    try:
        conexao.request("GET", caminho, headers={"Host": "localhost:8090"})
        resposta = conexao.getresponse()
        return resposta.status, dict(resposta.getheaders()), resposta.read()
    finally:
        conexao.close()


def main():
    corpos = []
    for porta in (8080, 8085, 8090):
        status, cabecalhos, _ = requisita(porta, "/")
        assert status == 302, f":{porta}: raiz retornou HTTP {status}"
        assert cabecalhos.get("Location") == "login.php", f":{porta}: redirecionamento inesperado"

        status, cabecalhos, corpo = requisita(porta, "/login.php")
        assert status == 200, f":{porta}: entrada retornou HTTP {status}"
        assert "charset=ISO-8859-1" in cabecalhos.get("Content-Type", ""), f":{porta}: charset inesperado"
        assert b'id="usu_login"' in corpo and b'id="usu_senha"' in corpo, f":{porta}: formulario ausente"
        assert b"js_acessar_dbportal" in corpo, f":{porta}: JavaScript de login ausente"
        if porta == 8090:
            assert cabecalhos.get("X-Ecidade-Runtime") == "PHP-7.4 (referencia)", "Proxy fora da referencia"

        normalizado, quantidade = re.subn(
            rb"(carregaCaptcha\.php\?sid=)[0-9a-f]{32}", rb"\1SID", corpo
        )
        assert quantidade == 1, f":{porta}: identificador do CAPTCHA inesperado"
        corpos.append(normalizado)
        print(f":{porta}: raiz 302, entrada 200, formulario e charset OK")

    assert corpos[0] == corpos[1] == corpos[2], "Conteudo da entrada diverge entre os runtimes"
    print("Entrada equivalente nas tres portas; proxy no PHP 7.4.")
    print("SHA-256 normalizado:", hashlib.sha256(corpos[0]).hexdigest())


if __name__ == "__main__":
    main()
