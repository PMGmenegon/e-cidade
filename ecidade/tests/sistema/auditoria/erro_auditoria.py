#!/usr/bin/env python3
"""Caminho de erro da auditoria de acesso (db_logs, libs/db_stdlib.php) igual nos dois runtimes - T-029.

  erro_auditoria.py --modo ro --sessao ARQ [--tela soc2_familiabairro001.php] [--p56 8080 --c56 ecidade_php56 --p85 8085 --c85 ecidade_php85]
  erro_auditoria.py --modo rw ...

ro: containers criados com SOMENTE_LEITURA=1, onde o nextval/INSERT do log falha. Exige, nos dois runtimes, HTTP 200 e o corpo
    exatamente "Houve um problema ao realizar a auditoria do sistema." (53 B), que e o que o 5.6 mostra.
rw: containers que gravam (rodar dentro de vigia-banco.sh antes/depois): a mesma tela tem de dar a mesma resposta normalizada nos
    dois, e nenhuma delas pode ser a mensagem de auditoria (caminho normal intacto).
ARQ e a sessao criada por sessao.sh (relatorios-kernel/); e restaurada antes de cada pedido. Sai 0 passou / 1 falhou.
"""
import argparse, re, subprocess, sys

MSG = b'Houve um problema ao realizar a auditoria do sistema.'
NORM = [(re.compile(rb'sid=[0-9a-f]{8,}'), b'sid=X'), (re.compile(rb'wname[0-9]+'), b'wnameX'), (re.compile(rb'[0-9a-f]{32}'), b'MD5X'),
        (re.compile(rb'localhost:[0-9]{2,5}'), b'localhost:PORT'), (re.compile(rb'[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}'), b'DATAHORA')]

def sh(c):
    return subprocess.run(c, capture_output=True)

def pede(porta, cont, sessao, sid, tela):
    destino = f'/var/lib/php/sessions/sess_{sid}'
    sh(['docker', 'cp', sessao, f'{cont}:{destino}'])
    sh(['docker', 'exec', '-u', 'root', cont, 'sh', '-c', f'chown www-data:www-data {destino}; chmod 600 {destino}'])
    o = sh(['curl', '-s', '-m', '60', '-b', f'ECIDADEWINDOWMAIN={sid}', '-w', '\n@@%{http_code}', f'http://localhost:{porta}/{tela}']).stdout
    i = o.rfind(b'\n@@')
    corpo = o[:i]
    for rx, rep in NORM: corpo = rx.sub(rep, corpo)
    return o[i + 3:].decode(), corpo

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--modo', choices=['ro', 'rw'], required=True); p.add_argument('--sessao', required=True)
    p.add_argument('--tela', default='soc2_familiabairro001.php')
    p.add_argument('--p56', default='8080'); p.add_argument('--c56', default='ecidade_php56')
    p.add_argument('--p85', default='8085'); p.add_argument('--c85', default='ecidade_php85')
    a = p.parse_args()
    sid = open(a.sessao + '.sid').read().strip()
    r56 = pede(a.p56, a.c56, a.sessao, sid, a.tela); r85 = pede(a.p85, a.c85, a.sessao, sid, a.tela)
    for rt, (cod, corpo) in (('5.6', r56), ('8.5', r85)):
        print(f'{rt}: HTTP {cod}, {len(corpo)} B' + (' (mensagem de auditoria)' if corpo.strip() == MSG else ''))
    ok = r56 == r85
    if a.modo == 'ro':
        ok = ok and all(c == '200' and b.strip() == MSG for c, b in (r56, r85))
    else:
        ok = ok and all(MSG not in b for _, b in (r56, r85))
    print('PASSOU' if ok else 'FALHOU'); return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
