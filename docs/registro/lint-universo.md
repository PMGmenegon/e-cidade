# Lint do universo PHP nos dois runtimes (T-003)

Rodado em 12/11/2026 sobre `laravel/integracao` (59c46e20b), via `scratchpad/lint_universo.sh <agente> <saida>` (containers do `sobe-ambiente.sh`; `php -l` por arquivo, `xargs -n1 -P8`, sem abortar no 1º erro). Universo: todo `*.php` de `ecidade/` exceto `vendor/`.
T-001 **não** estava integrada: só uma contagem. Repetir após a integração.

| Runtime | Arquivos | Falhas |
|---|---|---|
| PHP 5.6 (referência) | 32.907 | 101 |
| PHP 8.5 | 32.907 | 127 |

- Falham nos dois: **100** (defeito pré-existente da referência; não é regressão da migração).
- Falham **só no 8.5**: **27** (a migrar).
- Falha **só no 5.6**: **1** (`src/Patrimonial/Protocolo/Parametros/MensageriaProcesso.php`, "unexpected end of file"; no 8.5 passa).

Conferência manual: 3 arquivos do "só 8.5" reabertos com `php -l` direto no container (`calculoiptu.php`, `duplos.php`, `securimage/securimage.php`) deram a mesma mensagem. Mensagens completas por arquivo em `lint-universo-falhas.txt` (mesma pasta).

## Classificação

1. **Falham nos dois (100)** — "pré-existente, quebra igual nos dois: fora da migração": o 5.6 de referência também não compila, então o arquivo já não executa hoje. 80 são *call-time pass-by-reference* (removido no 5.4; maioria `pes2_*`, `forms/`, `dbagata/…/phpdocwriter`), ~10 `unexpected ')'`/`db_input`/`db_log` (fontes quebrados), 2 `Interface.php` (nome reservado), 2 `unexpected '<'` (`func_calendario_atendimento_*`).
2. **Só 8.5 (27)** — "precisa de trabalho" (compilavam no 5.6; nenhuma está resolvida em `origin/assistencia-social/migracao` nem `nucleo/login-seguranca`; `origin/laravel-upgrade` é só documentação):
   - 5 em `app/Domain/Patrimonial/Protocolo/**/AndamentoPadrao/` — `namespace` com nome qualificado inválido no 8 (`unexpected fully qualified name`).
   - 5 `'break' not in the 'loop' or 'switch' context` (erro de compilação no 8): `cad1_lote002`, `cad1_lote003`, `con1_contrib007`, `dbforms/db_virafolha`, `pro4_canarquiv002` — padrão já decidido no projeto: `break` → `exit` (5.6 morria ali).
   - 4 `unexpected token "["` (`calculoiptu`, `calculoissqnfixo`, `duplos`, `duploscgs`).
   - Chaves de string `{}`/offset removidos: `securimage/{securimage,WavFile}`, `ext/php/Michelf/Markdown*` (2), `fpdf151/impmodelos/mod_imprime{10,12,13,1333}` (4), `integracao_externa/gissonline/iss4_gissonline002` — `unexpected token "{"`.
   - `libs/jpgraph/jpgraph_pie.php` (assinatura incompatível com `&$img`), `libs/jpgraph/jpgraph_radar.php` (`;` após `new`).
   - `src/Financeiro/Contabilidade/Sagres/ArquivosSagresFiscalInterface.php` (`String` é nome especial).
   - `integracao_externa/auditoria/auditoria_migracao_cursor.php` (`Invalid numeric literal`).
   - Obs.: vários pertencem a módulos "concluídos" (Patrimonial, Financeiro); não alcançados pelas baterias de tela por serem includes/libs não roteados.
3. **Só 5.6 (1)** — `MensageriaProcesso.php`: falha só na referência; sem ação (sem impacto na migração).

## Falhas completas (arquivo :: mensagem)
Ver `lint-universo-falhas.txt`.

## Recontagem de 13/11/2026 (QA da T-003, integração `1f1b8258d`)

Universo 32.866 `*.php` (32.860 versionados + 6 de configuração local). PHP 5.6: 101 falhas; PHP 8.5: 107.
Falham nos dois: **100** (igual ao início). Só no 8.5: **7** (eram 27: −10 T-021, −6 T-018, −4 T-019) — `con1_contrib007`,
`dbforms/db_virafolha`, `pro4_canarquiv002`, `duplos`, `duploscgs`, `auditoria_migracao_cursor`, `iss4_gissonline002`, todos da T-020.
Só no 5.6: **1** (`MensageriaProcesso.php`, igual). Atenção: `php -l` não pega mudança de sentido sem erro (`$$x[$i]`, `split` com
regex) — ver T-037 e T-040.
