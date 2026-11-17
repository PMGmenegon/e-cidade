# O que usa os pacotes que saem do conjunto novo

Varredura só de leitura (`scratchpad/usos_pacotes.py`, 13/11/2026, base `laravel/integracao` `0114188f9`). Lista completa, uma
linha por uso (pacote, assunto dono, `arquivo:linha`, padrão, tipo de uso, alcance, telas de menu, trecho):
`docs/registro/usos-pacotes-que-saem.tsv`. Reproduzir: `python3 scratchpad/usos_pacotes.py --saida-tsv X.tsv` (≈3 min;
lê `db_itensmenu` com um SELECT via `ecidade_database`; `--sem-banco` usa só o roteamento). Testes: `scratchpad/sistema/test_usos_pacotes.py`.

Parte da matriz de versões (`docs/migracao-laravel/matriz-versoes.md`), do estudo do Silex (`docs/migracao-laravel/silex-caminhos-e-suporte.md`) e da linha de base de documentos; **os números batem** (Silex 20 arquivos com uso
real mais `app.php` e o docblock de `agendaPagamento`; Pimaco 4; Pix 1 arquivo; Phinx 1.510 migrations; PhpSpreadsheet 25
arquivos; PhpWord 11) e acrescentam o alcance e o assunto dono de cada uso.

## Resumo

| Pacote que sai | Dono | Ocorrências | Arquivos | Código (≠ comentário) | Tela de menu | Núcleo (quase toda tela) | Roteada (api/location) | CLI (migrations) | Sem referência estática | Laravel próprio (tratado a parte) |
|---|---|---|---|---|---|---|---|---|---|---|
| `silex/silex` | API V1 (Silex) | 57 | 22 | 56 (21 arq.) | 0 arq. | 1 arq. | 20 arq. | 0 arq. | 0 arq. | 0 arq. |
| `proner/phppimaco` | documentos (PDF/planilha/Word/etiquetas) | 5 | 4 | 5 (4 arq.) | 0 arq. | 0 arq. | 0 arq. | 0 arq. | 0 arq. | 4 arq. |
| `dbseller/phinx_postgres + robmorgan/phinx` | migrations Phinx | 1513 | 1512 | 1513 (1512 arq.) | 0 arq. | 0 arq. | 0 arq. | 1510 arq. | 2 arq. | 0 arq. |
| `dbseller/sdk-api-pix-bb` | Pix BB | 5 | 1 | 5 (1 arq.) | 0 arq. | 0 arq. | 0 arq. | 0 arq. | 0 arq. | 1 arq. |
| `mpdf/mpdf 7` | documentos (PDF/planilha/Word/etiquetas) | 7 | 3 | 7 (3 arq.) | 2 arq. | 0 arq. | 0 arq. | 0 arq. | 1 arq. | 0 arq. |
| `phpoffice/phpspreadsheet 1.8` | documentos (PDF/planilha/Word/etiquetas) | 92 | 25 | 31 (7 arq.) | 2 arq. | 0 arq. | 0 arq. | 0 arq. | 1 arq. | 4 arq. |
| `phpoffice/phpword 0.17` | documentos (PDF/planilha/Word/etiquetas) | 14 | 11 | 14 (11 arq.) | 5 arq. | 1 arq. | 2 arq. | 1 arq. | 0 arq. | 2 arq. |
| `zendframework/zend-*` | eventos do V3 (zend-*) | 7 | 7 | 7 (7 arq.) | 0 arq. | 4 arq. | 1 arq. | 0 arq. | 2 arq. | 0 arq. |

"Tela de menu" = o arquivo é alcançado por referência estática a partir de uma tela de `db_itensmenu`; "núcleo" = alcançado
por mais de 500 telas (`app.php`, `src/V3`); "roteada" = `api/` (FrontController) ou prefixo do `location` fora do menu;
"CLI" = `db/migrations`, `integracao_externa`; "sem referência estática" = nenhum arquivo PHP o cita (pode ser chamado por JS
ou URL; JS/HTML não foram varridos). "Laravel próprio" = `app/`, `routes/`, `config/`, `bootstrap/`: contado à parte, é tratado a parte.

## Leitura por assunto

- **API V1 (Silex):** 20 arquivos em `api/` (19 em `api/V1` + `api/api.php`), todos alcançados pela rota `api/` do
  FrontController, nenhum por tela de menu. `app.php:16` (`use Silex\Application`, import sem uso) é do núcleo.
  `model/agendaPagamento.model.php:2792` é só docblock.
- **Documentos (PDF, planilha, Word, etiquetas):** mPDF 7 em 3 arquivos: `forms/db_frmprotprocessovolume.php:28` (`use Mpdf\Tag\Strong`; chega por
  `pro4_protprocessovolume`, de menu), `src/Library/SpreadSheet/Template/Parser.php` e
  `db_download_todos_arquivos_visualizador.php` (nenhuma referência estática). PhpSpreadsheet: 7 arquivos de código
  (`arr2_extratocontribuinte002` — 5 usos, tela de menu via `arr2_extratocontribuinte001` —, `src/Library/SpreadSheet/Template/Parser.php`,
  `src/Financeiro/.../Razao/PorConta/Excel.php`, mais 4 em `app/`); o resto das 92 ocorrências são docblocks. PhpWord: 11
  arquivos (5 por tela de menu, 2 roteadas, 1 migration, 1 do núcleo, 2 em `app/`). Pimaco: 4 arquivos, todos em `app/`.
- **Pix BB:** 1 arquivo, `app/Domain/Tributario/Arrecadacao/Pix/Bancos/BancoDoBrasil.php`, 5 `use Swagger\Client`
  (código próprio do Laravel, tratado a parte).
- **Migrations Phinx:** 1.510 migrations (CLI) usam `Classes\PostgresMigration`/`Phinx`, mais `phinx.php:11` e
  `model/configuracao/DBDataBaseMigration.model.php:368,376` sem referência estática.
- **Eventos do V3 (`zend-*`):** `src/V3/Error/EventHandler.php`, `src/V3/Event/Handler.php`, `src/V3/Event/Manager.php`,
  `extension/package/DBug/Event/Bootstrap.php` (núcleo, toda tela), `iss4_isscalc.RPC.php:2` (`Zend\Stdlib\DateTime`, roteada),
  `extension/package/ErrorLog/Event/Handler.php` e `tests/Unit/V3/Error/EventHandlerTest.php` (sem referência estática).

## Conferência à mão (5)

`api/api.php:19` (`use Silex\Application`), `forms/db_frmprotprocessovolume.php:28` (`use Mpdf\Tag\Strong`),
`arr2_extratocontribuinte002.php:1627` (`\PhpOffice\PhpSpreadsheet\Style\Border`), `iss4_isscalc.RPC.php:2`
(`use Zend\Stdlib\DateTime`) e `phinx.php:11` (`'Classes\PostgresMigration'`): a linha existe e é código. Menu conferido em
`db_itensmenu`: `arr2_extratocontribuinte001`, `pro4_protprocessovolume` e `iss4_isscalc001` estão no menu;
`db_download_todos_arquivos_visualizador` não é citado por nenhum `.php`/`.js` do docroot.

## Limites

Include/`new` dinâmico (nome montado em variável) e chamadas por JS/URL não entram no grafo; o fecho por nome de classe
legada (≥ 6 letras) e por literal `nome.php` **superestima** o alcance, não o subestima por nome estático. Uso por
`extension/modification/data` (cache do `modification()`) fica fora.
