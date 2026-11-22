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

## Conferencia do Fluxo de Login Unificado (5.6 vs 7.4)

Conferencia realizada em 22/11/2026. O objetivo foi identificar as chamadas
do formulario antes e depois do PR #8, sem modificar codigo de autenticacao,
dependencias ou dados de negocio. A comparacao historica usa o commit
`e640eb485bf9a29f1fcda9c289c4ab23cffefe1d`, pai de
`c2c9af06a8ac989c6c12699503a0d4234983b8fd` (PR incorporado na base).
O manifesto anterior declara PHP >=5.6.4, Laravel 5.4 e Passport 4.

### Fluxo anterior: duas etapas, precedidas por uma chamada de configuracao

O handler ativo `js_acessar_dbportal()` do arquivo
`ecidade/templates/template_login_e-cidade.php` executava esta sequencia:

| Ordem | Chamada do navegador | Finalidade |
| --- | --- | --- |
| 1 | `POST /login.rpc.php` | `generateDatabase()` preparava ou removia os cookies de conexao, usando `setCookieDatabase` ou `destroyCookieDatabase`. Nao emitia token. |
| 2 | `POST /v4/oauth/token` | Enviava `username`, `password`, `client_id`, `client_secret` e `grant_type=password`; armazenava `access_token` no armazenamento local. |
| 3 | `GET /abrir.php?sAuth=...` | Abria uma janela com login e resumo MD5 da senha codificados em `sAuth`, alem do CAPTCHA e conexao quando aplicaveis. O PHP concluia a sessao legada e abria `inicio.php`. |

Portanto, havia dois POSTs no formulario e uma requisicao PHP adicional.
As duas etapas de autenticacao eram a emissao do token pelo Passport e a
criacao da sessao por `abrir.php`; `login.rpc.php` era preparacao da conexao.
Nao eram duas APIs independentes necessariamente, e nenhuma dessas chamadas
era a API V1. O fluxo 5.6 foi conferido no historico, nao executado nesta bateria.

### Fluxo atual: uma requisicao cria token e sessao

No mesmo template, `js_acessar_dbportal()` agora envia somente
`POST /v4/login`. Os campos observados foram `DB_HOST`, `DB_DATABASE`,
`DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `username`, `password` e
`conteudoCaptcha`. Os valores de credenciais nao integram este registro.

A rota e registrada por
`ecidade/app/Providers/RouteServiceProvider.php::mapUserAuthRoutes()`,
fora dos grupos definidos por `routes/api.php` e `routes/web.php`:

1. `App\Domain\Configuracao\Usuario\Controller\LoginController::authenticate`
   recebe `LoginRequest` e chama `AuthService::authenticate`.
2. O servico inicia a sessao `MAIN`, verifica usuario, CAPTCHA e versao, e
   chama `createToken()` com as credenciais do cliente obtidas no servidor.
3. `requestToPassport()` cria um objeto `ServerRequest` e chama diretamente
   `AuthorizationServer::respondToAccessTokenRequest`. E uma chamada PHP
   dentro do processo, sem uma segunda requisicao HTTP a `/v4/oauth/token`.
4. `buildSession()` preenche a sessao PHP com usuario, conexao e preferencias.
5. O controller devolve `DBJsonResponse`, com `message`, `error` e `data`.
   `data` contem `token_type`, `expires_in`, `access_token` e `refresh_token`.
6. O navegador guarda os tokens em `ecidade@user_token` e navega na mesma
   janela para `/extension/desktop`. Nao chama `abrir.php` nem `inicio.php`.

`login.php` continua carregando o template configurado e ainda contem a
funcao legada `js_acessar()`. Sua presenca no arquivo nao significa que ela
seja chamada pelo botao atual. `abrir.php` e `login.rpc.php` permanecem no
repositorio, sem alteracoes de conteudo nesse PR, mas sairam do percurso
do formulario padrao medido.

### Rotas preservadas e rotas novas

| Rota registrada no 7.4 | Acao e finalidade |
| --- | --- |
| `POST /v4/login` | `LoginController@authenticate`: sessao e token na mesma resposta. |
| `POST /v4/unblock` | `LoginController@unblock`: valida a senha, renova o token e desbloqueia a sessao existente. |
| `PUT /v4/kill` | `LoginController@kill`: encerra sessoes e cookies. |
| `PUT /v4/logout` | `LoginController@logout`: usa `api` e `auth:api`, revoga o token atual e encerra sessoes/cookies. |
| `POST /v4/oauth/token` | `AccessTokenController@issueToken`: continua registrado pelo Passport, com prefixo `v4/oauth` em `AuthServiceProvider`. Nao foi removido. |

As cinco rotas foram conferidas na colecao carregada do roteador. A listagem
geral de rotas encontrou um controller de outra area com classe ausente;
por isso a verificacao selecionou as rotas relevantes sem instanciar os
controllers alheios. `unblock` e `kill` foram inspecionados, nao disparados.

A API V1 e distinta de `/v4` e de `/rest/v1`. Seu codigo ainda declara
`POST /api/v1/auth/login` em `APIServiceProvider`/`AuthControllerProvider`.
No PR, o `FrontController.php` perdeu o desvio de `api/vN/` para `api/api.php`,
e a dependencia Silex saiu do manifesto. Esse codigo remanescente nao participa
do login padrao do 7.4 e nao foi reativado nesta conferencia.

### Evidencia pratica pelo proxy

Uma submissao do formulario e seu logout foram observados em
`http://localhost:8090`, com a conta demonstrativa e `APP_ENV=testing`.
Foram capturadas 90 requisicoes HTTP e 90 respostas, incluindo imagens,
estilos, fontes e scripts; nenhuma resposta apresentou status 4xx/5xx.
Metodos, caminhos e metadados foram registrados sem valores de cookies,
senhas, tokens ou segredos. A sequencia relevante foi:

