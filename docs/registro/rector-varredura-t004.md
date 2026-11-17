# Rector em simulação fora das áreas já portadas (T-004, 12–13/11/2026)

Pergunta: as áreas 1–8 já passaram pelo Rector; **sobrou algo no resto** (núcleo, `src/`, `app/`, `api/`, bibliotecas,
prefixos sem dono)? Resposta medida com `--dry-run` sobre a `laravel/integracao` em `1f1b8258d` (13/11/2026) —
**nenhum arquivo do sistema foi alterado**.

**Resposta curta:** sobrou, e muito. Dos 20.183 arquivos do recorte, **4.364 têm diff** do Rector e **16 nem
parseiam**. Tirando o que não muda nada no 8.5 e o que é decisão do cliente, **4.090 arquivos precisam de
trabalho** — 3.724 deles param o PHP 8.5 com erro fatal. Mais da metade (2.526) são as janelas de pesquisa `func_*`,
frente já conhecida (`CLAUDE.md`, "Frente depois das áreas"). A lista completa, arquivo por arquivo, com regra,
impacto, classe e evidência, está em `rector-varredura-t004-pendencias.tsv` (ao lado deste arquivo).

## Como reproduzir

Ferramental versionado em `scratchpad/`:

| Arquivo | Papel |
|---|---|
| `rector_recorte.py` | classifica cada `.php` versionado em `ecidade/` como DENTRO/FORA e grava a lista de alvos |
| `rector-t004-timeout.php` | a config do projeto (`rector-curado.php`, regras e denylist **intactas**) com outro paralelo: 6 processos, timeout 1800 s |
| `rector_t004_lotes.py` | roda o dry-run em lotes de 500; lote que derruba o Rector é dividido ao meio até isolar o arquivo |
| `rector_t004.sh` | roda os três em sequência |
| `rector_t004_junta.py` | atualiza o JSON quando a integração anda no meio da varredura (refaz só os arquivos que mudaram) |
| `rector_t004_analisa.py` | transforma o JSON na tabela por arquivo e regra, com o impacto medido e a classe de cada pendência |

```bash
# Rector 2.6.7 (a versão do experimento em catalogo-e-metodo.md) com PHPStan FIXADO em 2.2.17, fora do git
# (o container 8.5 não alcança o Packagist: instala-se com o composer do host e roda-se no container)
mkdir -p ecidade/tmp/rector22 && cd ecidade/tmp/rector22 && printf '%s\n' \
  '{"require": {"rector/rector": "2.6.7", "phpstan/phpstan": "2.2.17"}}' > composer.json && composer install && cd -
# com um container PHP 8.5 que monta ecidade/ em /var/www/html (o Rector não usa o banco):
bash scratchpad/rector_t004.sh <container_85> ecidade/tmp/t004_final.json
# outras branches: para cada branch, os arquivos com pendência que ela altera (git diff --name-only
# laravel/integracao...<branch>) e cuja versão difere da integração vão para t004_outras.tsv ("<branch>\t<arquivo>");
# essas versões (git show <branch>:ecidade/<arquivo>) são extraídas para ecidade/tmp/t004_outra/<branch com / → __>/
# e passam pelo mesmo rector_t004_lotes.py, gerando t004_outra.json
# classificação
python3 scratchpad/rector_t004_analisa.py ecidade/tmp/t004_final.json ecidade/tmp/t004_outras.tsv \
  ecidade/tmp/t004_outra.json docs/registro/lint-universo-falhas.txt ecidade/tmp/t004_alvos.txt \
  docs/registro/rector-varredura-t004-pendencias.tsv
```

As configs (`rector-curado.php`, `rector-t004-timeout.php`) são ferramenta do Rector, que exige PHP 8: `php -l` passa no
8.5 e falha no 5.6 (`Errors parsing`), como já era com a `rector-curado.php` das áreas.

O comando do Rector que cada lote executa (de `rector_t004_lotes.py`):

```bash
docker exec -u 1000 -i -e ALVOS=/var/www/html/tmp/t004_lote.txt <container_85> \
  php -d memory_limit=3G -d display_errors=stderr /var/www/html/tmp/rector22/vendor/bin/rector process \
  --dry-run --memory-limit=3G --config /var/www/html/tmp/rector22/rector-t004-timeout.php \
  --no-progress-bar --output-format=json
```

## O recorte — o que entra e por quê

Universo: os **32.860** `.php` versionados em `ecidade/` (`git ls-files`, em `1f1b8258d`). `vendor/`, `tmp/` e
`storage/` não são versionados e não entram.

