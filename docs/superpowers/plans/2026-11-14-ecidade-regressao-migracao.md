# Bateria de regressão da migração do e-cidade: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar três baterias de regressão (PHP, Laravel, completa) que provem que o e-cidade migrado responde igual ao de antes.

**Architecture:** Um pacote Python `regressao/` na raiz do repositório e-cidade. Um núcleo comum (vereditos, normalização, banco, ambiente, relatório) alimenta a bateria PHP (envolve as ferramentas de `scratchpad/`: diferencial ao vivo 5.6 × 8.5), a bateria Laravel (golden master gravado no 5.4 e reexecutado no Laravel 12) e a bateria completa (orquestrador mais fluxos de navegador).

**Tech Stack:** Python 3 + pytest, `requests`, `pyyaml`, `playwright` (Python), Docker/`docker exec`, PostgreSQL 16 (`psql`, `pg_dump`), WSL/Linux.

**Spec:** `docs/superpowers/specs/2026-11-14-ecidade-regressao-migracao-design.md` (cópia na pasta Infosousa; mova para o repo e-cidade junto com este plano).

## Global Constraints

- Branch `base-php84`; o repositório deve estar numa pasta chamada `e-cidade`, em WSL/Linux. Trabalhar numa branch `regressao`.
- Portas: `:8080` PHP 5.6 + Laravel 5.4 (referência, **não pode cair**; `docker-compose.yml` dele não se altera); `:8085` PHP 8.5; `:8087` `ecidade_lar12` (Laravel 12); `:8090` proxy nginx. Login `dbseller`/`dbseller`; Passport `client_id=9999999`, `client_secret` em `ecidade/config/application.php`.
- Banco: só o PostgreSQL 16 de desenvolvimento do Docker (`ecidade_database`, banco `ecidade`, LATIN1). Sem homologação.
- Vereditos: `IDENTICO`, `DIVERGE`, `INCONCLUSIVO`, `ERRO_AMBIENTE`. Só `IDENTICO` aprova. Saída: 0 = nenhum `DIVERGE` novo e nenhum `ERRO_AMBIENTE`; 1 = divergência nova; 2 = ambiente. `INCONCLUSIVO` é contado à parte e sozinho não vermelha a rodada.
- Equivalente não é correto: nunca corrigir defeito preexistente. Divergência preexistente só vai em `regressao/conhecidas.tsv`, com motivo.
- Arquivos em LATIN-1: toda comparação e todo hash operam sobre `bytes`, nunca decodificam como UTF-8; usar `grep -a`.
- Não alterar nenhum `docker-compose*.yml` existente nem código de produção. Ferramentas extras (Playwright, stub PIX, SMTP) ficam em `regressao/docker-compose.yml`.
- Casos rodam em ordem fixa, sem paralelismo; mesma ordem em `gravar` e `comparar`.
- Reaproveitar `scratchpad/cmp.py`, `escrita.php`, `porclasse.sh`, `escrita_post.py` por chamada; não movê-los nem reescrevê-los.
- Mudanças cirúrgicas, sem abstração de uso único (`CLAUDE.md` do repo).

## Review Focus

1. Dump restaurado com hash diferente do registrado: a rodada é **rejeitada** (`ERRO_AMBIENTE`), nunca vira `DIVERGE`. Teste na Task 2.
2. Resposta vazia nos dois lados, ou POST que não gravou nada: `INCONCLUSIVO`, nunca `IDENTICO`. Testes nas Tasks 5 e 6.
3. Bytes LATIN-1 (`b"\xe7\xe3o"`) no corpo: normalização e hash não podem lançar nem alterar. Teste na Task 1.
4. Laravel 12 que não sobe (500 no boot ou timeout): um único `ERRO_AMBIENTE` de ambiente, não centenas de `DIVERGE` por rota. Teste na Task 9.
5. Rota protegida sem token, com token inválido ou expirado: o caso de erro é gravado e comparado como qualquer outro (status 401 igual nos dois lados). Teste na Task 10.
6. Volátil mascarado em excesso: `--sem-normalizar` existe e mostra a diferença bruta. Teste na Task 1.

---

## File Structure

