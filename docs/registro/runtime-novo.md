# Runtime novo com `vendor/` próprio (T-022)

> Preparação da troca das bibliotecas do Laravel, 12–13/11/2026. Constrói o **mecanismo** que dá ao runtime novo (PHP 8.5)
> `vendor/`, `bootstrap/cache` e `storage/` próprios, sem escolher versão do Laravel: a prova usa uma **cópia do vendor
> atual**. A troca de versão é a etapa seguinte (bibliotecas do Laravel 13). Origem da ideia: a medição de 14/10/2026 em `laravel.md` (container
> `ecidade_lar12`, "vendor próprio do 8.5").

## Por que

O 5.6 e o 8.5 montam o mesmo `ecidade/vendor`. Nenhuma versão do Laravel roda nos dois PHPs (5.4 é a última do 5.6 e não
roda no 8; a 12 e a 13 exigem PHP 8.2+/8.3+). Atualizar o Laravel no `vendor/` comum derrubaria o 5.6, que é o gabarito.
O Laravel novo também grava `bootstrap/cache/*.php` e `storage/framework/*` no formato dele, o que quebraria o 5.4.

## Como funciona

| Arquivo | Papel |
|---|---|
| `docker-compose.runtime-novo.yml` | um serviço `runtime_novo` (imagem `ecidade-login-php85`, a mesma do 8.5): monta o **mesmo código** e, por cima, três pastas de `$RN_DIR`; as duas chaves OAuth do `ecidade/storage` entram **somente leitura** por cima do `storage/` sobreposto |
| `docker/runtime-novo/prepara.sh` | cria `$RN_DIR`: **cópia** do `vendor/` (não hardlink: o Composer reescreve arquivos no lugar, como `vendor/composer/autoload_*.php`, e um hardlink alteraria o vendor do 5.6), `storage/` sem as chaves e sem o que o Laravel gera, `bootstrap-cache/` vazio, e um marcador `.runtime-novo` em cada pasta |
| `.gitignore` | `/runtime-novo/` (a pasta padrão de `$RN_DIR`) nunca é versionada |

| Dentro do container | Vem de |
|---|---|
| `/var/www/html` | `$RN_CODIGO` (padrão `./ecidade`) — o mesmo código dos outros runtimes |
| `/var/www/html/vendor` | `$RN_DIR/vendor` |
| `/var/www/html/bootstrap/cache` | `$RN_DIR/bootstrap-cache` |
| `/var/www/html/storage` | `$RN_DIR/storage` (inclui os modelos `.xlsx` versionados de `storage/financeiro`) |
| `/var/www/html/storage/oauth-{private,public}.key` | `$RN_CODIGO/storage/…`, **somente leitura** (sem cópia de segredo) |
| `/var/lib/php/sessions`, `/tmp` | volumes `$RN_VOL_SESSOES` / `$RN_VOL_TMP` (padrão: `ecidade_sessions` / `ecidade_tmp`, os mesmos do 8.5 oficial, para o login no 5.6 valer aqui) |
| configuração local (`.env`, `libs/db_conn.php`, `config/*.php`) | o próprio código montado (não versionados; nada copiado) |

Variáveis (todas com padrão): `RN_NOME` (`ecidade_runtime_novo`), `RN_PORTA` (`8087`), `RN_CODIGO` (`./ecidade`),
`RN_DIR` (`./runtime-novo`), `RN_VOL_SESSOES`, `RN_VOL_TMP`, `RN_PGOPTIONS` (vazio). Com
`RN_PGOPTIONS='-c default_transaction_read_only=on'` toda conexão do container ao banco fica somente leitura — o mesmo
mecanismo do `SOMENTE_LEITURA=1` do `sobe-ambiente.sh`. **Regras do cliente (13/11/2026, revistas no mesmo dia):** tela de
menu e login/token rodam em container **que grava** (`RN_PGOPTIONS` vazio), a tela de menu com o
um vigia do banco (script local que compara `pg_stat_user_tables` antes/depois) (só `db_logsacessa*`, `db_usuariosonline` e o token do login podem mudar);
relatório/documento roda em somente leitura, salvo quando passou pela triagem por leitura de código (aí em container que
grava, com o vigia em volta de cada um). Em somente leitura a tela de menu não chega ao conteúdo (para no primeiro
INSERT, medido pelo Rev2: ver critério 2). O 5.6, o 8.5 e o `docker-compose.yml` de referência não mudam.

