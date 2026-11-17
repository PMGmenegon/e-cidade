# Convivência de sessão entre os runtimes hoje — linha de base (T-032, 13/11/2026)

Pergunta da PB-009 (critério 4): a sessão aberta num runtime vale no outro? Medido **sem mudar nada** (Regra 3): é o comportamento
herdado, não requisito novo. Script: `ecidade/tests/sistema/sessao-entre-runtimes.sh <agente>`; dados:
`ecidade/tests/sistema/dados/sessao-entre-runtimes-{compartilhada,isolada}.tsv`.

## Onde a sessão é guardada (critério 2)

| | PHP 5.6 | PHP 8.5 |
|---|---|---|
| Handler | `files` — `/etc/php/5.6/apache2/php.ini:1427` (`session.save_handler = files`) | `files` (padrão) |
| Caminho | `/var/lib/php/sessions` (padrão; `php.ini:1456` comentado) | `/var/lib/php/sessions` — `docker/php85-apache/Dockerfile:43` |
| Vida | `session.gc_maxlifetime = 7200` — `docker/php56-apache/Dockerfile:64` / `php.ini:1537` | `7200` — `docker/php85-apache/Dockerfile:42` |
| Nome do cookie | `ECIDADEWINDOWMAIN` (`src/V3/Window/Session.php:14`; uma sessão por janela, prefixo `ECIDADEWINDOW`; `PHPSESSID` é só o padrão do ini) | idem (mesmo código) |
| Cookie | caminho `/`, sem domínio (`Session.php:40-45`); o navegador não separa por porta | idem |
| Banco | **não** é guardada no banco (só `db_usuariosonline`, registro de usuário online) | idem |

A convivência vem de **um diretório comum**: `docker-compose.sessions.yml` monta o volume `ecidade_sessions` no 5.6 e
`docker-compose.php85.yml:36` monta o mesmo no 8.5 (o `docker-compose.proxy.yml` pressupõe isso). Os dois lêem/gravam o
mesmo arquivo `sess_<id>`. Evidência medida: `session.save_path|handler|name|gc_maxlifetime` por `php -r` nos dois
containers = `/var/lib/php/sessions|files|PHPSESSID|7200`.

## Medição (critério 1)

Login legado **contornando a tela** (`login.php` para o cookie, depois `POST abrir.php` direto, `dbseller`) num runtime; o mesmo cookie `ECIDADEWINDOWMAIN` é enviado a 3 telas de áreas
diferentes (`sau2_cgsduplos001`, `cai3_gerfinanc001`, `pro4_canarquiv001`: saúde, financeiro, patrimonial). "Logado" = o corpo
**não** é `Sessão inválida (12)` (`libs/db_conecta.php:43`). Sem escolher módulo, as telas respondem 200 com os avisos
`Variavel de sessão nao encontrada: DB_modulo…` (271 bytes) — isso é sessão aceita; sem sessão são 66 bytes de `Sessão inválida (12)`.
Nenhuma resposta redireciona (todas HTTP 200, sem `Location`).

| Cenário | Do 5.6 para o 8.5 | Do 8.5 para o 5.6 |
|---|---|---|
| **Volume de sessão compartilhado** (como `docker-compose.sessions.yml`/`php85.yml`) | 3/3 logado, 200 | 3/3 logado, 200 (*) |
| **Sessões separadas** (containers por agente de `sobe-ambiente.sh`, cada um com o próprio `/var/lib/php/sessions`) | 3/3 **não logado**, 200 | 3/3 **não logado**, 200 |
| Controle (login e tela no mesmo runtime) / sem cookie | logado / não logado | logado / não logado |

(*) **O sentido 8.5 → 5.6 só foi medido contornando a tela de login.** O template ativo (`config/require_extensions.xml:84` →
`templates/template_login_e-cidade.php`) primeiro faz `POST v4/oauth/token` (linha 199) e só abre `abrir.php?sAuth=…`
(linhas 222-224, GET no navegador; o script manda os mesmos `DB_login`/`DB_senha` por POST, equivalente pelas globais) se o token
voltar 200; no `.catch` (linhas 230-232) mostra "Houve um erro ao se autenticar." e **não abre sessão**. Como o `/v4/oauth/token`
dá 500 no 8.5, **pelo navegador não há login no 8.5 hoje**: a coluna "Do 8.5 para o 5.6" mostra que uma sessão criada no 8.5 (por
`abrir.php` direto) é aceita pelo 5.6, não que o usuário consiga logar nele.