```
regressao/
  README.md
  conftest.py
  conhecidas.tsv
  docker-compose.yml            # Playwright, stub PIX, SMTP de teste
  nucleo/{veredito,normaliza,conhecidas,banco,ambiente,relatorio}.py
  php/{sintaxe,telas,classes,posts,relatorios,hashes,cobertura,bateria}.py
  php/catalogo_posts.tsv  php/catalogo_relatorios.tsv
  laravel/{rotas,token,mascara,caso,integracao,bateria}.py
  laravel/stubs/{pix_stub,smtp_stub}.py
  laravel/casos/*.yml
  completa/{orquestra,fluxos}.py
  baseline/{baseline.dump.sha256,laravel/,hashes/}
  tests/                         # pytest do próprio pacote (unidade, sem docker)
```

Cada módulo tem uma responsabilidade. Testes de unidade em `regressao/tests/` rodam sem Docker; verificações de integração rodam contra o ambiente e estão descritas nos passos.

---

### Task 1: Núcleo: vereditos, normalização, exceções conhecidas

**Files:**
- Create: `regressao/nucleo/veredito.py`, `regressao/nucleo/normaliza.py`, `regressao/nucleo/conhecidas.py`, `regressao/conhecidas.tsv`
- Test: `regressao/tests/test_nucleo.py`

**Interfaces:**
- Produces:
  - `class Veredito(str, Enum)` com `IDENTICO, DIVERGE, INCONCLUSIVO, ERRO_AMBIENTE`.
  - `@dataclass class Caso: id: str; area: str; veredito: Veredito; detalhe: str = ""; diff: str = ""; conhecida: bool = False`.
  - `codigo_saida(casos: list[Caso]) -> int` (regra de saída dos Global Constraints; `conhecida=True` não conta como nova).
  - `REGRAS: list[tuple[str, re.Pattern[bytes], bytes]]` (motivo, padrão, marcador), com `sid=X`, `tmp/X.pdf`, `/DateX`, trocados nos dois lados.
  - `normaliza(corpo: bytes, regras=REGRAS) -> bytes`; `hash_corpo(corpo: bytes, regras=REGRAS) -> str` (sha256 hex do normalizado).
  - `carregar_conhecidas(caminho: Path) -> dict[str, str]` (id → motivo; TSV de duas colunas); `marcar(casos, conhecidas) -> list[Caso]` seta `conhecida=True` em `DIVERGE` cujo id está na lista.

- [ ] **Step 1: Write the failing tests** em `test_nucleo.py`: `test_codigo_saida_zero_sem_divergencia_nova` (IDENTICO + INCONCLUSIVO → 0), `test_codigo_saida_um_com_diverge_novo` (→ 1), `test_codigo_saida_ignora_diverge_conhecida` (→ 0), `test_codigo_saida_dois_com_erro_ambiente` (→ 2, tem precedência sobre 1), `test_normaliza_troca_sid_nos_dois_lados` (`b"x?sid=abc123"` e `b"x?sid=zzz999"` normalizam iguais), `test_normaliza_nao_decodifica_latin1` (`normaliza(b"a\xe7\xe3o") == b"a\xe7\xe3o"`), `test_hash_estavel_e_sensivel_a_um_byte`, `test_marcar_so_marca_diverge_listada`.
- [ ] **Step 2:** Run `pytest regressao/tests/test_nucleo.py -v`. Expected: FAIL (módulos inexistentes).
- [ ] **Step 3:** Implementar os três módulos conforme Interfaces. Cada regra de `REGRAS` leva um comentário com o motivo (falso positivo real que a motivou; a lista inicial vem do cabeçalho de `scratchpad/cmp.py`). Aceitar `--sem-normalizar` expondo `REGRAS = []` via parâmetro `regras`.
- [ ] **Step 4:** Run o mesmo comando. Expected: PASS.
- [ ] **Step 5: Commit** `git add regressao && git commit -m "feat(regressao): núcleo de vereditos e normalização"`.

---

### Task 2: Núcleo: banco, dump baseline, ambiente

**Files:**
- Create: `regressao/nucleo/banco.py`, `regressao/nucleo/ambiente.py`, `regressao/baseline/baseline.dump.sha256`
- Test: `regressao/tests/test_banco_ambiente.py`

