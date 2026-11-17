# Bateria com JavaScript das telas que chamam `/v4/` (T-030, parte A)

A bateria por `curl` (`cmp.py`) não executa JavaScript e por isso não exercita as telas legadas que chamam a API `/v4/` pelo navegador
(`docs/registro/laravel.md`, ponto 4 dos "Pontos de contato"). Esta ferramenta abre as telas num Chrome headless, com sessão e token reais,
e grava as chamadas `/v4/` que cada tela faz sozinha. A segunda metade da lista (parte B) usa a mesma ferramenta, com outro arquivo de casos.

Código: `ecidade/tests/sistema/telas-js/` (`lista.sh`, `bateria.mjs`, `rodar.sh`, `casos.tsv`, `base/`).

## A lista (critério 1)

```bash
bash ecidade/tests/sistema/telas-js/lista.sh      # 30 arquivos, ordem LC_ALL=C
```

É o `grep` do ponto 4 do `laravel.md` com ordem fixa: **30 arquivos**, a mesma contagem do registro (22 telas da raiz, `forms/db_frmarretipo002`,
`forms/db_frmdb_bancos`, 4 `scripts/`, `templates/template_login_e-cidade.php`, o middleware `api/V1/.../MenuAcessadoSessionMiddleware.php`).
**Primeira metade = os 15 primeiros** (até `pro3_consultaprocesso002.php`); a segunda metade é a parte B. Dos 15, `cai1_pix002.php` (Pix) fica para a
parte B. Restam **14 casos**, em `casos.tsv`.

## Como rodar

Dois containers sobre a mesma árvore, PHP 5.6 (porta-base) e PHP 8.5 (porta-base + 1), subidos SEM `SOMENTE_LEITURA`: tela de menu grava o log de acesso ao abrir, então roda em container que grava, com o vigia do banco em volta:

```bash
cd <worktree>   # containers ecidade_<agente>_56 e ecidade_<agente>_85 no ar
D=/tmp/telas-js; mkdir -p $D
bash ecidade/tests/sistema/telas-js/rodar.sh <agente> <porta-base> 56 $D/56-1.json   # vigia antes -> bateria -> vigia depois
bash ecidade/tests/sistema/telas-js/rodar.sh <agente> <porta-base> 56 $D/56-2.json
bash ecidade/tests/sistema/telas-js/rodar.sh <agente> <porta-base> 85 $D/85-1.json
node ecidade/tests/sistema/telas-js/bateria.mjs comparar $D/56-1.json $D/56-2.json    # IGUAIS (exit 0) ou DIFERE (exit 1)
node ecidade/tests/sistema/telas-js/bateria.mjs comparar ecidade/tests/sistema/telas-js/base/parte-A-5.6.json $D/85-1.json
```

`rodar.sh` sai com `3` se o vigia acusar escrita fora de `db_logsacessa*`, `db_usuariosonline`, `oauth_*`: pare e investigue antes de seguir (repita a tela isolada: o vigia enxerga o banco inteiro).
O vigia é o script `vigia-banco.sh` (compara `pg_stat_user_tables` antes e depois); a variável `QUADRO` aponta para a pasta que contém `ferramentas/vigia-banco.sh`.
Dependências: Node, o pacote `playwright` (achado no cache do `npx`, ou `PLAYWRIGHT_DIR=<pasta node_modules>`) e o Chrome do sistema
(`/usr/bin/google-chrome`, ou `CHROME=<caminho>`). Usuário de teste `dbseller`/`dbseller` (`SISTEMA_USUARIO`/`SISTEMA_SENHA`).

## O que a ferramenta faz

1. **Login pela tela real**: preenche e clica "Entrar" em `/login.php`; a tela faz `POST v4/oauth/token` e guarda o token no `localStorage`,
   de onde o `HttpClient` das telas o lê. O `window.open` do login é anulado e o `abrir.php` é pedido direto (mesma senha md5). Se o token não
   sai (8.5 de hoje) as telas seguem **sem token** e o modo fica no campo `login` do JSON.
2. Abre o desktop (`inicio.php`) e navega o **frame `corpo`** para cada tela, como o menu faz: `scripts.js` usa `CurrentWindow.corpo` e,
   sem ele, devolve ao login (aberta fora do desktop a tela não executa o próprio JS).
3. A sessão do login não traz instituição/módulo/exercício (o navegador os escolhe): são acrescentados no arquivo de sessão do container, **antes de
   cada tela**, como em `relatorios-kernel/sessao.sh`. Nada no banco.