## Subir e derrubar

Ambiente oficial (porta 8087, ao lado de 8080/8085/8090, sem mexer neles):

```bash
bash docker/runtime-novo/prepara.sh ecidade runtime-novo          # uma vez (copia ~247 MB)
docker compose -f docker-compose.runtime-novo.yml up -d
docker exec ecidade_runtime_novo sh -c 'chmod 1733 /var/lib/php/sessions'   # se o volume nascer sem permissão
docker compose -f docker-compose.runtime-novo.yml down             # nunca com --remove-orphans
```

Ambiente de um agente (como foi medido aqui; volumes próprios para não tocar nos do usuário):

```bash
# subir 5.6 e 8.5 de teste a partir desta árvore (script local da equipe)   # 5.6 :8110, 8.5 :8111 (gravam)
bash docker/runtime-novo/prepara.sh ecidade runtime-novo
docker volume create ecidade_back1_rn_sessoes; docker volume create ecidade_back1_rn_tmp
RN_NOME=ecidade_back1_rn RN_PORTA=8112 RN_VOL_SESSOES=ecidade_back1_rn_sessoes RN_VOL_TMP=ecidade_back1_rn_tmp \
docker compose -p ecidade_back1_rn -f docker-compose.runtime-novo.yml up -d                   # runtime novo :8112 (grava)
# relatorio sem triagem: SOMENTE_LEITURA=1 na frente do sobe-ambiente.sh e RN_PGOPTIONS='-c default_transaction_read_only=on'
docker exec ecidade_back1_rn sh -c 'chmod 1733 /var/lib/php/sessions; chmod 1777 /tmp'
# derrubar:
docker compose -p ecidade_back1_rn -f docker-compose.runtime-novo.yml down
docker volume rm ecidade_back1_rn_sessoes ecidade_back1_rn_tmp
# derrubar os dois containers de teste (script local da equipe)
```

Para trocar a versão depois (Laravel 13): `composer` roda **só** em `$RN_DIR` (por exemplo montando `$RN_DIR/vendor`
num container com o `composer.json` novo); o `ecidade/vendor` do 5.6 não é tocado.

## Prova (12/11/2026, ambiente de teste)

**Critério 1 — sobreposição só no runtime novo.** Marcadores `.runtime-novo` e `docker inspect`:

| | `vendor/.runtime-novo` | `storage/.runtime-novo` | `bootstrap/cache/.runtime-novo` | `bootstrap/cache/services.php` |
|---|---|---|---|---|
| `ecidade_back1_56` (5.6) | ausente | ausente | ausente | presente (o de sempre) |
| `ecidade_back1_85` (8.5 de hoje) | ausente | ausente | ausente | presente |
| `ecidade_back1_rn` (runtime novo) | **presente** | **presente** | **presente** | ausente até o 1º pedido a `/v4/` |

Depois de `GET /v4/oauth/token` no runtime novo (500, igual ao 8.5 de hoje: é o Laravel 5.4 no PHP 8), o Laravel gravou
`services.php` em `runtime-novo/bootstrap-cache/`; o `ecidade/bootstrap/cache/services.php` ficou com o mesmo sha256
(`e55e6c5aa16251a9…`) e `git status` sem mudança em `ecidade/`.

`docker inspect ecidade_back1_rn` (caminhos encurtados):

