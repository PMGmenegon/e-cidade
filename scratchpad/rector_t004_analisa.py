#!/usr/bin/env python3
"""T-004: transforma a saida JSON do dry-run do Rector na tabela de pendencias por arquivo e regra.

Uso (da raiz do repositorio):
    python3 scratchpad/rector_t004_analisa.py <final.json> <outras.tsv> <outra.json> <lint_falhas.txt> \
        <alvos.txt> <saida.tsv>

  final.json       dry-run sobre o recorte (rector_t004.sh, atualizado por rector_t004_junta.py)
  outras.tsv       "<branch>\\t<arquivo>": pendencias que outra branch altera (git diff --name-only)
  outra.json       dry-run sobre as versoes desses arquivos NA outra branch, extraidas para
                   tmp/t004_outra/<branch com / trocado por __>/<arquivo> (pode ser '-')
  lint_falhas.txt  docs/registro/lint-universo-falhas.txt (T-003): quem nao compila em cada runtime
  alvos.txt        o recorte (rector_recorte.py): total por grupo, para o zero aparecer como zero
  saida.tsv        classe, grupo, impacto, arquivo, regras, evidencia

Impacto de cada regra no PHP 8.5, MEDIDO com scripts minimos nos dois runtimes (tmp/t004_efeito/,
ver docs/registro/rector-varredura-t004.md):
  fatal       o 8.5 para (Error/TypeError/ArgumentCountError/parse error); o 5.6 roda
  silencioso  o 8.5 roda e devolve outro resultado
  aviso       o 8.5 roda igual e emite Warning/Deprecated
  nenhum      mesma saida nos dois; a regra so moderniza (e 2 delas emitem codigo que QUEBRA o 5.6)
  espaco      o diff so troca espaco em branco (nenhuma regra aplicada)

Classes, na ordem em que sao testadas:
  decisao-do-cliente         arquivo de area que o cliente mandou refazer a mao (BRANCH_DESCARTADA)
  ja-resolvida-outra-branch  outra branch altera o arquivo E o dry-run na versao dela da zero
  decisao-do-cliente         impacto nenhum/espaco (Regra 3: so atualizar, nao aplicar), nao compila
                             nem no 5.6 (T-003), ou biblioteca de terceiros embutida
  precisa-de-trabalho        todo o resto
"""
import collections
import json
import re
import sys

RAIZ = '/var/www/html/'

IMPACTO = {
    'ParseStrComExtractRector': 'fatal', 'EregToPregMatchRector': 'fatal',
    'ConsistentImplodeRector': 'fatal', 'RenameMktimeWithoutArgsToTimeRector': 'fatal',
    'ArrayKeyExistsOnPropertyRector': 'fatal', 'CreateFunctionToAnonymousFunctionRector': 'fatal',
    'CurlyToSquareBracketArrayStringRector': 'fatal', 'AssignArrayToStringRector': 'fatal',
    'Php4ConstructorRector': 'silencioso', 'GuardaComparacaoLiteralRector': 'silencioso',
    'PregReplaceEModifierRector': 'silencioso',
    'OptionalParametersAfterRequiredRector': 'aviso', 'FinalPrivateToPrivateVisibilityRector': 'aviso',
    'ThisCallOnStaticMethodToStaticCallRector': 'nenhum', 'StringClassNameToClassConstantRector': 'nenhum',
    'MultiDirnameRector': 'nenhum', 'GetCalledClassToStaticClassRector': 'nenhum',
    'SetCookieRector': 'nenhum', 'MbStrContainsRector': 'nenhum',
    # WrapVariableVariableNameInCurlyBracesRector: depende da forma (ver wrap_impacto)
}
ORDEM = ['fatal', 'silencioso', 'nao-medido', 'aviso', 'nenhum', 'espaco']
# $$x[...] no 5.6 e ${$x[...]}; no 7+ e ${$x}[...]. A forma simples $$x e igual nos dois.
VARVAR_ARRAY = re.compile(r'\$\$[A-Za-z_][A-Za-z0-9_]*\s*\[')

# Bibliotecas de terceiros copiadas para dentro do repositorio: porta-las (como a T-021 fez com o
# minimo para compilar) ou troca-las por versao nova e decisao, nao "migrar, nao consertar".
TERCEIROS = ('fpdf151/', 'securimage/', 'libs/jpgraph/', 'ext/php/Michelf/', 'scripts/widgets/jscalendar/',
             'dbagata/classes/jpgraph/', 'dbagata/classes/phpdocwriter/', 'dbagata/classes/fpdf151/',
             'dbagata/classes/pclzip/')

NOTA_BRANCH = {
    'nucleo/login-seguranca': ' (nao sera integrada: Regra 3)',
}
# Branch cujo porte o cliente descartou: os arquivos que ela altera sao da area que sera refeita a mao.
# Assistencia Social: T-001 revertida (31e3e5e84); fe5503916:docs/registro/correcoes-transversais.md l.3-5.
BRANCH_DESCARTADA = {
    'origin/assistencia-social/migracao': 'area a refazer a mao (decisao do cliente 13/11; T-001 revertida em 31e3e5e84)',
}


def rel(p):
    return p[len(RAIZ):] if p.startswith(RAIZ) else p


def grupo(p):
    if '/' in p:
        return p.split('/')[0]
    for pre in ('func_', 'db_'):
        if p.startswith(pre):
            return 'raiz:' + pre
    return 'raiz:outros'


def regras(f):
    return sorted({r.split('\\')[-1] for r in f.get('applied_rectors', [])})


def wrap_impacto(diff):
    removidas = [l for l in diff.splitlines() if l.startswith('-') and not l.startswith('---')]
    return 'silencioso' if any(VARVAR_ARRAY.search(l) for l in removidas) else 'nenhum'


