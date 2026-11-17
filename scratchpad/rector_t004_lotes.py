#!/usr/bin/env python3
"""T-004: roda o dry-run do Rector sobre o recorte em LOTES e junta tudo num JSON so.

Por que lotes: numa execucao unica sobre os 20 mil arquivos, um worker do modo paralelo morre
(memory_limit) e o Rector aborta inteiro -- 'Process "<id>" not found' (ProcessPool.php:28) --
sem nenhum resultado. Em lotes, o lote que falha e dividido ao meio ate isolar o arquivo; o
arquivo isolado vira um erro registrado em vez de derrubar a varredura.

Uso (da raiz do repositorio; os containers do agente no ar):
    python3 scratchpad/rector_t004_lotes.py <container_85> <alvos.txt> <saida.json> [tam_lote] [dir_rector]
  dir_rector: pasta da instalacao do Rector sob ecidade/ (padrao tmp/rector; tmp/rector22 = PHPStan 2.2.17)
NAO altera arquivo do sistema (--dry-run). Escreve so em ecidade/tmp/ (gitignored) e na saida.
"""
import json
import os
import subprocess
import sys

C, ALVOS, SAIDA = sys.argv[1:4]
TAM = int(sys.argv[4]) if len(sys.argv) > 4 else 500
DIR = '/var/www/html/' + (sys.argv[5] if len(sys.argv) > 5 else 'tmp/rector')
TMP = 'ecidade/tmp/t004_lote.txt'


def roda(arqs):
    with open(TMP, 'w', encoding='latin-1') as f:
        f.write('\n'.join(arqs) + '\n')
    p = subprocess.run(
        ['docker', 'exec', '-u', '1000', '-i', '-e', 'ALVOS=/var/www/html/tmp/t004_lote.txt', C,
         'php', '-d', 'memory_limit=3G', '-d', 'display_errors=stderr',
         DIR + '/vendor/bin/rector', 'process', '--dry-run', '--memory-limit=3G',
         '--config', DIR + '/rector-t004-timeout.php',
         '--no-progress-bar', '--output-format=json'],
        stdin=subprocess.DEVNULL, capture_output=True)
    try:
        d = json.loads(p.stdout.decode('utf-8', 'replace'))
    except ValueError:
        err = [l for l in p.stderr.decode('utf-8', 'replace').splitlines()
               if l.strip() and not l.startswith('Deprecated')]
        return None, ' | '.join(err[-4:])[:400]
    if any('system errors count limit' in str(e.get('message')) or 'Child process' in str(e.get('message'))
           for e in (d.get('errors') or [])):
        return None, ' | '.join(str(e.get('message')) for e in d['errors'])[:400]
    return d, None


def processa(arqs, diffs, erros, nivel=0):
    d, falha = roda(arqs)
    if d is not None:
        diffs.extend(d.get('file_diffs') or [])
        erros.extend(d.get('errors') or [])
        return
    if len(arqs) == 1:
        erros.append({'file': '/var/www/html/' + arqs[0], 'message': 'lote isolado falhou: ' + falha})
        print('   ISOLADO', arqs[0], falha[:150], flush=True)
        return
    print('   %slote de %d falhou (%s); dividindo' % ('  ' * nivel, len(arqs), falha[:100]), flush=True)
    m = len(arqs) // 2
    processa(arqs[:m], diffs, erros, nivel + 1)
    processa(arqs[m:], diffs, erros, nivel + 1)


def main():
    alvos = [l.strip() for l in open(ALVOS, encoding='latin-1') if l.strip()]
    diffs, erros = [], []
    for i in range(0, len(alvos), TAM):
        processa(alvos[i:i + TAM], diffs, erros)
        print('lote %d-%d: %d com pendencia, %d erros (acumulado)' % (
            i, min(i + TAM, len(alvos)), len(diffs), len(erros)), flush=True)
    json.dump({'totals': {'changed_files': len(diffs), 'errors': len(erros)},
               'file_diffs': diffs, 'errors': erros}, open(SAIDA, 'w'))
    os.remove(TMP)
    print('totais', len(alvos), 'arquivos;', len(diffs), 'com pendencia;', len(erros), 'erros')


if __name__ == '__main__':
    main()