**Interfaces:**
- Consumes: `Caso`, `Veredito` (Task 1).
- Produces:
  - `class BancoDiferente(Exception)`.
  - `gera_dump(destino: Path) -> str` (`docker exec ecidade_database pg_dump -Fc ecidade`; retorna sha256 do arquivo e grava em `baseline.dump.sha256`).
  - `restaura_dump(dump: Path) -> None` e `confere_baseline(dump: Path) -> None` (levanta `BancoDiferente` se o sha256 do dump ≠ registrado).
  - `hash_tabelas(tabelas: list[str]) -> dict[str, str]` (md5 de `select * from <t> order by 1` via `psql`).
  - `@dataclass class Alvos: ref: str; php_novo: str; laravel_novo: str; proxy: str`; `alvos_do_ambiente() -> Alvos` lê `REGRESSAO_REF_URL` (padrão `http://localhost:8080`), `REGRESSAO_PHP_NOVO_URL` (`http://localhost:8085`), `REGRESSAO_LARAVEL_NOVO_URL` (`http://localhost:8087`), `REGRESSAO_PROXY_URL` (`http://localhost:8090`).
  - `verifica(alvos: Alvos) -> list[str]` (problemas encontrados: URL sem resposta em 5 s, container ausente em `docker ps`; lista vazia se saudável).

- [ ] **Step 1: Write the failing tests:** `test_confere_baseline_rejeita_dump_alterado` (dump temporário com hash diferente do registrado → `BancoDiferente`), `test_alvos_usam_variaveis_de_ambiente` (monkeypatch), `test_verifica_reporta_alvo_fora` (porta fechada → mensagem cita a URL). Os dois primeiros sem Docker.
- [ ] **Step 2:** Run `pytest regressao/tests/test_banco_ambiente.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implementar. `restaura_dump` usa `pg_restore --clean --if-exists` no container. Um `BancoDiferente` ou `verifica` não vazio é convertido pelos orquestradores em um `Caso` `ERRO_AMBIENTE` (Task 9 e 11).
- [ ] **Step 4:** Run os testes. Expected: PASS.
- [ ] **Step 5:** No ambiente real: subir os containers (comandos do `CLAUDE.md`), rodar `gera_dump` e commitar apenas o `.sha256` (o dump em si fica fora do git, em `regressao/baseline/baseline.dump`, listado no `.gitignore` do pacote). Verificar com `python -c "from regressao.nucleo import banco; print(banco.confere_baseline(...))"`. Expected: sem exceção.
- [ ] **Step 6: Commit** `feat(regressao): banco, dump baseline e alvos`.

---

### Task 3: Núcleo: relatório e comparação entre rodadas

**Files:**
- Create: `regressao/nucleo/relatorio.py`
- Test: `regressao/tests/test_relatorio.py`

**Interfaces:**
- Consumes: `Caso`, `codigo_saida` (Task 1).
- Produces:
  - `escreve_rodada(diretorio: Path, casos: list[Caso], meta: dict) -> None` grava `resultado.json` (casos + meta: versões PHP/Laravel/Postgres, commit, hash do dump), `resumo.md` (totais por `area` e por veredito, divergências novas e conhecidas, `INCONCLUSIVO`) e `diffs/<id>.diff`.
  - `compara_rodadas(antes: Path, depois: Path) -> list[tuple[str, Veredito, Veredito]]` (id, veredito antes, veredito depois, só os que mudaram).

- [ ] **Step 1: Write the failing tests:** `test_resumo_conta_por_area_e_veredito`, `test_diff_vai_para_arquivo_do_caso`, `test_compara_rodadas_lista_so_o_que_mudou` (caso A `IDENTICO`→`DIVERGE`, caso B inalterado → só A).
- [ ] **Step 2:** Run `pytest regressao/tests/test_relatorio.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implementar com `json` e Markdown simples. `meta` é preenchido pelo chamador.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `feat(regressao): relatório de rodada`.

---

### Task 4: Bateria PHP: sintaxe e classes de dados

**Files:**
- Create: `regressao/php/sintaxe.py`, `regressao/php/classes.py`
- Test: `regressao/tests/test_php_parsers.py`

**Interfaces:**
- Consumes: `Caso`, `Veredito`.
- Produces:
  - `roda_lint(arquivos: list[str]) -> list[Caso]`: `php -l` em `ecidade_php56` e `ecidade_php85` (com `</dev/null`); `IDENTICO` se ambos compilam, `DIVERGE` se só um falha (detalhe traz a mensagem).
  - `compara_classes(saida56: str, saida85: str) -> list[Caso]`: uma linha `classe campo=valor` por campo; `DIVERGE` por classe com campo diferente; classe sem saída nos dois lados → `INCONCLUSIVO`.
  - `roda_classes(lista: list[str]) -> list[Caso]`: copia `escrita.php` e `porclasse.sh` para `ecidade/tmp/`, executa em cada container e chama `compara_classes`.

