# Inventário do código próprio do Laravel contra as quebras do 5.4 até o 13

Consulta de 13/11/2026. O alvo (Laravel 13) já está decidido; este inventário serve a qualquer caminho de atualização (versão a versão ou
salto direto) e **não muda nenhum código**: ele lista, para cada quebra documentada nos guias oficiais, onde o código próprio do e-Cidade a
usa (`arquivo:linha`) ou que não usa (zero aparece como zero), e propõe como agrupar o trabalho em tarefas pequenas.

Não repete a matriz de pacotes (`matriz-versoes.md`) nem a estimativa por caminho (`silex-caminhos-e-suporte.md`); parte delas.

## 1. Fontes e método

- **Guias** (`upgrade.md` de cada branch de `github.com/laravel/docs`, consultados em 13/11/2026): `5.5`, `5.6`, `5.7`, `5.8`, `6.x`, `7.x`,
  `8.x`, `9.x`, `10.x`, `11.x`, `12.x`, `13.x` — por exemplo `https://raw.githubusercontent.com/laravel/docs/13.x/upgrade.md`. Cada título de
  seção vira um item: **599 itens** nos 12 guias.
- **Código próprio varrido** (`ecidade/`): `app/`, `routes/`, `configuration/` (a pasta de configuração do Laravel do projeto; `App\Application`
  sobrescreve `configPath()`), `bootstrap/`, `database/`, `public/`, `tests/` e o `composer.json`. O legado procedural (`libs/`, `classes/`,
  `model/`, telas) e a API Silex (`api/`) ficam de fora, salvo nas contagens de pacotes (seção 5).
- **Varredura:** `scratchpad/inventario_laravel.py` + `scratchpad/inventario_laravel_padroes.py`: uma expressão regular por item, aplicada
  linha a linha (arquivos lidos como ISO-8859-1). Tipo **uso** = a expressão acha o recurso; **sinal** = indício que precisa de olho;
  **config** = chave de configuração. Itens que não são código (versão de PHP, instalador, títulos de grupo) e itens não varríveis por
  regex têm disposição explícita (`NAO APLICA` / `MANUAL`) e motivo. Todos os 599 itens, com padrão ou motivo, estão em
  `inventario-codigo-proprio-itens.tsv`.
- **Limite:** regex acha texto, não semântica. "NAO USA" é ausência do padrão (chamada dinâmica não aparece); "USA" com tipo `sinal` pode
  ser falso positivo. Conferência à mão de 5 itens contra `grep -a` independente: `env()` fora da configuração (20 em 9 arquivos),
  `$dates` (5), `belongsToMany` (30), facade `Input` (0) e `Cache::put` (4) — todos batem. (`grep` sem `-a` pula os arquivos
  ISO-8859-1 e dá números menores.)

## 2. O que existe no código próprio

| Item | Quantidade |
|---|---|
| `app/` | 1.259 arquivos `.php`, 123.120 linhas (1.211 em `app/Domain/`, por módulo) |
| `routes/` | 119 arquivos, 1.806 linhas; 787 chamadas `Route::` em 35 arquivos |
| **Rotas servidas pelo Laravel** | **561** (`php artisan route:list` no 5.6: GET 186, POST 361, DELETE 12, PUT 2). O número "138" de registros antigos está defasado |
| `configuration/` | 11 arquivos (`app`, `auth`, `broadcasting`, `cache`, `database`, `filesystems`, `mail`, `queue`, `services`, `session`, `view`), 1.155 linhas |
| `bootstrap/` e `public/` | 3 + 1 arquivos |
| Providers | 6 em `app/Providers/` (7 classes que estendem `ServiceProvider` em `app/`) |
| Middlewares | 15 em `app/Http/Middleware/` |
| Controllers | 5 em `app/Http/Controllers/` + 126 em `app/Domain/**/Controllers/` |
| Form requests | 86 (`extends FormRequest`) |
| Models Eloquent | 325 (`extends Model`) |
| Jobs / commands | 2 em `app/Jobs/` / 5 em `app/Console/Commands/` |
| Policies / gates | 1 arquivo com `Gate::` ou `Policy` |
| Mailables / notifications | 0 |
| Migrations do Laravel | 452 em `database/migrations/` (+ `database/seeds`, `database/factories/ModelFactory.php`) |
| Testes | 54 arquivos `.php`, 5.733 linhas em `tests/` |
| Funções globais próprias (`app/Helpers`, autoload `files`) | 29, **nenhuma** com nome de helper atual ou removido do Laravel |

## 3. Resultado por guia

