# Lint do universo: "depois" da T-018 (namespace AndamentoPadrao e nome `String`)

> Complementa `docs/registro/lint-universo.md` (T-003, branch `testes/T-003-lint-universo`, ainda não integrada: por isso este
> trecho está em arquivo próprio; juntar ao `lint-universo.md` quando a T-003 entrar). Medido em 12/11/2026 sobre
> `laravel/integracao` (59c46e20b), branch `laravel/T-018-namespace-reservados`.

## Os 6 arquivos

Classe de cada um (T-004 e T-017 ainda sem resultado publicado: a branch `rector/T-004-varredura-simulacao` está igual à
integração e não há branch da T-017; nenhum dos 6 aparece em outra branch; correção **manual**, sem Rector):

| Arquivo | Defeito (8.5) | Correção | Por que reproduz o 5.6 |
|---|---|---|---|
| `app/.../Controller/Processo/AndamentoPadrao/CamposDinamicosController.php` | `use …\AndamentoPadrao` + quebra de linha + `\CamposDinamicos as …` | nome do `use` numa linha só | o lexer do 5.6 ignora o espaço entre as partes do nome: fluxo de tokens idêntico |
| `…/CamposDinamicosRespostaController.php` | idem (`\CamposDinamicosResposta as …`) | idem | idem |
| `app/.../Repository/Processo/AndamentoPadrao/CamposDinamicosRepository.php` | `use …\Contracts\` + quebra + `AndamentoPadrao\CamposDinamicosRepository as RepositoryInterface` | idem | idem |
| `…/CamposDinamicosRespostaRepository.php` | idem | idem | idem |
| `app/.../Transformers/Processo/AndamentoPadrao/CamposDinamicosResposta.php` | `use …\AndamentoPadrao` + quebra + `\CamposDinamicosResposta as …Model` | idem | idem |
| `src/Financeiro/Contabilidade/Sagres/ArquivosSagresFiscalInterface.php` | `use Cake\Utility\String;` — `String` é nome especial no PHP 7+ | linha do `use` removida | o `String` do import **nunca é usado** no arquivo (só a linha 30 o cita); import sem uso não carrega classe no 5.6, então tirar a linha não muda nada em execução |

Nos 5 primeiros o texto é o mesmo, só sem a quebra de linha dentro do nome (o PHP 8 trata o nome qualificado como um token
único e rejeita o espaço). Nenhum nome de classe/namespace foi mudado, então **nenhuma referência** em `app/`, `src/`,
`routes/` ou autoload precisou de ajuste. Não há cópia em `extension/modification/`. ISO-8859-1 preservado (dois dos
arquivos são ISO-8859-1; a edição foi em nível de byte, mantendo o fim de linha).

## Medidas

- **`php -l`**, antes (em `laravel/integracao`) e depois, nos containers `ecidade_back3_56` / `ecidade_back3_85`:
  antes 6/6 passam no 5.6 e **6/6 falham** no 8.5; depois **6/6 passam nos dois**.
- **Fluxo de tokens no 5.6** (`token_get_all`, sem espaço e comentário): original × corrigido **idêntico** nos 5 de
  namespace; no `ArquivosSagresFiscalInterface.php` a diferença é exatamente os 7 tokens do `use Cake\Utility\String;`.
- **Carga das classes** (`class_exists`/`class_implements` sobre o `vendor/` atual): saída **igual** no 5.6 e no 8.5 para os
  2 controllers, os 2 repositórios (interfaces `BaseRepository` e `Contracts\…`) e o transformer. A interface Sagres,
  carregada direto por `require_once`, carrega nos dois com os mesmos métodos (`__construct`, `emitirXML`).

## Lacunas (registradas)

- **Rotas `/v4/patrimonial/protocolo/{tipo_processo}/andamento-padrao/campos-dinamicos…`** (`routes/api/patrimonial/protocolo.php`)
  usam os 2 controllers; o stack HTTP do Laravel 5.4 não roda no 8.5, então a comparação 5.6 × 8.5 por requisição **não é
  possível** hoje. No 5.6 a prova é a identidade de tokens acima. Exercitar as rotas exige token OAuth e gravaria no banco
  (POST/PUT), fora do permitido.
- **`ArquivosSagresFiscalInterface` (Financeiro)**: só é carregada quando um implementador é instanciado (alcançável por
  `con4_sagres.RPC.php`); não exercitada por tela nesta tarefa. O autoload do Composer não a resolve (carregada por
  `require` direto nos testes).
- O gêmeo `src/RecursosHumanos/Pessoal/Sagres/ArquivosSagresFiscalInterface.php` não está na lista de falhas e não foi tocado.