| Quantidade | Metodo e caminho | Status |
| --- | --- | --- |
| 2 | `GET /login.php`, na entrada e depois de sair | 200 |
| 1 | `POST /v4/login` | 200 |
| 1 | `GET /extension/desktop`, depois de entrar | 200 |
| 1 | `GET /v4/api/configuracao/menu/buscar-favoritos` | 200 |
| 1 | `GET /v4/api/configuracao/usuario/notificacoes` | 200 |
| 1 | `GET /v4/api/patrimonial/protocolo/documentos/usuario/total` | 200 |
| 1 | `PUT /v4/logout` | 200 |
| 1 | `GET /extension/desktop`, recarregado depois de sair | 302 para `login.php` |

As tres chamadas GET de API pertencem ao carregamento do Desktop, nao sao
novas autenticacoes. Durante a captura houve zero chamadas a `login.rpc.php`,
`abrir.php`, `/v4/oauth/token`, `/api/v1/auth/login`, `unblock` e `kill`.

`GET /login.php` manteve `text/html; charset=ISO-8859-1`. A resposta de
`POST /v4/login` foi `application/json`, com token `Bearer`, duracao de
86.400 segundos e ambos os campos de token preenchidos. Essa resposta emitiu
`Set-Cookie` para `ECIDADEWINDOWMAIN`, com caminho `/` e `SameSite=Lax`;
o cookie foi enviado no GET autenticado do Desktop. As respostas relevantes
trouxeram `X-Ecidade-Runtime: PHP-7.4 (referencia)` e diretivas de nao cache.
O Desktop abriu com 11 areas. O logout usou autorizacao Bearer, respondeu
200, expirou o cookie `MAIN` e removeu os tokens do armazenamento local;
o GET seguinte do Desktop voltou a entrada. Tambem foi observado `PHPSESSID`
no encerramento, sem registrar seu valor.

Os contadores do banco variaram somente em um log de acesso, um token de
acesso inserido e atualizado pela revogacao, e um token de renovacao inserido.
Nao houve exclusao manual de tokens ou auditoria nem escrita em tabelas de
negocio. Os artefatos da captura ficaram fora do repositorio, com metadados
sanitizados; o perfil temporario do navegador foi removido.

`scratchpad/verifica_ambiente.py` permaneceu inalterado e retornou codigo 0.
Ele verifica disponibilidade e equivalencia da entrada, sem autenticar ou
gerar tokens; a medicao do fluxo unificado foi feita separadamente para nao
transformar a verificacao de infraestrutura em um teste que grava no banco.

Conclusao: o PR consolidou as etapas de token e sessao em uma unica chamada
de autenticacao do formulario, `POST /v4/login`. Isso nao removeu todas as
rotas antigas nem significa que abrir o sistema inteiro exija uma unica
requisicao HTTP.
