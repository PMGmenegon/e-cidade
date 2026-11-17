# Container próprio da API V1 e regra `/api/v1/` no proxy

> 13/11/2026 (rótulo: T-047). A API V1 (`ecidade/api/V1`, Silex 2.2.4 + Symfony 3.4) passa a ser atendida por um
> container só dela, com o `vendor/` só dela (`docs/migracao-laravel/api-v1-dependencias.md`), e o proxy manda `/api/v1/`
> para ele. Motivo: o Symfony 3.4 da API e o Symfony do Laravel novo não convivem no mesmo processo (mesmos namespaces
> `Symfony\Component\*`), e o Silex não resolve junto com o Laravel novo. Caminho escolhido entre os dois possíveis: (a)
> escolher o autoload pela porta de entrada (`bootstrap.php:26`, `bootstrap/autoload.php`, `FrontController.php:4-5`),
> que mexe no núcleo; ou (b) container próprio com regra no proxy, que é só infraestrutura e segue o padrão que o projeto
> já usa para mandar cada prefixo ao runtime certo (`docker/proxy/nginx.conf`). Ficou o (b): nenhum arquivo do sistema
> muda, o 5.6 e o runtime do Laravel ficam intocados. Custo: um container a mais para subir.

## Arquivos

| Arquivo | Papel |
|---|---|
| `docker-compose.api-v1.yml` | serviço `ecidade_api_v1`: imagem do 8.5 de hoje (`docker/php85-apache`), o **mesmo código**, `$API_DIR/vendor` (padrão `./runtime-api/vendor`) **somente leitura** por cima do `vendor/`, o volume de sessão e o `/tmp` do 5.6, o `php.ini` de paridade; porta padrão 8086 |
| `docker/proxy/nginx.conf` | `location ~ ^(?:/w/[0-9]+)?/api/v1/` → `ecidade_api_v1:80`, antes das outras regras; cabeçalho `X-Ecidade-Runtime: PHP-8.5 (API V1, vendor proprio)`; sem o container da API, desvio (`error_page 502 503 504` → `location @api_v1_destino_de_hoje`) para o destino de hoje, o mesmo do `location /` |

A expressão é a do `FrontController.php:4` (`[^?]*api\/v\d\/`), restrita a `v1` e ao início do caminho, com ou sem o
`/w/<n>/` do desktop. O nome `ecidade_api_v1` é resolvido **no pedido** (DNS interno do Docker, `resolver 127.0.0.11`): o
proxy sobe e responde mesmo sem o container da API, e volta a mandar `/api/v1/` ao container quando ele sobe, sem reiniciar o
proxy.

**Sem o container da API, `/api/v1/` continua como hoje.** Quando o nome não resolve ou a conexão é recusada, o proxy gera
502 e o `error_page` manda o mesmo pedido (com o corpo) ao destino do `location /` — hoje o 5.6, como antes desta regra.
O desvio só acontece se **nada** chegou a ser enviado ao container da API (`$upstream_bytes_sent` vazio ou `0`): se a API
já recebeu o pedido e falhou depois (tempo esgotado, conexão cortada), a resposta é 502 e o pedido **não** é repetido no
outro runtime — um POST (recibo, inscrição) seria executado duas vezes. Respostas de erro da própria API (403, 500) passam
como estão, sem desvio.

## Como subir e derrubar (ambiente oficial)

Depois do proxy e dos runtimes de sempre (`CLAUDE.md`, "Como subir o ambiente"):

```bash
# 1. vendor da API (uma vez; comando completo em docs/migracao-laravel/api-v1-dependencias.md)
# 2. container da API
docker compose -f docker-compose.api-v1.yml up -d
# 3. o proxy relê o nginx.conf (bind mount de arquivo unico)
docker compose -f docker-compose.proxy.yml up -d --force-recreate
# derrubar so a API (o proxy continua; /api/v1/ volta ao destino de hoje)
docker compose -f docker-compose.api-v1.yml down          # nunca com --remove-orphans
```

**Sessão:** a API valida a sessão do login legado (cookie `ECIDADEWINDOWMAIN`, gravado pelo `abrir.php` no 5.6). O volume de
sessão compartilhado (`ecidade_sessions`) é **obrigatório** no container da API. Medido com o mesmo cookie de um login pelo
proxy: container com o volume → `GET /w/1/api/v1/protocolo/cgm/1` 200 com os dados; container sem o volume → 403
(`Sessão inválida ou expirada`, o mesmo 403 que o 5.6 dá sem sessão). O `/tmp` compartilhado segue o 8.5 de hoje.

## Prova (13/11/2026)

Ambiente de teste isolado do oficial: rede Docker própria em que os containers de teste respondem pelos nomes que o
`nginx.conf` usa (`ecidade_php56`, `ecidade_php85`, `ecidade_api_v1`, por apelido de rede), volume de sessão próprio
compartilhado pelos três, e dois proxies `nginx:1.27-alpine` com o mesmo `faseb_map.conf`: um com o `nginx.conf` antes da
mudança (`:8115`) e um com o novo (`:8114`). Vigia do banco (`pg_stat_user_tables` antes/depois) em volta de cada rodada:
só mudaram o log de acesso (`db_logsacessa_*`), usuários online (`db_usuariosonline`) e o token do login
(`oauth_access_tokens`/`oauth_refresh_tokens`).