```
bind  …/ecidade                         -> /var/www/html                          rw
bind  …/runtime-novo/vendor             -> /var/www/html/vendor                   rw
bind  …/runtime-novo/bootstrap-cache    -> /var/www/html/bootstrap/cache          rw
bind  …/runtime-novo/storage            -> /var/www/html/storage                  rw
bind  …/ecidade/storage/oauth-private.key -> /var/www/html/storage/oauth-private.key  ro
bind  …/ecidade/storage/oauth-public.key  -> /var/www/html/storage/oauth-public.key   ro
volume ecidade_back1_rn_sessoes         -> /var/lib/php/sessions                  rw
volume ecidade_back1_rn_tmp             -> /tmp                                   rw
bind  …/docker/php85-apache/paridade-56.ini -> …/conf.d/zz-paridade-56.ini        ro
```

**Critério 3 — chaves OAuth e configuração local.** As duas chaves aparecem no runtime novo com o mesmo tamanho e o mesmo
conteúdo dos outros dois runtimes (comparado por sha256 dentro dos containers; nenhum hash de chave privada vai para este
registro), montadas `ro`. Nada foi copiado para arquivo versionado nem para `$RN_DIR` (lá ficam só arquivos vazios, pontos
de montagem). `.env`, `libs/db_conn.php` e `config/*.php` vêm do código montado.

**Critério 2 — bateria dirigida, 8.5 de hoje (:8111) × runtime novo (:8112), vendor novo = cópia do atual, os três
containers GRAVÁVEIS, com o vigia do banco (13/11/2026).** Um prefixo por área; as **telas de menu** do prefixo
(`db_itensmenu.funcao` ligado em `db_menu`, com o parâmetro que o menu passa, só as que existem no disco); a mesma sessão
restaurada antes de cada pedido nos dois lados; `vigia-banco.sh antes` → prefixo → `vigia-banco.sh depois`. Prova de que
gravam: `PGOPTIONS` vazio no ambiente do Apache dos três (`/proc/1/environ`). Relatórios (as telas `…002` que não estão no
menu) ficam fora: pela regra do cliente só rodam em somente leitura ou depois de triagem por leitura de código, que esta
tarefa não faz.

| Área | Prefixo | Telas de menu | Idênticas | Divergentes | Timeout | Parou no INSERT (leitura-apenas) | Vigia (tabelas que mudaram) |
|---|---|---|---|---|---|---|---|
| Tributário (Cemitério) | `cem` | 47 | 47 | 0 | 0 | 0 | OK: `db_usuariosonline` +109 |
| Educação (Biblioteca) | `bib` | 44 | 44 | 0 | 0 | 0 | OK: `db_usuariosonline` +92 |
| Recursos Humanos (eSocial) | `eso` | 39 | 39 | 0 | 0 | 0 | OK: `db_usuariosonline` +68 |
| Patrimonial (Ouvidoria) | `ouv` | 29 | 29 | 0 | 0 | 0 | OK: `db_usuariosonline` +54 |
| Financeiro (Custos) | `cus` | 16 | 16 | 0 | 0 | 0 | OK: `db_usuariosonline` +32 |
| Saúde (Vacinas) | `vac` | 34 | 34 | 0 | 0 | 0 | OK: `db_usuariosonline` +68 |
| Configuração (Sistema) | `sys` | 24 | 24 | 0 | 0 | 0 | OK: `db_usuariosonline` +48, `db_logsacessa_202611_1` +40 |
| **Total** | 7 | **233** | **233** | **0** | **0** | **0** | 7 × OK |

O menu do `cus` lista 17 itens; `cus01_planocusto000.php` não existe no disco (fica fora, igual nos dois). Saída do vigia,
como sai (um bloco por prefixo; os outros seis iguais em forma):

