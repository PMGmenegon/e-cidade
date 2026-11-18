# Ferramentas da migração (`scratchpad/`)

Scripts e harnesses usados para migrar o e-cidade do PHP 5.6 para o 8.5, na ordem em que entram no trabalho de um lote.
O **como usar** de cada passo está no guia (`docs/migrar-um-modulo.md`); aqui está **o que cada arquivo faz, como faz e
o que ele altera**. Cada arquivo também traz, no topo, um cabeçalho com uso, entradas e saídas.

Todos rodam **da raiz do repositório**. Os `.php` são *harnesses*: são copiados para dentro dos containers e rodados nos
**dois** runtimes (5.6 e 8.5), e o que se compara é a saída de um com a do outro.

A coluna **Altera** diz o que o script muda além de gravar em `ecidade/tmp/`: **nada** (só lê e mede), **código**
(arquivos de `ecidade/`), **banco** (grava e restaura), **proxy** (`nginx.conf`, `faseb_map.conf`) ou **sessão** (o arquivo de
sessão de login usado nos testes).

## Comandos de um passo inteiro

| Arquivo | O que faz | Como faz | Passo | Altera |
| --- | --- | --- | --- | --- |
| `rector_lote.py` | o passo 4 em um comando | junta os alvos, copia a config e as regras para o container, confere a sintaxe da config, simula (`--dry-run`) e classifica cada regra (conhecida, ressalva, nova); com `--aplicar`, aplica e repete até uma rodada alterar 0 arquivos, e recusa se houver regra nova | 4 | código (só com `--aplicar`) |
| `verifica_lote.py` | os passos 4b, 5, 5b, 6, 6b, 6c e 7 de uma vez, com relatório único | roda cada harness nos dois containers sobre a mesma lista, compara, conta entradas e saídas, filtra os artefatos conhecidos e diagnostica cada tela divergente; `--tudo` faz a bateria completa do fim da área | 4b–7 | nada |
| `nivel3.py` | o nível 3 (POST real) em um comando | `--candidatas` lista as telas de inclusão pelo critério do guia; o teste liga o log de SQL (e sempre o desliga), gera o payload, roda o `escrita_post.py` e confere pelo `pg_stat_user_tables` se outra tabela foi escrita, inclusive por gatilho | nível 3 | banco (grava e restaura) |
| `rotear.py` | os passos 8 e 8b em um comando | modos `location`, `map`, `abas` (mostram antes; com `--aplicar` gravam, testam o `nginx -t` num container descartável, recriam o proxy e conferem o runtime das telas) e `8b` (levantamento) | 8, 8b | proxy (só com `--aplicar`) |

## Enumerar e dimensionar (antes do porte)

| Arquivo | O que faz | Como faz | Passo | Altera |
| --- | --- | --- | --- | --- |
| `dimensiona.py` | mede as áreas ainda não migradas | consulta o menu no banco, classifica cada tela (fantasma, já no 8.5, faltando) e roda o `enumera.py` por área | fluxo da área, B | nada |
| `prefixos_area.py` | diz quais prefixos uma área precisa migrar e se vão por `location` ou `map` | cruza o menu da área no banco com o `nginx.conf` e o `faseb_map.conf`, agrupando por prefixo | fluxo da área, B | nada |
| `enumera.py` | monta o universo de um lote e a lista de arquivos a alterar | parte das telas do prefixo (ou de `TELAS=`) e fecha pelas nove frentes (include, `new cl_*`, `getDao`, `model/`/`std/`, namespace); conta as categorias que quebram no PHP 8 | 1–3 | nada |
| `ns_fecho.py` | 9ª frente: classes com namespace em `src/`, `app/` e `api/` | acha nomes por `use`, nome qualificado e serviços do `bootstrap.php` e os resolve pelo mapa PSR-4, até não aparecer arquivo novo | 1–3 (dentro do `enumera.py`) | nada |
| `residuo.py` | mede o resíduo de cada módulo para escolher o próximo | fecho de cada tela e classificação de cada dependência (paga, exclusiva, compartilhada com módulo não portado) | escolha do próximo módulo | nada |
| `conta_tokens.php` | conta, pelo tokenizer, só no código (nunca em comentário ou string), as construções que não sobrevivem ao PHP 8 | tokeniza cada arquivo e conta `split`/`ereg`/`each`, `parse_str` de 1 argumento, construtor PHP 4 e `0 == ""` sem guarda | medições pontuais | nada (só roda no 8.5) |

## Portar (passo 4)

