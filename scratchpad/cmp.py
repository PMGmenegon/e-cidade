#!/usr/bin/env python3
"""Compara as telas do e-cidade entre dois runtimes (camada "sistema" da suite).

Restaura uma sessao autenticada antes de CADA requisicao (uma requisicao a
consome/reescreve) e normaliza os identificadores aleatorios, que senao geram
falsos positivos -- alguns deles INTERMITENTES, que e o pior tipo.

USO LEGADO (inalterado): cmp.py SID PREFIXO [SAIDA.tsv]
    lado A = 5.6 em :8080 (ecidade_php56); lado B = PORTA_B (padrao 8085).
    Env: PORTA_B, ONLY (lista separada por virgula), NORM_MENU=1.

USO PARAMETRIZADO:
    cmp.py --sid SID --a [HOST:]PORTA@CONTAINER --b [HOST:]PORTA@CONTAINER  SELECAO  [opcoes]
    SELECAO (uma ou mais; a uniao e comparada):
      --prefixo REGEX     arquivos .php do docroot cujo nome casa REGEX (ex.: '^cem1_')
      --telas ARQUIVO     lista de telas (uma por linha; '#' comenta; com ou sem .php)
      --menu              telas de menu das areas migradas (le o banco, SO LEITURA)
      --completa          todos os prefixos do location do nginx + menu
    --conhecidas TSV      divergencias ja caracterizadas (padrao: scratchpad/sistema/divergencias_conhecidas.tsv)
    --json ARQUIVO        relatorio estruturado
    --saida ARQUIVO       TSV das divergentes NOVAS (formato legado)
    --login-em LADO       (no lugar de --sid) faz login dbseller NESSE runtime e monta a sessao, que e copiada para A e B.
                          Login/token nao funcionam em container SOMENTE_LEITURA=1; o LADO e um container gravavel a parte.
    --vigia               (regra do cliente, 13/11) TELA DE MENU roda em container que grava + vigia do banco: tira a foto
                          antes, confere depois (so db_logsacessa pode mudar) e sai com 3 se algo mais mudou -- PARE e avise
                          o Lider. --vigia-permitir T1,T2 amplia a lista. RELATORIO roda so em containers SOMENTE_LEITURA=1 (sobe-ambiente.sh), sem --vigia.
    --rotulo-a/--rotulo-b nome do runtime nas mensagens (padrao: 'A <lado>' / 'B <lado>')

Saida: 0 = nenhuma divergencia NOVA; 1 = ha divergencia/timeout novo; 2 = erro de uso; 3 = o vigia viu escrita indevida.
Divergencia listada em --conhecidas aparece como CONHECIDA, com a referencia, e nao conta.
"""
import argparse, hashlib, json, os, re, shlex, subprocess, sys, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCROOT = os.path.join(RAIZ, 'ecidade')
VIGIA = os.environ.get('VIGIA', '')  # caminho do vigia-banco.sh
CONHECIDAS_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sistema', 'divergencias_conhecidas.tsv')

# Prefixos que o location do nginx serve (CLAUDE.md, "Rota no nginx").
PREFIXOS_LOCATION = ('cem|itbi?|agua?|jur|div|mar|not|fis|iss|dvr|arr|tri|inf|tra|tre|esc|rel|sec|bib|mer|edu|rh|eso|'
                     'rec|pes|ac|aco|ouv|lic|vei|pat|com|cus|pla|pl|tes|emp|orc|cai|fum|hip|age|amb|tfd|vac|lab|far|'
                     'sau|sys')
REGEX_LOCATION = r'^(?:%s)[0-9]*_' % PREFIXOS_LOCATION

# Areas migradas (atendcadarea): Tributario, Financeiro, RH, Patrimonial, Educacao, Saude, Configuracao.
AREAS_MIGRADAS = (1, 2, 3, 4, 8, 9, 11)

# Telas que contatam servico EXTERNO real: a bateria nao pode disparar conexao a
# terceiros. iss4_siss002 tem fixo o IP do SISS (200.192.137.56); o pg_connect leva
# ~134 s para desistir, igual nos dois runtimes -- nao e regressao, e rede.
PULAR = {'iss4_siss002.php'}

