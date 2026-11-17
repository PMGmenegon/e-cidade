# Documentos com as versões candidatas de mPDF, PhpSpreadsheet e PhpWord (PHP 8.5)

> 13/11/2026 (rótulo: T-035). Mede se as versões candidatas destas três bibliotecas geram o mesmo documento que o 5.6 gera
> hoje, usando a linha de base de `documentos-linha-de-base.md` (casos, dublês e comparador em
> `ecidade/tests/sistema/documentos/`). Nada do sistema nem do `vendor/` versionado foi alterado: as candidatas foram
> instaladas num `vendor/` descartável e servidas por um container 8.5 próprio (mecanismo de `runtime-novo.md`).
> Etiquetas Pimaco, código de barras e QR são medidos à parte.

## Candidatas e o vendor de teste

| Biblioteca | Hoje (`ecidade/composer.lock`) | Candidata (`docs/migracao-laravel/matriz-versoes.md`) | No 8.5 hoje |
|---|---|---|---|
| `mpdf/mpdf` | 7.1.9 | **8.3.1** | não compila (`Mpdf.php:2238`) |
| `phpoffice/phpspreadsheet` | 1.8.2 | **5.11.0** | roda, com Warning na leitura (`Reader/Xlsx/Styles.php:133-134`) |
| `phpoffice/phpword` | 0.17.0 | **1.4.0** | roda |

O vendor de teste é uma cópia do `ecidade/vendor` com só estas três trocadas, resolvido no PHP 8.5 a partir de uma cópia do
`ecidade/composer.json`/`composer.lock`:

```bash
composer require mpdf/mpdf:8.3.1 phpoffice/phpspreadsheet:5.11.0 phpoffice/phpword:1.4.0 proner/phppimaco:1.3.0 \
  -W --no-scripts --ignore-platform-req=php      # com "audit": {"block-insecure": false} na copia do composer.json
```

- `proner/phppimaco` 1.3.0 exige `mpdf/mpdf ^7.1`: entrou por repositório `path` (cópia do pacote com o `require` aceitando
  também `^8.0`; o código do pacote não foi tocado). Sem isso o mPDF 8 não resolve junto com o Pimaco.
- `--ignore-platform-req=php`: vários pacotes do lock de hoje declaram PHP < 8.
- O `-W` (atualizar dependências) trouxe também: `setasign/fpdi` 1.6.2 → 2.6.10 (o mPDF 8 exige), `markbaker/complex` e
  `markbaker/matrix` 1.x → 3.0, `maennchen/zipstream-php` 3.2.2, `phpoffice/math` 0.3.0, `phpoffice/wmf` 0.2.1,
  `composer/pcre` 3.4.0, `nikic/php-parser` 3.1.5 → 4.19.5, `phpdocumentor/*`, `psr/container` 1.1.2, `webmozart/assert`
  2.5.0, polyfills Symfony; saíram `pclzip/pclzip`, `phpoffice/common`, `zendframework/zend-escaper`. São efeitos da troca
  que um `composer.lock` novo também terá.

Container de teste: `docker-compose.runtime-novo.yml` com `RN_DIR` apontando para a pasta com esse vendor; a mesma árvore
`ecidade/` do 5.6, o mesmo banco.

## Resultado por caso (5.6 de hoje × 8.5 com as candidatas)

Casos da linha de base que exercitam estas bibliotecas. `razao_xlsx` é emissão real (`con2_razaocontas002.php`, liberado na
triagem por leitura de código), em container que grava, com o vigia do banco antes/depois de **cada** pedido: 8 de 8 `OK` (só
`db_usuariosonline` e `db_logsacessa_*`). Os outros três são dublês por linha de comando, sem banco.

```bash
python3 ecidade/tests/sistema/documentos/documentos.py captura --sessao <sessao> --saida <dir> --vigia \
  --c56 <container 5.6> --p56 <porta> --c85 <container candidato> --p85 <porta>     # casos.tsv so com os 4 casos abaixo
python3 ecidade/tests/sistema/documentos/documentos.py compara --dir <dir>
```

| Caso | Biblioteca | Resultado | Classificação |
|---|---|---|---|
| `razao_xlsx` | PhpSpreadsheet 5.11.0 (escrita) | descrição estrutural (abas, dimensões, células) **igual** | **igual**; dentro do pacote, diferenças só de metadado e de serialização de valores padrão (abaixo) |
| `phpword_docx` | PhpWord 1.4.0 | descrição estrutural (arquivos e texto) **igual** | **diferente de conteúdo (formatação)**: ver abaixo |
| `planilhas_leitura` | PhpSpreadsheet 5.11.0 (leitura) | **não termina**: `Fatal error: Allowed memory size of 536870912 bytes exhausted` em `Worksheet/Worksheet.php:1364` | **diferente de conteúdo** (não gera); com leitura limitada às colunas com dado, as 21 planilhas são idênticas |
| `pimaco_mpdf` | Pimaco + mPDF 8.3.1 | **não chega ao mPDF**: `Parse error: syntax error, unexpected token "{"` em `picqer/php-barcode-generator/src/BarcodeGenerator.php:293` (picqer 0.2.2, dependência do Pimaco) | não medido para o mPDF: é o único caso da linha de base que usa mPDF, e depende da troca do gerador de código de barras |