| Arquivo | O que faz | Como faz | Passo | Altera |
| --- | --- | --- | --- | --- |
| `rector-curado.php` | a configuração do Rector | lê os alvos de `ALVOS`, fixa a versão em PHP 8.0, carrega as duas regras próprias e veta 40 regras, cada uma com o motivo | 4 | código (quando o Rector roda) |
| `rector-rules/GuardaComparacaoLiteralRector.php` | regra própria: a guarda do `0 == ""` | troca `$this->X == "literal"` (X iniciada com inteiro) por `($this->X === 0 \|\| $this->X === 0.0 \|\| $this->X == "")` | 4 | código |
| `rector-rules/ParseStrComExtractRector.php` | regra própria: `parse_str` de 1 argumento | troca `parse_str($s);` por `parse_str($s, $__qs); extract($__qs);`, reaproveitando o nó para não perder comentários | 4 | código |
| `porta.py` | o passo 4 antigo, por regex sobre bytes (substituído pelo Rector desde o `iss`) | troca `split`, completa o `parse_str`, renomeia construtores PHP 4 e aplica a guarda; só relata `each`, `ereg`, offset `{}` e `=& new` | referência | código |

## Verificar (passos 5 a 7)

| Arquivo | O que faz | Como faz | Passo | Altera |
| --- | --- | --- | --- | --- |
| `carrega_arquivo.php` | carrega um arquivo com o bootstrap, para pegar assinatura incompatível entre classe mãe e filha (LSP) | inclui o bootstrap e o arquivo; uma função de shutdown relata o fatal | 5b | nada |
| `instancia_classes.php` | instancia cada classe e imprime uma assinatura do estado inicial | `new X()` sem argumentos e md5 das propriedades; o diff entre runtimes mostra construtor que não rodou | 6 | nada |
| `escrita.php` | exercita o `atualizacampos()` com um formulário simulado | preenche `HTTP_POST_VARS` com `1000`, `1001`… e imprime o que cada campo leu; mostra a guarda `0 == ""` faltando | 6b | nada |
| `porclasse.sh` | roda um harness com uma classe por processo | grava cada linha num arquivo e chama o php com `</dev/null`; um fatal derruba só aquela classe; `#TOTAL` no stderr | 6, 6b | nada |
| `harness_robusto.sh` | roda o `instancia_classes.php` pulando a classe que derruba o processo | conta as linhas de saída para achar a culpada e recomeça da seguinte (só serve para harness de uma linha por entrada) | 6 (forma antiga) | nada |
| `negada_alvos.py` | acha as ocorrências de `$this->X != ""` sem guarda | regex sobre bytes em `classes/`, anotando o método, o modo do `atualizacampos()` e se é auditoria ou negócio | 6c | nada |
| `negada.php` | mede se `campo != ""` decide igual nos dois runtimes | com o formulário vazio, instancia, chama o `atualizacampos()` no modo anotado e avalia a comparação | 6c | nada |
| `negada_compara.py` | compara as saídas do `negada.php` e dá o veredito do lote | indexa por (classe, campo, método), classifica as diferenças e separa o lote do resto | 6c | nada |
| `negada_corrige.py` | aplica a guarda da forma negada nos pontos da lista | localiza o método e troca só a forma sem guarda | 6c (correção) | código |
| `cmp.py` | a bateria de telas: compara cada tela entre 5.6 e 8.5 | restaura a sessão antes de cada pedido, normaliza o que muda a cada pedido, compara status e corpo e repete o par antes de acusar | 7 | sessão |
| `guarda_ciclo.py` | corrige, uma linha por vez, `pg_*` recebendo `false` | pede a tela ao 8.5, lê o fatal do `error.log` e envolve só aquela linha em `($r ? pg_xxx(...) : null)`; repete | 7 (correção) | código |
| `campo_ciclo.py` | o mesmo, para `pg_result` com coluna inexistente e `pg_free_result(false)` | mesmo ciclo, outros padrões | 7 (correção) | código |
| `const_ciclo.py` | o mesmo, para constante indefinida | troca por `(defined('X') ? X : 'X')`, o que o 5.6 devolvia | correção pontual (Educação) | código |

## Nível 3 (POST real)

