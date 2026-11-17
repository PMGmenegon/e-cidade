#!/usr/bin/env python3
"""Triagem por leitura de codigo de emissores de documento (feita antes de rodar cada emissor).

Uso (na raiz da worktree):  python3 ecidade/tests/sistema/documentos/triagem.py tela1.php tela2.php ...
Para cada tela, procura no PROPRIO arquivo e nos arquivos que ele inclui (include/require com literal, 1 nivel,
exceto libs/, dbforms/ e classes/db_*_classe.php, que so DEFINEM incluir/alterar/excluir/transacao) e, nos relatorios
Agata, o .agt chamado por cl_dbagata("x.agt") os padroes de escrita:
INSERT/UPDATE/DELETE em SQL, ->incluir/->alterar/->excluir, transacao, db_acount*/auditoria, pg_lo_*, e as chamadas de
configuracao de relatorio. Imprime os achados com arquivo:linha; quem decide e a leitura humana (registrada em
docs/registro/documentos-linha-de-base.md). O vigia do banco (documentos.py captura --vigia) e a segunda barreira, em volta de cada emissao.
"""
import os, re, sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
ESCRITA = re.compile(r'(?i)\b(insert\s+into|update\s+[\w.]+\s+set|delete\s+from)\b|->(incluir|alterar|excluir|incluir_|alterar_)\w*\s*\(|'
                     r'db_inicio_transacao|db_fim_transacao|\bBEGIN\b|db_acount|auditoria|pg_lo_(create|write|import|unlink)|'
                     r'orcparamseqfiltropadrao|->save\s*\(|->persist\s*\(|DB::(insert|update|delete)')
INC = re.compile(r'(?:include|require)(?:_once)?\b[^;]*?;', re.S)
LIT = re.compile(r'[\'"]([\w./\-]+\.(?:php|class|inc))[\'"]')

def le(p):
    return open(os.path.join(RAIZ, p), 'rb').read().decode('latin-1')

def achados(p):
    out = []
    for n, l in enumerate(le(p).splitlines(), 1):
        if ESCRITA.search(l) and not l.strip().startswith(('//', '*', '#')):
            out.append(f'    {p}:{n}: {l.strip()[:110]}')
    return out

def main():
    for tela in sys.argv[1:]:
        if not os.path.exists(os.path.join(RAIZ, tela)):
            print(f'{tela}: NAO EXISTE'); continue
        alvos = [tela]
        for st in INC.findall(le(tela)):
            for lit in LIT.findall(st):
                if lit.startswith(('libs/', 'dbforms/')) or re.match(r'classes/db_\w+_classe\.php', lit): continue
                if os.path.exists(os.path.join(RAIZ, lit)) and lit not in alvos: alvos.append(lit)
        for agt in re.findall(r'cl_dbagata\(\s*[\'"]([\w./\-]+\.agt)[\'"]', le(tela)):
            p = 'dbagata/reports/' + agt
            if os.path.exists(os.path.join(RAIZ, p)): alvos.append(p)
            else: print(f'    AVISO: {p} nao existe')
        res = [a for p in alvos for a in achados(p)]
        print(f'{tela}: {"SEM ACHADO de escrita" if not res else str(len(res)) + " achado(s)"}  (lidos: {len(alvos)} arquivo(s))')
        print('\n'.join(res[:25]))

if __name__ == '__main__':
    main()
