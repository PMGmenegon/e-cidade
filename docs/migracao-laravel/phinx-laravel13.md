# Phinx com as dependências do Laravel 13, sem tocar no banco

Medido em 13/11/2026, em cópia descartável fora do repositório (container PHP 8.5.12, Composer 2.11.1). Nada do `composer.json`/`composer.lock`
versionados, de `db/migrations/` ou do banco foi alterado; nenhuma conexão ao banco foi aberta (os comandos Phinx rodaram em container
`--network none`, sem variável de conexão).

## Contexto

As 1.510 migrations de `ecidade/db/migrations/` estendem `Classes\PostgresMigration`, do pacote `dbseller/phinx_postgres` (2 classes:
`classes/PostgresMigration.php` e `classes/Table.php`). O pacote exige `robmorgan/phinx ^0.10` (ou `v0.4.6`), que puxa `cakephp/database ^3.6` e Symfony até
4.x, e por isso não resolve com o Laravel 12/13 (Symfony 7/8). A matriz de versões (`matriz-versoes.md`) listou o bloqueio e a alternativa de usar
`robmorgan/phinx` direto (0.16.12 resolve com Laravel 12 e 13). Aqui cada alternativa é rodada de verdade, com o resolvedor e com o comando.

## 1. As alternativas, no resolvedor e no comando

Conjunto de partida: `ecidade/composer.json` com `laravel/framework ^13.0`, `laravel/passport ^13.0` e os pacotes que não resolvem por outro motivo
(`silex/silex`, `proner/phppimaco`, `dbseller/sdk-api-pix-bb`) retirados, como na matriz; só o Phinx varia.

| | Alternativa | Resolve? | Resultado |
|---|---|---|---|
| **A0** | adaptador `dbseller/phinx_postgres 1.3.0` como está | **não** | `phinx_postgres` exige `robmorgan/phinx ^0.10`, que exige `cakephp/database ^3.6`; a outra linha (`v0.4.6`) exige `symfony/config ~2.7`. Conflito com `laravel/framework ^13.0` |
| **A1** | adaptador atualizado: cópia do pacote com `"robmorgan/phinx": "^0.16"` (versão 1.4.0 local, código intacto) | **sim**: 146 pacotes | Laravel 13.42.0, Phinx 0.16.12, Symfony 8.1.11, `cakephp/database` 5.4.4. `phinx --help` e `phinx list` carregam; **mas as classes do adaptador não carregam** (ver abaixo) |
| **A2** | A1 com 5 ajustes de assinatura no adaptador (diff abaixo) | **sim**: 146 | as classes carregam; `phinx --help` e `phinx list` sem aviso; comportamento do `Table` conferido sem banco (abaixo) |
| **B** | adaptador padrão: sem o pacote DBSeller, `robmorgan/phinx ^0.16` direto | **sim**: 145 | Laravel 13.42.0, Phinx 0.16.12; `phinx --help` e `phinx list` sem aviso; as migrations perdem o comportamento do adaptador (seção 2) |
| **C** | Phinx num `vendor/` próprio, com o adaptador original (`dbseller/phinx_postgres ^1.3`) | **só sem o bloqueio de alertas de segurança** do Composer: 23 pacotes | Phinx 0.10.8, Symfony 4.4.49, `cakephp/database` 3.9.4; com o bloqueio padrão não resolve (`cakephp/database 3.x` "affected by security advisories"); `composer audit`: **7 alertas em 3 pacotes** (`cakephp/database`, `symfony/config`, `symfony/yaml`). `phinx --help` e `phinx list` carregam, com **26 linhas `Deprecated`** no PHP 8.5 (`Symfony\Component\Console\...`: parâmetros implicitamente anuláveis) |

### Por que o A1 não basta (o adaptador original no Phinx 0.16)

Com o código do adaptador intacto, o PHP 8.5 recusa as duas classes ao carregá-las:

```
Fatal error: Declaration of Classes\PostgresMigration::table($tableName, $options = []) must be compatible with
  Phinx\Migration\AbstractMigration::table(string $tableName, array $options = []): Phinx\Db\Table   (classes/PostgresMigration.php:12)
Fatal error: Declaration of Classes\Table::insert(array $columns, array $values) must be compatible with
  Phinx\Db\Table::insert(array $data)                                                                  (classes/Table.php:88)
Deprecated: Classes\Table::__construct(): Implicitly marking parameter $adapter as nullable ...        (classes/Table.php:25, 129)
```

