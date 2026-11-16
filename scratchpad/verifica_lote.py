#!/usr/bin/env python3
"""Roda TODAS as verificacoes automaticas de um lote e junta o resultado num relatorio so.

Uso (da raiz do repositorio):
    python3 scratchpad/verifica_lote.py <nome-do-lote> <prefixo> [<prefixo> ...] [opcoes]

    python3 scratchpad/verifica_lote.py as soc hab
    python3 scratchpad/verifica_lote.py as soc hab --so 6b,6c        # so alguns passos
    python3 scratchpad/verifica_lote.py as soc hab --continuar       # nao para no primeiro que falhar
    python3 scratchpad/verifica_lote.py as soc hab --base origin/base-php84   # lote ja commitado

Opcoes:
    --so PASSOS   lista separada por virgula, entre: 4b,5,5b,6,6b,6c,7 (padrao: todos)
    --continuar   segue para os passos seguintes mesmo depois de uma FALHA
    --base REF    referencia do git contra a qual o lote e medido no 4b e no 5 (padrao: HEAD,
                  isto e, as alteracoes ainda nao commitadas). Depois do commit do lote, passe
                  o commit anterior a ele, ex. --base origin/base-php84
    --sid SID     sessao autenticada a usar na bateria (padrao: a mais recente do 5.6)

Pre-requisitos:
    - os containers ecidade_database, ecidade_php56 e ecidade_php85 no ar;
    - o universo de cada prefixo ja gerado: python3 scratchpad/enumera.py <prefixo>
      (o script le ecidade/tmp/<prefixo>_universo.txt);
    - o Rector ja aplicado (passo 4). Este script NAO altera codigo nem o banco.

O que ele roda, nesta ordem (os detalhes de cada passo estao em docs/migrar-um-modulo.md):
    4b  funcoes novas no diff existem no PHP 5.6?
    5   php -l no universo, nos dois runtimes
    5b  cada arquivo com extends/implements carrega nos dois (assinatura incompativel, LSP)
    6   instanciar as classes: o estado inicial e igual nos dois?
    6b  caminho de escrita: atualizacampos() le o formulario igual nos dois?
    6c  forma negada `$this->x != ""`: decide igual nos dois? (so as classes do lote contam)
    7   bateria: cada tela dos prefixos responde byte a byte igual nos dois?
        e, para cada tela que divergir, um DIAGNOSTICO automatico: pede a tela de novo aos dois runtimes
        com os logs limpos, junta o erro fatal do PHP (arquivo e linha), os erros de SQL do PostgreSQL e,
        se os dois responderem 200, o trecho onde as paginas comecam a diferir; e classifica pela tabela
        de decisao do guia (regressao, pre-existente, quebra nos dois, silenciosa, nao reproduziu).

Ficam DE FORA de proposito: o passo 4 (Rector: exige conferir regra nova antes de aplicar),
o nivel 3 (POST real: grava no banco e exige escolher a tela), os passos 8/8b (mudam o proxy)
e qualquer correcao (guarda_ciclo, negada_corrige: exigem olhar caso a caso).

Saida: uma pasta por execucao, ecidade/tmp/verif/<lote>-<AAAAMMDD-HHMM>/, com
    RELATORIO.md   o resumo e, para cada passo, o criterio, os numeros e as linhas que importam.
                   E o UNICO arquivo que precisa ser lido; os demais sao a saida bruta de cada
                   passo, para quem quiser conferir ou diagnosticar.
    <passo>_*.txt  saida bruta de cada passo
A pasta fica dentro de ecidade/ (montada nos containers como /var/www/html), entao os
containers leem e escrevem nela sem `docker cp`. ecidade/tmp/ e ignorada pelo git.

Codigo de saida: 0 = tudo OK; 1 = algum passo com FALHA ou INVESTIGAR; 2 = pre-requisito faltando.

Situacoes de cada passo:
    OK          o criterio do passo foi atingido
    FALHA       o criterio nao foi atingido: e defeito (ou o teste nao rodou inteiro)
    INVESTIGAR  ha divergencia que precisa de diagnostico (pode ser defeito pre-existente)
    AVISO       nada a corrigir, mas algo merece atencao (ex.: nenhuma alteracao no diff)
    PULADO      fora do --so, ou nao rodou porque um passo anterior falhou
"""
import argparse, collections, datetime, os, re, shlex, subprocess, sys

# ---------------------------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------------------------

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # raiz do repositorio
os.chdir(RAIZ)
ECIDADE = os.path.join(RAIZ, "ecidade")      # montado como /var/www/html nos dois containers
WEB = "/var/www/html"
RT = {"56": "ecidade_php56", "85": "ecidade_php85"}
PASSOS = ["4b", "5", "5b", "6", "6b", "6c", "7"]

