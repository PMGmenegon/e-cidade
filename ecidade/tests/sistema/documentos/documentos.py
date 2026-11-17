#!/usr/bin/env python3
"""Linha de base dos documentos emitidos (PDF, planilha, Word, QR/codigo de barras).

  captura --sessao ARQ --saida DIR [--p56 8130 --c56 ecidade_doc_56 --p85 8131 --c85 ecidade_doc_85]
  compara --dir DIR                      sai 1 se algum caso difere entre 5.6 e 8.5 (comparacao ESTRUTURAL)
  confere --dir DIR --base DIR           sai 1 se algum caso difere da linha de base guardada (repeticao)

Containers: SOMENTE_LEITURA=1 para o que a triagem nao liberou; para emissor triado (so grava db_usuariosonline/db_logsacessa)
container que grava com --vigia (script do vigia do banco, apontado por VIGIA, antes/depois de cada pedido; 1o alerta = PARE, sai 3, nada e limpo). ARQ e a sessao criada por
sessao.sh (tests/sistema/relatorios-kernel/): ela e restaurada antes de CADA pedido, nos dois containers. casos.tsv: nome<TAB>biblioteca<TAB>caminho[<TAB>diverge:motivo]; caminho 'cli:<script.php>' = duble rodado por CLI no container.
Para cada caso e runtime grava <nome>.<56|85>.txt com a descricao estrutural normalizada:
  PDF   -> paginas, tamanho de pagina, texto extraido (pdftotext -layout), numero de imagens, hash do conteudo das imagens
  xlsx  -> abas, dimensoes, celulas (valores)         HTML/.xls/.doc -> texto sem tags     outros -> cabecalho + corpo
O corpo bruto vai para <nome>.<56|85>.bin (fora do git; --saida deve ser uma pasta de trabalho).
Saida: 0 igual / 1 difere / 2 uso / 3 vigia acusou escrita fora do permitido (captura).
"""
import argparse, hashlib, io, os, re, subprocess, sys, tempfile, zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))

NORM = [
    (re.compile(rb'sid=[0-9a-f]{8,}'), b'sid=X'),
    (re.compile(rb'localhost:[0-9]{2,5}'), b'localhost:PORT'),
    (re.compile(rb'[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}'), b'DATAHORA'),
    (re.compile(rb'tmp/[A-Za-z0-9_]+\.(?:pdf|csv|txt|xls|xlsx|doc|docx)'), b'tmp/X.arq'),
    (re.compile(rb'wname[0-9]+'), b'wnameX'),
]

def norm(b):
    for rx, rep in NORM:
        b = rx.sub(rep, b)
    return b

TEXTO = [  # data/hora de emissao impressas no rodape do documento (mudam a cada segundo; o resto do texto fica)
    (re.compile(r'(?<!\d)\d{2}:\d{2}:\d{2}(?!\d)'), 'HH:MM:SS'),
    (re.compile(r'(?i)\b(data|data emiss[ãa]o):\s*\d{2}[-/]\d{2}[-/]\d{4}'), r'\1: DD/MM/AAAA'),
]

def norm_texto(t):
    for rx, rep in TEXTO:
        t = rx.sub(rep, t)
    return t

def norm_bytes(b):
    b = re.sub(rb'(?<!\d)\d{2}:\d{2}:\d{2}(?!\d)', b'HH:MM:SS', b)
    return re.sub(rb'(?i)\b(data|data emiss[\xe3a]o):\s*\d{2}[-/]\d{2}[-/]\d{4}', rb'\1: DD/MM/AAAA', b)

def sh(cmd, entrada=None):
    return subprocess.run(cmd, capture_output=True, input=entrada)

def casos():
    with open(os.path.join(AQUI, 'casos.tsv'), encoding='utf-8') as f:
        for l in f:
            l = l.rstrip('\n')
            if l and not l.startswith('#'):
                c = l.split('\t')
                yield c[0], c[1], c[2], (c[3] if len(c) > 3 else '')

def pdf(corpo):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as t:
        t.write(corpo); t.flush()
        info = sh(['pdfinfo', t.name]).stdout.decode('latin-1')
        pag = re.search(r'Pages:\s+(\d+)', info); tam = re.search(r'Page size:\s+(.*)', info)
        txt = sh(['pdftotext', '-layout', '-enc', 'UTF-8', t.name, '-']).stdout.decode('utf-8', 'replace')
        im = sh(['pdfimages', '-list', t.name]).stdout.decode('latin-1').splitlines()[2:]
        hashes = []
        d = tempfile.mkdtemp()
        sh(['pdfimages', '-png', t.name, d + '/i'])
        for f in sorted(os.listdir(d)):
            hashes.append(hashlib.sha256(open(os.path.join(d, f), 'rb').read()).hexdigest()[:16]); os.unlink(os.path.join(d, f))
        os.rmdir(d)
    try:
        import pypdf
        rd = pypdf.PdfReader(io.BytesIO(corpo))
        cont = []
        for pg in rd.pages:
            c = pg.get_contents()
            b = c.get_data() if c is not None else b''
            b = norm_bytes(b)
            cont.append(hashlib.sha256(b).hexdigest()[:12])
    except Exception as e:
        cont = [f'ilegivel:{type(e).__name__}']
    return (f'tipo: pdf\nconteudo-paginas: {cont}\npaginas: {pag.group(1) if pag else "?"}\ntamanho: {tam.group(1) if tam else "?"}\n'
            f'imagens: {len(im)} {hashes}\n--- texto ---\n{norm_texto(txt)}')