| Decisão | Regra | Arquivos | Por quê |
|---|---|---|---|
| FORA | raiz, prefixo do `location` do nginx (`docker/proxy/nginx.conf`) | 9.332 | áreas 1–7: telas já portadas e verificadas tela a tela |
| FORA | raiz, entrada do `map` da Fase B (`docker/proxy/faseb_map.conf`) | 1.256 | áreas 1–7: telas de prefixo compartilhado roteadas por lista exata |
| FORA | raiz, prefixo `soc`/`hab` | 126 | área 8 (Assistência Social): fora desta varredura (áreas 1–8); área a refazer à mão (decisão do cliente 13/11: T-001 revertida em `31e3e5e84`; `fe5503916:docs/registro/correcoes-transversais.md` l. 3–5) |
| FORA | `db/migrations` (Phinx) e `database/migrations` (Laravel) | 1.963 | regra 2 do cliente: não tocar no banco |
| DENTRO | todo o resto | **20.183** | núcleo, classes, `src/`, `app/`, `api/`, bibliotecas, raiz sem dono (4.980) |

As dependências que as áreas portaram (classes, `model/`, `funcoes/`, `forms/` alcançados pelas telas) **entram** de
propósito: se o porte foi completo, o dry-run as devolve com zero; se não, aparecem. `funcoes/` (2.114) devolveu zero.

## Incidentes da execução (medidos)

1. **Timeout do paralelo.** Execução única sobre os 20 mil com a config do projeto (timeout padrão 120 s por processo
   filho): `Child process timed out after 120 seconds` → `Reached system errors count limit of 50, exiting...`, **0
   arquivos** no resultado. Por isso o `rector-t004-timeout.php` (só muda `withParallel`).
2. **Worker morto aborta tudo.** Com timeout de 1800 s e 6 processos, depois de ~25 min: `Process "5ix7virts5" not
   found` (`ProcessPool.php` linha 28) e de novo nenhum resultado. Por isso os lotes.
3. **PHPStan 2.3.5 derruba 121 arquivos.** O `composer require rector/rector:2.6.7` resolve `phpstan/phpstan` para a
   mais nova permitida (`^2.2.14` → 2.3.5), e ela quebra dentro do próprio Rector: `CallableTypeNode::__construct():
   Argument #1 ($identifier) must be of type ...IdentifierTypeNode, ...FullyQualifiedNameNode given, called in
   phar://.../phpstan.phar/src/Type/ClosureType.php on line 759` — em 121 arquivos (`src` 62, `app` 22, `model` 18,
   raiz 14…), que ficavam sem resposta. Com PHPStan **2.2.17** os 121 rodam (5 com pendência, 0 erro). Prova de que a
   troca não muda o resultado: amostra aleatória de 500 arquivos do recorte (semente 4, fora dos 121) dá **diff, regras e
   erros idênticos** nas duas versões e idênticos à varredura completa. Daqui em diante, `tmp/rector22` é a instalação.
4. **A integração andou no meio da varredura** (T-018, T-021, T-019 duas vezes, T-001 e sua reversão, `fe5503916`). A varredura
   completa rodou sobre a árvore de 12/11; depois, os arquivos do recorte que mudaram desde `59c46e20b` (a base da
   integração) foram refeitos e juntados (`rector_t004_junta.py`): 67 + 25 + 3 arquivos. Pista que denunciou o problema: os
   5 arquivos `AndamentoPadrao` davam erro de sintaxe numa linha que só existia antes da T-018.
5. **Uma passada só.** O Rector não converge numa passada (modo de falha 3 do *DECISÃO: Rector adotado*); em dry-run
   não há segunda passada. A lista de **arquivos** com pendência é confiável; a lista de **regras** por arquivo é um piso.

## Resultado

**4.364 arquivos com diff + 16 que não parseiam = 4.380 linhas** no `.tsv`. Zero aparece como zero (tabela por grupo).

### Por regra (arquivos em que a regra dispara)

