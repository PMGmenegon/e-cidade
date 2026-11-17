# Etiquetas Pimaco, codigo de barras e QR com as versoes candidatas (PHP 8.5)

Medido em 14/11/2026 sobre `laravel/integracao` (`5e74b3e4c`). Mede se as bibliotecas de etiqueta e de codigo de barras/QR,
trocadas por versoes que rodam no PHP 8.5 e no Laravel novo, geram o mesmo documento que o PHP 5.6 gera hoje. Usa os casos
`pimaco_mpdf` e `barras_qr` da linha de base de `documentos-linha-de-base.md` (dubles por linha de comando, sem banco e sem
HTTP) e decodifica o conteudo dos codigos nas duas saidas. Nada do sistema nem do `vendor/` versionado foi alterado: as
candidatas ficaram num `vendor/` descartavel. mPDF, PhpSpreadsheet e PhpWord sao medidos em `documentos-candidatas.md`.

## 1. Inventario

| Biblioteca | Hoje (`composer.lock`) | Quem usa | Candidata | Roda no 8.5 hoje | Roda no 8.5 com a candidata |
|---|---|---|---|---|---|
| `proner/phppimaco` (etiquetas) | 1.3.0 | `app/Domain/Patrimonial/Patrimonio/` (4 arquivos: `EtiquetasPimacoPDF`, `EtiquetaModelo01/02Builder`, `EtiquetaBuilder`) | sem versao nova que resolva com o Laravel novo (1.3.0 exige `mpdf ^7.1`, `picqer ^0.2`, `endroid/qr-code ^2.5`); medida a 1.3.0 com o `require` alargado (so o `composer.json` do pacote) | nao (nao chega ao mPDF) | sim, com o `require` alargado |
| `picqer/php-barcode-generator` (barras Code 128 da etiqueta; so via Pimaco) | 0.2.2 | `vendor/proner/phppimaco/src/Tags/Barcode.php:85` | **3.3.0** | nao: `BarcodeGenerator.php:293` (`$code{$i}`) e erro de sintaxe no 8 | sim, com mudanca de saida (secao 3) |
| `mpdf/mpdf` (renderiza a etiqueta) | 7.1.9 | Pimaco | 8.3.1 | nao compila (`Mpdf.php:2238`) | sim |
| `aferrandini/phpqrcode` (QR dos modelos de impressao) | 1.0.1 | 6 modelos em `fpdf151/impmodelos/` | 1.0.1 (sem versao nova; abandonado) | sim | sim, saida identica |
| `endroid/qr-code` 2.5.1, `bacon/bacon-qr-code` 1.0.3, `khanamiryan/qrcode-detector-decoder` | no lock | so o `Tags/QrCode.php` do Pimaco, que o sistema **nao** chama (so `->barcode()`, `EtiquetaModelo01Builder.php:36`) | fora do conjunto novo (a 2.5.1 pede Symfony 2 e nao resolve com o Laravel novo) | nao usados | nao usados |
| Barras intercalado 2 de 5 (`FPDF::int25`, `fpdf151/fpdf.php`) | codigo do projeto | boletos, carnes, recibos (79 arquivos, 10 de menu) | nao e biblioteca de terceiro | sim | sim, saida identica |

## 2. Vendor descartavel

Copia do `ecidade/vendor` com so estas trocas, resolvida no PHP 8.5 (imagem `ecidade-login-php85`) a partir de copia do
`composer.json`/`composer.lock` (com `audit.block-insecure` desligado na copia):

```bash
# pimaco-pkg = copia de vendor/proner/phppimaco com o composer.json alargado:
#   version 1.3.0; mpdf/mpdf "^7.1 || ^8.0"; picqer "^0.2.0 || ^3.0"; sem endroid/qr-code
composer require mpdf/mpdf:8.3.1 picqer/php-barcode-generator:^3 proner/phppimaco:1.3.0 \
  -W --no-scripts --no-plugins --ignore-platform-req=php        # repositorio "path" para pimaco-pkg
composer dump-autoload --no-scripts --no-plugins
```

Resultado: `mpdf/mpdf` 8.3.1, `picqer/php-barcode-generator` 3.3.0, `setasign/fpdi` 2.6.10 (exigido pelo mPDF 8),
`proner/phppimaco` 1.3.0 (codigo do pacote intocado), `aferrandini/phpqrcode` 1.0.1. O `endroid/qr-code` sai junto com o
`require` do Pimaco. O mPDF 8 precisa de `vendor/mpdf/mpdf/tmp/mpdf` gravavel (o 7 tambem usa essa pasta).

Os dubles rodam por linha de comando no container, sem banco:

```bash
docker run --rm -v $PWD/ecidade:/var/www/html -v <vendor descartavel>:/var/www/html/vendor -w /var/www/html \
  ecidade-login-php85:latest php -d display_errors=stderr tests/sistema/documentos/dubles/gera_pimaco.php > pimaco.pdf
```