### `razao_xlsx`: só metadado e valores padrão

Valores, abas e dimensões iguais. Dentro do `.xlsx` (XML formatado, 5.6 × candidata):

- `docProps/core.xml`: data de criação/modificação (muda a cada emissão); `docProps/app.xml`: `<Company>Microsoft
  Corporation</Company>` → `<Company/>`, `<HyperlinkBase/>` a mais.
- `xl/worksheets/sheet1.xml`: some o `<sheetProtection …>` com todos os atributos `false` e o `<headerFooter>` vazio;
  `<pageSetup>` igual, com `pageOrder="downThenOver"` (o padrão) explícito.
- `xl/styles.xml`: o preenchimento `gray125`, a borda vazia e o alinhamento padrão do estilo 0 são escritos na forma curta.

Tudo é valor padrão do formato; nenhum dado, estilo aplicado ou configuração de impressão muda.

### `phpword_docx`: formatação muda

Texto, tabela e quebra de página iguais; arquivos do pacote iguais. No XML:

- `word/document.xml`: **`<w:noWrap/>` em todas as células de tabela** (6 de 6). Com isso o Word deixa de quebrar o texto
  dentro da célula — muda a aparência de tabelas com texto longo (atas, contratos).
- `word/fontTable.xml`: fonte `Garamond` declarada a mais; `word/settings.xml`: `<w:bookFoldPrinting w:val="false"/>`;
  `word/styles.xml`: cor padrão `000000` explícita.
- `docProps/core.xml`: datas.

O `<w:noWrap/>` é padrão novo da biblioteca para células sem estilo; o código do sistema não o pede.

### `planilhas_leitura`: a coluna mais alta vira `XFD`

O PhpSpreadsheet 5.11.0 calcula para `config/templates/IN22/anexo12.xlsx` a coluna mais alta `XFD` (16.384ª coluna; a
1.8.2 dá `E`): `calculateWorksheetDimension()` = `A1:XFD990` no lugar de `A1:E990`; as células com dado continuam em
`A1:D990` (39 células, mesmo hash). Percorrer a linha com `getCellIterator()` sem limite cria as células vazias até `XFD` em
990 linhas e estoura a memória. Nas outras 20 planilhas as dimensões são as mesmas. Lendo só até a última coluna com dado
(`getCellIterator('A', $ws->getHighestDataColumn())`, variante do dublê só para medir, rodada nos dois lados), as 21
planilhas dão abas, dimensões de dado, número de células e hash **idênticos**, e o Warning que o 1.8.2 emite no 8.5 some.

O código do sistema percorre igual: `src/Library/SpreadSheet/Template/Parser.php:115-116` e `:147-148`
(`getCellIterator()` com `setIterateOnlyExistingCells(false)`) — é o leitor dos modelos IN22 usados pelos anexos do
TCE-RO (telas que citam os modelos IN22, ex.: `con2_tceroanexoin22.RPC.php`, `con2_tceroanexosin22011.php`). Com a candidata, a emissão desses anexos a partir
do `anexo12.xlsx` deve estourar a memória do mesmo jeito (não emitido aqui: as telas exigem dados que a base não tem).

## Mudanças que o código do sistema precisaria (não feitas)

Varredura por nome (`api_scan.py`, abaixo): métodos, classes e constantes que existem no vendor de hoje e não existem na
candidata, procurados nos arquivos do sistema que usam cada biblioteca (fora de `vendor/`, `tmp/` e `tests/`). Pega o que
foi **removido**; mudança de comportamento com o mesmo nome só aparece pela medição.

| Biblioteca | Removidos na candidata (métodos / classes / constantes) | Usos no sistema | Onde |
|---|---|---|---|
| PhpSpreadsheet | 292 / 17 / 39 | **32 pontos em 1 arquivo** | `app/Domain/Financeiro/Planejamento/Relatorios/ProgramaGestaoXls.php`: `setCellValueByColumnAndRow` (linhas 172, 173, 202, 243–247, 254, 260, 261, 264, 269, 271, 324, 350), `mergeCellsByColumnAndRow` (137, 153, 170, 171, 217, 219, 221, 225, 235, 253, 335), `getStyleByColumnAndRow` (138, 156, 180, 274, 338). Não existem na 5.11.0; os métodos equivalentes recebem a coordenada (`'A1'` ou `[coluna, linha]`). Usado pelo relatório `POST /v4/api/financeiro/planejamento/programa-gestao` |
| PhpSpreadsheet (comportamento) | — | 2 pontos | `src/Library/SpreadSheet/Template/Parser.php:115-116,147-148`: percorrer até a coluna mais alta estoura a memória com `anexo12.xlsx` (seção anterior) |
| PhpWord | 49 / 1 / 13 | 0 | o `<w:noWrap/>` é mudança de saída da biblioteca, sem chamada a trocar |
| mPDF | 32 / 3 / 0 | 0 | os 2 usos diretos (`db_download_todos_arquivos_visualizador.php:6-31`: `new Mpdf([...])`, `setFooter`, `AddPage`, `Image`, `Output(..., Destination::DOWNLOAD)`; `forms/db_frmprotprocessovolume.php:28`: `use Mpdf\Tag\Strong`) existem na 8.3.1 |
| Pimaco (pacote, não sistema) | — | — | `proner/phppimaco` 1.3.0 declara `mpdf/mpdf ^7.1` e depende de `picqer/php-barcode-generator` 0.2.2, que não compila no 8.5 |

