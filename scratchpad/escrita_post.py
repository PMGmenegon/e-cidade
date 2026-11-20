#!/usr/bin/env python3
"""NIVEL 3 da cobertura de escrita: submete um POST REAL aos dois runtimes e
compara o SQL que cada um emite.

O problema central: os dois runtimes compartilham o banco, entao o primeiro POST
muda o estado que o segundo veria. A saida e comparar o SQL EMITIDO -- que e
onde o defeito `0 == <literal>` se manifesta (o campo sai 0 em vez do valor
submetido) -- com snapshot/restore das tabelas afetadas entre os dois lados.

Exige log_statement ligado:
    ALTER DATABASE ecidade SET log_statement = 'all';
e, ao terminar:
    ALTER DATABASE ecidade RESET log_statement;

Uso:
  python3 scratchpad/escrita_post.py <SID> <tela.php> <tabelas,virgula> <payload>
Exemplo:
  python3 scratchpad/escrita_post.py <SID> jur1_advog001.php advog \
     'db_opcao=Incluir&v57_numcgm=19&v57_oab=OAB123&v57_matriculaadvogado=M1'

Como faz (passo a passo):
  1. copia a sessao do 7.4 para /tmp/_sess.bak (a sessao e compartilhada pelos dois
     runtimes, via volume; o /tmp tambem);
  2. fotografa cada tabela em public._n3snap_<tabela> (CREATE TABLE AS) e guarda
     last_value/is_called das sequencias dela;
  3. restaura a sessao, anota quantas linhas o log do ecidade_database tem, faz o
     POST no 7.4 (:8080) e le do log so os statements emitidos depois disso;
  4. restaura as tabelas (so a diferenca) e as sequencias;
  5. repete 3 e 4 no 8.5 (:8085);
  6. apaga as copias _n3snap_, filtra INSERT/UPDATE/DELETE, tira as tabelas de
     infraestrutura (auditoria, sessao) e compara a lista de escrita de NEGOCIO.

Entradas: SID de uma sessao autenticada; a tela (relativa a ecidade/); as tabelas
  que a tela grava, separadas por virgula, FILHAS ANTES DA MAE (ver restaurar());
  o payload (querystring; varios POSTs em sequencia separados por "|||").
Saida (stdout): contagens, ate 6 statements de negocio de cada lado e o veredito.
Codigo de saida: 0 = IDENTICO; 1 = DIVERGE (ou ABORTADO: sys.exit(<texto>) sai
  com 1); 2 = INCONCLUSIVO (nenhuma escrita de negocio nos dois lados).
Efeitos colaterais: GRAVA NO BANCO DE VERDADE (o POST) e depois desfaz pelo
  restore; cria e apaga as tabelas public._n3snap_*; reescreve o arquivo de
  sessao e o /tmp/_sess.bak no container ecidade_php74. NAO liga nem desliga o
  log_statement (quem chama faz isso: nivel3.py ou demo_nivel3.sh). Se ABORTAR,
  o POST do 7.4 JA GRAVOU e as _n3snap_ ficam no banco -- conferir e limpar a mao.
  Escrita feita por GATILHO nao aparece no log e nao e vista aqui (o nivel3.py
  confere isso pelas estatisticas do PostgreSQL).
Usado em: "Nivel 3" do guia (docs/migrar-um-modulo.md, secao dentro de "Passos
  4b a 6c -- os portoes", Passo 4 do nivel 3); chamado pelo nivel3.py e pelo
  demo_nivel3.sh.
"""
import re, subprocess, sys, os

SID, TELA, TABELAS, PAYLOAD = sys.argv[1], sys.argv[2], sys.argv[3].split(','), sys.argv[4]
# arquivo de sessao dentro do container; o diretorio e o volume ecidade_sessions,
# montado tambem no 8.5 -- restaurar pelo 5.6 vale para os dois
SESS = f"/var/lib/php/sessions/sess_{SID}"
DB   = "docker exec -i ecidade_database psql -U postgres -d ecidade"

# roda um comando de shell (bash -lc) e devolve o CompletedProcess com stdout/stderr
# em BYTES -- o banco e LATIN1, cada chamador decodifica
def sh(c, entrada=None):
    return subprocess.run(["bash","-lc",c], capture_output=True, input=entrada)