## 3. Resultado

| Caso | 5.6 (hoje) | 8.5 com o vendor de hoje | 8.5 com as candidatas |
|---|---|---|---|
| `pimaco_mpdf` | PDF 1 pagina, 4 etiquetas | nao gera (`Parse error` no mPDF 7 e no picqer 0.2.2) | PDF 1 pagina; paginas, tamanho, texto e numero de imagens **iguais**; barras **diferentes** (abaixo) |
| `barras_qr` | PDF 2 paginas, 3 barras 2 de 5, 1 QR | identico ao 5.6 | **identico** ao 5.6 e a linha de base (mesmo texto, mesma matriz do QR) |

### Conteudo dos codigos (decodificado)

`ecidade/tests/sistema/documentos/decodifica_codigos.py` extrai as imagens do PDF (`pdfimages`) e le o codigo: Code 128 por
decodificador proprio (larguras das barras, tabela do padrao, digito de controle) e QR com o `cv2.QRCodeDetector`.

```
python3 decodifica_codigos.py code128 pimaco.pdf
  5.6      122x15  000123  000124  000125  000126
  candidata 68x15  000123  000124  000125  000126          # mesmo conteudo, mesmo subconjunto C do Code 128
python3 decodifica_codigos.py qr barras_qr.pdf              # 5.6, 8.5 de hoje e candidata:
  175x175  https://exemplo.invalid/autenticidade/00000000-0000-0000-0000-000000000000
```

As barras int25 do `barras_qr` sao vetor no PDF: o PDF da candidata tem o mesmo conteudo de pagina que o do 5.6 (e que a
linha de base), portanto as mesmas barras.

### Diferenca de saida: a barra Code 128 da etiqueta fica 26% mais estreita no papel

O codigo do sistema pede largura de barra `1,8` (`EtiquetaModelo01Builder.php:36`, `->setWidth(1.8)`). O picqer 0.2.2 aceita
numero decimal (imagem de **122 px**, 128 ppi no PDF: 68,6 pt). O picqer 3.3.0 declara `int $widthFactor`
(`BarcodeGeneratorPNG.php:22`): o `1,8` vira `1` (imagem de **68 px**, 1 px por modulo, 96 ppi: 51 pt) e o PHP 8.5 avisa
"implicit conversion from float to int". Mesmo codigo, mesmo conteudo, mas a barra impressa na etiqueta perde 26% de largura
fisica (de 68,6 pt para 51 pt); a leitura por scanner nao foi medida. Nenhum inteiro reproduz o `1,8` (com `2` a barra fica
mais larga, 136 px, medido com `getBarcode("000123", TYPE_CODE_128, 2, 15)`; com `1.8` o picqer 3.3.0 mede 68 px e avisa).

## 4. Mudanca de API necessaria (nao feita)

| Onde | Mudanca |
|---|---|
| `vendor/proner/phppimaco/composer.json` | `require` aceitar `mpdf/mpdf ^8` e `picqer/php-barcode-generator ^3` e dispensar `endroid/qr-code` (fork do pacote ou repositorio proprio; o codigo do pacote nao precisou mudar) |
| `vendor/proner/phppimaco/src/Tags/Barcode.php:88-150` (`getBarcode($content, $tipo, $this->width, $this->height)`) | picqer 3 tem `int $widthFactor` e `int $height`: o `width` decimal (`1.8`) e truncado. Decisao a tomar: aceitar a barra mais estreita, ou passar largura inteira em `app/Domain/Patrimonial/Patrimonio/Builders/EtiquetaModelo01Builder.php:36` |
| `vendor/proner/phppimaco/src/Tags/QrCode.php:75-110` | usa a API do `endroid/qr-code` 2.x (`setWriterByName`, `setPadding`...); nao existe nas versoes atuais. O sistema nao chama `->qrcode()`, entao so importa se alguem passar a usar |
| `vendor/mpdf/mpdf/tmp/mpdf` | pasta gravavel no 8.5 (mesma exigencia do 7) |
| `vendor/picqer/php-barcode-generator` 0.2.2 | `$code{$i}` (`BarcodeGenerator.php:293`) nao compila no 8: so a 3.x serve |

## 5. O que isto nao prova

- Etiquetas com dados reais de bens (a base de exemplo nao tem bens): coberto so pelo duble, com 4 bens inventados e os
  modelos 01 e 02 (so o 01 e comparado).
- Leitura das barras por scanner fisico, em tamanho impresso.
- Boletos, carnes e recibos reais (as barras int25 e os QR dos `impmodelos` dependem de dados que a base nao tem; o duble usa as
  mesmas funcoes).
- Renderizacao: a comparacao e estrutural (texto, paginas, hash das imagens, conteudo de pagina) mais a decodificacao dos codigos.
