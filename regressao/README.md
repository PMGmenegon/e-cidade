# Regressão da migração (PHP 5.6 → 8.5 e Laravel 5.4 → 12)

Baterias que dizem, com evidência, se o e-Cidade migrado **se comporta como o de referência**. Tudo roda
da raiz do repositório, dentro do WSL/Linux, contra a pilha Docker descrita no `README.md` da raiz.

| Bateria | Pergunta que responde | Como compara |
|---|---|---|
| **PHP** (`regressao/php`) | PHP 8.5 (:8085) responde como PHP 5.6 (:8080)? | roda a mesma coisa nos dois runtimes sobre o mesmo banco: lint, classes, telas (GET), POSTs reais, relatórios (PDF/CSV/HTML por conteúdo), hashes e cobertura |
| **Laravel** (`regressao/laravel`) | o Laravel novo responde como o 5.4? | *golden master*: grava as respostas do 5.4 em `regressao/baseline/laravel/` e compara o alvo novo contra elas (rotas `/v4`, `rest/v1`, Silex, token Passport, escritas com SQL de negócio) |
| **Fluxos de navegador** (`regressao/completa/fluxos.py`) | o usuário, no navegador, vê o mesmo? | Playwright pelo proxy `:8090`: login → módulo → telas → inclusão → relatório → sair; golden master em `regressao/baseline/fluxos/` |
| **Completa** (`regressao/completa/orquestra.py`) | tudo junto, e antes × depois | roda as três, agrega num relatório só e compara duas rodadas completas |

## 1. Pré-requisitos

- Docker com Compose v2, WSL Ubuntu (ou Linux), e a **pasta do repositório chamada `e-cidade`** (a rede do Compose
  usa esse nome). Passos 1–8 do `README.md` da raiz (volumes `ecidade_sessions`/`ecidade_tmp`, PHP 5.6 + banco,
  PHP 8.5, proxy). Containers esperados: `ecidade_php56` (:8080), `ecidade_php85` (:8085), `ecidade_proxy` (:8090),
  `ecidade_database`.
- Python 3.12 e o venv do projeto (não versionado):

  ```bash
  python3 -m venv regressao/.venv
  regressao/.venv/bin/pip install -r regressao/requirements.txt
  regressao/.venv/bin/python -m playwright install chromium          # ~700 MB em ~/.cache/ms-playwright
  wsl -u root -- /caminho/e-cidade/regressao/.venv/bin/python -m playwright install-deps chromium   # bibliotecas do sistema (apt), se faltarem
  ```

- **Login web funcionando** (o `README.md` da raiz tem lacunas; ele não é editado por este plano, ver `docs/`). Três
  arquivos **ignorados pelo git** precisam existir, senão o login dá 404/500:

  ```bash
  cp ecidade/config/require_extensions.xml.dist ecidade/config/require_extensions.xml
  cp ecidade/libs/db_acessa.php.dist            ecidade/libs/db_acessa.php
  mkdir -p ecidade/extension/log && chmod 777 ecidade/extension/log
  touch ecidade/extension/log/error.log ecidade/extension/log/application.log && chmod 666 ecidade/extension/log/*.log
  ```

  E a senha do usuário `dbseller` no banco precisa ser **`sha1(md5("dbseller"))`**, que é o que o login web confere. O
  `update` do passo 5 do `README.md` da raiz grava `sha1("dbseller")` (`699f20e7…`) e o login web recusa. Use:

  ```bash
  H=$(printf dbseller | md5sum | cut -d' ' -f1 | tr -d '\n' | sha1sum | cut -d' ' -f1)
  docker exec ecidade_database psql -U postgres -d ecidade -c "update configuracoes.db_usuarios set senha='$H' where id_usuario=1"
  ```

  (Só então gere o dump da seção 2: ele carrega a senha correta.)

- O proxy precisa estar de pé: `curl -sI http://localhost:8090/login.php | grep -i x-ecidade`.

## 2. A baseline do banco (o dump)

Todas as baterias começam **restaurando** `regressao/baseline/baseline.dump` (sha256 em
`baseline.dump.sha256`, conferido a cada rodada). Isso dá o mesmo estado inicial sempre e apaga qualquer resíduo
de rodada anterior (um POST abortado deixa lixo no banco). Para (re)criar, com o ambiente recém-instalado e **antes de
qualquer teste ao vivo** (um simples GET já grava auditoria/sessão no banco):

