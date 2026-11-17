# Silex (API V1), caminho de atualização e datas de suporte

Tarefa T-007. Spike: só relatório, nenhum código do sistema foi alterado e nada foi
instalado. Medições feitas em 12/11/2026 sobre a worktree `laravel/T-007-silex-caminhos` (= `laravel/integracao`, commit
`59c46e20b`). O que não foi medido está marcado **[não medido]** ou **[estimativa]**.

## 1. Silex 2 e a `api/V1`

### 1.1 O que existe (medido)

| Item | Valor | Como contar |
|---|---|---|
| Arquivos em `ecidade/api/V1/` | **33** (todos `.php`; 1.815 linhas) + `ecidade/api/api.php` (o bootstrap Silex, fora de `V1/`) | `find ecidade/api/V1 -type f` |
| Arquivos que citam `Silex` | **19** em `V1/` + `api/api.php` = **20** (bate com o registro, `laravel.md`: "20 arquivos") | `grep -rla Silex api/V1` (19); `grep -rla Silex api` (20) |
| Arquivos de `V1/` que citam Silex, Pimple ou `Symfony\Component` | **27** de 33 | `grep -rlaF -e Silex -e Pimple -e 'Symfony\Component' api/V1` |
| Arquivos que usam `League\Fractal` | 6 (os `Transformers` e `GenericController`) | `grep -rla 'League\\Fractal'` |
| Providers de rotas (`mount`) | **5**: `auth`, `protocolo`, `configuracao`, `tributario`, `matriculaonline` | `APIServiceProvider.php` |
| Providers de serviço Pimple (`Providers/Domain`) | **8** (auth da aplicação, content-type, banco, persistência do usuário, query, resposta, sessão, auth do usuário) | `ls Providers/Domain` |
| **Rotas HTTP** | **7** | tabela abaixo |
| Despacho | `FrontController.php:4` — `preg_match('/[^?]*api\/v\d\//')` → `require_once 'api/api.php'` | — |
| `use Silex\Application` do `app.php` | import sem uso (conforme o registro) | — |

Rotas (prefixo `/api/v1`, `ApplicationConfig::APPLICATION_PREFIX`):

| # | Método e caminho | Controller | Autenticação |
|---|---|---|---|
| 1 | `POST /auth/login` | `Auth\Login` | guardada (`RouteConfig::routes`) |
| 2 | `GET /protocolo/cgm` | `Protocolo\Cgm::getAll` | sessão legada (`$app->before`) |
| 3 | `GET /protocolo/cgm/{id}` (`id` = `\d+`) | `Protocolo\Cgm::get` | sessão legada |
| 4 | `GET /configuracao/formulario/{id}/instituicao/{instituicao}` | `Configuracao\Formulario::getAll` | sessão legada |
| 5 | `POST /tributario/recibo` | `Tributario\Recibo::geraRecibo` | guardada + `userAuthRoutes` |
| 6 | `POST /matriculaonline/inscricao` | `MatriculaOnline\InscricaoCandidato::inscricao` | guardada |
| 7 | `GET /matriculaonline/emissaoProtocolo` | `MatriculaOnline\InscricaoCandidato::emissaoProtocolo` | guardada |

Duas famílias de rota, com dois mecanismos de autenticação em `api/api.php`: as 4 "guardadas" ganham os 8 providers
Pimple (sessão própria, token); as outras 3 usam `Registry::get('app.request')->session()` e `db_getsession()` do legado.
Portanto **não existe um só jeito de autenticar a API V1 — são dois, a reproduzir os dois**.

Consumidores no repositório: `con4_manutencaoformulario001.php:498` (rota 4, URL relativa `api/v1/...`) e
`scripts/HTTPRequest.js:17` (rota 2, com host fixo de desenvolvimento da DBSeller — provável resto). **[não medido]**
se há consumidores externos (portal de matrícula online, Redesim etc.): as rotas 1, 5, 6 e 7 têm cara de integração
externa; só o cliente/DBSeller sabe. É o principal risco de qualquer opção.