Conclusão: **hoje a sessão criada num runtime vale no outro nos dois sentidos, e só porque os dois enxergam o mesmo diretório de
sessões.** Pelo caminho normal (navegador) o login só acontece no 5.6; o 8.5 só recebe a sessão. Sem o volume comum a
convivência não existe.

## Token OAuth do `/v4` (critério 3)

| Passo | Resultado |
|---|---|
| `POST /v4/oauth/token` (password grant) no 5.6 | 200, emite |
| token do 5.6 em `GET /v4/api/configuracao/banco-pix/listar` no 5.6 | 200 |
| o mesmo token no 8.5 | **500** (Laravel 5.4 não roda em PHP 8; o token não chega a ser avaliado) |
| `POST /v4/oauth/token` no 8.5 | **500**, não emite |

O token mora no banco (`oauth_access_tokens`), não na sessão; portanto não é a camada que impede o cruzamento — é o `/v4` do 8.5
que não sobe. Se o `/v4` rodasse no 8.5, um token do 5.6 poderia ser aceito (mesmo banco/chaves); isso **não foi medido**.

## Como reproduzir os dois cenários

- **Sessões separadas:** `bash <quadro>/ferramentas/sobe-ambiente.sh <Agente> <worktree> <porta-base>` (cada container com o próprio
  `/var/lib/php/sessions`; o script não monta volume de sessão).
- **Volume compartilhado:** o mesmo, mas subindo os containers à mão com um volume comum (o `sobe-ambiente.sh` não o faz):
  ```bash
  A=<agente>; W=<worktree>; R=/home/gustavo/git/ecidade-laravel
  docker volume create ecidade_${A}_sessions
  E=(-e DB_HOST=ecidade_database -e DB_PORT=5432 -e DB_DATABASE=ecidade -e DB_USERNAME=postgres -e DB_PASSWORD=postgres)
  docker run -d --name ecidade_${A}_56 --network e-cidade_ecidade -p <base>:80 "${E[@]}" -v $W/ecidade:/var/www/html \
    -v ecidade_${A}_sessions:/var/lib/php/sessions e-cidade-ecidade_php56 apachectl -D FOREGROUND
  docker run -d --name ecidade_${A}_85 --network e-cidade_ecidade -p <base+1>:80 "${E[@]}" -v $W/ecidade:/var/www/html \
    -v ecidade_${A}_sessions:/var/lib/php/sessions -v $R/docker/php85-apache/paridade-56.ini:/usr/local/etc/php/conf.d/zz-paridade-56.ini:ro \
    ecidade-login-php85
  sleep 3; docker exec ecidade_${A}_56 chmod 1777 /var/lib/php/sessions   # o volume nasce root 755 e o www-data do 5.6 não grava
  ```
  Limpeza: `docker rm -f ecidade_${A}_56 ecidade_${A}_85; docker volume rm ecidade_${A}_sessions`.
- Rodar: `vigia-banco.sh antes <foto>`; `bash ecidade/tests/sistema/sessao-entre-runtimes.sh <agente>`; `vigia-banco.sh depois <foto>`.
  O script sai com `1` se não achar a porta de um container, se o login não devolver `ECIDADEWINDOWMAIN` ou se algum HTTP vier `000`
  (antes, sem containers, saía 0 com `000` e duas rodadas "iguais").

## Como foi rodado (critério 4)

Cada cenário rodado 2× dentro de `vigia-banco.sh antes/depois`: saída do script idêntica nas 2 rodadas (`diff` vazio) e
vigia `OK: so tabelas permitidas` (rc=0) nas 4 execuções. Mudaram só `db_logsacessa_*`, `db_usuariosonline`,
`oauth_access_tokens`, `oauth_refresh_tokens`. As credenciais do cliente OAuth são lidas dentro do container e nunca impressas.

## Lacunas

- Navegador real (cookie compartilhado entre `:8080`/`:8085` e pelo proxy `:8090`) não foi exercitado; usado `curl` com o cookie.
- Telas sem módulo escolhido (não é possível escolher módulo sem gravar `db_usumod`).