E `save()` (`Table.php:77`) também precisa de `: void`, porque o Phinx 0.16 declara `save(): void`. Como `phinx --help`/`list` não carregam a
classe-base das migrations, eles passam mesmo no A1; o erro só aparece quando uma migration é carregada.

### O ajuste mínimo (A2)

```diff
--- classes/PostgresMigration.php
-    public function table($tableName, $options = array())
+    public function table(string $tableName, array $options = []): \Phinx\Db\Table
--- classes/Table.php
-    public function __construct($name, $options = [], AdapterInterface $adapter = null)
+    public function __construct($name, $options = [], ?AdapterInterface $adapter = null)
-    public function save()
+    public function save(): void
-    public function insert(array $columns, array $values)
+    public function insert(array $columns, ?array $values = null)
+        if ($values === null) {
+            return parent::insert($columns);
+        }
-    private function getSchemaName($table, AdapterInterface $adapter = null)
+    private function getSchemaName($table, ?AdapterInterface $adapter = null)
```

A forma `insert($colunas, $valores)` que as migrations usam continua igual; a forma de 1 argumento do Phinx passa a ser aceita (antes seria erro).

## 2. Provas do critério "carrega sem conectar"

- Ambiente dos comandos: `docker run --rm --network none ... php vendor/bin/phinx --help` e `... list`, sem nenhuma variável `DB_*`/`PG*`. Sem rede, uma tentativa de conexão
  falharia; nenhum comando falhou. Os dois comandos não leem o `phinx.php` do projeto (o `phinx.php:34` faz `pg_connect` ao ser carregado, o que só
  acontece nos comandos que precisam da configuração: `migrate`, `status`, `rollback`...).
- Resultado (A1, A2, B): código de saída 0; `--help` com 40 linhas e `list` com 31, **sem nenhum `Deprecated`/`Warning`/`Fatal`** com `error_reporting=-1`.
  C: código 0; 83 e 79 linhas, 26 `Deprecated`.
- Comportamento do `Table` do A2 conferido **sem banco**, com um adaptador `PostgresAdapter` cuja consulta ao `information_schema` é simulada:

| Chamada | Resultado |
|---|---|
| `new Classes\Table('db_config', [], $adaptador)` (schema simulado `configuracoes`) | nome `configuracoes.db_config` |
| `new Classes\Table('patrimonio.bens', [], $adaptador)` | nome `patrimonio.bens` (já qualificado: não consulta) |
| `insert(['a','b'], [[1,2],[3,4]])` | linhas `[{"a":1,"b":2},{"a":3,"b":4}]` |
| `insert([['a'=>1],['a'=>2]])` (forma do Phinx) | linhas `[{"a":1},{"a":2}]` |

## 3. Diferenças entre o adaptador da DBSeller e o padrão (lidas no código)

Para quem um dia rodar as migrations. Linhas do adaptador: `vendor/dbseller/phinx_postgres/classes/`; linhas do Phinx: `robmorgan/phinx 0.16.12`, `src/Phinx/`.
Contagens nas 1.510 migrations de `ecidade/db/migrations/` (sem `index.php`), em **arquivos** e em **ocorrências** (chamadas), pelo script versionado
`python3 docs/migracao-laravel/matriz/phinx/contagem-migrations.py` (lê como latin-1: 64% da base é ISO-8859-1, e `grep` sem `-a` pula esses arquivos; conta por
chamada, com parênteses balanceados; `addForeignKey` em comentário de cabeçalho não conta). Saída de 14/11/2026:

```
->insert(colunas, valores) (2 listas)                59 arquivos    482 ocorrencias   (259 na forma $table->insert($aColumns, $aValues))
$this->table(...) qualificado                         3 arquivos      4 ocorrencias
$this->table(...) opcao schema                       90 arquivos    536 ocorrencias
$this->table(...) nenhum                              6 arquivos     10 ocorrencias
->addForeignKey(                                     34 arquivos    114 ocorrencias
importLargeObject                                     1 arquivo
Padrao (B) muda o comportamento em (uniao): 95 arquivos de 1510 = 6,3%
```