SQL_MENU = """
with recursive t as (
 select a.at26_codarea area, a.at26_id_item mod, m.id_item_filho id
   from atendcadareamod a join db_menu m on m.id_item=a.at26_id_item and m.modulo=a.at26_id_item
  where a.at26_codarea in (%s)
 union
 select t.area, t.mod, m.id_item_filho from t join db_menu m on m.id_item=t.id and m.modulo=t.mod)
select distinct split_part(i.funcao,'?',1) from t join db_itensmenu i on i.id_item=t.id
 where i.funcao ~* '[.]php' order by 1;
"""

BASE_NORM = [
    (re.compile(rb'sid=[0-9a-f]{8,}'),            b'sid=X'),
    (re.compile(rb'arquivo=[A-Za-z0-9+/=]{12,}'), b'arquivo=X'),
    (re.compile(rb'wname[0-9]+'),                 b'wnameX'),
    (re.compile(rb'iframe[A-Za-z0-9]{4,}\.php'),  b'iframeX.php'),
    (re.compile(rb'[0-9a-f]{32}'),                b'MD5X'),
    (re.compile(rb'nomeArquivo[^\s"\']*'),        b'nomeArquivoX'),
    # PDF temporario: o nome carrega PID e timestamp, aleatorios por requisicao.
    (re.compile(rb'tmp/[A-Za-z0-9_]+\.pdf'),      b'tmp/X.pdf'),
    # CSV/TXT temporario com timestamp no nome (arquivo_infra_escola_1791906927.csv);
    # dentro de JSON a barra vem escapada (tmp\/...). Achado no edu2.
    (re.compile(rb'tmp\\?/[A-Za-z0-9_]+\.(?:csv|txt)'), b'tmp/X.arq'),
    # Data de criacao gravada dentro do PDF pelo FPDF: muda se as duas
    # requisicoes cairem em segundos diferentes. Passou a aparecer depois que
    # tmp/ virou gravavel e os relatorios comecaram a ser gerados de fato.
    (re.compile(rb'/(CreationDate|ModDate) ?\(D:[0-9]{14}[^)]*\)'), b'/DateX'),
]

# NORM_MENU=1: troca o trecho emitido pelo db_menu() por um marcador nos DOIS lados.
# Usado so na comparacao com o TCC de referencia, onde o desktop vem desligado por um
# defeito do codigo dele (a camada V3 perde o login da sessao) e o db_menu() emite o
# menu classico (~400 linhas) no lugar do estilo/script do desktop. Separa esse defeito
# unico, sistematico, dos defeitos por tela.
MENU = [re.compile(rb'<style>\s*\nbody\.no-menu.*?</script>\n?', re.S),                          # ramo desktop
        re.compile(rb'<div id="db-menu">.*?</div>(?=<div id="db-tooltip")', re.S),                # ramo classico: menu
        re.compile(rb'<script>\s*\(window\.CurrentWindow \|\| parent\.CurrentWindow\)\.bstatus.*?autoCompleteMenu\(\);\s*\}\s*</script>', re.S)]  # classico: status

# Porta legada -> container (uso sem --b).
CONTAINER_LEGADO = {8085: 'ecidade_php85', 8086: 'ecidade_tcc_gerson', 8087: 'ecidade_lar12'}


class Lado:
    """Um runtime: host, porta e container (o container serve para sessao e para matar PHP preso)."""
    def __init__(self, host, porta, container, rotulo=None):
        self.host, self.porta, self.container = host, int(porta), container
        self.rotulo = rotulo or ('%s:%d' % (host, self.porta))

    def base(self):
        return 'http://%s:%d' % (self.host, self.porta)


def parse_lado(texto, rotulo=None):
    """[HOST:]PORTA@CONTAINER -> Lado."""
    m = re.fullmatch(r'(?:([A-Za-z0-9_.-]+):)?([0-9]{2,5})@([A-Za-z0-9_.-]+)', texto or '')
    if not m:
        raise ValueError("lado invalido %r: use [HOST:]PORTA@CONTAINER" % texto)
    return Lado(m.group(1) or 'localhost', m.group(2), m.group(3), rotulo)


