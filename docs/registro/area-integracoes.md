# Integrações (EFD-Reinf): migração do PHP 7.4 (PR #8) para o 8.5

Branch `integracoes/8.5`, criada da `base-php85` depois do PR #39 (núcleo).

## 1. Escopo (22/11/2026)

No menu, a área **DB:INTEGRAÇÕES** (`atendcadarea` 16) tem um único módulo, o **EFD-Reinf** (`db_modulos` 228077).
São 14 entradas, em 13 telas:

| Telas | Arquivos |
|---|---|
| do EFD-Reinf | `edf04_r1070_processos001`, `efd01_preenchimentoexclusaoeventos`, `efd04_r2010_servicos_tomados001`, `efd04_r2020_servicos_prestados001`, `efd04_r2099_fechamento_periodicos001`, `efd4_configuracaoenvio001`, `efd4_efdreinfconfiguracao001`, `efd4_unidaderesponsavel001` |
| do eSocial e do SPED, abertas com `?integracao=1` | `eso01_agendamentoenvio` (2 entradas), `eso02_situacaoevento001`, `eso4_enviocertificado001`, `sped02_preenchimento`, `sped04_retornoevento001` |

As telas carregam, além do núcleo:
- **7 RPCs:** `efd02_retencoesservicostomados`, `efd4_configuracaoenvio`, `eso02_situacaoevento001`, `eso4_esocialapi`,
  `sped02_preenchimento`, `spedapi` e `spedretorno`;
- **outros arquivos próprios:** `func_efd_processos`, `func_efd_servicos_prestados` e `forms/db_frmsituacaoevento.php`;
- **classes:** `src/Integracao/Sped` (20), `app/Domain/Integracoes` (10) e `src/RecursosHumanos/ESocial` (253).

Ficam fora deste módulo:
- `src/RecursosHumanos/ESocial`, que pela tabela de áreas é do Pessoal (RH);
- as classes de dados e buscas genéricas compartilhadas: `db_cgm_classe`, `db_db_config_classe`, `func_cgm*` e
  `func_selecao`.

Antes deste trabalho, nenhum commit desde a `base-php74` tinha mexido nessas telas. Nenhum arquivo estava reservado
ou concluído no quadro, e as siglas `efd`, `edf`, `eso` e `sped` não têm área na tabela do grupo.

## 2. Medição

- **Sintaxe:** `php -l` passa nos dois runtimes em todo o escopo (319 arquivos, com as classes do RH).
- **Telas:** as 14 entradas do menu saem idênticas no 7.4 e no 8.5.
- **RPCs:** foram chamadas nos dois runtimes as 15 ações de leitura, com a mesma sessão e o 7.4 chamado duas vezes
  para separar o que muda sozinho. Todas saíram idênticas: `buscar*`, `consulta*`, `get*`, `inicializar`, `gerar*`.
  Ficaram de fora as ações que gravam ou chamam serviço externo: `salvar`, `enviarEventosParaApi`,
  `agendarEnvioLote`, `atualizaRegistro` e a `consulta` do `spedapi`.
  - Com dados reais: `getTipos`, `getTiposRetorno` e `getEmpregadores` devolvem os eventos e a prefeitura.
  - Com mensagem de negócio: as demais param em "nenhum registro" ou "configurar acesso ao eSocial". O banco de teste
    não tem o eSocial configurado.
- **Busca de padrões do MCP** (com os ruidosos) nos 66 arquivos próprios:
  - `count_null`: 11 ocorrências. Só uma conta algo que pode não ser lista: a resposta da API no `consultaStatus`.
    As outras contam arrays criados no próprio código ou retornos que são sempre array; três delas os RPCs exercitaram
    sem erro.
  - `${}` em strings (4) e parâmetro tipado com `null` implícito (1): no 8.5 só geram aviso de obsoleto, sem efeito
    na resposta com `display_errors` desligado.
  - `== ""` (40): só nas classes compartilhadas `db_cgm_classe` e `db_db_config_classe`, de outras áreas.

## 3. Lote 1 — `sizeof()` da resposta da API (22/11/2026)

`eso02_situacaoevento001.RPC.php:434` (`consultaStatus`) conta o retorno de `ESocial::request()`, que é o
`json_decode` da resposta da API:
- `null` (corpo vazio ou inválido) contava 0 no 7.4 e lança `TypeError` no 8;
- um objeto JSON contava 1 no 7.4 e também lança `TypeError` no 8.

A forma nova conta 0 para `null` e 1 para o que não é contável, como o `count()` do 7.4.

Prova:
- **Forma:** caracterizada com `null`, objeto, lista, lista vazia, JSON inválido e vazio. O original no 7.4 é igual
  ao novo no 7.4 e no 8.5.
- **8.5:** as 14 entradas do menu e as 15 ações de leitura dos RPCs continuam idênticas no 7.4 e no 8.5.
- **7.4:** as respostas dos RPCs ficaram iguais byte a byte antes e depois.
- **Alcance:** o caminho corrigido só roda com o eSocial configurado e a API respondendo, o que não existe no banco
  de teste. A forma foi provada direto, não pela tela.

No quadro, foram concluídos os 22 arquivos exercitados pela medição: as 13 telas, 6 RPCs, as duas buscas
`func_efd_*` e o formulário. Não foram concluídos:
- o `spedapi.RPC.php`, que só tem a ação que chama serviço externo;
- as classes de `src/Integracao/Sped` e `app/Domain/Integracoes`, que passaram só pela análise estática. As de `app/`
  rodam sobre o Laravel, cuja migração é do grupo Laravel.

## 4. O que não foi coberto

- As ações que gravam (preencher, agendar e enviar eventos) e as que dependem da API do eSocial ou do SPED. Exigem
  ambiente com certificado e API, e a gravação real em contêiner próprio com o vigia do banco, como manda a regra.
- As rotas Laravel de `app/Domain/Integracoes/EFDReinf`, que dependem do porte do Laravel 13.
