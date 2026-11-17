#!/usr/bin/env python3
"""Compara as telas de um modulo entre os runtimes 5.6 (:8080) e 8.5 (:8085).

Restaura uma sessao autenticada antes de CADA requisicao (uma requisicao a
consome/reescreve) e normaliza os identificadores aleatorios, que senao geram
falsos positivos -- alguns deles INTERMITENTES, que e o pior tipo.

Como faz:
  1. guarda uma copia do arquivo de sessao (sess_<SID>) em /tmp/_sess.bak no
     container do 5.6 (o /tmp e as sessoes sao volumes compartilhados entre os
     runtimes, ver docs/registro/ambiente.md);
  2. lista as telas .php de ecidade/ cujo nome casa com o prefixo (ou usa ONLY);
  3. para cada tela, restaura a sessao, faz GET com curl no 5.6 e no lado B,
     normaliza os dois corpos (NORM) e compara codigo HTTP + corpo;
  4. se diferir, repete as duas requisicoes uma vez (filtra flakes) antes de
     acusar DIVERGE; resposta que estoura 60 s conta como TIMEOUT, nao como identica.

Uso (da raiz do repo; passo 7 do guia docs/migrar-um-modulo.md e bateria do fim da area):
  python3 scratchpad/cmp.py <SID> '^<pref>[0-9]*_' /tmp/<pref>_div.txt
  ONLY="tela1.php,tela2.php" python3 scratchpad/cmp.py <SID> '^<pref>[0-9]*_' /dev/null

Entradas:
  <SID>    id de uma sessao autenticada (ver "Prova de fumaca" no guia; /tmp/sid.txt)
  <regex>  re.match, sem diferenciar maiusculas, contra o nome do arquivo em ecidade/
  [saida]  opcional; /dev/null ou ausente = nao grava
  ambiente: ONLY=a.php,b.php (substitui a lista do regex), PORTA_B=8085|8086|8087
            (lado B; padrao 8085 = nosso 8.5), NORM_MENU=1 (remove o menu, so para o TCC)

Saidas:
  stdout   "N telas", uma linha por tela problematica ("  DIVERGE <tela>  56=<cod>/<bytes>B
           85=<cod>/<bytes>B", "  TIMEOUT <tela>  56=<cod>  85=<cod> ...", "  PULADA <tela> ..."),
           progresso a cada 50 e o resumo final "=== X/N identicas, D divergentes, T timeout ===".
  [saida]  TSV, uma divergente por linha: tela  cod56  cod85  bytes56  bytes85
           (TIMEOUT nao entra no arquivo, so no stdout).
"""
import re, subprocess, sys, os, shlex

# O projeto vive em ecidade/; sem isto o os.listdir('.') abaixo nao acha as telas.
os.chdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ecidade'))

SID  = sys.argv[1]
PREF = sys.argv[2]
OUT  = sys.argv[3] if len(sys.argv) > 3 else None
SESS = f"/var/lib/php/sessions/sess_{SID}"

def sh(c):
    """Roda um comando no bash do host e devolve o CompletedProcess (stdout em bytes)."""
    return subprocess.run(["bash", "-lc", c], capture_output=True)

# Copia de seguranca da sessao, feita UMA vez no inicio. Os ciclos de guarda pg_*
# (guarda_ciclo.py / campo_ciclo.py) restauram a partir deste mesmo /tmp/_sess.bak --
# por isso o guia manda rodar a bateria antes deles.
sh(f"docker exec -u root ecidade_php56 cp {SESS} /tmp/_sess.bak")

def restore():
    """Repoe a sessao salva (dono www-data, modo 600) antes de cada requisicao.
    Feito pelo container do 5.6, mas vale para os dois: o diretorio de sessoes e compartilhado."""
    sh("docker exec -u root ecidade_php56 sh -c "
       f"'cp /tmp/_sess.bak {SESS}; chown www-data:www-data {SESS}; chmod 600 {SESS}'")