| Guia (de → para) | Itens | Usa | Não usa | Não se aplica | Manual |
|---|---|---|---|---|---|
| 5.4 → 5.5 | 59 | 16 | 19 | 20 | 4 |
| 5.5 → 5.6 | 45 | 4 | 15 | 21 | 5 |
| 5.6 → 5.7 | 57 | 7 | 19 | 29 | 2 |
| 5.7 → 5.8 | 76 | 22 | 26 | 26 | 2 |
| 5.8 → 6 | 51 | 14 | 16 | 20 | 1 |
| 6 → 7 | 31 | 7 | 13 | 10 | 1 |
| 7 → 8 | 42 | 8 | 16 | 17 | 1 |
| 8 → 9 | 77 | 6 | 47 | 23 | 1 |
| 9 → 10 | 37 | 7 | 12 | 17 | 1 |
| 10 → 11 | 51 | 10 | 13 | 27 | 1 |
| 11 → 12 | 25 | 5 | 6 | 13 | 1 |
| 12 → 13 | 48 | 6 | 21 | 20 | 1 |
| **Total** | **599** | **112** | **223** | **243** | **21** |

("Manual" inclui os itens `CONFERIDO` — cobertos pelo padrão de outro item — e os `MANUAL`.) Os itens "Não se aplica" são, em sua maioria, títulos de grupo
(Cache, Eloquent, Queue…), versão de PHP/Composer, ferramentas fora do sistema (instalador, Dusk, Spark, Cashier, Sanctum, Telescope) e
recursos de bancos que o e-Cidade não usa (MySQL, SQLite, SQL Server).

## 4. Onde o código usa algo que mudou

A tabela abaixo é gerada pelo script (um item por linha; o mesmo recurso aparece em mais de um guia quando foi mexido em mais de uma versão).
Exemplos são `arquivo:linha`; a lista completa está no `.tsv`.

