<?php
// Sem banco: adaptador Phinx com fetchRow simulado (devolve o schema 'configuracoes'); nunca chama getConnection().
require 'vendor/autoload.php';
$ad = new class(['name' => 'x', 'adapter' => 'pgsql']) extends Phinx\Db\Adapter\PostgresAdapter {
    public function fetchRow(string $sql): array|false { return ['table_schema' => 'configuracoes']; }
};
echo 'classe PostgresMigration: ', class_exists('Classes\PostgresMigration') ? 'carrega' : 'NAO carrega', "\n";
$t = new Classes\Table('db_config', [], $ad);
echo 'Table sem schema -> ', $t->getName(), "\n";
$t2 = new Classes\Table('patrimonio.bens', [], $ad);
echo 'Table com schema -> ', $t2->getName(), "\n";
$t->insert(['a', 'b'], [[1, 2], [3, 4]]);
echo 'insert(colunas, valores) -> ', json_encode($t->getData()), "\n";
$t3 = new Classes\Table('outra', [], $ad);
$t3->insert([['a' => 1], ['a' => 2]]);
echo 'insert(linhas) -> ', json_encode($t3->getData()), "\n";
