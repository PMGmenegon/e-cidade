# API V1 (Silex): POST de recibo e inscricao, so caminhos de erro (sem gravar)

Teste: `ecidade/tests/sistema/SistemaApiV1PostTest.php` (camada sistema, usa `Cliente.php`). Dados: `ecidade/tests/sistema/dados/api-v1-post-erros.tsv`.
Roda no 5.6 e no 8.5 atuais e compara; rodar com `bash ecidade/tests/suite/rodar.sh --camada sistema --agente <nome>` ou o arquivo direto no PHPUnit.

## O que e coberto

POST em `/api/v1/tributario/recibo` e `/api/v1/matriculaonline/inscricao` (2 rotas) com 8 casos cada (16 comparacoes):
corpo vazio, JSON vazio, JSON invalido, so `id`, so `hash`, `id` nao numerico, cliente inexistente (`id=2147483647`) e hash
invalido para um cliente existente (o codigo e lido do banco; a chave nunca e lida nem usada).

Todos terminam em `AuthMiddleware` (`api/V1/Middleware/Auth/AuthMiddleware.php`), **antes** de `PersistUserDataServiceProvider`,
que e quem grava o cliente da API (`ApiClienteRepository::save`, coluna `db172_ultima_utilizacao`). Resultado nos dois runtimes:
HTTP 500 `application/json` com a mensagem `Sem permissao para acessar a API.` (14 casos) ou `Cliente nao encontrado.` (2 casos,
`cliente inexistente`). O teste normaliza os campos volateis do corpo (rastro, arquivo, linha).

## Resultado (13/11/2026)

16 de 16 iguais entre 5.6 e 8.5; duas rodadas seguidas com o mesmo relatorio (diff vazio). O vigia do banco (`antes`/`depois`
em volta de cada rodada) fechou com rc=0 nas duas: mudaram apenas `db_logsacessa_*` e `db_usuariosonline`.

## Lacunas (nao cobertas)

- **Caminho de sucesso** de `recibo` e `inscricao`: grava o cliente da API (`db172_ultima_utilizacao`), o recibo e a inscricao, e
  precisa de um cliente valido com a chave; fica fora porque gravaria no banco.
- **Replay de hash antigo** (`A requisicao informada nao e valida.`): exige a chave do cliente para montar o hash; fora.
- **Sem permissao de usuario** em `recibo` (`idUsuario` ausente/invalido/inexistente, `UserAuthServiceProvider`): so e alcancado depois do
  `save` do cliente, ou seja, depois de uma gravacao; fora.
- **Comparacao com o runtime novo** (Laravel/PHP atualizados): sera repetida quando esse runtime existir; hoje a coluna "novo" e o 8.5
  com o mesmo vendor.