| Guia | Item | Ocorrencias | Arquivos | Exemplos | Tipo |
|---|---|---|---|---|---|
| 5.5 | Auto-Loading Commands | 1 | 1 | `app/Console/Kernel.php:15` | uso |
| 5.5 | The optimize Command | 2 | 1 | `composer.json:129` `composer.json:133` | sinal |
| 5.5 | The basic and onceBasic Methods | 1 | 1 | `app/Http/Kernel.php:76` | uso |
| 5.5 | Database Driver | 1 | 1 | `configuration/cache.php:42` | config |
| 5.5 | The belongsToMany Method | 30 | 23 | `app/Domain/Financeiro/Contabilidade/Models/PlanoDespesa.php:32` `app/Domain/Financeiro/Contabilidade/Models/Pcasp.php:58` `app/Domain/Financeiro/Contabilidade/Models/Conplano.php:313` | uso |
| 5.5 | Relationship create Methods | 3 | 3 | `app/Domain/Patrimonial/Patrimonio/Services/EtiquetaService.php:18` `app/Domain/Saude/Ambulatorial/Services/FindOrCreateCgsService.php:40` `app/Http/Middleware/WindowSessionMiddleware.php:41` | sinal |
| 5.5 | Exception Format | 1 | 1 | `app/Exceptions/Handler.php:46` | uso |
| 5.5 | JSON Authentication Attempts | 1 | 1 | `app/Http/Middleware/AuthSimMiddleware.php:31` | uso |
| 5.5 | A Note On Form Requests | 340 | 169 | `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Update.php:6` `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Update.php:9` `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Sequencial.php:6` | uso |
| 5.5 | The dispatch Helper | 1 | 1 | `app/Domain/RecursosHumanos/Pessoal/Services/ContraChequeService.php:48` | uso |
| 5.5 | The all Method | 1 | 1 | `app/Http/Middleware/DBRequestMiddleware.php:27` | sinal |
| 5.5 | The has Method | 2 | 1 | `app/Http/Middleware/AuthSimMiddleware.php:26` `app/Http/Middleware/AuthSimMiddleware.php:35` | sinal |
| 5.5 | The request() Helper | 4 | 4 | `app/Domain/Configuracao/Banco/Controller/BancoPixController.php:252` `app/Domain/Tributario/Arrecadacao/Requests/RegraEmissaoRequest.php:29` `app/Domain/Tributario/Arrecadacao/Requests/TipoDebitoPixRequest.php:30` | uso |
| 5.5 | Tinker | 1 | 1 | `composer.json:37` | uso |
| 5.5 | Validator Methods | 41 | 24 | `app/Domain/RecursosHumanos/RH/ConcessaoDireitos/Controllers/AssentConcedeConfigController.php:97` `app/Domain/RecursosHumanos/RH/ConcessaoDireitos/Controllers/ConcessaoCalculoController.php:96` `app/Domain/RecursosHumanos/RH/ConcessaoDireitos/Controllers/AssentPercController.php:81` | sinal |
| 5.5 | Dynamic "With" Variable Names | 5 | 5 | `app/Domain/Patrimonial/Protocolo/Model/TipoProcesso.php:32` `app/Domain/Patrimonial/Protocolo/Model/Processo/TipoProc.php:22` `app/Domain/Saude/Ambulatorial/Resources/ProblemasPacienteResource.php:30` | sinal |
| 5.6 | The optimize Command | 2 | 1 | `composer.json:129` `composer.json:133` | sinal |
| 5.6 | New Configuration File | 1 | 1 | `app/Http/Controllers/Auth/RegisterController.php:68` | sinal |
| 5.6 | New Configuration File | 1 | 1 | `app/Http/Controllers/Auth/RegisterController.php:68` | sinal |
| 5.6 | Bootstrap 4 | 1 | 1 | `app/Domain/Core/Base/Repository/BaseRepository.php:49` | sinal |
| 5.7 | The register Method | 1 | 1 | `app/Providers/AppServiceProvider.php:34` | sinal |
| 5.7 | The ResetsPasswords Trait | 2 | 1 | `app/Http/Controllers/Auth/ResetPasswordController.php:6` `app/Http/Controllers/Auth/ResetPasswordController.php:21` | uso |
| 5.7 | The SendsPasswordResetEmails Trait | 2 | 1 | `app/Http/Controllers/Auth/ForgotPasswordController.php:6` `app/Http/Controllers/Auth/ForgotPasswordController.php:21` | uso |
| 5.7 | The whereDate Method | 2 | 1 | `app/Domain/Saude/Farmacia/Services/DemandaReprimidaService.php:76` `app/Domain/Saude/Farmacia/Services/DemandaReprimidaService.php:77` | uso |
| 5.7 | QUEUE_DRIVER Environment Variable | 4 | 4 | `app/Jobs/RecursosHumanos/Pessoal/EmissaoContraChequeJob.php:88` `configuration/queue.php:18` `phpunit.xml:29` | uso |
| 5.7 | Nested Validation Data | 11 | 10 | `app/Domain/RecursosHumanos/RH/ConcessaoDireitos/Controllers/AssentConcedeConfigController.php:97` `app/Domain/RecursosHumanos/RH/ConcessaoDireitos/Controllers/ConcessaoCalculoController.php:96` `app/Domain/RecursosHumanos/RH/ConcessaoDireitos/Controllers/AssentPercController.php:81` | sinal |
| 5.7 | The Validator Contract | 1 | 1 | `app/Http/Controllers/Auth/RegisterController.php:46` | uso |
| 5.8 | The environment Method | 2 | 2 | `app/User.php:51` `app/Providers/AppServiceProvider.php:36` | sinal |
| 5.8 | Password Reset Notification Route Parameter | 1 | 1 | `app/Http/Controllers/Auth/ResetPasswordController.php:8` | uso |
| 5.8 | New Default Password Length | 1 | 1 | `app/Http/Controllers/Auth/RegisterController.php:53` | sinal |
| 5.8 | TTL in seconds | 4 | 3 | `app/Domain/Patrimonial/Protocolo/Controller/DocumentoAndamentoController.php:118` `app/Domain/Patrimonial/Protocolo/Controller/DocumentoAndamentoController.php:164` `app/Domain/Assinador/Controllers/AssinadorAPI.php:177` | sinal |
| 5.8 | PSR-16 Conformity | 12 | 3 | `app/Domain/Patrimonial/Protocolo/Controller/DocumentoAndamentoController.php:112` `app/Domain/Patrimonial/Protocolo/Controller/DocumentoAndamentoController.php:113` `app/Domain/Patrimonial/Protocolo/Controller/DocumentoAndamentoController.php:118` | sinal |
| 5.8 | Carbon 2.0 | 63 | 27 | `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:7` `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:35` `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:36` | uso |
| 5.8 | The Kernel Contract | 2 | 2 | `bootstrap/app.php:37` `tests/CreatesApplication.php:5` | uso |
| 5.8 | Migrations & bigIncrements | 32 | 26 | `database/migrations/2021_12_16_111552_M19629_create_arretipopixasso.php:18` `database/migrations/2022_04_27_111632_m20466_estrutura_andamento_documentos.php:195` `database/migrations/2022_04_27_111632_m20466_estrutura_andamento_documentos.php:214` | uso |
| 5.8 | Model Names Ending With Irregular Plurals | 325 | 325 | `app/User.php:21` `app/Domain/RecursosHumanos/Pessoal/Model/Ponto/PontoSalario.php:23` `app/Domain/RecursosHumanos/Pessoal/Model/Servidor/Cbo.php:18` | sinal |
| 5.8 | Custom Pivot Models With Incrementing IDs | 6 | 6 | `app/Domain/Saude/Ambulatorial/Models/ProblemaCid.php:13` `app/Domain/Saude/Ambulatorial/Models/Cid.php:26` `app/Domain/Saude/Ambulatorial/Models/Problema.php:53` | uso |
| 5.8 | The ExceptionHandler Contract | 1 | 1 | `bootstrap/app.php:42` | uso |
| 5.8 | Pheanstalk 4.0 | 3 | 1 | `configuration/queue.php:14` `configuration/queue.php:44` `configuration/queue.php:45` | uso |
| 5.8 | The TransformsRequest Middleware | 4 | 2 | `app/Http/Kernel.php:32` `app/Http/Kernel.php:33` `app/Http/Middleware/TrimStrings.php:5` | uso |
| 5.8 | The StartSession Middleware | 1 | 1 | `app/Http/Kernel.php:48` | uso |
| 5.8 | Prefer String And Array Classes Over Helpers | 2 | 2 | `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/ComissaoController.php:75` `database/factories/ModelFactory.php:22` | uso |
| 5.8 | Deferred Service Providers | 1 | 1 | `app/Domain/Core/Base/Providers/BaseDeferredProvider.php:13` | uso |
| 5.8 | Read-Only env Helper | 20 | 9 | `app/Domain/RecursosHumanos/Pessoal/Relatorios/ContraChequePdf.php:52` `app/Domain/Assinador/Service/CertificadoPfxService.php:78` `app/Domain/Assinador/Service/CertificadoPfxService.php:79` | uso |
| 5.8 | The setUp & tearDown Methods | 16 | 14 | `tests/TestCase.php:25` `tests/Unit/RecursosHumanos/Pessoal/Model/ServidorMovimentacaoTest.php:796` `tests/Unit/RecursosHumanos/Pessoal/Model/ControleRubricasParametrosTest.php:22` | uso |
| 5.8 | PHPUnit 8 | 1 | 1 | `composer.json:65` | uso |
| 5.8 | The Validator Contract | 1 | 1 | `app/Http/Controllers/Auth/RegisterController.php:46` | uso |
| 5.8 | Email Validation | 8 | 6 | `app/Domain/Financeiro/Planejamento/Relatorios/Anexos/Xls.php:115` `app/Domain/Financeiro/Planejamento/Services/RelatorioAnexoIService.php:95` `app/Domain/Financeiro/Planejamento/Services/Relatorios/RelatorioPlanejamentoRclService.php:183` | sinal |
| 5.8 | The getData Method | 10 | 7 | `app/Domain/Patrimonial/Ouvidoria/Services/AtendimentoProcessoService.php:281` `app/Domain/Patrimonial/Protocolo/Repository/Processo/ArquivamentoRepository.php:51` `app/Domain/Patrimonial/Protocolo/Repository/Processo/ProcessoDocumentoRepository.php:61` | sinal |
| 6.x | Carbon 1.x No Longer Supported | 63 | 27 | `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:7` `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:35` `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:36` | uso |
| 6.x | The AWS_REGION Environment Variable | 1 | 1 | `configuration/filesystems.php:69` | uso |
| 6.x | Redis Default Client | 1 | 1 | `configuration/database.php:108` | config |
| 6.x | SQS Environment Variables | 4 | 1 | `configuration/queue.php:14` `configuration/queue.php:51` `configuration/queue.php:52` | config |
| 6.x | The Capsule table Method | 2 | 2 | `app/Domain/Integracoes/EFDReinf/Services/ConsultaEventoService.php:5` `app/Domain/Financeiro/Empenho/Models/RetencaoReceitasProdutorRural.php:6` | uso |
| 6.x | Arrayable & toArray | 27 | 27 | `app/Domain/Financeiro/Contabilidade/Models/Pcasp.php:47` `app/Domain/Financeiro/Contabilidade/Models/Conplano.php:101` `app/Domain/Financeiro/Contabilidade/Models/PlanoReceita.php:32` | uso |
| 6.x | Declaration Of Primary Key Type | 53 | 53 | `app/Domain/RecursosHumanos/Pessoal/Model/Jetom/ComissaoConfiguracao.php:23` `app/Domain/RecursosHumanos/Pessoal/Model/Jetom/ComissaoServidor.php:31` `app/Domain/RecursosHumanos/Pessoal/Model/Jetom/ComissaoFuncao.php:24` | uso |
| 6.x | String & Array Helpers Package | 2 | 2 | `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/ComissaoController.php:75` `database/factories/ModelFactory.php:22` | uso |
| 6.x | Mandrill & SparkPost Drivers Removed | 3 | 2 | `configuration/mail.php:14` `configuration/mail.php:15` `configuration/services.php:28` | uso |
| 6.x | Password Validation | 1 | 1 | `app/Http/Controllers/Auth/RegisterController.php:53` | sinal |
| 6.x | Queue Retry Limit | 1 | 1 | `app/Jobs/RecursosHumanos/Pessoal/EmissaoContraChequeJob.php:34` | uso |
| 6.x | Rackspace Storage Driver Removed | 1 | 1 | `configuration/filesystems.php:40` | uso |
| 6.x | Route URL Generation & Extra Parameters | 1 | 1 | `app/Exceptions/Handler.php:113` | sinal |
| 6.x | FormRequest validationData Method | 9 | 4 | `app/Domain/Configuracao/Banco/Controller/BancoPixController.php:124` `app/Domain/Configuracao/Banco/Controller/BancoPixController.php:126` `app/Domain/Configuracao/Banco/Controller/BancoPixController.php:127` | uso |
| 7.x | Symfony 5 Required | 7 | 1 | `composer.json:51` `composer.json:52` `composer.json:53` | uso |
| 7.x | Symfony 5 Related Upgrades | 104 | 104 | `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Update.php:47` `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Sequencial.php:30` `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Store.php:47` | uso |
| 7.x | Date Serialization | 141 | 68 | `app/Domain/RecursosHumanos/Pessoal/Model/Jetom/Sessao.php:358` `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/ComissaoController.php:76` `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/SessaoController.php:91` | sinal |
| 7.x | Factory Types | 3 | 2 | `app/Domain/Tributario/ISSQN/Services/AlvaraOnline/AlvaraOnlineService.php:97` `app/Domain/Tributario/ISSQN/Services/AlvaraOnline/AlvaraOnlineService.php:127` `database/factories/ModelFactory.php:15` | uso |
| 7.x | PSR-7 Compatibility | 3 | 3 | `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/ComissaoController.php:19` `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/ComissaoTipoSessaoController.php:14` `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/FuncaoController.php:13` | uso |
| 7.x | Configuration File Changes | 1 | 1 | `configuration/mail.php:115` | config |
| 7.x | Unique Route Names | 2 | 1 | `routes/api/educacao/escola.php:14` `routes/api/educacao/escola.php:23` | sinal |
| 7.x | The different Rule | 1 | 1 | `app/Domain/Configuracao/Configuracao/Requests/SalvarOrganogramaRequest.php:18` | uso |
| 8.x | Seeder & Factory Namespaces | 1 | 1 | `database/seeds/DatabaseSeeder.php:5` | uso |
| 8.x | Model Factories | 3 | 2 | `app/Domain/Tributario/ISSQN/Services/AlvaraOnline/AlvaraOnlineService.php:97` `app/Domain/Tributario/ISSQN/Services/AlvaraOnline/AlvaraOnlineService.php:127` `database/factories/ModelFactory.php:15` | uso |
| 8.x | The EventServiceProvider Class | 3 | 2 | `app/Providers/EventServiceProvider.php:6` `app/Providers/EventServiceProvider.php:8` `configuration/app.php:177` | uso |
| 8.x | Maintenance Mode Updates | 1 | 1 | `app/Http/Kernel.php:30` | uso |
| 8.x | Pagination Defaults | 1 | 1 | `app/Domain/Core/Base/Repository/BaseRepository.php:49` | sinal |
| 8.x | Failed Jobs Table Batch Support | 3 | 2 | `configuration/queue.php:82` `database/migrations/2022_08_30_164544_create_failed_jobs_table.php:16` `database/migrations/2022_08_30_164544_create_failed_jobs_table.php:33` | uso |
| 8.x | Automatic Controller Namespace Prefixing | 1 | 1 | `app/Providers/RouteServiceProvider.php:17` | uso |
| 8.x | Database Rule Connections | 70 | 44 | `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Update.php:25` `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Update.php:29` `app/Domain/RecursosHumanos/Pessoal/Requests/Jetom/ComissaoServidor/Update.php:40` | sinal |
| 9.x | Exception Handler Contract Binding | 1 | 1 | `bootstrap/app.php:42` | uso |
| 9.x | The FILESYSTEM_DRIVER Environment Variable | 1 | 1 | `configuration/filesystems.php:16` | uso |
| 9.x | Flysystem 3.x | 1 | 1 | `configuration/app.php:234` | uso |
| 9.x | The when / unless Methods | 95 | 33 | `app/Domain/RecursosHumanos/Pessoal/Model/Jetom/ComissaoServidor.php:238` `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/SessaoController.php:60` `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/SessaoController.php:63` | sinal |
| 9.x | The opis/closure Library | 1 | 1 | `composer.json:34` | uso |
| 9.x | Unvalidated Array Keys | 29 | 13 | `app/Domain/Integracoes/EFDReinf/Controllers/ConfiguracaoController.php:37` `app/Domain/Integracoes/EFDReinf/Controllers/UnidadeResponsavelController.php:28` `app/Domain/Integracoes/EFDReinf/Controllers/UnidadeResponsavelController.php:44` | sinal |
| 10.x | Minimum Stability | 1 | 1 | `composer.json:92` | config |
| 10.x | The registerPolicies Method | 1 | 1 | `app/Providers/AuthServiceProvider.php:27` | uso |
| 10.x | Database Expressions | 48 | 28 | `app/Domain/RecursosHumanos/Pessoal/Model/Jetom/Sessao.php:381` `app/Domain/RecursosHumanos/RH/ConcessaoDireitos/Controllers/ConcessaoCalculoLogController.php:29` `app/Domain/RecursosHumanos/RH/ConcessaoDireitos/Controllers/ConcessaoCalculoLogController.php:53` | uso |
| 10.x | Model "Dates" Property | 5 | 5 | `app/Domain/Financeiro/Planejamento/Models/Planejamento.php:41` `app/Domain/Financeiro/Orcamento/Models/Recurso.php:35` `app/Domain/Educacao/Escola/Models/Aluno.php:93` | uso |
| 10.x | The dispatch() Helper Return Value | 1 | 1 | `app/Domain/RecursosHumanos/Pessoal/Services/ContraChequeService.php:48` | uso |
| 10.x | Middleware Aliases | 1 | 1 | `app/Http/Kernel.php:74` | uso |
| 10.x | Service Mocking | 22 | 3 | `tests/TestCase.php:7` `tests/TestCase.php:13` `tests/Unit/RecursosHumanos/Pessoal/Service/ControleRubricasMatriculasServiceTest.php:13` | uso |
| 11.x | Application Structure | 4 | 2 | `app/Http/Kernel.php:20` `app/Http/Kernel.php:44` `app/Http/Kernel.php:74` | uso |
| 11.x | Password Rehashing | 1 | 1 | `app/Http/Controllers/Auth/RegisterController.php:68` | sinal |
| 11.x | The AuthenticationException Class | 4 | 1 | `app/Exceptions/Handler.php:6` `app/Exceptions/Handler.php:18` `app/Exceptions/Handler.php:104` | uso |
| 11.x | Cache Key Prefixes | 1 | 1 | `configuration/cache.php:89` | config |
| 11.x | Eloquent Model casts Method | 32 | 32 | `app/Domain/Financeiro/Planejamento/Models/Configuracao.php:43` `app/Domain/Financeiro/Planejamento/Models/CronogramaDesembolsoReceita.php:55` `app/Domain/Financeiro/Planejamento/Models/FatorCorrecaoDespesa.php:30` | uso |
| 11.x | Floating-Point Types | 7 | 3 | `database/migrations/2022_05_26_163234_M20866_Createe_assentperc.php:20` `database/migrations/2021_12_14_114408_M19629_create_pix_tipo_debito.php:23` `database/migrations/2021_12_14_114408_M19629_create_pix_tipo_debito.php:24` | uso |
| 11.x | Doctrine DBAL Removal | 1 | 1 | `composer.json:30` | uso |
| 11.x | Carbon 3 | 63 | 27 | `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:7` `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:35` `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:36` | uso |
| 11.x | Synchronous Jobs in Database Transactions | 3 | 1 | `configuration/queue.php:18` `configuration/queue.php:33` `configuration/queue.php:34` | config |
| 11.x | Updating Passport | 8 | 6 | `app/User.php:8` `app/Http/Kernel.php:17` `app/Http/Kernel.php:18` | uso |
| 12.x | Carbon 3 | 63 | 27 | `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:7` `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:35` `app/Domain/Financeiro/Contabilidade/Builder/PlanoOrcamentarioReceitaBuilder.php:36` | uso |
| 12.x | Container Class Dependency Resolution | 3 | 3 | `app/Domain/Tributario/Arrecadacao/Services/AntecipaVencimentoDataTermoService.php:114` `app/Domain/Tributario/Arrecadacao/Services/ReversaoParcelamentoVencidoService.php:37` `app/Domain/Tributario/Arrecadacao/Services/AntecipaDataVencidaService.php:123` | sinal |
| 12.x | Nested Array Request Merging | 1 | 1 | `app/Http/Middleware/DBRequestMiddleware.php:29` | sinal |
| 12.x | Route Precedence | 533 | 31 | `routes/api/configuracao/relatoriolegal.php:4` `routes/api/configuracao/relatoriolegal.php:5` `routes/api/configuracao/relatoriolegal.php:6` | sinal |
| 12.x | Local Filesystem Disk Default Root Path | 3 | 1 | `configuration/filesystems.php:48` `configuration/filesystems.php:53` `configuration/filesystems.php:60` | config |
| 13.x | Cache Prefixes and Session Cookie Names | 7 | 4 | `configuration/database.php:39` `configuration/database.php:52` `configuration/database.php:65` | config |
| 13.x | Collection Model Serialization Restores Eager-Loaded Relations | 4 | 2 | `app/Jobs/RecursosHumanos/Pessoal/ProcessPayrollDataJob.php:12` `app/Jobs/RecursosHumanos/Pessoal/ProcessPayrollDataJob.php:19` `app/Jobs/RecursosHumanos/Pessoal/EmissaoContraChequeJob.php:13` | uso |
| 13.x | Default Password Reset Subject | 1 | 1 | `app/Http/Controllers/Auth/ResetPasswordController.php:8` | uso |
| 13.x | Queued Notifications and Missing Models | 2 | 2 | `app/Jobs/RecursosHumanos/Pessoal/ProcessPayrollDataJob.php:17` `app/Jobs/RecursosHumanos/Pessoal/EmissaoContraChequeJob.php:18` | uso |
| 13.x | withScheduling Registration Timing | 1 | 1 | `app/Console/Kernel.php:38` | uso |
| 13.x | Request Forgery Protection | 3 | 2 | `app/Http/Kernel.php:51` `app/Http/Middleware/VerifyCsrfToken.php:5` `app/Http/Middleware/VerifyCsrfToken.php:7` | uso |

