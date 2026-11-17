# Suíte de testes: guia curto

Um comando roda os testes **unitários** e de **integração** (e, quando existir, de **sistema**) no PHP 5.6 e no 8.5 e
grava um relatório por runtime. Detalhes técnicos: `docs/registro/suite-script.md`. Linha de base: `docs/registro/suite-testes.md`.

## Como rodar

1. Suba os runtimes da sua worktree (porta-base livre, ver `PROJETO.md`):
   `bash <quadro>/ferramentas/sobe-ambiente.sh <Agente> <worktree> <porta-base>`
2. Da raiz da worktree:
   `node <quadro>/ferramentas/suite.mjs bash ecidade/tests/suite/rodar.sh`
   - o agente (containers `ecidade_<nome>_56` e `_85`) é o trecho depois do último hífen do nome da pasta da worktree
     (`ecidadelaravel-front1` → `front1`); se o seu for outro, passe `--agente <nome>` (o nome usado no `sobe-ambiente.sh`)
   - só uma camada: `--camada unitario` (ou `integracao`, `sistema`, `todas`)
   - só um runtime: `--runtime 56` ou `--runtime 85`
3. Código de saída: `0` tudo passou; `1` teste falho/erro/nada selecionado; `2` uso ou ambiente (container parado, camada inválida).
4. Derrube ao terminar: `… sobe-ambiente.sh <Agente> <worktree> <porta-base> parar`.

## Onde fica o relatório

`ecidade/tests/suite/relatorios/relatorio-56.txt` e `relatorio-85.txt` (total, aprovados, falhos, pulados, erros de
execução, tempo, por camada, `resultado: APROVADO|REPROVADO`) e o JUnit bruto em `junit-56/`, `junit-85/`. A pasta não vai
para o git: copie o resultado para `docs/registro/` quando for registro.

## Como acrescentar um teste

1. Escreva o teste para rodar **igual no PHPUnit 5.7 (PHP 5.6) e no 9.6 (PHP 8.5)**:
   `use PHPUnit\Framework\TestCase;`, sem sintaxe PHP > 5.6 no arquivo e **sem sobrescrever `setUp()`/`tearDown()`** (o 9.6 exige
   `: void`, que não compila no 5.6: use um método auxiliar chamado no início do teste). Não herde de `Tests\TestCase`
   (Mockery antigo do `vendor/`, fatal no 8.5). Anotações como `@dataProvider` funcionam nos dois.
2. Registre o arquivo (ou pasta, relativo a `ecidade/`) em `ecidade/tests/suite/camadas/<camada>.lista`, uma por linha.
   Para limitar o runtime: `caminho|56`, `caminho|85` ou `caminho|56,85`.
3. Rode a camada nos dois runtimes e confirme `APROVADO`.
4. Teste que grava no banco ou chama terceiro (Pix, TEF, banco): use dublê. Se não der, não entra na lista.

## O que é lacuna

Teste que **não** roda na suíte, com o motivo. Fica em `ecidade/tests/suite/camadas/lacunas.lista` (`arquivo|motivo`) e é
copiado para o fim de cada relatório. Motivos aceitos: depende de gravação no banco (regra do cliente: não tocar no banco),
depende de serviço de terceiro sem dublê, ou não roda no PHPUnit 9.6 (`setUp()` sem `: void`, ou herda de `Tests\TestCase` com o Mockery antigo do `vendor/`). Lacuna sem motivo não vale.
