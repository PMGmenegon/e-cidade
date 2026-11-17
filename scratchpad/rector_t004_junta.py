#!/usr/bin/env python3
"""T-004: atualiza o JSON do dry-run quando a integracao anda durante a varredura.

A varredura inteira (rector_t004.sh, ~20 mil arquivos) leva horas; se a laravel/integracao recebe
commits no meio, refaz-se o dry-run SO nos arquivos do recorte que mudaram ou entraram
(rector_t004_lotes.py sobre essa lista) e junta-se aqui:
  - sai do JSON velho todo arquivo que nao esta mais no recorte novo ou que foi refeito;
  - entram os resultados refeitos.

Uso (da raiz do repositorio):
    python3 scratchpad/rector_t004_junta.py <velho.json> <refeito.json> <refeitos.txt> <alvos_novo.txt> <saida.json>
"""
import json
import sys

RAIZ = '/var/www/html/'


def rel(p):
    return p[len(RAIZ):] if p.startswith(RAIZ) else p


def main():
    velho, refeito, refeitos, alvos, saida = sys.argv[1:6]
    v, r = json.load(open(velho)), json.load(open(refeito))
    feitos = {l.strip() for l in open(refeitos, encoding='latin-1') if l.strip()}
    recorte = {l.strip() for l in open(alvos, encoding='latin-1') if l.strip()}

    def fica(x):
        a = rel(x.get('file') or '')
        return a in recorte and a not in feitos

    diffs = [f for f in v.get('file_diffs') or [] if fica(f)] + (r.get('file_diffs') or [])
    erros = [e for e in v.get('errors') or [] if fica(e)] + (r.get('errors') or [])
    json.dump({'totals': {'changed_files': len(diffs), 'errors': len(erros)},
               'file_diffs': diffs, 'errors': erros}, open(saida, 'w'))
    print('pendencias', len(v.get('file_diffs') or []), '->', len(diffs),
          '; erros', len(v.get('errors') or []), '->', len(erros))


if __name__ == '__main__':
    main()