# Artefatos conhecidos dos harnesses dos passos 6 e 6b: classes que aparecem diferentes entre
# os runtimes por causa do TESTE, nao da migracao. Registrados em Patrimonial, Financeiro e
# Saude; explicados no guia (passos 6 e 6b). UMA lista so: ela gera o filtro (uma linha de diff
# que case com algum padrao e ignorada; QUALQUER outra conta como divergencia) e a secao
# "Artefatos conhecidos" do fim do relatorio.
#   (padrao no texto da linha, classe, o que aparece no diff, por que nao e defeito)
ARTEFATOS_LISTA = [
    (r"requisicaoMaterial\.model", "RequisicaoMaterial",
     "`ArgumentCountError` so no 8.5 (no 5.6, valores `NULL`)",
     "o construtor exige 1 argumento e o teste faz `new X()` sem nenhum. O PHP 5.6 so avisava e seguia; o 8 recusa. "
     "O sistema de verdade sempre passa o argumento"),
    (r"solicitacaocompras\.model", "solicitacaoCompra",
     "`ArgumentCountError` so no 8.5 (no 5.6, `SEM_SAIDA`)", "idem"),
    (r"lancamentoContabil", "lancamentoContabil", "`ArgumentCountError` so no 8.5", "idem"),
    (r"ordemPagamento", "ordemPagamento", "`ArgumentCountError` so no 8.5", "idem"),
    (r"avaliacaogruporespostatrabalhointermitente", "cl_avaliacaogruporespostatrabalhointermitente",
     "`ERRO ... Exception` no 8.5 e `SEM_SAIDA` (ou um \"pulado\") no 5.6",
     "o construtor procura um arquivo `.dd.xml` que nao existe nesta base e falha NOS DOIS: o 8.5 captura a "
     "excecao e o teste a imprime; o 5.6 morre sem imprimir nada"),
    (r"classes/empenho\.php", "empenho, campo datausu", "`1969-12-31` no 5.6 contra a data de hoje no 8.5",
     "so acontece SEM sessao (sem a data do usuario logado), que e condicao do teste, nao do uso real"),
]
ARTEFATOS = re.compile("|".join(p for p, *_ in ARTEFATOS_LISTA))

# ---------------------------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------------------------