### Mudanças de comportamento sem erro (as mais perigosas)

1. **TTL do cache passa de minutos para segundos (5.8).** 4 chamadas `Cache::put(..., 5|10)`:
   `app/Domain/Patrimonial/Protocolo/Controller/DocumentoAndamentoController.php:118` e `:164`, `app/Domain/Assinador/Controllers/AssinadorAPI.php:177`,
   `app/Jobs/RecursosHumanos/Pessoal/EmissaoContraChequeJob.php:105`. Hoje guardam 5 e 10 **minutos**; depois da atualização guardariam 5 e 10 **segundos**.
2. **Helpers removidos em 6.0 (pacote `laravel/helpers`):** `array_pluck` em `app/Domain/RecursosHumanos/Pessoal/Controller/Jetom/ComissaoController.php:75` e
   `str_random` em `database/factories/ModelFactory.php:22`. Os outros 40 nomes do grupo têm 0 usos.
3. **`env()` fora da configuração (5.8, congelamento da configuração):** 20 usos em 9 arquivos (`WebIss/Autenticacao.php`, `CorsMiddleware.php`,
   `ClearPayrollData.php`, `ProcessPayrollDataJob.php`, `EmissaoContraChequeJob.php`, `CertificadoPfxService.php`, `ContraChequePdf.php`…). Com a
   configuração em cache, `env()` devolve `null`. `EmissaoContraChequeJob.php:88` ainda lê `QUEUE_DRIVER` (renomeada para `QUEUE_CONNECTION` na 5.7).