```bash
regressao/.venv/bin/python -c "from regressao.nucleo.banco import ARQ_DUMP, gera_dump; print(gera_dump(ARQ_DUMP))"
```

Trocar o dump invalida as baselines do Laravel e dos fluxos (elas guardam o sha256 e as baterias recusam rodar
com outro): regrave-as (seção 6). Restaurar leva **≈ 3–5 min** (`DROP DATABASE` + `pg_restore --create`).

**Guarde uma cópia do `baseline.dump` fora do git** (disco/backup do time). `pg_dump -Fc` **não reproduz o mesmo
sha256** ao ser rodado de novo (metadados e ordem mudam): se o arquivo se perder, um dump novo é outra baseline e
obriga a regravar Laravel e fluxos.

**Restaurar num container de banco NOVO** exige o que o dump não leva: as *roles* são globais ao cluster. As roles do
ambiente atual (`\du`) são `dbseller` (sem atributos), `ecidade` e `plugin` (superusuários) e `postgres`; crie-as
(com as senhas do seu `.env`/`libs/db_conn.php`, que **não** estão aqui) antes do `pg_restore`. O `search_path` real é
configurado **por banco** (`ALTER DATABASE ecidade SET search_path = "$user", public, teleatend, acordos, …` com ~70
schemas) e vem no dump porque ele é gerado com `--create`; não há `ALTER ROLE … SET`. Confira com
`psql -c '\du'` e `select * from pg_db_role_setting`.

## 3. Rodar

Sempre da raiz do repositório, com `regressao/.venv/bin/python -m …`. Cada comando escreve uma pasta de saída com
`resultado.json`, `resumo.md` e `diffs/`.

```bash
# PHP 5.6 x 8.5. Rodada completa de telas leva HORAS (~0,83 s/tela; 12 mil telas ≈ 3 h): para fumaça use --area/--prefixo
python -m regressao.php.bateria --saida /tmp/php --prefixo '^arr1_(procjurtipo|grupotaxa)001\.php$'
python -m regressao.php.bateria --saida /tmp/php --area tributario            # uma área (≈ 5,5 mil telas)
# opções: --sem-normalizar, --incluir-nao-verificados, --sem-restaurar (só desenvolvimento: rodada NÃO comparável)

# Laravel (a baseline é gravada no 5.4 e comparada com o alvo novo)
python -m regressao.laravel.bateria gravar   --saida /tmp/lar-g                # no :8080 (5.4); recusa sobrescrever (seção 6)
python -m regressao.laravel.bateria gravar   --saida /tmp/lar-g --apenas-novos --confirmo-sobrescrever   # só casos novos (11b)
python -m regressao.laravel.bateria comparar --saida /tmp/lar                  # alvo = REGRESSAO_LARAVEL_NOVO_URL (padrão :8087)
python -m regressao.laravel.bateria comparar --saida /tmp/lar --alvo http://localhost:8080   # prova de estabilidade (5.4 contra ele mesmo)

# Fluxos de navegador
python -m regressao.completa.fluxos gravar   --saida /tmp/fl-g
python -m regressao.completa.fluxos comparar --saida /tmp/fl [--fluxo navegacao --fluxo incluir-registro --fluxo emitir-relatorio]

# Completa (PHP -> Laravel -> fluxos, cada uma com a própria restauração)
python -m regressao.completa.orquestra --saida /tmp/completa [--area A ...] [--prefixo RX ...] [--sem-fluxos] [--alvo-laravel URL]
python -m regressao.completa.orquestra --comparar /tmp/antes /tmp/depois
```

URLs dos alvos vêm de `REGRESSAO_REF_URL` (:8080), `REGRESSAO_PHP_NOVO_URL` (:8085), `REGRESSAO_LARAVEL_NOVO_URL`
(:8087) e `REGRESSAO_PROXY_URL` (:8090).

### Fluxos de navegador (o que cobrem)

