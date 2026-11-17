#!/usr/bin/env python3
"""Onde o codigo legado usa os pacotes que SAEM do conjunto novo (so leitura).

Uso: usos_pacotes.py [--saida-tsv ARQ] [--resumo-md ARQ] [--sem-banco]

Varre ecidade/ (menos vendor/ e caches) atras de classe, `use`, `new`, `require`, string de classe e `vendor/<pacote>`
de cada pacote, e classifica cada ocorrencia:
  uso      : codigo (use, new, estatico, require, string)
  comentario: linha de comentario/docblock
  alcance  : menu (tela de db_itensmenu), roteada (prefixo do location/api), cli, include (so alcancado por outro arquivo),
             morto (nada referencia) ; para include/classe, conta as telas de menu que chegam ao arquivo por referencia
             estatica (nome do arquivo ou da classe) -- SUPERESTIMA (palavra comum casa), nunca subestima.
Banco: so SELECT em db_itensmenu (docker exec ecidade_database psql). --sem-banco usa so o roteamento.
"""
import argparse, collections, os, re, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(RAIZ, 'ecidade')
EXCL = {'vendor', 'node_modules', 'storage', 'tmp', '.git'}
EXCL_CAMINHO = ('extension/modification/data',)
LARAVEL_PROPRIO = ('app/', 'routes/', 'config/', 'bootstrap/')   # codigo proprio do Laravel: contado a parte
EXT = ('.php', '.inc', '.class', '.phtml', '.lib', '.tpl', '.model')
LIMITE_NUCLEO = 500   # arquivo alcancado por mais telas de menu que isto e do nucleo (FrontController, app.php, src/V3)
LOCATION = (r'^(?:cem|itbi?|agua?|jur|div|mar|not|fis|iss|dvr|arr|tri|inf|tra|tre|esc|rel|sec|bib|mer|edu|rh|eso|rec|pes|'
            r'ac|aco|ouv|lic|vei|pat|com|cus|pla|pl|tes|emp|orc|cai|fum|hip|age|amb|tfd|vac|lab|far|sau|sys)[0-9]*_')

B = r'\\{1,2}'
PACOTES = [  # (pacote que sai, dono, [(rotulo, regex)])
    ('silex/silex', 'API V1 (Silex)', [('Silex', r'\bSilex' + B + r'\w'), ('Pimple', r'\bPimple' + B + r'\w'),
                               ('vendor/silex', r'vendor/silex')]),
    ('proner/phppimaco', 'documentos (PDF/planilha/Word/etiquetas)', [('PhpPimaco', r'\bPhpPimaco\b'), ('vendor/phppimaco', r'vendor/proner')]),
    ('dbseller/phinx_postgres + robmorgan/phinx', 'migrations Phinx',
     [('Phinx', r'\bPhinx' + B + r'\w'), ('PostgresMigration', r'Classes' + B + r'(?:PostgresMigration|Table)\b'),
      ('vendor/phinx', r'vendor/(?:robmorgan|dbseller/phinx)')]),
    ('dbseller/sdk-api-pix-bb', 'Pix BB', [('Swagger\\Client', r'\bSwagger' + B + r'Client\b'),
                                           ('vendor/sdk-api-pix', r'vendor/dbseller/sdk')]),
    ('mpdf/mpdf 7', 'documentos (PDF/planilha/Word/etiquetas)', [('new mPDF', r'\bnew\s+\\?mPDF\b'), ('Mpdf\\', r'\\?\bMpdf' + B + r'\w'),
                               ('vendor/mpdf', r'vendor/mpdf')]),
    ('phpoffice/phpspreadsheet 1.8', 'documentos (PDF/planilha/Word/etiquetas)', [('PhpSpreadsheet', r'PhpOffice' + B + r'PhpSpreadsheet'),
                                                ('vendor/phpspreadsheet', r'vendor/phpoffice/phpspreadsheet')]),
    ('phpoffice/phpword 0.17', 'documentos (PDF/planilha/Word/etiquetas)', [('PhpWord', r'PhpOffice' + B + r'PhpWord'),
                                          ('vendor/phpword', r'vendor/phpoffice/phpword')]),
    ('zendframework/zend-*', 'eventos do V3 (zend-*)', [('Zend\\', r'\bZend' + B + r'\w'), ('vendor/zend', r'vendor/zendframework')]),
]
COMPILADOS = [(p, d, [(r, re.compile(x, re.I if r.startswith('new mPDF') else 0)) for r, x in pats]) for p, d, pats in PACOTES]
USO = [('use', re.compile(r'^\s*use\s')), ('new', re.compile(r'\bnew\s')),
       ('require', re.compile(r'\b(?:require|include)(?:_once)?\b')), ('estatico', re.compile(r'::')),
       ('string', re.compile(r'["\']'))]