4. Registra, por tela: status do documento, título, chamadas `/v4/` (método, rota, status, corpo normalizado), `alert()`/`confirm()` (dispensados) e
   erros de JavaScript. Não clica em nada.
5. **Normalização**: JSON com chaves ordenadas; máscara de hashes md5, `localhost:PORTA`, `sid=`, `wname…`, datas/horas e epoch; texto não JSON
   com espaços colapsados e cortado em 1.500 caracteres. As chamadas saem ordenadas (as respostas chegam em ordem variável).

## Resultado (13/11/2026, commit-base `bf9e07f56`)

14 casos: **13 abertos** (11 telas + 2 formulários abertos pela tela que os inclui), 1 ponto cego. Das 13, **6 telas fazem 8 chamadas `/v4/` ao abrir**; as outras 7 só chamam depois de uma ação do usuário.

| Tela | Chamadas ao abrir (5.6) |
|---|---|
| `efd4_efdreinfconfiguracao001` | `POST …/efd-reinf/configuracao/get` 200 |
| `pes3_consvantagemconf002` | `POST //v4/…/concessaodireitos/configuracao` **500** (`Undefined index: rh500_sequencial` em `AssentConfigController.php:69`; o JS chama a rota com barra dupla e sem parâmetro, igual no 5.6: defeito antigo, não corrigido) |
| `pes4_jetomcomissao` | `GET …/jetom/comissao/`, `…/funcao/`, `…/tiposessao/all`: 200 |
| `pes4_jetomfuncao`, `pes4_jetomprocessamento`, `pes4_jetomsessao` | 1 `GET` cada: 200 |

- **5.6 duas vezes: diff vazio** (`diff` byte a byte do JSON). Baseline: `base/parte-A-5.6.json`.
- **Texto do erro de JavaScript:** com 3 chamadas 500 em paralelo, o Chrome ora diz `Failed to execute 'json' on 'Response': Unexpected end of JSON input`, ora só `Unexpected end of JSON input` (corrida entre quem lança). A ferramenta tira o prefixo `Failed to execute 'json' on 'Response': ` do texto. Com isso o **8.5 rodado 2 vezes dá diff vazio** e a linha de base `base/parte-A-8.5-hoje.json` foi regravada.
- **8.5 de hoje** (`base/parte-A-8.5-hoje.json`): a tela de login não obtém o token (`Houve um erro ao se autenticar.`, o `/v4` dá 500 no 8.5) e
  **as 8 chamadas voltam 500 sem corpo**; as páginas abrem (200) mas acusam erros de JavaScript das respostas vazias (`…reading 'map'`). Diferem 6 das 15 linhas
  (as 6 telas acima); o resto é igual. Esta é a linha de base do 8.5, não falha da ferramenta (critério 4).
- **Vigia** (`vigia-banco.sh depois`, rc=0 nas 3 rodadas): mudaram só `db_logsacessa_202611_0`, `db_usuariosonline` e `oauth_access_tokens`/`oauth_refresh_tokens` (login).

## Pontos cegos (com motivo)

- `api/V1/Middleware/Session/MenuAcessadoSessionMiddleware.php`: middleware PHP, sem tela nem chamada JS; roda em toda rota `/v4/api` autenticada, então
  sua linha de base são as chamadas acima e as rotas `/v4` da bateria de rotas.
- `cai1_pix002.php`: Pix, na parte B.
- **Ação do usuário**: `lic4_integracaocomprasbr` (exportar/importar), `forms/db_frmdb_bancos` (atualizar/excluir banco Pix), `forms/db_frmarretipo002`
  (atualizar tipo de débito, listar banco Pix), `pes4_importacaoponto001`, `edu1_atividadecomplementarespecial001`, `pro3_consultaprocesso002`
  (precisa de nº de processo) e `con4_ecidadeinfo.RPC.php` só chamam `/v4/` depois de clique ou parâmetro. Não clicamos (poderia gravar); ficam sem chamadas
  na linha de base. Os formulários de `forms/` são abertos por `cai1_arretipo001.php` e `con1_db_bancos001.php` (telas de inclusão, sem chave).
- `forms/db_frmarretipo002` registra 1 erro de JavaScript (`appendChild`) igual no 5.6 e no 8.5: herdado.
- Respostas `/v4/` com dados (`data: []`) dependem do que a base de exemplo tem; vazias aqui, podem ser diferentes em outra prefeitura.