`navegacao` (login → "atualizar cadastro"/Cancelar → instituição → área → módulo Arrecadação → tela de cadastro
`arr1_grupotaxa001` → tela de relatório `cai2_relcaixa_001` → sair), `incluir-registro` (preenche `arr1_grupotaxa001`
pela UI, inclui, confere o alerta e o **efeito no banco**: `hash_tabelas` de `arrecadacao.grupotaxa` e contagem de
linhas) e `emitir-relatorio` (clica *Imprimir* em `cai2_relcaixa_001?db_opcao=tabrecjm`, confere status, tipo e texto
do PDF). Por passo: DOM normalizado do frame `corpo`, status das requisições principais, alertas, valores digitados e
banco. O cabeçalho **`X-Ecidade-Runtime` é registrado e mostrado como INFO, nunca é falha** (ele vai mudar na
migração: telas hoje em 5.6 passarão a 8.5). Erros de console e requisições com falha só viram veredito se
**diferirem da baseline**; `net::ERR_ABORTED` (cancelamento por navegação/download) é ignorado. Limite de 120 s por
fluxo; passo que estoura vira falha com mensagem. Senha, SID e tokens nunca vão para a baseline (a gravação é barrada
se aparecerem). Fluxos por área crítica (rodada pós-entrega A): **`financeiro`** (área Financeiro, módulo Orçamento:
inclui uma função orçamentária em `orc1_orcfuncao001`, efeito em `orcamento.orcfuncao`), **`tributario`** (módulo
ISSQN: abre `iss2_tipcalc001` e emite o PDF `iss2_tipcalc002`) e **`cadastros`** (módulo Protocolo: CPF → formulário
→ inclui um CGM pessoa física em `prot1_cadcgm001`, efeito em `cgm`, `cgmfisico`, `db_cgmcpf`, `cgmendereco`,
`personacgm`). **Não cobertos**: telas fora desses módulos, upload, impressão fora de `cai2_relcaixa`/`iss2_tipcalc`,
alteração/exclusão (só inclusão), navegadores além do Chromium headless, o fluxo "com o login recusado". Achado dos
fluxos: o PNG `/228358.png` do formulário de Orçamento responde HTTP 500 (visível em `falhas`).

## 4. Ler os resultados

> **ESCOPO DA BATERIA PHP (leia antes de confiar no verde).** `./ecidade` é montado nos **dois** runtimes
> (`docker-compose.yml` e `docker-compose.php85.yml`): o mesmo código roda em 5.6 e em 8.5. A bateria PHP prova
> **paridade 5.6 × 8.5 sobre o código ATUAL**; ela **não detecta** uma regressão introduzida num código comum aos dois
> (um bug que apareça igual nos dois lados dá IDENTICO). Só o **Laravel** e os **fluxos de navegador** são *golden master*
> contra uma gravação anterior. O `compara_hashes` das telas **não** entra no `--comparar`. Esse aviso fixo também sai no
> `resumo.md` da completa.

| Veredito | Significa |
|---|---|
| `IDENTICO` | os dois lados responderam igual (depois de normalizar o que é volátil) |
| `DIVERGE` | respostas diferentes: **achado real** da migração (diff em `diffs/`). Se já existia antes, entra em `regressao/conhecidas.tsv` **com prova** |
| `INCONCLUSIVO` | o caso **não foi exercitado** (ex.: 5xx nos dois lados, sem escrita capturada, payload sem linha-semente). **NÃO é aprovação**: é lacuna de cobertura e vem listado com o motivo |
| `ERRO_AMBIENTE` | a rodada não pôde ser feita (container fora, banco/baseline diferente, alvo inexistente, sessão inválida). Nada se conclui |

Código de saída (de cada bateria e da completa): **2** se houver `ERRO_AMBIENTE`; **1** se houver `DIVERGE` que não seja
conhecida; **0** caso contrário. Na completa vale o **pior** das três. Um 0 com INCONCLUSIVO não é "tudo certo": leia a
seção *INCONCLUSIVO por motivo* e a *Cobertura* do `resumo.md` (catálogos PHP verificados × não, rotas Laravel
cobertas × não, passos de fluxo). O resumo também mostra git, versões, sha256 da baseline e tempos por fase;
`meta.comparavel=false` marca rodadas que **não** servem para antes×depois (ex.: `--sem-restaurar`).