| Regra | Arquivos | Impacto no 8.5 |
|---|---|---|
| `ParseStrComExtractRector` (própria) | 3.256 | fatal |
| `GuardaComparacaoLiteralRector` (própria) | 654 | silencioso |
| `EregToPregMatchRector` | 652 | fatal |
| `Php4ConstructorRector` | 640 | silencioso |
| `OptionalParametersAfterRequiredRector` | 121 | aviso |
| `WrapVariableVariableNameInCurlyBracesRector` | 107 | nenhum na forma `$$x`; **silencioso e regra NÃO fiel** na forma `$$x[...]` (7 arquivos) |
| `ConsistentImplodeRector` | 18 | fatal |
| `ThisCallOnStaticMethodToStaticCallRector` | 15 | nenhum |
| `StringClassNameToClassConstantRector` | 11 | nenhum |
| `FinalPrivateToPrivateVisibilityRector` | 6 | aviso |
| `MultiDirnameRector` | 5 | nenhum |
| `GetCalledClassToStaticClassRector` | 4 | nenhum |
| `SetCookieRector` | 3 | nenhum — **e a reescrita quebra o 5.6** |
| `RenameMktimeWithoutArgsToTimeRector` | 2 | fatal |
| `ArrayKeyExistsOnPropertyRector` | 2 | fatal |
| `CurlyToSquareBracketArrayStringRector` | 1 | fatal (parse error) |
| `AssignArrayToStringRector` | 1 | fatal |
| `MbStrContainsRector` | 1 | nenhum — **e a reescrita quebra o 5.6** |
| `PregReplaceEModifierRector` | 1 | silencioso |
| `CreateFunctionToAnonymousFunctionRector` | 1 | fatal |
| (diff sem regra) | 144 | só espaço em branco: o printer do Rector apaga espaço no fim de linha |

### Impacto medido de cada regra

Scripts mínimos de 1–6 linhas, um por regra, rodados nos dois runtimes (`ecidade/tmp/t004_efeito/`, fora do git;
`php -d display_errors=1 -d error_reporting=-1`). O que o código **original** faz:

| Caso | 5.6 | 8.5 |
|---|---|---|
| `parse_str('a=1')` | `a=1` | `ArgumentCountError: parse_str() expects exactly 2 arguments, 1 given` |
| `ereg('a','abc')` | `casa` (Deprecated) | `Call to undefined function ereg()` |
| `implode(array('a','b'), ',')` | `a,b` | `TypeError: implode(): Argument #1 ($separator) must be of type string` |
| `mktime()` | `ok` (Strict Standards) | `ArgumentCountError: mktime() expects at least 1 argument, 0 given` |
| `array_key_exists('a', $obj)` | `bool(true)` | `TypeError: array_key_exists(): Argument #2 ($array) must be of type array` |
| `create_function(...)` | `4` | `Call to undefined function create_function()` |
| `$s=''; $s[]='x'` | `array(1)` | `Error: [] operator not supported for strings` |
| `$s{1}` | `b` | `Parse error: syntax error, unexpected token "{"` |
| construtor PHP 4 `function Foo()` | `chamou` | `nao chamou` (o construtor não roda) |
| `preg_replace('/a/e', ...)` | `"Abc"` | `NULL` |
| `$$m[$i]` (m = array de nomes) | `Ana` | vazio |
| `function f($a = 1, $b)` | `3` | `3` + `Deprecated: Optional parameter $a declared before required parameter $b` |
| `final private function` | `ok` | `ok` + `Warning: Private methods cannot be final` |
| `$this->metodoEstatico()`, `dirname(dirname())`, `get_called_class()`, `setcookie(.., 0, '/')`, `mb_strpos() !== false` | iguais nos dois | |

`GuardaComparacaoLiteralRector` (`0 == ""` etc.) é a regra própria já medida nas áreas (`contexto.md`, superfície de
incompatibilidade). Avisos (`aviso`) contam como trabalho: a saída depende de `php.display_errors`/`error_reporting`
da config do sistema (`bootstrap.php:87`) e do Whoops, não do `php.ini`.

### Por classe (critério 3)

| Classe | fatal | silencioso | aviso | nenhum | espaço | não parseia | **Total** |
|---|---|---|---|---|---|---|---|
| precisa de trabalho | 3.724 | 258 | 106 | 0 | 0 | 2 | **4.090** |
| decisão do cliente | 45 | 14 | 4 | 68 | 143 | 13 | **287** |
| já resolvida em outra branch | 1 | 0 | 0 | 0 | 1 | 1 | **3** |

Critério de cada classe (testados nesta ordem; a evidência de cada linha está no `.tsv`):

- **Decisão do cliente — área a refazer à mão (24, testado primeiro):** arquivos que a
  `origin/assistencia-social/migracao` altera — 22 `classes/db_habit*`/`db_workflow*` e `func_habitcandidato.php`,
  `func_habitprograma.php`, todos fatais no 8.5. O porte dessa branch não conta como solução: o cliente decidiu em
  13/11 refazer a Assistência Social à mão (T-001 revertida em `31e3e5e84`; branch apagada do GitHub;
  `fe5503916:docs/registro/correcoes-transversais.md` l. 3–5).
