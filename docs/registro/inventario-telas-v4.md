# Telas e front Vue que chamam `/v4`: inventário (sem banco)

Para saber por onde começar quando as rotas `/v4` forem comparadas entre o 7.4 e o 8.5: quais telas legadas (`*.php` da raiz e `forms/`), scripts (`scripts/`, `extension/`) e componentes Vue (`resources/vue/`) chamam quais rotas,
e quais rotas ninguém chama. **Só leitura de código na `base-php74`: nada foi rodado e não houve banco.** As rotas foram lidas dos arquivos de rotas (sem `route:list`), e as chamadas foram achadas por varredura de texto.

**Resumo:** 1.294 rotas `/v4` (mais 113 `/web` e 4 `/rest`); **926 têm chamador firme**, 81 só um chamador provável, 13 só uma chamada à base do caminho e **274 não têm chamador achado**.
1.332 chamadas em 484 arquivos (233 telas legadas, 233 arquivos Vue, 17 `scripts/`, 1 `extension/`); 53 chamadas em 27 arquivos apontam para rotas que **não existem**.

Arquivos de dados (todos em `docs/registro/`): `inventario-v4-rotas.tsv` (1.411 rotas com situação e exemplos de chamador), `inventario-v4-chamadas.tsv` (1.332 chamadas: arquivo, linha, método, caminho, classe, rotas casadas) e `inventario-v4-lotes.tsv` (61 lotes).

## Como foi feito

Três scripts em `scratchpad/`, rodados em sequência da raiz do repositório:

```bash
python3 scratchpad/inventario_v4_rotas.py rotas.tsv
python3 scratchpad/inventario_v4_chamadas.py rotas.tsv chamadas.tsv rotas-uso.tsv
python3 scratchpad/inventario_v4_lotes.py rotas.tsv rotas-uso.tsv chamadas.tsv inventario-v4-rotas.tsv inventario-v4-lotes.tsv
```

- **Rotas** (`inventario_v4_rotas.py`): parte de `app/Providers/RouteServiceProvider.php` e segue `Route::prefix`, `Route::middleware`, `Route::group`, `->group(closure)`, `->group(base_path('routes/...'))`, `Route::get/post/put/patch/delete/match/resource/apiResource`;
  resolve as variáveis de caminho e de controller que são só de literais; acrescenta as 15 rotas do Passport 10 (`Passport::routes(null, ['prefix' => 'v4/oauth'])`, que vêm do pacote). Conferido contra o texto: das linhas `Route::(get|post|put|patch|delete|any|match)` dos arquivos (1.411, algumas comentadas), as únicas não lidas, fora as comentadas, são as 29 dos 3 arquivos que ninguém carrega (abaixo).
- **Chamadas** (`inventario_v4_chamadas.py`): acha `v4/...` dentro de string em `.php`, `.js`, `.vue`, `.html` (fora de `vendor/`, `tmp/`, `public/`, `tests/`, `routes/`, `database/`, `dbagata/`), troca `${x}`, `' + x + '` e `<?= ?>` por `{x}`, tira a query string e detecta o método pela chamada vizinha (`.get(`, `.post(`, `method:`). Classes:
  `exata` (o caminho existe), `composta` (o arquivo define a base e outro literal dele fecha uma rota), `relativa` (`'financeiro/planejamento/x'` com a base vinda de `requestApi`/`urlApi`/`apiUrl`; a tela legada nem escreve `v4/`),
  `provavel` (o literal é o rabo de uma rota, 2 segmentos ou mais), `prefixo` (só a base de um módulo), `base_global` (`/v4` ou `/v4/api` sem o resto) e `sem_rota` (nenhuma rota casa).
  Fora da conta ficam 22 ocorrências em `app/` e `src/`, que são comentários `@api` das próprias rotas, não chamadores.
- **Lotes** (`inventario_v4_lotes.py`): agrupa por `área/módulo` (os 2 primeiros segmentos depois de `v4/api`).

## 1. Rotas lidas