Detalhes de leitura: `telas_com_dados` é um **limite superior** (a heurística `tem_dados` conta qualquer `<td` fora do
cabeçalho, e o e-Cidade usa `<td>` em layout). Tela cuja resposta é uma **página de erro** (Notificação do Sistema/Erro
interno, Fatal/Parse error) igual nos dois lados vira INCONCLUSIVO, não IDENTICO. O **lint** só cobre as telas
selecionadas por `--area/--prefixo`, **não** classes, `libs/` nem models. `--sem-normalizar` só existe na bateria PHP e
**não chega ao `cmp.py`** (que normaliza por conta própria).

`git_sujo` olha o repositório inteiro (costuma ser `true` por causa do ambiente Docker); **`git_sujo_regressao`** olha só
`regressao/`: se for `true`, o código da bateria que rodou não é o do commit registrado.

## 5. Adicionar casos

- **POST real (PHP)**: uma linha em `regressao/php/catalogo_posts.tsv`: `tela<TAB>tabelas (filhas antes da mãe, separadas por
  vírgula)<TAB>campos (querystring)<TAB>area<TAB>verificado|nao-verificado`. Use os campos reais do formulário
  (nomes dos `input`). Rode a linha ao vivo: `verificado` quer dizer *"o caso é válido e o veredito é confiável"* (a
  referência 5.6 respondeu com conteúdo real), **qualquer que seja o veredito**: um `verificado` que dá `DIVERGE` é
  achado e deixa a rodada vermelha. `nao-verificado` é pulado (a menos de `--incluir-nao-verificados`).
  Cuidado com as tabelas filhas: um POST que aborta numa FK deixa resíduo (o próximo restore limpa).
- **Relatório (PHP)**: `regressao/php/catalogo_relatorios.tsv` (`tela<TAB>query<TAB>pdf|xls|html|doc<TAB>area<TAB>status`).
  Mesma semântica de `verificado`. No e-Cidade, "xls" é CSV via `db_download.php`.
- **Telas / lint / classes** não precisam de cadastro: vêm do que existe em `ecidade/` (`--area`/`--prefixo` escolhem).
- **Laravel**: o gerador cria um caso por rota (GET autenticado; sonda `{}` nas demais) a partir do inventário do
  `route:list`: `python -m regressao.laravel.gerador` (regera `casos/rotas_*.yml`); a cobertura sai de
  `python -m regressao.laravel.cobertura`. Casos escritos à mão ficam em `casos/auth.yml` e `casos/escrita.yml`.
  `casos/_ajustes.yml` guarda o que a regeneração preserva: `volateis` (campos JSON mascarados), `instaveis`,
  `perigosas` (sondas que **escreveram** ao vivo: deixam de ser geradas) e `permitidas` (allowlist de
  DELETE/PUT/PATCH, vazia por padrão). `espera_status: N` declara que uma rejeição é esperada (ex.: 500 de rota
  protegida no 5.4): o caso vira IDENTICO só se a **referência** confirmar esse status na gravação.
  Depois de mudar casos, **regrave** a baseline (abaixo).
- **Fluxo de navegador**: uma função em `regressao/completa/fluxos.py` (lista de passos `(nome, função, tira_snapshot)`)
  registrada em `FLUXOS`; rode `gravar --fluxo <id> --confirmo-sobrescrever`.

## 6. Proteção da baseline

As baselines (`regressao/baseline/laravel/`, `regressao/baseline/fluxos/`, o dump) são a **referência pré-migração**.
Regravá-las com o sistema já migrado destrói a comparação. Por isso:

- `gravar` **recusa** (saída 2) sobrescrever baseline existente, e gravar contra um alvo que não seja o 5.4/proxy de
  referência, sem `--confirmo-sobrescrever` (e `--alvo` explícito para outro alvo). Só use a flag para regravar
  **no sistema ainda não migrado** depois de mudar casos.
- `gravar` não produz "casos IDENTICO": nada foi comparado; o resumo diz `GRAVACAO ... nao e comparacao`.
- `comparar` recusa baseline gravada com outro sha256 de dump.
- O repositório no GitHub (`Segunddo/e-cidade`) é **PÚBLICO** e as baselines contêm **dados do banco de desenvolvimento**
  (nome e telefones da instituição, usuários, textos de telas etc.; o campo `senha` de `/v4/api/user` é mascarado).
  Não publique a branch `regressao`
  sem decidir isso. Senhas, SIDs e tokens nunca são gravados.

