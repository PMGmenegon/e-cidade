# Índice das tarefas da migração do Laravel (rótulos `T-0xx`)

Os registros da migração do Laravel/PHP 8.5 citam rótulos de tarefa (`T-001`, `T-026`…). Este índice diz, para cada
rótulo citado em `docs/` ou no `CLAUDE.md`, o título, o que a tarefa mediu ou mudou e onde está o registro. Situação
medida na `laravel/integracao` em 14/11/2026.

Lista dos rótulos citados (é a que este índice cobre; nenhum fica de fora):

```bash
git grep -oh 'T-0[0-9][0-9]' -- docs CLAUDE.md | sort -u
```

"Integrada" = o merge da branch da tarefa está na `laravel/integracao`. "Fora da integração" = a branch existe só
localmente (em andamento, em revisão ou descartada); o registro dela ainda não está no repositório.

## Integradas

| Rótulo | Título | O que mediu ou mudou | Registro |
|---|---|---|---|
| T-002 | Incorporar o documento da branch `laravel-upgrade` | trouxe o estudo do despacho do `FrontController.php` (`api/vN/`, `v4/`, `rest/v1/`, `app.php`) com correções de 12/11/2026 | `docs/migracao-laravel/compatibilidade-FrontController.md` |
| T-003 | Checagem de sintaxe do universo nos dois runtimes | `php -l` nos 32.907 arquivos no 5.6 e no 8.5: 100 falham nos dois, 27 só no 8.5 | `docs/registro/lint-universo.md`, `lint-universo-falhas.txt` |
| T-004 | Rector em simulação fora das áreas já portadas | rodou o Rector do projeto em `--dry-run` sobre os 20.183 arquivos fora das áreas 1–8 e classificou as 4.380 pendências por impacto medido no 8.5 | `docs/registro/rector-varredura-t004.md`, `rector-varredura-t004-pendencias.tsv` |
| T-005 | Matriz de versões e resolução do Composer (L12/L13, PHP 8.4/8.5) | resolveu o Composer para Laravel 12 e 13 em PHP 8.4 e 8.5 e listou os pacotes que travam | `docs/migracao-laravel/matriz-versoes.md`, `docs/registro/laravel.md` |
| T-006 | Passport sobre o esquema atual `oauth_*` sem migration | leu o esquema `oauth_*` (só leitura) e provou em execução o que o Passport 12.4/13 lê e grava nele | `docs/registro/passport-esquema.md` |
| T-007 | Silex (API V1): caminho de atualização e datas de suporte | mediu a API V1 (7 rotas, 33 arquivos) e comparou manter, atualizar e substituir, com as datas de suporte de Laravel e PHP | `docs/migracao-laravel/silex-caminhos-e-suporte.md` |
| T-008 | Script único da suíte: esqueleto nos dois runtimes | criou `ecidade/tests/suite/rodar.sh`, que roda o PHPUnit por camada no 5.6 e no 8.5 e gera um relatório por runtime | `docs/registro/suite-script.md` |
| T-009 | Inventário dos testes existentes e dublês | classificou os 46 arquivos de teste por runtime e mediu PHPUnit 9.6 × 12.5 | `docs/registro/testes-inventario.md` |
| T-010 | Linha de base da suíte (unitário e integração) e guia | rodou a suíte nos dois runtimes antes de qualquer atualização do Laravel e escreveu o guia de uso | `docs/registro/suite-testes.md`, `docs/suite-de-testes.md` |
| T-011 | Sistema/telas: parametrizar o comparador e as divergências conhecidas | deixou o `cmp.py` comparar dois runtimes quaisquer (seleção de telas, vigia do banco) e listou as divergências medidas | `docs/registro/sistema-telas.md` |
| T-012 | Sistema: rotas `/v4`, API V1 e login, 5.6 × novo | camada sistema da suíte: GET só de leitura nas rotas `/v4`, na API V1 e no login, comparando 5.6 × novo | `docs/registro/testes-sistema-rotas.md` |
| T-017 | Inventário de todas as branches contra a integração | classificou cada branch local e do `origin` contra a `laravel/integracao` e a `origin/base-php84` | `docs/registro/inventario-branches.md` |
| T-018 | Porte residual: namespace `AndamentoPadrao` e nome `String` (6) | corrigiu os 6 arquivos que não compilavam só no 8.5 (5 `use` com nome qualificado quebrado e um `use Cake\Utility\String` sem uso) | `docs/registro/lint-universo-depois-t018.md` |
| T-019 | Porte residual: cálculo de IPTU, ISSQN fixo e lote (4) | portou os 4 arquivos de cálculo que não compilavam no 8.5; reaberta para os 22 `$$matriz[$i]` | `docs/registro/lint-universo.md` (seção "Depois — T-019") |
| T-020 | Porte residual: demais legados (7) | corrigiu os 7 arquivos que ainda não compilavam só no 8.5, cada um no mínimo que reproduz o 5.6 | `docs/registro/lint-universo.md` (seção "Depois da T-020") |
| T-021 | Porte residual: bibliotecas fpdf, jpgraph, securimage e Michelf (10) | portou o mínimo para as 10 bibliotecas embutidas compilarem no 8.5 | `docs/registro/lint-universo.md` ("Depois — porte residual das bibliotecas") |
| T-022 | Runtime novo com `vendor/` próprio (mecanismo, sem escolher versão) | deu ao runtime novo (PHP 8.5) `vendor/`, `bootstrap/cache` e `storage/` próprios, provado com uma cópia do vendor atual, sem tocar no 5.6 | `docs/registro/runtime-novo.md` |
| T-023 | Linha de base dos 5 relatórios que sobem o Laravel (5.6) | capturou no 5.6 a saída dos 5 relatórios que sobem o kernel do Laravel na página | `docs/registro/relatorios-kernel-linha-de-base.md` |
| T-024 | Inventário e linha de base de documentos (PDF, planilha, Word, QR) | inventariou os documentos emitidos e fotografou 14 casos no 5.6 × 8.5, antes de trocar as bibliotecas | `docs/registro/documentos-linha-de-base.md` |
| T-026 | Handler de erro V3 no PHP 8 (`ArgumentCountError`): porte mínimo | `$context` opcional no handler e no `Logger`, `@` reconhecido pelos bits fatais; 3 telas 5.6 × 8.5 | `docs/registro/handler-erro-php8.md` |
| T-027 | `pg_lo_export` com OID inválido igual ao 5.6 (`false`) | mediu `false` no 5.6 × `ValueError` no 8.x e pôs a guarda nos 14 pontos | `docs/registro/pg-lo-export-oid-invalido.md` |
| T-028 | jpgraph no PHP 8: pizza (`TypeError`) e pizza 3D (assinatura), porte mínimo | corrigiu os defeitos em cadeia que impediam a pizza e a pizza 3D do jpgraph de rodar no 8.5, com o 5.6 como gabarito | `docs/registro/lint-universo.md` (seção "T-028: pizza do jpgraph no PHP 8") |
| T-032 | Convivência de sessão entre runtimes hoje (linha de base) | mediu como a sessão e o token OAuth do `/v4` passam entre 5.6 e 8.5 (volume `ecidade_sessions` compartilhado) | `docs/registro/sessao-entre-runtimes.md` |
| T-033 | API V1 (Silex) no 8.5 em `vendor/` descartável | rodou a API V1 no 8.5 com `vendor/` só dela e comparou 4 GET rota a rota com o 5.6 | `docs/migracao-laravel/api-v1-silex-85.md` |
| T-041 | AgataReport: soma com célula não numérica igual ao 5.6 | corrigiu o `TypeError` do 8.5 na soma do `AgataReport` (`pro1_relcgm002` dava 500) reproduzindo o 5.6 | `docs/registro/agatareport-soma.md` |
| T-030 | Bateria com JavaScript das telas que chamam `/v4` (ferramenta + 1ª metade) | criou a ferramenta de telas com navegador sem interface e gravou a linha de base da 1ª metade das telas que chamam `/v4` | `docs/registro/telas-js.md` |
| T-035 | mPDF, PhpSpreadsheet e PHPWord novos contra a linha de base dos documentos | mediu mPDF 8.3.1, PhpSpreadsheet 5.11.0 e PHPWord 1.4.0 no 8.5 contra os documentos de referência; mudanças de código só listadas | `docs/registro/documentos-candidatas.md` |
| T-043 | Dependências do Laravel 13 só do runtime novo | criou `composer-runtime-novo.json/.lock` (165 pacotes, Laravel 13.42.0, Passport 13.10.0) sem mudar o composer do 5.6 | `docs/registro/dependencias-laravel13.md` |
| T-046 | Dependências só da API V1, nas versões de hoje | trava própria da `api/V1` (Silex 2.2.4 + Symfony 3.4, as versões do lock de hoje) | `docs/migracao-laravel/api-v1-dependencias.md` |
| T-047 | Container próprio da API V1 com regra no proxy | `/api/v1/` vai a um container com as bibliotecas só da API; em andamento: falta o retorno ao 5.6 quando esse container não estiver no ar | `docs/migracao-laravel/api-v1-container.md` |
| T-052 | `mod_imprime11` (carnê) no 8.5: o `split` divergente é alcançável? | mediu se o modelo de carnê com `split` divergente é alcançável por tela servida pelo 8.5 | `docs/registro/split-mod-imprime11.md` |
| T-037 | Varredura da sintaxe uniforme de variáveis (`$$a[...]`) no universo | mediu, por tokenizador, as formas `$$a[...]`/`$o->$p[...]` que mudam de sentido no PHP 7+ e as reescritas do Rector `${$a}[...]` contra o `master` | `docs/registro/varredura-variaveis-variaveis.md` |
| T-040 | `split()` no 8.5: padrões regex e entradas sem autoload | mediu as 2.309 chamadas de `split()`: 41 divergem em silêncio no 8.5 (o substituto faz `explode`) | `docs/registro/split-polyfill-t040.md` |

## Integradas e depois revertidas, ou canceladas

| Rótulo | Título | O que aconteceu | Registro |
|---|---|---|---|
| T-001 | Integrar por merge a 8ª área (Assistência Social) | integrada e **revertida** (`31e3e5e84`): o grupo decidiu refazer a área à mão; no lugar entraram só as correções transversais (`ae96652a7`) | `docs/registro/correcoes-transversais.md`, `inventario-branches.md` |
| T-013 | Integração da branch do login | integrada e **revertida** (`dab17000e`): por decisão do grupo, o login fica igual ao legado, só atualizado | `docs/registro/inventario-branches.md` |
| T-014, T-015 | Mudanças no login e na API (duas tarefas) | **canceladas** antes de integrar, pelo mesmo motivo: o login fica igual ao legado | `docs/registro/inventario-branches.md` |

## Fora da integração (em andamento ou em revisão)

| Rótulo | Título | Situação |
|---|---|---|
| T-016 | Sistema/telas: bateria completa e linha de base | branch `testes/T-016-linha-de-base-telas`, sem registro na integração; citada em `sistema-telas.md` e `suite-testes.md` como a linha de base completa das telas |