def normalizadores(lados):
    """A pagina de erro monta URL absoluta a partir de HTTP_HOST (ver $DB_URL_ABS), entao
    carrega host:porta do runtime que a serviu. Diferenca por construcao: normaliza as portas dos lados."""
    extra = [(re.compile(re.escape(('%s:%d' % (l.host, l.porta)).encode())), b'localhost:PORT') for l in lados]
    return extra + BASE_NORM


def norm(b, regras):
    for rx, rep in regras:
        b = rx.sub(rep, b)
    return b


def nome_tela(t):
    """'y.php?a=1' -> 'y.php'; 'cem1_x' -> 'cem1_x.php'."""
    t = t.strip().split('?')[0]
    return t if t.lower().endswith('.php') else t + '.php'


def le_telas(caminho):
    with open(caminho, encoding='latin-1') as fh:
        return [nome_tela(l) for l in fh if l.strip() and not l.lstrip().startswith('#')]


def carrega_conhecidas(caminho):
    """TSV: tela<TAB>tipo(DIVERGE|TIMEOUT)<TAB>referencia<TAB>motivo. Devolve {tela: (tipo, ref, motivo)}."""
    out = {}
    if not caminho or not os.path.exists(caminho):
        return out
    with open(caminho, encoding='latin-1') as fh:
        for l in fh:
            if not l.strip() or l.lstrip().startswith('#'):
                continue
            c = l.rstrip('\n').split('\t')
            if len(c) < 3:
                continue
            out[nome_tela(c[0])] = (c[1].strip().upper(), c[2].strip(), c[3].strip() if len(c) > 3 else '')
    return out


def classifica(tela, tipo, conhecidas):
    """tipo: IDENTICA | DIVERGE | TIMEOUT -> (status, referencia). status: IDENTICA, CONHECIDA, NOVA, RESOLVIDA."""
    k = conhecidas.get(tela)
    if tipo == 'IDENTICA':
        return ('RESOLVIDA', k[1]) if k else ('IDENTICA', '')
    if k and k[0] == tipo:
        return 'CONHECIDA', k[1]
    return 'NOVA', ''


def primeira_diferenca(a, b, contexto=70):
    """Posicao e trecho de cada lado ao redor do primeiro byte diferente (latin-1, numa linha)."""
    n = 0
    lim = min(len(a), len(b))
    while n < lim and a[n] == b[n]:
        n += 1
    def cut(x):
        return x[max(0, n - 20):n + contexto].decode('latin-1').replace('\n', ' ').replace('\r', ' ')
    return n, cut(a), cut(b)


