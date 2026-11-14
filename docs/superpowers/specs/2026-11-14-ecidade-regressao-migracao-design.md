# Bateria de regressão para a migração do e-cidade (PHP + Laravel)

Data: 2026-11-14 · Repositório alvo: `git@github.com:Segunddo/e-cidade.git`, branch `base-php84`

## 1. Intenção e porquê

O e-cidade (PHP 5.6 + Laravel 5.4, ~33 mil arquivos PHP, PostgreSQL LATIN1) está sendo migrado para o PHP mais novo (8.5) e para o Laravel 12. O dono da migração precisa **provar que, depois da migração, o sistema responde exatamente como antes**. O sistema não tem especificação nem testes automatizados (`ecidade/tests/` está vazio, Cypress configurado sem testes); a única referência confiável é o próprio sistema antigo rodando.

Entregável: **três baterias** com um único comando cada e um relatório de aprovado/reprovado:

1. **Bateria PHP**: o legado (telas `*.php`, classes, relatórios) se comporta igual no PHP 8.5 e no 5.6.
2. **Bateria Laravel**: a camada Laravel (`app/`, `routes/`, Passport, `api/V1` Silex, PIX) se comporta igual no Laravel 12 e no 5.4.
3. **Bateria completa**: roda as duas, acrescenta fluxos de navegador ponta a ponta e emite um relatório único.

## 2. O que já existe (não refazer)

Em `docs/como-testamos.md` e `scratchpad/`:

- `cmp.py`: GET de cada tela nos dois PHPs (:8080 = 5.6, :8085 = 8.5), comparação byte a byte com normalização (sid, tmp, datas em PDF), restauração de sessão, refazer o par antes de acusar, timeout não conta como igual.
- `escrita.php` + `porclasse.sh`: estado das classes `db_*_classe.php` após `atualizacampos()`.
- `escrita_post.py`: POST real nas duas portas; compara o SQL de negócio via `log_statement`, com foto e restauração das tabelas e sequências. Resultados: IDENTICO / DIVERGE / INCONCLUSIVO / ABORTADO.
- `php -l` nos dois runtimes.
- Ambiente: `docker-compose*.yml`, proxy nginx :8090, laboratório Laravel 12 em :8087 (`ecidade_lar12`), login `dbseller`/`dbseller`.
- Medição prévia: 3.294 telas sobre o vendor do Laravel 12 idênticas ao 5.6, exceto 23 divergências preexistentes.

## 3. Goals

- Resultados reproduzíveis: mesma bateria rodada antes e depois da migração, mesmo veredito para o que não mudou.
- A bateria PHP reaproveita as ferramentas atuais, sem reescrevê-las.
- A bateria Laravel fica independente do sistema antigo: grava um **golden master** da baseline (Laravel 5.4) e o replica contra o Laravel 12, mesmo depois de o 5.4 ser desligado.
- Cada divergência aponta *onde* e *o quê* (diff), não só "falhou".
- Relatório único com contagens por área e lista de divergências, comparável entre rodadas (hashes por tela).

## 4. Non-goals

- Não corrigir defeitos existentes: **equivalente não é correto**. Se o sistema antigo calcula errado, o novo deve calcular igual.
- Não testar a lógica de negócio em si nem criar especificação.
- Não migrar nem alterar código de produção.
- Sem dados reais ou homologação: só o banco de desenvolvimento do Docker.

## 5. Anti-goals (falha mesmo que "passe")

- Teste que aprova por não ter exercitado nada (tela vazia, POST que não gravou). `INCONCLUSIVO` nunca conta como aprovado.
- Baseline gravada com o banco em estado diferente do da reexecução.
- Diferença escondida por normalização exagerada.
- Gravar a baseline com o sistema novo, ou misturar baseline de uma versão com resposta de outra.

## 6. Restrições

