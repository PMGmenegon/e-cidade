#!/usr/bin/env bash
set -euo pipefail

# Somente o banco descartavel de desenvolvimento; nao executa migrations das areas.
if [[ "${ECIDADE_BANCO_DESCARTAVEL:-}" != 1 || "${DB_HOST:-}" != ecidade_database ]]; then
    echo 'Use somente no banco descartavel, com ECIDADE_BANCO_DESCARTAVEL=1.' >&2
    exit 1
fi

cd /var/www/html
php artisan migrate --no-interaction --no-ansi \
    --path=database/migrations/2021_10_25_083540_alter_secret_to_oauth_clients.php \
    --path=database/migrations/2021_10_25_084718_add_provider_to_oauth_clients.php \
    --path=database/migrations/2022_10_24_103009_create_notifications_table.php \
    --path=database/migrations/2024_07_10_090243_M28384_add_column_api.php \
    --path=database/migrations/2024_11_18_115626_M29463_add_table_item_menu_favorito.php \
    --path=database/migrations/2024_11_28_142041_M29463_add_item_menu_gerenciamento_favoritos.php

# Credencial demonstrativa do dump, calculada pelo proprio projeto.
php <<'PHP'
<?php
require 'bootstrap.php';
$db = new PDO(
    'pgsql:host=' . getenv('DB_HOST') . ';port=' . getenv('DB_PORT') . ';dbname=' . getenv('DB_DATABASE'),
    getenv('DB_USERNAME'),
    getenv('DB_PASSWORD'),
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
);
$statement = $db->prepare('UPDATE configuracoes.db_usuarios SET senha = ? WHERE id_usuario = 1 AND login = ?');
$statement->execute([Encriptacao::encriptaSenha('dbseller'), 'dbseller']);
if ($statement->rowCount() !== 1) {
    throw new RuntimeException('Conta demonstrativa do dump nao encontrada.');
}
echo "Desktop preparado; credencial demonstrativa: dbseller / dbseller.\n";
PHP