## 7. Migração: antes × depois

> Lembrete de escopo (§4): como `./ecidade` é compartilhado pelos dois runtimes, a rodada PHP "antes" **não** é uma
> fotografia do comportamento pré-migração; só Laravel e fluxos guardam referência gravada. Para PHP, o "antes × depois"
> mede a paridade 5.6 × 8.5 em cada momento.

**ANTES de migrar** (no sistema de referência, ambiente recém-subido, nada rodado ao vivo antes do dump):

1. Gerar o dump (seção 2) e commitar `baseline.dump.sha256`.
2. `python -m regressao.laravel.bateria gravar --saida /tmp/lar-g` (Laravel 5.4 em :8080) e
   `python -m regressao.completa.fluxos gravar --saida /tmp/fl-g`; commitar as baselines.
3. Rodada completa de referência, arquivada: `python -m regressao.completa.orquestra --saida ~/regressao/antes
   --alvo-laravel http://localhost:8080` (o Laravel 5.4 contra ele mesmo: todos IDENTICO/INCONCLUSIVO).

**DEPOIS de migrar** (Laravel 12 de pé em `REGRESSAO_LARAVEL_NOVO_URL`):

4. `python -m regressao.completa.orquestra --saida ~/regressao/depois` (e `--area/--prefixo` se quiser reduzir o PHP).
5. `python -m regressao.completa.orquestra --comparar ~/regressao/antes ~/regressao/depois` → `comparacao.md/.json`:
   **regressões** (IDENTICO/INCONCLUSIVO → DIVERGE/ERRO_AMBIENTE, e a *perda de verificação* IDENTICO → INCONCLUSIVO),
   **correções** (DIVERGE/ERRO → IDENTICO), casos **adicionados** e **removidos**, e diferenças de meta (commit, sha da
   baseline, versões). A saída é o **pior** entre a comparação e o estado de DEPOIS: 1 se houver regressão ou caso
   removido **ou** DEPOIS tiver `DIVERGE` não conhecida (mesmo igual a ANTES); 2 se alguma rodada for inválida ou
   `comparavel=false` **ou** DEPOIS tiver `ERRO_AMBIENTE`. `AVISOS` no `comparacao.md/.json` dizem isso. Transições
   `DIVERGE/ERRO_AMBIENTE → INCONCLUSIVO` aparecem em **Lacunas** (não são correção: o caso deixou de ser verificado).

## 8. Custos, tempos e memória

- **Restauração ≈ 3,5–4,5 min** cada. A completa restaura **3 vezes** (PHP, Laravel, fluxos): ≈ 12 min só de restore.
- PHP: ~0,83 s/tela, POSTs 4–17 s cada, relatórios ~1 s; uma rodada de fumaça (`--prefixo`) leva ~5–6 min no total. Áreas
  inteiras levam **horas**. Laravel: ≈ 8 min de casos (381 casos) + restore. Fluxos: ≈ 1 min + restore.
- A memória do host é apertada: antes de rodadas longas, solte o cache de arquivos do WSL
  (`wsl -d Ubuntu-24.04 -u root -- sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'`). Um `.wslconfig` com `memory=6GB` e
  `autoMemoryReclaim=gradual` ajuda; fica a critério do usuário. Os fluxos usam um Chromium só, fechado ao fim.
- **Estado do banco**: cada bateria assume banco recém-restaurado e o **deixa sujo**; os fluxos (que rodam por último na
  completa) deixam um registro de teste em `grupotaxa`. Nada precisa ser limpo à mão: a próxima rodada restaura.

## 9. Limitações conhecidas

- **A bateria PHP só prova paridade 5.6 × 8.5 sobre o código atual** (código compartilhado, ver §4); não detecta regressão
  de código comum aos dois runtimes.