4. **Serialização de datas em JSON (7.x):** `toArray()`/`toJson()` em 141 pontos (68 arquivos) passam a serializar datas em ISO-8601/UTC
   (`2026-11-13T10:00:00.000000Z`); hoje saem como `Y-m-d H:i:s`. Os 5 models com `$dates` (removida no 10) precisam virar `$casts`.
5. **Carbon 1 → 3:** 63 usos em 27 arquivos; `diffIn*()` (cujo retorno muda no Carbon 3) tem 0 usos no código varrido.
6. **Validação `exists:`/`unique:` com conexão (8.x):** 70 regras em 44 arquivos; `->validated()`/`validate()` em 29 pontos (13 arquivos): a partir do 9.x o validador
   exclui sozinho do resultado as chaves de array sem regra.
7. **Precedência de rotas (12.x):** 533 definições `Route::get|post|…` em 31 arquivos de `routes/`; a ordem relativa de rotas que casam o mesmo
   caminho pode mudar o despacho. Nomes de rota (únicos a partir do 7.x): 18 rotas têm nome no `route:list` e nenhum se repete.

### Estrutura que muda de lugar

- **11.x (estrutura slim):** `app/Http/Kernel.php` (`$middleware`, `$middlewareGroups`, `$routeMiddleware` → alias), `app/Console/Kernel.php` (`$commands`, `schedule()`),
  `bootstrap/app.php` (contratos `Kernel` e `ExceptionHandler`) e `app/Providers/*` (6) acompanham a nova inicialização. O guia do 11 **não recomenda** migrar a estrutura
  de uma aplicação 10 e diz que o 11 aceita a estrutura antiga; os guias do 12 e do 13 não tratam do assunto. Migrar a estrutura é uma decisão
  separada de fazer o código rodar.
