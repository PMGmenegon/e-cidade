#!/usr/bin/env python3
"""Decodifica o conteudo de codigos de barras Code 128 e de QR em imagens de PDF (uso: relatorio de documentos).

  decodifica_codigos.py code128 <pdf>   decodifica as barras Code 128 do PDF (imagens com mascara, como as das etiquetas Pimaco)
  decodifica_codigos.py qr <pdf>        decodifica os QR codes do PDF (precisa de python3 com opencv: cv2)

Extrai as imagens com `pdfimages -png` e, para as barras, usa a mascara (smask) como "tinta". Para cada imagem imprime
largura x altura e o texto lido; saida 1 se alguma imagem nao decodificar. So le o PDF; nada e gravado fora de /tmp.
"""
import os, subprocess, sys, tempfile

# Code 128: larguras das 6 faixas (barra, espaco, ...) de cada simbolo 0..105 e a do fim (106), em modulos.
PADROES = '212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 113222 123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412 211214 211232 233111'.split()
UNID = {p: i for i, p in enumerate(PADROES[:106])}
FIM = '2331112'


def imagens(pdf, tmp):
    subprocess.run(['pdfimages', '-png', pdf, os.path.join(tmp, 'i')], check=True)
    return sorted(os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith('.png'))


def corridas(png):
    from PIL import Image
    im = Image.open(png).convert('L')
    w, h = im.size
    linha = [im.getpixel((x, h // 2)) for x in range(w)]
    barra = [v > 127 for v in linha]  # a mascara e 255 onde ha tinta
    runs, atual, n = [], barra[0], 0
    for b in barra:
        if b == atual:
            n += 1
        else:
            runs.append((atual, n)); atual, n = b, 1
    runs.append((atual, n))
    while runs and not runs[0][0]:
        runs.pop(0)
    while runs and not runs[-1][0]:
        runs.pop()
    return [n for _, n in runs]


def code128(png):
    r = corridas(png)
    if len(r) < 13 or (len(r) - 7) % 6:
        return None
    nsim = (len(r) - 7) // 6 + 1          # simbolos de 6 faixas, mais o fim de 7
    total = sum(r)
    unid = total / (11 * nsim + 2)
    q = [max(1, round(n / unid)) for n in r]
    simb = [''.join(map(str, q[i:i + 6])) for i in range(0, len(q) - 7, 6)]
    if ''.join(map(str, q[-7:])) != FIM or any(s not in UNID for s in simb):
        return None
    v = [UNID[s] for s in simb]
    if sum(x * (i if i else 1) for i, x in enumerate(v[:-1])) % 103 != v[-1]:
        return None
    sub, saida = {103: 'A', 104: 'B', 105: 'C'}[v[0]], ''
    for x in v[1:-1]:
        if x in (99, 100, 101, 103, 104, 105):
            sub = {99: 'C', 100: 'B', 101: 'A'}.get(x, sub)
        elif sub == 'C':
            saida += '%02d' % x
        else:
            saida += chr(x + 32) if x < 96 or sub == 'B' else chr(x - 64)
    return saida


def qr(png):
    import cv2
    img = cv2.imread(png)
    img = cv2.copyMakeBorder(img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    texto, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return texto or None


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('code128', 'qr'):
        sys.exit(__doc__)
    modo, pdf = sys.argv[1:]
    falhou = False
    with tempfile.TemporaryDirectory() as tmp:
        for png in imagens(pdf, tmp):
            from PIL import Image
            w, h = Image.open(png).size
            if modo == 'code128' and (h > 60 or w < 20 or len(corridas(png)) < 13):
                continue   # a imagem RGB (so preta) e a mascara sao pares: so a mascara tem barras
            if modo == 'qr' and not (w == h):
                continue
            # barras: so a mascara carrega as barras; QR: a propria imagem
            lido = code128(png) if modo == 'code128' else qr(png)
            print('%dx%d\t%s' % (w, h, lido))
            falhou = falhou or lido is None
    sys.exit(1 if falhou else 0)


if __name__ == '__main__':
    main()
