# Inventário de branches contra a integração (T-017)

Medido em 13/11/2026, depois de `git fetch origin`. A tabela foi tirada com `laravel/integracao` em `d46b684c6`; a integração mudou
durante a tarefa (decisão do cliente de 13/11, ver "Atualização" abaixo), então **as contagens atrás/frente envelhecem a
cada merge — rode o script para os números do momento**. Escopo: toda branch local e `origin/*`, exceto `equipe/*` (8 branches
de apoio do Maestri) e `testes/rodada`. Somente leitura: nada foi mesclado, enviado ou apagado por esta tarefa.

## Como reproduzir

```bash
git fetch origin
bash scratchpad/inventario_branches.sh      # TSV: ref, atrás/frente de laravel/integracao e de origin/base-php84, data, no_github, último commit
git cherry laravel/integracao <branch>      # '-' = commit com patch equivalente já na integração; '+' = ainda fora
git log --oneline laravel/integracao..<branch>
git ls-remote --heads origin                # as 11 branches que existem de fato no GitHub
```

O `git fetch origin` **não apaga** refs locais de branches removidas no GitHub; por isso a coluna `no_github` do script cruza cada
`origin/*` com `git ls-remote --heads origin` (`nao` = ref local velho). Hoje só `origin/assistencia-social/migracao` está nesse caso.
(`git fetch --prune origin` removeria o ref local; não foi feito para não perder a referência.)

Colunas: *atrás* = commits da referência que a branch não tem; *frente* = commits da branch que a referência
não tem. "Fora" abaixo é *frente* contra `laravel/integracao`.

## Resultado em uma frase

O GitHub tem 11 branches: as sete áreas, `base-php84`, `master`, `laravel-upgrade` e `nucleo/correcoes-transversais`. Fora da
integração só há `laravel-upgrade` (1 commit, já integrado por conteúdo pela T-002); `correcoes-transversais` entrou inteira em
`ae96652a7`. `origin/assistencia-social/migracao` **foi apagada do GitHub** por decisão do cliente (a área será refeita à mão) e o
merge da T-001 foi **revertido** (`31e3e5e84`). Fora disso, só branches de tarefa locais e as três do login (decisão do cliente).

## Ocorrências durante a medição (13/11/2026)

1. **`origin/nucleo/correcoes-transversais`** (1 commit, `fe5503916`, Diego, 12/11) não estava no inventário do `PROJETO.md`.
   Conteúdo: `pg_lo_export` na ordem antiga em 14 pontos, `dbagata` (`AgataQuery`, `pclzip`), remoção de 56 arquivos de cache do
   `modification()`, docs. Medida feita com a integração em `d46b684c6` (por arquivo, comparando o blob de `fe5503916` com o da
   integração): o commit toca **79 arquivos**; **75** já estavam iguais ou aplicados (as 56 remoções de cache, 18 arquivos de
   `ecidade/` e `docs/registro/dimensionamento.md`, por terem vindo no merge da T-001) e **4 diferiam**: `CLAUDE.md`,
   `docs/divergencias-conhecidas.md`, `docs/registro/area-tributario.md` e `docs/registro/correcoes-transversais.md`. A nota de
   `MERGES.md` ("26 de 30 arquivos iguais") usa outra contagem. **Classificação: decidida pelo cliente em 13/11/2026 — integrada inteira em `ae96652a7` (ver Atualização).**
2. **`origin/base-php84` estava 2 commits à frente** de `laravel/integracao` (`79958b1fb`, `36f42cefb`, 12/11:
   `docs/migrar-um-modulo.md`, skill `migrar-modulo`, `scratchpad/prefixos_area.py`). Só docs/ferramenta.
   Resolvido em `d46b684c6`; hoje 0 atrás.
3. **T-001 constava Feita mas o merge não estava na integração.** Resolvido em `0f862305d` — e depois revertido (ocorrência 4).
4. **`origin/assistencia-social/migracao` não existe mais no GitHub** (`git ls-remote --heads origin` não a lista; o ref local é
   tracking velho, por isso o script traz a coluna `no_github`). Evidência do motivo:
   `fe5503916:docs/registro/correcoes-transversais.md`, linhas 3–5 — "em 12/11/2026 o usuário decidiu **refazer a Assistência Social
   à mão** e pediu para separar estas correções numa branch própria antes de apagar aquela". Isso conflitava com a premissa da
   decisão (f) / T-001 (`BACKLOG.md`: integrar a Assistência Social por merge). **Classificação: decidida pelo cliente em 13/11/2026 (a Assistência Social sai da integração).** Resolvido
   em 13/11 (ver Atualização).

