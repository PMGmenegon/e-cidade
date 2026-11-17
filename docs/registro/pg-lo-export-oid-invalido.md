# `pg_lo_export` com OID inválido

Achado na verificação da área Assistência Social. `pg_lo_export` com OID inválido devolve `false` no 5.6 e **lança `ValueError` no 8.x**: defeito de migração
(a tela passa de "não exporta" para 500). A correção reproduz o 5.6 e só toca o caso inválido.

## Medido (13/11/2026, containers `back2`, banco `ecidade`, dentro de `begin`/`rollback`, sem gravar)

`pg_lo_export($conn, $oid, '/tmp/x')`:

| OID | 5.6 | 8.5.12 |
|---|---|---|
| `0`, `null`, `-1`, `'abc'`, `'12x'`, `'00'` | `false` | **`ValueError`** (`Invalid OID value passed`) |
| `''` (vazio) | `false` | `false` (**não** lança) |
| `'999999999'`, `99999999999`, `'0123'`, `' 12'`, `'1e3'`, `'+5'`, `true`, `12.0`, número maior que o `unsigned long` (inexistentes ou não numéricos) | `false` | `false` |
| OID **existente** como `<oid>`, `(int)<oid>`, `' <oid>'`, `'+<oid>'`, `'<oid> '`, `'0<oid>'`, `'<oid>.0'` | `true` | `true` |
| `'-<oid>'` (existente com sinal negativo) | `false` | **`ValueError`** |

Ou seja, o `ValueError` é só com OID **zero, `null`, negativo ou não numérico** (e `'00'`); o vazio devolve `false` nos dois. A forma antiga de 2
argumentos (`pg_lo_export($oid, $arq)`) tem o mesmo comportamento (`ValueError` no 8 com o OID no argumento 1).

## Correção

Cada chamada fica dentro de um `try`/`catch` que **só** troca o `ValueError` do 8.x por `false` (o que o 5.6 devolve) e deixa
passar todo OID que o 5.6 aceita:

```php
try { $r = pg_lo_export($conn, $oid, $arquivo); } catch (\ValueError $oErroOid) { $r = false; }
```

Em chamada sem atribuição o `catch` fica vazio. No 5.6 a classe `ValueError` não existe e o `catch` nunca casa (compila e não muda
nada). Uma primeira versão filtrava o OID antes (`ctype_digit(...) && $oid > 0`); a medida com OID existente mostrou que ela **mudava o
comportamento com OID que o 5.6 aceita**: medido com um large object existente, o 5.6 **e** o 8.5 exportam com `' <oid>'`, `'+<oid>'`,
`'<oid> '`, `'<oid>.0'` e `'0<oid>'` (`true`), e a guarda por filtro devolvia `false` para os três primeiros. Trocada pelo
`try`/`catch`; o teste `testOidQueOCincoSeisAceitaContinuaExportando` falha com a versão antiga (nos dois runtimes) e passa com a nova.

Arquivos ISO-8859-1 editados em bytes. O `lab4_emissaoresult001.php:106` era `if (pg_lo_export(...)) {`; ganhou uma linha com
o `try`/`catch` antes e o `if` passou a testar `$bExportouLaudo`.

14 pontos (os da categoria "ordem antiga", já reordenados): `edu2_aluno002:139`, `edu2_fichaaluno002:157`, `edu3_alunos001:168`,
`edu4_escola.RPC:328`, `lab4_emissaoresult001:106`, `pes4_autprocvalores.RPC:304`, `sys4_cadastrotemplateRPC:112`,
`libs/db_stdlib.php:3735`, `std/DBLargeObject.php:101`, `model/documentoTemplate.model.php:85`, `classes/db_db_bancos_classe.php:468`,
`forms/db_frmalunodados.php:68`, `cad3_conscadastro_002_marica:62`, `model/integracao/transparencia/IntegracaoLicitacao.model.php:264`.
Não há cópia em `extension/modification/`.

### Pontos restantes (11): 6 corrigidos, 5 já iguais ao 5.6