- **Já resolvida em outra branch:** outra branch altera o arquivo **e** o dry-run sobre a versão dela dá zero. 2 na
  `nucleo/T-020-legados-residuais` (em andamento: `iss4_gissonline002.php`, `auditoria_migracao_cursor.php`), 1 na
  `nucleo/T-028-jpgraph-pizza` (`jpgraph_pie3d.php`, só espaço aqui).
- **Decisão do cliente (demais):**
  - **211 sem efeito no 8.5** (68 `nenhum` + 143 `espaço`): a mesma saída nos dois runtimes; pela Regra 3 (só
    atualizar) **não aplicar**. Já decidida.
  - **13 não compilam nem no 5.6** (T-003, `lint-universo.md`: "falham nos dois"): `classes/db_cursoedu_ext_classe.php`,
    5 `forms/db_frm*`, 2 `pdw_document.php` do `dbagata`, 3 `func_*`, 2 `Interface.php` do `src/Saude`.
  - **39 em biblioteca de terceiros embutida** com impacto real: `fpdf151/` (23), `libs/jpgraph/` (11), `dbagata/`
    (jpgraph/phpdocwriter/fpdf151/pclzip, 3), `ext/php/Michelf` (1), `scripts/widgets/jscalendar` (1). Portar o mínimo
    (como a T-021 fez para compilar) ou trocar por versão nova é escolha do cliente; `fpdf151/` já é dívida aberta
    no `CLAUDE.md`.
- **Precisa de trabalho:** o resto. Por evidência:
  - **2.526 `func_*`** (2.525 fatais): janelas de pesquisa servidas hoje pelo 5.6, porque o prefixo é compartilhado;
    a frente já está registrada (`CLAUDE.md`: "as 2.993 janelas de pesquisa `func_` (2.527 ainda com `parse_str` de 1
    argumento)"). Bate com esta medida.
  - **720 telas da raiz fora do proxy** (`con` 303, `cad` 110, `ate` 97, `pro` 74, `mat` 61, `ipa` 16, `tel` 10…):
    prefixos compartilhados cujas telas fora do menu não estão no `location` nem no `map`; servidas hoje pelo 5.6.
  - **844 no resto** (`classes` 660, `model` 64, `forms` 37, `dbforms` 28, `src` 25, `libs` 10, `integracao_externa`
    7…): dependências que nenhuma tela portada alcançou, ou alcançou por caminho que a enumeração das áreas não viu.
    Inclui o núcleo `libs/db_stdlib.php` (ver abaixo).
  - 6 em que outra branch mexe mas ainda resta regra: `con1_contrib007.php`, `dbforms/db_virafolha.php`, `duplos.php`,
    `duploscgs.php` (T-020), `libs/db_stdlib.php` (T-027), `LoginBehat.php` (`nucleo/login-seguranca`, que não será
    integrada pela Regra 3).
  - 2 que não compilam só no 8.5 (`duplos.php`, `duploscgs.php`): já na lista dos 27 da T-003 (`lint-universo.md`).

### Por grupo (o zero aparece como zero)

| Grupo | Recorte | Precisa de trabalho | Decisão do cliente | Já resolvida |
|---|---|---|---|---|
| `app` | 1.259 | 1 | 7 | 0 |
| `bin` | 16 | 2 | 0 | 0 |
| `builder` | 2 | 0 | 1 | 0 |
| `classes` | 4.106 | 660 | 24 | 0 |
| `dbagata` | 121 | 0 | 32 | 0 |
| `dbforms` | 47 | 28 | 3 | 0 |
| `ext` | 7 | 0 | 2 | 0 |
| `extension` | 14 | 0 | 1 | 0 |
| `forms` | 2.361 | 37 | 33 | 0 |
| `fpdf151` | 194 | 0 | 47 | 0 |
| `imagens` | 7 | 1 | 0 | 0 |
| `integracao_externa` | 103 | 7 | 1 | 2 |
| `libs` | 83 | 10 | 18 | 1 |
| `manuais` | 48 | 1 | 0 | 0 |
| `model` | 1.658 | 64 | 40 | 0 |
| raiz `db_*` | 23 | 4 | 0 | 0 |
| raiz `func_*` | 2.986 | 2.526 | 8 | 0 |
| raiz, outros | 1.971 | 720 | 43 | 0 |
| `routes` | 119 | 0 | 1 | 0 |
| `scripts` | 2 | 0 | 1 | 0 |
| `securimage` | 3 | 0 | 2 | 0 |
| `skins` | 26 | 1 | 0 | 0 |
| `src` | 2.651 | 25 | 18 | 0 |
| `std` | 42 | 3 | 3 | 0 |
| `tests` | 54 | 0 | 2 | 0 |