- [ ] **Step 1: Write the failing tests** (puros, sobre texto): `test_compara_classes_iguais_sao_identicas`, `test_compara_classes_detecta_zero_vs_valor` (`z01_numcgm='1012'` × `z01_numcgm=0` → `DIVERGE`), `test_compara_classes_sem_saida_nos_dois_lados_e_inconclusiva`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar os parsers e as chamadas `docker exec`.
- [ ] **Step 4:** Run os testes. Expected: PASS. Verificação de integração: `roda_classes(["classes/db_cgm_classe.php"])` no ambiente deve retornar um `Caso` `IDENTICO`.
- [ ] **Step 5: Commit** `feat(regressao): bateria PHP, sintaxe e classes`.

---

### Task 5: Bateria PHP: telas (GET) com hashes e cobertura

**Files:**
- Create: `regressao/php/telas.py`, `regressao/php/hashes.py`, `regressao/php/cobertura.py`
- Test: `regressao/tests/test_php_telas.py`

**Interfaces:**
- Consumes: `Caso`, `hash_corpo`.
- Produces:
  - `parse_cmp(saida: str, area: str) -> list[Caso]`: lê o formato de `cmp.py` (`DIVERGE <tela>  56=200/18668B  85=500/4558B` e o resumo `=== N/M identicas, X divergentes, Y timeout ===`). Divergentes → `DIVERGE`; timeout → `ERRO_AMBIENTE`; as demais telas → `IDENTICO`, exceto resposta de 0 bytes nos dois lados → `INCONCLUSIVO`.
  - `roda_telas(sid: str, prefixo: str, area: str) -> list[Caso]`: executa `python3 scratchpad/cmp.py <sid> <prefixo>`.
  - `grava_hashes(diretorio: Path, tela_para_corpo: dict[str, bytes]) -> Path` escreve `hashes_<rodada>.tsv` (tela, sha256 do corpo normalizado); `compara_hashes(a: Path, b: Path) -> list[str]` devolve as telas cujo hash mudou.
  - `cobertura_telas(casos: list[Caso], corpos: dict[str, bytes]) -> dict` com `com_dados` e `tabela_vazia`, considerando vazia a tela sem nenhuma linha de dados detectável (heurística fixa: corpo sem `<td` fora do cabeçalho).