| Aspecto | Adaptador DBSeller | Phinx padrão 0.16 | Migrations afetadas |
|---|---|---|---|
| Schema da tabela, **3 casos** | `Table.php:29` `if (!hasSchema($name))`; `:30` `$schema = empty($options['schema']) ? getSchemaName(...) : $options['schema']`; `:32-34` `public` se vazio; `:36` prefixa `"schema.nome"`. `getSchemaName` (`:129-138`) consulta `information_schema.tables where table_name = '...'` e usa a 1ª linha | `Db/Table.php`: **não lê** a opção `schema` da tabela (0 ocorrências); `Db/Adapter/PostgresAdapter.php:74-76` e `:138-139` usam só o `schema` das opções da **conexão**; `:1741-1747` (`getSchemaName`): `schema.tabela` é separado pelo ponto, senão vale `$this->schema` (`:67`, padrão `public`) | (a) **qualificado** `'schema.tabela'`: 3 arquivos, 4 ocorrências: igual nos dois. (b) **opção `array('schema' => 'configuracoes')`**: 90 arquivos, 536 ocorrências: DBSeller usa a opção (`:30`); padrão a ignora e cai em `public`. (c) **nenhum dos dois**: 6 arquivos, 10 ocorrências: DBSeller procura o schema pelo nome (`:129-138`); padrão usa `public` |
| `insert(colunas, valores)` | `Table.php:88-107` converte as duas listas em linhas | `Db/Table.php:624`: `insert(array $data)`; o 2º argumento seria **ignorado** e `$colunas` tratado como uma linha de dados (colunas `0`, `1`...), não como lista de colunas | 59 arquivos, 482 ocorrências (259 na forma `$table->insert($aColumns, $aValues)`) |
| `addForeignKey` | `Table.php:113-121`: prefixa o schema da tabela referenciada (`getSchemaName`, `:118`) | `Db/Table.php:494`: usa o nome como veio | 34 arquivos, 114 ocorrências (os outros 212 arquivos que citam o nome o fazem só no comentário do cabeçalho) |
| `save()` | `Table.php:77-81`: copia `tableSchema` para a opção `schema` do adaptador | sem equivalente | nenhum (`setTableSchema` tem 0 usos; a opção fica `null`, ignorada em `PostgresAdapter.php:74`) |
| `importLargeObject($arquivo)` | `PostgresMigration.php:22-37`: cria large object pela PDO (`pgsqlLOBCreate`/`pgsqlLOBOpen`) e devolve o OID | **não existe** | 1 migration: `20170118165415_m7771.php:15` |
| Base das migrations | `phinx.php:11`: `migration_base_class = Classes\PostgresMigration` | classe-base padrão `AbstractMigration` | todas as 1.510 |
| Tabela de controle | `phinx.php:14`: `environments.default_migration_table` | `Db/Adapter/AbstractAdapter.php:81-84`: chave **deprecada desde a 0.13** (`E_USER_DEPRECATED`), copiada para `migration_table` | configuração |

Independem do adaptador: **1.504** das 1.510 migrations executam SQL literal por `$this->execute(...)`.

Leitura: o adaptador padrão (B) **não é equivalente**. Sem `Classes\Table`, as 94 migrations que chamam `$this->table(` com a opção `schema` (90) ou sem schema (6; 2 arquivos têm os dois casos) passam a mirar `public`;
os 59 arquivos com `insert($colunas, $valores)` (482 ocorrências) montam linhas erradas; e a migration com `importLargeObject` quebra. No total, **95 arquivos de 1.510 (6,3%)**
mudam de comportamento (união dos três grupos, sem dupla contagem; os 34 com `addForeignKey` já estão dentro). Corrigir isso é reescrever migrations (fora do escopo:
nenhuma migration pode ser alterada). O A2 mantém o comportamento como está.

## 4. Recomendação

**A2 (atualizar o adaptador).** Motivos:

1. Resolve com o conjunto do Laravel 13 (146 pacotes, Phinx 0.16.12) e carrega o Phinx e a classe-base sem avisos no PHP 8.5.
2. É a menor mudança que preserva o comportamento: 5 assinaturas em 2 arquivos de 2 classes, sem tocar em nenhuma das 1.510 migrations nem na lógica de schema.
3. B muda o comportamento de **95 migrations** (6,3% das 1.510): `table()` sem qualificar (94: 90 com a opção `schema` ignorada e 6 sem schema, 2 arquivos com os dois), das quais 59 também com `insert` de duas listas, mais a que usa
   `importLargeObject` (seção 3); C mantém o Phinx 0.10.8/Symfony 4.4 com 7 alertas de segurança, 26 avisos no 8.5 e só resolve
   desligando o bloqueio do Composer.