Comportamento a preservar (princípio "migrar, não consertar"): o `$app->error()` devolve um `JsonResponse` com o corpo
`{statusCode, message, stacktrace}` (`stacktrace` porque `debug` está `true`). O código HTTP **não** é fixo em 200: o
`JsonResponse` nasce com 200, mas o `HttpKernel::handleException` do Symfony 3.4.49 travado no lock
(`vendor/symfony/http-kernel/HttpKernel.php:247-255`) troca o status quando a resposta não é de erro: exceção
`HttpExceptionInterface` (ex.: o `AccessDeniedHttpException` do `api.php`) mantém o código dela (403, 404, 405…) e
qualquer outra exceção vira **500**. O que é fixo e deve ser reproduzido é o formato do corpo e esse mapeamento de
status. Uma reescrita que "conserte" qualquer dos dois muda a saída. **[leitura do código; não medido por requisição real]**

### 1.2 Por que "manter" não vale na versão nova

- `silex/silex` 2.2.4 (travado no `composer.lock`) exige `symfony/http-foundation`, `http-kernel`, `routing`,
  `event-dispatcher` em `~2.8|^3.0`. O Laravel 12 exige Symfony 7 (`composer-compatibilidade-revisada.md`).
  Resultado já medido: o Silex é um dos 4 pacotes que **não resolvem** com Laravel 12.
- O último release, `silex/silex` 2.3.0, aceita só `symfony/http-kernel` `^4.0` e PHP `>=7.1.3` — ainda não é
  Symfony 7 (Packagist, ver fontes). Não existe versão posterior.
- O projeto está arquivado: o GitHub mostra "This repository was archived by the owner on Jul 4, 2018" e o README diz
  "[DEPRECATED -- Use Symfony instead]" e "Ends of life is set to June 2018".

### 1.3 Opções

| Opção | O que é | Esforço **[estimativa]** | Risco |
|---|---|---|---|
| **A. Manter** | Silex 2.2.4/2.3.0 num `composer.json` e `vendor/` **separados** (ex.: `ecidade/api/composer.json`), fora do Laravel novo | 2–3 tarefas (vendor próprio, `api.php` carregando o autoload dele, teste nos dois PHPs) | **Alto**: Symfony 3/4 sem suporte, sobre PHP 8.5 não suportado pelo Silex (2.3.0 declara `>=7.1.3`, nunca testado em 8.x) **[não medido: se roda no 8.5]**; mais um `vendor/` por runtime; adia o problema. Dívida de segurança. |
| **B. Atualizar** | Subir a versão do Silex | — | **Inviável**: não há versão acima de 2.3.0 (Symfony 4). |
| **C1. Substituir por rotas do Laravel** | Os 5 `ControllerProvider` viram `routes/` do Laravel; os 7 métodos de controller viram controllers Laravel; os 8 providers Pimple viram middleware/serviço; `api.php` deixa de existir e `FrontController` manda `api/vN/` para `public/index.php` | **5–7 tarefas**: (1) rotas + `Cgm` e `Formulario` com Fractal; (2) `Recibo`; (3) `Login` + `InscricaoCandidato`; (4) middleware das duas famílias de autenticação; (5) erro idêntico: corpo `{statusCode,message,stacktrace}` e mapeamento de status (exceção HTTP mantém o código, as demais viram 500); (6) testes de contrato 5.6 × novo nas 7 rotas; (7) ajuste do despacho. | Médio: depende de o Laravel novo inicializar (hoje não inicializa — 1º provider); consumidores externos desconhecidos; reproduzir o formato e o mapeamento de status do erro. Não acrescenta framework novo. |
| **C2. Substituir por Symfony (MicroKernel) ou Slim** | Reescrever sobre outro micro-framework | 7–9 tarefas **[estimativa]** | Médio-alto: segundo framework de rotas no projeto, duplicando o que o Laravel já faz, sem ganho. Não recomendado. |

Indicação (a decisão é do cliente): **C1**, já que as 7 rotas são poucas e o Laravel novo será a camada HTTP de qualquer
jeito (`/v4/*`). C1 também tira da lista os 4 pacotes travados um por um (o Silex some), sem depender dos outros três.
O custo de C1 só começa depois de o Laravel novo inicializar; antes disso, a `api/V1` continua no runtime 5.6
(mesma regra do `/v4/*`, "Pontos de contato" em `laravel.md`).