- **Baselines Laravel guardam `file`/`line`/stacktrace absolutos** (115 de 381 registros trazem caminhos do servidor 5.4,
  p.ex. `/var/www/html/...` e números de linha). **Decisão (implementada em `laravel/mascara.py::normaliza_erro`,
  aplicada só na comparação; a baseline bruta não foi regravada) — **escopo estreito**: só em **respostas de erro**
  (status >= 400 ou objeto com `exception`), só no `json` (e no `texto` de respostas 5xx); nunca em `sql_negocio`,
  cabeçalhos, tipos, hashes de tabela nem em respostas de sucesso. Em objetos com cara de erro (têm `exception`/`trace`/
  `stacktrace`, ou o envelope do app `error: true`) os campos `file`, `line`, `trace`, `stacktrace`/`stack_trace` viram
  `<X>`; um objeto de negócio `{message, file, line}` **não** é tocado. Caminhos absolutos só com **raiz conhecida do
  servidor** (`/var/www/html`, `/var/www`, `/app`, `/srv/<x>`) seguida de `vendor/`, `app/`, `bootstrap/`, `storage/`,
  `ecidade/`, `libs/`… viram `<caminho>` e `on line N` vira `on line <N>`; URLs como `/storage/a.pdf` ou `/public/x.png`
  continuam comparadas. A classe da exceção (`exception`) e a `message` **continuam comparadas**: mudar a exceção é
  DIVERGE real. Consequência: um erro que só muda de arquivo/linha entre 5.4 e 12 não aparece como divergência.

- **Laboratório Laravel 12 inexistente**: não há compose para o `:8087`. `comparar` no alvo padrão devolve **um**
  `ERRO_AMBIENTE` (`laravel:boot`, saída 2, sem restaurar o banco) e a completa segue com as outras frentes. Só a
  prova de estabilidade (5.4 contra ele mesmo) foi exercitada ao vivo.
- **Integrações (11b), o que existe e o que não existe** (`laravel/integracao.py`, `laravel/stubs/`,
  `laravel/casos/integracao.yml`):
  - **Arquivo gerado por conteúdo**: 5 casos (`arquivo-vacinacao-pdf-*` x3, `arquivo-siconfi-csv`,
    `arquivo-pcasp-csv`): a rota devolve JSON com o caminho do arquivo (`data.path`/`data.csv`), a bateria o baixa e
    compara o **texto extraído** (pypdf/CSV/openpyxl/xlrd), nunca os bytes; o nome com timestamp é mascarado. Das 77
    rotas que parecem gerar arquivo, só estas devolveram arquivo com corpo mínimo conhecido; as demais pedem dados de
    domínio (planejamento existente, instituição na sessão legada `DB_instit`, filtros) que o banco de dev não tem
    (`Undefined index: DB_instit`/`planejamento_id`...). Nenhum caso XLSX real: o app serve CSV.
  - **Console**: 3 casos (`console-list` só pelos nomes dos comandos, `console-env`, `console-migrate-status`),
    executados com `docker exec ... php artisan`. **O container acompanha o alvo**: na referência (5.4) é sempre
    `ecidade_php56`; em qualquer outro alvo `REGRESSAO_LARAVEL_CONSOLE_CONTAINER` é **obrigatória** (sem ela o caso vira
    `ERRO_AMBIENTE`, para nunca comparar o 5.4 com ele mesmo e dar falso IDENTICO). Falha do `docker exec` (125/126/127,
    "No such container") também é `ERRO_AMBIENTE`; só `list`, `env` e `migrate:status` passam pela allowlist.
    `console-migrate-status` compara o **conjunto completo** de migrations (contagem + sha256 + lista, sem truncar).
    Comandos de domínio (`agendamento:inativarvinculoprofessor`,
    `matriculaonline:alteracaoinscricao`, `payroll:*`) **escrevem** no banco e não foram incluídos.
  - **SMTP de teste e stub PIX**: servidores locais (`SmtpStub`, `PixStub`), sobem e param por `com_stubs()`; o
    SMTP captura a mensagem e `compara_email` normaliza `Date`, `Message-ID` e fronteiras MIME (testado com
    `smtplib`). **Mas nenhum caso os exercita**, por inviabilidade comprovada: (a) nenhum código de Laravel/Silex
    (`app/`, `src/`) usa `Mail::`, PHPMailer ou Swift (o `.env` aponta `smtp.mailtrap.io:2525`; o envio de e-mail vive
    no PHP legado e nenhuma rota `/v4` ou `/api/v1` o dispara); (b) as URLs do Banco do Brasil estão fixas em
    constantes HTTPS (`BancoDoBrasil::BASE_URL`/`BASE_AUTH_URL`), `POST pix/gerar` exige sessão legada + recibo com
    código de barras + CGM com CPF/CNPJ válido, e redirecionar o app ao stub exigiria DNS/TLS dentro do container,
    o que não é permitido alterar aqui. Quando o Laravel 12 tiver um ponto de configuração para a URL do PSP, o
    stub já está pronto para receber o caso.
  - **Adicionar sem regravar**: `python -m regressao.laravel.bateria gravar --saida DIR --apenas-novos
    --confirmo-sobrescrever` roda só os casos **ausentes do `_meta`** (restaurando o dump) e acrescenta à baseline; os
    registros existentes não são tocados. Recusa: alvo que não seja a referência 5.4, dump diferente, registros
    **perdidos** (id no `_meta` sem arquivo) e arquivo órfão. Para refazer um registro: `python -m regressao.laravel.caso
    remove <id>` (apaga o arquivo e tira o id do `_meta`) e depois `--apenas-novos`.