- [ ] **Step 1: Write the failing tests:** `test_parse_cmp_divergente_vira_diverge` com a linha de exemplo do `como-testamos.md`, `test_parse_cmp_timeout_nao_conta_como_igual`, `test_resposta_vazia_nos_dois_lados_e_inconclusiva`, `test_compara_hashes_lista_telas_alteradas`.
- [ ] **Step 2:** Run `pytest regressao/tests/test_php_telas.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implementar. O SID vem de `docker exec ecidade_php56 sh -c 'ls -t $(grep -la DB_modulo /var/lib/php/sessions/sess_*) | head -1'` (função `obtem_sid()` no mesmo módulo).
- [ ] **Step 4:** Run. Expected: PASS. Integração: `roda_telas(obtem_sid(), "^cem[0-9]*_", "configuracao")` deve reproduzir o resumo do `cmp.py` direto.
- [ ] **Step 5: Commit** `feat(regressao): bateria PHP, telas e hashes`.

---

### Task 6: Bateria PHP: POST real e catálogo

**Files:**
- Create: `regressao/php/posts.py`, `regressao/php/catalogo_posts.tsv`
- Test: `regressao/tests/test_php_posts.py`

**Interfaces:**
- Consumes: `Caso`, `Veredito`.
- Produces:
  - `@dataclass class PostCaso: tela: str; tabelas: list[str]; campos: str; area: str` (TSV com colunas `tela, tabelas(,), campos, area`; `tabelas` com as filhas **antes** da mãe).
  - `carrega_catalogo(tsv: Path) -> list[PostCaso]`.
  - `parse_post(saida: str, caso: PostCaso) -> Caso`: mapeia `SQL de escrita de NEGOCIO IDENTICO` → `IDENTICO`, `DIVERGE` → `DIVERGE`, `INCONCLUSIVO` → `INCONCLUSIVO`, `ABORTADO` → `ERRO_AMBIENTE` (com a tabela a acrescentar no detalhe).
  - `roda_post(sid: str, caso: PostCaso) -> Caso`: liga `log_statement='all'`, executa `python3 scratchpad/escrita_post.py`, e **sempre** desliga (`RESET`) em `finally`.

- [ ] **Step 1: Write the failing tests:** `test_parse_post_identico`, `test_parse_post_inconclusivo_nao_aprova`, `test_parse_post_abortado_vira_erro_ambiente`, `test_catalogo_ordena_filhas_antes_da_mae` (valida que o TSV carregado mantém a ordem declarada), `test_log_statement_e_resetado_mesmo_com_falha` (mock do subprocesso que falha).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar. Semear `catalogo_posts.tsv` com o conteúdo de `scratchpad/n3_rh_payloads.tsv` convertido ao formato e **mais** um caso por módulo central (CGM, Orçamento, Arrecadação, Folha) incluindo `*001/002/003`; cada caso novo só entra no catálogo depois de dar `IDENTICO` (não `INCONCLUSIVO`) no ambiente.
- [ ] **Step 4:** Run. Expected: PASS. Integração: a tela de exemplo do `como-testamos.md` (`assenta`/`assentamentofuncional`) → `IDENTICO`.
- [ ] **Step 5: Commit** `feat(regressao): bateria PHP, POST real e catálogo`.

---

### Task 7: Bateria PHP: relatórios e GET com parâmetros

**Files:**
- Create: `regressao/php/relatorios.py`, `regressao/php/catalogo_relatorios.tsv`
- Test: `regressao/tests/test_php_relatorios.py`

**Interfaces:**
- Consumes: `normaliza`, `Caso`.
- Produces:
  - `@dataclass class RelCaso: tela: str; query: str; tipo: str  # "html"|"pdf"|"xls"|"doc"; area: str`.
  - `extrai_conteudo(corpo: bytes, tipo: str) -> str`: PDF → texto (`pdftotext -layout`, no container ou local); XLS/XLSX → `sheet|linha|coluna|valor` por célula; HTML/DOC → `normaliza(corpo)` decodificado em `latin-1`.
  - `compara_relatorio(corpo56: bytes, corpo85: bytes, caso: RelCaso) -> Caso`: `IDENTICO` se o conteúdo extraído é igual (mesmo se os bytes diferem por metadados); `INCONCLUSIVO` se ambos são vazios ou sem células de dados; `DIVERGE` com `diff` unificado caso contrário.
  - `roda_relatorio(sid: str, caso: RelCaso) -> Caso`: GET com a query nos dois runtimes, sessão restaurada antes de cada um.

- [ ] **Step 1: Write the failing tests:** `test_pdf_com_metadado_diferente_e_identico_pelo_conteudo` (dois PDFs de teste em `tests/fixtures/` com `/CreationDate` distinto e o mesmo texto), `test_xls_celula_diferente_diverge`, `test_relatorio_vazio_e_inconclusivo`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar. Semear o catálogo com ao menos um relatório PDF, um XLS e uma consulta HTML por área que retornem dados no dump.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `feat(regressao): bateria PHP, relatórios por conteúdo`.

---

### Task 8: Bateria PHP: orquestração

**Files:**
- Create: `regressao/php/bateria.py`
- Test: `regressao/tests/test_php_bateria.py`

**Interfaces:**
- Consumes: tudo das Tasks 1 a 7.
- Produces: `roda_bateria_php(diretorio_saida: Path, areas: list[str] | None = None) -> int` (código de saída). Fluxo: `verifica(alvos)` → `confere_baseline` → `restaura_dump` → sintaxe → classes → telas por prefixo de área → POSTs → relatórios → `marcar` com `conhecidas.tsv` → `escreve_rodada` → `codigo_saida`. CLI: `python -m regressao.php.bateria --saida DIR [--area tributario ...] [--sem-normalizar]`.

- [ ] **Step 1: Write the failing tests** (com os módulos das etapas anteriores substituídos por dublês): `test_ambiente_fora_gera_erro_ambiente_e_codigo_2`, `test_banco_diferente_rejeita_rodada` (levanta `BancoDiferente` → `ERRO_AMBIENTE`, nenhum teste executado), `test_diverge_conhecida_nao_quebra_rodada`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar, usando `areas` ↔ prefixos de `scratchpad/prefixos_area.py`.
- [ ] **Step 4:** Run. Expected: PASS. Integração: rodar a bateria numa área pequena (`--area configuracao`) e verificar `resumo.md`; registrar no `conhecidas.tsv` as 23 divergências preexistentes já documentadas, cada uma com motivo, **só depois** de conferir que são as mesmas.
- [ ] **Step 5: Commit** `feat(regressao): orquestrador da bateria PHP`.

