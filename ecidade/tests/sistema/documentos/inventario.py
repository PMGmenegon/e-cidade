#!/usr/bin/env python3
"""Inventario das bibliotecas que emitem documentos (PDF, planilha, Word, QR, codigo de barras).

Uso (na raiz da worktree):  python3 ecidade/tests/sistema/documentos/inventario.py [--menu ARQ] [--json ARQ]
  --menu ARQ  lista de telas de menu (uma por linha; SELECT distinct trim(funcao) FROM db_itensmenu, so leitura)
  --json ARQ  grava o resultado completo (por biblioteca: arquivos diretos, telas da raiz que chegam, telas de menu)

Para cada biblioteca: arquivos que a usam DIRETAMENTE (padrao no codigo) e telas da RAIZ de ecidade/ que chegam a ela
por include/require ou por referencia a classe, ate PROF=2 niveis (cota superior; classe com namespace so casa pelo nome qualificado ou
pelo mesmo namespace; nos com mais de HUB consumidores nao sao ponte). Le tudo como latin-1 (a base e 64% ISO-8859-1). Nao grava nada no repositorio nem no banco.
"""
import argparse, collections, json, os, re, sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
SKIP = ('vendor', 'tmp', 'node_modules', '.git', 'db/migrations', 'database/migrations', 'extension/modification/data')

PROF = 2    # niveis de indirecao seguidos a partir do uso direto (mais fundo que isso o casamento por nome de classe vira ruido)
HUB = 300  # no com mais consumidores que isto e biblioteca comum, nao ponte para a tela

BIB = [  # (nome, padrao que marca o uso direto)
    ('FPDF 1.51 (fpdf151/, db_conectapdf)', r'fpdf151/|db_conectapdf'),
    ('dbagata (relatorios Agata)',           r'dbagata/|\bAgata\b'),
    ('mPDF',                                 r'Mpdf\\|mPDF|mpdf/'),
    ('Dompdf',                               r'Dompdf'),
    ('FPDI',                                 r'\bFPDI\b'),
    ('PhpSpreadsheet',                       r'PhpSpreadsheet'),
    ('PHPExcel',                             r'PHPExcel'),
    ('PhpWord',                              r'PhpWord'),
    ('Pimaco (etiquetas)',                   r'(?i)pimaco'),
    ('QR (endroid/phpqrcode/bacon)',         r'Endroid\\QrCode|QRcode::|phpqrcode|BaconQrCode|\bQrCode\b'),
    ('Codigo de barras (db_barras/2of5)',    r'db_barras|geraCodigoBarras|int25|barcode2of5'),
    ('Excel por header (HTML/CSV como .xls)', r'vnd\.ms-excel|application/excel'),
    ('Word por header (HTML como .doc)',     r'application/msword|vnd\.ms-word'),
]

def lista():
    for dp, dn, fn in os.walk(RAIZ):
        rel = os.path.relpath(dp, RAIZ).replace(os.sep, '/')
        if any(rel == s or rel.startswith(s + '/') for s in SKIP):
            dn[:] = []; continue
        for f in fn:
            if f.endswith('.php'):
                yield os.path.normpath(os.path.join(rel, f)).replace(os.sep, '/')

def grafo():
    arqs = sorted(lista())
    txt = {}
    for p in arqs:
        try: txt[p] = open(os.path.join(RAIZ, p), 'rb').read().decode('latin-1')
        except OSError: pass
    # definicoes: nome qualificado / nome curto -> arquivo
    rdef = re.compile(r'^\s*(?:abstract\s+|final\s+)?(?:class|interface|trait)\s+([A-Za-z_]\w*)', re.M)
    rns = re.compile(r'^\s*namespace\s+([\w\\]+)\s*;', re.M)
    ns = {}; fqn = {}; curto = collections.defaultdict(set); ns_curto = collections.defaultdict(set)
    for p, t in txt.items():
        m = rns.search(t); ns[p] = m.group(1) if m else ''
        for c in rdef.findall(t):
            if ns[p]: fqn[ns[p] + '\\' + c] = p; ns_curto[c].add(p)
            else: curto[c].add(p)
    # arestas consumidor -> definidor
    base = collections.defaultdict(set)
    for p in txt: base[os.path.basename(p)].add(p)
    rinc = re.compile(r'(?:include|require)(?:_once)?\b[^;]*?;', re.S)
    rpath = re.compile(r'([\w./\-]+\.php)')
    rpal = re.compile(r'[A-Za-z_]\w*')
    deps = collections.defaultdict(set)  # arquivo -> arquivos de que depende
    for p, t in txt.items():
        for st in rinc.findall(t):
            for lit in rpath.findall(st):
                alvo = base.get(os.path.basename(lit), ())
                if len(alvo) <= 3: deps[p].update(alvo)
        palavras = set(rpal.findall(t))
        for c in palavras & curto.keys(): deps[p].update(curto[c])
        for c in palavras & ns_curto.keys():
            for q in ns_curto[c]:
                f = ns[q] + '\\' + c
                if ns[p] == ns[q] or f in t or f.replace('\\', '\\\\') in t or ('use ' + f) in t:
                    deps[p].add(q)
        deps[p].discard(p)
    rev = collections.defaultdict(set)
    for p, ds in deps.items():
        for d in ds: rev[d].add(p)
    return txt, deps, rev

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--menu'); ap.add_argument('--json')
    a = ap.parse_args()
    menu = set(l.strip() for l in open(a.menu, encoding='latin-1')) if a.menu else set()
    txt, deps, rev = grafo()
    saida = {}
    for nome, pad in BIB:
        rx = re.compile(pad)
        propria = ('fpdf151/',) if nome.startswith('FPDF') else ('dbagata/',) if nome.startswith('dbagata') else ()
        diretos = sorted(p for p, t in txt.items() if rx.search(t) and not p.startswith(propria + ('libs/jpgraph',)))
        prof = {d: 0 for d in diretos}; fila = list(diretos)
        while fila:
            n = fila.pop(0)
            if prof[n] >= PROF or (len(rev.get(n, ())) > HUB and n not in diretos): continue  # hub (db_stdlib...) nao e ponte
            for c in rev.get(n, ()):
                if c not in prof: prof[c] = prof[n] + 1; fila.append(c)
        vistos = set(prof)
        telas = sorted(p for p in vistos if '/' not in p)
        saida[nome] = {'diretos': diretos, 'telas_raiz': telas, 'telas_menu': [p for p in telas if p in menu]}
    print('%-42s %8s %10s %10s' % ('biblioteca', 'diretos', 'telas raiz', 'telas menu'))
    for nome, r in saida.items():
        print('%-42s %8d %10d %10d' % (nome, len(r['diretos']), len(r['telas_raiz']), len(r['telas_menu'])))
    if a.json: json.dump(saida, open(a.json, 'w'), indent=1)

if __name__ == '__main__':
    main()
