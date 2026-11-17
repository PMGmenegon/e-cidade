# Linha de base do login da API V1 (5.6)

`POST /api/v1/auth/login` (`api/V1/Controllers/Auth/Login.php`): resposta do PHP 5.6 a entradas inválidas e incompletas, gravada para
comparar com o runtime novo. O módulo reaproveita o cliente HTTP da camada de sistema (`ecidade/tests/sistema/Cliente.php`) e só
documenta o comportamento atual; nada é corrigido.

## O que entra e o que fica de fora

O endpoint só chega ao controller com um **cliente da API válido** (`id` + `hash` AES com a chave do cliente, `AuthMiddleware`).
Com cliente válido, o próprio sistema grava, **antes** de conferir usuário e senha, `configuracoes.api_clients.db172_ultima_utilizacao`
e a trilha de auditoria dessa alteração. Medido numa rodada de 34 requisições (19 com cliente válido), no 5.6:

| Tabela | Linhas gravadas |
|---|---|
| `configuracoes.api_clients` | +19 (`db172_ultima_utilizacao` passou de `NULL` para `2026-11-13 01:39:49`) |
| `configuracoes.db_acount` | +95 (19 × 5 colunas) |
| `configuracoes.db_acountacesso` | +19 |
| `configuracoes.db_acountkey` | +19 |
| `configuracoes.db_usuariosonline` | +32 |

Por isso o roteiro tem **só os casos que não chegam a essa gravação** (A01–A15). Os casos que exigem cliente válido (credencial certa e errada,
usuário inexistente, campos vazios ou ausentes, tipos trocados, entradas longas) **não têm linha de base**: ficam como lacuna até existir um
cliente de teste em banco descartável. As linhas gravadas na rodada de medida não foram apagadas nem restauradas.

Os casos A01–A15 não gravam nada: o vigia do banco (lista padrão, sem `api_clients` nem `db_acount*`) fecha com rc=0 em todas as rodadas e
`db172_ultima_utilizacao` fica igual antes e depois (o `captura.sh` lê só essa coluna).

## Como rodar

Containers do agente no ar e **com gravação** (sem `SOMENTE_LEITURA`: a API V1 abre conexão com o banco):

```bash
bash ecidade/tests/sistema/login-api-v1/captura.sh <agente> 56 /tmp/rodada1   # roteiro + vigia antes/depois; exit 3 se o vigia acusar
bash ecidade/tests/sistema/login-api-v1/captura.sh <agente> 56 /tmp/rodada2
bash ecidade/tests/sistema/login-api-v1/captura.sh <agente> 85 /tmp/rodada85
bash ecidade/tests/sistema/login-api-v1/compara.sh /tmp/rodada1 /tmp/rodada2   # e 56 x 85
```

`roteiro.php` roda dentro do container e grava um `.out` por caso (status, tipo, nomes de cookie, `Location`, corpo normalizado: stacktrace
omitido, hash de resposta trocado por marcador). **Linha de base do 5.6:** `login-api-v1/base-5.6/` (15 `.out` + `resumo.tsv`).
Id e chave do cliente são lidos do banco só em memória (casos A05, A14 e A15) e nunca são impressos nem gravados.

## Casos (todos sem cliente válido)

| Caso | Entrada | 5.6 (= 8.5) |
|---|---|---|
| A01 | POST sem corpo | 500 json, "Sem permissão para acessar a API." |
| A02 | `user`/`password` sem `id`/`hash` | 500, idem |
| A03 | `id` não numérico | 500, idem |
| A04 | `id` numérico inexistente | 500, "Cliente não encontrado." |
| A05 | `id` existente, hash inválido | 500, "Sem permissão…" |
| A06 / A07 | GET / PUT | 405 json, `No route found … Method Not Allowed (Allow: POST)` |
| A08 | GET com `user`/`password` na query | 405 |
| A09 | corpo JSON (`Content-Type: application/json`) | 500, "Sem permissão…" (só lê campos de formulário) |
| A10 | `id[]=1` | 500, idem |
| A11 | `user` com 1 MB | 500, idem |
| A12 | cabeçalho `X-Forwarded-For` com aspa | 500, idem |
| A13 | cookie de sessão já existente | 500, idem |
| A14 | hash válido sem o campo `time` | 500, "Tempo não informado no HASH." |
| A15 | hash válido com `time` antigo | 500, "A requisição informada não é valida." Só é enviado se já houver uma última utilização gravada (sem ela o sistema aceita o hash e grava) |

Todas respondem `application/json`; os erros saem como **HTTP 500** (o `statusCode` do corpo é o objeto `Request` serializado, como no 5.6).

## Rodadas (A01–A15)

| Rodada | Runtime | Resultado | Vigia |
|---|---|---|---|
| 1 | 5.6 | 15 casos | rc=0 (0 tabelas alteradas) |
| 2 | 5.6 | **igual à rodada 1** (`diff -r`, 15/15) | rc=0 |
| 3 | 8.5.12 | **igual ao 5.6** (15/15) | rc=0 |

`db172_ultima_utilizacao`: `2026-11-13 01:39:49` antes e depois de cada rodada.

## Rodadas no container próprio da API V1 (vendor só dela)

Mesmos 15 casos contra o container da API (`docker-compose.api-v1.yml`, `docs/migracao-laravel/api-v1-container.md`): imagem do 8.5, mesmo código,
`vendor/` só da API (23 pacotes, Silex 2.2.4 + Symfony 3.4, sem `laravel/framework`). Duas formas de chegar a ele: direto ao container e **pelo proxy** com a
regra `/api/v1/` (`docker/proxy/nginx.conf`; o cabeçalho `X-Ecidade-Runtime: PHP-8.5 (API V1, vendor proprio)` confirma quem respondeu).

```bash
bash ecidade/tests/sistema/login-api-v1/captura.sh <agente> api /tmp/api1                       # direto ao container ecidade_<agente>_api
BASE=http://<proxy> bash ecidade/tests/sistema/login-api-v1/captura.sh <agente> api /tmp/px1    # pelo proxy
diff -r /tmp/api1/casos ecidade/tests/sistema/login-api-v1/base-5.6                              # contra a linha de base do 5.6
```

| Rodada | Caminho | Resultado | Vigia |
|---|---|---|---|
| 1 e 2 | direto ao container da API | iguais entre si (15/15) e **iguais à linha de base do 5.6** (15/15: status, tipo, cookies e corpo normalizado) | rc=0 |
| 3 e 4 | pelo proxy, regra `/api/v1/` | iguais entre si (15/15) e **iguais à linha de base do 5.6** (15/15) | rc=0 |

Nenhuma diferença a classificar. `db172_ultima_utilizacao` ficou em `2026-11-13 01:39:49` antes e depois de cada rodada; nenhum caso com cliente válido foi executado.

## Lacunas

Casos com cliente válido sem linha de base (acima). O 8.5 só foi comparado nos 15 casos sem cliente válido, com o `vendor/` atual;
a atualização do Laravel/Silex é outra frente.