def xlsx(corpo):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(corpo), data_only=False)
    out = ['tipo: xlsx', 'abas: ' + repr(wb.sheetnames)]
    for ws in wb.worksheets:
        out.append(f'--- aba {ws.title} {ws.dimensions} ---')
        for row in ws.iter_rows():
            v = [str(c.value) for c in row if c.value is not None]
            if v: out.append(' | '.join(v))
    return '\n'.join(out) + '\n'

def docx(corpo):
    z = zipfile.ZipFile(io.BytesIO(corpo))
    x = z.read('word/document.xml').decode('utf-8', 'replace')
    x = re.sub(r'</w:p>', '\n', x); x = re.sub(r'<[^>]+>', '', x)
    return f'tipo: docx\narquivos: {sorted(z.namelist())}\n--- texto ---\n{x}\n'

def descreve(corpo, ctype):
    c = corpo
    if c[:5] == b'%PDF-':
        return pdf(c)
    if c[:2] == b'PK':
        z = zipfile.ZipFile(io.BytesIO(c)); n = z.namelist()
        if any(a.startswith('xl/') for a in n): return xlsx(c)
        if any(a.startswith('word/') for a in n): return docx(c)
        return f'tipo: zip\narquivos: {sorted(n)}\n'
    t = norm(c).decode('latin-1')
    if re.search(r'(?i)<(html|table|body)', t):
        t = re.sub(r'(?is)<(script|style).*?</\1>', '', t); t = re.sub(r'<[^>]+>', ' ', t)
        t = re.sub(r'[ \t\r]+', ' ', t); t = re.sub(r'\n\s*\n+', '\n', t)
        return f'tipo: html/texto\n--- texto ---\n{norm_texto(t)}\n'
    return f'tipo: outro ({ctype})\n--- corpo ---\n{t}\n'

def pede(porta, container, sessao, sid, caminho):
    if caminho.startswith('cli:'):  # dubles: script PHP rodado no container (sem HTTP, sem banco)
        r = sh(['docker', 'exec', '-w', '/var/www/html', container, 'php', '-d', 'display_errors=stderr', caminho[4:]])
        # avisos do PHP no stderr, sem os Deprecated do vendor antigo (os 2 runtimes os emitem em numero diferente)
        erro = b'\n'.join(sorted(set(re.sub(rb'/var/www/html', b'', l) for l in r.stderr.splitlines() if l.strip() and not l.startswith(b'Deprecated'))))
        if r.returncode != 0 or not r.stdout:  # o erro do PHP e o resultado
            return '500 text/plain', b'rc=%d\n' % r.returncode + erro[:600], b''
        return '200 ' + ('application/pdf' if r.stdout[:5] == b'%PDF-' else 'application/zip' if r.stdout[:2] == b'PK' else 'text/plain'), r.stdout, erro
    destino = f'/var/lib/php/sessions/sess_{sid}'
    sh(['docker', 'cp', sessao, f'{container}:{destino}'])
    sh(['docker', 'exec', '-u', 'root', container, 'sh', '-c', f'chown www-data:www-data {destino}; chmod 600 {destino}'])
    r = sh(['curl', '-s', '-m', '120', '-b', f'ECIDADEWINDOWMAIN={sid}', '-w', '\n@@%{http_code} %{content_type}',
            f'http://localhost:{porta}/{caminho}'])
    o = r.stdout; i = o.rfind(b'\n@@')
    meta, corpo = (o[i + 3:].decode(errors='replace'), o[:i]) if i >= 0 else ('000 sem-resposta', o)
    # relatorios Agata/db_redireciona: a resposta e <script>location.href='tmp/arquivo'</script>; o documento e o arquivo
    m = re.fullmatch(rb"\s*<script>location\.href='([^']+)'</script>\s*", corpo)
    if m and not m.group(1).startswith((b'http', b'db_erros')):
        r = sh(['curl', '-s', '-m', '120', '-b', f'ECIDADEWINDOWMAIN={sid}', '-w', '\n@@%{http_code} %{content_type}',
                f'http://localhost:{porta}/' + m.group(1).decode()])
        o = r.stdout; i = o.rfind(b'\n@@')
        meta, corpo = (o[i + 3:].decode(errors='replace'), o[:i]) if i >= 0 else ('000 sem-resposta', o)
    return meta, corpo, b''