```bash
# fontes das candidatas num projeto minimo (no PHP 8.5)
echo '{"require":{"mpdf/mpdf":"8.3.1","phpoffice/phpspreadsheet":"5.11.0","phpoffice/phpword":"1.4.0"}}' > composer.json
composer update --no-scripts
python3 api_scan.py <ecidade> <vendor do projeto minimo>
```

```python
#!/usr/bin/env python3
"""metodos, classes e constantes das 3 bibliotecas que existem no vendor de hoje e nao existem na candidata,
e onde o codigo do sistema os usa (heuristica por nome; confirmar lendo cada ponto). uso: api_scan.py <ecidade> <vendor-candidato>"""
import os, re, sys
ECI, NOVO = sys.argv[1], sys.argv[2]
LIBS = {'PhpSpreadsheet': ('phpoffice/phpspreadsheet/src', r'PhpOffice\\+PhpSpreadsheet'),
        'PhpWord': ('phpoffice/phpword/src', r'PhpOffice\\+PhpWord'),
        'mPDF': ('mpdf/mpdf/src', r'\bMpdf\\|\bmPDF\b')}
def scan(raiz):
    m, fq, k = set(), set(), set()
    for dp, _, fs in os.walk(raiz):
        for f in fs:
            if not f.endswith('.php'): continue
            t = open(os.path.join(dp, f), encoding='latin1').read()
            ns = re.search(r'^namespace\s+([\w\\]+);', t, re.M); ns = ns.group(1) + '\\' if ns else ''
            fq.update(ns + x for x in re.findall(r'^\s*(?:abstract\s+|final\s+|readonly\s+)*(?:class|interface|trait|enum)\s+(\w+)', t, re.M))
            m.update(x.lower() for x in re.findall(r'function\s+&?\s*(\w+)\s*\(', t))
            k.update(re.findall(r'\bconst\s+(?:\w+\s+)?(\w+)\s*=', t)); k.update(re.findall(r'^\s*case\s+(\w+)\s*[=;]', t, re.M))
    return m, fq, k
for lib, (rel, pat) in LIBS.items():
    om, ofq, ok = scan(os.path.join(ECI, 'vendor', rel)); nm, nfq, nk = scan(os.path.join(NOVO, rel))
    gm, gc, gk = om - nm, ofq - nfq, ok - nk
    hits = set()
    for dp, dn, fs in os.walk(ECI):
        dn[:] = [d for d in dn if d not in ('vendor', 'tmp', 'tests', 'node_modules', '.git')]
        for f in fs:
            if not f.endswith('.php'): continue
            p = os.path.join(dp, f); t = open(p, encoding='latin1').read()
            if not re.search(pat, t): continue
            rp = p[len(ECI) + 1:]
            for i, l in enumerate(t.split('\n'), 1):
                for x in re.findall(r'(?:->|::)(\w+)\s*\(', l):
                    if x.lower() in gm: hits.add((rp, i, 'metodo', x))
                for x in re.findall(r'((?:PhpOffice\\+Php(?:Spreadsheet|Word)|Mpdf)\\+[\w\\]+)', l):
                    c = re.sub(r'\\+', r'\\', x)
                    if c in gc: hits.add((rp, i, 'classe', c))
                for x in re.findall(r'::([A-Z][A-Z0-9_]+)\b', l):
                    if x in gk: hits.add((rp, i, 'constante', x))
    print(f'== {lib}: removidos na candidata: {len(gm)} metodos, {len(gc)} classes, {len(gk)} constantes; '
          f'usados no sistema: {len(hits)} pontos em {len(set(h[0] for h in hits))} arquivos')
    for h in sorted(hits): print('  %s:%d %s %s' % h)
```

## O que isto não prova

- O mPDF 8 contra a linha de base: o único caso com mPDF (etiqueta Pimaco) para antes, no gerador de código de barras.
- Emissões reais de Word (atas, contratos, minutas): dependem de modelo guardado no banco e de telas que gravam.
- Os anexos IN22 e o relatório "programa de gestão" emitidos de verdade: a base não tem dados; os pontos de código estão
  listados acima.
- A varredura é por nome: assinatura alterada ou comportamento novo com o mesmo nome só aparece medindo.
- A comparação é estrutural (texto, células, arquivos do pacote) mais a leitura do XML; não compara renderização.
