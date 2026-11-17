# `split()` do resumo da Solicitação de Compra no 8.5 (`mod_imprime11.php`) (T-052, 13/11/2026)

**Resumo:** a linha do resumo do modelo 11 do `db_impcarne` usa `split("[\n\r]", …)`. No 8.5 o `split()` vem do
polyfill do vendor (`dbseller/legacy`, `bootstrap/PHP_56.php`), que faz `explode()` e não trata a regex: o resumo
não é quebrado nem tem as linhas repetidas removidas. O modelo 11 é **alcançável no 8.5** (duas telas servidas pelo
8.5 o usam fixo). Corrigido com o mínimo: `split` → `preg_split("/[\n\r]/", …)`, igual ao 5.6 nos 6 casos medidos e
compatível com os dois runtimes. Uma linha alterada.

## Onde o modelo 11 é usado

`fpdf151/impcarne.php` (classe `db_impcarne`) recebe o número do modelo no construtor (`__construct(&$objpdf,
$impmodelo = null)`, linha 755) e no fim inclui `fpdf151/impmodelos/mod_imprime{$this->impmodelo}.php` (linha 1370).
O modelo 11 é a **Solicitação de Compra** (comentário no próprio `mod_imprime11.php`: `MODELO 11 - SOLICITACAO DE
COMPRA`).

| Quem instancia | Modelo | Servido pelo 8.5? |
|---|---|---|
| `com2_emitesolicita002.php:347` | `'11'` fixo | sim: prefixo `com` no `location` do proxy |
| `pes1_rhempemitesolfolha002.php:127` | `'11'` fixo | sim: prefixo `pes` no `location` do proxy |

As outras 73 instanciações de `db_impcarne` passam outro número fixo ou uma variável. As de compras que leem o modelo
de parâmetro (`com2_procorc002.php`, `com2_solorc002.php`, `emp2_ordemcompra002.php`) usam `pcparam`, que na base
tem 13/13/10 (consulta abaixo). Não há modelo específico de cliente para o 11 (`fpdf151/impmodelos/especificos/`
sem `*_11_*`).

Consultas (só leitura, `PGOPTIONS='-c default_transaction_read_only=on'`, `show default_transaction_read_only` = `on`):

```sql
select count(*), count(*) filter (where pc10_resumo ~ E'\r'),
       count(*) filter (where pc10_resumo ~ E'\n'), count(*) filter (where pc10_resumo <> '') from solicita;
-- 0|0|0|0   (a base de exemplo não tem nenhuma solicitação)
select pc30_instit, pc30_modeloorc, pc30_modeloorcsol, pc30_modeloordemcompra from pcparam order by 1;
-- 1|13|13|10
select count(*) from solicitem;   -- 0
```

## A diferença (antes) e a igualdade (depois)

O resumo vem de `pc10_resumo`, digitado num `<textarea>`: o navegador envia as quebras como CRLF.
`com2_emitesolicita002.php:403` e `pes1_rhempemitesolfolha002.php:152` copiam o campo para `$pdf1->Sresumo`, e o
`mod_imprime11.php:151` faz:

```php
$aResumo = array_unique(split("[\n\r]", $this->Sresumo));   // antes
$aResumo = array_unique(preg_split("/[\n\r]/", $this->Sresumo));   // depois
$Sresumo = implode("\n", $aResumo);
```

Trecho isolado `scratchpad/split_mod_imprime11.php` (a linha acima com o autoload do composer, como na tela; a base
não tem solicitação, então as entradas são as que um textarea produz). Saída literal (`json_encode`):

| Caso | 5.6 antes | 8.5 antes | 5.6 depois | 8.5 depois |
|---|---|---|---|---|
| vazio | `""` | `""` | `""` | `""` |
| uma linha | igual à entrada | igual | igual | igual |
| CRLF (3 linhas) | `"Aquisicao de material\n\nPara a secretaria X\nEntrega em 30 dias"` | `"Aquisicao de material\r\nPara a secretaria X\r\nEntrega em 30 dias"` | = 5.6 antes | = 5.6 antes |
| CRLF com repetidas | `"Item A\n\nItem B"` | `"Item A\r\nItem A\r\nItem B\r\n\r\nItem B"` | = 5.6 antes | = 5.6 antes |
| só LF | `"Linha 1\nLinha 2"` | `"Linha 1\nLinha 2\nLinha 1"` | = 5.6 antes | = 5.6 antes |
| CR sozinho | `"Linha 1\nLinha 2"` | `"Linha 1\rLinha 2"` | = 5.6 antes | = 5.6 antes |

Antes: o 8.5 diverge em 4 dos 6 casos (não separa, não remove as linhas repetidas). O `MultiCell` do FPDF apaga
`\r`, mas as linhas repetidas e a contagem de linhas continuam diferentes no PDF. Depois: os quatro lados são iguais
ao 5.6 de antes em todos os casos. O comportamento estranho do 5.6 (linha em branco depois de cada CRLF e linhas
repetidas removidas pelo `array_unique`) é preservado de propósito.

```bash
# dois containers (PHP 5.6 e 8.5) montando ecidade/ em /var/www/html
cp scratchpad/split_mod_imprime11.php ecidade/tmp/
docker exec <container_56> php /var/www/html/tmp/split_mod_imprime11.php /var/www/html/vendor/autoload.php
docker exec <container_85> php /var/www/html/tmp/split_mod_imprime11.php /var/www/html/vendor/autoload.php
```

## Verificação

- `php -l` de `fpdf151/impmodelos/mod_imprime11.php` limpo no 5.6 e no 8.5.
- Encoding preservado: o arquivo continua ISO-8859-1, editado em bytes; o diff é uma linha.
- Não há cópia do arquivo em `extension/modification/`.
- Suíte (`ecidade/tests/suite/rodar.sh`): 5.6 286/286 e 8.5 87/87.

## Lacunas

- A emissão do PDF da Solicitação de Compra não foi comparada 5.6 × 8.5: a base de exemplo não tem solicitação
  (`solicita` vazia) e criar uma seria gravar no banco.
- As outras 40 chamadas de `split()` com regex no código ficam como estão: todas em telas servidas hoje pelo 5.6.