# Normalizacao: (regex, substituto) aplicados em ordem aos DOIS corpos antes de comparar.
# Cada um apaga um valor que muda a cada requisicao e nao tem relacao com o runtime.
NORM = [
    (re.compile(rb'sid=[0-9a-f]{8,}'),            b'sid=X'),          # id de sessao em URL
    (re.compile(rb'arquivo=[A-Za-z0-9+/=]{12,}'), b'arquivo=X'),      # parametro arquivo= em base64
    (re.compile(rb'wname[0-9]+'),                 b'wnameX'),         # nome de janela com numero aleatorio
    (re.compile(rb'iframe[A-Za-z0-9]{4,}\.php'),  b'iframeX.php'),    # nome de iframe gerado
    (re.compile(rb'[0-9a-f]{32}'),                b'MD5X'),           # qualquer hash md5 (tokens, nomes)
    (re.compile(rb'nomeArquivo[^\s"\']*'),        b'nomeArquivoX'),   # nomeArquivo... ate espaco ou aspa
    # PDF temporario: o nome carrega PID e timestamp, aleatorios por requisicao.
    (re.compile(rb'tmp/[A-Za-z0-9_]+\.pdf'),      b'tmp/X.pdf'),
    # CSV/TXT temporario com timestamp no nome (arquivo_infra_escola_1791906927.csv);
    # dentro de JSON a barra vem escapada (tmp\/...). Achado no edu2.
    (re.compile(rb'tmp\\?/[A-Za-z0-9_]+\.(?:csv|txt)'), b'tmp/X.arq'),
    # A pagina de erro monta URL absoluta a partir de HTTP_HOST (ver $DB_URL_ABS),
    # entao ela carrega a porta do runtime que a serviu. Diferenca por construcao.
    (re.compile(rb'localhost:80(80|85|86|87)'),         b'localhost:PORT'),
    # Data de criacao gravada dentro do PDF pelo FPDF: muda se as duas
    # requisicoes cairem em segundos diferentes. Passou a aparecer depois que
    # tmp/ virou gravavel e os relatorios comecaram a ser gerados de fato.
    (re.compile(rb'/(CreationDate|ModDate) ?\(D:[0-9]{14}[^)]*\)'), b'/DateX'),
]
def norm(b):
    """Aplica todas as substituicoes de NORM, em ordem, ao corpo em bytes."""
    for rx, rep in NORM:
        b = rx.sub(rep, b)
    return b

# NORM_MENU=1: troca o trecho emitido pelo db_menu() por um marcador nos DOIS lados.
# Usado so na comparacao com o TCC de referencia, onde o desktop vem desligado por um
# defeito do codigo dele (a camada V3 perde o login da sessao) e o db_menu() emite o
# menu classico (~400 linhas) no lugar do estilo/script do desktop. Separa esse defeito
# unico, sistematico, dos defeitos por tela.
MENU = [re.compile(rb'<style>\s*\nbody\.no-menu.*?</script>\n?', re.S),                          # ramo desktop
        re.compile(rb'<div id="db-menu">.*?</div>(?=<div id="db-tooltip")', re.S),                # ramo classico: menu
        re.compile(rb'<script>\s*\(window\.CurrentWindow \|\| parent\.CurrentWindow\)\.bstatus.*?autoCompleteMenu\(\);\s*\}\s*</script>', re.S)]  # classico: status

def fetch(port, page):
    """GET de uma tela num runtime. Devolve (codigo HTTP em texto, corpo normalizado).
    O curl acrescenta ao fim "\\n@@<codigo>@<segundos>"; o marcador e separado do corpo
    pela ULTIMA ocorrencia de "\\n@@". Codigo '000' = timeout/sem resposta; '???' = sem marcador
    (resposta truncada no teto de 5 MB)."""
    restore()
    # teto de 5 MB: uma pagina com laco infinito (ver -1 >= "" no PHP 8) estoura
    # a memoria do harness e o mata com SIGKILL. Truncada, ela perde o marcador
    # @@ e cai como divergente, que e o desfecho correto.
    r = sh(f"curl -s -m 60 -b 'ECIDADEWINDOWMAIN={SID}' "
           f"-w '\\n@@%{{http_code}}@%{{time_total}}' {shlex.quote(f'http://localhost:{port}/{page}')} | head -c 5000000")
    out = r.stdout
    i = out.rfind(b'\n@@')
    code = out[i+3:].decode(errors='replace') if i >= 0 else '???'
    code, _, t = code.partition('@')
    # Resposta que bateu no -m 60 sai TRUNCADA com codigo 200, e cada lado corta num
    # ponto diferente: parecia divergencia. Achado no mer3_mer_nutriitem002 (~53 s nos
    # dois runtimes; sob a carga da bateria passa de 60). Vira TIMEOUT.
    if t and float(t) >= 59.5:
        code = '000'
    if code == '000':
        # O curl desistiu, mas o PHP CONTINUA rodando no servidor -- e segura o
        # flock do arquivo de sessao. Como a sessao e compartilhada, toda tela
        # seguinte trava nos DOIS runtimes e "timeout nos dois" parecia identico.
        # Achado no edu4: `while(!feof(false))` e laco eterno no 5.6.
        # Mata, no container que serviu, os filhos do apache em estado R (rodando) --
        # o terceiro campo de /proc/<pid>/stat e o estado -- poupando o processo mestre
        # (pgrep -o = o mais antigo). Libera o flock da sessao para as telas seguintes.
        c = 'ecidade_php56' if port == 8080 else CONTAINER_B
        sh(f"docker exec -u root {c} sh -c 'm=$(pgrep -o apache2); for p in $(pgrep apache2); do "
           f"[ $p = $m ] && continue; [ \"$(cut -d\\  -f3 /proc/$p/stat)\" = R ] && kill $p; done; true'")
    corpo = norm(out[:i] if i >= 0 else out)
    if os.environ.get('NORM_MENU'):
        for rx in MENU: corpo = rx.sub(b'', corpo)
    return code, corpo

