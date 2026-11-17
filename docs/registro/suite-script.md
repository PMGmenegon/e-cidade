# Script único da suíte de testes (esqueleto, T-008)

Um comando roda as camadas **unitária** e **de integração** (e, quando existir, a de **sistema**) no PHP 5.6 e no 8.5
e gera um relatório por runtime. Origem: PB-003 (critérios 1 e 2). Linha de base e guia final: T-010; inventário dos
testes legados: T-009.

## Comando

Da raiz da worktree, com os containers do agente no ar (`sobe-ambiente.sh <Agente> <worktree> <porta-base>`):

```bash
node <quadro>/ferramentas/suite.mjs bash ecidade/tests/suite/rodar.sh [opções]
```

`suite.mjs` limita a 2 suítes simultâneas na máquina. Opções de `rodar.sh`:

| Opção | Efeito |
|---|---|
| `--camada unitario,integracao,sistema` ou `todas` | camadas a rodar (padrão `unitario,integracao`) |
| `--runtime 56\|85\|ambos` | runtime (padrão `ambos`) |
| `--agente NOME` | containers `ecidade_<nome>_56/_85` (padrão: derivado do nome da worktree) |
| `--saida PASTA` | onde gravar os relatórios (padrão `ecidade/tests/suite/relatorios/`, ignorado pelo git) |

Código de saída: `0` tudo passou; `1` algum teste falhou, erro de execução, ou nenhum teste selecionado; `2` uso/ambiente
(camada inválida, container parado, phar com sha256 errado).

## Como funciona

- **PHPUnit por runtime, fora do `vendor/`:** phar fixado por versão e sha256 em `ferramentas.sha256`
  (5.7.27 no 5.6; 9.6.38 no 8.5 (trocado do 12.5.0 pela T-009: o 12 não lê `@dataProvider`; ver `testes-inventario.md`)). Fica em `~/.cache/ecidade-suite/` (`SUITE_CACHE`), baixado de `phar.phpunit.de` se faltar,
  conferido a cada execução e copiado para `/tmp/suite/` do container. Nada é gravado no `vendor/` nem no banco.
- **Sem `phpunit.xml`:** roda com `--no-configuration --bootstrap tests/suite/bootstrap.php` (só o autoload do composer);
  o `ecidade/phpunit.xml` é do PHPUnit 5.7 e não serve ao 12.
- **Camadas:** `ecidade/tests/suite/camadas/<camada>.lista`, uma entrada por linha (arquivo ou pasta relativa a `ecidade/`),
  opcionalmente `|56`, `|85` ou `|56,85` para limitar o runtime. A camada **sistema** está vazia de propósito: T-011/T-012
  acrescentam as entradas. Pedir só camadas vazias sai com `1`.
- **Lacunas:** `camadas/lacunas.lista` (`arquivo|motivo`) é copiada para o fim de cada relatório.
- **Relatório:** `relatorio-56.txt` e `relatorio-85.txt` (total, aprovados, falhos, pulados, erros de execução, tempo, por
  camada, `resultado`), mais `junit-<runtime>/`. Contado a partir dos `<testcase>` do JUnit, igual nas duas versões.
- **Escrever teste que rode nos dois:** `use PHPUnit\Framework\TestCase;` (existe no 5.7 e no 12), sem `setUp()` com tipo de
  retorno (`: void` não compila no 5.6), sem anotações de metadados (o 12 não lê). As amostras estão em `tests/suite/amostra/`.

## Estado

As duas amostras passam nos dois runtimes. **T-009:** os 46 arquivos de `ecidade/tests/Unit` estão em `camadas/unitario.lista`
(10 nos dois runtimes, 36 só no 5.6) e as 36 lacunas do 8.5, mais `Recadastramento.php` e `cypress`, em `camadas/lacunas.lista`, com
motivo. `bootstrap.php` agora também carrega o bootstrap do e-cidade. Números e achados: `docs/registro/testes-inventario.md`.