| Família | Rotas |
|---|---|
| `/v4/api/...` | 1.275 |
| `/v4/oauth/...` (Passport) | 15 |
| `/v4/login`, `/v4/logout`, `/v4/kill`, `/v4/unblock` | 4 |
| **`/v4` no total** | **1.294** |
| `/web/...` | 113 |
| `/rest/v1/...` | 4 |
| **Todas** | **1.411** (1.453 registros; 42 pares método+caminho aparecem duas vezes porque o mesmo arquivo de rotas é carregado por dois grupos) |

**Três arquivos de rotas que nenhum provider carrega**, 29 rotas que nunca são registradas: `routes/api/assinador/assinador.php` (6), `routes/api/patrimonial/ouvidoria.php` (22) e `routes/web/Tributario/Arrecadacao.php` (1).
Conferência: `git grep -nE 'assinador/assinador|patrimonial/ouvidoria|Tributario/Arrecadacao' -- ecidade/routes ecidade/app ecidade/bootstrap ecidade/configuration` não acha nenhuma referência.

## 2. Chamadas

| Classe | Chamadas |
|---|---|
| `exata` | 531 |
| `relativa` (+1 com método diferente) | 475 + 1 |
| `provavel` | 124 |
| `composta` | 96 |
| `sem_rota` | 53 |
| `base_global` | 28 |
| `prefixo` | 17 |
| `exata` com método diferente da rota | 7 |
| **Total** | **1.332** |

Por tipo de arquivo: 665 chamadas em telas legadas (233 arquivos), 610 em Vue (233 arquivos), 55 em `scripts/` (17 arquivos) e 2 em `extension/` (1 arquivo).

As 7 chamadas com método diferente da rota: `forms/db_frmrechumanoativ.php:198` (`atestado-frequencia/salvar-obs-rh`), `Jobs.vue:147` (`jobs/{x}destroy-many`), `AbaFinalizar.vue:188` (`gerador/relatorios/{x}`) e 4 em `ManutencaoParametrosFundeb.vue` e `ProcessamentoRubricaSalario.vue` (`rhcargo/list`, `rhlocaltrab/list`, `tipoasse/list`, `rhrubricas/list`).
O método é inferido da chamada vizinha, então podem ser falso alarme; fica para quem for comparar a rota.

## 3. Rotas × chamadores

De 1.294 rotas `/v4`:

| Situação | Rotas | Significado |
|---|---|---|
| `firme` | 926 | ao menos uma chamada `exata`, `composta` ou `relativa` |
| `provavel` | 81 | só chamadores `provavel` (o rabo da rota aparece num arquivo que usa a API) |
| `so_base` | 13 | só chamadas à base do módulo (`prefixo`) |
| `sem_chamador` | 274 | nenhum chamador achado |

### Chamadas sem rota (53 em 27 arquivos)

O front chama rotas que **não estão registradas** em `routes/`. 29 delas em `tributario/cadastro` (`emissao_ecarta/*`, `decad/*`, `calculo_iput/*`, `arquivo_xml_correios`, só em componentes Vue de `Tributario/Cadastro/`; `git grep -liE 'emissao_ecarta|calculo_iput|decad/' -- ecidade/app ecidade/routes ecidade/src` não acha nada),
8 em `tributario/arrecadacao` (`request-api-pix/*`: existe `RequisicaoAPIPIXController`, mas nenhuma rota aponta para ele), 4 em `educacao/matricula-online`, 3 em `configuracao/arquivo_xml_correios`, 2 em `patrimonial/ouvidoria`
(nesse módulo, o arquivo de rotas existe mas ninguém o carrega) e 7 espalhadas. A lista completa é `inventario-v4-chamadas.tsv` filtrado por `classe = sem_rota`.
Comando: `awk -F'\t' 'NR>1 && $6=="sem_rota"' docs/registro/inventario-v4-chamadas.tsv | wc -l` dá 53.

## 4. Rotas sem nenhum chamador conhecido (274)

