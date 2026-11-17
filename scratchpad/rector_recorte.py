#!/usr/bin/env python3
"""Recorte da varredura do Rector fora das areas ja portadas (T-004).

Classifica cada .php versionado em ecidade/ como DENTRO ou FORA do recorte, com o motivo,
e grava a lista de caminhos (relativos a ecidade/) que o rector-curado.php le por ALVOS.

Uso (da raiz do repositorio):
    python3 scratchpad/rector_recorte.py ecidade/tmp/t004_alvos.txt [resumo.tsv]

Regras (ordem importa; a primeira que casar decide):
  FORA area1-7-location  raiz, prefixo do `location` do nginx (docker/proxy/nginx.conf)
  FORA area1-7-map       raiz, entrada do map da Fase B (docker/proxy/faseb_map.conf)
  FORA area8-socialhab   raiz, prefixo soc/hab: Assistencia Social, portada na
                         origin/assistencia-social/migracao; fora da integracao por decisao do
                         cliente (T-001 revertida em 13/11/2026) e fora desta varredura (areas 1-8)
  FORA banco-migrations  db/migrations (Phinx) e database/migrations (Laravel): regra do
                         cliente "nao tocar no banco"
  DENTRO <grupo>         todo o resto (nucleo, classes, model, src, app, api, bibliotecas,
                         raiz sem dono...)
"""
import re
import subprocess
import sys
from collections import Counter

RAIZ = 'ecidade'
NGINX = 'docker/proxy/nginx.conf'
MAP = 'docker/proxy/faseb_map.conf'


def prefixos_location():
    for l in open(NGINX, encoding='latin-1'):
        m = re.search(r'location ~\*.*\?:\(\?:([a-z0-9?|]+)\)\[0-9\]\*_', l)
        if m:
            return re.compile(r'^(?:%s)[0-9]*_' % m.group(1), re.I)
    sys.exit('location nao achado em ' + NGINX)


def entradas_map():
    s = set()
    for l in open(MAP, encoding='latin-1'):
        m = re.match(r'\s+(\S+)\s+php85;', l)
        if m:
            s.add(m.group(1).lower())
    return s


def classifica(p, loc, mapa):
    partes = p.split('/')
    if len(partes) == 1:
        if loc.match(p):
            return 'FORA', 'area1-7-location'
        if p.lower() in mapa:
            return 'FORA', 'area1-7-map'
        if re.match(r'^(?:soc|hab)[0-9]*_', p, re.I):
            return 'FORA', 'area8-socialhab'
        return 'DENTRO', 'raiz-sem-dono'
    if partes[0] in ('db', 'database') and partes[1] == 'migrations':
        return 'FORA', 'banco-migrations'
    return 'DENTRO', partes[0]


def main():
    saida = sys.argv[1]
    resumo = sys.argv[2] if len(sys.argv) > 2 else None
    loc, mapa = prefixos_location(), entradas_map()
    arqs = subprocess.run(['git', 'ls-files', '-z', '--', RAIZ], capture_output=True,
                          check=True).stdout.decode('latin-1').split('\0')
    arqs = [a[len(RAIZ) + 1:] for a in arqs if a.lower().endswith('.php')]
    cont, alvos, linhas = Counter(), [], []
    for a in sorted(arqs):
        dec, mot = classifica(a, loc, mapa)
        cont[(dec, mot)] += 1
        linhas.append('%s\t%s\t%s' % (dec, mot, a))
        if dec == 'DENTRO':
            alvos.append(a)
    with open(saida, 'w', encoding='latin-1') as f:
        f.write('\n'.join(alvos) + '\n')
    if resumo:
        with open(resumo, 'w', encoding='latin-1') as f:
            f.write('\n'.join(linhas) + '\n')
    for (dec, mot), n in sorted(cont.items()):
        print('%-6s %-20s %6d' % (dec, mot, n))
    print('total %d  dentro %d' % (len(arqs), len(alvos)))


if __name__ == '__main__':
    main()