# Lado B configuravel: PORTA_B=8086 compara o 5.6 com o codigo do TCC de referencia
# (container ecidade_tcc_gerson). O padrao continua sendo o nosso 8.5.
PORTA_B = int(os.environ.get('PORTA_B', '8085'))
CONTAINER_B = {8085: 'ecidade_php85', 8086: 'ecidade_tcc_gerson', 8087: 'ecidade_lar12'}[PORTA_B]
# Universo: arquivos .php de ecidade/ cujo nome casa com o regex (re.match = ancorado no
# inicio; IGNORECASE porque ha prefixos com maiuscula no disco, ex. Amb1_*). ONLY, se dado, substitui tudo
# (o regex fica sem efeito -- a bateria do map passa '^$' so para ocupar o argumento).
files = sorted(f for f in os.listdir('.')
               if re.match(PREF, f, re.IGNORECASE) and f.endswith('.php'))
if os.environ.get('ONLY'):
    files = os.environ['ONLY'].split(',')
# Telas que contatam servico EXTERNO real: a bateria nao pode disparar conexao a
# terceiros. iss4_siss002 tem fixo o IP do SISS (200.192.137.56); o pg_connect leva
# ~134 s para desistir, igual nos dois runtimes -- nao e regressao, e rede.
PULAR = {'iss4_siss002.php'}
for f in sorted(set(files) & PULAR):
    print(f"  PULADA {f}  (contata servico externo)", flush=True)
files = [f for f in files if f not in PULAR]

print(f"{len(files)} telas\n", flush=True)
div = []; tout = []
# Uma tela de cada vez, sempre 5.6 primeiro e depois o lado B (nunca em paralelo: a sessao
# e unica e compartilhada; duas requisicoes simultaneas disputariam o flock dela).
for n, f in enumerate(files, 1):
    c56, b56 = fetch(8080, f)
    c85, b85 = fetch(PORTA_B, f)
    if '000' in (c56, c85):
        tout.append(f)
        print(f"  TIMEOUT {f}  56={c56}  85={c85}  (nao conta como identica)", flush=True)
        continue
    if not (c56 == c85 and b56 == b85):
        # CONFIRMAR antes de acusar. Relatorios em PDF carregam um horario
        # DENTRO do fluxo comprimido (FlateDecode), fora do alcance da
        # normalizacao: se as duas requisicoes cairem em segundos diferentes,
        # os bytes mudam. Uma regressao real e persistente; um flake nao.
        c56, b56 = fetch(8080, f)
        c85, b85 = fetch(PORTA_B, f)
    if not (c56 == c85 and b56 == b85):
        div.append((f, c56, c85, len(b56), len(b85)))
        print(f"  DIVERGE {f}  56={c56}/{len(b56)}B  85={c85}/{len(b85)}B", flush=True)
    if n % 50 == 0:
        print(f"  ... {n}/{len(files)}", flush=True)

print(f"\n=== {len(files)-len(div)-len(tout)}/{len(files)} identicas, {len(div)} divergentes, {len(tout)} timeout ===")
if OUT and OUT != '/dev/null':
    with open(OUT, "w") as fh:
        for d in div:
            fh.write(f"{d[0]}\t{d[1]}\t{d[2]}\t{d[3]}\t{d[4]}\n")
