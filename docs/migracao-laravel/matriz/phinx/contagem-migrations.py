#!/usr/bin/env python3
"""Conta, em ecidade/db/migrations, o que o adaptador da DBSeller (Classes\\PostgresMigration/Table) faz diferente do Phinx padrao.
uso (na raiz da worktree):  python3 docs/migracao-laravel/matriz/phinx/contagem-migrations.py [pasta das migrations]
Le como latin-1 (a base e 64% ISO-8859-1; grep sem -a pularia esses arquivos). Cada numero sai em ARQUIVOS e em OCORRENCIAS (chamadas),
lidas por chamada com os parenteses balanceados (nao por linha); 'addForeignKey' em comentario de cabecalho nao conta.
Exclui index.php. A uniao no fim nao conta arquivo duas vezes."""
import glob, os, re, sys
D = sys.argv[1] if len(sys.argv) > 1 else 'ecidade/db/migrations'
arqs = [f for f in sorted(glob.glob(D + '/*.php')) if os.path.basename(f) != 'index.php']

def chamadas(txt, padrao):
    for m in re.finditer(padrao, txt):
        i = m.end(); n = 1; j = i
        while j < len(txt) and n:
            n += (txt[j] == '(') - (txt[j] == ')'); j += 1
        yield txt[i:j - 1]

def args(a):
    n = 0; partes = []; cur = ''; q = None
    for c in a:
        if q:
            cur += c; q = None if c == q else q; continue
        if c in "'\"": q = c
        n += (c in '([') - (c in ')]')
        if c == ',' and n == 0: partes.append(cur); cur = ''
        else: cur += c
    partes.append(cur)
    return [p.strip() for p in partes if p.strip()]

ins2 = {}; tab = {'qualificado': {}, 'opcao schema': {}, 'nenhum': {}}; fk = {}; lo = set(); forma = 0
for f in arqs:
    t = open(f, 'rb').read().decode('latin-1'); k = os.path.basename(f)
    for a in chamadas(t, r'->insert\('):
        if len(args(a)) >= 2: ins2[k] = ins2.get(k, 0) + 1
        if re.fullmatch(r'\$aColumns,\s*\$aValues', a.strip()): forma += 1
    for a in chamadas(t, r'\$this->table\('):
        nome = (args(a) or [''])[0]
        tipo = 'qualificado' if re.fullmatch(r"['\"][a-z_0-9]+\.[a-z_0-9]+['\"]", nome) else ('opcao schema' if re.search(r"['\"]schema['\"]\s*=>", a) else 'nenhum')
        tab[tipo][k] = tab[tipo].get(k, 0) + 1
    for a in chamadas(t, r'->addForeignKey\('):
        fk[k] = fk.get(k, 0) + 1
    if 'importLargeObject' in t: lo.add(k)

def linha(nome, d): print('%-48s %5d arquivos %6d ocorrencias' % (nome, len(d), sum(d.values())))
print('migrations (sem index.php):', len(arqs))
linha("->insert(colunas, valores) (2 listas)", ins2); print('   destas, a forma $table->insert($aColumns, $aValues):', forma, 'ocorrencias')
for tipo, d in tab.items(): linha('$this->table(...) %s' % tipo, d)
linha('->addForeignKey(', fk)
print('%-48s %5d arquivos' % ('importLargeObject', len(lo)))
afetadas = set(ins2) | set(tab['opcao schema']) | set(tab['nenhum']) | lo
print('Padrao (B) muda o comportamento em (uniao, sem dupla contagem):', len(afetadas), 'arquivos de', len(arqs),
      '= %.1f%%' % (100.0 * len(afetadas) / len(arqs)))
print('   dentro dela: insert 2 listas', len(set(ins2) & afetadas), '| table() sem qualificar', len(set(tab['opcao schema']) | set(tab['nenhum'])),
      '| addForeignKey', len(set(fk) & afetadas), '| importLargeObject', len(lo & afetadas))