- **Autenticação:** `app/User.php` (Passport: `HasApiTokens`, `findForPassport`, `validateForPassportPasswordGrant`), `AuthServiceProvider` (`Passport::routes`,
  `registerPolicies`), 4 controllers `Auth/*` (traits `ResetsPasswords`, `SendsPasswordResetEmails`; regra de senha, `Validator`), `AuthSimMiddleware`
  (`Auth::attempt`). Esse bloco depende do Passport que for escolhido.
- **Filas:** `configuration/queue.php` (beanstalkd/Pheanstalk, SQS, `failed_jobs`, `sync`), 2 jobs com `$tries`, `SerializesModels` e dependência de `env`.
- **Testes:** `tests/TestCase.php` e 14 arquivos com `setUp`/`tearDown` sem `: void` (PHPUnit 8+); `Mockery`/`shouldReceive` em 3 arquivos.

## 5. Helpers, facades e pacotes que somem

- **Facade `Input` (removida no 6):** 0 usos. **Helpers `str_*`/`array_*` globais (6.0):** 2 usos (acima).
- **Funções globais próprias (`app/Helpers`):** 29, nenhuma com nome de helper do Laravel (nem dos removidos); sem conflito com os helpers do 13 nem com as
  funções novas do PHP 8.5 (`array_first`, `array_last`, `mb_trim`… — 0 declarações).
