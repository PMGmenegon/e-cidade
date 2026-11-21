# Ambiente local da base-php74

Verificado em 19/11/2026 e revalidado em 21/11/2026, a partir do commit
`982a95fb5902186cab75fa25d30c83ee52e7695d`, na branch
`nucleo/ambiente-base-php74`. Escopo: iniciar os runtimes e o proxy, preparar
o banco local e validar entrada, autenticacao, Desktop e uma consulta. A migracao
das areas, do Laravel e das APIs permanece com as respectivas frentes.

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
  `http://localhost:8090`, com `APP_ENV=testing`. Foram geradas a chave da
  aplicacao e as chaves locais do Passport. Nao foi executado `passport:install`.
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

## Validacao da abertura

- Login real com a conta demonstrativa nas portas 8080 e 8090, emissao de
  token, carregamento completo do Desktop e das 11 areas do menu: passou.
- Logout com retorno a entrada e tentativa com senha incorreta recusada:
  passaram. A credencial de teste foi preparada pela funcao do proprio projeto.
- Navegacao por Configuracao > Consultas > Consulta procedimentos: passou,
  incluindo os frames, o departamento e o exercicio. Os recursos dessa
  navegacao nao apresentaram falhas HTTP.
- A mesma consulta autenticada, `/w/1/sys3_proced001.php`, respondeu HTTP 200
  nas tres portas, com 22.529 bytes identicos, sem normalizacao. SHA-256:
  `1ced7c14a6b285b3a721a881cf6bb1dee0931a0640c2786cea6bfa78bd8d8f57`.
- Na revalidacao de 21/11, os contadores registraram um token de acesso, um de
  renovacao, um usuario on-line com tres atualizacoes e sete logs de acesso.
  Nao houve gravacao de dados de negocio. A auditoria do sistema foi preservada.
- Parada e retomada dos quatro containers, mantendo volumes e banco: passou.
  A verificacao automatica detectou os servicos parados e voltou a passar
  depois da retomada. O fluxo autenticado foi repetido apos o reinicio.

As capturas, comparacoes e contagens estao em `ecidade/tmp/linha-base-php74/`.
Os artefatos da revalidacao de 21/11 ficaram em diretorio temporario fora do
repositorio; o perfil de navegador criado nessa rodada foi removido.
Nao foram exercitadas integracoes externas de negocio, nem operacoes de
cadastro, calculos, pagamentos ou emissao de documentos.

## Preparar o Desktop em uma instalacao de teste

Partir de uma instalacao do projeto com o dump original restaurado, dependencias
do lock instaladas, configuracao local e chaves geradas, conforme o
[README](../../README.md). Nunca repetir o instalador original em banco existente.
Usar `APP_ENV=testing`, `APP_URL=http://localhost:8090` e `DB_PORT_ALT=5432` no
`.env` local; a conexao deve apontar ao PostgreSQL descartavel deste ambiente.

O script abaixo aplica apenas seis migrations existentes do PR: dois ajustes
do Passport, notificacoes, coluna `db_itensmenu.api`, tabela de favoritos e
item de menu de favoritos. Tambem prepara a conta demonstrativa
`dbseller` / `dbseller`, usando a funcao de senha do projeto.

**Somente banco descartavel restaurado do dump.** O script exige uma marcacao
explicita e nao deve ser usado em instalacoes com usuarios ou dados reais.

```bash
mkdir -p ecidade/dumps
docker exec ecidade_database pg_dump -U postgres -d ecidade -Fc > ecidade/dumps/base-php74-antes-desktop.dump
docker exec -i --env ECIDADE_BANCO_DESCARTAVEL=1 ecidade_php74 bash -s < docker/prepara-desktop-php74.sh
```

A preparacao foi comprovada em uma segunda copia limpa do dump: passou de
456 para 462 migrations registradas, autenticou a conta e carregou as 11
areas do Desktop sem erros HTTP. Repetir o script retornou `Nothing to migrate`.
O bloqueio sem a marcacao de banco descartavel tambem foi testado.

Verificar as permissoes de escrita do grupo `www-data` em `storage`,
`bootstrap/cache`, `tmp`, `extension/log`, `arquivos` e `extension/data`, alem
de `config` para as preferencias locais. Os volumes comuns precisam das
permissoes descritas no inicio deste registro.

## Verificacao repetivel

```bash
python3 scratchpad/verifica_ambiente.py
```

Usa somente a biblioteca padrao do Python. Confere redirecionamento da raiz,
HTTP 200 na entrada, formulario, JavaScript, charset, equivalencia dos corpos
e encaminhamento do proxy ao 7.4. Sai com erro se algum criterio falhar.
Esse comando verifica disponibilidade e entrada; os testes autenticados
descritos acima foram feitos separadamente no navegador.

Os padroes `*.dump`, `*.log`, `/ecidade/dumps/` e `/ecidade/tmp/` estao
explicitamente ignorados na raiz. Configuracao local, bancos, logs e capturas
nao integram os commits da linha de base.

## Pendencias das outras frentes

O login direto pelo PHP 8.5 ainda retorna HTTP 500 ao carregar o CAPTCHA
legado; `securimage/securimage.php` nao compila nesse runtime. A frente PHP
8.5 deve portar esse ponto. O login continua no 7.4 pelo proxy, e nenhum
modulo foi roteado ao 8.5. A abertura da entrada e da consulta no 8.5 nao
comprova a compatibilidade de todas as telas ou do Laravel 8 com esse runtime.

A tentativa de executar todas as migrations encontrou problemas anteriores
de instalacao no dump. No banco principal deste teste ficaram 593 registros
de migrations; a execucao geral parou em
`2023_04_17_134234_m23809_adicionando_campo_is_classe_bilingue`, que referencia
o registro inexistente `db_sysarquivo.codarq=1010083`. Essa falha de Educacao
nao foi corrigida nesta frente, nem marcada como executada.

Antes desse bloqueio, foram conferidos dois estados ja existentes no dump
(a estrutura de 2019 e a remocao das tabelas de tutorial) para regularizar seu
historico. Duas views ausentes foram preparadas com as definicoes da propria
migration; duas tabelas de backup conflitantes foram preservadas com sufixo
`_antes_migracao`. Tres migrations de SQL legado exigiram
`PGOPTIONS='-c standard_conforming_strings=off'` somente nas respectivas
conexoes. Nenhum arquivo de migration foi modificado.

Esses ajustes da tentativa geral nao sao necessarios para o procedimento
minimo de abertura, comprovado separadamente na copia limpa. As migrations
das areas continuam sob responsabilidade das respectivas frentes. A
preparacao do Desktop nao significa que todas as migrations foram aplicadas
ou que os modulos de negocio foram homologados.