---

### Task 9: Bateria Laravel: inventário, token, máscara

**Files:**
- Create: `regressao/laravel/rotas.py`, `regressao/laravel/token.py`, `regressao/laravel/mascara.py`
- Test: `regressao/tests/test_laravel_base.py`

**Interfaces:**
- Consumes: `Caso`, `Alvos`.
- Produces:
  - `@dataclass class Rota: metodo: str; caminho: str; middleware: list[str]; controller: str; origem: str  # "laravel"|"rest"|"silex"`.
  - `inventario(raiz: Path) -> list[Rota]`: Laravel via `docker exec ecidade_php56 php artisan route:list` (parse da tabela do 5.4); Silex via varredura de `api/V1` por `$app->(get|post|put|delete)(...)`; arquivo único `regressao/laravel/casos/_inventario.tsv`.
  - `obtem_token(base_url: str, usuario="dbseller", senha="dbseller") -> str` (POST `/v4/oauth/token`, `grant_type=password`, `client_id=9999999`, secret lido de `ecidade/config/application.php`).
  - `mascara_json(obj, campos_volateis: list[str]) -> object`: troca os valores dos campos listados (caminho com ponto, `*` para listas) por `"<X>"`, ordena chaves, preserva o resto.
  - `laravel_sobe(base_url: str) -> Caso | None`: `GET <base>/v4/oauth/token` fora do ar ou 5xx de boot → `Caso` `ERRO_AMBIENTE` único com a mensagem de `php_errors.log`; `None` se sobe.

- [ ] **Step 1: Write the failing tests:** `test_mascara_troca_volateis_e_ordena_chaves`, `test_mascara_lista_com_asterisco`, `test_inventario_parseia_tabela_route_list` (fixture de texto), `test_laravel_que_nao_sobe_e_um_so_erro_ambiente` (servidor falso devolvendo 500 → um `Caso` único `ERRO_AMBIENTE`).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar. A contagem de rotas e telas de gravação é impressa no início do inventário e vai no `resumo.md` (limite de cobertura da v1).
- [ ] **Step 4:** Run. Expected: PASS. Integração: `obtem_token("http://localhost:8080")` retorna um token; se o cliente Passport não existir no dump, semeá-lo (script SQL em `regressao/baseline/seed_passport.sql`) e regerar o dump (Task 2, passo 5).
- [ ] **Step 5: Commit** `feat(regressao): Laravel, inventário, token e máscara`.

---

### Task 10: Bateria Laravel: casos, gravar e comparar

**Files:**
- Create: `regressao/laravel/caso.py`, `regressao/laravel/casos/auth.yml`, `regressao/laravel/casos/<modulo>.yml`
- Test: `regressao/tests/test_laravel_caso.py`

**Interfaces:**
- Consumes: `Rota`, `obtem_token`, `mascara_json`, `hash_tabelas`, `Caso`.
- Produces:
  - `@dataclass class CasoHttp: id: str; metodo: str; caminho: str; corpo: dict | None; autenticado: bool = True; token: str | None = None  # None = usar o válido; "" = ausente; outro = inválido; campos_volateis: list[str] = []; tabelas: list[str] = []`.
  - `@dataclass class Resposta: status: int; cabecalhos: dict[str, str]; json: object; sql_negocio: list[str]`.
  - `carrega_casos(diretorio: Path) -> list[CasoHttp]` (YAML, ordem do arquivo; ordem dos arquivos alfabética).
  - `executa(caso: CasoHttp, base_url: str, token: str) -> Resposta`: captura o SQL de negócio com a técnica do `escrita_post.py` e restaura as `tabelas` do caso depois.
  - `gravar(casos, base_url: str, diretorio: Path) -> None`: grava `baseline/laravel/<id>.json` (status, cabeçalhos relevantes, json mascarado, sql_negocio, hash).
  - `comparar(casos, base_url: str, diretorio: Path) -> list[Caso]`: `laravel_sobe` primeiro (se `ERRO_AMBIENTE`, devolve **só** ele); depois um `Caso` por caso HTTP: status/JSON/SQL iguais → `IDENTICO`; senão `DIVERGE` com diff; sem arquivo de baseline → `ERRO_AMBIENTE`.

