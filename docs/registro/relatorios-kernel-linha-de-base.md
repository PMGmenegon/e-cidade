# Linha de base dos 5 relatórios que sobem o kernel do Laravel (T-023, 13/11/2026)

Gabarito do 5.6 (Laravel 5.4) **antes** de qualquer troca de Laravel (a comparação com o runtime novo vem depois). Os 5 relatórios
(`docs/registro/laravel.md`, "Pontos de contato", item 3) fazem `require bootstrap/app.php` e `$kernel->handle(Request::capture())` dentro da página:
`con2_lrfdivida002_2018`, `con2_lrfgarantias002_2018`, `con2_lrfresumido002_2018`, `con2_opercredito002_2018`, `con2_anexovirgf_002`.

Módulo novo da camada sistema: `ecidade/tests/sistema/relatorios-kernel/` (não toca `cmp.py` nem `rodar.sh`).

| Arquivo | Para quê |
|---|---|
| `casos.tsv` | os 10 pedidos GET (por relatório: sem parâmetros e com os parâmetros que a tela de filtro envia: `periodo`, `db_selinstit`, `emite_*`) |
| `sessao.sh` | login pelo 5.6 e arquivo de sessão (com instituição/módulo/exercício 2018 acrescentados na própria sessão); roda em container **normal** |
| `relatorios_kernel.py captura` | refaz a sessão antes de cada pedido, pede ao container, normaliza e grava um `.out` por caso |
| `relatorios_kernel.py compara` | compara uma captura com `base/`; **sai 1** se algum caso difere (mostra o diff) |
| `base/*.out` | a linha de base (10 arquivos; só mensagens de erro/redirecionamento, sem dado pessoal) |

Normalização: `sid=`, `wname…`, hashes de 32 hex, `localhost:<porta>`, data/hora, datas de PDF e o número do recurso do pg (`result index N`).

## Reproduzir

```bash
P=<porta do 5.6>; C=<container do 5.6>              # 5.6 sobre a sua cópia do repositório
# suba o 5.6 normal (que grava), só para criar a sessão: o login grava token/log de acesso
bash ecidade/tests/sistema/relatorios-kernel/sessao.sh $P $C /tmp/sessao-rk 2018
# recrie o 5.6 com PGOPTIONS='-c default_transaction_read_only=on' (somente leitura; a sessão fica no host)
python3 ecidade/tests/sistema/relatorios-kernel/relatorios_kernel.py captura --porta $P --container $C --sessao /tmp/sessao-rk --saida /tmp/nova
python3 ecidade/tests/sistema/relatorios-kernel/relatorios_kernel.py compara --novo /tmp/nova    # 0 = igual à linha de base
```

O arquivo de sessão que o `sessao.sh` gera contém a senha do banco do container: mantê-lo fora do repositório (`/tmp`).

## Resultado

- Duas capturas seguidas em containers `SOMENTE_LEITURA=1`: **10/10 iguais**. Teste do comparador: contra a própria linha de base, 10/10 e saída 0;
  com um caractere acrescentado em `anexovirgf_periodo.out`, 9/10 e saída 1 (mostra o diff).
- Confirmado que a captura não grava: `pg_stat_user_tables` (inserções/alterações/exclusões) antes e depois não mudou em nenhuma tabela dos relatórios.
  (`db_usuariosonline` também sobe por causa dos outros agentes que usam o mesmo banco; nas tabelas de configuração a diferença é zero.)

| Caso | 5.6 em container somente leitura (= `base/`) |
|---|---|
| `anexovirgf_*` (3) | roda até o fim do que os parâmetros permitem: redireciona a `db_erros.php` com `Undefined property: stdClass::$db_selinstit` / `$rcl` / `$pessoal` (kernel sobe antes: `bootstrap/app.php` é carregado na 1ª linha do `try`) |
| `lrfdivida_*`, `lrfgarantias_*`, `opercredito_*`, `lrfresumido_balorc` (7) | **param na trava**: `Erro:(27) inserindo arquivo em db_usuariosonline: ERRO: não é possível executar INSERT em uma transação de leitura-apenas` (a tela grava o registro de usuário online antes de qualquer coisa) |

## O que a trava escondeu — medido uma vez, com container gravável (informativo, não é linha de base)

Para saber o que há por trás da trava rodei os mesmos pedidos num container normal (grava só o acesso do sistema). Respostas do 5.6:
`lrfdivida_*` e `lrfgarantias_*` → `pg_result(): Unable to jump to row 0 on PostgreSQL result index N`; `opercredito_*` → `Division by zero`;
`lrfresumido_balorc` → HTTP 500 JSON `Undefined property: stdClass::$prevatu`; `lrfresumido` sem nenhum `emite_*` (fora de `casos.tsv`) → **gera um PDF de ~37 KB**.
A base de exemplo **não tem dados contábeis** (`orcdotacao`, `orcreceita`, `empempenho`, `conlancam` vazias; configuração de relatório existe), por isso nenhum relatório chega a um PDF de números reais.

**Achado — herdado do legado, não corrigido:** emitir esses relatórios **grava no banco**. Cada rodada dos 10
pedidos, no 5.6 gravável, apagou e reinseriu 46 linhas de `orcparamseqfiltropadrao` (código "duplica as configurações padrão", `libs/db_libcontabilidade.php` ~6445; saldo líquido 0)
e criou ~460 linhas de trilha em `db_acount*`. Essa medição foi feita antes de eu saber que havia escrita (ao menos 3 rodadas gravando, além de sondagens preliminares; líquido zero em `orcparamseqfiltropadrao`; as
trilhas `db_acount*` ficaram). A captura que vale como linha de base é a de container somente leitura, que não grava.

## Lacunas (a fechar na comparação com o runtime novo)

1. Os 7 casos barrados pela trava só mostram o erro de `db_usuariosonline`: não provam que o kernel subiu nem a saída dos relatórios. Comparar o runtime novo com eles só prova que a trava continua igual.
   Exercitar o corpo dos relatórios exige escrita (usuário online + duplicação de filtros) e dados contábeis: banco descartável com dados, fora da regra do cliente → dublê ou lacuna.
2. PDF com dados reais nunca foi gerado (base sem dados); o normalizador de datas de PDF existe, mas não foi exercitado.
3. O 8.5 não roda estes cinco hoje (Laravel 5.4): a comparação 5.6 × novo vem depois, com `compara --novo <captura do runtime novo>`.