- **Pacotes que a matriz de versões aponta como impeditivos ou que mudam de major** (uso no código do projeto, fora do `vendor/`):

| Pacote | Uso no código |
|---|---|
| `silex/silex` | 14 arquivos, todos em `api/` (API V1) |
| `proner/phppimaco` | 4 arquivos em `app/Domain/Patrimonial/Patrimonio/` (etiquetas) |
| `dbseller/phinx_postgres` | `phinx.php` + 1.511 migrations em `db/migrations/` via `Classes\PostgresMigration` (nenhuma usa `Phinx\` direto) |
| `dbseller/sdk-api-pix-bb` | `app/Domain/Tributario/Arrecadacao/Pix/Bancos/BancoDoBrasil.php` (`Swagger\Client\…`) |
| `jeremeamia/superclosure` | `src/Task/Closure.php` (`SuperClosure\SerializableClosure`); no `composer.json` o uso do guia 9 (`opis/closure`) aparece só como dependência |
| `doctrine/dbal` | só no `composer.json` (DBAL some do Laravel 11); 0 usos no código varrido |
| `laravel/tinker` | só no `composer.json` |

## 6. Agrupamento sugerido em tarefas pequenas

Cada grupo cabe em ~300 linhas manuais; ordem sugerida da base para o topo. Nenhum é implementação.

1. **Inicialização da aplicação:** `bootstrap/app.php`, `public/index.php`, `app/Application.php` (`configPath`), `app/Http/Kernel.php`, `app/Console/Kernel.php`,
   `app/Exceptions/Handler.php` (`render`, `AuthenticationException`), `tests/CreatesApplication.php`.
2. **Configuração (`configuration/`, 11 arquivos):** cache (driver `database`, prefixo, TTL), database (cliente Redis, prefixos), filesystems (Rackspace, `AWS_REGION`,
   `FILESYSTEM_DRIVER`, raiz do disco local), mail (Mandrill/SparkPost, markdown), queue (Pheanstalk, SQS, `failed_jobs`, `sync`), session, `app.php` (providers/aliases).
3. **Providers (6) e eventos:** `AppServiceProvider`, `AuthServiceProvider`, `EventServiceProvider`, `RouteServiceProvider` (`$namespace`), `QueueServiceProvider`, `BaseDeferredProvider` (`$defer`).
4. **Middlewares (15):** `CorsMiddleware`, `DBRequestMiddleware` (`all`/`has`/`merge`), `AuthSimMiddleware`, `TrimStrings`/`ConvertEmptyStringsToNull`, `VerifyCsrfToken`.
5. **Autenticação e Passport:** `User.php`, controllers `Auth/*`, `Passport::routes`, regras de senha — depende da escolha do Passport.
6. **Cache, `env()` e filas:** os 4 `Cache::put` (minutos → segundos), os 20 `env()` fora da configuração, `QUEUE_DRIVER`, 2 jobs, 5 commands.
7. **Datas:** Carbon (63 usos), `$dates` (5), serialização de datas em `toArray`/`toJson` (141), `$casts` (32 models).
8. **Eloquent (325 models):** `belongsToMany` (30), pivots customizados (6), `$keyType` (53), `toArray` (27), nomes de tabela, factories antigas (3 usos + `ModelFactory.php`).
9. **Validação (86 form requests):** regras `exists`/`unique` com conexão (70), `validationData` (9), `validated` (29), regra `password`/`image`.
10. **Rotas (561):** ordem/precedência (533 `Route::`), `$namespace` automático de controllers (8.x).
11. **Migrations do Laravel (452):** `bigIncrements` (32), `float`/`double` (7), `change()`; e **helpers removidos** (`array_pluck`, `str_random`).
12. **Testes:** `setUp`/`tearDown` (16), Mockery (22 usos em 3 arquivos), `Tests\TestCase`.
13. **Pacotes:** Silex/API V1 (14), PhpPimaco (4), Phinx (`phinx.php` + 1.511 migrations), SDK do Pix BB (1), SuperClosure (1).

## 7. Como reproduzir

```bash
python3 scratchpad/inventario_laravel.py contagem                       # seção 2
python3 scratchpad/inventario_laravel.py guias <pasta>                  # baixa os 12 guias (rede)
python3 scratchpad/inventario_laravel.py itens <pasta> > itens.tsv      # seções 1, 3 e 4 (a saída é o .tsv do repositório)
python3 scratchpad/inventario_laravel.py md itens.tsv                   # tabela da seção 4
python3 scratchpad/inventario_laravel.py helpers                        # seção 5
```