- **Só o banco de desenvolvimento Docker**, PostgreSQL 16, LATIN1. O conjunto de dados é pequeno e pode deixar telas e relatórios vazios; isso limita a cobertura. A bateria deve **medir e relatar** essa cobertura (telas que só rodam com tabela vazia), não escondê-la.
- Ambiente em WSL/Linux (nomes de arquivos que só diferem em caixa; ver README). Nome da pasta deve ser `e-cidade`.
- O 5.6 é a referência e **não pode cair**: o `vendor/` do Laravel 12 só vale no container 8.5 (montado por cima, mais `bootstrap/cache` e `storage/`).
- 64% dos arquivos em LATIN-1: nenhuma ferramenta pode converter encoding; usar `grep -a`.
- O login hoje só funciona no 5.6 (Passport/Laravel 5.4). O Laravel 12 ainda não inicializa (`BaseDeferredProvider::register()`); a bateria Laravel precisa produzir sua baseline **antes** disso e conseguir rodar em estado "não sobe" (falha clara, não timeout).
- Pacotes sem versão compatível (`silex/silex`, `dbseller/sdk-api-pix-bb`, `dbseller/phinx_postgres`, `proner/phppimaco`, `lcobucci/jwt`, `mpdf` 7, `phpspreadsheet` 1.8, `phpword` 0.17) vão mudar na migração; seus casos de teste devem existir *antes* da troca.
- Diretrizes do repo (`CLAUDE.md`): mudanças cirúrgicas, nada além do pedido, sem abstrações de uso único, objetivos verificáveis.

## 7. Abordagens consideradas

| | O que é | Prós | Contras |
|---|---|---|---|
| A. Só diferencial ao vivo | Mesmo pedido ao antigo e ao novo, comparar | Reusa 100% das ferramentas | Exige o antigo vivo e o banco igual; morre quando o 5.4 for desligado |
| B. Só golden master | Gravar tudo da baseline e comparar depois | Sobrevive ao desligamento; roda em CI | Exige banco congelado e normalização; descarta o que já funciona |
| **C. Híbrido (escolhida pelo usuário)** | PHP: diferencial ao vivo + hashes gravados. Laravel: golden master. Completa: orquestra e acrescenta navegador | Cada técnica onde rende mais | Manter duas técnicas |

Escolha: **C**, decidida pelo usuário.

## 8. Design

### 8.1 Princípios comuns

- **Estado do banco é parte do teste.** Um dump do banco de desenvolvimento (`baseline.dump`) é versionado por hash. Toda rodada restaura o dump antes de começar e compara os hashes das tabelas tocadas ao final. Rodada com banco diferente da baseline é rejeitada, não "falha".
- **Normalização declarada**: lista única, com um comentário por regra do motivo (cada regra nasceu de um falso positivo real). Um modo `--sem-normalizar` mostra o bruto.
- **Veredito por caso**: `IDENTICO`, `DIVERGE` (com diff), `INCONCLUSIVO` (nada exercitado), `ERRO_AMBIENTE` (serviço fora, timeout). Só `IDENTICO` aprova; `DIVERGE` preexistente conhecido vai para uma lista de exceções versionada (`conhecidas.tsv`) com motivo, e só nela.
- **Saída**: um diretório por rodada com `resultado.json`, `resumo.md`, os diffs e os hashes. Códigos de saída: 0 tudo aprovado, 1 divergência nova, 2 ambiente.

### 8.2 Bateria PHP (legado)

Baseia-se nas ferramentas existentes, sem reescrevê-las; acrescenta:

1. **Camada fina de execução** (`bateria-php`) que encadeia: `php -l` em todos os `*.php` alterados ou todos; `cmp.py` por prefixo de área (Tributário, Educação, Financeiro, Patrimonial, RH, Saúde, Configuração); `escrita.php` sobre as classes; `escrita_post.py` sobre uma lista de POSTs.
2. **Catálogo de POSTs** (`n3_rh_payloads.tsv` generalizado): um payload por tela de gravação priorizada. Priorização por área e por criticidade (cadastros centrais, lançamentos financeiros, arrecadação, folha). Meta inicial: cobrir ao menos as telas de inclusão/alteração/exclusão (`*001`, `*002`, `*003`) de cada módulo, lote a lote.
3. **GET com parâmetros** para relatórios e consultas (hoje só GET sem parâmetros): lista de casos (tela + query string) que exercitam relatórios PDF/XLS/DOC com dados do dump. Comparação de PDF/XLS por conteúdo extraído (texto e células), além de bytes, para tolerar metadados.
4. **Hashes gravados** por tela (SHA-256 do corpo normalizado) em `hashes_<rodada>.tsv`, para comparar rodada com rodada e mostrar que um lote novo não alterou o que já estava migrado.
5. **Relatório de cobertura**: quantas telas retornam conteúdo com dados vs tabela vazia; quantas não têm POST coberto.

### 8.3 Bateria Laravel

Golden master, independente do sistema antigo vivo após a gravação.

1. **Inventário de rotas** extraído do próprio código (`routes/api.php` e `routes/api/**`, `rest/v1`, `api/V1`): método, caminho, middleware (`auth:api`), controller. Gera a lista de casos; rota nova sem caso aparece como "não coberta".
2. **Autenticação**: fluxo `/v4/oauth/token` (password grant, `client_id`, `client_secret`) com usuário `dbseller`; casos de token inválido, expirado, ausente; refresh. O valor do token não é comparado (muda a cada vez); comparam-se status, formato e escopos.
3. **Casos por rota**: para cada rota, ao menos o caso feliz com parâmetros semeados no dump, e o caso de erro previsível (sem token, parâmetro faltando, id inexistente). Registrar: status, cabeçalhos relevantes, corpo JSON normalizado (ordem estável de chaves, campos voláteis mascarados: ids gerados, timestamps, tokens) e **efeito no banco** (SQL de negócio, como em `escrita_post.py`).
4. **Gravação da baseline** (`gravar`): roda contra o Laravel 5.4 (:8080) e guarda `baseline/laravel/<caso>.json` + hash; o dump do banco fica ao lado. **Replay** (`comparar`): roda contra o Laravel 12 (:8087 ou o runtime final) e compara. Os dois comandos usam o mesmo código de caso.
5. **Casos de integração** com dependências trocadas na migração: PIX Banco do Brasil (com o servidor do banco **simulado** por um stub local, para ser determinístico; compara o que a aplicação enviou e como tratou a resposta); geração de PDF (mpdf) e planilha (phpspreadsheet) comparados por conteúdo; envio de e-mail (PHPMailer) capturado por servidor SMTP de teste; `api/V1` Silex, incluindo a rota `post recibo`.
6. **Console** (`src/Console`, artisan): comandos executáveis comparados por saída e efeito no banco; os 21 com assinatura `execute()` a corrigir aparecem como falha de carga.

### 8.4 Bateria completa

1. Orquestrador (`bateria-completa`): restaura o dump, sobe/valida o ambiente (portas, containers, versões), roda PHP e Laravel, agrega os resultados.
2. **Fluxos de navegador (Playwright)**, poucos e críticos, via proxy :8090: login → abrir módulo → abrir tela → incluir/alterar um registro → emitir um relatório → sair. Comparação por DOM normalizado e pelo estado do banco. Capturam o que as outras baterias não veem: JavaScript, sessão entre PHP 5.6 e 8.5, redirecionamentos do proxy, cabeçalhos `X-Ecidade-Runtime`.
3. **Relatório único** (`relatorio.md` e `.json`): totais por área, divergências novas vs conhecidas, cobertura, hash da baseline, versões (PHP, Laravel, Postgres, commit).
4. Comparação entre rodadas: "antes" vs "depois" da migração lado a lado, mostrando o que mudou de veredito.

### 8.5 Onde vive no repositório