| Por middleware | Rotas |
|---|---|
| `clientCredential` (token de cliente, forma de integração externa) | 43 (de 55 rotas `/v4` com esse middleware) |
| `AuthRedesim` / `AuthSim` (integração) | 1 |
| `auth:api` (usuário logado) | 168 |
| sem middleware de autenticação | 62 |

Por módulo, as que mais têm: `financeiro/contabilidade` 29, `patrimonial/protocolo` 30, `educacao/central-de-matriculas` 25, `recursos-humanos/pessoal` 22, `tributario/issqn` 19, `tributario/cadastro` 15 (todas `clientCredential`), `educacao/escola` 15, `financeiro/planejamento` 14 (`inventario-v4-lotes.tsv`, coluna `sem_chamador`).
Quase todas as `clientCredential` e as `/v4/oauth/*` (inclusive `POST /v4/oauth/token`, que o login novo não chama mais) têm cara de integração externa. As 168 com `auth:api` e as 62 sem autenticação podem ser tela que a varredura não achou ou rota sem uso.

**Esta lista é um limite superior.** Uma amostra de 40 rotas sem chamador achou o rabo do caminho em algum arquivo para 8 (20%): por exemplo `ProcessoInscricaoService.js`, `AcompanhamentoAlunosPCD.vue`, `NotaExplicativa.vue`, `Emissoes.vue` e `ExecutarAcaoRedesim.js`, onde a base e o resto do caminho ficam em lugares diferentes ou com método/parâmetro que o script não casou.
Estimativa: de 20% das 274 (cerca de 55) já têm chamador; **cerca de 220 sem chamador é o número a esperar**.

## 5. Ordem sugerida dos lotes

Critério: primeiro o que toda sessão usa, depois os módulos com **mais arquivos chamadores distintos** (mais telas afetadas se a rota mudar), e por último o que só tem integração externa ou ninguém. Lotes de até ~60 rotas.

| Ordem | Lote | Rotas | Com chamador firme | Arquivos chamadores | Observação |
|---|---|---|---|---|---|
| 0 | acesso: `/v4/login`, `/logout`, `/kill`, `/unblock` e `/v4/oauth/*` | 19 | 4 | login e Desktop | toda sessão passa por aqui; depende do Passport 13 |
| 1 | `configuracao/*` (16 módulos: `gerador` 15, `jobs` 15, `instituicao` 7, `menu` 7, `usuario` 6, `banco-pix` 5…) | 78 | 50 | 8 (`gerador`), 6, 5, 4, 4 | usadas pelo Desktop e por vários componentes Vue |
| 2 | `financeiro/contabilidade` (3 lotes) | 157 | 116 | 55 | o módulo com mais chamadores (26 Vue) |
| 3 | `educacao/escola` (3 lotes) | 141 | 112 | 42 | |
| 4 | `financeiro/planejamento` (2 lotes) | 118 | 99 | 36 | só telas legadas (`pla*`, `pl4_*`), nenhuma em Vue |
| 5 | `recursos-humanos/pessoal` (2 lotes) | 107 | 74 | 33 | |
| 6 | `patrimonial/pncp` | 54 | 51 | 22 | |
| 7 | `financeiro/orcamento` | 45 | 35 | 22 | |
| 8 | `educacao/secretaria` | 37 | 34 | 18 | |
| 9 | `financeiro/tesouraria` | 27 | 24 | 17 | |
| 10 | `tributario/arrecadacao` | 46 | 35 | 16 | |
| 11 | `tributario/issqn` | 45 | 26 | 14 | |
| 12 | `educacao/matricula-online` | 41 | 36 | 14 | |
| 13 | `patrimonial/protocolo`, `tributario/cadastro` | 50 + 32 | 11 + 17 | 12 + 13 | boa parte é `clientCredential` ou sem chamador |
| 14 | os 27 lotes restantes (`financeiro/empenho`, `recursos-humanos/rh`, `saude/*`, `integracoes/*`…) | 297 | 202 | ≤ 12 cada | tabela completa em `inventario-v4-lotes.tsv` |
| 15 | as 274 rotas sem chamador conhecido (estão dentro dos lotes acima: não somar) | 274 | 0 | 0 | por último, com a lista de integração externa à parte |