VIGIA = os.environ.get('VIGIA')  # script: 'antes <foto>' / 'depois <foto>'; sai 0 (so tabelas permitidas) ou 3 (escrita fora do permitido)

def vigia(modo, foto):
    """antes/depois do vigia do banco. 'depois' devolve (rc, saida); rc 3 = escrita fora do permitido -> PARE."""
    r = sh(['bash', VIGIA, modo, foto])
    return r.returncode, (r.stdout + r.stderr).decode(errors='replace')

def captura(a):
    if a.vigia and not VIGIA:
        print('defina VIGIA=<script do vigia do banco> para usar --vigia'); return 2
    sid = open(a.sessao + '.sid').read().strip()
    os.makedirs(a.saida, exist_ok=True)
    for nome, _, caminho, _x in casos():
        for rt, porta, cont in (('56', a.p56, a.c56), ('85', a.p85, a.c85)):
            foto = os.path.join(a.saida, f'{nome}.{rt}.foto')
            if a.vigia: vigia('antes', foto)
            meta, corpo, avisos = pede(porta, cont, a.sessao, sid, caminho)
            if a.vigia:
                rc, vs = vigia('depois', foto)
                open(os.path.join(a.saida, f'{nome}.{rt}.vigia'), 'w').write(vs)
                if rc != 0:
                    print(f'PARE: vigia rc={rc} em {nome} ({rt}):\n{vs}'); return 3
            code, _, ctype = meta.partition(' ')
            try: desc = descreve(corpo, ctype)
            except Exception as e: desc = f'tipo: ilegivel ({type(e).__name__}: {e})\n'
            with open(os.path.join(a.saida, f'{nome}.{rt}.txt'), 'w', encoding='utf-8') as f:
                f.write(f'http: {code}\ncontent-type: {ctype.split(";")[0]}\nbytes: {len(corpo)}\n'
                        + (f'avisos-php:\n{avisos.decode("latin-1")}\n' if avisos else '') + desc)
            with open(os.path.join(a.saida, f'{nome}.{rt}.bin'), 'wb') as f: f.write(corpo)
            print(f'{nome} {rt}: {code} {ctype.split(";")[0]} ({len(corpo)} B)')
    return 0

def ler(p):
    # bytes/http: o tamanho bruto varia (datas, ids); a comparacao e pela descricao estrutural, sem a linha "bytes:"
    return re.sub(r'^bytes: \d+\n', '', open(p, encoding='utf-8').read(), flags=re.M)

def compara(a):
    dif = 0; n = 0; conhecidas = 0
    for nome, bib, _, esperado in casos():
        n += 1
        p56, p85 = os.path.join(a.dir, nome + '.56.txt'), os.path.join(a.dir, nome + '.85.txt')
        if not (os.path.exists(p56) and os.path.exists(p85)): print(f'FALTA: {nome}'); dif += 1; continue
        igual = ler(p56) == ler(p85)
        if esperado.startswith('diverge') and not igual:
            conhecidas += 1; print(f'DIVERGE (conhecida): {nome} ({bib}) - {esperado[8:]}')
        elif esperado.startswith('diverge') and igual:
            dif += 1; print(f'AGORA IGUAL (atualize a coluna 4 e a linha de base): {nome}')
        elif not igual:
            dif += 1; print(f'DIFERE 5.6 x 8.5: {nome} ({bib})')
    print(f'{n - dif - conhecidas}/{n} iguais, {conhecidas} divergencias conhecidas, {dif} novas/diferentes'); return 1 if dif else 0

def confere(a):
    dif = 0; n = 0
    for nome, _, _b, _x in casos():
        for rt in ('56', '85'):
            n += 1
            pb, pn = os.path.join(a.base, f'{nome}.{rt}.txt'), os.path.join(a.dir, f'{nome}.{rt}.txt')
            if not (os.path.exists(pb) and os.path.exists(pn)): print(f'FALTA: {nome}.{rt}'); dif += 1; continue
            if ler(pb) != ler(pn): dif += 1; print(f'DIFERE da base: {nome}.{rt}')
    print(f'{n - dif}/{n} iguais a linha de base, {dif} diferentes'); return 1 if dif else 0

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    c = s.add_parser('captura'); c.add_argument('--sessao', required=True); c.add_argument('--saida', required=True)
    c.add_argument('--p56', default='8130'); c.add_argument('--c56', default='ecidade_doc_56')
    c.add_argument('--vigia', action='store_true', help='vigia do banco (env VIGIA) antes/depois de CADA pedido (container que grava); rc 3 = PARE')
    c.add_argument('--p85', default='8131'); c.add_argument('--c85', default='ecidade_doc_85'); c.set_defaults(f=captura)
    d = s.add_parser('compara'); d.add_argument('--dir', required=True); d.set_defaults(f=compara)
    e = s.add_parser('confere'); e.add_argument('--dir', required=True); e.add_argument('--base', required=True); e.set_defaults(f=confere)
    a = p.parse_args(); sys.exit(a.f(a))
