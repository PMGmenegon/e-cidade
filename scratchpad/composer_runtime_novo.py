#!/usr/bin/env python3
"""Gera o ponto de partida do composer do runtime novo (Laravel 13, PHP 8.5) a partir do composer.json do 5.6.

Uso (da raiz do repositorio), em dois passos com o resolvedor no meio:
    python3 scratchpad/composer_runtime_novo.py ecidade/composer.json ecidade/composer-runtime-novo.json
    (composer update --no-install no container 8.5: gera ecidade/composer-runtime-novo.lock)
    python3 scratchpad/composer_runtime_novo.py --travar ecidade/composer-runtime-novo.lock ecidade/composer-runtime-novo.json
    (composer update --lock: so atualiza o content-hash do lock; as versoes nao mudam)

Regras (cenario "Laravel 13 + Passport ^13" da matriz de versoes, docs/migracao-laravel/matriz-versoes.md):
  - laravel/framework ^13.0 e laravel/passport ^13.0; todo outro requisito direto (nao php/ext) vira "*";
    --travar troca a restricao de cada pacote (nao php/ext) por "^<versao resolvida>" (o `composer bump` daria ">="
    sem teto a partir de "*");
    dbseller/session fica dev-master, como no 5.6;
  - fora do conjunto: os 4 pacotes que nao resolvem com o Laravel 13 (silex/silex, proner/phppimaco,
    dbseller/phinx_postgres, dbseller/sdk-api-pix-bb) -- substitutos sao etapas proprias;
  - php ^8.5 (o runtime novo e o PHP 8.5);
  - Session (dbseller/session dev-master) pelo mesmo repositorio, por https (publico) em vez de ssh;
  - sem "scripts": os de hoje chamam php5.6/artisan do Laravel 5.4;
  - autoload, autoload-dev, minimum-stability e prefer-stable iguais aos do 5.6.
O composer.json do 5.6 so e lido.
"""
import json
import sys

FORA = ('silex/silex', 'proner/phppimaco', 'dbseller/phinx_postgres', 'dbseller/sdk-api-pix-bb')


def travar(lock, out):
    c = json.load(open(out))
    lk = json.load(open(lock))
    ver = {p['name']: p['version'] for p in lk['packages'] + lk['packages-dev']}
    for sec in ('require', 'require-dev'):
        for k in c[sec]:
            if k == 'php' or k.startswith('ext-'):
                continue
            r = ver[k]
            c[sec][k] = r if r.startswith('dev-') else '^' + r.lstrip('v')
    json.dump(c, open(out, 'w'), indent=4)
    open(out, 'a').write('\n')


def main():
    if sys.argv[1] == '--travar':
        return travar(*sys.argv[2:4])
    src, out = sys.argv[1:3]
    c = json.load(open(src))
    c['description'] = 'e-cidade GRP - dependencias do runtime novo (Laravel 13, PHP 8.5)'
    # no-api: clona por git em vez de usar a API do GitHub (que pede token)
    c['repositories'] = [{'type': 'vcs', 'url': 'https://github.com/DBSeller/Session.git', 'no-api': True}]
    for sec in ('require', 'require-dev'):
        for k in list(c[sec]):
            if k in FORA:
                del c[sec][k]
            elif k != 'php' and not k.startswith('ext-'):
                c[sec][k] = '*'
    c['require']['php'] = '^8.5'
    c['require']['laravel/framework'] = '^13.0'
    c['require']['laravel/passport'] = '^13.0'
    c.pop('scripts', None)
    c.pop('secure-http', None)
    json.dump(c, open(out, 'w'), indent=4)
    open(out, 'a').write('\n')


if __name__ == '__main__':
    main()
