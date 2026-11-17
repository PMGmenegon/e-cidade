<?php
// Bootstrap da suite: autoload do composer (vendor/ de cada runtime) + bootstrap do e-cidade, o mesmo que o phpunit.xml
// do projeto usa (autoloader das classes de src/, definicoes, handlers). T-009: os testes existentes dependem dele.
// Nao abre conexao nem sessao: o banco so e tocado por quem o pedir.
require_once __DIR__ . '/../../vendor/autoload.php';
require_once __DIR__ . '/../../bootstrap.php';