- [ ] **Step 1: Write the failing tests:** `test_gravar_e_comparar_mesma_resposta_e_identico`, `test_comparar_json_diferente_diverge_com_diff`, `test_sem_token_e_401_gravado_e_comparado` (`token=""`; ambos os lados 401 → `IDENTICO`), `test_token_invalido_e_401`, `test_baseline_ausente_e_erro_ambiente`, `test_resposta_vazia_nos_dois_lados_e_inconclusiva`. Todos com um servidor HTTP falso local.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar. `auth.yml`: token válido (campos `token_type`, `expires_in`, `access_token` mascarado), senha errada, `client_secret` errado, refresh, rota protegida sem token, com token inválido e com token expirado (forçado alterando `expires_at` em `oauth_access_tokens` dentro do caso).
- [ ] **Step 4:** Run. Expected: PASS. Integração: `gravar` dos casos `auth.yml` contra `:8080`, depois `comparar` contra `:8080` mesmo. Expected: todos `IDENTICO` (estabilidade da própria baseline).
- [ ] **Step 5: Commit** `feat(regressao): Laravel, casos gravar e comparar`.

---

### Task 11: Bateria Laravel: casos por rota e integrações

**Files:**
- Create: `regressao/laravel/casos/<modulo>.yml` (um por módulo do inventário), `regressao/laravel/integracao.py`, `regressao/laravel/stubs/pix_stub.py`, `regressao/laravel/stubs/smtp_stub.py`, `regressao/docker-compose.yml`
- Test: `regressao/tests/test_laravel_integracao.py`

**Interfaces:**
- Consumes: `CasoHttp`, `gravar`, `comparar`, `extrai_conteudo` (Task 7).
- Produces:
  - Para cada rota do inventário: um caso feliz (parâmetros semeados no dump) e um caso de erro previsível (parâmetro faltando ou id inexistente). Rota sem caso fica listada como "não coberta" no relatório e não reprova.
  - `pix_stub.py`: servidor HTTP local que responde às chamadas do `dbseller/sdk-api-pix-bb` com respostas fixas e registra o que a aplicação enviou; `caso_pix() -> CasoHttp` aponta a aplicação ao stub e compara o enviado e a reação.
  - `smtp_stub.py`: servidor SMTP de teste que guarda as mensagens; `compara_email(msg56: bytes, msg_novo: bytes) -> Caso` normaliza `Date`, `Message-ID` e fronteiras MIME.
  - `casos_pdf_xls(...) -> list[CasoHttp]` com comparação por `extrai_conteudo` (mpdf e phpspreadsheet).
  - `casos_console() -> list[CasoHttp]`: executa comandos `artisan` selecionados e compara saída e efeito no banco; comando que não carrega no Laravel 12 → `DIVERGE` com a mensagem de carga.

- [ ] **Step 1: Write the failing tests:** `test_stub_pix_registra_chamada_recebida`, `test_email_normaliza_date_e_message_id`, `test_rota_sem_caso_aparece_como_nao_coberta`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar. `regressao/docker-compose.yml` define os serviços do stub PIX, SMTP e Playwright em rede própria, **sem** tocar nos compose existentes. Cobrir `api/V1` (Silex), incluindo `post recibo`.
- [ ] **Step 4:** Run. Expected: PASS. Integração: `gravar` de tudo no `:8080`; `comparar` contra `:8080` → todos `IDENTICO`.
- [ ] **Step 5: Commit** `feat(regressao): Laravel, casos por rota e integrações`.

---

### Task 12: Bateria Laravel: orquestração

**Files:**
- Create: `regressao/laravel/bateria.py`
- Test: `regressao/tests/test_laravel_bateria.py`

**Interfaces:**
- Consumes: Tasks 9 a 11 e o núcleo.
- Produces: `roda_bateria_laravel(diretorio_saida: Path, modo: str) -> int` com `modo` em `"gravar"` ou `"comparar"`. `gravar` roda contra `Alvos.ref` (:8080); `comparar` roda contra `Alvos.laravel_novo` (:8087 ou valor de `REGRESSAO_LARAVEL_NOVO_URL`). Mesmo fluxo de ambiente e banco da Task 8. CLI: `python -m regressao.laravel.bateria gravar|comparar --saida DIR`.

