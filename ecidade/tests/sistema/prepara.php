<?php
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; } // so linha de comando
// T-012: pede token (Passport) e sessoes legadas ANTES de subir os containers SOMENTE_LEITURA=1 (onde login/token nao gravam).
// Escreve token, sessao-56, sessao-85 em SistemaCliente::segredos() (/tmp do container, 0600; NUNCA sob o docroot). Uso, com os containers normais no ar:
//   docker exec -w /var/www/html ecidade_<agente>_85 php tests/sistema/prepara.php
// Grava so o que o login grava (log de acesso, oauth_access_tokens, sessao): excecao autorizada.
require __DIR__ . '/Cliente.php';
$a = SistemaCliente::alvos();
if (!$a) { fwrite(STDERR, "defina SISTEMA_AGENTE ou .agente\n"); exit(2); }
$d = SistemaCliente::segredos();
if (!is_dir($d)) { mkdir($d, 0700, true); }
foreach (array('token', 'sessao-56', 'sessao-85') as $f) { @unlink($d . '/' . $f); }
$t = SistemaCliente::token($a['56']);
$s56 = SistemaCliente::sessao($a['56']);
$s85 = SistemaCliente::sessao($a['85']);
if (!$t || !$s56 || !$s85) { fwrite(STDERR, "falhou: token=" . (int) !!$t . " sessao56=" . (int) !!$s56 . " sessao85=" . (int) !!$s85 . "\n"); exit(1); }
file_put_contents($d . '/token', $t); chmod($d . '/token', 0600);
file_put_contents($d . '/sessao-56', $s56); chmod($d . '/sessao-56', 0600);
file_put_contents($d . '/sessao-85', $s85); chmod($d . '/sessao-85', 0600);
echo "ok\n";