11 chamadas continuam sem guarda e lançam `ValueError` no 8.x com OID inválido: de 3 argumentos `sys4_processarelatorioRPC:171`,
`con4_contratos.RPC:1379`, `libs/db_stdlib.php:3883`, `model/integracao/transparencia/IntegracaoContrato.model.php:339`; de 2
argumentos `lic1_liccomissaodownload:49`, `con4_contratos.RPC:1432`, `lic4_licitacon.RPC:97`, `model/AcordoComissaoMembro.model.php:157`,
`model/convenio.model.php:264`, `model/licitacao/DocumentoEventoLicitacao.model.php:297`, `extension/package/Desktop/Controller/Desktop.php:180`.
Ficam como lacuna até serem corrigidas em lote.
Os 11 pontos que ficaram sem guarda foram examinados um a um. Só difere do 5.6 o ponto cujo OID pode chegar à chamada como `NULL`
cru, `0`, negativo ou não numérico (o `''` devolve `false` nos dois, ver tabela acima). As colunas são `oid` (só dígitos positivos
ou `NULL`); `NULL` convertido para string vira `''`.

| # | Ponto | Origem do OID | Alcança OID inválido? | Decisão |
|---|---|---|---|---|
| 1 | `sys4_processarelatorioRPC.php:171` | `db_geradorrelatoriotemplate.db15_documento`, coluna anulável, passada crua | sim (`NULL`) | corrigido |
| 2 | `con4_contratos.RPC.php:1379` | `acordodocumento.ac40_arquivo`, anulável, crua | sim | corrigido |
| 3 | `con4_contratos.RPC.php:1432` | `acordocomissaomembro.ac07_arquivo`, anulável, crua (o próprio modelo trata `getArquivo() === null`) | sim | corrigido; o `if` passou a testar `$bExportouMembro` |
| 4 | `libs/db_stdlib.php:3883` | `db_configarquivos.db38_arquivo`, anulável, crua | sim | corrigido |
| 5 | `model/integracao/transparencia/IntegracaoContrato.model.php:339` | `acordodocumento.ac40_arquivo`, anulável, crua | sim | corrigido; o `if` passou a testar `$bExportouDocumento` |
| 6 | `lic1_liccomissaodownload.php:49` | `l30_arquivo`, mas a chamada vem depois de `!empty($oComissao->l30_arquivo) &&`, que descarta `NULL`, `0`, `'0'` e `''` | não | **não mexido** (igual ao 5.6) |
| 7 | `lic4_licitacon.RPC.php:97` | chave de array (`foreach (getAnexos() as $iOID => ...)`): `NULL` vira chave `''`, que devolve `false` nos dois | só com `0` | **não mexido** |
| 8 | `model/AcordoComissaoMembro.model.php:157` | `ac07_arquivo`, anulável, crua (a linha de cima grava `'null'` quando `getArquivo() === null`) | sim | corrigido |
| 9 | `model/convenio.model.php:264` | `"$oBanco->db90_logo"`: `NULL` vira `''` (`false` nos dois); em `db_bancos` há 55 `NULL` e 0 zeros em 57 linhas | só com `0` | **não mexido** |
| 10 | `model/licitacao/DocumentoEventoLicitacao.model.php:297` | `liclicitaeventodocumento.l47_arquivo`, `NOT NULL` | só com `0` | **não mexido** |
| 11 | `extension/package/Desktop/Controller/Desktop.php:180` | `$oidFoto`, chamado só dentro de `if ($oidFoto)` | não | **não mexido** |

Nos pontos 7, 9 e 10 a diferença exigiria o valor `0`, que não aparece em nenhuma das colunas na base de exemplo
(`liclicitaeventodocumento`, `acordodocumento`, `acordocomissaomembro` e `db_geradorrelatoriotemplate` estão vazias; `db_configarquivos`:
4 linhas, 0 `NULL`, 0 zeros; `db_bancos.db90_logo`: 57 linhas, 55 `NULL`, 0 zeros). Ficam sem guarda por serem iguais ao 5.6 com os
valores observados; se `0` for considerado possível, a guarda é a mesma dos outros pontos.

