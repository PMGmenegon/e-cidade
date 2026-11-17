# Auditoria de acesso: caminho de erro igual ao 5.6

`db_logs()` (`ecidade/libs/db_stdlib.php`, chamada por `libs/db_conecta.php:279` em toda página de menu) grava uma linha em
`db_logsacessa` a cada acesso: pega `nextval('db_logsacessa_codsequen_seq')`, guarda o número na sessão (`DB_acessado`) e faz o INSERT.
Se o INSERT falha, a página morre com `Houve um problema ao realizar a auditoria do sistema.` (53 bytes).

## Defeito de migração

Quando o próprio `nextval` falha (banco somente leitura, sequência indisponível), `db_query()` devolve `false`:

| Runtime | `pg_result(false, 0, 0)` | Resultado da página |
|---|---|---|
| PHP 5.6 | aviso e retorno `false`; o INSERT seguinte, com `codsequen` vazio, falha | HTTP 200, `Houve um problema ao realizar a auditoria do sistema.` |
| PHP 8.5 | `TypeError` (o argumento deve ser `PgSql\Result`) | HTTP 500, página "Notificação do Sistema" (`Erro interno`, ~3,7 KB) |

## Correção

Uma linha, no mesmo estilo do `pg_numrows` logo acima no mesmo bloco, reproduzindo o 5.6 (que continuava com `codsequen = false`):

```php
$codsequen = $result ? pg_result($result, 0, 0) : false;
```

O INSERT seguinte falha como no 5.6 e o `die()` existente mostra a mesma mensagem. O caminho normal (consulta que funciona) não muda.
`libs/db_logsmanual` e `db_logsmanual_demais` não têm o defeito (não leem o resultado do `nextval`). Não há cópia do trecho em
`extension/modification/`.

## Medição (13/11/2026, tela `soc2_familiabairro001.php`, módulo Social da sessão de teste)

Teste: `ecidade/tests/sistema/auditoria/erro_auditoria.py`.

| Modo | Antes da correção | Depois |
|---|---|---|
| `--modo ro` (containers `SOMENTE_LEITURA=1`, o INSERT/`nextval` falha) | 5.6: 200, 53 B (mensagem); 8.5: 500, 3.725 B | 5.6: 200, 53 B; 8.5: 200, 53 B. **Passou** |
| `--modo rw` (containers que gravam, vigia do banco em volta (compara `pg_stat_user_tables` antes e depois)) | n/a | 5.6: 200, 7.456 B; 8.5: 200, 7.456 B, iguais e sem a mensagem. **Passou**; o vigia só viu `db_logsacessa_202611_1` e `db_usuariosonline` |

`php -l libs/db_stdlib.php` limpo nos dois runtimes.

## Como repetir

```bash
SOMENTE_LEITURA=1 bash sobe-ambiente.sh <agente> "$PWD" <porta>      # modo ro
python3 ecidade/tests/sistema/auditoria/erro_auditoria.py --modo ro --sessao <sessao.dat>
bash sobe-ambiente.sh <agente> "$PWD" <porta>                         # modo rw, com o vigia antes/depois
python3 ecidade/tests/sistema/auditoria/erro_auditoria.py --modo rw --sessao <sessao.dat>
```

A sessão autenticada é criada por `sessao.sh` (`ecidade/tests/sistema/relatorios-kernel/`); a sessão é restaurada antes de cada pedido.