**Zero em tudo:** `api` (34), `bootstrap` (2), `config` (2), `configuration` (11), `database` (2), `db` (1), `dd` (1),
`estilos` (1), `fpdf` (18), `funcoes` (2.114), `funcs` (37), `interfaces` (14), `jobs` (13), `legacy` (2), `licenca` (1),
`modification` (4), `public` (1), `resources` (9), `templates` (6), `webservices` (7). Ou seja: a API Silex, o
bootstrap e `funcoes/` não precisam do Rector; `app/` (Laravel) precisa de 1 arquivo
(`BalancetesMensaisService.php`, `implode` invertido).

## Achados que valem além desta tarefa

1. **`WrapVariableVariableNameInCurlyBracesRector` não é fiel na forma `$$x[...]`** (a varredura das
   áreas portadas atrás dessa forma é trabalho à parte). No 5.6, `$$m[$i]` é `${$m[$i]}`; no 7+, `${$m}[$i]`. A regra escreve
   `${$m}[$i]` — fixa a leitura do 8.5 e **muda o 5.6** (medido: 5.6 original `Ana`, 5.6 reescrito vazio, 8.5 vazio). A
   reescrita fiel seria `${$m[$i]}`. Na `area-tributario.md` a regra foi verificada só na forma `$$label`. Nas áreas já
   portadas há 6 arquivos onde `$$x[...]` do `master` virou `${$x}[...]` (`prot1_cadcgm001/002`, `sau1_cgm001/002`,
   `pro2_duploscgm002`, `con2_lrfimpostossaude002`). Neste recorte, 7 arquivos têm a forma: `ate2_confereatend002.php`,
   `con2_lrfimpostossaude002_2007.php`, `dbforms/db_classes_criaiframe.php`,
   `dbforms/db_classes_iframe_alterar_excluir.php`, `dbforms/db_classes_iframe_seleciona_2005.php`,
   `func_consbens001.php`, `libs/db_stdlib.php` (`calculoiptu.php` e `calculoissqnfixo.php` tinham e foram corrigidos
   pela T-019, integrada em `1f1b8258d`). A bateria 5.6 × 8.5 não vê esse defeito: os dois rodam o mesmo
   código reescrito.
2. **Recomendação de denylist** (antes de qualquer aplicação do Rector fora das áreas): acrescentar
   - `Rector\Php73\Rector\FuncCall\SetCookieRector` — passa as opções como array (`['expires' => 0, 'path' => '/']`);
     no 5.6: `Warning: setcookie() expects parameter 3 to be long, array given` e o cookie **não é gravado**. Dispara em
     `login.rpc.php` (cookies `DB_base`/`DB_servidor`/`DB_porta`), `model/configuracao/SkinService.service.php` e
     `src/V3/Window/Session.php`.
   - `Rector\Php80\Rector\NotIdentical\MbStrContainsRector` — emite `str_contains()`; no 5.6: `Call to undefined
     function str_contains()` (irmã da `StrContainsRector`, que já está na denylist). Dispara em `std/DBString.php`.
   - `Rector\Php70\Rector\Variable\WrapVariableVariableNameInCurlyBracesRector` — pelo achado 1: fiel só na forma `$$x`, que não precisa de
     mudança; na forma `$$x[...]` muda o 5.6.
3. **Núcleo ainda tem pendência real:** `libs/db_stdlib.php` (alcançado por toda tela) tem `preg_replace` com `/e`
   (8.5 devolve `NULL`) e a forma `$$x[...]`; o `dbagata/`, dado como portado no `CLAUDE.md`, tem 32 pendências, todas
   em bibliotecas de terceiros embutidas ou sem efeito.

## Lacunas

- **Uma passada só** (incidente 5): o número de **regras** por arquivo é piso; o de **arquivos** não.
- O impacto é por **regra**, não por ocorrência: um arquivo "fatal" pode ter o `parse_str` num ramo que nenhuma tela
  executa. Isso não muda a classe (o arquivo para quando o ramo roda), mas a ordem de ataque deve ser por tela.
- "Já resolvida" depende das branches de origem: T-020 e T-028 ainda não foram integradas. Se não entrarem, as 3
  voltam a "precisa de trabalho".
- Os 16 que não parseiam não passam pelo Rector: o que o Rector faria neles é desconhecido até compilarem.
- Nada foi aplicado: a classe "precisa de trabalho" diz **onde** falta porte, não **como** portar (ver achado 1: nem
  toda reescrita do Rector é fiel).
