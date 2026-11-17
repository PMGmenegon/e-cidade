<?php
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; } // so linha de comando: nunca servir por HTTP
// T-012: imprime {"id":..,"secret":..} do cliente OAuth do config (so para a camada de sistema; nao logar a saida).
error_reporting(0);
chdir(dirname(dirname(__DIR__)));
require 'bootstrap.php';
$c = ECidade\V3\Extension\Registry::get('app.config');
echo json_encode(array('id' => $c->get('api.client.id'), 'secret' => $c->get('api.client.secret')));