COMENT = re.compile(r'^\s*(?://|#|\*|/\*)')
NAMESPACE = re.compile(r'^\s*namespace\s+([\w\\]+)\s*;', re.M)
ARQ_LIT = re.compile(r'["\'](?:[^"\'\n]*[/\\])?([A-Za-z0-9_.-]+\.(?:php|inc|class))["\']')
QUALIF = re.compile(r'\\?[A-Za-z_]\w*(?:\\{1,2}[A-Za-z_]\w*)+')
PALAVRA = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
CLASSE = re.compile(r'^\s*(?:abstract\s+|final\s+)?(?:class|interface|trait)\s+([A-Za-z_]\w*)', re.M)


def arquivos():
    for d, ds, fs in os.walk(DOC):
        rel = os.path.relpath(d, DOC)
        ds[:] = [x for x in ds if not (rel == '.' and x in EXCL) and x not in ('node_modules', '.git')
                 and not any(os.path.join(rel, x).replace('\\', '/').startswith(e) for e in EXCL_CAMINHO)]
        for f in fs:
            if f.lower().endswith(EXT):
                yield os.path.normpath(os.path.join(rel, f)).replace('\\', '/')


def le(rel):
    try:
        with open(os.path.join(DOC, rel), encoding='latin-1') as fh:
            return fh.read()
    except OSError:
        return ''


def menu_stems(usar_banco):
    if not usar_banco:
        return set()
    sql = "select distinct split_part(funcao,'?',1) from db_itensmenu where funcao ~* '[.]php'"
    r = subprocess.run(['docker', 'exec', '-i', 'ecidade_database', 'psql', '-U', 'postgres', '-d', 'ecidade', '-At'],
                       input=sql.encode(), capture_output=True)
    if r.returncode:
        sys.exit('consulta do menu falhou: ' + r.stderr.decode(errors='replace')[:200])
    return {os.path.basename(l).lower() for l in r.stdout.decode('latin-1').splitlines() if l.strip()}


