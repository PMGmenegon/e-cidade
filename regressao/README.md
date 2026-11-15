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
com outro): regrave-as (seção 4). Restaurar leva **≈ 3–5 min** (`DROP DATABASE` + `pg_restore --create`).

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
se aparecerem). **Não cobertos**: telas fora do módulo Arrecadação, escrita em tabelas além de `grupotaxa`, upload,
impressão/PDF fora do `cai2_relcaixa`, navegadores além do Chromium headless, o fluxo "com o login recusado".

## 4. Ler os resultados

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

- **Laboratório Laravel 12 inexistente**: não há compose para o `:8087`. `comparar` no alvo padrão devolve **um**
  `ERRO_AMBIENTE` (`laravel:boot`, saída 2, sem restaurar o banco) e a completa segue com as outras frentes. Só a
  prova de estabilidade (5.4 contra ele mesmo) foi exercitada ao vivo.
- **Integrações (11b) não implementadas**: stub do PIX, SMTP de teste, PDF/XLS do Laravel por conteúdo e comandos de
  console/artisan **não** têm casos.
- Laravel: cobre 366 de 568 rotas; ficam de fora rotas com parâmetro de caminho, perigosas por nome e 4 sondas que
  gravaram. `rest/v1` só com rotas parametrizadas (nenhum caso gerado); `PATCH`/`HEAD` colapsam em `PUT`/`GET`. Os
  casos de rota protegida dão HTTP 500 (não 401) no 5.4 e usam `espera_status`; ~100 casos são `INCONCLUSIVO`
  (5xx nos dois lados). `dbseller` com senha errada recebe token no 5.4 (achado do app legado, gravado como referência).
- PHP: o catálogo de POSTs não tem **CGM** (`prot1_cadcgm001`: tem muitas tabelas filhas por FK e deixa resíduo), nem
  Orçamento/Arrecadação além das telas `*001`; 2 linhas de POST e 3 de relatório estão `nao-verificado`. Os relatórios `db_download.php`
  (CSV) provam só o *serving* do arquivo.
- **6 relatórios PDF dão HTTP 500 no PHP 8.5** e funcionam no 5.6 (`mat2_cadunidade002`, `prot2_cadcgm002`,
  `con2_relinstituicoes002`, `con2_conhist002`, `con2_conhistdoc002`, `con2_balancrece002`): são regressões **reais**
  da migração e mantêm a bateria PHP vermelha (saída 1) até serem corrigidas ou aceitas em `conhecidas.tsv`.
- O PHP não cobre ainda a rodada de **área inteira** quanto à memória (corpos ficam em memória por prefixo): prefixos
  enormes (`con`, `edu`) usam mais RAM.
- Fluxos: só o módulo Arrecadação e uma tabela de efeito; DOM compara estrutura (scripts inline e estilos são removidos),
  então erro de JS que não mude o DOM só aparece pelo console; PDF vem de um GET idêntico com a sessão do navegador
  (o Chromium headless trata o PDF como download). Banco de dev pode mudar o conteúdo de telas como "últimos acessos
  ao módulo": por isso os fluxos restauram o dump antes de cada rodada.