Em `scratchpad/` já ficam as ferramentas; as baterias novas entram em um diretório próprio (proposta: `regressao/` com `php/`, `laravel/`, `completa/`, `baseline/`, `conhecidas.tsv`), reaproveitando os scripts de `scratchpad/` por chamada, sem movê-los.

## 9. Decisões do usuário

- Três baterias: completa, Laravel e PHP.
- Abordagem **C** (híbrida).
- Só o banco de desenvolvimento do Docker; sem homologação.

## 10. Calls minhas (a conferir)

- Playwright para os fluxos de navegador (o repo tem Cypress configurado, sem testes; Playwright evita depender de configuração antiga). Pode trocar por Cypress.
- Stub local para o PIX e SMTP de teste, para determinismo.
- Diretório `regressao/` na raiz e lista de exceções `conhecidas.tsv`.
- Prioridade de cobertura de POSTs por criticidade, começando por cadastros centrais, financeiro, arrecadação e folha.
- Comparar PDF/XLS por conteúdo extraído, não só por bytes.

### Respostas da revisão (decididas sem o usuário)

- **Baseline do Laravel 5.4 e Passport (já respondido pelo repo):** o :8080 expõe `/v4/oauth/token` com `client_id=9999999` e `client_secret` em `ecidade/config/application.php`; o login `dbseller`/`dbseller` existe no dump. Primeiro marco: obter um token no :8080 e gravar um caso. Se o cliente Passport não existir no dump, a bateria o semeia e o seed entra no `baseline.dump`.
- **Estado do banco entre casos (minha call):** casos rodam em ordem fixa e igual em `gravar` e `comparar`, sobre um único banco restaurado. Casos com escrita usam foto e restauração das tabelas tocadas, como `escrita_post.py`. Dependências (criar e depois ler) ficam no mesmo caso, em sequência. Sem paralelismo na v1.
- **Escala e critério de cobertura (minha call):** o construtor mede o número de rotas e telas de gravação logo no início e o registra no relatório. O primeiro lote é um ponto de partida, não um portão. Rota ou tela sem caso aparece como "não coberta" no relatório e não reprova a rodada.
- **Códigos de saída e `INCONCLUSIVO` (minha call):** 0 = nenhum `DIVERGE` e nenhum `ERRO_AMBIENTE`; 1 = alguma divergência nova; 2 = ambiente. `INCONCLUSIVO` não conta como aprovado: é contado à parte na cobertura e, sozinho, não torna a rodada vermelha. Isso evita uma bateria permanentemente reprovada por causa das tabelas vazias do banco de desenvolvimento. O banco não é enriquecido na v1.
- **Alvos de execução (resposta do repo):** bateria PHP compara :8080 (5.6) com :8085 (8.5, vendor do 5.4). Bateria Laravel grava no :8080 e compara no :8087 (Laravel 12). O alvo "novo" é configurável por variável de ambiente, para apontar depois ao runtime final.
- **Determinismo (minha call):** campos voláteis mascarados por rota; ordenação estável de listas sem `ORDER BY` só quando comprovadamente sem ordem definida; chamadas externas sempre simuladas. Congelar o relógio só se aparecer um caso real.
- **Dependências de ferramenta (minha call):** tudo mora em `regressao/` com seu próprio compose (`regressao/docker-compose.yml`) para Playwright, stub do PIX e SMTP de teste. Nenhum `docker-compose*.yml` existente é alterado.

## 11. Deixado ao construtor

- Escolha exata das telas de POST e relatórios do primeiro lote e a ordem dos lotes.
- Formato interno dos arquivos de baseline e do `resultado.json`.
- Mecanismo exato de mascaramento de campos voláteis por rota.
- Se `regressao/` usa Python puro ou um runner (pytest) para os casos Laravel.
- Como lidar com o Laravel 12 que ainda não sobe: provavelmente a bateria Laravel só fica verde depois do primeiro boot; antes disso devolve `ERRO_AMBIENTE` claro.