**Lacunas do Silex [não medidas]:** (a) se a `api/V1` roda hoje no PHP 8.5 com o `vendor/` atual (Silex 2.2.4 +
Symfony 3); (b) as 7 rotas não têm teste algum no repositório.

## 2. Versão a versão × salto direto

### 2.1 Fatos que sustentam a comparação

Do registro (`docs/registro/laravel.md`, medidas de 14/10/2026 e 03/11/2026):

- Laravel 5.4 não roda em PHP 8; nenhuma versão do Laravel roda no 5.6 **e** no 8.5 → o runtime novo precisa de `vendor/`
  próprio.
- `app/` tem 1.259 arquivos, 771 usam Laravel (61%); `src/` tem 2.651, só 44 usam. **138** rotas `/v4/*` (60 web + 78 api).
- Com Laravel 12: 135 pacotes resolvem, **4 não** (`silex/silex`, `proner/phppimaco`, `dbseller/phinx_postgres`,
  `dbseller/sdk-api-pix-bb`). Legado sobre o `vendor/` novo: 3.294 telas, zero regressão. 29 de 3.910 classes
  deixam de carregar (21 em `src/Console`, 8 em `app/`). O Laravel 12 **não inicializa** (1º provider).
- APIs removidas, medidas por varredura estática: 50 `DB::raw` em `app/` (10.0), 10 helpers `str_*`/`array_*` (6.0),
  5 `$dates` (10.0), 1 `Passport::routes()` (11.0), 105 usos de PhpOffice (1.8 → 5).
- O legado só depende do Eloquent/Capsule, que já roda no 8.5; o custo está todo na camada HTTP.

Da tabela oficial de suporte (seção 3): Laravel 10 roda em PHP 8.1–8.3 e o 11 em 8.2–8.4 — **nenhum dos dois roda no
8.5**. Isto pesa contra a subida em degraus.

### 2.2 Estimativa

Conta dos degraus: 5.4 → 5.5 → 5.6 → 5.7 → 5.8 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 = **12 degraus** (11 até o 12).
O registro fala em "~8 saltos" até o 12: contou menos degraus; vale a conta aqui, que lista todos os majors/minors com guia
oficial de upgrade (`https://laravel.com/docs/<versão>/upgrade`, **[não consultado nesta tarefa]**).

| | Versão a versão | Salto direto + reescrita da camada HTTP |
|---|---|---|
| Unidade de trabalho | cada degrau: ajuste do `composer.json`, correção de `app/`, bateria das 138 rotas | uma matriz de dependências, depois correção de `app/` por assunto |
| Tarefas **[estimativa]** | ≈ 3 por degrau × 12 = **~36**, mais Passport (4 → … → 12.4, uma tarefa por major com mudança de esquema a analisar) **~8**, mais Silex **6–8**: **~50–55** | dependências travadas (4 pacotes) **6–8**; boot, providers, config **4**; Passport 12.4 + auth **3**; `app/` por assunto (`DB::raw`, helpers, `$dates`, PhpOffice 105 usos, `src/Console` 21 classes) **~8**; rotas 138 em lotes **~4**; Silex (C1) **5–7**: **~30–34** |
| Runtimes necessários | os degraus 10 e 11 não rodam no 8.5 (tabela oficial: 8.1–8.3 e 8.2–8.4) e o 5.4 não roda no 8; o projeto tem só 5.6 e 8.5 → vários PHP intermediários a criar para testar os degraus **[estimativa: ~6 imagens; versões exigidas pelos degraus 5.5–9 não consultadas]** | o 8.5 que já existe |
| Pacotes travados | resolvidos em degraus intermediários onde ainda houver versão compatível, **mas todos acabam travando no 12** | tratados uma vez, no alvo |
| Risco principal | cada degrau tem de ficar verde com o Laravel intermediário **em PHP não-8.5** — a comparação 5.6 × novo do projeto (que usa o 8.5) não vale nos intermediários; esforço joga fora o que o degrau seguinte reescreve; Passport nos degraus tem migrations de esquema que a Regra 2 do cliente proíbe aplicar **[hipótese: a verificar degrau a degrau]** | o grande bang no fim: 771 arquivos de `app/` sem um estado intermediário rodando; o Laravel 12 hoje nem inicializa. Mitigação: o legado já está provado sobre o `vendor/` novo (3.294 telas), e o login e o `/v4/*` seguem no 5.6 até o boot funcionar |
| Valor entregue no meio | cada degrau é um Laravel que roda, mas nenhum roda no 5.6 e 8.5 ao mesmo tempo | nada roda até o boot — mas nada do legado depende dele |

