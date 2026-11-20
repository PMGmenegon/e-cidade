# Área Tributário — migração do PHP 7.4 (PR #8) para o 8.5

Branch `tributario/8.5`, criada da `migracao/parse-str-e-guardas-sql` (que já traz o `parse_str` de 1 argumento
convertido em todas as áreas e as guardas `pg_*` dos wrappers do núcleo). Referência: PHP 7.4 do PR, porta 8080.
O histórico da migração anterior, feita sobre o código antigo, continua em `area-tributario.md`.

## 1. Escopo

Os 14 prefixos que o menu do sistema põe na área Tributário e que não são de outra área:
`cad`, `iss`, `fis`, `arr`, `div`, `itb`/`itbi`, `cem`, `jur`, `mar`, `not`, `dvr`, `tri`, `inf`, `agu`/`agua`.
Telas avulsas de `cai`, `pro`, `con`, `pre`, `prot`, `amb`, `rec` e `sys` que também aparecem no menu do
Tributário ficam com as áreas donas desses prefixos.

**Posse dos arquivos fora dos prefixos** (classes, formulários, models), para mexer só no que é da área:
- classes de dados: pelas tabelas dos módulos do dicionário (`db_sysarqmod`) `agua`, `arrecadacao`, `cadastro`,
  `cemiterio`, `diversos`, `divida`, `fiscal`, `inflatores`, `issqn`, `itbi`, `juridico`, `marcas`,
  `notificacoes` e `tributario`, descartando tabela que também esteja em módulo de outra área — o mesmo critério
  usado no Financeiro;
- demais arquivos: só os citados exclusivamente por telas dos 14 prefixos (janelas `func_*` e arquivos sem prefixo
  de módulo, como `reciboitbi*.php`, contam como neutros);
- ficam de fora as 35 classes já concluídas pelo Financeiro (`arre*`, `tabrec*`, `notificacao`), que o
  Tributário também usa.

## 2. Linha de base (19/11/2026)

`php -l` nos 2.807 arquivos dos prefixos: 1 não compila (`fis1_fis_vistorias003.php`), **igual no 7.4** —
defeito pré-existente, não é migração.

Bateria GET 7.4 × 8.5 (`scratchpad/cmp.py`, sessão autenticada), 2.805 telas: **2.234 idênticas, 571 divergentes**.

| Prefixo | Telas | Divergentes | | Prefixo | Telas | Divergentes |
|---|---|---|---|---|---|---|
| `cem` | 117 | 8 | | `div` | 148 | 38 |
| `itb`/`itbi` | 123 | 34 | | `arr` | 166 | 47 |
| `mar` | 35 | 4 | | `agu`/`agua` | 224 | 51 |
| `not` | 14 | 4 | | `iss` | 400 | 93 |
| `tri` | 35 | 9 | | `fis` | 792 | 106 |
| `inf` | 30 | 7 | | `cad` | 540 | 123 |
| `dvr` | 33 | 14 | | `jur` | 148 | 33 |

Causa da primeira quebra de cada divergente, lida no `extension/log/error.log` ao abrir a tela no 8.5:

| Causa | Telas | Onde |
|---|---|---|
| `ParseError` — offset de string com chaves (`$s{i}`, removido no 8.0) | **248** | `fpdf151/fpdf.php:614` (núcleo): todo relatório em PDF |
| o mesmo | **130** | `libs/JSON.php:188` (núcleo): todo RPC que usa o JSON antigo |
| `Call to a member function label() on null` — construtor estilo PHP 4 que não roda no 8 | ~70 | classes da área |
| `pg_*(): ... false given` — consulta que falhou | ~40 | telas e formulários da área |
| avulsas: assinatura incompatível com a mãe, `reset(null)`, `sizeof(null)`, `array_key_exists` em objeto, `DBLargeObject` | ~20 | área e núcleo |
| sem erro fatal (diferença de saída) | 23 | caso a caso |

**378 das 571 divergências (66%) dependem só de dois arquivos do núcleo**, que não são desta frente.

## 3. Lotes

Do menor para o maior, um por vez:

| Lote | Prefixos | Telas | Divergentes na linha de base |
|---|---|---|---|
| 1 | `cem`, `itb`/`itbi`, `mar`, `not`, `tri`, `inf`, `dvr` | 387 | 80 |
| 2 | `jur`, `div`, `arr` | 462 | 118 |
| 3 | `agu`/`agua` | 224 | 51 |
| 4 | `iss` | 400 | 93 |
| 5 | `fis` | 792 | 106 |
| 6 | `cad` | 540 | 123 |

## 4. Lote 1 — `cem`, `itb`/`itbi`, `mar`, `not`, `tri`, `inf`, `dvr` (20/11/2026)

| Commit | O quê | Prova |
|---|---|---|
| construtores (manual) | `__construct` em 15 classes: `cl_diverimporta`, `cl_isencao`, `cl_isencaotipo`, `cl_isscalc`, `cl_itbialt`, `cl_itbiconstr`, `cl_itbidadosimovel`, `cl_itbinome`, `cl_itbinomecgm`, `cl_itbiruralcaract`, `cl_itburbano`, `cl_itenserv`, `cl_parissqn`, `cl_parreciboitbi`, `cl_setorloc`. Só a linha da declaração; nenhuma filha nem chamada ao nome antigo na base | estado inicial das 15 (instanciação): antes 7.4 ≠ 8.5; depois 8.5 = 7.4 e 7.4 = 7.4 |
| `0 == ""` (Rector, automático) | regra do grupo `GuardaComparacaoLiteralRector`, sozinha, PHP 8.0 fixado, em 104 classes (tabelas dos módulos do lote 1); 559 linhas, só inserção | caminho de escrita (`atualizacampos` com POST): antes 104 classes ≠; depois 1 |
| construtor de `cl_diversos` (manual) | a 1 que restou; tabela do módulo Diversos, usada também pelo Caixa, não tocada pelo Financeiro | escrita: 104/104 iguais; 7.4 = 7.4 |
| `pg_*` (script, automático) | `($rs ? pg_x($rs) : null)` em `itb2_relresumoitbi002`, `itb4_consultacancelamento001`, `tri4_carregadadosisencao` (decisão 2a) | resposta do 7.4 igual antes/depois; 3/3 idênticas |

`php -l` nos dois runtimes em todo arquivo alterado: 0 erros. Nenhum byte ISO-8859-1 alterado.

**Resultado:** bateria do lote **307/387 → 346/387** idênticas. As **41** que divergem dependem só do núcleo:
- 40: `fpdf151/fpdf.php` e `libs/JSON.php` (offset com chaves);
- 1: `cem2_emitecertisen002.php` — os dois runtimes terminam em "Falha ao gerar relatório", mas o 7.4 imprime
  antes `<b>Mensagem: </b><br>`: a mensagem vem de `dbagata/classes/util/Dialog.class`, cujo construtor
  `Dialog()` é estilo PHP 4 e não roda no 8.5. O `dbagata/` tem 128 classes com construtor estilo PHP 4.

## 5. Pendências do núcleo (avisar o dono)

| Arquivo | Defeito no 8.5 | Telas do Tributário afetadas |
|---|---|---|
| `fpdf151/fpdf.php:614` | `ParseError`: offset de string com chaves | 248 (todos os relatórios em PDF) |
| `libs/JSON.php:188` | o mesmo | 130 (RPCs) |
| `dbagata/` (128 classes) | construtor estilo PHP 4 não roda | relatórios do Agata (1 no lote 1) |
| `classes/db_db_logsacessa_classe.php` | construtor estilo PHP 4 | usada pela Configuração e por webservices |
| `abrir.php:372` | `db_verifica_ip_banco()` chamada sem o argumento que o PR passou a exigir; quebra **igual no 7.4** (depois de gravar a sessão) | login direto pelo `abrir.php` |

## 6. Ambiente

- O login pelo formulário confere `sha1(md5(senha))`; o dump desta base já vem assim. O `update` do
  `CONTRIBUINDO.md` (`sha1('dbseller')`) quebra esse login: não rodar nesta base.
- `passport:install` falha no `install.sh` porque o banco não tem as migrations do PR (lacuna já registrada para o
  ambiente 7.4). Não impede as telas.
- Máquina Windows: o repositório tem de ficar no sistema de arquivos do Linux (WSL), por causa dos arquivos que só
  diferem em maiúsculas — vários são do Tributário (`cem1_legista00*`, model `Tabrec`, rota de arrecadação, model
  de ISSQN, manual do ITBI).
