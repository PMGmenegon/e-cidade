# Linha de base do token /v4 (Passport) no 5.6

Respostas do PHP 5.6 (Laravel 5.4 + Passport 4) à emissão de token em `POST /v4/oauth/token`, ao uso do token numa rota protegida e a casos de
borda, gravadas para comparar com o runtime novo. O módulo `ecidade/tests/sistema/token-v4/` reaproveita o cliente HTTP da camada de sistema
(`ecidade/tests/sistema/Cliente.php`) e só documenta o comportamento atual; nada é corrigido.

## Como rodar

Containers do agente no ar e **com gravação** (emitir token grava `oauth_access_tokens` e `oauth_refresh_tokens`):

```bash
T=ecidade/tests/sistema/token-v4
TOKEN_NOVO=/tmp/tok bash $T/captura.sh <agente> 56 /tmp/r0                  # aquecimento: so gera o token que a rodada seguinte reaproveita
TOKEN_NOVO=/tmp/tok bash $T/captura.sh <agente> 56 /tmp/r1 /tmp/tok
TOKEN_NOVO=/tmp/tok bash $T/captura.sh <agente> 56 /tmp/r2 /tmp/tok
bash $T/captura.sh <agente> 85 /tmp/r85 /tmp/tok                           # token emitido pelo 5.6 reaproveitado no 8.5
bash $T/compara.sh /tmp/r1 /tmp/r2                                         # e 5.6 x 8.5
```

`roteiro.php` roda dentro do container e grava um `.out` por caso (status, tipo, cookies, corpo normalizado: `access_token`/`refresh_token`
trocados por marcador com o tamanho, rastros omitidos, dados do usuário reduzidos a chave e tipo). O `captura.sh` confere o banco antes e depois com o
vigia (lista padrão: `db_logsacessa`, `db_usuariosonline`, `oauth_access_tokens`, `oauth_refresh_tokens`) e sai com 3 se outra tabela mudar. Credenciais do cliente
OAuth vêm de `credenciais.php` (nunca impressas); os tokens ficam só em memória e no arquivo temporário `0600` que passa de uma rodada à outra (fora do repositório).
**Linha de base do 5.6:** `token-v4/base-5.6/` (20 `.out` + `resumo.tsv`).

## Casos e respostas

Rota protegida usada: `GET /v4/api/educacao/escola/vacinas` (leitura; responde 200 com token válido). 5.6 = duas rodadas iguais; 8.5 = uma rodada.

| Caso | Entrada | 5.6 | 8.5 |
|---|---|---|---|
| E01 | senha certa (`dbseller`) | 200 json, `token_type`, `expires_in` (~1 ano: 31536000 s menos o atraso entre emitir e responder; vira o marcador `<~1 ano>` na linha de base), `access_token`, `refresh_token` | 500 html |
| E03 | usuário inexistente | 401 json | 500 html |
| E04 | `username` vazio | 401 json | 500 html |
| E06 | `client_secret` errado | 401 json | 500 html |
| E07 | `client_id` inexistente | 401 json | 500 html |
| E08 / E09 | `grant_type` inválido / ausente | 400 json | 500 html |
| E10 | `scope` inexistente | 400 json (`invalid_scope`) | 500 html |
| E11 | GET no lugar de POST | 405 json | 500 html |
| E12 | corpo JSON | 200 json | 500 html |
| E13 | `username` com 10 mil caracteres | 401 json | 500 html |
| U01 | token recém emitido na rota protegida | 200 json | 500 html |
| U02 / U03 / U04 | token adulterado (1 caractere da assinatura / do payload) / sem assinatura | 500 json, `Unauthenticated.` | sem token para adulterar |
| U09 | token emitido por rodada anterior (no 8.5: emitido pelo 5.6) | 200 json | 500 html |
| C01 / C02 | `POST /v4/api/client/auth/usuario` com `cpfcnpj` inexistente / ausente | 401 json | 500 html |
| C03 | o mesmo com o CPF/CNPJ do usuário 1 (`createToken` de `App\Domain\Client`) | 200 json, dados do usuário + `access_token` (1.071 caracteres; só chave e tipo gravados) | 500 html |
| C04 | uso do token gerado por `createToken` | 200 json | 500 html |

No 8.5 todo caso responde 500 html: o Laravel 5.4 não roda no PHP 8 (ver `docs/registro/laravel.md`). Os 500 json do 5.6 em erros de autenticação são a resposta
atual da rota.

## Gravações (vigia do banco)

Por rodada no 5.6: `oauth_access_tokens` +4, `oauth_refresh_tokens` +2, `db_usuariosonline` +27 a +60 (depende de quantas telas do navegador abertas por outros processos); nenhuma outra tabela. Na rodada do 8.5: só `db_usuariosonline` (+39). As linhas de token ficam no banco (não foram limpas).

## Lacunas (sem linha de base)

- **Credencial incorreta ou vazia, requisição sem token válido e revogação de token:** o resultado depende da configuração do ambiente em que o runtime roda; ficam fora da linha de base
  versionada (a comparação com o runtime novo só vale com o mesmo ambiente).
- **Token expirado:** exigiria mudar o relógio ou a validade gravada; a validade emitida é de 1 ano (`expires_in` ~31536000). Sem escrita direta no banco, não há como expirar.
- **Usuário 6 × cliente pessoal 6:** `createToken()` usa o cliente pessoal de id 6, e a rota `client/auth/usuario` só emite para usuário com CPF/CNPJ cadastrado. O usuário 6 não tem
  CPF/CNPJ na base, então a emissão para ele não é possível sem tocar no banco. Só o usuário 1 (C03/C04) tem linha de base.
- O 8.5 só foi comparado com o `vendor/` atual (Laravel 5.4 em PHP 8), onde tudo é 500.