def sequencias(t):
    """Sequencias da tabela. O e-cidade as cria SEM OWNED BY, entao
    pg_get_serial_sequence nao as enxerga -- casa pelo nome."""
    # A convencao NAO e uniforme. Tres formas vistas:
    #   cemiterioisencao_cm34_sequencial_seq   <tabela>_<campo>_seq
    #   cem_legista_seq                        <modulo>_<tabela>_seq   <- a tabela no MEIO
    #   <tabela>_seq
    # Casar so a primeira deixava a sequencia de `legista` para tras, e o INSERT
    # do segundo runtime saia com o numero seguinte -- divergencia benigna que
    # parecia defeito de migracao.
    # No LIKE, o '\\_' do Python chega como \_ no SQL: _ literal (sem escape, _ casa qualquer caractere)
    q = ("select relname from pg_class where relkind='S' and ("
         "relname like '" + t + "\\_%\\_seq' or "
         "relname like '%\\_" + t + "\\_seq' or "
         "relname = '" + t + "_seq')")
    r = sh(DB + ' -tAc "' + q + '"')
    return [x for x in r.stdout.decode("latin1").split() if x]

# nome da tabela auxiliar com a foto de t (schema.tabela -> schema_tabela)
def copia(t):
    return "public._n3snap_" + t.replace(".", "_")

def snapshot():
    """Copia de cada tabela NO BANCO (tabela auxiliar) + last_value das sequencias.
    Sem repor a sequencia, o segundo runtime recebe o numero seguinte e o INSERT
    diverge por motivo benigno."""
    snap = {}
    for t in TABELAS:
        r = sh(f'{DB} -c "DROP TABLE IF EXISTS {copia(t)}; CREATE TABLE {copia(t)} AS SELECT * FROM {t}"')
        if r.returncode != 0:
            sys.exit(f"ABORTADO: nao consegui copiar {t}: {r.stderr.decode('latin1')[:200]}")
        # a contagem serve para conferir, no fim do restore, que voltou ao mesmo numero de linhas
        snap[t] = sh(f'{DB} -tAc "select count(*) from {t}"').stdout.decode().strip()
    seq = {}
    for t in TABELAS:
        for sq in sequencias(t):
            # guardado como texto 'last_value|is_called' (saida -tA do psql)
            seq[sq] = sh(DB + ' -tAc "select last_value, is_called from ' + sq + '"').stdout.decode().strip()
    snap["__seq__"] = seq
    return snap

def restaurar(snap):
    """Restaura so a DIFERENCA, comparando a linha inteira: apaga o que nao estava no
    snapshot e reinsere o que sumiu. Apagar a tabela inteira (como era) falhava em
    toda tabela referenciada por FK -- em RH, quase todo cadastro auxiliar e
    referenciado por rhpessoal. O DELETE continua respeitando FK: se uma linha NOVA
    estiver referenciada, falha e aborta (rede de seguranca). TRUNCATE CASCADE
    apagaria tabelas vizinhas em silencio."""
    # A ORDEM vem da linha de comando: as tabelas tem de ser passadas FILHAS ANTES DA
    # MAE, para o DELETE apagar o filho antes do pai (FK) e o INSERT, que percorre
    # ao contrario, repovoar o pai antes do filho.
    # s::text = x::text compara a linha INTEIRA convertida em texto (a tabela pode
    # nao ter chave primaria); linha alterada pelo POST conta como apagada + nova.
    for t in TABELAS:                      # apaga filho -> pai
        r = sh(f'{DB} -c "DELETE FROM {t} x WHERE NOT EXISTS (SELECT 1 FROM {copia(t)} s WHERE s::text = x::text)"')
        if r.returncode != 0:
            sys.exit(f"ABORTADO: nao consegui restaurar {t}: {r.stderr.decode('latin1')[:200]}")
    for t in reversed(TABELAS):            # repovoa pai -> filho
        r = sh(f'{DB} -c "INSERT INTO {t} SELECT * FROM {copia(t)} s WHERE NOT EXISTS (SELECT 1 FROM {t} x WHERE x::text = s::text)"')
        if r.returncode != 0:
            sys.exit(f"ABORTADO: nao consegui repovoar {t}: {r.stderr.decode('latin1')[:200]}")
        n = sh(f'{DB} -tAc "select count(*) from {t}"').stdout.decode().strip()
        if n != snap[t]:
            sys.exit(f"ABORTADO: {t} tinha {snap[t]} linhas e ficou com {n} depois do restore")
    # setval com o is_called original: sem ele o proximo nextval pularia ou repetiria um numero
    for sq, v in snap['__seq__'].items():
        lv, chamada = [x.strip() for x in v.split('|')]
        cal = 'true' if chamada == 't' else 'false'
        sh(DB + ' -c "select setval(\'' + sq + '\', ' + lv + ', ' + cal + ')"')