```
##### cem (47 telas de menu) 01:18:42
foto: 4230 tabelas
=== @menu_cem.txt: 47/47 identicas, 0 divergentes, 0 timeout; HTTP 200 no lado A: 47; com erro de leitura-apenas: 0 ===
mudaram: 1 tabela(s)
  configuracoes.db_usuariosonline 109
OK: so tabelas permitidas
vigia rc=0
...
##### sys (24 telas de menu) 01:19:54
foto: 4230 tabelas
=== @menu_sys.txt: 24/24 identicas, 0 divergentes, 0 timeout; HTTP 200 no lado A: 22; com erro de leitura-apenas: 0 ===
mudaram: 2 tabela(s)
  configuracoes.db_logsacessa_202611_1 40
  configuracoes.db_usuariosonline 48
OK: so tabelas permitidas
vigia rc=0
```

**O "idêntico" é de conteúdo, não de erro.** Respostas do 8.5 classificadas (`conteudo.py`, mesma sessão): **227 de 233**
trazem a tela (HTTP 200 com `<form>`/`<table>`/`<iframe>`); nenhuma com `leitura-apenas`, sessão inválida ou fatal do PHP.
As 6 restantes respondem igual nos **três** runtimes (5.6, 8.5 e runtime novo, conferidas à parte):

| Tela | Resposta (igual em 5.6, 8.5 e runtime novo) | Motivo |
|---|---|---|
| `vac2_aerograma001.php`, `vac3_aplicavacnia001.php` | HTTP 200, "Departamento não é um sala de vacinação!" | departamento 1 da sessão de teste não é sala de vacina (dado) |
| `vac4_vac_aplicaanula001.php` | idem + `alert('Variavel de sessão nao encontrada: DB_itemmenu_acessado')` | idem; a sessão de teste não passa pelo menu |
| `eso1_cadastroavaliacoes002.php` | HTTP 200, só `location.href='hab1_avaliacao002.php?iModulo=1'` | a tela é um redirecionamento |
| `sys4_criafontes.php`, `sys4_criafuncao.php` | HTTP 500, "Notificação do Sistema" | erro de sintaxe no próprio arquivo: `E_PARSE` no 5.6, `ParseError` no 8.5 (`extension/log/error.log`) — herdado |

Comparação contra o somente leitura (a rodada reprovada): com `RN_PGOPTIONS` ligado, o Rev2 mediu 119 de 131 telas
`cus`/`ouv` parando em `não é possível executar INSERT em uma transação de leitura-apenas`; aqui, **0 de 233**.

```bash
# sessao: login no 5.6 (grava so o log de acesso/usuario online), variaveis do modulo no arquivo de sessao
MD5=$(printf dbseller | md5sum | cut -d' ' -f1)
curl -s -c c -b c http://localhost:8110/login.php -o /dev/null
curl -s -c c -b c -X POST -d "DB_login=dbseller&DB_senha=$MD5&conteudoCaptcha=" http://localhost:8110/abrir.php -o /dev/null
SID=$(grep ECIDADEWINDOWMAIN c | awk '{print $7}')
docker exec -u www-data ecidade_back1_56 php -r 'ini_set("session.save_path","/var/lib/php/sessions"); session_id($argv[1]);
  session_start(); $_SESSION += ["DB_instit"=>1, "DB_coddepto"=>1, "DB_nomedepto"=>"CPD", "DB_modulo"=>1,
  "DB_nome_modulo"=>"Configuracao", "DB_Area"=>1, "DB_anousu"=>2026, "DB_datausu"=>mktime(0,0,0,11,13,2026),
  "DB_uol_hora"=>mktime(8,0,0,11,13,2026)]; session_write_close();' $SID
docker cp ecidade_back1_56:/var/lib/php/sessions/sess_$SID sess.bak
# telas de menu do prefixo (so as que existem no disco, com a grafia do disco e o parametro do menu)
for p in cem bib eso ouv cus vac sys; do
  docker exec ecidade_database psql -U postgres -d ecidade -tA -c "select distinct trim(i.funcao)
    from configuracoes.db_itensmenu i join configuracoes.db_menu m on m.id_item_filho=i.id_item
    where i.funcao ~* '^${p}[0-9]*_.*\.php' order by 1" > menu_$p.raw
  : > menu_$p.txt; while read f; do a=${f%%\?*}; r=$(ls ecidade | grep -ix -- "$a" | head -1); [ -n "$r" ] && echo "$r${f#$a}" >> menu_$p.txt; done < menu_$p.raw
done
# bateria: um vigia por prefixo, os dois lados gravaveis
V=<script local de vigia do banco>
for p in cem bib eso ouv cus vac sys; do
  bash $V antes foto_$p
  python3 cmp_rn.py ecidade $SID sess.bak @menu_$p.txt ecidade_back1_85:8111 ecidade_back1_rn:8112 </dev/null
  bash $V depois foto_$p
done
```