Forma da guarda (a mesma dos 14 pontos anteriores): `try { ... } catch (\ValueError $oErroOid) { ... }`, com `false` atribuído quando o
resultado é usado. Arquivos ISO-8859-1 editados em bytes. Não há cópia em `extension/modification/`.

## Verificação

- **Teste** `tests/suite/integracao/DBLargeObjectLeituraTest.php` (camada de integração, nos dois runtimes; lê o banco, não grava:
  `begin`/`rollback` por OID e leitura de um large object existente): OID inválido → `false`; vazio e inexistente → `false`; OID
  válido continua exportando (`true`, arquivo criado) **também com `' <oid>'`, `'+<oid>'`, `'<oid> '` e inteiro**, como no 5.6. Visto **falhar só no 8.5** (`ValueError`) sem a correção e passar nos dois com ela.
  Uma transação por OID porque, no 5.6, o `pg_lo_export` que falha aborta a transação.
- `rodar.sh` (unitário + integração): 5.6 282/282; 8.5 76/78, as 2 falhas conhecidas do handler de erro V3 (`ErrorTest::testHandleWithoutReporting`, `ShutdownTest::testHandleExpectNothing`, `ArgumentCountError` no 8.x), nenhuma nova.
- `php -l` limpo nos 14 arquivos, nos dois runtimes.
- **Tela da amostra da Assistência Social**, 5.6 × 8.5, mesma sessão, container que grava (só `db_usuariosonline` mudou):

| Tela | 5.6 | 8.5 antes | 8.5 depois |
|---|---|---|---|
| `cad4_certidaoexistencia003` | 200 | 500 `ValueError` em `DBLargeObject.php:101` | **200, idêntica ao 5.6** |

**Fora da amostra** (a verificação anterior as atribuía a este defeito, mas falham *antes* do export; medido com e sem a correção, igual): `cad1_reliptuender002`
(500 também no 5.6, `Class "Agata" not found` em `dbagata/classes/core/AgataCore.class:42`: defeito que já existe no 5.6) e `pro1_relcgm002`
(PDF no 5.6, 500 no 8.5 por `Unsupported operand types: int + string` em `dbagata/classes/reports/AgataReport.class:122`: defeito de migração em tratamento à parte).
Nenhuma é corrigida aqui.

### Os 6 pontos corrigidos depois (teste `PgLoExportPontosTest`)

`tests/suite/integracao/PgLoExportPontosTest.php` lê a linha real de cada ponto no arquivo-fonte e a executa isolada, com `NULL`, `0`, `-1` e
`'abc'` no lugar do OID (e, em outro teste, com um OID existente), dentro de `begin`/`rollback`, em container `SOMENTE_LEITURA=1`.

| | 5.6 | 8.5 antes | 8.5 depois |
|---|---|---|---|
| OID inválido nos 6 pontos | `false`, sem exceção | `ValueError` em todos (24 combinações; ex.: `pg_lo_export(): Argument #2 ($oid) Invalid OID value passed`) | `false`, sem exceção, nenhum arquivo criado |
| OID existente nos 6 pontos | exporta | exporta | exporta, `md5` igual ao de um `pg_lo_export` direto |

O teste também confere que o `NULL` convertido em `''` (pontos 7 e 9) devolve `false` nos dois runtimes. `php -l` limpo nos 5 arquivos, nos dois
runtimes. Camada de integração (`rodar.sh --camada integracao`): 5.6 9/9, 8.5 9/9.

## Resíduo conhecido

No 5.6, o `pg_lo_export` com OID inválido **aborta a transação** aberta (as consultas seguintes falham até o `rollback`); com a
guarda, no 8.x a transação continua válida. Com o `try`/`catch` o `ValueError` é lançado antes de a chamada chegar ao banco, então no 8.x a transação continua válida. Nenhum dos 14 pontos grava na mesma transação do export, e o chamador trata `false`;
não foi reproduzido o aborto (seria forçar um erro de banco).