Os lotes 2 a 13 somam 900 rotas. A soma dos lotes 0, 1, 2 a 13 e 14 é 19 + 78 + 900 + 297 = 1.294, que é o total de `/v4` e a soma da coluna `rotas` de `inventario-v4-lotes.tsv` (`awk -F'\t' 'NR>1 {s+=$2} END {print s}' docs/registro/inventario-v4-lotes.tsv`). O lote 15 não entra na soma (é um recorte dos outros).

## Conferência das contagens

Da raiz do repositório (`R` = `docs/registro/inventario-v4-rotas.tsv`, `C` = `docs/registro/inventario-v4-chamadas.tsv`):

| Contagem | Comando | Resultado |
|---|---|---|
| rotas (todas) | `tail -n +2 $R \| wc -l` | 1.411 |
| rotas `/v4` | `awk -F'\t' 'NR>1 && $2 ~ /^\/v4\//' $R \| wc -l` | 1.294 |
| `/v4/api`, `/v4/oauth`, `/web`, `/rest` | o mesmo `awk` com `/^\/v4\/api\//`, `/^\/v4\/oauth\//`, `/^\/web\//`, `/^\/rest\//` | 1.275, 15, 113, 4 |
| situação das rotas `/v4` | `awk -F'\t' 'NR>1 && $2 ~ /^\/v4\// {c[$6]++} END {for (k in c) print k, c[k]}' $R` | firme 926, provavel 81, so_base 13, sem_chamador 274 |
| `sem_chamador` com `clientCredential` / `/v4` com `clientCredential` | `awk -F'\t' 'NR>1 && $2 ~ /^\/v4\// && $6=="sem_chamador" && $4 ~ /clientCredential/' $R \| wc -l` (e sem o `$6==...`) | 43 / 55 |
| chamadas | `tail -n +2 $C \| wc -l` | 1.332 |
| arquivos com chamada | `tail -n +2 $C \| cut -f1 \| sort -u \| wc -l` | 484 |
| chamadas por classe | `tail -n +2 $C \| cut -f6 \| sort \| uniq -c` | `exata` 531, `relativa` 475 (+1), `provavel` 124, `composta` 96, `sem_rota` 53, `base_global` 28, `prefixo` 17, `exata(metodo difere)` 7 |
| chamadas por tipo | `tail -n +2 $C \| cut -f3 \| sort \| uniq -c` | `php-legado` 665, `vue` 610, `js` 55, `extension` 2 |
| arquivos com chamada `sem_rota` | `awk -F'\t' 'NR>1 && $6=="sem_rota"' $C \| cut -f1 \| sort -u \| wc -l` | 27 |
| soma dos lotes | `awk -F'\t' 'NR>1 {s+=$2} END {print s}' docs/registro/inventario-v4-lotes.tsv` | 1.294 (61 lotes) |
| linhas `Route::` lidas | `git grep -hE 'Route::(get\|post\|put\|patch\|delete\|any\|match)\(' -- ecidade/routes ecidade/app/Providers/RouteServiceProvider.php \| wc -l` | 1.411 (inclui linhas comentadas e as 29 dos arquivos não carregados; mais 8 `resource`/`apiResource`, que viram várias rotas) |

## Limites

- A varredura é de texto: chamada montada por código (`apiUrl + variavel`) em arquivo diferente da base só entra como `provavel` ou `prefixo`; chamada em arquivo que não foi lido (`dbagata/`, minificados de `public/`) não conta.
- O método do chamador é o da chamada mais próxima da linha; quando não acha, o casamento ignora o método.
- `/web/...` e `/rest/v1/...` foram lidas como rotas, mas não têm chamadores aqui (não são `/v4`).
- O uso real (telas mais acessadas) depende de dados de acesso, que não existem sem banco: a ordem usa o número de arquivos chamadores como aproximação.
