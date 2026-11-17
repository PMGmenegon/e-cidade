# SDK do Pix do Banco do Brasil com o Guzzle do Laravel 13 (medição)

Medido em 14/11/2026, sem nenhuma chamada real: o SDK roda contra um **dublê HTTP local** num container sem rede (`--network none`).
Uso no código: `ecidade/app/Domain/Tributario/Arrecadacao/Pix/Bancos/BancoDoBrasil.php` (`Swagger\Client\…`, pacote `dbseller/sdk-api-pix-bb` 1.0.0, que exige `guzzlehttp/guzzle ^6.2`).

## Conclusão

**Não roda só mudando a restrição de versão.** Com o Guzzle de qualquer conjunto novo (7.16.1, do Laravel 12, ou 8.5.0 + psr7 3.4.0, o da trava do Laravel 13 em `ecidade/composer-runtime-novo.lock`) instalado ao lado do SDK
de hoje, a primeira chamada (`Oauth2Api::gerarAccessToken()`) falha:

```
Error: Call to undefined function GuzzleHttp\Psr7\build_query()
```

A causa é o código gerado do SDK, não a restrição: ele chama funções que o Guzzle novo removeu. Com a **troca mínima abaixo no SDK** ele roda e os **pedidos HTTP saem
idênticos aos do 5.6, byte a byte**, e as respostas viram os mesmos objetos e as mesmas classes de exceção. Isso é o que fica para a decisão sobre o SDK (pedir versão nova à
DBSeller × fork com a troca).

| Combinação | SDK de hoje, sem mudança | SDK com a troca mínima |
|---|---|---|
| PHP 5.6 + Guzzle 6.5.8 (de hoje) | **roda** (referência) | — |
| PHP 8.5 + Guzzle 7.16.1 (Laravel 12) | **não roda** (`build_query` indefinida) | roda; pedidos e resultados iguais ao 5.6 |
| PHP 8.5 + Guzzle 8.5.0 + psr7 3.4.0 (trava do Laravel 13; o 8.4.0 da matriz de versões dá a mesma saída byte a byte) | **não roda** (idem) | roda; pedidos e resultados iguais ao 5.6; 1 diferença na mensagem de erro (abaixo) |

### Troca mínima (26 linhas, 2 arquivos do SDK, nenhuma no código do sistema)

| Chamada removida | Substituta | Onde | Necessária em |
|---|---|---|---|
| `\GuzzleHttp\Psr7\build_query(` | `\GuzzleHttp\Psr7\Query::build(` | `Api/Oauth2Api.php:74,76`; `Api/QrCodesApi.php:205,398,418,735,755,1073,1093,1407,1427,1726,1746` (14 chamadas) | Guzzle 7 e 8 |
| `\GuzzleHttp\json_encode(` | `\GuzzleHttp\Utils::jsonEncode(` | `Api/QrCodesApi.php:379,394,716,731,1054,1069,1388,1403,1707,1722,2038,2053` (12 chamadas) | só Guzzle 8 (o 7 ainda tem a função) |

## O que o `BancoDoBrasil.php` chama

| Linha | Chamada |
|---|---|
| 5, 9–13 | `use` de `GuzzleHttp\Client` e de `Swagger\Client\{Api\Oauth2Api, Api\QrCodesApi, Configuration, Model\ArrecadacaoqrcodesBody, Model\InlineResponse201}` |
| 72–90 (`preparaConfiguracao`) | `Configuration::getDefaultConfiguration()`, `setAmbienteBB`, `setHost`, `setUrlAutenticacaoOauth2`, `setChaveAplicacaoBB`, `setUsername`, `setPassword`; `new Oauth2Api(new Client(['verify' => false]), $config)`; `gerarAccessToken()`; `setAccessToken` |
| 100–114 (`preparaCorpo`) | `new ArrecadacaoqrcodesBody()` e os campos por `ArrayAccess` |
| 45–55 | `new QrCodesApi(new Client(['verify' => false]), $config)`; `criaBoletoBancarioId($envio, $token, $chave)` |
| 59–65 | leitura da resposta `InlineResponse201` (`getTimestampCriacaoSolicitacao`, `getEstadoSolicitacao`, …, `getQrCode`) |

O exercício (`scratchpad/pix_bb/exercicio.php`) refaz exatamente essas chamadas, em quatro situações do dublê: sucesso, erro 400 (corpo de erro do BB), erro 500 e resposta que não é JSON.

## Resultado do dublê

Pedidos gravados pelo dublê (método, URL com a chave de aplicação, cabeçalhos com `Authorization` mascarado, corpo): **8 pedidos, idênticos nas três execuções**
(5.6 × Guzzle 7 com a troca × Guzzle 8 com a troca; `cmp` sem diferença). Respostas (uma linha por etapa, classe do resultado ou da exceção): iguais nas três, nas quatro situações:

| Situação | `gerarAccessToken()` | `criaBoletoBancarioId()` |
|---|---|---|
| sucesso | string do token | `Swagger\Client\Model\InlineResponse201` com os mesmos campos |
| erro 400 | `GuzzleHttp\Exception\ClientException` | `Swagger\Client\ApiException` (código 400) |
| erro 500 | `GuzzleHttp\Exception\ServerException` | `Swagger\Client\ApiException` (código 500) |
| resposta inválida | `NULL` (aviso de propriedade em `null`) | `NULL` |

