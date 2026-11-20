# Imagem descartavel dos testes (sem banco): php:<versao>-cli + as extensoes que os testes unitarios de hoje pedem.
# bcmath: tests/Unit/Tributario/Agua (bcmul); calendar: classes de datas do sistema. Sem pgsql: nenhum teste abre conexao.
ARG PHP=7.4
FROM php:${PHP}-cli
RUN docker-php-ext-install bcmath calendar >/dev/null