O que falta para adotar: publicar uma versão do pacote com a restrição `robmorgan/phinx ^0.16` e os 5 ajustes (o repositório do pacote é da DBSeller) ou apontar
o `composer.json` do runtime novo para uma cópia. **Executar as migrations** (`migrate`, `status`) no Phinx 0.16 contra o banco **não foi feito**: fica como lacuna e
exige banco descartável, hoje fora do que o projeto pode tocar.

## 5. Como reproduzir

Pré-requisitos: Docker com a imagem `ecidade-login-php85` (PHP 8.5.12 e Composer 2.11.1), worktree preparada (`ecidade/vendor/dbseller/session` e `ecidade/vendor/dbseller/phinx_postgres`)
e rede para o Composer. Os scripts ficam em `docs/migracao-laravel/matriz/phinx/` (ao lado dos scripts da matriz de versões, de onde vem o `gera.py`):

| Arquivo | Faz |
|---|---|
| `alternativas.sh` | monta A0, A1, A2, B, C e C2 numa pasta descartável, resolve cada uma, instala as que resolvem e roda `phinx --help`/`list` sem rede; imprime o resumo |
| `adaptador-a2.patch` | o diff do A2 (seção 1), aplicado por `alternativas.sh` com `patch -p1` sobre a cópia do adaptador |
| `teste-adaptador.php` | teste do `Table` sem banco: adaptador `PostgresAdapter` com `fetchRow` simulado |
| `contagem-migrations.py` | as contagens da seção 3 |

```bash
bash docs/migracao-laravel/matriz/phinx/alternativas.sh /tmp/phinx        # ~10 min; imprime RESOLVEU/NAO RESOLVEU por alternativa e os comandos
python3 docs/migracao-laravel/matriz/phinx/contagem-migrations.py         # seção 3
```

O que o script faz, passo a passo (para rodar à mão):

1. **A1** (adaptador com a restrição trocada): copia `ecidade/vendor/dbseller/phinx_postgres/{classes,composer.json,README.md}` para `$T/fork` e troca o `require` por
   `{"php": ">=8.4", "robmorgan/phinx": "^0.16"}`. No `composer.json` da alternativa (gerado por `gera.py ... -dbseller/phinx_postgres`) acrescenta o repositório
   `{"type": "path", "url": "/fork", "options": {"versions": {"dbseller/phinx_postgres": "1.4.0"}}}` e `require dbseller/phinx_postgres ^1.4`; o container monta `$T/fork` em `/fork`.
2. **A2**: `cp -r $T/fork $T/fork2 && (cd $T/fork2 && patch -p1 < adaptador-a2.patch)`; mesmo repositório `path`, agora em `/fork2`.
3. **B**: `gera.py ... -dbseller/phinx_postgres robmorgan/phinx=^0.16`. **A0**: `gera.py` sem remover o adaptador.
4. **C**: `composer.json` só com `{"require": {"php": ">=8.4", "dbseller/phinx_postgres": "^1.3"}, "config": {"platform": {"php": "8.5.12"}}}`; **C2** igual, mais `"policy": {"advisories": {"block": false}}`.
5. Resolver: `docker run --rm --init --network host -u "$(id -u):$(id -g)" -v $T/<alt>:/w -v $T/session-src:/sess:ro -v $T/fork:/fork:ro -v $T/fork2:/fork2:ro -w /w ecidade-login-php85 composer update --no-install --no-scripts --no-plugins --no-interaction`;
   instalar: `composer install` com os mesmos mounts. Sucesso = existir `composer.lock`.
6. Comandos Phinx, **sem rede e sem variável de conexão**: `docker run --rm --network none -v $T/<alt>:/w:ro -w /w ecidade-login-php85 php -d error_reporting=-1 -d display_errors=1 vendor/bin/phinx list` (e `--help`).
7. Teste do `Table` (A2): `... -v $T/fork2:/fork2:ro -v teste-adaptador.php:/t.php:ro ... php /t.php` em `altA2`; carga das classes do A1: `php -r "require 'vendor/autoload.php'; class_exists('Classes\\\\PostgresMigration');"`.
