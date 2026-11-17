# Telas que carregam o `.env` com `new \Dotenv\Dotenv('./')` (T-068, 14/11/2026)

**Resumo:** 9 arquivos carregam o `.env` da raiz direto, com a API do Dotenv 2. No 5.6 e no 8.5 de hoje (`vendor/` do 5.6,
`vlucas/phpdotenv` v2.6.9) funciona; no runtime novo (Laravel 13, Dotenv v5.8.0) dá
`TypeError: Dotenv\Dotenv::__construct(): Argument #1 ($store) must be of type Dotenv\Store\StoreInterface, string given`
e a tela devolve HTTP 500. Cada ponto trocou **1 linha**, escolhendo pela API que existe:

```php
$dotenv = method_exists('Dotenv\Dotenv', 'createUnsafeImmutable') ? \Dotenv\Dotenv::createUnsafeImmutable('./') : new \Dotenv\Dotenv('./');
$dotenv->load();   // linha seguinte, sem mudança
```

No 5.6 e no 8.5 de hoje o ramo é o `new \Dotenv\Dotenv('./')` de antes. No runtime novo, `createUnsafeImmutable` é a
forma do Dotenv 5 que escreve nos mesmos três lugares que o 2 escrevia (`getenv`/`putenv`, `$_ENV`, `$_SERVER`) e, como
o 2 com `load()`, não sobrescreve variável já definida. Medido abaixo: mesmo efeito.

| Arquivo:linha | Tela de menu que chega ao ponto |
|---|---|
| `cai3_gerfinanc001.php:49` | ela mesma ("Geral Financeira"), no topo |
| `con4_atividades_documentos.php:9` | ela mesma ("Andamento de Documentos"), no topo |
| `db_assinar_documentos.php:9` | aberta por `scripts/classes/patrimonio/AndamentoProcesso.js`, no topo |
| `cad4_emissaogeralisencao002.php:42` | relatório de `cad4_emissaogeralisencao.php` ("Emissão Geral de Certidão de Isenção"), no topo |
| `cad2_certisen002.php:42` | relatório aberto pela consulta `cad3_conscadastro_002_detalhes.php`, no topo |
| `emp1_empempenho005.php:318` | "Alteração de empenho", só depois de gravar a alteração |
| `emp4_empempenho004.php:1207` | emissão do empenho, depois de gravá-lo |
| `pes4_gerarEmpenhoFolhaRPC.php:528` | geração dos empenhos da folha, depois de gravá-los |
| `app/Domain/RecursosHumanos/Pessoal/Relatorios/ContraChequePdf.php:50` | contracheque em PDF pelo Laravel (lê `env('BASE_URL_AUTENTICIDADE')` em seguida) |

Nenhum deles tem cópia em `extension/modification/`. Os 9 continuam ISO-8859-1; `php -l` limpo no 5.6, no 8.5 e no
runtime novo. Nada mais nesses arquivos mudou.

## Trecho: o que fica carregado

`scratchpad/dotenv_sonda.php` (precisa ficar na raiz de `ecidade/`, como as telas, porque o Apache recusa `.php` em
`tmp/`; foi copiado para lá só durante a medição e apagado): carrega o `.env` real como as telas e mostra, para cada uma
das 42 chaves do `.env`, o que havia e o que ficou em `getenv()`, `$_ENV` e `$_SERVER` (só presença e 8 caracteres do
sha1 do valor: o `.env` tem segredos). Pedida pelo Apache nos três runtimes, em 8 situações: nada definido antes,
`APP_NAME` definida antes em `putenv`, em `$_ENV` ou em `$_SERVER`, cada uma carregando uma ou duas vezes. Além disso, o
próprio container já define `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME` e `DB_PASSWORD` no ambiente, que o
`.env` também tem.

| Comparação | Resultado |
|---|---|
| runtime novo, linha antiga | `TypeError` acima (o "antes") |
| runtime novo, linha nova × 8.5 de hoje, linha antiga (mesmo PHP, Dotenv 5.8 × 2.6.9) | **igual em 8 de 8** |
| 8.5 de hoje, linha nova × linha antiga | igual em 8 de 8 |
| 5.6, linha nova × linha antiga | igual em 8 de 8 |
| 5.6 × runtime novo, só as chaves que o Dotenv mudou (depois ≠ antes) | **igual em 8 de 8** |

**Sobrescreve variável já definida? Nenhum dos dois.** A `APP_NAME` definida antes (em qualquer dos três lugares) e as
`DB_*` do ambiente do container ficam com o valor de antes, e o Dotenv não as copia para os outros dois lugares; carregar
duas vezes não muda nada. As chaves que só existem no `.env` vão para os três lugares nos dois.

A única diferença entre a saída do 5.6 e a do runtime novo não é do Dotenv: no PHP 8.5 (o de hoje e o novo)
`variables_order` é `EGPCS` e as variáveis do ambiente já estão em `$_ENV` **antes** de carregar; no 5.6 (`GPCS`) não.
Antes e depois iguais em cada runtime.

## Telas

`scratchpad/t068_telas.sh`: a mesma sessão (login no 5.6) restaurada antes de cada pedido, corpo normalizado (porta da URL e
`sid` do captcha), linhas novas do `extension/log/error.log`. "Antes" é a linha antiga posta de volta nos 9 arquivos só
durante a medição.

| Tela | Container | 5.6 antes | 5.6 depois | novo antes | novo depois |
|---|---|---|---|---|---|
| `con4_atividades_documentos.php` | somente leitura | 200, 28.362 B | igual | **500** (`TypeError`) | igual ao 5.6 |
| `db_assinar_documentos.php` | somente leitura | 200, 14.743 B | igual | **500** | igual ao 5.6 |
| `cad4_emissaogeralisencao002.php` | somente leitura | 200 (`Filtro de ano inválido!`) | igual | **500** | igual ao 5.6 |
| `cad2_certisen002.php?matric=1&codigoIsencao=1` | somente leitura | 200 | igual | **500** | igual ao 5.6 |
| `cai3_gerfinanc001.php` | que grava (a tela atualiza `db_usuariosonline` antes do ponto) | 200 (`numpref não configurada`) | igual | **500** | igual ao 5.6 |

"Igual" = mesmo md5 do corpo normalizado e nenhuma linha nova no `error.log`. Vigia do banco nas duas rodadas: **rc=0**
(só `db_usuariosonline`).

## Lacunas

- `emp1_empempenho005.php`, `emp4_empempenho004.php` e `pes4_gerarEmpenhoFolhaRPC.php` só chegam ao ponto depois de
  gravar empenho: não rodados. A linha é a mesma do trecho medido.
- `ContraChequePdf.php` roda pelo Laravel, que no runtime novo ainda não passa do boot. Idem.