As duas colunas são **estimativas por contagem de itens medidos**, não medições: o tamanho de uma "tarefa" é o da
metodologia (≤ meio dia). A razão entre elas (~1,6 a 1,8 vez) é mais confiável que o valor absoluto.

Indicação (decisão (h) é do cliente): **salto direto**, com a ordem do registro — trocar o `vendor/` do 8.5 cedo, portar
`app/` em paralelo, login e `/v4/*` no 5.6 até o boot funcionar. A subida em degraus só vence se o cliente exigir manter
o Laravel antigo em produção durante a migração, caso em que o 5.6 já cumpre esse papel de graça.

## 3. Datas de suporte (consulta em 12/11/2026)

| Produto | Lançamento | Correções (bug fix / suporte ativo) até | Segurança até | Situação em 12/11/2026 |
|---|---|---|---|---|
| **Laravel 12** (PHP 8.2–8.5) | 24/02/2025 | 13/08/2026 | **24/02/2027** | só segurança; ~3,5 meses restantes |
| **Laravel 13** (PHP 8.3–8.5) | 17/03/2026 | Q3 2027 (a página não dá o dia) | **17/03/2028** | correções e segurança |
| **PHP 8.4** | 21/11/2024 | **31/12/2026** | 31/12/2028 | suporte ativo acaba em ~1,5 mês |
| **PHP 8.5** | 20/11/2025 | 31/12/2027 | **31/12/2029** | suporte ativo |

Leitura:

- Laravel 12 já saiu do suporte ativo e sua segurança acaba antes de qualquer migração desta escala terminar; **Laravel 13
  acompanha o PHP 8.5** (ambos com segurança até 2028–2029), então o par 13 + 8.5 é o que dura mais.
- PHP 8.4 só tem suporte ativo até 31/12/2026; escolher 8.4 como alvo é escolher um PHP em modo segurança desde o início.
  O Laravel 13 exige PHP ≥ 8.3, então o 8.4 é possível, mas encurta a vida útil.
- A página do Laravel 12 (`docs/12.x/releases`) ainda lista o 13 como "Q1 2026 / Q3 2027 / Q1 2028"; a do 13
  (`docs/13.x/releases`) tem a data exata (17/03/2026). Vale a da 13.x.

Fontes (todas consultadas em 12/11/2026):

- Laravel 13 — https://laravel.com/docs/13.x/releases (Support Policy)
- Laravel 12 — https://laravel.com/docs/12.x/releases (Support Policy)
- PHP — https://www.php.net/supported-versions.php
- Silex — https://github.com/silexphp/Silex (arquivado em 04/07/2018; README: "DEPRECATED")
- Silex 2.2.4 / 2.3.0 (versões e requisitos) — https://repo.packagist.org/p2/silex/silex.json
- Requisitos do Silex 2.2.4 e do Symfony do Laravel 12 — `docs/migracao-laravel/auditoria/composer-compatibilidade-revisada.md`
- Medições do projeto — `docs/registro/laravel.md`

Tentativa sem sucesso: `https://symfony.com/blog/silex-maintenance-and-support` (404) e, numa primeira chamada,
`https://symfony.com/blog/the-end-of-silex` (falha de rede). O README do Silex já cita o fim de vida (junho de 2018),
então não foi insistido.

## 4. Verificações

- `php -l`: **não se aplica** — nenhum arquivo PHP foi tocado (só `docs/` e uma linha do `CLAUDE.md`).
- Nada instalado, `vendor/` intocado, banco intocado.
