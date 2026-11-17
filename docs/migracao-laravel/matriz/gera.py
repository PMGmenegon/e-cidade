#!/usr/bin/env python3
"""Gera a copia descartavel do composer.json para um alvo.
uso: gera.py <composer.json original> <dir saida> <laravel: 12|13> <php: 8.4|8.5> [pacote=restricao ...] [-pacote ...] [@semblock]
Regra: laravel/framework ^N.0; todo outro requisito direto (nao php/ext) vira "*";
repositorio vcs do Session (SSH) vira "path" para a copia do commit travado f3020b4 (vendor/dbseller/session). 8.4 = config.platform.php."""
import json, sys, os
src, out, lv, pv, *extra = sys.argv[1:]
c = json.load(open(src))
c['repositories'] = [{"type": "path", "url": "/sess", "options": {"versions": {"dbseller/session": "dev-master"}}}]
for sec in ('require', 'require-dev'):
    for k in list(c[sec]):
        if k != 'php' and not k.startswith('ext-'):
            c[sec][k] = '*'
c['require']['laravel/framework'] = f'^{lv}.0'
semblock = '@semblock' in extra
extra = [e for e in extra if e != '@semblock']
for e in extra:
    if e.startswith('-'):
        n = e[1:]; c['require'].pop(n, None); c['require-dev'].pop(n, None)
    else:
        n, r = e.split('=', 1)
        (c['require-dev'] if n in c['require-dev'] else c['require'])[n] = r
c.pop('scripts', None)
c['autoload'] = {}; c.pop('autoload-dev', None)
c['config'] = {"sort-packages": True, "platform": {"php": "8.4.14" if pv == '8.4' else "8.5.12"}}
if semblock:  # @semblock: desliga o bloqueio por alerta de seguranca, para separar alerta de conflito de versao
    c['config']['policy'] = {"advisories": {"block": False}}
os.makedirs(out, exist_ok=True)
for f in ('composer.lock',):
    try: os.remove(os.path.join(out, f))
    except FileNotFoundError: pass
json.dump(c, open(os.path.join(out, 'composer.json'), 'w'), indent=4)