Instrumento: `cmp_rn.py` (anexo), a mesma lógica do `scratchpad/cmp.py` (restaura a sessão antes de cada pedido, mesmas
normalizações, confirma divergência com uma 2ª rodada, timeout não conta como igual, pula `iss4_siss002`) com os dois lados
configuráveis — o `cmp.py` fixa o lado A em `ecidade_php56:8080`, o ambiente oficial, que não podia ser usado. Aceita uma
lista de telas (`@arquivo`) e conta as respostas com `leitura-apenas`.

**Sessão de teste.** O login no 5.6 (`POST abrir.php`) cria uma sessão sem instituição e sem módulo; as telas exigem
`DB_modulo`, `DB_nome_modulo`, `DB_anousu`, `DB_instit` e `DB_uol_hora` (`libs/db_sessoes.php`). Quem as grava no uso normal
é `modulos.php`/`corpo.php`/`topo.php`, que também gravam em `db_usumod` — escrita fora da exceção do cliente. Por isso as
variáveis foram acrescentadas **direto no arquivo de sessão** (PHP CLI no container 5.6: instituição 1, departamento 1
`CPD`, módulo 1 `Configuração`, exercício 2026), e o mesmo arquivo foi copiado para os dois lados. O vigia em volta do login
acusou só `db_logsacessa_202611_0`, `db_usuariosonline` e `oauth_access_tokens`/`oauth_refresh_tokens` — o `abrir.php` não
emite token; esses dois são logins de outros agentes no mesmo intervalo (o vigia vê o banco inteiro).

**Rodadas que não contam.**
- 12/11, containers **somente leitura** (601/601 "idênticas", todas as telas de 7 prefixos): reprovada pelo Rev2 — em
  somente leitura a tela para no INSERT do registro de acesso, e a comparação era quase só do mesmo erro dos dois lados.
- 12/11, antes da regra de 13/11: rodada gravável sem vigia, interrompida em `cem` (116/116) e `bib` (98/98). Essas telas
  (todas as do prefixo, inclusive relatórios) podem ter gravado trilha de auditoria (`db_acount*`), como mostrou a T-023;
  pela decisão do cliente, linhas já gravadas ficam.
- 13/11, primeira rodada com vigia (`cem`, `bib`, `eso` iguais e vigia OK), interrompida: usava uma cópia local do
  `vigia-banco.sh` com `set +e`, porque o original saía `rc=1` sem saída quando a última tabela alterada era permitida
  (defeito avisado ao Lider e corrigido por ele na ferramenta). Refeita inteira com o original — é a da tabela acima.

## O que isto não prova

- Nada sobre o Laravel novo: o vendor é o atual. O comportamento com o vendor novo é da etapa seguinte.
- Telas com parâmetros, POST e chamadas `/v4/` por JavaScript (a bateria é GET, como a do projeto).

## Anexo: `cmp_rn.py`

