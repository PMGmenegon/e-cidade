# Documentacao da migracao Laravel

Esta pasta organiza o trabalho de avaliacao e planejamento para migrar o e-Cidade da stack legada atual para uma versao moderna do Laravel e do PHP. Os documentos registram evidencias, riscos, decisoes que ainda precisam de responsavel e as validacoes futuras. Eles nao significam que a migracao foi iniciada ou concluida.

## Como navegar

- [Matriz de versoes e resolucao do Composer](matriz-versoes.md) (T-005, 12/11/2026): Laravel 12 e 13 x PHP 8.4 e 8.5 resolvidos de verdade numa copia descartavel; os 4 pacotes que impedem a resolucao e a alternativa de cada um. Scripts em [`matriz/`](matriz/).
- [Auditoria revisada do Composer](auditoria/composer-compatibilidade-revisada.md): resumo dos bloqueios de resolucao ja identificados, das dependencias sem compatibilidade demonstrada e dos testes ainda necessarios.
- [Plano de migracao](plano-de-migracao.md): fases propostas, dependencias entre atividades e criterios para avancar.
- [Decisoes pendentes](decisoes-pendentes.md): alternativas e evidencias necessarias antes de escolher um alvo ou substituir bibliotecas.
- [Compatibilidade do FrontController](compatibilidade-FrontController.md): como o `FrontController.php` despacha `api/vN/`, `v4/`, `rest/v1/` e o resto, e a compatibilidade de cada ponto de entrada (documento da branch `origin/laravel-upgrade`, com referencias aos registros que ja cobrem o assunto).
- [Silex (API V1), caminho de atualizacao e datas de suporte](silex-caminhos-e-suporte.md): 7 rotas e 33 arquivos da `api/V1`, opcoes manter/atualizar/substituir, versao a versao x salto direto e datas oficiais de Laravel 12/13 e PHP 8.4/8.5 (consulta de 12/11/2026).

## Documentos de referencia

O arquivo [`compatibilidade-composer.md`](../../compatibilidade-composer.md), na raiz do repositorio, e o relatorio anterior. Ele deve ser preservado como referencia historica e **nao deve ser substituido** pela auditoria revisada desta pasta. A versao revisada registra correcoes de classificacao e contexto da auditoria posterior.

O levantamento de descobertas feito por outro integrante da equipe ainda precisa ser incorporado. Na auditoria anterior, o documento esperado `docs/migracao-laravel/levantamento/descobertas-do-projeto.md` nao foi encontrado no workspace. Seu conteudo nao foi presumido; a integracao dessas descobertas permanece pendente ate que o arquivo ou seu conteudo seja disponibilizado.

## Estado

Esta pasta documenta uma avaliacao e um plano. Nenhuma instalacao ou atualizacao de dependencia, alteracao de codigo, migracao de banco ou execucao de testes foi realizada como parte desta documentacao.
