#!/usr/bin/env python3
"""Laco de eliminacao: resolve; se falhar, tira o pacote raiz citado no 1o problema (nunca laravel/framework)
e repete ate resolver. Grava cada rodada em <dir>/rodada-N.txt e o resumo em <dir>/eliminados.txt.
uso: elimina.py <composer.json original> <dir> <laravel> <php> [extras do gera.py]"""
import re, subprocess, sys, os, shutil
src, d, lv, pv, *extra = sys.argv[1:]
aqui = os.path.dirname(os.path.abspath(__file__))
tirados = []
for n in range(1, 30):
    subprocess.run([f'{aqui}/gera.py', src, d, lv, pv, *extra, *['-'+t for t in tirados]], check=True)
    subprocess.run([f'{aqui}/resolve.sh', d], stdout=subprocess.DEVNULL)
    shutil.copy(f'{d}/saida.txt', f'{d}/rodada-{n}.txt')
    if os.path.exists(f'{d}/composer.lock'):
        break
    s = open(f'{d}/saida.txt', errors='replace').read()
    raiz = [r for r in re.findall(r'Root composer\.json requires (\S+)', s) if r != 'laravel/framework']
    if not raiz:
        print('SEM PACOTE RAIZ IDENTIFICAVEL; ver', f'{d}/saida.txt'); sys.exit(1)
    tirados.append(raiz[0])
    print(f'rodada {n}: tira {raiz[0]}', flush=True)
open(f'{d}/eliminados.txt', 'w').write('\n'.join(tirados) + '\n')
print('RESOLVEU' if os.path.exists(f'{d}/composer.lock') else 'NAO', d, 'eliminados:', tirados)
