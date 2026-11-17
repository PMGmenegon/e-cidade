# Camada sistema: telas (T-011)

`scratchpad/cmp.py` compara as telas entre dois runtimes quaisquer. O uso legado (`cmp.py SID PREFIXO [SAIDA.tsv]`,
5.6 em :8080 x 8.5) continua igual.

## Uso

```
python3 scratchpad/cmp.py --login-em 8160@ecidade_front3_56 \
   --a 8160@ecidade_front3_56 --b 8161@ecidade_front3_85 \
   (--prefixo '^cem1_' | --telas lista.txt | --menu | --completa) --vigia [--json rel.json] [--saida novas.tsv]
```

- Lado: `[HOST:]PORTA@CONTAINER`. Seleção: `--prefixo` (regex), `--telas` (arquivo), `--menu` (telas de menu das áreas
  migradas, lidas do banco só com SELECT), `--completa` (prefixos do `location` + menu); as seleções se somam.
- `--vigia`: regra do cliente (13/11/2026). Tela de menu roda em container que grava, com `vigia-banco.sh`; só
  `db_logsacessa*`, `db_usuariosonline` e tokens OAuth podem mudar. Escrita indevida: saída 3. Relatório roda só em
  container `SOMENTE_LEITURA=1`, sem `--vigia`.
- Saída: 0 = nenhuma divergência nova; 1 = divergência ou timeout novo (tela, resumo dos dois lados, runtime, byte da
  primeira diferença); 2 = erro de uso; 3 = vigia acusou escrita.
- `scratchpad/sistema/divergencias_conhecidas.tsv` (tela, tipo, referência, motivo): divergência listada sai como
  `CONHECIDA` com a referência e não conta. Tela listada que fica idêntica sai como `RESOLVIDA?`.

## Áreas que entram

`--menu`/`--completa` usam `AREAS_MIGRADAS = (1, 2, 3, 4, 8, 9, 11)` (`atendcadarea`: Tributário, Financeiro, Recursos Humanos,
Patrimonial, Educação, Saúde e Configuração) e `PREFIXOS_LOCATION` (os prefixos do `location` do nginx, sem `soc`/`hab`).
**Assistência Social (área 15, `soc`/`hab`) está FORA de propósito:** a integração dela (T-001) foi revertida por decisão do
cliente em 13/11/2026 (revert `31e3e5e84`; será refeita à mão), então não há o que comparar. Se voltar, acrescentar `15` em
`AREAS_MIGRADAS` e `soc|hab` em `PREFIXOS_LOCATION`.

## Ligação à suíte (T-008)

`ecidade/tests/suite/rodar.sh` só roda arquivos PHPUnit (`camadas/*.lista`), então a camada `sistema.lista` **não foi ligada**:
fazê-lo exigiria editar o script da suíte, que a spec proíbe. A camada roda pela mesma trava de concorrência da suíte:

```
node /home/gustavo/git/ecidade-laravel/.quadro/ferramentas/suite.mjs \
  python3 scratchpad/cmp.py --login-em 8160@ecidade_front3_56 --a 8160@ecidade_front3_56 --b 8161@ecidade_front3_85 \
  --menu --vigia --json relatorio-sistema.json
```

## Limitação

`CONHECIDA` casa por **tela + tipo** (DIVERGE/TIMEOUT), sem comparar o conteúdo. Uma divergência conhecida que piore (por
exemplo, um erro novo no 8.5 na mesma tela) continua `CONHECIDA`. O relatório JSON traz o trecho de cada lado para conferir.

## Medição (13/11/2026, Front3, :8160 x :8161, vigia OK)

48 telas dos registros das áreas, sem lista de conhecidas: 22 idênticas, 26 divergentes (bib, cai2, edu1, edu4, lab, orc,
rec2, sau2, sys3, sys4). As 26 entraram no TSV, cada uma com o registro da área que a caracteriza; mais 5 de `docs/divergencias-conhecidas.md` (`iss4_issbasecaracteristicas001`, `agu1_aguaconsumo999`, `agu4_cancelaleituras_classe`, `fis1_sanitario004`, `edu4_exportarsituacaoaluno002`), confirmadas na bateria (5/5 divergem como descrito, vigia OK). O TSV tem 31 telas; a lista curada é `docs/divergencias-conhecidas.md`. Com o TSV: **22/48 idênticas, 26 conhecidas, 0 novas**, saída 0, vigia OK (só tabelas permitidas).
As 36 `tra` e `cai3_gerfinanc013` já estão idênticas; `mer_subitem004` só diverge em fim de semana
(`area-saude.md`) e não consta.

A lista é parcial: só as telas citadas pelos registros por nome. A linha de base completa é a T-016.