## Atualização — decisão do cliente de 13/11/2026 (durante a T-017)

A integração passou a ser: `31e3e5e84` **reverte** o merge da Assistência Social (`0f862305d`; a área vai ser refeita à mão) e
`ae96652a7` integra só `nucleo/correcoes-transversais` (`fe5503916`: `pg_lo_export`, `dbagata`, cache do `modification()`), com os
4 arquivos de docs que faltavam. Consequências para a tabela abaixo:
- `origin/nucleo/correcoes-transversais`: **já integrada** (ancestral da integração).
- `origin/assistencia-social/migracao`, `laravel/T-001-merge-assistencia-social`, `qa/T-001`: **decisão do cliente** — commits no
  histórico, mas o conteúdo da área **não** está na integração (merge revertido); só as correções transversais entraram.
- T-019 (`tributario/T-019-calculos-lote`): integrada em `1439ca125` e **reaberta** (22 `$$matriz[$i]`); 3 commits novos na
  branch, em Revisão. T-023 (`25feaf5c1`) e T-006 (`bf9e07f56`): integradas.
- Novas desde a medição: `nucleo/T-027-pg-lo-export-guarda` (WIP), `nucleo/T-028-jpgraph-pizza`, `testes/T-032-sessao-entre-runtimes`
  (tarefas em andamento).

## Tabela

`int` = `laravel/integracao`; `base` = `origin/base-php84`. Pares são *atrás/frente*.

### Já integradas (frente 0 contra a integração)

| Branch | int | base | Último commit | Observação |
|---|---|---|---|---|
| `origin/base-php84` | 0/0 | 0/0 | 12/11 | base do fork; a integração a contém (48 à frente) |
| `laravel/integracao` | 0/0 | 0/48 | 13/11 | referência |
| `base-php84` (local) | 220/0 | 172/0 | 30/10 | cópia local antiga da base |
| `master`, `origin/master` | 222/0 | 174/0 | 07/08 | ancestral; checkout do cliente — não mexer |
| `origin/1tributario-migrado` | 159/0 | 111/0 | 27/10 | área 1, PR #2 |
| `origin/2educacao-migrado` | 134/0 | 86/0 | 27/10 | área 2 |
| `origin/3recursoshumanos-migrado` | 111/0 | 63/0 | 27/10 | área 3 |
| `origin/4patrimonial-migrado` | 98/0 | 50/0 | 29/10 | área 4 |
| `origin/5financeiro-migrado` | 85/0 | 37/0 | 30/10 | área 5 |
| `origin/6saude-migrado` | 72/0 | 24/0 | 01/11 | área 6 |
| `origin/7configuracao-migrado` | 64/0 | 16/0 | 03/11 | área 7 |
| `origin/nucleo/correcoes-transversais` | 58/0 | 2/1 | 12/11 | **decidida pelo cliente 13/11**: integrada inteira em `ae96652a7` (ocorrência 1 e Atualização) |
| `laravel/T-001-merge-assistencia-social`, `qa/T-001` | 40/0 | 2/10 | 12/11 | T-001; commits no histórico, efeito **revertido** em `31e3e5e84` (decisão do cliente) |
| `docs/T-002-compatibilidade-frontcontroller`, `qa/T-002` | 47/0 | 2/3 | 12/11 | T-002 |
| `laravel/T-005-matriz-versoes`, `qa/T-005` | 48/0 | 2/2 | 12/11 | T-005 |
| `laravel/T-007-silex-caminhos`, `qa/T-007` | 47/0 | 2/3 | 12/11 | T-007 |
| `testes/T-008-suite-script`, `qa/T-008` | 49/0 | 2/1 | 12/11 | T-008 |
| `testes/T-009-inventario-testes`, `qa/T-009` | 39/0 | 2/11 | 12/11 | T-009 |
| `laravel/T-018-namespace-reservados`, `qa/T-018` | 42/0 | 2/8 | 12/11 | T-018 |
| `nucleo/T-021-bibliotecas-residuais`, `qa/T-021` | 46/0 | 2/4 | 12/11 | T-021 |
| `qa/T-019` | 44/1 | 2/7 | 12/11 | T-019 (cópia de revisão) |
| `nucleo/T-013-login-seguranca`, `qa/T-013` | 41/0 | 2/9 | 12/11 | commits no histórico da integração, mas o efeito foi **revertido** em `dab17000e` (Regra 3): conteúdo fora; branch fica só como registro |
| `tmp-x` | 48/0 | 2/2 | 12/11 | ponteiro de trabalho da T-009, ancestral da integração; descartável |
| `testes/T-024-inventario-documentos` | 14/0 | 2/36 | 12/11 | recém-criada, sem commit próprio (T-024 não começou) |
| `docs/T-017-inventario-branches` | 0/0 | 0/48 | 13/11 | esta tarefa |