def classifica_uso(linha):
    if COMENT.match(linha):
        return 'comentario'
    for nome, rx in USO:
        if rx.search(linha):
            return nome
    return 'codigo'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--saida-tsv')
    ap.add_argument('--resumo-md')
    ap.add_argument('--sem-banco', action='store_true')
    a = ap.parse_args()

    todos = sorted(arquivos())
    textos, achados = {}, collections.defaultdict(list)   # arquivo -> [(pacote,dono,rotulo,linha,texto)]
    for rel in todos:
        t = le(rel)
        textos[rel] = t
        if not any(k in t for k in ('Silex', 'Pimple', 'PhpPimaco', 'Phinx', 'PostgresMigration', 'Swagger', 'mPDF', 'Mpdf',
                                    'PhpSpreadsheet', 'PhpWord', 'Zend', 'vendor/', 'phppimaco')) and 'mpdf' not in t.lower():
            continue
        for n, linha in enumerate(t.splitlines(), 1):
            for pac, dono, pats in COMPILADOS:
                for rot, rx in pats:
                    if rx.search(linha):
                        achados[rel].append((pac, dono, rot, n, linha.strip()[:160]))
                        break
    menu = menu_stems(not a.sem_banco)
    raizes = set()
    for rel in todos:
        if '/' not in rel and (re.match(LOCATION, rel, re.I) or os.path.basename(rel).lower() in menu):
            raizes.add(rel)
    # Arestas "X referencia Y" (estaticas; include dinamico nao entra -> pode SUBestimar, ver docs):
    #  1) literal 'nome.php|inc|class' em X  -> arquivos de mesmo nome-base
    #  2) nome qualificado (Namespace\\Classe) em X -> arquivo que declara essa classe (PSR-4 em src/ app/ api/)
    #  3) classe legada (sem namespace, nome >= 6 letras) citada como palavra em X
    por_base = collections.defaultdict(set)
    fqn_de, legadas = {}, collections.defaultdict(set)
    for rel in todos:
        por_base[os.path.basename(rel).lower()].add(rel)
        t = textos[rel]
        ns = NAMESPACE.search(t)
        for c in CLASSE.findall(t):
            if ns:
                fqn_de.setdefault((ns.group(1) + '\\' + c).lower(), set()).add(rel)
            elif len(c) >= 6:
                legadas[c.lower()].add(rel)
    pai = collections.defaultdict(set)      # arquivo -> arquivos que o referenciam
    for rel in todos:
        t = textos[rel]
        alvos_ = set()
        for lit in ARQ_LIT.findall(t):
            alvos_ |= por_base.get(os.path.basename(lit.replace('\\', '/')).lower(), set())
        for q in QUALIF.findall(t):
            alvos_ |= fqn_de.get(q.replace('\\\\', '\\').lstrip('\\').lower(), set())
        for w in PALAVRA.findall(t):
            alvos_ |= legadas.get(w.lower(), set())
        for d in alvos_:
            if d != rel:
                pai[d].add(rel)


    def sobe(rel):
        vistos, fila, raizes_ach = {rel}, [rel], set()
        while fila:
            x = fila.pop()
            if x in raizes:
                raizes_ach.add(x)
            for p in pai.get(x, ()):
                if p not in vistos:
                    vistos.add(p)
                    fila.append(p)
        return raizes_ach

    linhas, cache = [], {}
    for rel in sorted(achados):
        if rel.startswith(LARAVEL_PROPRIO):
            alc, n_menu, ex = 'laravel-proprio (tratado a parte)', '', ''
        elif rel.startswith('api/'):
            alc, n_menu, ex = 'roteada (FrontController api/)', '', ''
        elif rel.startswith('db/migrations/') or rel.startswith('integracao_externa/') or rel.startswith('db/'):
            alc, n_menu, ex = 'cli', '', ''
        else:
            if rel not in cache:
                cache[rel] = sobe(rel)
            rs = cache[rel]
            noMenu = sorted(r for r in rs if os.path.basename(r).lower() in menu)
            roteadas = sorted(r for r in rs if r not in noMenu)
            if rel in raizes:
                rs, noMenu = {rel} | rs, sorted({rel} | set(noMenu)) if os.path.basename(rel).lower() in menu else noMenu
            if len(noMenu) > LIMITE_NUCLEO:
                alc, n_menu, ex = 'menu (nucleo: carregado por quase toda tela)', len(noMenu), ''
            elif noMenu:
                alc, n_menu, ex = 'menu', len(noMenu), ','.join(noMenu[:3])
            elif roteadas or rel in raizes:
                alc, n_menu, ex = 'roteada (location, fora do menu)', 0, ','.join(roteadas[:3] or [rel])
            else:
                alc, n_menu, ex = 'sem referencia estatica (JS/URL nao varridos)', 0, ''
        for pac, dono, rot, n, txt in achados[rel]:
            uso = classifica_uso(txt)
            al = alc if uso != 'comentario' else 'comentario (nao executa)'
            linhas.append((pac, dono, '%s:%d' % (rel, n), rot, uso, al, n_menu, ex, txt))

    cab = ('pacote', 'dono', 'arquivo:linha', 'padrao', 'uso', 'alcance', 'telas_menu', 'exemplos', 'trecho')
    if a.saida_tsv:
        with open(a.saida_tsv, 'w', encoding='utf-8') as fh:
            fh.write('\t'.join(cab) + '\n')
            for l in linhas:
                fh.write('\t'.join(str(x).replace('\t', ' ') for x in l) + '\n')
    resumo(linhas, a.resumo_md)
    return 0


def resumo(linhas, caminho):
    por = collections.OrderedDict((p, [l for l in linhas if l[0] == p]) for p, _, _ in PACOTES)
    out = ['| Pacote que sai | Dono | Ocorrências | Arquivos | Código (≠ comentário) | Tela de menu | Núcleo (quase toda tela) | Roteada (api/location) | CLI (migrations) | Sem referência estática | Laravel próprio (tratado a parte) |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    for (p, d, _) in PACOTES:
        ls = por[p]
        cod = [l for l in ls if l[4] != 'comentario']
        arq = lambda xs: len({x[2].rsplit(':', 1)[0] for x in xs})
        g = lambda pref: arq([l for l in cod if l[5].startswith(pref)])
        out.append('| `%s` | %s | %d | %d | %d (%d arq.) | %d arq. | %d arq. | %d arq. | %d arq. | %d arq. | %d arq. |' % (
            p, d, len(ls), arq(ls), len(cod), arq(cod), g('menu') - g('menu (nucleo'), g('menu (nucleo'), g('roteada'),
            g('cli'), g('sem referencia'), g('laravel')))
    txt = '\n'.join(out)
    print(txt)
    if caminho:
        with open(caminho, 'w', encoding='utf-8') as fh:
            fh.write(txt + '\n')


if __name__ == '__main__':
    sys.exit(main())