**1. Cada lado com o seu vendor** (`vendor/composer/installed.json` dentro do container e `docker inspect`):

| Container | Pacotes | `silex/silex` | `symfony/http-kernel` | `laravel/framework` | `vendor/` vem de |
|---|---|---|---|---|---|
| API | 23 | v2.2.4 | v3.4.49 | ausente | `runtime-api/vendor` (ro) |
| 8.5 de hoje | 140 | v2.2.4 | v3.4.49 | v5.4.36 | o `ecidade/vendor` do código |

O runtime 8.5 de hoje ainda usa o vendor do 5.6 (com Symfony 3.4). A prova de que o runtime do Laravel novo não carrega
Symfony 3.4 só existe quando o vendor do Laravel novo existir; a mesma medição (esta tabela e a do item 2) deve ser
repetida então.

**2. As 4 GET da API pelo proxy novo, iguais ao 5.6** (cliente `ecidade/tests/sistema/Cliente.php`: token do password grant
pedido ao 5.6, sessão legada feita em cada alvo, `{param}` → `1`, comparação por status, tipo e corpo sem token,
`stacktrace`, `file`, `line`):

| Rota | 5.6 direto | proxy antigo (→ 5.6) | proxy novo (→ container da API) |
|---|---|---|---|
| `GET /api/v1/configuracao/formulario/1/instituicao/1` | 500 JSON "Formulário de código 1 não existe…" | igual | **igual** |
| `GET /api/v1/matriculaonline/emissaoProtocolo` | 500 JSON "Sem permissão para acessar a API." | igual | **igual** |
| `GET /api/v1/protocolo/cgm` | 200 JSON | igual | **igual** |
| `GET /api/v1/protocolo/cgm/1` | 200 JSON | igual | **igual** |

O log do Apache do container da API registrou os 4 pedidos; o cabeçalho `X-Ecidade-Runtime` pelo proxy novo é
`PHP-8.5 (API V1, vendor proprio)` e pelo antigo `PHP-5.6 (referencia)`. Sem sessão, `GET /api/v1/protocolo/cgm` dá 403 no
5.6 direto, no proxy antigo e no novo. As 3 rotas POST não foram chamadas (gravam no banco).

**3. As outras telas não mudam.** Telas de menu de um prefixo por área (as ligadas em `db_menu`, que existem no disco, com o
parâmetro do menu), proxy antigo × novo, mesma sessão restaurada antes de cada pedido, mesmas normalizações da bateria do
projeto:

| Área | Prefixo | Telas | Idênticas | Divergentes | Timeout | Vigia |
|---|---|---|---|---|---|---|
| Tributário | `cem` | 47 | 47 | 0 | 0 | OK |
| Educação | `bib` | 44 | 44 | 0 | 0 | OK |
| Recursos Humanos | `eso` | 39 | 39 | 0 | 0 | OK |
| Patrimonial | `ouv` | 29 | 29 | 0 | 0 | OK |
| Financeiro | `cus` | 16 | 16 | 0 | 0 | OK |
| Saúde | `vac` | 34 | 34 | 0 | 0 | OK |
| Configuração | `sys` | 24 | 24 | 0 | 0 | OK |
| **Total** | 7 | **233** | **233** | **0** | **0** | 7 × OK |

Repetida em 14/11/2026 com o desvio do item 4 no `nginx.conf`: de novo 233/233, vigia 7 × OK.

**4. Desvio ao destino de hoje** (14/11/2026, mesmo ambiente de teste, vigia `OK` em cada rodada). As 4 GET do item 2 e 3
POST de erro de `/api/v1/tributario/recibo` que não gravam (corpo vazio, `{}` e `{"id":"999999","hash":"abc"}`, este
respondido `Cliente não encontrado.`, ou seja, o corpo chega) pelos três caminhos — 5.6 direto, proxy antigo, proxy novo:

| Cenário | Proxy novo serve por | 4 GET | 3 POST |
|---|---|---|---|
| container da API inexistente | 5.6 (`X-Ecidade-Runtime: PHP-5.6 (referencia)`) | iguais ao 5.6 e ao proxy antigo | iguais |
| container da API criado e parado | 5.6 | iguais | iguais |
| container da API no ar | container da API (`PHP-8.5 (API V1, vendor proprio)`) | iguais | iguais |

Guarda contra repetição: proxy de teste com o mesmo `nginx.conf` e só `proxy_read_timeout 3s`, e no lugar do container da
API um processo que aceita a conexão e não responde. `GET` e `POST` em `/api/v1/tributario/recibo` → **502** com
`X-Ecidade-Runtime: PHP-8.5 (API V1, vendor proprio)` e **0** pedidos no log de acesso do 5.6. Controle, sem esse
processo: o mesmo `POST` → 500 do 5.6 (`PHP-5.6 (referencia)`) e 1 pedido no log do 5.6.

## O que isto não prova

- O runtime do Laravel novo sem Symfony 3.4 (item 1): depende do vendor do Laravel novo; repetir os itens 1 e 2 contra ele.
- As 3 rotas POST da API e o login da API (`POST /api/v1/auth/login`), que gravam.
- O ambiente oficial (`:8090`): a regra foi medida em proxies de teste com o mesmo `nginx.conf`; o oficial passa a usá-la
  quando for recriado. Sem o container da API ele segue igual a hoje (desvio ao 5.6).
