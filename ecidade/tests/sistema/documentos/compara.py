#!/usr/bin/env python3
"""Roda os geradores de documento no 7.4 e no 8.5 (sem banco, via docker/composer-85/roda-isolado.sh) e compara por conteudo.
PDF: paginas, tamanho de pagina, texto, posicao das palavras e imagens. xlsx/docx: partes do zip (datas internas normalizadas).
PNG: pixels. Uso (raiz do repositorio): python3 ecidade/tests/sistema/documentos/compara.py [gerador ...]  -> rc 1 se algum difere."""
import base64, hashlib, io, json, os, re, subprocess, sys, tempfile, zipfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
RODA = os.path.join(RAIZ, 'docker/composer-85/roda-isolado.sh')
IMAGENS = {'7.4': 'ecidade-php74-cli', '8.5': 'ecidade-composer-85:2.11.2'}
GERADORES = ['gera_dompdf', 'gera_mpdf', 'gera_planilha', 'gera_word', 'gera_etiquetas']


def roda(versao, gerador):
    env = dict(os.environ, IMAGEM=IMAGENS[versao])
    if versao == '7.4':
        env['VENDOR'] = os.path.join(RAIZ, 'runtime-85/referencia-74/vendor')  # vendor do composer.lock do PR
    p = subprocess.run(['bash', RODA, versao, os.path.join(os.path.dirname(__file__), gerador + '.php')],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        sys.exit('ERRO: %s no %s rc=%d\n%s' % (gerador, versao, p.returncode, p.stderr[-1500:]))
    docs = {}
    for l in p.stdout.splitlines():
        if l.startswith('{"nome"'):
            d = json.loads(l)
            docs[d['nome']] = base64.b64decode(d['b64'])
    avisos = [l for l in p.stderr.splitlines() if re.match(r'(Deprecated|Warning|Notice):', l)]
    return docs, avisos


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def resumo_pdf(b):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(b); f.flush()
        info = sh('pdfinfo', f.name)
        paginas = re.search(r'Pages:\s+(\d+)', info).group(1)
        tam = re.search(r'Page size:\s+(.*)', info).group(1)
        texto = sh('pdftotext', '-layout', f.name, '-')
        bbox = sh('pdftotext', '-bbox', f.name, '-')
        palavras = re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)"[^>]*>(.*?)</word>', bbox)
        imgs = [re.sub(r'^\s*\d+\s+\d+\s+', '', l) for l in sh('pdfimages', '-list', f.name).splitlines()[2:]]
        return {'paginas': paginas, 'tamanho': tam, 'texto': texto,
                'posicoes': [(round(float(x), 1), round(float(y), 1), w) for x, y, w in palavras],
                'imagens': [' '.join(l.split()[:4]) for l in imgs]}


def norm_xml(b):
    s = b.decode('utf-8', 'replace')
    s = re.sub(r'(<(?:dcterms:created|dcterms:modified|cp:lastModifiedBy|dc:creator|Application|meta:creation-date|dc:date)[^>]*>)[^<]*', r'\1', s)
    s = re.sub(r'\b(rsid\w*|w14:paraId|w14:textId)="[0-9A-Fa-f]+"', '', s)
    return s


def resumo_zip(b):
    z = zipfile.ZipFile(io.BytesIO(b))
    return {n: hashlib.sha256(norm_xml(z.read(n)).encode() if n.endswith(('.xml', '.rels')) else z.read(n)).hexdigest()
            for n in sorted(z.namelist())}


def resumo_png(b):
    from PIL import Image
    im = Image.open(io.BytesIO(b)).convert('RGBA')
    return {'tam': im.size, 'pixels': hashlib.sha256(im.tobytes()).hexdigest()}


def resumo(nome, b):
    if nome.endswith('.pdf'): return resumo_pdf(b)
    if nome.endswith(('.xlsx', '.docx')): return resumo_zip(b)
    if nome.endswith('.png'): return resumo_png(b)
    return {'sha': hashlib.sha256(b).hexdigest()}


def main():
    sel = sys.argv[1:] or GERADORES
    dif = 0
    for g in sel:
        d74, a74 = roda('7.4', g)
        d85, a85 = roda('8.5', g)
        print('== %s: %d documentos no 7.4, %d no 8.5; avisos 7.4=%d, 8.5=%d' % (g, len(d74), len(d85), len(a74), len(a85)))
        if not d74 or set(d74) != set(d85):
            print('  DIFERE: conjuntos de documentos (%s x %s)' % (sorted(d74), sorted(d85))); dif += 1; continue
        for nome in sorted(d74):
            r74, r85 = resumo(nome, d74[nome]), resumo(nome, d85[nome])
            if r74 == r85:
                print('  igual   %s' % nome)
            else:
                dif += 1
                chaves = [k for k in r74 if r74[k] != r85.get(k)] if isinstance(r74, dict) and all(k in r85 for k in r74) else ['conteudo']
                print('  DIFERE  %s: %s' % (nome, ', '.join(str(k)[:60] for k in chaves[:8])))
        for rotulo, av in (('7.4', a74), ('8.5', a85)):
            for t, n in sorted(__import__('collections').Counter(re.sub(r' in /app/.*| on line \d+', '', a)[:110] for a in av).items()):
                print('  aviso %s x%d: %s' % (rotulo, n, t))
    print('DIFERENCAS: %d' % dif)
    sys.exit(1 if dif else 0)


if __name__ == '__main__':
    main()