- [ ] **Step 1: Write the failing tests:** `test_modo_invalido_levanta_erro`, `test_comparar_com_laravel_fora_devolve_um_unico_erro_ambiente_e_codigo_2`, `test_gravar_nao_altera_baseline_quando_ambiente_falha`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Run. Expected: PASS. Integração: `gravar` da baseline completa e commit de `regressao/baseline/laravel/`. Com o Laravel 12 ainda sem subir, `comparar` deve terminar com código 2 e uma única linha `ERRO_AMBIENTE`.
- [ ] **Step 5: Commit** `feat(regressao): orquestrador da bateria Laravel`.

---

### Task 13: Bateria completa: orquestrador, fluxos de navegador, comparação antes/depois

**Files:**
- Create: `regressao/completa/orquestra.py`, `regressao/completa/fluxos.py`, `regressao/README.md`
- Test: `regressao/tests/test_completa.py`

**Interfaces:**
- Consumes: `roda_bateria_php`, `roda_bateria_laravel`, `escreve_rodada`, `compara_rodadas`.
- Produces:
  - `roda_fluxos(proxy_url: str) -> list[Caso]`: Playwright via `:8090`, fluxo login → abrir módulo → abrir tela → incluir/alterar um registro → emitir relatório → sair. Compara DOM normalizado (`normaliza`) e estado do banco; confere o cabeçalho `X-Ecidade-Runtime`.
  - `roda_completa(diretorio_saida: Path) -> int`: restaura o dump; valida o ambiente; roda PHP, Laravel (modo `comparar`) e fluxos; agrega em `relatorio.md`/`.json` (totais por área, divergências novas × conhecidas, cobertura, hash da baseline, versões, commit); código de saída conforme Global Constraints. CLI: `python -m regressao.completa.orquestra --saida DIR` e `--comparar ANTES DEPOIS` (usa `compara_rodadas`).
  - `README.md`: como subir o ambiente, gerar o dump, `gravar`, rodar cada bateria, interpretar os vereditos, e como adicionar um caso.

- [ ] **Step 1: Write the failing tests:** `test_agrega_resultados_das_tres_frentes`, `test_codigo_de_saida_pega_o_pior_das_frentes` (PHP 0, Laravel 2 → 2), `test_flag_comparar_lista_mudancas_de_veredito`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar. Fluxos de navegador mínimos: um por área crítica (cadastros, financeiro, tributário). O que o navegador vê e o PHP/Laravel não: JS, sessão compartilhada, redirecionamentos do proxy.
- [ ] **Step 4:** Run. Expected: PASS. Integração (passo final do plano): rodar `roda_completa` **antes** da migração, guardar a pasta de saída como "antes"; conferir que `resumo.md` traz contagens por área, a cobertura e o hash do dump.
- [ ] **Step 5: Commit** `feat(regressao): bateria completa e README`.

---

## Self-Review

- **Cobertura da spec:** núcleo comum (8.1) → Tasks 1–3; bateria PHP (8.2: orquestração, catálogo de POSTs, GET com parâmetros e relatórios por conteúdo, hashes, cobertura) → Tasks 4–8; bateria Laravel (8.3: inventário, token, casos por rota, gravar/comparar, integrações PIX/PDF/e-mail/Silex/console) → Tasks 9–12; completa (8.4: orquestrador, navegador, relatório único, antes/depois) → Task 13; local no repo (8.5) → File Structure. Respostas da revisão: baseline e Passport (Task 9 passo 4), estado do banco e ordem fixa (Global Constraints, Task 10), escala e cobertura (Task 9 passo 3), exit codes e `INCONCLUSIVO` (Global Constraints, Task 1), alvos por variável de ambiente (Task 2), determinismo e mascaramento (Tasks 9 e 10), dependências em `regressao/` (Task 11).
- **Tipos:** `Caso`, `Veredito`, `Alvos`, `PostCaso`, `RelCaso`, `CasoHttp`, `Rota` usados com os mesmos nomes e campos em todas as tasks. `codigo_saida`, `hash_corpo`, `normaliza`, `restaura_dump`, `confere_baseline` definidos nas Tasks 1–2 e consumidos depois.
- **Review Focus:** cada item tem teste na task citada (itens 1, 2, 3, 4, 5, 6 → Tasks 2, 5/6, 1, 9, 10, 1).
- **Proporção:** o plano descreve interfaces e testes, não corpos de função.
