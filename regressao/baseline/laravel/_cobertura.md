# Cobertura de rotas (Laravel)

Rotas no inventario: **568**.

| origem | total | cobertas | nao cobertas |
|---|---:|---:|---:|
| laravel | 557 | 361 | 196 |
| rest | 4 | 0 | 4 |
| silex | 7 | 5 | 2 |

## Resposta da referencia (Laravel 5.4) nas rotas cobertas

2xx: 83  3xx: 0  4xx: 182  5xx: 101  sem baseline: 0

**5xx na referencia: 101.** Rota quebrada ou que precisa de dados em dev; o caso e IDENTICO nos dois lados mas termina INCONCLUSIVO (500 x 500): a rota nao foi exercitada, so o seu roteamento/erro. Lista:

- `rota:POST:/v4/api/assinador/obter-assinantes-portaria`
- `rota:POST:/v4/api/assinador/recuperar-pfx`
- `rota:POST:/v4/api/configuracao/assinantes`
- `rota:GET:/v4/api/configuracao/bancos`
- `rota:POST:/v4/api/configuracao/documento-assinado`
- `rota:GET:/v4/api/configuracao/documentos-assinar/assinante`
- `rota:POST:/v4/api/configuracao/documentos-assinar/atualizar-assinado-por`
- `rota:POST:/v4/api/configuracao/documentos-assinar/atualizar-assinantes`
- `rota:POST:/v4/api/configuracao/documentos-assinar/novo-documento`
- `rota:POST:/v4/api/configuracao/organograma/filtrar`
- `rota:POST:/v4/api/configuracao/relatorios-legais/upload/template`
- `rota:GET:/v4/api/configuracao/usuario/assinantes`
- `rota:GET:/v4/api/educacao/censo/tabelas-censo/areas-pos-graduacao`
- `rota:POST:/v4/api/educacao/escola/recursos-humanos/buscar-documento-pos-graducao`
- `rota:POST:/v4/api/educacao/escola/recursos-humanos/salvar-documento-pos-graducao`
- `rota:POST:/v4/api/educacao/escola/relatorios/emitirRelatorioTurmasAee`
- `rota:POST:/v4/api/educacao/secretaria/parametros/notificacoes`
- `rota:POST:/v4/api/financeiro/contabilidade/consulta/lancamento/conta-pcasp/documentos`
- `rota:POST:/v4/api/financeiro/contabilidade/consulta/lancamento/conta-pcasp/info`
- `rota:POST:/v4/api/financeiro/contabilidade/consulta/lancamento/conta-pcasp/recursos`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/consulta/orcamentario/despesa/ecidade`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/consulta/orcamentario/receita/ecidade`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/emitir/orcamentario/despesa/mapeamento`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/emitir/orcamentario/receita/mapeamento`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/emitir/pcasp/mapeamento`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/orcamentario/despesa/vincular`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/orcamentario/receita/vincular`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/pcasp/editar-estruturais`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/pcasp/salvar-conta-bancaria`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/pcasp/salvar-conta-caixa`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/pcasp/salvar-conta-extra`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/pcasp/salvar-outras-contas`
- `rota:POST:/v4/api/financeiro/contabilidade/plano-contas/pcasp/vincular`
- `rota:POST:/v4/api/financeiro/contabilidade/relatorio/atributos-plano-conas`
- `rota:POST:/v4/api/financeiro/contabilidade/relatorio/balancete-receita-por-complemento`
- `auth-sem-token`
- `rota:POST:/v4/api/financeiro/empenho/relatorio/retencoesEfdReinf`
- `rota:POST:/v4/api/financeiro/orcamento/cadastro/complemento/salvar`
- `rota:POST:/v4/api/financeiro/orcamento/relatorios/cotas-despesa`
- `rota:POST:/v4/api/financeiro/orcamento/relatorios/meta-arrecadacao`
- `rota:POST:/v4/api/financeiro/orcamento/relatorios/meta-x-cotas`
- `rota:POST:/v4/api/financeiro/orcamento/relatorios/siconfi-recursos-2022`
- `rota:POST:/v4/api/financeiro/planejamento/configuracao/salvar`
- `rota:POST:/v4/api/financeiro/planejamento/despesa/cronograma/buscar`
- `rota:POST:/v4/api/financeiro/planejamento/iniciativa-vincular-objetivo/buscar`
- `rota:POST:/v4/api/financeiro/planejamento/iniciativa-vincular-objetivo/vincular`
- `rota:POST:/v4/api/financeiro/planejamento/pib`
- `rota:GET:/v4/api/financeiro/planejamento/programas-estrategico`
- `rota:POST:/v4/api/financeiro/planejamento/programas-estrategico/salvar`
- `rota:POST:/v4/api/financeiro/planejamento/projecao-despesa/projecao`
- `rota:POST:/v4/api/financeiro/planejamento/projecao-despesa/salvar-projecao`
- `rota:POST:/v4/api/financeiro/planejamento/projecao/receita/atualizar/valor-exercicio`
- `rota:POST:/v4/api/financeiro/planejamento/receita/cronograma/buscar`
- `rota:POST:/v4/api/financeiro/planejamento/relatorios/cotas-despesa`
- `rota:POST:/v4/api/financeiro/planejamento/relatorios/por-elemento`
- `rota:POST:/v4/api/financeiro/planejamento/relatorios/programa-estrategico`
- `rota:POST:/v4/api/financeiro/planejamento/relatorios/programa-gestao`
- `rota:POST:/v4/api/financeiro/planejamento/relatorios/projecao-despesa-agrupado`
- `rota:POST:/v4/api/financeiro/planejamento/relatorios/projecao-despesa-agrupado-sintetico`
- `rota:POST:/v4/api/financeiro/planejamento/relatorios/projecao-despesa-conferencia-recurso`
- `rota:POST:/v4/api/financeiro/tesouraria/contatesouraria/buscar`
- `rota:POST:/v4/api/financeiro/tesouraria/relatorio/ExtratoContaBancaria`
- `rota:POST:/v4/api/integracoes/efd-reinf/configuracao/save`
- `rota:POST:/v4/api/patrimonial/licitacoes/itensBloqueados`
- `rota:POST:/v4/api/patrimonial/patrimonio/relatorio/transferencia-bens-aberto`
- `rota:POST:/v4/api/patrimonial/protocolo/documentos/atividades-executadas`
- `rota:POST:/v4/api/patrimonial/protocolo/documentos/buscar-por-identificador`
- `rota:POST:/v4/api/patrimonial/protocolo/documentos/conferir`
- `rota:POST:/v4/api/patrimonial/protocolo/documentos/salvar-documento-assinado`
- `rota:GET:/v4/api/patrimonial/protocolo/processo/andamento-padrao/campos-dinamicos/resposta`
- `rota:POST:/v4/api/patrimonial/protocolo/processo/andamento-padrao/campos-dinamicos/resposta`
- `rota:GET:/v4/api/recursos-humanos/pessoal/jetom/comissao`
- `rota:POST:/v4/api/recursos-humanos/pessoal/jetom/comissao/tiposessao/update`
- `rota:GET:/v4/api/recursos-humanos/pessoal/jetom/funcao/all`
- `rota:GET:/v4/api/recursos-humanos/pessoal/jetom/funcao/find`
- `rota:POST:/v4/api/recursos-humanos/rh/concessaodireitos/assentconcedeconfig`
- `rota:POST:/v4/api/recursos-humanos/rh/concessaodireitos/assentform`
- `rota:POST:/v4/api/recursos-humanos/rh/concessaodireitos/assentperc`
- `rota:POST:/v4/api/recursos-humanos/rh/concessaodireitos/concessaocalculo`
- `rota:POST:/v4/api/recursos-humanos/rh/concessaodireitos/concessaocalculolog`
- `rota:POST:/v4/api/recursos-humanos/rh/concessaodireitos/configuracao`
- `rota:POST:/v4/api/recursos-humanos/rh/concessaodireitos/gravaconcessaoassent`
- `rota:POST:/v4/api/recursos-humanos/rh/concessaodireitos/gravarconfiguracao`
- `rota:GET:/v4/api/saude/ambulatorial/parametros`
- `rota:POST:/v4/api/tributario/arrecadacao/pix/gerar`
- `rota:POST:/v4/api/tributario/issqn/redesim/inclusao-inscricao`
- `rota:POST:/v4/api/tributario/issqn/redesim/relatorio-inscricoes`
- `rota:GET:/v4/api/tributario/itbi/benfeitoria/padrao-construtivo`
- `rota:GET:/v4/oauth/authorize`
- `rota:POST:/v4/oauth/authorize`
- `rota:GET:/v4/oauth/clients`
- `rota:POST:/v4/oauth/clients`
- `rota:GET:/v4/oauth/personal-access-tokens`
- `rota:POST:/v4/oauth/personal-access-tokens`
- `rota:GET:/v4/oauth/scopes`
- `rota:POST:/v4/oauth/token/refresh`
- `rota:GET:/v4/oauth/tokens`
- `rota:POST:/api/v1/auth/login`
- `rota:GET:/api/v1/matriculaonline/emissaoProtocolo`
- `rota:POST:/api/v1/matriculaonline/inscricao`
- `rota:POST:/api/v1/tributario/recibo`

