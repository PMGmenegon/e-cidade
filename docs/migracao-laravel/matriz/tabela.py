#!/usr/bin/env python3
"""Monta a matriz (markdown) a partir dos composer.lock de cada alvo.
uso: tabela.py <ecidade/composer.json> <ecidade/composer.lock> <dir l12-84> <dir l12-85> <dir l13-84> <dir l13-85>"""
import json, sys, os
cj, cl, *alvos = sys.argv[1:]
orig = json.load(open(cj)); atual = json.load(open(cl))
def idx(lock):
    return {p['name']: p for p in lock.get('packages', []) + lock.get('packages-dev', [])}
ati = idx(atual)
locks = {}
for d in alvos:
    f = os.path.join(d, 'composer.lock')
    locks[os.path.basename(d.rstrip('/'))] = idx(json.load(open(f))) if os.path.exists(f) else None
def cel(nome, alvo):
    l = locks[alvo]
    if l is None: return None
    return l.get(nome)
print('| Pacote direto | Restrição atual | Travada hoje | Candidata L12 | PHP exigido (L12) | Candidata L13 | PHP exigido (L13) | L12 8.4 | L12 8.5 | L13 8.4 | L13 8.5 |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for sec in ('require', 'require-dev'):
    for nome, rest in orig[sec].items():
        if nome == 'php' or nome.startswith('ext-'): continue
        hoje = ati.get(nome, {}).get('version', '(ausente do lock)')
        cols = []
        for lv in ('l12-85', 'l13-85'):
            p = cel(nome, lv)
            cols += [p['version'] if p else '—', (p.get('require', {}).get('php', '(não declara)') if p else '—')]
        res = []
        for a in ('l12-84', 'l12-85', 'l13-84', 'l13-85'):
            res.append('sim' if cel(nome, a) else 'não')
        tag = ' (dev)' if sec == 'require-dev' else ''
        print(f'| `{nome}`{tag} | `{rest}` | {hoje} | ' + ' | '.join(f'`{c}`' if c != '—' else c for c in cols) + ' | ' + ' | '.join(res) + ' |')
