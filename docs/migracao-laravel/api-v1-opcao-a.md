# API V1 (Silex): opcao A - manter isolada - e o contrato na suite de testes

Registro da escolha para a `api/V1` (7 rotas, Silex 2) e do que a suite de testes passou a cobrir. A medicao esta em
`api-v1-silex-85.md` (T-033), a infraestrutura em `api-v1-container.md` e `api-v1-dependencias.md` (T-046, T-047), as linhas de base
em `docs/registro/testes-sistema-rotas.md`, `testes-sistema-api-v1-post.md` e `testes-login-api-v1.md`.

## A escolha

**Opcao A: manter o Silex em um `vendor/` so da API e servir a API por um container proprio.** A alternativa (C1) era reescrever as
7 rotas no Laravel 13 com a mesma resposta. A regra de decisao era: se a API isolada roda no 8.5 com resposta igual a do 5.6, mantem;
senao, reescreve.

Numeros da medicao (T-033, 8.5, vendor so da API):

| Item | Valor |
|---|---|
| Pacotes resolvidos pelo Composer (Silex 2.3.0 + Symfony 4.4) | 31 pacotes, 8,6 MB |
| 4 rotas GET, 5.6 x API isolada no 8.5, **com** a correcao do handler de erro V3 (T-026) | 4 de 4 iguais |
| as mesmas 4 rotas **sem** a T-026 | 2 de 4 diferem (200 vazio no lugar do 500 JSON) |
| `composer audit` do vendor de 4.x | 8 alertas em 3 pacotes (`http-foundation`, `http-kernel`, `routing`), sem correcao dentro da 4.x |

## Versoes: ficam as de hoje

Entre Symfony 4.4 (tags estaveis ou ramo `4.4.x-dev`) e manter as versoes de hoje, ficou **manter as de hoje: Silex 2.2.4 +
Symfony 3.4**, so para a API. A T-033 mediu o vendor de hoje no 8.5 igual ao 5.6 nas 4 rotas. A API passa a ter 23 pacotes, todos na
mesma versao e referencia do `ecidade/composer.lock` de hoje (0 diferencas), sem `laravel/framework`. `cakephp/utility` declara
PHP < 8: o `composer install` da API usa `--ignore-platform-req=php`, so nesse comando; o 5.6 e o conjunto do Laravel novo nao mudam.

**Alertas de seguranca do Symfony 3.4 (herdados, so documentados).** `composer audit --locked` sobre a trava da API (3.4.49):
8 alertas em 3 pacotes - `symfony/http-foundation` 4 (1 alta, 1 baixa, 2 sem severidade), `symfony/http-kernel` 2 (1 media),
`symfony/routing` 2 (medias). Sao os mesmos 8 alertas em 3 pacotes do 4.x e ja existem no vendor que o 5.6 usa hoje; nenhuma das
opcoes os fecha (so a reescrita no Laravel, descartada pela medicao). Nao foram alterados.

## Caminho escolhido: container proprio com regra no proxy

Duas formas de a API usar o seu `vendor/` e o Laravel novo o dele no mesmo codigo: escolher o autoload pela porta de entrada
(mexe em `bootstrap.php`, `bootstrap/autoload.php` e `FrontController.php`) ou um container so da API com regra `/api/v1/` no proxy.
Ficou o container: so infraestrutura, nenhum arquivo do sistema muda e segue o padrao que o proxy ja usa para mandar cada prefixo
ao runtime certo. Medido (T-047): `/api/v1/` pelo proxy novo responde igual ao 5.6 nas 4 GET; 233 telas de menu em 7 areas iguais
entre proxy antigo e novo; sem o container da API no ar, o proxy manda `/api/v1/` ao destino de hoje (o 5.6) e a resposta e igual; o 502 so acontece quando a API ja recebeu o pedido e nao respondeu (o POST nao e repetido). As telas seguem 200.

## O que a suite cobre (camada sistema)

`ecidade/tests/suite/camadas/sistema.lista` roda, pelo `rodar.sh` e por `suite.mjs`, estes testes da API V1 comparando o 5.6 com o alvo novo:

| Teste | Cobre | Resultado (14/11/2026) |
|---|---|---|
| `SistemaRotasTest::testRotasApiV1SilexIguaisNosDoisRuntimes` | 4 GET (`formulario`, `emissaoProtocolo`, `cgm`, `cgm/1`) | 4 de 4 iguais |
| `SistemaApiV1PostTest` | POST de `recibo` e `inscricao` so nos caminhos de erro (2 rotas x 8 casos) | 16 de 16 iguais |
| `SistemaLoginApiV1Test` | login da API, 15 casos sem cliente valido, 5.6 x novo e 5.6 x linha de base versionada | 15 de 15 iguais |

O alvo "novo" e o container proprio da API quando `SISTEMA_URL_API` aponta para ele (por exemplo `http://ecidade_front2_api`, ou o
proxy com a regra `/api/v1/`); sem a variavel, e o 8.5 de hoje. O `rodar.sh` repassa a variavel ao container. Medido com os dois alvos:
8.5 de hoje e container da API (23 pacotes, o log do container registrou 35 pedidos a `/api/v1/` por rodada, 4 GET + 16 POST + 15 de login, 70 nas 2 rodadas), iguais nos dois;
2 rodadas seguidas com o mesmo relatorio; vigia do banco com rc=0 em cada rodada (so `db_logsacessa*`, `db_usuariosonline` e
`oauth_*` mudaram; `db172_ultima_utilizacao` inalterada).

## Lacunas

- **Sucesso dos POST** (`recibo`, `inscricao`, `auth/login` com cliente valido): gravam o cliente da API (`db172_ultima_utilizacao`),
  a trilha de auditoria (`db_acount*`), o recibo e a inscricao; ficam sem linha de base.
- **Cliente da API valido**: nao ha cliente de teste em banco descartavel; o login com credencial certa ou errada, usuario
  inexistente, campos vazios ou tipos trocados fica fora (os 15 casos cobrem so o que para antes da gravacao).
- **Alertas do Symfony 3.4**: herdados e nao corrigidos (secao acima).
- **Runtime do Laravel novo** sem Symfony 3.4: so se prova com o vendor do Laravel novo; repetir a medicao do container e destes testes
  quando ele existir.