# Volta a sessao ao estado salvo antes de CADA runtime: a requisicao do 5.6 pode
# alterar a sessao (variaveis de tela, DB_*), e o 8.5 tem de partir do mesmo estado,
# senao a divergencia viria da sessao e nao do runtime.
def restaurar_sessao():
    sh("docker exec -u root ecidade_php74 sh -c "
       f"'cp /tmp/_sess.bak {SESS}; chown www-data:www-data {SESS}; chmod 600 {SESS}'")

# marca d'agua no log do PostgreSQL (stdout do container): o que vier depois desta
# linha foi emitido pela requisicao. O log e compartilhado, entao statements de
# outras conexoes no mesmo intervalo tambem entram (sao filtrados como INFRA ou
# aparecem como ruido na contagem total).
def linhas_log():
    return int(sh("docker logs ecidade_database 2>&1 | wc -l").stdout.strip() or 0)

# Linha de log que ABRE um statement: '<data> <hora> <tz> [<pid>] LOG:  <rotulo>: '
# (o [^:]*: casa o rotulo do statement, que vem traduzido para o portugues). O que
# casa aqui e removido, sobrando so o SQL.
PREFIXO = re.compile(rb'^\d{4}-\d{2}-\d{2} [\d:.]+ [^ ]+ \[\d+\] LOG:\s+[^:]*:\s*')
# QUALQUER linha de log do PostgreSQL, nao so as de LOG: -- ERRO:, INSTRUCAO:,
# DICA: e AVISO: tambem comecam assim. Sem distinguir, a juncao de continuacao
# engolia a linha de ERRO (com timestamp e PID proprios) para dentro do
# statement, e duas execucoes do MESMO insert divergiam so pelo relogio.
LINHA_LOG = re.compile(rb'^\d{4}-\d{2}-\d{2} [\d:.]+ [^ ]+ \[\d+\] ')

def capturar(desde):
    """Statements emitidos depois de `desde`, sem o prefixo de log, juntando as
    continuacoes de linha -- e SO as continuacoes."""
    bruto = sh(f"docker logs ecidade_database 2>&1 | tail -n +{desde+1}").stdout
    out, aberto = [], False
    for l in bruto.split(b'\n'):
        m = PREFIXO.match(l)
        if m:
            out.append(bytearray(l[m.end():])); aberto = True
        elif LINHA_LOG.match(l):
            aberto = False                       # outra linha de log encerra o statement
        elif aberto and l.strip():
            out[-1] += b' ' + l.strip()
    return [bytes(x) for x in out if x.strip()]

# Normalizacao antes de comparar: literal de data/hora vira '<TS>' (o relogio difere
# entre as duas requisicoes) e qualquer sequencia de espacos vira um espaco.
NORM = [(re.compile(rb"'\d{4}-\d{2}-\d{2}[ T][\d:.]+'"), b"'<TS>'"),   # timestamps
        (re.compile(rb'\s+'), b' ')]
def norm(s):
    for rx, rep in NORM: s = rx.sub(rep, s)
    return s.strip()

def requisitar(porta):
    restaurar_sessao()
    antes = linhas_log()
    # Varios POSTs separados por "|||" correm em sequencia na MESMA sessao (restaurada
    # so antes do primeiro): fluxos que guardam estado na sessao entre requisicoes,
    # como a avaliacao do estagio probatorio (respostas em $_SESSION, gravadas no fim).
    for parte in PAYLOAD.split("|||"):
        sh(f"curl -s -m 60 -b 'ECIDADEWINDOWMAIN={SID}' -X POST "
           f"--data '{parte}' -o /dev/null http://localhost:{porta}/{TELA}")
    # da tempo de o PostgreSQL escrever o log antes de le-lo
    sh("sleep 1")
    return [norm(s) for s in capturar(antes)]