- Laravel: cobre 366 de 568 rotas; ficam de fora rotas com parâmetro de caminho, perigosas por nome e 4 sondas que
  gravaram. `rest/v1` só com rotas parametrizadas (nenhum caso gerado); `PATCH`/`HEAD` colapsam em `PUT`/`GET`. Os
  casos de rota protegida dão HTTP 500 (não 401) no 5.4 e usam `espera_status`; ~100 casos são `INCONCLUSIVO`
  (5xx nos dois lados). `dbseller` com senha errada recebe token no 5.4 (achado do app legado, gravado como referência).
- PHP: o catálogo de POSTs (52 linhas, 50 `verificado`) **não tem CGM como linha rodável**: o `DELETE` em `cgm` falha fora
  do app (trigger `tg_atualiza_issbaseintegracaoexterna`: EXECUTE com argumento nulo), então o restore por diferença do
  `escrita_post.py` aborta. O CGM foi verificado à mão com 2 restaurações completas do dump: os 3 INSERTs de negócio
  (`cgm`, `cgmfisico`, `db_cgmcpf`) são idênticos em 5.6 e 8.5, exceto `z01_hora` (relógio). Além dele, só `*001`
  (inclusão) em Orçamento/Arrecadação; as linhas novas de Caixa/Água (18) são todas IDENTICO. Alguns cadastros não
  restauram a `sequence` (ex.: `cai1_bancoshistmovcategoria001` dá DIVERGE falso por id 3 × 4) e ficaram de fora.
  `nao-verificado`: 2 POSTs e 2 relatórios (`func_cgm.php`, que devolve só a página de pesquisa, e o CSV
  `balrec.csv`, só com cabeçalho). `cem2_renovacoes` é `verificado` com evidência fraca (modelo de PDF em branco). Os
  relatórios `db_download.php` (CSV) provam só o *serving* do arquivo.
- **11 relatórios PDF dão HTTP 500 no PHP 8.5** e funcionam no 5.6 (`mat2_cadunidade002`, `prot2_cadcgm002`,
  `con2_relinstituicoes002`, `con2_conhist002`, `con2_conhistdoc002`, `con2_balancrece002` e, na rodada pós-entrega A,
  `con2_balancdespele002`, `con2_balancrecu002`, `con2_contasrecdesp002`, `con2_relrec002`, `cad2_loteam002`): são regressões **reais**
  da migração e mantêm a bateria PHP vermelha (saída 1) até serem corrigidas ou aceitas em `conhecidas.tsv`.
- O PHP não cobre ainda a rodada de **área inteira** quanto à memória (corpos ficam em memória por prefixo): prefixos
  enormes (`con`, `edu`) usam mais RAM.
- Fluxos: 6 fluxos (Arrecadação, Orçamento, ISSQN, Protocolo/CGM), só inclusão e emissão; DOM compara estrutura (scripts inline e estilos são removidos),
  então erro de JS que não mude o DOM só aparece pelo console; PDF vem de um GET idêntico com a sessão do navegador
  (o Chromium headless trata o PDF como download). Banco de dev pode mudar o conteúdo de telas como "últimos acessos
  ao módulo": por isso os fluxos restauram o dump antes de cada rodada.