### Só documentação, já integrada por conteúdo

| Branch | int | Fora | Evidência |
|---|---|---|---|
| `origin/laravel-upgrade` | 221/1 | 1 (`23e181d3e`) | `git cherry` dá `-`: o patch está na integração pela T-002 (`compatibilidade-FrontController.md`). Commit original preservado. |

### Tarefas em andamento (trabalho esperado, ainda a integrar por tarefa)

| Branch | int | Fora | Estado / tarefa |
|---|---|---|---|
| `laravel/T-006-passport-esquema`, `qa/T-006` | 52/0 | 0 | T-006, integrada em `bf9e07f56` (só documentação) |
| `testes/T-023-linha-de-base-relatorios-kernel` | 52/0 | 0 | T-023, integrada em `25feaf5c1` |
| `tributario/T-019-calculos-lote` | 52/3 | 3 | T-019 reaberta na revisão: 22 `$$matriz[$i]` |
| `nucleo/T-027-pg-lo-export-guarda` | 7/2 | 2 | T-027, em andamento |
| `nucleo/T-028-jpgraph-pizza` | 9/3 | 3 | T-028 |
| `testes/T-032-sessao-entre-runtimes` | 5/3 | 3 | T-032 |
| `testes/T-003-lint-universo`, `qa/T-003` | 49/1 e 14/2 | 1 e 2 | T-003 (QA); `qa/T-003` traz também um merge da integração |
| `testes/T-012-sistema-rotas`, `qa/T-012` | 14/4 | 4 | T-012 (validação); dividir o commit grande antes de integrar |
| `testes/T-010-linha-de-base-guia` | 14/1 | 1 | T-010 |
| `testes/T-011-sistema-telas` | 50/2 | 2 | T-011, em andamento |
| `laravel/T-022-vendor-proprio-runtime-novo` | 29/2 | 2 | T-022, reprovada, refazendo a bateria |
| `nucleo/T-026-handler-erro-php8` | 17/2 | 2 | T-026 |
| `nucleo/T-020-legados-residuais` | 14/1 | 1 | T-020 |
| `rector/T-004-varredura-simulacao` | 0/2 | 2 | T-004, em andamento; só scripts e doc |

### Decisão do cliente (login e Assistência Social; ficam fora da integração)

| Branch | int | Fora | Evidência |
|---|---|---|---|
| `origin/assistencia-social/migracao` | 42/0 | 0 (merge revertido) | 8ª área. **Apagada no GitHub** (ref local velho; `no_github=nao`); merge da T-001 revertido em `31e3e5e84`: a área será refeita à mão (ocorrência 4, Atualização). Os commits estão no histórico, o conteúdo da área **não** está na integração. |
| `nucleo/login-seguranca` | 52/6 | 6 | login seguro; Regra 3 do cliente: login igual ao legado. Documentado, não integrado. Atenção: `git cherry` dá `-` em 5 dos 6 porque os patches da T-013 estão no histórico da integração, mas foram **revertidos em `dab17000e`**: o conteúdo **não** está na integração. |
| `nucleo/T-014-segredo-api-endpoint` | 41/6 | 6 | T-014 cancelada (Regra 3) |
| `nucleo/T-015-segredo-api-ambiente` | 41/9 | 9 (os 6 da T-014 + 3) | T-015 cancelada (Regra 3) |

### Obsoletas / abandonadas

Nenhuma encontrada. `base-php84` local e `tmp-x` são só ponteiros atrasados; `qa/T-*` são cópias de revisão
das mesmas tarefas e podem ser apagadas depois do merge (decisão fora desta tarefa).

## Conferência do critério 3

Branches do GitHub (`git ls-remote --heads origin`, 11): as sete áreas, `base-php84`, `master`, `laravel-upgrade`
e `nucleo/correcoes-transversais`. Fora da integração restava apenas o descrito acima, tudo classificado; a única
novidade em relação ao inventário do `PROJETO.md` foi `correcoes-transversais` (ocorrência 1, hoje integrada). Todo o resto fora da
integração está em branches de tarefa locais, nas três do login e na Assistência Social apagada (decisão do cliente).

O número de commits muda a cada integração; para atualizar a tabela, rode o script de novo.