## Por caso (explica a diferenca rotas x casos)

Casos carregados: 381; com 5xx na referencia: 104 = 100 que terminam INCONCLUSIVO (500 x 500, nao exercitados) + 4 de rejeicao esperada (`espera_status`: IDENTICO, comportamento documentado do 5.4).

- rejeicao esperada: `auth-sem-token`
- rejeicao esperada: `auth-token-invalido`
- rejeicao esperada: `auth-token-expirado`
- rejeicao esperada: `auth-token-revogado`

Notas: rotas GET|HEAD sao exercitadas so por GET (HEAD nao e sondado); PUT|PATCH, se permitido, so por PUT. Rotas com metodo colapsado alem de HEAD: 0.

## Nao cobertas

- metodo destrutivo sem allowlist: 1
- parametro de caminho {cgm}: 1
- parametro de caminho {cgs}: 4
- parametro de caminho {client_id}: 2
- parametro de caminho {codcon}: 1
- parametro de caminho {codigoProcesso}: 1
- parametro de caminho {codigo_processo}: 1
- parametro de caminho {codigo}: 1
- parametro de caminho {codtipopix?}: 1
- parametro de caminho {cpf}: 3
- parametro de caminho {data?}: 1
- parametro de caminho {db90_codban?}: 1
- parametro de caminho {db90_codban}: 3
- parametro de caminho {eid}: 1
- parametro de caminho {escola}: 2
- parametro de caminho {estrutural}: 4
- parametro de caminho {exercicio}: 5
- parametro de caminho {file_id}: 4
- parametro de caminho {idRequisicaoExame}: 1
- parametro de caminho {idRequisicao}: 1
- parametro de caminho {idUsuario}: 1
- parametro de caminho {id}: 18
- parametro de caminho {importar}: 2
- parametro de caminho {instituicao}: 1
- parametro de caminho {instit}: 2
- parametro de caminho {k00_tipo}: 3
- parametro de caminho {k48_sequencial}: 3
- parametro de caminho {matricula}: 5
- parametro de caminho {nome}: 1
- parametro de caminho {numParcelamento}: 2
- parametro de caminho {numero_processo}: 2
- parametro de caminho {planejamento_id}: 1
- parametro de caminho {processar}: 3
- parametro de caminho {profissionalVacinacao}: 1
- parametro de caminho {profissional}: 2
- parametro de caminho {relatorio}: 1
- parametro de caminho {rg}: 1
- parametro de caminho {sessao}: 2
- parametro de caminho {tipo?}: 1
- parametro de caminho {tipoPlano}: 1
- parametro de caminho {tipoProcesso}: 1
- parametro de caminho {tipo_processo}: 3
- parametro de caminho {tipo}: 3
- parametro de caminho {token_id}: 2
- parametro de caminho {turmaOrigem}: 1
- parametro de caminho {turma}: 2
- parametro de caminho {vacina}: 1
- rota perigosa: 97