def sh(cmd, entrada=None, timeout=None):
    """Roda um comando (lista de argumentos) e devolve (codigo, stdout, stderr) como texto.
    latin-1 nos dois sentidos: 64% da base e LATIN-1, e utf-8 estrito quebraria na leitura."""
    r = subprocess.run(cmd, input=entrada.encode("latin-1") if entrada is not None else None,
                       stdin=None if entrada is not None else subprocess.DEVNULL,
                       capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode("latin-1"), r.stderr.decode("latin-1")

def dentro(caminho_host):
    """Caminho de um arquivo de ecidade/ visto de DENTRO dos containers."""
    return WEB + "/" + os.path.relpath(caminho_host, ECIDADE)

def ler(caminho):
    with open(caminho, encoding="latin-1") as f:
        return f.read()

def linhas(caminho):
    return [l for l in ler(caminho).splitlines() if l.strip()]

def gravar(caminho, texto):
    with open(caminho, "w", encoding="latin-1", errors="replace") as f:
        f.write(texto)

def diff_linhas(a, b):
    """Linhas so de um lado (multiconjunto: a ordem nao importa, repeticao conta)."""
    ca, cb = collections.Counter(a), collections.Counter(b)
    return sorted((ca - cb).elements()), sorted((cb - ca).elements())

def amostra(itens, n=15):
    """Lista para o relatorio, cortada em n itens com a contagem do resto."""
    itens = list(itens)
    corpo = "\n".join(itens[:n])
    if len(itens) > n:
        corpo += f"\n... e mais {len(itens) - n} (ver o arquivo bruto)"
    return corpo

class Resultado:
    """O que cada passo devolve: situacao, uma linha de resumo e o texto do relatorio."""
    def __init__(self, situacao, resumo, detalhe="", arquivos=()):
        self.situacao, self.resumo, self.detalhe, self.arquivos = situacao, resumo, detalhe, list(arquivos)

# ---------------------------------------------------------------------------------------------
# Pre-requisitos
# ---------------------------------------------------------------------------------------------

def preparar(args):
    """Confere containers, universos e sessao. Devolve o contexto usado pelos passos."""
    _, out, _ = sh(["docker", "ps", "--format", "{{.Names}}"])
    faltam = [c for c in ("ecidade_database", "ecidade_php56", "ecidade_php85") if c not in out.split()]
    if faltam:
        sys.exit(f"ERRO: container(s) parado(s): {', '.join(faltam)}. Religue (docs/migrar-um-modulo.md, "
                 "'Antes de comecar').")

    universo = set()
    for p in args.prefixos:
        u = os.path.join(ECIDADE, "tmp", f"{p}_universo.txt")
        if not os.path.isfile(u):
            sys.exit(f"ERRO: falta {os.path.relpath(u)}. Rode antes: python3 scratchpad/enumera.py {p}")
        universo |= set(linhas(u))
    codigo = sorted(f for f in universo if f.endswith((".php", ".class", ".inc"))
                    and os.path.isfile(os.path.join(ECIDADE, f)))
    classes = sorted(f for f in codigo if f.startswith("classes/"))

    # Arquivos alterados pelo lote, relativos a ecidade/ (usado no 4b e no 5).
    _, out, _ = sh(["git", "diff", "--name-only", args.base, "--", "ecidade/"])
    alterados = {l[len("ecidade/"):] for l in out.splitlines() if l.startswith("ecidade/")}

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    pasta = os.path.join(ECIDADE, "tmp", "verif", f"{args.lote}-{ts}")
    os.makedirs(pasta, exist_ok=True)
    os.chmod(pasta, 0o777)          # os containers (www-data/root) escrevem aqui

    gravar(os.path.join(pasta, "universo_codigo.txt"), "\n".join(codigo) + "\n")
    gravar(os.path.join(pasta, "classes.txt"), "\n".join(classes) + "\n")
    return {"pasta": pasta, "codigo": codigo, "classes": classes, "alterados": alterados,
            "sid": args.sid or achar_sessao()}

def achar_sessao():
    """A sessao autenticada MAIS RECENTE do 5.6. O sess_?* exclui o arquivo "sess_" sem
    identificador (criado por requisicao com cookie vazio), que vinha primeiro e dava SID vazio."""
    _, out, _ = sh(["docker", "exec", "-i", "ecidade_php56", "sh", "-c",
                    "ls -t $(grep -la DB_modulo /var/lib/php/sessions/sess_?*) | head -1"])
    sid = out.strip().rsplit("sess_", 1)[-1]
    if len(sid) != 40:
        sys.exit("ERRO: nenhuma sessao autenticada. Entre em http://localhost:8090 (dbseller/dbseller) e rode de novo.")
    return sid

# ---------------------------------------------------------------------------------------------
# Passos
# ---------------------------------------------------------------------------------------------

def passo_4b(ctx, args):
    """Funcoes que APARECERAM nas linhas novas do diff e nao existem no PHP 5.6.
    O Rector pode emitir funcao do PHP 7/8 (str_contains, array_key_first) que compila no 5.6
    e so explode em execucao -- nenhum `php -l` pega."""
    _, d, _ = sh(["git", "diff", "-U0", args.base, "--", "ecidade/"])
    if not d.strip():
        return Resultado("AVISO", f"nenhuma alteracao em ecidade/ em relacao a {args.base}",
                         f"O diff contra `{args.base}` esta vazio. Se o lote ja foi commitado, rode com "
                         "`--base <commit anterior ao lote>`; se o Rector ainda nao rodou, rode-o antes.")
    # (?<!function ) exclui DECLARACOES: sem ele, "__construct" seria acusada como ausente
    rx = re.compile(r"(?<![\$>:\w])(?<!function )([a-z_][a-z0-9_]{2,})\s*\(")
    nov, vel = set(), set()
    for l in d.splitlines():
        if l.startswith(("+++", "---")):
            continue
        if l.startswith("+"):
            nov |= set(rx.findall(l))
        elif l.startswith("-"):
            vel |= set(rx.findall(l))
    novas = sorted(nov - vel)
    arq = os.path.join(ctx["pasta"], "4b_funcoes_novas.txt")
    gravar(arq, "\n".join(novas) + "\n")
    _, out, err = sh(["docker", "exec", "-i", "ecidade_php56", "php", "-r",
                      f'foreach(file("{dentro(arq)}", FILE_IGNORE_NEW_LINES|FILE_SKIP_EMPTY_LINES) as $f)'
                      ' if(!function_exists(trim($f))) echo trim($f),"\\n";'])
    ausentes = [l for l in out.splitlines() if l.strip()]
    if ausentes:
        return Resultado("FALHA", f"{len(novas)} funcoes novas, {len(ausentes)} AUSENTES no 5.6",
                         "Funcoes que o Rector emitiu e o PHP 5.6 nao tem. Banir a regra que as emitiu e refazer o "
                         "passo 4 (guia: 'Como banir uma regra').\n\n```\n" + amostra(ausentes) + "\n```", [arq])
    return Resultado("OK", f"{len(novas)} funcoes novas, 0 ausentes no 5.6",
                     "Funcoes novas no diff (todas existem no 5.6): " + (", ".join(novas) or "nenhuma"), [arq])

def lint(ctx, rt, lista):
    """Arquivos da lista que NAO passam no `php -l` do runtime, com a mensagem de erro.
    `</dev/null` no php: sem ele o php consome o stdin do laco e o laco da uma volta so."""
    script = ('while IFS= read -r f; do m=$(php -l "$f" 2>&1 </dev/null) || '
              'printf "%s\\t%s\\n" "$f" "$(echo "$m" | grep -a -m1 -i error)"; done < ' + shlex.quote(dentro(lista)))
    _, out, _ = sh(["docker", "exec", "-i", RT[rt], "sh", "-c", f"cd {WEB}; {script}"], timeout=3600)
    return dict(l.split("\t", 1) for l in out.splitlines() if "\t" in l)

def passo_5(ctx, args):
    """`php -l` em TODO o universo, nos dois runtimes. Um arquivo que nao parseia no 5.6 derruba
    o runtime que serve o login; um que nao parseia no 8.5 derruba a tela migrada."""
    lista = os.path.join(ctx["pasta"], "universo_codigo.txt")
    e56, e85 = lint(ctx, "56", lista), lint(ctx, "85", lista)
    for rt, e in (("56", e56), ("85", e85)):
        gravar(os.path.join(ctx["pasta"], f"5_lint_erros_{rt}.txt"), "".join(f"{k}\t{v}\n" for k, v in sorted(e.items())))
    so56 = sorted(set(e56) - set(e85))
    so85 = sorted(set(e85) - set(e56))
    nos_dois = sorted(set(e56) & set(e85))
    quebrados_pelo_lote = [f for f in nos_dois if f in ctx["alterados"]]
    n = len(ctx["codigo"])
    det = [f"{n} arquivos verificados em cada runtime."]
    if so56:
        det.append("**So no 5.6** (o lote quebrou o runtime de referencia):\n```\n" + amostra(f"{f}  {e56[f]}" for f in so56) + "\n```")
    if so85:
        det.append("**So no 8.5:**\n```\n" + amostra(f"{f}  {e85[f]}" for f in so85) + "\n```")
    if quebrados_pelo_lote:
        det.append("**Falham nos dois E foram alterados pelo lote** (o lote pode te-los quebrado):\n```\n"
                   + amostra(quebrados_pelo_lote) + "\n```")
    if nos_dois:
        det.append(f"Falham nos dois e nao foram alterados (pre-existentes, so registrar): {len(nos_dois) - len(quebrados_pelo_lote)}.")
    arqs = [os.path.join(ctx["pasta"], f"5_lint_erros_{rt}.txt") for rt in ("56", "85")]
    if so56 or so85 or quebrados_pelo_lote:
        return Resultado("FALHA", f"{n} arquivos: {len(so56)} so no 5.6, {len(so85)} so no 8.5, "
                         f"{len(quebrados_pelo_lote)} alterados que falham nos dois", "\n\n".join(det), arqs)
    return Resultado("OK", f"{n} arquivos, 0 erros novos ({len(nos_dois)} pre-existentes)", "\n\n".join(det), arqs)

def por_processo(ctx, rt, harness, lista, saida):
    """Roda um harness PHP UMA ENTRADA POR PROCESSO (scratchpad/porclasse.sh): um fatal mata so
    aquele processo, e o resto da lista continua. Com a lista inteira num processo so, o 5.6
    morreu na classe 119 de 772 no soc e o diff comparou 103 classes sem acusar nada.
    Devolve o numero de entradas processadas (o #TOTAL do porclasse.sh)."""
    c = RT[rt]
    sh(["docker", "cp", "scratchpad/porclasse.sh", f"{c}:/tmp/pc.sh"])
    sh(["docker", "cp", harness, f"{c}:/tmp/h_{os.path.basename(harness)}"])
    _, out, err = sh(["docker", "exec", "-i", c, "sh", "/tmp/pc.sh", f"/tmp/h_{os.path.basename(harness)}"],
                     entrada=ler(lista), timeout=7200)
    gravar(saida, out)
    m = re.search(r"#TOTAL (\d+)", err)
    return int(m.group(1)) if m else -1

def comparar_harness(ctx, nome, harness, explicacao):
    """Passos 6 e 6b: roda o harness nos dois runtimes e compara as saidas, ignorando os
    artefatos conhecidos. Criterio: as duas rodadas cobrem a lista inteira E nao sobra
    nenhuma linha de diferenca fora dos artefatos."""
    lista = os.path.join(ctx["pasta"], "classes.txt")
    n = len(ctx["classes"])
    s = {rt: os.path.join(ctx["pasta"], f"{nome}_{rt}.txt") for rt in RT}
    tot = {rt: por_processo(ctx, rt, harness, lista, s[rt]) for rt in RT}
    a, b = linhas(s["56"]), linhas(s["85"])
    so56, so85 = diff_linhas(a, b)
    reais56 = [l for l in so56 if not ARTEFATOS.search(l)]
    reais85 = [l for l in so85 if not ARTEFATOS.search(l)]
    vistos = {cls for pad, cls, *_ in ARTEFATOS_LISTA for l in so56 + so85 if re.search(pad, l)}
    ctx.setdefault("artefatos_vistos", set()).update(vistos)
    sem = {rt: sum(1 for l in linhas(s[rt]) if l.startswith("SEM_SAIDA")) for rt in RT}
    det = [explicacao,
           f"Classes na lista: {n}. Processadas: 5.6={tot['56']}, 8.5={tot['85']}. "
           f"Sem saida (nada a testar ou o processo morreu): 5.6={sem['56']}, 8.5={sem['85']}.",
           "Artefatos conhecidos que apareceram (ignorados; explicados no fim do relatorio): "
           + (", ".join(sorted(vistos)) or "nenhum")]
    if reais56 or reais85:
        det.append("**Diferencas fora dos artefatos** (`<` = 5.6, `>` = 8.5):\n```\n"
                   + amostra([f"< {l}" for l in reais56] + [f"> {l}" for l in reais85], 30) + "\n```")
    if tot["56"] != n or tot["85"] != n:
        return Resultado("FALHA", f"incompleto: {n} classes, processadas 5.6={tot['56']} 8.5={tot['85']}",
                         "\n\n".join(det), s.values())
    if reais56 or reais85:
        return Resultado("FALHA", f"{n} classes, {len(reais56) + len(reais85)} linhas de diferenca fora dos artefatos",
                         "\n\n".join(det), s.values())
    return Resultado("OK", f"{n} classes, so artefatos conhecidos ({len(vistos)})", "\n\n".join(det), s.values())

def passo_5b(ctx, args):
    """Carregar cada arquivo com extends/implements nos dois runtimes. O `php -l` olha um arquivo
    de cada vez e nao ve assinatura incompativel entre filha e mae em arquivos diferentes (LSP):
    no PHP 8 isso e fatal ao declarar a classe."""
    alvo = []
    for f in ctx["codigo"]:
        with open(os.path.join(ECIDADE, f), "rb") as fh:
            if re.search(rb"\b(extends|implements)\b", fh.read()):
                alvo.append(f)
    lista = os.path.join(ctx["pasta"], "5b_lista.txt")
    gravar(lista, "\n".join(alvo) + "\n")
    s = {}
    for rt in RT:
        sh(["docker", "cp", "scratchpad/carrega_arquivo.php", f"{RT[rt]}:/tmp/ca.php"])
        # Cada linha sai como <arquivo><TAB><ultima linha do harness>. O nome vai na frente porque
        # o harness nem sempre imprime "<arquivo><TAB>OK": um arquivo que exige login imprime so
        # "Feche seu navegador e faca login novamente.", e sem o nome a linha ficava sem dono.
        _, out, _ = sh(["docker", "exec", "-i", RT[rt], "sh", "-c",
                        f'while read f; do r=$(php /tmp/ca.php "$f" </dev/null 2>/dev/null | tail -1); '
                        f'printf "%s\\t%s\\n" "$f" "$r"; done < {shlex.quote(dentro(lista))}'],
                       timeout=3600)
        s[rt] = os.path.join(ctx["pasta"], f"5b_carga_{rt}.txt")
        gravar(s[rt], out)
    # "OK" quando o harness terminou em "<arquivo><TAB>OK"; qualquer outra coisa e a mensagem de falha
    res = {}
    for rt in RT:
        res[rt] = {}
        for l in linhas(s[rt]):
            f, _, r = l.partition("\t")
            res[rt][f] = ["OK"] if r.endswith("\tOK") else [r.split("\t", 1)[-1] or "sem saida"]
    quebra = sorted(f for f in alvo if res["56"].get(f, ["?"])[0] == "OK" and res["85"].get(f, ["?"])[0] != "OK")
    nos_dois = sum(1 for f in alvo if res["56"].get(f, ["?"])[0] != "OK" and res["85"].get(f, ["?"])[0] != "OK")
    det = [f"Arquivos com extends/implements: {len(alvo)}. Com resultado: 5.6={len(res['56'])}, 8.5={len(res['85'])}. "
           f"Falham nos dois (pre-existentes): {nos_dois}."]
    if len(res["56"]) != len(alvo) or len(res["85"]) != len(alvo):
        return Resultado("FALHA", f"incompleto: {len(alvo)} arquivos, resultados 5.6={len(res['56'])} 8.5={len(res['85'])}",
                         "\n\n".join(det), s.values())
    if quebra:
        det.append("**Carregam no 5.6 e NAO no 8.5:**\n```\n"
                   + amostra(f"{f}  {' '.join(res['85'][f])}" for f in quebra) + "\n```")
        return Resultado("FALHA", f"{len(alvo)} arquivos, {len(quebra)} so quebram no 8.5", "\n\n".join(det), s.values())
    return Resultado("OK", f"{len(alvo)} arquivos, 0 so no 8.5 ({nos_dois} falham nos dois)", "\n\n".join(det), s.values())

def passo_6(ctx, args):
    return comparar_harness(ctx, "6_classes", "scratchpad/instancia_classes.php",
                            "Instancia cada classe e compara uma assinatura do estado inicial. Pega construtor estilo "
                            "PHP 4 que ficou sem renomear: no PHP 8 ele nao executa, sem erro nem aviso.")

def passo_6b(ctx, args):
    return comparar_harness(ctx, "6b_escrita", "scratchpad/escrita.php",
                            "Simula um formulario enviado (um valor por campo), chama atualizacampos() e compara o que "
                            "cada campo leu. Uma linha `< campo '1003'` / `> campo 0` e a guarda `0 == \"\"` faltando: "
                            "dado errado gravado em silencio.")

def passo_6c(ctx, args):
    """Forma negada `$this->x != ""`. Mede em TODAS as classes (negada_alvos.py nao recebe prefixo)
    e o negada_compara.py separa o que e do lote. So os pares do lote decidem o resultado."""
    p = ctx["pasta"]
    tsv = os.path.join(p, "6c_negada.tsv")
    sh(["python3", "scratchpad/negada_alvos.py", os.path.relpath(tsv, ECIDADE)])  # o script entra em ecidade/
    cls = os.path.join(p, "6c_classes.txt")
    gravar(cls, "\n".join(sorted({l.split("\t")[0] for l in linhas(tsv)})) + "\n")
    s = {}
    for rt in RT:
        sh(["docker", "cp", "scratchpad/negada.php", f"{RT[rt]}:/tmp/negada.php"])
        # UM arquivo temporario POR RUNTIME: o /tmp e compartilhado entre os containers
        script = (f'cd {WEB}; while read c; do grep -F "$(printf "%s\\t" "$c")" {shlex.quote(dentro(tsv))} > /tmp/_neg_{rt}.tsv; '
                  f'php -d display_errors=0 /tmp/negada.php /tmp/_neg_{rt}.tsv 2>/dev/null </dev/null; done < {shlex.quote(dentro(cls))}')
        _, out, _ = sh(["docker", "exec", "-i", RT[rt], "sh", "-c", script], timeout=7200)
        s[rt] = os.path.join(p, f"6c_negada_{rt}.txt")
        gravar(s[rt], out)
    _, out, _ = sh(["python3", "scratchpad/negada_compara.py", s["56"], s["85"], os.path.join(p, "classes.txt")])
    rel = os.path.join(p, "6c_comparacao.txt")
    gravar(rel, out)
    m = re.search(r"VEREDITO: (\w+)", out)
    veredito = m.group(1) if m else "?"
    fora = re.search(r"== FORA DO LOTE: (\d+) pares", out)
    dentro_lote = re.search(r"^== DO LOTE: (\d+) pares", out, re.M)   # ^ e "== ": senao casa com o "FORA DO LOTE"
    resumo = f"{dentro_lote.group(1) if dentro_lote else '?'} divergencias no lote ({fora.group(1) if fora else '?'} fora do lote, ignoradas)"
    det = ("Saida do negada_compara.py. Os pares FORA DO LOTE sao de classes que o lote nao usa (areas ainda "
           "servidas pelo 5.6) e nao se corrigem aqui.\n\n```\n" + out.strip() + "\n```")
    situacao = {"PASSOU": "OK", "INCOMPLETO": "FALHA", "INVESTIGAR": "INVESTIGAR"}.get(veredito, "FALHA")
    return Resultado(situacao, resumo, det, [s["56"], s["85"], rel])

def normalizacao_do_cmp():
    """A MESMA normalizacao que o cmp.py aplica antes de comparar (sid, nomes temporarios, datas
    de PDF...). Lida do proprio cmp.py, e nao copiada, para o diagnostico enxergar exatamente a
    diferenca que a bateria enxergou. Devolve uma funcao bytes -> bytes."""
    fonte = ler("scratchpad/cmp.py")
    bloco = fonte[fonte.index("NORM = ["): fonte.index("def norm(")]
    ns = {"re": re}
    exec(bloco, ns)
    def norm(b):
        for rx, rep in ns["NORM"]:
            b = rx.sub(rep, b)
        return b
    return norm

LOG_PHP = os.path.join(ECIDADE, "extension", "log", "error.log")

def pedir(porta, tela, sid, sess):
    """Pede UMA tela a uma porta, como a bateria faz (sessao restaurada antes), e devolve
    (codigo HTTP, corpo, erros fatais do PHP, erros de SQL do PostgreSQL) daquele pedido.
    O error.log e zerado antes, e o log do banco e lido so a partir do instante do pedido."""
    sh(["docker", "exec", "-u", "root", "ecidade_php56", "sh", "-c",
        f"cp /tmp/_diag_sess.bak {sess}; chown www-data:www-data {sess}"])
    open(LOG_PHP, "w").close()
    t0 = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    r = subprocess.run(["curl", "-s", "-m", "60", "-b", f"ECIDADEWINDOWMAIN={sid}", "-w", "\n@@%{http_code}",
                        f"http://localhost:{porta}/{tela}"], capture_output=True, stdin=subprocess.DEVNULL)
    corpo, _, codigo = r.stdout.rpartition(b"\n@@")
    import time; time.sleep(1)               # o Logger e o PostgreSQL gravam logo depois da resposta
    fatais = sorted({re.sub(r"^\[[^]]*\]\s*", "", l).strip() for l in ler(LOG_PHP).splitlines()
                     if "E_ERROR" in l or "Uncaught" in l})
    _, out, err = sh(["docker", "logs", "--since", t0, "ecidade_database"])
    # o docker devolve o log ja em UTF-8 (com o caractere de substituicao no lugar do LATIN-1 que nao
    # converteu); o sh() decodificou como latin-1, entao desfaz e decodifica como UTF-8
    sql, ls = [], (out + err).encode("latin-1").decode("utf-8", "replace").splitlines()
    for i, l in enumerate(ls):
        if "ERRO:" in l:                     # o log do PostgreSQL e em PORTUGUES (locale pt_BR)
            sql.append(l.split("ERRO:", 1)[1].strip()
                       + (" | " + ls[i + 1].split(":", 1)[-1].strip() if i + 1 < len(ls) and "INSTRU" in ls[i + 1] else ""))
    return codigo.decode() or "000", corpo, fatais, sql

def trecho_diferente(a, b, contexto=80):
    """Onde dois corpos (ja normalizados) comecam a diferir, com um pouco de texto em volta."""
    i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
    ini = max(0, i - contexto)
    fmt = lambda x: x[ini:i + contexto].decode("latin-1").replace("\n", "\\n")
    return i, fmt(a), fmt(b)

def diagnosticar(telas, sid, p):
    """Para cada tela divergente: pede de novo aos dois runtimes, coleta os erros e classifica
    pela tabela de decisao do guia (passo 7). Devolve as linhas para o relatorio."""
    norm = normalizacao_do_cmp()
    sess = f"/var/lib/php/sessions/sess_{sid}"
    sh(["docker", "exec", "-u", "root", "ecidade_php56", "cp", sess, "/tmp/_diag_sess.bak"])
    saida = []
    try:
        for tela in telas:
            c56, b56, f56, q56 = pedir(8080, tela, sid, sess)
            c85, b85, f85, q85 = pedir(8085, tela, sid, sess)
            n56, n85 = norm(b56), norm(b85)
            if c56 == c85 and n56 == n85:
                tipo = "NAO REPRODUZIU (identica agora: diferenca ocasional, ex. horario)"
            elif c56 == "200" and c85 != "200":
                tipo = "REGRESSAO: quebra so no 8.5 -> corrigir"
            elif c56 != "200" and c85 == "200":
                tipo = "PRE-EXISTENTE: quebra so no 5.6 (defeito da referencia) -> registrar, nao corrigir"
            elif c56 != "200" and c85 != "200":
                tipo = "QUEBRA NOS DOIS (pre-existente ou dado ausente) -> nao mexer; conferir se a causa e a mesma"
            else:
                tipo = "SILENCIOSA: 200 nos dois, conteudo diferente -> o tipo mais perigoso, ver o trecho"
            bloco = [f"### {tela}", "", f"- 5.6: HTTP {c56}, {len(b56)} bytes; 8.5: HTTP {c85}, {len(b85)} bytes",
                     f"- **Classificacao: {tipo}**"]
            for rt, fat, sql in (("8.5", f85, q85), ("5.6", f56, q56)):
                for x in fat[:3]:
                    bloco.append(f"- erro do PHP no {rt}: `{x[:400]}`")
                for x in sql[:3]:
                    bloco.append(f"- erro de SQL no {rt}: `{x[:400]}`")
            if c56 == c85 == "200" and n56 != n85:
                pos, t56, t85 = trecho_diferente(n56, n85)
                bloco += [f"- as paginas comecam a diferir no byte {pos}:", "", "```",
                          f"5.6: ...{t56}...", f"8.5: ...{t85}...", "```"]
            if not (f56 or f85 or q56 or q85) and not (c56 == c85 == "200"):
                bloco.append("- nenhum erro registrado nos logs: ver o corpo da resposta (pagina de erro da aplicacao?)")
            for rt, b in (("56", b56), ("85", b85)):
                gravar(os.path.join(p, "7_corpo_" + tela.replace("/", "_") + f"_{rt}.html"), b.decode("latin-1"))
            saida.append("\n".join(bloco))
    finally:
        sh(["docker", "exec", "-u", "root", "ecidade_php56", "sh", "-c",
            f"cp /tmp/_diag_sess.bak {sess}; chown www-data:www-data {sess}; rm -f /tmp/_diag_sess.bak"])
    return saida

def passo_7(ctx, args):
    """Bateria byte a byte (scratchpad/cmp.py) em todas as telas dos prefixos. O cmp.py restaura a
    sessao antes de cada pedido, normaliza o que muda a cada requisicao e refaz o par antes de acusar."""
    p = ctx["pasta"]
    # Prova de fumaca: com sessao invalida as duas portas devolvem a mesma pagina de login e a
    # bateria daria "tudo identico" sem ter testado nada. Exige uma tela de verdade (> 1 KB).
    sid = ctx["sid"]
    sess = f"/var/lib/php/sessions/sess_{sid}"
    sh(["docker", "exec", "-u", "root", "ecidade_php56", "cp", sess, "/tmp/_verif_sess.bak"])
    _, tam, _ = sh(["curl", "-s", "-o", "/dev/null", "-w", "%{size_download}", "-b", f"ECIDADEWINDOWMAIN={sid}",
                    "http://localhost:8080/cem1_campas001.php"])
    sh(["docker", "exec", "-u", "root", "ecidade_php56", "sh", "-c",
        f"cp /tmp/_verif_sess.bak {sess}; chown www-data:www-data {sess}; rm -f /tmp/_verif_sess.bak"])
    if int(tam or 0) < 1000:
        return Resultado("FALHA", f"sessao invalida (tela de teste com {tam} bytes)",
                         "A sessao nao esta autenticada: a bateria compararia duas paginas de login. Entre em "
                         "http://localhost:8090 (dbseller/dbseller) e rode de novo, ou passe --sid.")
    rx = "^(?:" + "|".join(re.escape(x) for x in args.prefixos) + ")[0-9]*_"
    div = os.path.join(p, "7_divergentes.txt")
    _, out, err = sh(["python3", "scratchpad/cmp.py", sid, rx, div], timeout=6 * 3600)
    log = os.path.join(p, "7_bateria.log")
    gravar(log, out + err)
    m = re.search(r"=== (\d+)/(\d+) identicas, (\d+) divergentes, (\d+) timeout ===", out)
    if not m:
        return Resultado("FALHA", "a bateria nao terminou (ver 7_bateria.log)", "```\n" + (out + err)[-2000:] + "\n```", [log])
    ok, tot, nd, nt = map(int, m.groups())
    linhas_div = [l for l in (out + err).splitlines() if l.strip().startswith(("DIVERGE", "TIMEOUT", "PULADA"))]
    det = (f"Regex das telas: `{rx}`. Resultado: **{ok}/{tot} identicas**, {nd} divergentes, {nt} timeout.\n\n"
           "Cada divergencia precisa de diagnostico (guia, passo 7: log do PostgreSQL, error.log, tabela de decisao): "
           "pode ser regressao (quebra so no 8.5) ou defeito pre-existente (quebra igual, ou so no 5.6).")
    if linhas_div:
        det += "\n\n```\n" + amostra(linhas_div, 40) + "\n```"
    if nd or nt:
        # Diagnostico automatico de cada divergente (os timeouts nao: repetir o pedido levaria mais 60 s
        # cada e o motivo de um timeout raramente aparece em log).
        divergentes = [l.split()[1] for l in linhas_div if l.strip().startswith("DIVERGE")]
        if divergentes:
            det += ("\n\n**Diagnostico automatico** (cada tela pedida de novo aos dois runtimes, com os logs limpos; "
                    "a classificacao segue a tabela de decisao do guia, passo 7). As paginas de cada lado ficam na "
                    "pasta como `7_corpo_<tela>_56.html` / `_85.html`.\n\n" + "\n\n".join(diagnosticar(divergentes, sid, p)))
        return Resultado("INVESTIGAR", f"{ok}/{tot} identicas, {nd} divergentes, {nt} timeout", det, [log, div])
    return Resultado("OK", f"{ok}/{tot} telas identicas", det, [log])

FUNCOES = {"4b": passo_4b, "5": passo_5, "5b": passo_5b, "6": passo_6, "6b": passo_6b, "6c": passo_6c, "7": passo_7}
TITULOS = {"4b": "funcoes novas existem no 5.6", "5": "php -l nos dois runtimes", "5b": "carga dos arquivos (LSP)",
           "6": "instanciar as classes", "6b": "caminho de escrita", "6c": "forma negada != \"\"",
           "7": "bateria byte a byte"}

# ---------------------------------------------------------------------------------------------
# Relatorio
# ---------------------------------------------------------------------------------------------

def relatorio(ctx, args, resultados, inicio):
    """Escreve RELATORIO.md: cabecalho, tabela-resumo e uma secao por passo."""
    _, br, _ = sh(["git", "branch", "--show-current"])
    _, hd, _ = sh(["git", "log", "-1", "--format=%h %s"])
    fim = datetime.datetime.now()
    r = [f"# Verificacao do lote `{args.lote}` ({' '.join(args.prefixos)})", "",
         f"- Data: {inicio:%d/%m/%Y %H:%M} (duracao {str(fim - inicio).split('.')[0]})",
         f"- Branch: `{br.strip()}`, HEAD `{hd.strip()}`; alteracoes medidas contra `{args.base}` "
         f"({len(ctx['alterados'])} arquivos alterados em ecidade/)",
         f"- Universo: {len(ctx['codigo'])} arquivos de codigo, {len(ctx['classes'])} classes",
         f"- Pasta: `{os.path.relpath(ctx['pasta'], RAIZ)}`", "",
         "| Passo | O que verifica | Situacao | Resumo |", "| --- | --- | --- | --- |"]
    for k in PASSOS:
        res = resultados.get(k)
        r.append(f"| {k} | {TITULOS[k]} | **{res.situacao if res else 'PULADO'}** | {res.resumo if res else ''} |")
    r += ["", "Situacoes: OK = criterio atingido; FALHA = defeito ou teste incompleto; INVESTIGAR = divergencia a "
          "diagnosticar; AVISO = nada a corrigir, mas conferir; PULADO = nao rodou.",
          "Fora deste relatorio (rodar a mao, ver o guia): passo 4 (Rector), nivel 3 (POST real), passos 8/8b (roteamento)."]
    for k in PASSOS:
        res = resultados.get(k)
        if not res:
            continue
        r += ["", f"## {k} - {TITULOS[k]}: {res.situacao}", "", res.detalhe]
        if res.arquivos:
            r += ["", "Arquivos brutos: " + ", ".join(f"`{os.path.basename(a)}`" for a in res.arquivos)]
    # Secao final: o que sao os artefatos conhecidos que os passos 6 e 6b ignoram
    vistos = ctx.get("artefatos_vistos", set())
    r += ["", "## Artefatos conhecidos (passos 6 e 6b)", "",
          "Classes que aparecem diferentes entre o 5.6 e o 8.5 por causa do **teste**, nao da migracao. Os passos 6 e 6b "
          "ignoram as linhas delas; qualquer **outra** diferenca conta como defeito. Registrados nas areas Patrimonial, "
          "Financeiro e Saude e explicados no guia (`docs/migrar-um-modulo.md`, passos 6 e 6b).", "",
          "| Apareceu nesta execucao? | Classe | O que aparece | Por que nao e defeito |", "| --- | --- | --- | --- |"]
    for _, cls, oque, porque in ARTEFATOS_LISTA:
        r.append(f"| {'**sim**' if cls in vistos else 'nao'} | `{cls}` | {oque} | {porque} |")
    caminho = os.path.join(ctx["pasta"], "RELATORIO.md")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")
    return caminho

# ---------------------------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Roda as verificacoes automaticas de um lote (ver o docstring do arquivo).")
    ap.add_argument("lote", help="nome do lote, usado no nome da pasta de saida (ex.: as)")
    ap.add_argument("prefixos", nargs="+", help="prefixos das telas do lote (ex.: soc hab)")
    ap.add_argument("--so", default=",".join(PASSOS), help="passos a rodar, separados por virgula")
    ap.add_argument("--continuar", action="store_true", help="nao parar no primeiro passo que falhar")
    ap.add_argument("--base", default="HEAD", help="referencia do git para medir as alteracoes do lote")
    ap.add_argument("--sid", default=None, help="sessao autenticada para a bateria")
    args = ap.parse_args()
    escolhidos = [x.strip() for x in args.so.split(",") if x.strip()]
    invalidos = [x for x in escolhidos if x not in FUNCOES]
    if invalidos:
        sys.exit(f"ERRO: passo(s) desconhecido(s): {', '.join(invalidos)}. Validos: {', '.join(PASSOS)}")

    inicio = datetime.datetime.now()
    ctx = preparar(args)
    print(f"Lote {args.lote} ({' '.join(args.prefixos)}): {len(ctx['codigo'])} arquivos, {len(ctx['classes'])} classes")
    print(f"Saida em {os.path.relpath(ctx['pasta'], RAIZ)}/\n")

    resultados, parar = {}, False
    for k in PASSOS:
        if k not in escolhidos or parar:
            continue
        print(f"  {k:3} {TITULOS[k]:32} ...", end="", flush=True)
        try:
            res = FUNCOES[k](ctx, args)
        except subprocess.TimeoutExpired:
            res = Resultado("FALHA", "estourou o tempo limite", "O passo nao terminou no tempo limite.")
        resultados[k] = res
        print(f"\r  {k:3} {TITULOS[k]:32} {res.situacao:10} {res.resumo}")
        if res.situacao in ("FALHA", "INVESTIGAR") and not args.continuar:
            parar = True
            print("\n  Parado no primeiro passo com problema (use --continuar para seguir mesmo assim).")

    caminho = relatorio(ctx, args, resultados, inicio)
    print(f"\nRelatorio: {os.path.relpath(caminho, RAIZ)}")
    ruins = [k for k, r in resultados.items() if r.situacao in ("FALHA", "INVESTIGAR")]
    sys.exit(1 if ruins else 0)

if __name__ == "__main__":
    main()
