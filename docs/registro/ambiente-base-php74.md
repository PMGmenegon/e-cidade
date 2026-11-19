# Ambiente local da base-php74

Verificado em 19/11/2026, a partir do commit
`982a95fb5902186cab75fa25d30c83ee52e7695d`, na branch
`nucleo/ambiente-base-php74`. Escopo: iniciar os runtimes e o proxy, preparar
o banco local e registrar a abertura da tela de entrada. A migracao das areas,
do Laravel e das APIs permanece com as respectivas frentes.

## Servicos verificados

| Servico | Versao | Acesso |
| --- | --- | --- |
| ecidade_php74 | PHP 7.4.33, Laravel 8.73.2 | http://localhost:8080 |
| ecidade_php85 | PHP 8.5.12 | http://localhost:8085 |
| ecidade_proxy | nginx 1.27.5 | http://localhost:8090 |
| ecidade_database | PostgreSQL 16, banco ecidade, LATIN1 | Rede interna do Docker |

O endereco de uso e `http://localhost:8090`. O proxy encaminha tudo ao PHP 7.4:
nenhuma tela foi acrescentada ao mapa do PHP 8.5. A resposta do proxy inclui
`X-Ecidade-Runtime: PHP-7.4 (referencia)`.

Os dois PHPs montam o mesmo codigo, o volume `ecidade_sessions` em
`/var/lib/php/sessions` e o volume `ecidade_tmp` em `/tmp`. As permissoes dos
volumes sao, respectivamente, `1733` e `1777`. As pastas de runtime da aplicacao
receberam grupo `www-data` e permissao de escrita para o grupo.
Um teste com o usuario `www-data` gravou uma sessao e um temporario no 7.4 e
confirmou a leitura dos mesmos arquivos no 8.5.

## Iniciar novamente

Executar na raiz do repositorio, preservando o nome de projeto `e-cidade`, pois
os arquivos do PHP 8.5 e do proxy usam a rede externa `e-cidade_ecidade`:

```bash
docker volume create ecidade_sessions
docker volume create ecidade_tmp
docker-compose -p e-cidade -f docker-compose.yml -f docker-compose.sessions.yml up -d
docker-compose -p e-cidade -f docker-compose.php85.yml up -d
docker-compose -p e-cidade -f docker-compose.proxy.yml up -d
docker exec ecidade_proxy nginx -t
docker ps
```

Nesta maquina esta instalado `docker-compose` 1.29.2. Em maquinas com Compose
atual, usar `docker compose` no lugar de `docker-compose`.

Nao usar `--remove-orphans`: cada arquivo descreve somente parte do ambiente.
Para apenas parar e retomar os servicos, usar `docker stop` e `docker start`
com os nomes dos containers. O banco usa o volume anonimo da imagem PostgreSQL;
preservar esse volume e o container, e guardar dumps antes de recriar o banco.

## Instalacao realizada

- As imagens foram construidas a partir dos Dockerfiles da propria base.
- Os servidores principais do Ubuntu apresentaram timeout. A imagem PHP 7.4
  foi construida com resolucao temporaria para o espelho oficial dos EUA,
  usando `docker build --add-host archive.ubuntu.com:<IP-do-espelho>
  --add-host security.ubuntu.com:<IP-do-espelho> -t ecidade-php74:latest
  docker/php74-apache`. Esse ajuste vale apenas durante a construcao.
- Foram instalados os 165 pacotes do `composer.lock`, incluindo desenvolvimento:
  zero atualizacoes e zero remocoes. Manifesto, lock e Dockerfiles permanecem
  inalterados. Os avisos de autoload PSR-4 existentes nao foram corrigidos.
- A configuracao local veio dos exemplos do projeto, por `configure-desktop`.
  O `.env` aponta para `ecidade_database:5432`, banco `ecidade`, com URL local
  `http://localhost:8090`. Foram geradas a chave da aplicacao e as chaves locais
  do Passport. Nao foi executado `passport:install`.
- Um PostgreSQL novo recebeu o dump `ecidade/docker/ecidade_base.sql.gz`,
  preservando o arquivo comprimido. Foram aplicadas somente as adaptacoes para
  PostgreSQL 16 e o `pos.sql` ja presentes no instalador do projeto.
- A copia anterior a qualquer migration esta em
  `ecidade/dumps/base-php74-antes-migrations.dump`, com os roles em
  `ecidade/dumps/base-php74-globals.sql`. Ambos ficam fora do versionamento.
  A leitura do catalogo do backup com `pg_restore --list` passou.

## Linha de base da entrada

`GET /` respondeu nas tres portas com HTTP 302 e `Location: login.php`.

`GET /login.php`, com o mesmo cabecalho `Host: localhost:8090`, respondeu nas
tres portas com HTTP 200, `text/html; charset=ISO-8859-1` e 11.052 bytes.
Os formularios de usuario e senha e o JavaScript de entrada estao presentes.

A unica diferenca entre os corpos e o identificador aleatorio de 32 caracteres
em `carregaCaptcha.php?sid=...`. Substituindo somente esse identificador por
`SID`, os tres corpos ficam identicos, com 11.023 bytes e SHA-256
`5bd718831c6ca8e7d90f2cbc61654a26304843988b0e45fd60990a360484fe7c`.

As respostas brutas, os cabecalhos, as respostas normalizadas e a captura do
navegador pelo proxy estao em `ecidade/tmp/linha-base-php74/`, fora do Git.
O navegador confirmou a renderizacao do formulario, imagens e estilos.
As extensoes exigidas pelo ambiente foram verificadas nos dois PHPs, e a
conexao do PHP 8.5 ao PostgreSQL foi confirmada por leitura.

## Limites e proximo passo

Nao foram executadas migrations. O dump restaurado registra 456 migrations;
a ultima e `2022_12_29_093554_M23031_adiciona_formasarrecadacao_baixabanco`.
Faltam `configuracoes.itens_menu_usuario_favoritos` e a coluna
`db_itensmenu.api`, exigidas pelo Desktop da nova base.

A aplicacao das migrations no banco descartavel depende da decisao prevista
no documento de migracao. A entrada foi validada; autenticacao, menu e telas
internas ainda nao foram validados. A abertura da entrada no PHP 8.5 nao prova
compatibilidade do Laravel 8, das rotas ou dos modulos com esse runtime.
Nao foram chamados servicos externos durante os testes da aplicacao.