| Arquivo | O que faz | Como faz | Passo | Altera |
| --- | --- | --- | --- | --- |
| `escrita_post.py` | faz o POST nos dois runtimes e compara o SQL de escrita de negócio | fotografa as tabelas e sequências, posta no 5.6, restaura, posta no 8.5, restaura, e compara os `INSERT`/`UPDATE`/`DELETE` lidos do log do PostgreSQL (sem a auditoria) | nível 3 | banco (grava e restaura) |
| `payload.py` | mostra o formulário da tela, para montar o payload à mão | GET da tela no 5.6 e extração dos campos e botões | nível 3 | sessão |
| `payload_auto.py` | gera uma primeira tentativa de payload | o mesmo GET, com valores por heurística sobre o nome do campo | nível 3 | sessão |
| `demo_nivel3.sh` | demonstração do nível 3 (IDÊNTICO, DIVERGE com a guarda desfeita, IDÊNTICO) | roda o `payload_auto.py` e o `escrita_post.py`; na 2ª rodada edita uma classe e a devolve pelo git | demonstração | banco e código (devolvidos no fim) |
| `n3_rh_payloads.tsv` | dados: os payloads montados à mão para as telas de cadastro do RH em que o payload automático não grava | uma linha por tela: tela, tabelas a restaurar (filha antes da mãe) e payload | nível 3 do RH | — |

## Roteamento (passos 8 e 8b)

| Arquivo | O que faz | Como faz | Passo | Altera |
| --- | --- | --- | --- | --- |
| `gera_map_faseb.py` | gera o `docker/proxy/faseb_map.conf` (roteamento por lista) | exporta do banco as telas de cada área, soma o `faseb_map_abas.txt`, descarta o que não existe em disco e reescreve o arquivo inteiro | 8 | proxy |
| `redirecionamentos.py` | acha telas no 8.5 que, ao abrir, mandam a uma tela servida pelo 5.6 | GET de cada tela de menu no 8.5 e procura de redirecionamento e `iframe`; classifica cada destino | 8b | sessão |

## Investigação pontual

| Arquivo | O que faz | Usado em |
| --- | --- | --- |
| `teste_phar.php` | testa o `PHPExcel.phar` (carrega as classes e gera um XLS para comparar o md5 entre os runtimes) | 12ª lacuna, RH |
| `valida_token.php` | confere se um token do Passport antigo é aceito pelo `league/oauth2-server` novo | migração do Laravel |

## Defeitos conhecidos nestes scripts

Levantados na revisão de 17/11/2026, que acrescentou os comentários. **Ainda não corrigidos**: a revisão mudou só
comentários.

| Arquivo | Defeito | Efeito |
| --- | --- | --- |
| `verifica_lote.py` | no passo 7, o `if sumiram:` e o `else:` ficaram presos ao `if tout_56:` (indentação) | as conhecidas que voltaram a ficar idênticas só aparecem se houver timeout no 5.6; com a lista carregada, o relatório pode dizer "sem lista de conhecidas" |
| `rotear.py` | o modo `abas` grava o `faseb_map_abas.txt` antes de guardar a cópia de segurança | se o `nginx -t` falhar, o desfazer não restaura esse arquivo |
| `redirecionamentos.py`, `payload_auto.py`, `demo_nivel3.sh` | restauram a sessão de um `.bak` que eles mesmos não criam | se o `.bak` for de outra sessão, sobrescreve a sessão atual |
| `demo_nivel3.sh` | acha a sessão com `sess_*` em vez de `sess_?*` | pode pegar o arquivo `sess_` vazio |
| `escrita_post.py` | ABORTADO sai com o mesmo código de DIVERGE; nele, as tabelas `_n3snap_*` ficam no banco; payload com `'` quebra o comando | resultado ambíguo e resíduo no banco |
| `guarda_ciclo.py`, `campo_ciclo.py`, `const_ciclo.py` | a troca vale para **todas** as ocorrências da linha, não só a do fatal | pode guardar mais que o necessário |
| `gera_map_faseb.py` | não confere se o `psql` funcionou | pode reaproveitar sem aviso uma exportação antiga |
| `residuo.py` | usa só as frentes antigas de enumeração | mede um universo menor que o do `enumera.py` |
| `enumera.py` | imprime "universo (6 frentes)", mas percorre nove | só o rótulo está errado |

## Como conferir que um arquivo mudou só nos comentários

A revisão que acrescentou os comentários foi conferida mecanicamente, comparando cada arquivo com a versão anterior
**sem os comentários**: a árvore sintática no Python (`ast`), os *tokens* do PHP (`token_get_all`) e as linhas sem
comentário no shell. Os 35 arquivos deram iguais, o que prova que nenhuma linha de código mudou. Também foram conferidos
a codificação e os finais de linha (sem mudança) e o `php -l` de cada `.php` antes e depois, nos dois runtimes (o mesmo
resultado). Os `.php` que não compilam no 5.6 (`conta_tokens.php`, `rector-curado.php`, as duas `rector-rules/` e
`valida_token.php`) são ferramentas feitas só para o PHP 8, e já não compilavam antes.