**Diferença única**, só no texto de `getMessage()` das exceções do Guzzle: no Guzzle 8 a URL da mensagem **não traz a query string** (no 5.6:
`…/pix/arrecadacao-qrcodes?gw-dev-app-key=<chave>`; no Guzzle 8: `…/pix/arrecadacao-qrcodes`) e o trecho do corpo vem numa linha só. O pedido enviado continua levando a chave na query. Quem
registrar ou exibir a mensagem da exceção vai ver o texto sem a chave.

**Avisos do PHP 8.5** (não erros): o código gerado declara parâmetros com padrão `null` sem tipo anulável (`__construct($data = null)`, `QrCodesApi::__construct(…$selector = null)`): `E_DEPRECATED` em cada classe carregada; com o
tratador de erros do sistema isso depende do nível de relatório configurado.

## Nenhuma chamada real

Cada execução roda em `docker run --network none` (container sem interface de rede além do loopback): o SDK é apontado por `Configuration::setHost` e `setUrlAutenticacaoOauth2` para `127.0.0.1:8099`,
onde o dublê (`php -S` com `scratchpad/pix_bb/double.php`) grava todo pedido que recebe. Credenciais usadas: valores de teste fixos (`usuario-de-teste`, `senha-de-teste`, `chave-de-teste`); nenhum segredo real.

## Como reproduzir

```bash
# Guzzle de cada conjunto, em pastas descartaveis (composer no container 8.5):
for v in 7:7.16.1 8:8.5.0; do d=g${v%%:*}; mkdir -p /tmp/pix/$d; echo "{\"require\":{\"guzzlehttp/guzzle\":\"${v##*:}\"}}" > /tmp/pix/$d/composer.json
  docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -v ~/.local/bin/composer:/usr/local/bin/composer:ro -v /tmp/pix/$d:/proj -w /proj \
    --entrypoint php ecidade-login-php85 /usr/local/bin/composer install --no-interaction --no-scripts; done
export G7=/tmp/pix/g7 G8=/tmp/pix/g8
# SDK de hoje (copias com a troca minima):
L=ecidade/vendor/dbseller/sdk-api-pix-bb/lib; cp -r $L /tmp/pix/sdk-p7; cp -r $L /tmp/pix/sdk-p8
find /tmp/pix/sdk-p7 /tmp/pix/sdk-p8 -name '*.php' -exec sed -i 's#\\GuzzleHttp\\Psr7\\build_query(#\\GuzzleHttp\\Psr7\\Query::build(#g' {} +
find /tmp/pix/sdk-p8 -name '*.php' -exec sed -i 's#\\GuzzleHttp\\json_encode(#\\GuzzleHttp\\Utils::jsonEncode(#g' {} +
bash scratchpad/pix_bb/rodar.sh 56 /tmp/pixout                           # sem SDKLIB: SDK de hoje no 5.6
bash scratchpad/pix_bb/rodar.sh g7 /tmp/pixout                           # SDK de hoje: falha em build_query
SDKLIB=/tmp/pix/sdk-p7 bash scratchpad/pix_bb/rodar.sh g7 /tmp/pixout    # com a troca
SDKLIB=/tmp/pix/sdk-p8 bash scratchpad/pix_bb/rodar.sh g8 /tmp/pixout
```

## Versão oficial já publicada (consulta de 14/11/2026)

O repositório público `github.com/DBSeller/sdk-api-pix-bb` tem, além do `1.0.0` usado hoje (referência `bc13e2b`), as branches `master` (`e1c12cb`, merge do PR #2 `php8`, 12/10/2026), `php74` e `php8`. Comparada com o pacote de hoje,
a `master` só troca as **14 chamadas `build_query` por `\GuzzleHttp\Psr7\Query::build`** (28 linhas de diff) e declara `php >=7.4` e `guzzlehttp/guzzle` **exatamente `7.5.0`**. As **12 chamadas
`\GuzzleHttp\json_encode` continuam** (existem no Guzzle 7, não no 8): para o Guzzle 8.5.0 do Laravel 13 faltam essas 12 linhas (`\GuzzleHttp\Utils::jsonEncode`) e relaxar a restrição de versão. O `composer.json` diz
`"license": "proprietary"` e nenhuma branch tem arquivo de licença.

## O que esta medição não prova

Não houve chamada ao BB: o contrato real (campos extras, `Content-Type` do erro, certificados com `verify => false`) segue como está. O conjunto do Laravel 13 existe na trava
(`ecidade/composer-runtime-novo.lock`: `guzzlehttp/guzzle` 8.5.0, `psr7` 3.4.0, `promises` 3.1.0); esta medição instalou só o Guzzle e o psr7 dele (as mesmas versões), e o SDK de hoje ficou
fora da trava (não está em `composer-runtime-novo.json`). Com o 8.4.0 (versão da matriz de versões) a saída é idêntica à do 8.5.0, byte a byte. Nada foi mudado em `composer.json`, `composer.lock`,
`vendor/` ou no código do sistema.