# --- execucao: backup da sessao, foto, POST 5.6 + restore, POST 8.5 + restore ---
# (o /tmp/_sess.bak criado aqui tambem e usado pelos *_ciclo.py)
sh(f"docker exec -u root ecidade_php74 cp {SESS} /tmp/_sess.bak")
snap = snapshot()
print("  snapshot: " + "  ".join(t + "=" + snap[t] + " linhas"
      for t in TABELAS) + "  | sequencias=" + str(len(snap["__seq__"])))

a = requisitar(8080); restaurar(snap)
b = requisitar(8085); restaurar(snap)
for t in TABELAS:
    sh(f'{DB} -c "DROP TABLE IF EXISTS {copia(t)}"')
print(f"  statements: 7.4={len(a)}  8.5={len(b)}")

# so o que escreve -- e onde o defeito aparece
# (SELECTs variam por cache/estado de sessao e nao provam nada sobre a gravacao)
esc = re.compile(rb'^\s*(insert|update|delete)\b', re.I)
ea, eb = [s for s in a if esc.match(s)], [s for s in b if esc.match(s)]
print(f"  destes, INSERT/UPDATE/DELETE: 7.4={len(ea)}  8.5={len(eb)}")

# Separa escrita de NEGOCIO da de INFRAESTRUTURA. A auditoria (db_acount*) e a
# sessao (db_usuariosonline) carregam sequencia e relogio, que divergem por
# construcao entre duas requisicoes -- nao sao defeito.
INFRA = re.compile(rb'\b(db_acount\w*|db_usuariosonline|db_logsacessa|db_menu\w*|db_sessao\w*)\b', re.I)
na, nb = [s for s in ea if not INFRA.search(s)], [s for s in eb if not INFRA.search(s)]
print(f"  destes, escrita de NEGOCIO: 7.4={len(na)}  8.5={len(nb)}")
for s in na[:6]: print(f"    7.4> {s.decode('latin1')[:140]}")
for s in nb[:6]: print(f"    8.5> {s.decode('latin1')[:140]}")
ea, eb = na, nb

# So as tabelas passadas na linha de comando sao restauradas. Se a tela grava em
# outra, essa escrita FICA no banco (ou, se ela referencia linha nova, o restore
# aborta pela FK -- foi o que aconteceu com pensao/pensaoretencao e rhipe/rhipenumcgm
# no RH, e as linhas de teste tiveram de ser apagadas a mao).
# captura o nome da tabela-alvo do INSERT/UPDATE/DELETE (com schema, se houver)
alvo = re.compile(rb'^\s*(?:insert\s+into|update|delete\s+from)\s+([\w.]+)', re.I)
fora = sorted({m.group(1).decode('latin1').split('.')[-1].lower() for s in na + nb
               for m in [alvo.match(s)] if m} - {t.split('.')[-1].lower() for t in TABELAS})
if fora:
    print(f"  ATENCAO: a tela gravou tambem em {', '.join(fora)}, que NAO e restaurada.")
    print( "     Conferir se ficou linha de teste e, na proxima vez, incluir a tabela no 2o argumento.")

# INCONCLUSIVO != IDENTICO. Com os dois lados vazios o teste nao exercitou nada
# -- payload errado, tela inexistente, validacao recusando antes do INSERT. Sem
# esta guarda o harness APROVA o nada, que e o pior resultado possivel: da a
# impressao de cobertura onde nao houve nenhuma.
if not ea and not eb:
    print("  == INCONCLUSIVO: nenhuma escrita de negocio nos DOIS runtimes ==")
    print("     o POST nao chegou a gravar. Conferir: a tela existe? o nome do")
    print("     botao de submit esta certo? a validacao recusou antes do INSERT?")
    sys.exit(2)

if ea == eb:
    print("  == SQL de escrita de NEGOCIO IDENTICO nos dois runtimes ==")
else:
    print("  == DIVERGE ==")
    # compara posicao a posicao; um statement a mais de um lado aparece como <ausente>
    for i in range(max(len(ea), len(eb))):
        x = ea[i].decode('latin1') if i < len(ea) else '<ausente>'
        y = eb[i].decode('latin1') if i < len(eb) else '<ausente>'
        if x != y:
            print(f"    7.4: {x[:150]}")
            print(f"    8.5: {y[:150]}")
sys.exit(0 if ea == eb else 1)
