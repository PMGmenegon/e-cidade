#!/usr/bin/env python3
"""Linha de base dos 5 relatorios que sobem o kernel HTTP do Laravel dentro da pagina (T-023).

  captura  --porta P --container C --sessao ARQ --saida DIR   gera as respostas normalizadas (um .out por caso)
  compara  --novo DIR [--base DIR]                            sai 1 se alguma resposta difere da linha de base

Captura: para CADA requisicao a sessao e restaurada (a requisicao a reescreve), como no scratchpad/cmp.py. Nao grava no banco:
rode contra containers criados com SOMENTE_LEITURA=1. ARQ e o arquivo de sessao criado por sessao.sh.
Formato do .out: 1a linha "<http> <content-type>", depois o corpo normalizado (ISO-8859-1 lido como latin-1).
Saida: 0 igual / 1 difere / 2 uso.
"""
import argparse, difflib, os, re, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))

NORM = [  # identificadores aleatorios e horarios que mudam a cada requisicao
    (re.compile(rb'sid=[0-9a-f]{8,}'), b'sid=X'),
    (re.compile(rb'wname[0-9]+'), b'wnameX'),
    (re.compile(rb'result index [0-9]+'), b'result index N'),  # numero do recurso pg, depende de quantos resultados vieram antes
    (re.compile(rb'[0-9a-f]{32}'), b'MD5X'),
    (re.compile(rb'localhost:[0-9]{2,5}'), b'localhost:PORT'),
    (re.compile(rb'[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}'), b'DATAHORA'),
    (re.compile(rb'/(CreationDate|ModDate) ?\(D:[0-9]{14}[^)]*\)'), b'/DateX'),
]

def normaliza(b):
    for rx, rep in NORM:
        b = rx.sub(rep, b)
    return b

def casos():
    with open(os.path.join(AQUI, 'casos.tsv'), encoding='utf-8') as f:
        for l in f:
            l = l.rstrip('\n')
            if l and not l.startswith('#'):
                n, p = l.split('\t')
                yield n, p

def sh(cmd):
    return subprocess.run(cmd, capture_output=True)

def captura(a):
    sid = open(a.sessao + '.sid').read().strip()
    os.makedirs(a.saida, exist_ok=True)
    destino = f'/var/lib/php/sessions/sess_{sid}'
    for nome, caminho in casos():
        # restaura a sessao pristina antes de cada pedido
        sh(['docker', 'cp', a.sessao, f'{a.container}:{destino}'])
        sh(['docker', 'exec', '-u', 'root', a.container, 'sh', '-c', f'chown www-data:www-data {destino}; chmod 600 {destino}'])
        r = sh(['curl', '-s', '-m', '120', '-b', f'ECIDADEWINDOWMAIN={sid}', '-w', '\n@@%{http_code} %{content_type}',
                f'http://localhost:{a.porta}/{caminho}'])
        o = r.stdout
        i = o.rfind(b'\n@@')
        meta, corpo = (o[i + 3:], o[:i]) if i >= 0 else (b'000 sem-resposta', o)
        with open(os.path.join(a.saida, nome + '.out'), 'wb') as f:
            f.write(meta + b'\n' + normaliza(corpo))
        print(f'{nome}: {meta.decode(errors="replace")} ({len(corpo)} B)')
    return 0

def compara(a):
    base = a.base or os.path.join(AQUI, 'base')
    esperados = {n + '.out' for n, _ in casos()}
    dif = 0
    for arq in sorted(esperados):
        pb, pn = os.path.join(base, arq), os.path.join(a.novo, arq)
        if not os.path.exists(pb):
            print(f'FALTA na linha de base: {arq}'); dif += 1; continue
        if not os.path.exists(pn):
            print(f'FALTA na saida nova: {arq}'); dif += 1; continue
        b, n = open(pb, 'rb').read(), open(pn, 'rb').read()
        if b != n:
            dif += 1
            print(f'DIFERE: {arq}')
            for l in list(difflib.unified_diff(b.decode('latin-1').splitlines(), n.decode('latin-1').splitlines(),
                                               'base', 'novo', lineterm='', n=0))[:12]:
                print('   ', l[:200])
    print(f'{len(esperados) - dif}/{len(esperados)} iguais, {dif} diferentes')
    return 1 if dif else 0

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    c = s.add_parser('captura'); c.add_argument('--porta', required=True); c.add_argument('--container', required=True)
    c.add_argument('--sessao', required=True); c.add_argument('--saida', required=True); c.set_defaults(f=captura)
    d = s.add_parser('compara'); d.add_argument('--novo', required=True); d.add_argument('--base'); d.set_defaults(f=compara)
    a = p.parse_args()
    sys.exit(a.f(a))
