# Área Recursos Humanos na base-php74 — dimensionamento da migração para o PHP 8.5

> Branch: `pessoal/rh-php85` (a partir da `base-php74`). Data do dimensionamento: 18/11/2026.
> Guia: `base-php84`. Referência funcional: PHP 7.4. **Nenhum código foi alterado nesta fase** — só medição.
> Escopo: prefixos `rh`, `eso`, `rec`, `pes` (`[0-9]*_`) e `src/RecursosHumanos`. O registro da migração anterior
> (sobre o 5.6) continua em `area-recursos-humanos.md`.

## Decisões do usuário (18/11/2026) — valem para toda a área

1. **c2:** critério = **manter a 74 e acrescentar só o que o 8.5 exigir**, usando a 84 como referência de *como* corrigir.
   `pes1_reajusteprog001.php` **não se altera**: não compila em PHP algum, é defeito pré-existente da DBSeller — fica
   **caracterizado e para reportar** (ver *Defeitos caracterizados*).
2. **c1:** a regra "manter a 74 (`explode`)" vale **só para separador literal**. Separador com metacaractere de regex
   (`+ * ? [ ] ( ) | . ^ $ \`) fica com `preg_split`, como manda a skill. Os 51 foram conferidos um a um (ver *c1*).
3. **`src/RecursosHumanos`:** aprovado como **lote 1B**, logo depois de rh+eso.
4. **`esocial_externo.RPC.php` e `rhpessoalmov001.RPC.php`:** entram no lote rh+eso.
5. **Pedidos ao núcleo:** a divisão de quem porta o quê (RH × núcleo × DAOs) **ainda será decidida com o coordenador**; as
   contagens abaixo servem a essa conversa.

## Método

Três vias, com a base comum `e640eb485` (merge-base das duas branches = `master`):

- **mudança da DBSeller** = `diff(e640eb485, base-php74)`; **mudança da migração** = `diff(e640eb485, base-php84)`;
- por arquivo: só uma das duas → classificação direta; as duas → `git merge-file` (limpo ou com conflito);
- cada conflito foi conferido de novo **normalizando espaço no fim da linha e `<?` → `<?php`** (a DBSeller reformatou os
  arquivos): só 2 de 81 eram formatação; os outros 79 são conflitos reais;
- `php -l` no 8.5 (imagem `e-cidade-ecidade_php85`, PHP 8.5.12, `docker run --rm` com `./ecidade` somente leitura, sem banco);
- universo fora da área por `scratchpad/enumera.py` (nove frentes) nos quatro prefixos, sobre a base-php74.

Universo da área: **2.129 arquivos** (`(rh|eso|rec|pes)[0-9]*_*` + `src/RecursosHumanos`; este tem 585). Das alterações
na área, a **DBSeller mexeu em 1.343** arquivos (34 novos), a **migração anterior em 517**; **476 foram tocados pelos dois**;
745 arquivos não foram tocados por nenhum.

## Classes usadas

| Classe | Significado | Ação |
|---|---|---|
| **a1** | só a base-php84 mudou (a 74 não tem) | trazer a versão da 84 |
| **a2** | os dois mudaram, `merge-file` **limpo** | aplicar a mudança da 84 por 3 vias, mantendo a da DBSeller |
| **b** | só a base-php74 mudou (funcionalidade DBSeller; inclui 34 arquivos novos) | **preservar**; ainda passa pelo Rector e `php -l` do lote |
| **c1** | conflito só de `split()` **literal**: a 74 já converteu para `explode()`, a 84 usou `preg_split("#,#m")` | manter a da 74; aplicar o resto da 84 |
| **c2** | conflito real, ou fora da regra do c1 | manter a 74 e acrescentar só o que o 8.5 exigir (decisão 1) |

## Tabela por prefixo

| Grupo | Arquivos | a1 | a2 | b | c1 | c2 | Sem mudança |
|---|---:|---:|---:|---:|---:|---:|---:|
| rh + eso | 94 | 0 | 0 | 31 | 0 | 0 | 63 |
| rec | 283 | 13 | 50 | 121 | 6 | 7 | 86 |
| pes3 + pes4 | 273 | 6 | 35 | 151 | 4 | 5 | 72 |
| pes1 | 370 | 11 | 129 | 159 | 9 | 5 | 57 |
| pes2 | 524 | 10 | 183 | 269 | 29 | 13 | 20 |
| src/RecursosHumanos | 585 | 1 | 0 | 136 | 0 | 1 | 447 |
| **Total** | **2.129** | **41** | **397** | **867** | **48** | **31** | **745** |

`pes1_reajusteprog001.php` está contado em *b* (a DBSeller o alterou), mas não compila: *Defeitos caracterizados*. c1 e c2 já
reúnem a reclassificação de 18/11/2026 (3 arquivos de c1 para c2).

Achados que mudam o plano:

1. **A DBSeller já fez parte da migração para o 7.x** (`split()` → `explode()`). Por isso 120 trechos em conflito são "os dois
   converteram"; o trabalho real é menor que o diff da 84 sugere.
2. **`rh` e `eso` não tiveram nenhuma mudança na migração anterior**: o lote 1 é validar (`php -l` ok) e passar o Rector
   sobre os 31 arquivos *b*.
3. **Os 867 arquivos *b* nunca passaram pelo Rector.** Preservar a funcionalidade não dispensa o porte: eles têm de ser varridos
   pelas categorias do 8.5 (`$this->X == literal`, `parse_str` de 1 argumento, `each`, construtor PHP 4…). O inventário do
   `enumera.py` sobre a 74, no universo do `pes`, dá 4.279 arquivos e 1.497 a alterar (6.931 ocorrências de `$this->X == literal`,
   421 de `parse_str`, 111 de `split(`, 24 de `each(`, 22 construtores PHP 4, 1 `{}` em string). O número inclui o fecho em
   `classes/`/`libs/`, **fora da área** (ver *Pedidos ao núcleo*). Para os outros prefixos: `rh` 2.402 arquivos/856 a alterar,
   `eso` 2.647/877, `rec` 2.921/1.000.
4. A DBSeller mudou o **modo** de arquivos (755 → 644) e reformatou (`<?` → `<?php`, espaço no fim da linha): diffs de 3 vias têm
   ruído; conferir com `git diff --ignore-cr-at-eol -w`. O código segue em ISO-8859-1.

## php -l no 8.5 (base-php74)

2.126 arquivos `.php` da área verificados; **2 não compilam**:

| Arquivo | Erro | Classe | Observação |
|---|---|---|---|
| `src/RecursosHumanos/RH/PontoEletronico/Calculo/Horas/Falta.php` | l. 143: *Unparenthesized `a ? b : c ? d : e` is not supported* | a1 | a 84 já corrige (parênteses à esquerda, associação do 5.6) e compila no 8.5 |
| `pes1_reajusteprog001.php` | l. 132: *Unmatched '}'* | c2 | **defeito introduzido pela DBSeller**: a base antiga e a 84 têm o arquivo sem a edição; o bloco novo do eSocial deixou chaves desbalanceadas. Não compila em versão alguma do PHP |

`php -l` não pega fatal de **carga** (LSP) nem *TypeError* de execução: o passo `carrega_arquivo.php` nos arquivos de `src/` com
`extends`/`implements` continua necessário no lote.

## Lista (c) — precisa de decisão

### c2 — 31 conflitos que exigem leitura (28 reais + 3 vindos de c1) — critério: manter a 74, acrescentar só o que o 8.5 exigir

`pes1_relac002.php`, `pes1_rhcontasrec003.php`, `pes1_rhteutri002.php`, `pes1_rhteutri003.php`, `pes2_admitidos002.php`, `pes2_analitica002.php`, `pes2_bb240cnabgeracao002.php`, `pes2_func_e_depend002.php`, `pes2_pensalim002.php`, `pes2_relcad001.php`, `pes2_relfichafinanceira002.php`, `pes2_relfichafinanceiratxt002.php`, `pes2_resumorecursoempenhos002.php`, `pes2_rhteutri002.php`, `pes2_sapestagioprob002.php`, `pes2_termorescisao002.php`, `pes2_valetransp_anual002.php`, `pes3_consponto001.php`, `pes3_conspontoregistro002.php`, `pes3_gerfinanc001.php`, `pes3_gerfinanc018.php`, `pes4_rhfopag91002.php`, `rec1_protelac002.php`, `rec1_protelac003.php`, `rec2_certcomprobatorio002.php`, `rec2_relassentaporperiodo002.php`, `rec2_vantagens002.php`, `src/RecursosHumanos/ESocial/Integracao/Formatter/AlteracaoDadosServidorFormatter.php`, **mais os 3 vindos de c1:** `pes1_importainfla001.php`, `rec1_leis001.php`, `rec1_leis002.php`.

Conflito real = a 84 e a 74 alteraram as mesmas linhas de forma **diferente**. Nos 79 arquivos em conflito havia 43 trechos que não são
`split` nem guarda `0==""` e 7 de guarda `0==""`. **Decisão (item 1):** mantém-se a 74 e acrescenta-se só o que o 8.5 exigir, usando a 84
como referência de *como* corrigir. Cada arquivo ainda precisa ser lido no lote; não há resolução automática.

### c1 — 48 conflitos só de `split` com separador literal (resolução aprovada: manter a 74, `explode`)

`pes1_pontoRfx0011.php`, `pes1_pontoRfx0011_iframe.php`, `pes1_rhbases004.php`, `pes1_rhcadcalend002.php`, `pes1_rhempexcluirsol001.php`, `pes1_rhrubricas004.php`, `pes1_rhrubricas005.php`, `pes1_virafolha001.php`, `pes1_virafolha003.php`, `pes2_acountcadastro001.php`, `pes2_acountponto001.php`, `pes2_aleemitearqbanco002.php`, `pes2_bagemitearqbanco002.php`, `pes2_banrisul240cnab002.php`, `pes2_banrisul240cnabgeracao002.php`, `pes2_bb240cnab002.php`, `pes2_caremitearqbanco002.php`, `pes2_cef240cnabgeracao002.php`, `pes2_daeemitearqbanco002.php`, `pes2_emitearquivobancario_banrisul002.php`, `pes2_gerabbrasil001.php`, `pes2_guaemitearqbanco002.php`, `pes2_guaemitebb200lay002.php`, `pes2_impactoorc001.php`, `pes2_itaemitearqbanco002.php`, `pes2_itau240cnab002.php`, `pes2_itau240cnabgeracao002.php`, `pes2_liquido001.php`, `pes2_osoemitearqbanco002.php`, `pes2_osoemitebb200lay002.php`, `pes2_relfuncaolotacaoorgao001.php`, `pes2_relrub002.php`, `pes2_retconsig002.php`, `pes2_retconsigfolha002.php`, `pes2_sapconfcaixa002.php`, `pes2_sapemitebb200lay002.php`, `pes2_sapretconsig002.php`, `pes2_valetransp_anual001.php`, `pes4_cadferia004.php`, `pes4_contratosemergenciais.RPC.php`, `pes4_implantaferias001.php`, `pes4_rhpesrescis004.php`, `rec1_assentamdia002.php`, `rec1_assentamdia003.php`, `rec1_portlotecolexc003.php`, `rec2_gradeefetividade002.php`, `rec2_tabcurritipo001.php`, `rec4_bancohoras.RPC.php`.

**Conferência um a um (feita em 18/11/2026):** nos 51 arquivos há 107 trechos em conflito com `split(` no lado da base (a conferência leu o lado da base de cada trecho). Separadores:
110 chamadas, **todas literais** (72 × `-`, 33 × `,`, 4 × `/`, 1 × `_`), onde `explode` equivale. Fogem da regra **3 arquivos** (113 chamadas ao todo), que
passaram para c2:

| Arquivo | Separador | O que fez a 74 | O que fez a 84 | Proposta |
|---|---|---|---|---|
| `rec1_leis001.php` (l. 40) | `"\|"` (regex: pipe escapado) | `explode("|", …)` | `preg_split("#\\|#m", …)` | pela regra, **preg_split** (84). O `explode("|")` da 74 é equivalente (pipe escapado = pipe literal), então pode-se manter a 74 se o usuário preferir |
| `rec1_leis002.php` (l. 42) | `"\|"` | idem | idem | idem |
| `pes1_importainfla001.php` (l. 67) | **variável** `$separador` | `explode($separador, …)` | `preg_split` com guarda que devolve `false` para separadores com `\|` | não dá para provar literal; manter a 84 (guarda) até ver a origem de `$separador` |

Observação: `pes1_pontoRfx0011_iframe.php` ainda tem 4 chamadas `split(` **não convertidas** na 74 (fora do trecho em conflito); são trabalho do Rector no lote.

### Outras decisões (resolvidas em 18/11/2026)

- `src/RecursosHumanos` → **lote 1B**, após rh+eso (aprovado).
- `esocial_externo.RPC.php` e `rhpessoalmov001.RPC.php` → **lote rh+eso** (aprovado; a DBSeller alterou os dois, a 84 não: classe *b*).
- `pes2_sapguiapatronal002.sal` e `pes4_gerafolha004_modificado.php.dist` (não-PHP) ficam de fora.

### Defeitos caracterizados (não se corrigem; reportar à DBSeller)

- `pes1_reajusteprog001.php`: `Unmatched '}'` na linha 132 — bloco novo do eSocial deixou chaves desbalanceadas. A base antiga e a 84
  têm o arquivo sem a edição. **Não compila em PHP algum**; pré-existente da DBSeller. **Não se altera** (decisão do usuário). A tela
  fica fora da bateria até a DBSeller corrigir; reportar.

## Lotes propostos (um por vez; commit local por lote)

| Lote | Escopo | Arquivos | Trazer (a1+a2) | Decidir (c1+c2) | Preservar (b) |
|---|---|---:|---:|---:|---:|
| 1 | `rh` + `eso` + 2 `.RPC.php` (aprovado) | 96 | 0 | 0 | 33 |
| 1B | `src/RecursosHumanos` (aprovado) | 585 | 1 | 1 | 136 |
| 2 | `rec` (rec1–rec4) | 283 | 63 | 13 | 121 |
| 3 | `pes3` + `pes4` | 273 | 41 | 9 | 151 |
| 4 | `pes1` | 370 | 140 | 14 | 159 |
| 5 | `pes2` | 524 | 193 | 42 | 269 |

Cada lote: enumerar (`enumera.py <prefixo>`) → `php -l` no 7.4 e no 8.5 sobre o **universo** → Rector (pin de versão, repetir até
zero) → `carrega_arquivo.php` nos de `src/` → bateria do lote. **Bloqueio de ambiente:** a bateria por proxy (7.4 × 8.5, `cmp.py`)
só roda com o ambiente do 7.4 de pé (o build falha hoje com 503 no Launchpad; Fase 1 pendente). Até lá, cada lote termina em
`php -l` + revisão do diff.

## PEDIDOS AO NÚCLEO

Arquivos **fora da área** que a migração anterior alterou, que o RH alcança (universo do `enumera.py` nos quatro prefixos: 4.979
arquivos, 2.929 fora da área) e que a base-php74 **ainda não tem corrigidos**. Dos 1.218 que a 84 alterou, a 74 já tem o
equivalente em 2. São pedidos ao dono do núcleo (CONTRIBUINDO, regra 5); nenhum foi alterado aqui.

### P1 — a 74 não tem nenhuma das correções (141: só a 84 mudou)

- `libs/db_app.utils.php` (`DB_VERSION` indefinida);
- `model/pessoal/std/DBPessoal.model.php` (`$F032 - $F031` com string vazia; cálculo da folha);
- `model/pessoal/folhapagamento/FolhaPagamento.model.php`, `FolhaPagamentoSalario.model.php`, `FolhaPagamentoSuplementar.model.php`,
  `model/pessoal/PontoFerias.model.php`, `model/linhaRelatorioContabil.model.php`;
- raiz: `corpo.php` e 12 `func_*.php`: `corpo.php`, `func_avaliacaogruporespostacat.php`, `func_avaliacaogruporespostamonitoramentosaude.php`, `func_avaliacaogruporespostaobras.php`, `func_avaliacaogruporespostaprocesso.php`, `func_desligamentoservidor.php`, `func_desligamentotrabalhadorsemvinculo.php`, `func_fonterecurso.php`, `func_orctiporec.php`, `func_rhdepend.php`, `func_rhlotacaotributaria.php`, `func_rhpessoaladmiss.php`, `func_rhrubricas.php`;
- 121 DAOs `classes/db_*_classe.php`.

### P2 — mudança da DBSeller e da 84 convivem: 3 vias limpa (71)

29 fora de `classes/db_*_classe`: `emp2_emitenotaemp002.php`, `forms/db_frmimplantacaoponto.php`, `forms/db_frmrhempemitesolfolha.php`, `forms/db_frmrhempexcluirsol.php`, `forms/db_frmrhempgerasolfolha.php`, `forms/db_frmrhpesdoc.php`, `fpdf151/fpdf.php`, `fpdf151/impcarne.php`, `fpdf151/pdf.php`, `func_bases.php`, `func_cgmjuridico.php`, `func_db_bancos.php`, `func_db_layouttxt.php`, `func_db_usuarios.php`, `func_grupomotivoafastamentoesocial.php`, `func_nome.php`, `func_operadorasaude.php`, `func_orcorgao.php`, `func_rhcargo.php`, `func_rhemissaochequeitem.php`, `func_rhlocaltrab.php`, `func_rhlota.php`, `func_rhlotaestrutinstit.php`, `func_rubricas.php`, `func_selecao.php`, `func_tipoasse.php`, `model/manad.model.php`, `src/Financeiro/Contabilidade/MatrizSaldoContabil/Repository/Lancamento.php`, `std/DBDate.php`; mais 42 DAOs.
Os de maior risco para a folha: `fpdf151/fpdf.php` e `fpdf151/pdf.php` (`Cell()`, `$align=='R'`), `std/DBDate.php`.

### P3 — conflito de 3 vias (1.004: 29 não-DAO + 975 DAOs)

Não-DAO: `buscaBasesClientes.RPC.php`, `classes/empenho.php`, `classes/estagioAvaliacoes.classe.php`, `dbforms/db_classesgenericas.php`, `dbforms/db_funcoes.php`, `dbforms/db_geraformulario.php`, `dbforms/db_layouttxt.php`, `forms/db_frmaturubricas.php`, `forms/db_frmpensao.php`, `forms/db_frmtipoasse.php`, `fpdf151/pdf1.php`, `fpdf151/pdf2.php`, `func_rhfuncao.php`, `libs/db_libcontabilidade.php`, `libs/db_liborcamento.php`, `libs/db_libparagrafo.php`, `libs/db_libparagrafoCodPhp.php`, `libs/db_libParagrafoTabela.php`, `libs/db_libparagrafoText.php`, `libs/db_libpessoal.php`, `libs/db_libpostgres.php`, `libs/db_libsys.php`, `libs/db_stdlib.php`, `libs/db_stdlibwebseller.php`, `libs/db_utils.php`, `libs/JSON.php`, `model/dbGeradorRelatorio.model.php`, `model/pontoFolha.model.php`, `std/DBString.php`.

Destaque: **`libs/db_libpessoal.php`**. A 84 mudou 9 linhas (`each()` em dois laços → `key/current/next`; `split` → `explode`;
**`db_val()`: `try { return $string+0; } catch (TypeError)` devolve 0**, ponto da folha). A 74 reformatou o arquivo inteiro
(+1.713/−1.681 linhas), então o merge conflita; os trechos precisam ser reaplicados à mão. Idem `libs/db_stdlib.php`
(84: +47/−36; 74: +1.083/−996) e `libs/db_utils.php`. Nos não-DAO **não** repeti a normalização de espaço.

#### Recontagem dos 975 DAOs ignorando espaço, quebra de linha e equivalências triviais

Normalização aplicada aos três lados (base, 74, 84) antes do `git merge-file`, em três níveis cumulativos:

| Nível | Normalização | DAOs sem conflito | Conflito restante |
|---|---|---:|---:|
| 0 | nenhuma (`merge-file` cru) | 0 | 975 |
| 1 | só espaço no fim da linha, CRLF e `<?` → `<?php` | 10 | 965 |
| 2 | + todo espaço dentro/ao redor das linhas (≈ `git diff -w`) | 14 | 961 |
| 3 | + equivalências do 7.x: `public`/`private` antes de `function` (a 74 já escreveu `public function __construct()`), `preg_split("#X#m")` ≡ `explode("X")` para `X` literal | **890** | **85** |

**Sobram 85 DAOs com conflito de verdade (8,7%).** A causa dos 961 que o nível 2 não resolvia era a migração em duplicidade:
a DBSeller já renomeou o construtor (`function cl_x()` → `public function __construct()`) e converteu `split("#")` em `explode("#")`,
e a 84 fez o mesmo de outro jeito (`function __construct()`, `preg_split("#\\##m")`). Os 85 restantes misturam: (i) trechos com
`explode` de aspas simples × duplas e chaves em linhas diferentes (cosméticos, ainda não absorvidos pela normalização),
(ii) trechos de guarda `$this->X == ""` em que a DBSeller editou a mesma linha (aparecem na amostra, não recontei após o nível 3), e (iii) **mudança real da DBSeller** na `sql_query`
de alguns DAOs (vista nas amostras) (`order by {$ordem}` em vez do laço sobre `explode("#")` da base) — esta *não* é migração e deve ser preservada.
Ressalva: a normalização é heurística; "sem conflito" significa que o merge se aplica sem sobreposição, não que o resultado foi executado.

#### P1 + P3 separados por quem usa

Critério (heurístico, por nome da tabela): **RH** = `rh*`, `pes*`, `gerf*`, `ponto*`, `eso*`, `cfpess`, `assenta*`, `tipoasse*`, `afasta*`,
`inssirf`, `bases*`, `selecao*`, `cadferia`, `pensao*`, `previden*`, `relrub`, `rubricas*`, `vtf*`, `rescisao`, `portaria` e afins.
**Compartilhado-referenciado** = DAO que não é do RH mas que alguma tela/classe da área instancia direto (`cl_x` ou `getDao('x')`, 480
nomes referenciados nos 2.126 `.php` da área). **Compartilhado** = só entra pelo fecho do `enumera.py`. Não é o dono da tabela no banco:
é a decisão a levar ao coordenador. `rec*` não entrou como critério: os 8 DAOs `rec*` do universo são `rechumano*` (Educação) e `recibo*` (arrecadação).

| Grupo | Total | DAOs do RH | Compartilhados referenciados pela área | Compartilhados (só fecho) |
|---|---:|---:|---:|---:|
| P1 (só a 84 mudou) | 121 | 50 | 18 | 53 |
| P3 (conflito cru) | 975 | 221 | 101 | 653 |
| P3 — os 85 **conflitos reais** (nível 3) | 85 | 14 | 11 | 60 |
| **P1 + P3 (conflito cru)** | **1.096** | **271** | **119** | **706** |
| **P1 + os 85 reais** | **206** | **64** | **29** | **113** |

- DAOs do RH com conflito real (14): `pensaocontabancaria`, `pensaoretencao`, `portaria`, `rescisao`, `rhcontasrec`, `rhdirfgeracao`,
  `rhempenhofolhaempenho`, `rhpesdoc`, `rhpessoal`, `rhrubricasadiantamento`, `rhslipfolha`, `rhteutri`, `selecao`, `servidoroperadorasaudedependente`.
- Compartilhados referenciados pela área com conflito real (11): `admissao`, `assinatura`, `cgm`, `operadorasaude`, `orcdotacao`,
  `orcprojativ`, `orctiporec`, `orcunidade`, `protelac`, `protprocesso`, `relac`.
- DAOs do RH em P1 (50, só a 84 mudou): `afastaassenta`, `assenta`, `assentadb_cadattdinamicovalorgrupo`, `assentamentorra`,
  `assentamentosencerramentoefetividade`, `assentamentosubstituicao`, `folhafiltros`, `inssirf`, `rhcedencia`, `rhcontratoemergencialrenovacao`,
  `rhemitecontracheque`, `rhferiasassenta`, `rhferiasperiodoassentamento`, `rhfuncaooutrosdados`, `rhlocaltrabequipamentoprotecao`,
  `rhlocaltrabequipamentoprotecaoepi`, `rhlocaltrabregistroambiental`, `rhlotacaotributaria`, `rhlotavincrubrica`, `rhpescargo`, `rhpespadrao`,
  os 25 `rhpessoalprocesso*`/`rhprocesso*`, `rhreajusteparidade`, `rhsindicato`, `rubricasusuario`, `tipoasseexterno`.
- Compartilhados de P1 referenciados pela área (18): `avaliacaogruporesposta*` (8), `contribuicaosindical*` (2), `controleafastamento`,
  `db_cadattdinamicoatributosvalor`, `db_uf`, `db_usuarios`, `pcparam`, `siopequalificacao`, `siopesegmentoatuacao`, `siopesituacao`.

#### Arquivos de `model/pessoal/`

O universo do RH tem 48 arquivos em `model/pessoal/`; a 84 alterou 6:

| Arquivo | Situação | Pedido |
|---|---|---|
| `model/pessoal/std/DBPessoal.model.php` | **P1**: a 74 não tem a correção (`$F032 - $F031` com string vazia; cálculo da folha) | trazer a da 84 |
| `model/pessoal/folhapagamento/FolhaPagamento.model.php` | **P1** | trazer a da 84 |
| `model/pessoal/folhapagamento/FolhaPagamentoSalario.model.php` | **P1** | trazer a da 84 |
| `model/pessoal/folhapagamento/FolhaPagamentoSuplementar.model.php` | **P1** | trazer a da 84 |
| `model/pessoal/PontoFerias.model.php` | **P1** | trazer a da 84 |
| `model/pessoal/ReajustePadroes.php` | **P4**: a 74 já é equivalente | nada |

Nenhum de `model/pessoal/` está em P2 (limpo) nem P3 (conflito): são os 5 de aplicação direta. Também em `model/` e relevante à folha,
mas **fora** de `model/pessoal/`: `model/pontoFolha.model.php` (P3, conflito) e `model/manad.model.php` (P2, limpo).

### P4 — já equivalente na 74 (nada a pedir)

`libs/db_libgertxtfolha.php`, `model/pessoal/ReajustePadroes.php`.

### Observações

- `libs/db_calcula.php` foi alterado pelos dois, mas **não** está no universo do RH.
- Sem P1–P3, a bateria do lote mede o núcleo, não a tela. Sugestão: o núcleo trata P1 e os 29 não-DAO de P2/P3 antes do lote 2;
  os DAOs (42 limpos + 975, dos quais só 85 têm conflito real) são o maior volume: ver a divisão RH × compartilhado em P3.

## PROGRESSO

| Lote | Escopo | Estado | Commit | Observações |
|---|---|---|---|---|
| 0 | Dimensionamento, decisões (c), conferência do c1, recontagem dos DAOs | **feito** (18/11/2026) | este commit | só documentação |
| 1 | `rh` + `eso` + 2 `.RPC.php` | pendente | — | — |
| 1B | `src/RecursosHumanos` (aprovado) | pendente | — | `Falta.php` não compila (a1) |
| 2 | `rec` | pendente | — | — |
| 3 | `pes3` + `pes4` | pendente | — | — |
| 4 | `pes1` | pendente | — | `pes1_reajusteprog001.php` não compila: caracterizado, não se altera, reportar |
| 5 | `pes2` | pendente | — | — |
| Pedidos ao núcleo (P1–P3) | fora da área | pendente | — | aguardam o dono do núcleo |
| Bateria completa (7.4 × 8.5) | área toda | pendente | — | ambiente do 7.4 ainda não está de pé |