def lista_menu(db_container, areas=AREAS_MIGRADAS):
    """Telas de menu das areas migradas, lidas do banco (so SELECT) e filtradas ao que existe no docroot."""
    sql = SQL_MENU % ','.join(str(int(a)) for a in areas)
    r = subprocess.run(['docker', 'exec', '-i', db_container, 'psql', '-U', 'postgres', '-d', 'ecidade', '-At'],
                       input=sql.encode(), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError('consulta do menu falhou: ' + r.stderr.decode(errors='replace')[:200])
    nomes = {nome_tela(l) for l in r.stdout.decode('latin-1').splitlines() if l.strip() and '/' not in l}
    return sorted(n for n in nomes if os.path.exists(os.path.join(DOCROOT, n)))


def seleciona(args):
    todas = sorted(f for f in os.listdir(DOCROOT) if f.endswith('.php'))
    if os.environ.get('ONLY') and not (args.prefixo or args.telas or args.menu or args.completa):
        return os.environ['ONLY'].split(',')
    sel = set()
    if args.prefixo:
        rx = re.compile(args.prefixo, re.IGNORECASE)
        sel |= {f for f in todas if rx.match(f)}
    if args.telas:
        sel |= set(le_telas(args.telas))
    if args.menu or args.completa:
        sel |= set(lista_menu(args.db_container))
    if args.completa:
        rx = re.compile(REGEX_LOCATION, re.IGNORECASE)
        sel |= {f for f in todas if rx.match(f)}
    return sorted(sel)


class Comparador:
    def __init__(self, a, b, sid, regras, norm_menu=False, origem=None):
        self.a, self.b, self.sid, self.regras, self.norm_menu = a, b, sid, regras, norm_menu
        self.origem = origem or a.container   # container onde a sessao foi criada
        self.sess = '/var/lib/php/sessions/sess_%s' % sid

    @staticmethod
    def sh(c, entrada=None):
        return subprocess.run(['bash', '-lc', c], capture_output=True, input=entrada)

    def prepara_sessao(self):
        """Guarda a sessao da origem e a replica em A e B (containers proprios nao compartilham /var/lib/php/sessions)."""
        r = self.sh('docker exec -u root %s cat %s' % (self.origem, self.sess))
        if r.returncode != 0 or not r.stdout:
            raise RuntimeError('sessao %s nao encontrada em %s' % (self.sid, self.origem))
        for c in {self.a.container, self.b.container}:
            self.sh("docker exec -i -u root %s sh -c 'mkdir -p /var/lib/php/sessions; cat > /tmp/_sess.bak'" % c, r.stdout)

    def restaura(self, container):
        self.sh("docker exec -u root %s sh -c 'cp /tmp/_sess.bak %s; chown www-data:www-data %s; chmod 600 %s'"
                % (container, self.sess, self.sess, self.sess))

    def mata_preso(self, container):
        # O curl desistiu, mas o PHP CONTINUA rodando no servidor -- e segura o flock do arquivo
        # de sessao. Como a sessao e compartilhada, toda tela seguinte trava e "timeout nos dois"
        # parecia identico. Achado no edu4: `while(!feof(false))` e laco eterno no 5.6.
        self.sh("docker exec -u root %s sh -c 'm=$(pgrep -o apache2); for p in $(pgrep apache2); do "
                "[ $p = $m ] && continue; [ \"$(cut -d\\  -f3 /proc/$p/stat)\" = R ] && kill $p; done; true'" % container)

    def busca(self, lado, pagina):
        self.restaura(lado.container)
        # teto de 5 MB: uma pagina com laco infinito (ver -1 >= "" no PHP 8) estoura a memoria do
        # harness e o mata com SIGKILL. Truncada, ela perde o marcador @@ e cai como divergente.
        r = self.sh("curl -s -m 60 -b 'ECIDADEWINDOWMAIN=%s' -w '\\n@@%%{http_code}@%%{time_total}' %s | head -c 5000000"
                    % (self.sid, shlex.quote('%s/%s' % (lado.base(), pagina))))
        out = r.stdout
        i = out.rfind(b'\n@@')
        code = out[i + 3:].decode(errors='replace') if i >= 0 else '???'
        code, _, t = code.partition('@')
        # Resposta que bateu no -m 60 sai TRUNCADA com codigo 200, e cada lado corta num ponto
        # diferente: parecia divergencia. Achado no mer3_mer_nutriitem002. Vira TIMEOUT.
        try:
            if t and float(t) >= 59.5:
                code = '000'
        except ValueError:
            pass
        if code == '000':
            self.mata_preso(lado.container)
        corpo = norm(out[:i] if i >= 0 else out, self.regras)
        if self.norm_menu:
            for rx in MENU:
                corpo = rx.sub(b'', corpo)
        return code, corpo

    def compara(self, tela):
        """-> (tipo, (codigoA, corpoA), (codigoB, corpoB)); tipo IDENTICA | DIVERGE | TIMEOUT."""
        ca, ba = self.busca(self.a, tela)
        cb, bb = self.busca(self.b, tela)
        if '000' in (ca, cb):
            return 'TIMEOUT', (ca, ba), (cb, bb)
        if not (ca == cb and ba == bb):
            # CONFIRMAR antes de acusar. Relatorios em PDF carregam um horario DENTRO do fluxo
            # comprimido (FlateDecode), fora do alcance da normalizacao. Regressao real e persistente.
            ca, ba = self.busca(self.a, tela)
            cb, bb = self.busca(self.b, tela)
        if ca == cb and ba == bb:
            return 'IDENTICA', (ca, ba), (cb, bb)
        return 'DIVERGE', (ca, ba), (cb, bb)


def cria_sessao(lado, usuario='dbseller', senha='dbseller', modulo=604, nome_modulo='Protocolo', item=9982):
    """Login real no lado (login.php + abrir.php) e acrescenta na sessao o que o clique em instituicao/modulo poria
    (DB_instit, DB_modulo, DB_anousu, DB_datausu, DB_uol_hora, DB_coddepto, DB_itemmenu_acessado). Devolve o SID."""
    jar = '/tmp/_cmp_cookie_%d' % os.getpid()
    sh = Comparador.sh
    try:
        sh('rm -f {0}; curl -s -c {0} -b {0} {1}/login.php -o /dev/null'.format(jar, lado.base()))
        md5 = hashlib.md5(senha.encode()).hexdigest()
        sh('curl -s -c {0} -b {0} -X POST -d "DB_login={2}&DB_senha={3}&conteudoCaptcha=" {1}/abrir.php -o /dev/null'
           .format(jar, lado.base(), usuario, md5))
        sid = sh("grep ECIDADEWINDOWMAIN %s | awk '{print $7}'" % jar).stdout.decode().strip()
    finally:
        if os.path.exists(jar):
            os.unlink(jar)
    if not re.fullmatch(r'[0-9a-f]{40}', sid):
        raise RuntimeError('login falhou em %s' % lado.base())
    agora = int(time.time())
    extra = ('DB_instit|s:1:"1";DB_modulo|i:%d;DB_nome_modulo|s:%d:"%s";DB_anousu|i:%d;DB_datausu|i:%d;DB_Area|i:1;'
             'DB_uol_hora|i:%d;DB_coddepto|s:1:"1";DB_nomedepto|s:3:"CPD";'
             'DB_itemmenu_acessado|s:%d:"%d";' % (modulo, len(nome_modulo), nome_modulo, time.localtime().tm_year, agora, agora, len(str(item)), item))
    # www-data (dono do arquivo): em /var/lib/php/sessions (sticky) nem o root anexa a arquivo alheio (protected_regular).
    r = sh("docker exec -i -u www-data %s sh -c 'cat >> /var/lib/php/sessions/sess_%s'" % (lado.container, sid), extra.encode())
    if r.returncode != 0:
        raise RuntimeError('nao consegui completar a sessao: ' + r.stderr.decode(errors='replace')[:120])
    return sid


def monta_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('sid_pos', nargs='?', help='(legado) SID')
    p.add_argument('pref_pos', nargs='?', help='(legado) prefixo regex')
    p.add_argument('out_pos', nargs='?', help='(legado) TSV de saida')
    p.add_argument('--sid')
    p.add_argument('--login-em')
    p.add_argument('--vigia', action='store_true')
    p.add_argument('--vigia-permitir', default='',
                   help='tabelas EXTRAS que o vigia aceita (virgula); o padrao do vigia-banco.sh ja cobre db_logsacessa* e db_usuariosonline')
    p.add_argument('--a')
    p.add_argument('--b')
    p.add_argument('--rotulo-a')
    p.add_argument('--rotulo-b')
    p.add_argument('--prefixo')
    p.add_argument('--telas')
    p.add_argument('--menu', action='store_true')
    p.add_argument('--completa', action='store_true')
    p.add_argument('--db-container', default='ecidade_database')
    p.add_argument('--conhecidas', default=CONHECIDAS_PADRAO)
    p.add_argument('--json')
    p.add_argument('--saida')
    args = p.parse_args(argv)
    args.sid = args.sid or args.sid_pos
    args.prefixo = args.prefixo or args.pref_pos
    args.saida = args.saida or args.out_pos
    if not (args.sid or args.login_em):
        p.error('informe o SID (posicional ou --sid) ou --login-em')
    if not (args.a or args.b):
        pb = int(os.environ.get('PORTA_B', '8085'))
        args.a = '8080@ecidade_php56'
        args.b = '%d@%s' % (pb, CONTAINER_LEGADO.get(pb, 'ecidade_php85'))
    if not (args.a and args.b):
        p.error('informe --a e --b')
    if not (args.prefixo or args.telas or args.menu or args.completa or os.environ.get('ONLY')):
        p.error('informe a selecao: --prefixo, --telas, --menu ou --completa')
    return args


def main(argv=None):
    args = monta_args(sys.argv[1:] if argv is None else argv)
    try:
        a = parse_lado(args.a, args.rotulo_a or 'A ' + args.a)
        b = parse_lado(args.b, args.rotulo_b or 'B ' + args.b)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    os.chdir(DOCROOT)   # o projeto vive em ecidade/; sem isto nao se acham as telas
    conhecidas = carrega_conhecidas(args.conhecidas)
    files = seleciona(args)
    for f in sorted(set(files) & PULAR):
        print('  PULADA %s  (contata servico externo)' % f, flush=True)
    files = [f for f in files if f not in PULAR]
    origem = None
    if args.login_em:
        try:
            lg = parse_lado(args.login_em)
            origem = lg.container
            args.sid = cria_sessao(lg)
        except (RuntimeError, ValueError) as e:
            print(e, file=sys.stderr)
            return 2
    cmpd = Comparador(a, b, args.sid, normalizadores([a, b]), bool(os.environ.get('NORM_MENU')), origem)
    try:
        cmpd.prepara_sessao()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 2

    foto = '/tmp/_cmp_vigia_%d' % os.getpid()
    if args.vigia and subprocess.run(['bash', VIGIA, 'antes', foto]).returncode != 0:
        print('vigia-banco.sh antes falhou', file=sys.stderr)
        return 2

    print('%d telas  [%s  x  %s]\n' % (len(files), a.rotulo, b.rotulo), flush=True)
    rel, novas = [], []
    for n, f in enumerate(files, 1):
        tipo, (ca, ba), (cb, bb) = cmpd.compara(f)
        status, ref = classifica(f, tipo, conhecidas)
        if status != 'IDENTICA':
            off, ta, tb = primeira_diferenca(ba, bb) if tipo == 'DIVERGE' else (None, '', '')
            reg = {'tela': f, 'tipo': tipo, 'status': status, 'referencia': ref,
                   'lado_a': {'runtime': a.rotulo, 'codigo': ca, 'bytes': len(ba), 'trecho': ta},
                   'lado_b': {'runtime': b.rotulo, 'codigo': cb, 'bytes': len(bb), 'trecho': tb},
                   'primeira_diferenca_byte': off}
            rel.append(reg)
            if status == 'NOVA':
                novas.append(reg)
                print('  NOVA %s %s  [%s]=%s/%dB  [%s]=%s/%dB' % (tipo, f, a.rotulo, ca, len(ba), b.rotulo, cb, len(bb)), flush=True)
                if tipo == 'DIVERGE':
                    print('       no byte %d: A %r | B %r' % (off, ta, tb), flush=True)
            elif status == 'CONHECIDA':
                print('  CONHECIDA %s %s  (%s)' % (tipo, f, ref), flush=True)
            else:
                print('  RESOLVIDA? %s agora identica; consta como conhecida (%s)' % (f, ref), flush=True)
        if n % 50 == 0:
            print('  ... %d/%d' % (n, len(files)), flush=True)

    cont = {s: sum(1 for r in rel if r['status'] == s) for s in ('CONHECIDA', 'NOVA', 'RESOLVIDA')}
    ident = len(files) - cont['CONHECIDA'] - cont['NOVA']
    print('\n=== %d/%d identicas, %d conhecidas, %d NOVAS ===' % (ident, len(files), cont['CONHECIDA'], cont['NOVA']))
    if args.json:
        with open(args.json, 'w') as fh:
            json.dump({'a': a.rotulo, 'b': b.rotulo, 'total': len(files), 'identicas': ident,
                       'conhecidas': cont['CONHECIDA'], 'novas': cont['NOVA'], 'resolvidas': cont['RESOLVIDA'],
                       'divergencias': rel}, fh, indent=1, ensure_ascii=False)
    if args.saida and args.saida != '/dev/null':
        with open(args.saida, 'w') as fh:
            for r in novas:
                fh.write('%s\t%s\t%s\t%d\t%d\n' % (r['tela'], r['lado_a']['codigo'], r['lado_b']['codigo'],
                                                  r['lado_a']['bytes'], r['lado_b']['bytes']))
    if args.vigia:
        v = subprocess.run(['bash', VIGIA, 'depois', foto] + [t for t in args.vigia_permitir.split(',') if t]).returncode
        if os.path.exists(foto):
            os.unlink(foto)
        if v != 0:
            return 3
    return 1 if novas else 0


if __name__ == '__main__':
    sys.exit(main())