def impacto(f):
    rs = regras(f)
    if not rs:
        return 'espaco'
    imps = [wrap_impacto(f['diff']) if r == 'WrapVariableVariableNameInCurlyBracesRector'
            else IMPACTO.get(r, 'nao-medido') for r in rs]
    return min(imps, key=ORDEM.index)


def le_lint(caminho):
    """{'5.6': set(arquivos), '8.5': set(arquivos)} a partir do arquivo da T-003."""
    sec, res = None, {'5.6': set(), '8.5': set()}
    for l in open(caminho, encoding='latin-1'):
        if l.startswith('### PHP '):
            sec = l.split()[2]
        elif l.startswith('./') and sec in res:
            res[sec].add(l[2:].split(' :: ')[0].strip())
    return res


def evid_padrao(g, outra):
    if g == 'raiz:func_':
        return 'janela de pesquisa servida hoje pelo 5.6; frente ja registrada (CLAUDE.md, dimensionamento.md)'
    if g.startswith('raiz:'):
        return 'tela fora do location/map do proxy: servida hoje pelo 5.6'
    return 'outra branch altera o arquivo' if outra else 'nenhuma branch altera o arquivo'


def main():
    final, outras, outra_json, lint, alvos, saida = sys.argv[1:7]
    d = json.load(open(final))
    falha = le_lint(lint)

    branch_de = collections.defaultdict(list)
    for l in open(outras, encoding='latin-1'):
        if l.strip():
            b, a = l.rstrip('\n').split('\t')
            branch_de[a].append(b)
    pend_outra = {}
    if outra_json != '-':
        for f in json.load(open(outra_json)).get('file_diffs') or []:
            slug, a = rel(f['file']).split('tmp/t004_outra/', 1)[1].split('/', 1)
            if regras(f):          # diff so de espaco nao e pendencia
                pend_outra[(slug.replace('__', '/'), a)] = regras(f)

    linhas, cont = [], collections.Counter()

    def classifica(a, imp):
        g = grupo(a)
        for b in branch_de.get(a, []):
            if b in BRANCH_DESCARTADA:
                return 'decisao-do-cliente', BRANCH_DESCARTADA[b]
        for b in branch_de.get(a, []):
            if (b, a) not in pend_outra:
                return 'ja-resolvida-outra-branch', '%s altera o arquivo; dry-run na versao dela = 0%s' % (
                    b, NOTA_BRANCH.get(b, ''))
        if imp in ('nenhum', 'espaco'):
            return 'decisao-do-cliente', 'mesma saida no 5.6 e no 8.5 (medido): Regra 3, nao aplicar'
        if imp == 'nao-compila' and a in falha['5.6']:
            return 'decisao-do-cliente', 'nao compila nem no 5.6 (T-003, lint-universo.md: falham nos dois)'
        if a.startswith(TERCEIROS):
            return 'decisao-do-cliente', 'biblioteca de terceiros embutida: portar (como T-021) ou trocar'
        ev = evid_padrao(g, branch_de.get(a))
        if imp == 'nao-compila':
            ev = 'nao compila so no 8.5 (T-003: 27 so no 8.5, lint-universo.md)'
        for b in branch_de.get(a, []):
            ev += '; %s altera mas restam %s' % (b, ','.join(pend_outra[(b, a)]))
        return 'precisa-de-trabalho', ev

    for f in d.get('file_diffs') or []:
        a, imp, rs = rel(f['file']), impacto(f), regras(f)
        cls, ev = classifica(a, imp)
        cont[(cls, imp)] += 1
        linhas.append((cls, grupo(a), imp, a, ','.join(rs) or '(so espaco)', ev))
    for e in d.get('errors') or []:
        a = rel(e['file'])
        cls, ev = classifica(a, 'nao-compila')
        cont[(cls, 'nao-compila')] += 1
        linhas.append((cls, grupo(a), 'nao-compila', a, 'ERRO: ' + e['message'][:90].replace('\t', ' '), ev))

    linhas.sort(key=lambda x: (x[0], x[1], x[3]))
    with open(saida, 'w', encoding='latin-1') as o:
        o.write('classe\tgrupo\timpacto\tarquivo\tregras\tevidencia\n')
        o.write(''.join('\t'.join(l) + '\n' for l in linhas))

    print('arquivos com diff: %d   erros (nao parseia): %d' % (len(d.get('file_diffs') or []),
                                                               len(d.get('errors') or [])))
    print('\npor regra (arquivos)')
    por_regra = collections.Counter(r for f in d.get('file_diffs') or [] for r in regras(f))
    for r, n in por_regra.most_common():
        print('  %-45s %6d' % (r, n))
    print('\npor classe e impacto')
    chave = lambda x: (x[0][0], ORDEM.index(x[0][1]) if x[0][1] in ORDEM else 9)
    for (cls, imp), n in sorted(cont.items(), key=chave):
        print('  %-27s %-12s %6d' % (cls, imp, n))
    tot = collections.Counter(grupo(l.strip()) for l in open(alvos, encoding='latin-1') if l.strip())
    pc = collections.defaultdict(collections.Counter)
    for l in linhas:
        pc[l[1]][l[0]] += 1
    print('\n  %-20s %8s %8s %8s %8s' % ('grupo', 'recorte', 'trabalho', 'cliente', 'outra'))
    for g in sorted(tot):
        print('  %-20s %8d %8d %8d %8d' % (g, tot[g], pc[g]['precisa-de-trabalho'],
                                           pc[g]['decisao-do-cliente'], pc[g]['ja-resolvida-outra-branch']))


if __name__ == '__main__':
    main()
