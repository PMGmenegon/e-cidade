# Suíte de testes: linha de base

Guia: `docs/suite-de-testes.md`. Script: `docs/registro/suite-script.md`. Inventário dos testes: `docs/registro/testes-inventario.md`.

## Linha de base (antes de qualquer atualização do Laravel)

- **Data:** 13/11/2026.
- **Código medido:** `laravel/integracao` no commit `132fd39da` (T-008 e T-009 integradas; nenhuma tarefa de upgrade do Laravel).
- **Comando** (da raiz da worktree, runtimes no ar por `sobe-ambiente.sh`; camadas `unitario,integracao`, os dois runtimes):
  `node <quadro>/ferramentas/suite.mjs bash ecidade/tests/suite/rodar.sh`
- **Ambiente:** PHP 5.6.40 com PHPUnit 5.7 e PHP 8.5.12 com PHPUnit 9.6.38 (phars da T-008).
  Os testes desta suíte são unitários e de integração em memória: não usam banco nem terceiros.

| | PHP 5.6.40 | PHP 8.5.12 |
|---|---|---|
| total | 279 | 75 |
| aprovados | 279 | 73 |
| falhos | 0 | **2** |
| pulados | 0 | 0 |
| erros de execução | 0 | 0 |
| unitário | 277/277 | 71/73 |
| integração | 2/2 | 2/2 |
| resultado | APROVADO | REPROVADO |

Código de saída do comando: `1` (por causa do 8.5). A diferença de total (279 × 75) não é regressão: dos 46 arquivos de teste
existentes, 36 só compilam no PHPUnit 5.7 e estão em `lacunas.lista` para o 8.5 (abaixo). Rodam nos dois os outros 10 e as amostras.

### Falhas no 8.5 (achados, não corrigidos)

Os dois testes passam no 5.6 e falham no 8.5 pela mesma causa, o handler de erro V3 (`src/V3/Error/Handler/Error.php:20`:
`_handle()` recebe 4 argumentos e exige 5):

1. `ECidade\V3\Error\Handler\ShutdownTest::testHandleExpectNothing` — `ArgumentCountError`.
2. `ECidade\V3\Error\Handler\ErrorTest::testHandleWithoutReporting` — `ExpectationFailedException` (a entidade de erro não é a esperada).

São defeitos de migração (só no runtime novo); a tarefa é a **T-026**. A linha de base **não** os esconde: o 8.5 fica REPROVADO até
a T-026 entrar. Depois dela, rodar de novo e acrescentar aqui uma linha "depois".

### Lacunas (testes que não rodam, com o motivo)

Fonte: `ecidade/tests/suite/camadas/lacunas.lista` (38 entradas), copiada para o fim de cada relatório.

- **33 no 8.5** — herdam de `Tests\TestCase` (Mockery antigo do `vendor/`, `setUp()` sem `void`: fatal no PHPUnit 9/12). Só se
  resolvem quando o `vendor/` do runtime novo trouxer Mockery/Laravel atualizados (tarefa de upgrade, não desta).
- **3 no 8.5** — `tests/Unit/V3/Extension/{Container,Logger,ParameterBag}Test.php`: `setUp()` sem tipo de retorno (o PHPUnit 9 exige
  `: void`, que não compila no 5.6; mexer no teste está fora do escopo).
- **`tests/Unit/Recadastramento.php`** — fora do `phpunit.xml`; 4/5 passam no 5.6, `testCampoValor` falha já no 5.6 (defeito antigo).
- **`tests/cypress/`** — camada de sistema no navegador, das tarefas T-011/T-012.

A camada **sistema** está vazia nesta linha de base (T-011/T-012/T-016 acrescentam as entradas).

### O que a linha de base não prova

Só o que está nos 46 testes existentes e nas amostras (classes de `V3`, `Agua`, RH, `Msc`, `LicitaCon`, helpers). Não cobre telas,
rotas `/v4`, o Laravel inicializando nem banco; isso fica para a camada de sistema.

### Como reproduzir

```
bash <quadro>/ferramentas/sobe-ambiente.sh <Agente> <worktree> <porta-base>
node <quadro>/ferramentas/suite.mjs bash ecidade/tests/suite/rodar.sh
cat ecidade/tests/suite/relatorios/relatorio-56.txt ecidade/tests/suite/relatorios/relatorio-85.txt
```

Esperado no `132fd39da`: 5.6 `APROVADO` (279/279); 8.5 `REPROVADO` (73/75, as duas falhas acima); saída `1`.