```python
#!/usr/bin/env python3
"""T-022: compara telas entre dois runtimes 8.5 (o de hoje e o runtime novo), com a mesma sessao.
Mesma logica do scratchpad/cmp.py (restaura a sessao antes de CADA requisicao; normaliza ids aleatorios;
confirma divergencia com uma 2a rodada; timeout nao conta como igual), mas com os dois lados configuraveis.
uso: cmp_rn.py <pasta ecidade> <SID> <arquivo de sessao> <regex prefixo | @lista> CONTA:PORTA CONTB:PORTB"""
import re, subprocess, sys, os, shlex
ECI, SID, SESSFILE, PREF, A, B = sys.argv[1:7]
A = A.split(':'); B = B.split(':')
SESS = f"/var/lib/php/sessions/sess_{SID}"
def sh(c): return subprocess.run(["bash", "-c", c], capture_output=True)
for c, _ in (A, B):
    sh(f"docker cp {shlex.quote(SESSFILE)} {c}:/root/_sess.bak")
def restore(c):
    sh(f"docker exec -u root {c} sh -c 'cp /root/_sess.bak {SESS}; chown www-data:www-data {SESS}; chmod 600 {SESS}'")
NORM = [(re.compile(rb'sid=[0-9a-f]{8,}'), b'sid=X'), (re.compile(rb'arquivo=[A-Za-z0-9+/=]{12,}'), b'arquivo=X'),
        (re.compile(rb'wname[0-9]+'), b'wnameX'), (re.compile(rb'iframe[A-Za-z0-9]{4,}\.php'), b'iframeX.php'),
        (re.compile(rb'[0-9a-f]{32}'), b'MD5X'), (re.compile(rb'nomeArquivo[^\s"\']*'), b'nomeArquivoX'),
        (re.compile(rb'tmp/[A-Za-z0-9_]+\.pdf'), b'tmp/X.pdf'), (re.compile(rb'tmp\\?/[A-Za-z0-9_]+\.(?:csv|txt)'), b'tmp/X.arq'),
        (re.compile(rb'localhost:81[0-9][0-9]'), b'localhost:PORT'),
        (re.compile(rb'/(CreationDate|ModDate) ?\(D:[0-9]{14}[^)]*\)'), b'/DateX')]
def fetch(c, port, page):
    restore(c)
    r = sh(f"curl -s -m 60 -b 'ECIDADEWINDOWMAIN={SID}' -w '\\n@@%{{http_code}}@%{{time_total}}' "
           f"{shlex.quote(f'http://localhost:{port}/{page}')} | head -c 5000000")
    out = r.stdout; i = out.rfind(b'\n@@')
    code, _, t = (out[i+3:].decode(errors='replace') if i >= 0 else '???').partition('@')
    if t and float(t) >= 59.5: code = '000'
    corpo = out[:i] if i >= 0 else out
    for rx, rep in NORM: corpo = rx.sub(rep, corpo)
    return code, corpo
if PREF.startswith('@'):   # lista de telas (ex.: as telas de menu do prefixo, com o parametro do db_itensmenu)
    files = [l.strip() for l in open(PREF[1:]) if l.strip()]
else:
    files = sorted(f for f in os.listdir(ECI) if re.match(PREF, f, re.IGNORECASE) and f.endswith('.php'))
files = [f for f in files if f != 'iss4_siss002.php']   # contata servico externo (lista PULAR do cmp.py)
div, tout, ro, ok200 = [], [], [], 0
for f in files:
    ca, ba = fetch(A[0], A[1], f); cb, bb = fetch(B[0], B[1], f)
    if b'leitura-apenas' in ba or b'leitura-apenas' in bb: ro.append(f)   # parou no INSERT (container somente leitura)
    ok200 += ca == '200'
    if '000' in (ca, cb):
        tout.append(f); print(f"  TIMEOUT {f} A={ca} B={cb}", flush=True); continue
    if not (ca == cb and ba == bb):
        ca, ba = fetch(A[0], A[1], f); cb, bb = fetch(B[0], B[1], f)
    if not (ca == cb and ba == bb):
        div.append(f); print(f"  DIVERGE {f} A={ca}/{len(ba)}B B={cb}/{len(bb)}B", flush=True)
print(f"=== {PREF}: {len(files)-len(div)-len(tout)}/{len(files)} identicas, {len(div)} divergentes, {len(tout)} timeout; HTTP 200 no lado A: {ok200}; com erro de leitura-apenas: {len(ro)} ===", flush=True)
```