| origem | metodo | uri | motivo |
|---|---|---|---|
| laravel | GET|HEAD | `/v4/api/assinador/obter-arquivo-base64/{eid}` | parametro de caminho {eid}: nao se envia id real |
| laravel | POST | `/v4/api/assinador/obter-dados-arquivo` | rota perigosa (arquiv): nao e sondada |
| laravel | POST | `/v4/api/assinador/salvar-arquivo-tmp` | rota perigosa (arquiv): nao e sondada |
| laravel | DELETE | `/v4/api/configuracao/assinantes/{file_id}` | parametro de caminho {file_id}: nao se envia id real |
| laravel | POST | `/v4/api/configuracao/banco-pix/atualizar/{db90_codban}` | parametro de caminho {db90_codban}: nao se envia id real |
| laravel | DELETE | `/v4/api/configuracao/banco-pix/excluir/{db90_codban}` | parametro de caminho {db90_codban}: nao se envia id real |
| laravel | POST | `/v4/api/configuracao/banco-pix/validar/{db90_codban?}` | parametro de caminho {db90_codban?}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/configuracao/banco-pix/{db90_codban}` | parametro de caminho {db90_codban}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/configuracao/documentos-assinar/documento/{file_id}/assinado-por` | parametro de caminho {file_id}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/configuracao/documentos-assinar/documento/{file_id}/assinantes` | parametro de caminho {file_id}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/configuracao/documentos-assinar/{file_id}` | parametro de caminho {file_id}: nao se envia id real |
| laravel | POST | `/v4/api/configuracao/entrega-continua/migrate` | rota perigosa (migrate): nao e sondada |
| laravel | POST | `/v4/api/configuracao/instituicao/departamento-principal` | rota perigosa (provada ao vivo): UPDATE em db_config com corpo vazio (200) |
| laravel | GET|HEAD | `/v4/api/configuracao/instituicao/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/configuracao/menu/permissoes/saude/duplicar` | rota perigosa (duplic): nao e sondada |
| laravel | GET|HEAD | `/v4/api/configuracao/organograma/{instit}` | parametro de caminho {instit}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/configuracao/organograma/{instit}/{departamento}` | parametro de caminho {instit}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/configuracao/relatorios-legais/periodos/{relatorio}` | parametro de caminho {relatorio}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/configuracao/usuario/{idUsuario}/assinantes` | parametro de caminho {idUsuario}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/educacao/escola/calendario/{escola}` | parametro de caminho {escola}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/educacao/escola/matriculas-por-turma/{turma}/{etapa}` | parametro de caminho {turma}: nao se envia id real |
| laravel | POST | `/v4/api/educacao/escola/profissional/excluir-vacinacao/{profissionalVacinacao}` | parametro de caminho {profissionalVacinacao}: nao se envia id real |
| laravel | POST | `/v4/api/educacao/escola/profissional/{profissional}/salvar-vacinacao` | parametro de caminho {profissional}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/educacao/escola/profissional/{profissional}/vacinas` | parametro de caminho {profissional}: nao se envia id real |
| laravel | POST | `/v4/api/educacao/escola/recursos-humanos/excluir-documento-pos-graducao` | rota perigosa (exclu): nao e sondada |
| laravel | POST | `/v4/api/educacao/escola/recursos-humanos/excluir-formacao-superior-profissional` | rota perigosa (exclu): nao e sondada |
| laravel | GET|HEAD | `/v4/api/educacao/escola/recursos-humanos/profissionais-com-superior/{escola}/{ativos}` | parametro de caminho {escola}: nao se envia id real |
| laravel | POST | `/v4/api/educacao/escola/recursos-humanos/salvar-formacao-superior-profissional` | rota perigosa (provada ao vivo): INSERT DEFAULT VALUES em escola.rhformacaosuperior com corpo vazio (500) |
| laravel | GET|HEAD | `/v4/api/educacao/escola/regencias-turmas/{turmaOrigem}/{turmaDestino}/{etapa}` | parametro de caminho {turmaOrigem}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/educacao/escola/turma/{codigo}` | parametro de caminho {codigo}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/educacao/escola/vacinas/{vacina}` | parametro de caminho {vacina}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/educacao/escola/vagas-por-turma/{turma}` | parametro de caminho {turma}: nao se envia id real |
| laravel | POST | `/v4/api/educacao/secretaria/tipo-base/excluir` | rota perigosa (exclu): nao e sondada |
| laravel | POST | `/v4/api/educacao/secretaria/tipo-base/salvar` | rota perigosa (provada ao vivo): INSERT em secretariadeeducacao.tipobase com corpo vazio (500) |
| laravel | POST | `/v4/api/financeiro/contabilidade/BalancetesMensais/balancete-mensal-anexo1` | rota perigosa (processar): nao e sondada |
| laravel | POST | `/v4/api/financeiro/contabilidade/importar/msc` | rota perigosa (import): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/contabilidade/plano-contas/emitir/orcamentario/{tipoPlano}/{origem}/{exercicio}` | parametro de caminho {tipoPlano}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/contabilidade/plano-contas/emitir/pcasp/{tipo}/{exercicio}` | parametro de caminho {tipo}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/exclusao-geral/orcamentario/despesa` | rota perigosa (exclu): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/contabilidade/plano-contas/exclusao-geral/orcamentario/despesa/{estrutural}/{exercicio}` | parametro de caminho {estrutural}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/exclusao-geral/orcamentario/receita` | rota perigosa (exclu): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/contabilidade/plano-contas/exclusao-geral/orcamentario/receita/{estrutural}/{exercicio}` | parametro de caminho {estrutural}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/exclusao-geral/pcasp` | rota perigosa (exclu): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/contabilidade/plano-contas/exclusao-geral/pcasp/{estrutural}/{exercicio}` | parametro de caminho {estrutural}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/importar/orcamentario/despesa` | rota perigosa (import): nao e sondada |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/importar/orcamentario/receita` | rota perigosa (import): nao e sondada |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/importar/pcasp` | rota perigosa (import): nao e sondada |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/orcamentario/despesa/desvincular` | rota perigosa (desvincul): nao e sondada |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/orcamentario/receita/desvincular` | rota perigosa (desvincul): nao e sondada |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/pcasp/conta-corrente/remover` | rota perigosa (remov): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/contabilidade/plano-contas/pcasp/conta-corrente/{codcon}/{exercicio}` | parametro de caminho {codcon}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/contabilidade/plano-contas/pcasp/estrural-existe/{estrutural}/{exercicio}` | parametro de caminho {estrutural}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/contabilidade/plano-contas/pcasp/remover-reduzido` | rota perigosa (remov): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/contabilidade/procedimento/encerramento-periodo-contabil/{instituicao}` | parametro de caminho {instituicao}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/contabilidade/relatorio-disponibilidade-recurso` | rota perigosa (processar): nao e sondada |
| laravel | POST | `/v4/api/financeiro/contabilidade/relatorio/notificacao-recebimento-recursos-federais` | rota perigosa (processar): nao e sondada |
| laravel | POST | `/v4/api/financeiro/orcamento/acompanhamento/cronograma/despesa/recalcular` | rota perigosa (recalcul): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/orcamento/acompanhamento/cronograma/despesa/{exercicio}` | parametro de caminho {exercicio}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/orcamento/acompanhamento/cronograma/receita/recalcular` | rota perigosa (recalcul): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/orcamento/acompanhamento/cronograma/receita/{exercicio}` | parametro de caminho {exercicio}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/orcamento/cadastro/complemento/excluir` | rota perigosa (exclu): nao e sondada |
| laravel | POST | `/v4/api/financeiro/orcamento/cadastro/especificacao-recurso/excluir` | rota perigosa (exclu): nao e sondada |
| laravel | POST | `/v4/api/financeiro/orcamento/cadastro/recurso/excluir` | rota perigosa (exclu): nao e sondada |
| laravel | POST | `/v4/api/financeiro/orcamento/cadastro/recurso/inativar` | rota perigosa (inativ): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/orcamento/cadastro/recurso/{id}/{exercicio}` | parametro de caminho {id}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/orcamento/cadastro/recursos/inativar/{exercicio}` | parametro de caminho {exercicio}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/orcamento/de-para-siconfi/exportar/{exercicio}` | parametro de caminho {exercicio}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/orcamento/de-para-siconfi/importar` | rota perigosa (import): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/orcamento/recursos/{data?}` | parametro de caminho {data?}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/orcamento/utiliza-decimal/{exercicio}` | parametro de caminho {exercicio}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/planejamento/abrangencia/excluir` | rota perigosa (exclu): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/area-resultado/excluir` | rota perigosa (exclu): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/consulta/plano/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/consulta/planos-em-desenvolvimento/{tipo?}` | parametro de caminho {tipo?}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/consulta/planos/{tipo}` | parametro de caminho {tipo}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/consulta/planos/{tipo}/{status}` | parametro de caminho {tipo}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/consulta/situacoes/movimentar/plano/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/planejamento/despesa/cronograma/recalcular` | rota perigosa (recalcul): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/despesa/cronograma/recalcularGeral` | rota perigosa (recalcul): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/despesa/detalhamento/remover` | rota perigosa (remov): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/despesa/detalhamento/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/planejamento/indicador-programa/remover` | rota perigosa (remov): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/iniciativa/regionalizacoes/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/planejamento/iniciativa/remover` | rota perigosa (remov): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/iniciativa/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/planejamento/meta-objetivo/remover` | rota perigosa (remov): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/objetivo-estrategico/excluir` | rota perigosa (exclu): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/objetivo-programa/remover` | rota perigosa (remov): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/orcamento/cancelar` | rota perigosa (cancel): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/pib/{planejamento_id}` | parametro de caminho {planejamento_id}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/planejamento/programas-estrategico/remover` | rota perigosa (remov): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/programas-estrategico/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/planejamento/projecao-despesa/recalcular` | rota perigosa (recalcul): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/projecao/receita/recalcular` | rota perigosa (recalcul): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/recalcular-valores-sinteticos` | rota perigosa (recalcul): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/receita/cronograma/recalcular` | rota perigosa (recalcul): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/receita/previsao/remover` | rota perigosa (remov): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/receita/previsao/removerNaturezas` | rota perigosa (remov): nao e sondada |
| laravel | GET|HEAD | `/v4/api/financeiro/planejamento/receita/previsao/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/planejamento/regionalizacao/excluir` | rota perigosa (exclu): nao e sondada |
| laravel | POST | `/v4/api/financeiro/planejamento/remove` | rota perigosa (remov): nao e sondada |
| laravel | POST | `/v4/api/financeiro/tesouraria/importar` | rota perigosa (import): nao e sondada |
| laravel | POST | `/v4/api/financeiro/tesouraria/inconsistente` | rota perigosa (processar): nao e sondada |
| laravel | POST | `/v4/api/financeiro/tesouraria/processar` | rota perigosa (processar): nao e sondada |
| laravel | POST | `/v4/api/financeiro/tesouraria/processar-implantacao` | rota perigosa (processar): nao e sondada |
| laravel | POST | `/v4/api/financeiro/tesouraria/processar-implantacao-por-conta` | rota perigosa (processar): nao e sondada |
| laravel | DELETE | `/v4/api/financeiro/tesouraria/processar/{processar}` | parametro de caminho {processar}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/financeiro/tesouraria/processar/{processar}` | parametro de caminho {processar}: nao se envia id real |
| laravel | PUT|PATCH | `/v4/api/financeiro/tesouraria/processar/{processar}` | parametro de caminho {processar}: nao se envia id real |
| laravel | POST | `/v4/api/financeiro/tesouraria/relatorio/tef` | rota perigosa (arquiv): nao e sondada |
| laravel | POST | `/v4/api/integracoes/efd-reinf/unidaderesponsavel/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/patrimonial/licitacoes/integracaocomprasbr/importar` | rota perigosa (import): nao e sondada |
| laravel | POST | `/v4/api/patrimonial/licitacoes/tramita/importar` | rota perigosa (import): nao e sondada |
| laravel | POST | `/v4/api/patrimonial/ouvidoria/atendimento/atendimento/aprovarProcessoOuvidoria` | rota perigosa (aprov): nao e sondada |
| laravel | POST | `/v4/api/patrimonial/ouvidoria/atendimento/atendimento/rejeitarProcessoOuvidoria` | rota perigosa (rejeit): nao e sondada |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/processo-eletronico/detalhe-processo/{codigoProcesso}` | parametro de caminho {codigoProcesso}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/processo-eletronico/mensagens/{numero_processo}` | parametro de caminho {numero_processo}: nao se envia id real |
| laravel | POST | `/v4/api/patrimonial/ouvidoria/atendimento/processo-eletronico/savevisualizacao/{numero_processo}` | parametro de caminho {numero_processo}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/processo-eletronico/servidor/{cpf}/tipoprocesso/{tipoProcesso}` | parametro de caminho {cpf}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/servidor/anos-trabalhados/{matricula}` | parametro de caminho {matricula}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/servidor/assentamentos/{matricula}` | parametro de caminho {matricula}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/servidor/averbacoes/{matricula}` | parametro de caminho {matricula}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/servidor/comprovante-irrf/{matricula}/ano/{ano}` | parametro de caminho {matricula}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/servidor/ferias/{matricula}` | parametro de caminho {matricula}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/ouvidoria/atendimento/servidor/matriculas/{cpf}` | parametro de caminho {cpf}: nao se envia id real |
| laravel | POST | `/v4/api/patrimonial/protocolo/atividades-execucao/excluir-vinculo` | rota perigosa (exclu): nao e sondada |
| laravel | GET|HEAD | `/v4/api/patrimonial/protocolo/atividades-execucao/tipo-processo/{tipoProcesso}` | parametro de caminho {tipoProcesso}: nao se envia id real |
| laravel | POST | `/v4/api/patrimonial/protocolo/documentos/arquivar` | rota perigosa (arquiv): nao e sondada |
| laravel | POST | `/v4/api/patrimonial/protocolo/documentos/devolver` | rota perigosa (devolv): nao e sondada |
| laravel | GET|HEAD | `/v4/api/patrimonial/protocolo/processo/andamento-padrao/campos-dinamicos/{codigo_processo}` | parametro de caminho {codigo_processo}: nao se envia id real |
| laravel | DELETE | `/v4/api/patrimonial/protocolo/processo/{tipo_processo}/andamento-padrao/campos-dinamicos` | parametro de caminho {tipo_processo}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/patrimonial/protocolo/processo/{tipo_processo}/andamento-padrao/campos-dinamicos` | parametro de caminho {tipo_processo}: nao se envia id real |
| laravel | POST | `/v4/api/patrimonial/protocolo/processo/{tipo_processo}/andamento-padrao/campos-dinamicos/{ordem}` | parametro de caminho {tipo_processo}: nao se envia id real |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/contra-cheques/processar-competencia` | rota perigosa (processar): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/comissao/config/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/comissao/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/comissao/funcao/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/comissao/permissao/delete` | rota perigosa (delete): nao e sondada |
| laravel | GET|HEAD | `/v4/api/recursos-humanos/pessoal/jetom/comissao/permissao/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/comissao/servidor/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/comissao/tiposessao/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/funcao/deletar` | rota perigosa (delete): nao e sondada |
| laravel | GET|HEAD | `/v4/api/recursos-humanos/pessoal/jetom/importar` | rota perigosa (import): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/importar` | rota perigosa (import): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/importar/arquivoponto` | rota perigosa (import): nao e sondada |
| laravel | DELETE | `/v4/api/recursos-humanos/pessoal/jetom/importar/{importar}` | parametro de caminho {importar}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/recursos-humanos/pessoal/jetom/importar/{importar}` | parametro de caminho {importar}: nao se envia id real |
| laravel | POST | `/v4/api/recursos-humanos/pessoal/jetom/sessao/processar` | rota perigosa (processar): nao e sondada |
| laravel | DELETE | `/v4/api/recursos-humanos/pessoal/jetom/sessao/{sessao}` | parametro de caminho {sessao}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/recursos-humanos/pessoal/jetom/sessao/{sessao}` | parametro de caminho {sessao}: nao se envia id real |
| laravel | POST | `/v4/api/recursos-humanos/rh/concessaodireitos/deleteassentconcedeconfig` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/rh/concessaodireitos/deleteassentform` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/rh/concessaodireitos/deleteassentperc` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/rh/concessaodireitos/deleteconfiguracao` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/recursos-humanos/rh/concessaodireitos/processar` | rota perigosa (processar): nao e sondada |
| laravel | GET|HEAD | `/v4/api/saude/ambulatorial/cgs/familiamicroarea/{cgs}` | parametro de caminho {cgs}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/saude/ambulatorial/cgs/{cgs}` | parametro de caminho {cgs}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/saude/ambulatorial/consulta/problemaspaciente/by-paciente/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/saude/ambulatorial/procedimento/acompanhamento-acs/delete` | rota perigosa (delete): nao e sondada |
| laravel | GET|HEAD | `/v4/api/saude/ambulatorial/procedimento/acompanhamento-acs/paciente/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/saude/ambulatorial/procedimento/acompanhamento-acs/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/saude/ambulatorial/procedimento/problemaspaciente/apagar` | rota perigosa (apag): nao e sondada |
| laravel | GET|HEAD | `/v4/api/saude/esf/consulta/equipes/by-unidade/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/saude/esf/vacinas/by-paciente/{cgs}` | parametro de caminho {cgs}: nao se envia id real |
| laravel | POST | `/v4/api/saude/farmacia/cadastro/demanda-reprimida/delete` | rota perigosa (delete): nao e sondada |
| laravel | GET|HEAD | `/v4/api/saude/farmacia/consulta/demanda-reprimida/by-paciente/{cgs}` | parametro de caminho {cgs}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/saude/laboratorio/exames/requisicao/{idRequisicao}` | parametro de caminho {idRequisicao}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/saude/laboratorio/exames/resultado/{idRequisicaoExame}` | parametro de caminho {idRequisicaoExame}: nao se envia id real |
| laravel | POST | `/v4/api/tributario/arrecadacao/controle-parcelamentos-vencidos/agendamento/desativar` | rota perigosa (desativ): nao e sondada |
| laravel | POST | `/v4/api/tributario/arrecadacao/controle-parcelamentos-vencidos/agendamento/salvar` | rota perigosa (provada ao vivo): INSERT em arrecadacao.controleparc_agendamento com corpo vazio (500) |
| laravel | GET|HEAD | `/v4/api/tributario/arrecadacao/controle-parcelamentos-vencidos/buscar/{numParcelamento}` | parametro de caminho {numParcelamento}: nao se envia id real |
| laravel | POST | `/v4/api/tributario/arrecadacao/controle-parcelamentos-vencidos/processar/{numParcelamento}` | parametro de caminho {numParcelamento}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/tributario/arrecadacao/controle-parcelamentos-vencidos/tipo-parcelamento/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/tributario/arrecadacao/regra-emissao/atualizar/{k48_sequencial}` | parametro de caminho {k48_sequencial}: nao se envia id real |
| laravel | DELETE | `/v4/api/tributario/arrecadacao/regra-emissao/excluir/{k48_sequencial}` | parametro de caminho {k48_sequencial}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/tributario/arrecadacao/regra-emissao/{k48_sequencial}` | parametro de caminho {k48_sequencial}: nao se envia id real |
| laravel | POST | `/v4/api/tributario/arrecadacao/tef/baixar-debito` | rota perigosa (baix): nao e sondada |
| laravel | POST | `/v4/api/tributario/arrecadacao/tef/comprovante-desfazimento` | rota perigosa (desfaz): nao e sondada |
| laravel | POST | `/v4/api/tributario/arrecadacao/tef/desfazer-operacao` | rota perigosa (desfaz): nao e sondada |
| laravel | POST | `/v4/api/tributario/arrecadacao/tipo-debito/atualizar/{k00_tipo}` | parametro de caminho {k00_tipo}: nao se envia id real |
| laravel | DELETE | `/v4/api/tributario/arrecadacao/tipo-debito/excluir/{k00_tipo}` | parametro de caminho {k00_tipo}: nao se envia id real |
| laravel | POST | `/v4/api/tributario/arrecadacao/tipo-debito/validar/{codtipopix?}` | parametro de caminho {codtipopix?}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/tributario/arrecadacao/tipo-debito/{k00_tipo}` | parametro de caminho {k00_tipo}: nao se envia id real |
| laravel | GET|HEAD | `/v4/api/tributario/cadastro/dados-isencao/{id}` | parametro de caminho {id}: nao se envia id real |
| laravel | POST | `/v4/api/tributario/issqn/alvaraeventos/alvaraevento/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/tributario/issqn/alvaraeventos/ordemservico/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/tributario/issqn/alvaraeventos/ordemservico/desprocessar` | rota perigosa (desprocess): nao e sondada |
| laravel | POST | `/v4/api/tributario/issqn/alvaraeventos/ordemservico/processar` | rota perigosa (processar): nao e sondada |
| laravel | POST | `/v4/api/tributario/issqn/veiculos/condutorauxiliar/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/tributario/issqn/veiculos/veiculo/delete` | rota perigosa (delete): nao e sondada |
| laravel | POST | `/v4/api/tributario/issqn/veiculos/veiculo/desprocessar` | rota perigosa (desprocess): nao e sondada |
| laravel | DELETE | `/v4/oauth/authorize` | metodo destrutivo sem allowlist: DELETE/PUT/PATCH nao sao sondados |
| laravel | DELETE | `/v4/oauth/clients/{client_id}` | parametro de caminho {client_id}: nao se envia id real |
| laravel | PUT | `/v4/oauth/clients/{client_id}` | parametro de caminho {client_id}: nao se envia id real |
| laravel | DELETE | `/v4/oauth/personal-access-tokens/{token_id}` | parametro de caminho {token_id}: nao se envia id real |
| laravel | DELETE | `/v4/oauth/tokens/{token_id}` | parametro de caminho {token_id}: nao se envia id real |
| rest | GET|HEAD | `/rest/v1/enderecopessoa/{cgm}` | parametro de caminho {cgm}: nao se envia id real |
| rest | GET|HEAD | `/rest/v1/pesquisapessoa/nro_cpf/{cpf}` | parametro de caminho {cpf}: nao se envia id real |
| rest | GET|HEAD | `/rest/v1/pesquisapessoa/nro_rg/{rg}` | parametro de caminho {rg}: nao se envia id real |
| rest | GET|HEAD | `/rest/v1/pesquisapessoa/txt_nome/{nome}/{tp_pesquisa?}` | parametro de caminho {nome}: nao se envia id real |
| silex | GET | `/api/v1/configuracao/formulario/{id}/instituicao/{instituicao}` | parametro de caminho {id}: nao se envia id real |
| silex | GET | `/api/v1/protocolo/cgm/{id}` | parametro de caminho {id}: nao se envia id real |
