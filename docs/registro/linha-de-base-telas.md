# Linha de base das telas de menu: PHP 5.6 x PHP 8.5

Medida em 14/11/2026 sobre o commit `5e74b3e4c` (ponta da integracao), com o comparador de telas descrito em
`sistema-telas.md`. Serve de ponto de partida antes de qualquer atualizacao do Laravel: o que mudar depois e comparado com
este resultado.

## Como foi medido

```
node <ferramentas>/suite.mjs python3 scratchpad/cmp.py --login-em 8160@ecidade_front3_56 \
  --a 8160@ecidade_front3_56 --b 8161@ecidade_front3_85 --menu --vigia --json menu.json --saida novas.tsv
```

- Runtimes: PHP 5.6 (`:8160`) e PHP 8.5 (`:8161`), cada um no seu container, mesmo banco `ecidade`, sessao de `dbseller`
  copiada para os dois, uma requisicao GET sem parametros por tela, corpo normalizado (sid, nomes temporarios, datas de PDF).
- Telas: as de menu das areas migradas (`atendcadarea` 1, 2, 3, 4, 8, 9 e 11: Tributario, Financeiro, Recursos Humanos,
  Patrimonial, Educacao, Saude e Configuracao) que existem no docroot. A Assistencia Social esta fora (sua integracao foi
  revertida por decisao do cliente). `iss4_siss002` e pulada (contata servico externo).
- Container que grava, com o vigia do banco: so podem mudar `db_logsacessa*`, `db_usuariosonline` e os tokens OAuth.

## Resultado

| Item | Valor |
|---|---|
| Data / commit | 14/11/2026 / `5e74b3e4c` |
| Telas de menu comparadas | **4.569** |
| Identicas (5.6 = 8.5) | **4.567** |
| Conhecidas (ja caracterizadas) | 0 |
| Novas | **2** (caracterizadas abaixo) |
| Timeouts | 0 |
| Vigia do banco | OK: so `db_logsacessa_202611_*` (535 linhas), `db_usuariosonline` (12.397) e `oauth_access_tokens`/`oauth_refresh_tokens` (104/70) mudaram |

Duracao: cerca de 3 h. Uma tentativa anterior foi interrompida em ~2.700 telas e refeita do zero; chegou as mesmas 2 novas.

## As 2 divergencias novas

Reproduzidas a mao (sessao nova, uma requisicao por lado, log do container).

1. **`con1_conrelinfo002.php` — defeito so do 8.5.** 5.6 responde 200 (7.326 B, pagina inicial); 8.5 responde 500
   (`ArgumentCountError: parse_str() expects exactly 2 arguments, 1 given`, `con1_conrelinfo002.php:34`:
   `parse_str($HTTP_SERVER_VARS["QUERY_STRING"]);`). O arquivo nao foi portado: a linha com 1 argumento segue como no 5.6.
   Correcao minima possivel: a mesma que as demais telas receberam (`parse_str($..., $__qs); extract($__qs);`). **Nao corrigida
   aqui**; fica como pendencia.
2. **`cai3_gerfinanc001.php` — artefato do ambiente, nao e defeito.** 5.6 e 8.5 dao 500 com textos diferentes
   ("Tabela de parametro (numpref) nao configurada" x "Erro interno"). O codigo do arquivo ja usa
   `parse_str($_SERVER['QUERY_STRING'], $__qs)`; quem executava era a copia antiga guardada em
   `extension/modification/data/cache/` (estado de execucao, ignorado pelo git), que ainda trazia `parse_str` de 1 argumento.
   Removida a copia, a tela sai **identica** nos dois runtimes. Lembrete: depois de trocar de branch, limpar esse cache antes
   de medir.

## Limites

So telas de menu, sem parametros (o uso real manda parametros). Relatorios (`SOMENTE_LEITURA=1`) e prefixos do `location`
fora do menu nao entram nesta linha de base.
