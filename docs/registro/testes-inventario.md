# Inventário dos testes existentes (T-009, 13/11/2026)

Escopo: `ecidade/tests/{Unit,Feature}` e `ecidade/tests/cypress`. Executor **único**: `ecidade/tests/suite/rodar.sh` (T-008);
os testes entram pelas listas `camadas/unitario.lista` e `camadas/lacunas.lista`. Medido em `ecidade_front2_56` (PHP 5.6.40, phar
PHPUnit 5.7.27) e `ecidade_front2_85` (PHP 8.5.12).

## Resumo (camada unitária pelo `rodar.sh`, com as 2 amostras da T-008)

| | 5.6 (PHPUnit 5.7.27) | 8.5 (PHPUnit 9.6.38) |
|---|---|---|
| Arquivos de teste existentes | 46 rodam | **10 rodam**, 36 em `lacunas.lista` com motivo |
| Testes | **277/277** passam (275 existentes + 2 amostras) | 71/73 passam (69/71 existentes), **2 falham** |
| `tests/Feature` | só `.gitkeep` | idem |

Nenhum teste grava no banco nem chama terceiro (nenhum casa com DB/Eloquent/HTTP/curl/Pix/TEF; a suíte do 5.6 passa com
`--network none`, sem o `ecidade_database` alcançável): **sem dublê a criar, sem lacuna de gravação**.

## Versão do PHPUnit do 8.5: medida, não escolha (decisão do Lider)

Testes existentes, só com a adaptação mecânica abaixo, **sem** alterar asserção, pelo mesmo bootstrap:

| PHPUnit do 8.5 | testes executados | passam | motivo da diferença |
|---|---|---|---|
| 12.5.0 (fixado pela T-008) | 26 | **5** | o 12 não lê `@dataProvider` (só atributo): os testes com data provider viram erro |
| **9.6.38** (escolhido) | 71 | **69** | lê as anotações do 5.7 |

`ferramentas.sha256` passou a fixar `phpunit-9.6.38.phar` (sha256 `6b5235f2…98d7`) para o runtime 85; só essa linha mudou.

## Adaptações (declaradas no próprio teste, comentário `T-009`); nenhuma asserção alterada

Em 10 arquivos de `tests/Unit/V3/`: `PHPUnit_Framework_TestCase` → `PHPUnit\Framework\TestCase` (alias que existe no 5.7) e nome da
classe igualado ao do arquivo (o 9/12 exige; o 5.7 não). Classes renomeadas: `TraceTeste`→`TraceTest` (`V3/Error/TraceTest.php`) e
`DataTest`→`FileTest` (`V3/Modification/Data/FileTest.php`). Outros dois arquivos de Água têm classe ≠ arquivo e **não foram
tocados** (estão em lacuna): `Tributario/Agua/CalculaConsumoTest.php` (classe `CalculoConsumoTest`) e
`Tributario/Agua/CalcularConsumoLeituraTest.php` (classe `CalcularConsumoLeitura`).
`tests/suite/bootstrap.php` passou a carregar também o `bootstrap.php` do e-cidade (o mesmo que o `phpunit.xml` usa; sem ele
as classes de `src/` não carregam).

## Lacunas no 8.5 (36 arquivos, em `lacunas.lista`)

- **33 arquivos que estendem `Tests\TestCase`**: a base herda de `MockeryTestCase` do Mockery antigo do `vendor/`, cujo `setUp()`
  não tem `: void`; fatal no PHPUnit 9/12 (silencioso: o handler do `bootstrap.php` engole o fatal). Destrava com o Mockery novo (tarefa do vendor).
- **3 arquivos com `setUp()` sem tipo** (`Extension/ContainerTest`, `LoggerTest`, `ParameterBagTest`): o PHPUnit 9 exige `: void`, que não compila no 5.6.
- Fora da suíte: `tests/Unit/Recadastramento.php` (sem sufixo `Test.php`; 4/5 no 5.6, `testCampoValor` falha já no 5.6) e
  `tests/cypress` (T-011/T-012).

## Falhas reais no 8.5 (2 testes): achados, **não adaptados**

1. `V3/Error/Handler/ShutdownTest::testHandleExpectNothing`: `src/V3/Error/Handler/Error.php:20` `_handle($type,$message,$file,$line,$context)` exige o
   5º argumento que o PHP 8 não passa mais; qualquer aviso com esse handler vira `ArgumentCountError` (defeito de portabilidade do núcleo).
2. `V3/Error/Handler/ErrorTest::testHandleWithoutReporting`: usa `error_reporting(null)`; no PHP 8 `null` só consulta o nível.

Aviso para quando os 36 arquivos entrarem: numa cópia adaptada descartada (decisão do Lider) medi que `assertEquals` de float e `assertContains`
do PHPUnit 9 são mais estritos que os do 5.7 e fariam falhar `CalculoPercentual` e `Economia` (o valor é o mesmo nos dois PHP). Isso deve
aparecer como falha registrada, não ser mascarado.

## Arquivos (ecidade/tests/Unit) e onde rodam

| arquivo | 5.6 | 8.5 |
|---|---|---|
| Configuracao/Api/Generator/HashGeneratorTest.php | roda (3 testes) | lacuna (ver acima) |
| Configuracao/Model/DBRegistryTest.php | roda (9 testes) | lacuna (ver acima) |
| Core/Helpers/HourHelperTest.php | roda (2 testes) | lacuna (ver acima) |
| ExampleTest.php | roda (1 testes) | lacuna (ver acima) |
| Financeiro/Contabilidade/Msc/LancamentoRepositoryTest.php | roda (2 testes) | lacuna (ver acima) |
| Patrimonial/Licitacao/LicitaCon/JulgamentoTest.php | roda (3 testes) | lacuna (ver acima) |
| Patrimonial/Licitacao/LicitaCon/SituacaoTest.php | roda (8 testes) | lacuna (ver acima) |
| Patrimonial/Licitacao/LicitaCon/VersaoTest.php | roda (2 testes) | lacuna (ver acima) |
| RecursosHumanos/ESocial/Factory/EsocialPreenchimentoValidatorFactoryTest.php | roda (2 testes) | lacuna (ver acima) |
| RecursosHumanos/ESocial/Factory/SugestaoPreenchimentoTest.php | roda (2 testes) | lacuna (ver acima) |
| RecursosHumanos/ESocial/Validators/ServidorPreenchimentoValidatorTest.php | roda (2 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Model/ControleRubricasParametrosTest.php | roda (7 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Model/PontoTest.php | roda (1 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Model/ServidorMovimentacaoTest.php | roda (36 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Model/ServidorTest.php | roda (2 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Model/SindicatoTest.php | roda (7 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Repository/DependenteRepositoryTest.php | roda (1 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Repository/ServidorMovimentacaoRepositoryTest.php | roda (3 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Service/ControleRubricasCalculoServiceTest.php | roda (7 testes) | lacuna (ver acima) |
| RecursosHumanos/Pessoal/Service/ControleRubricasMatriculasServiceTest.php | roda (5 testes) | lacuna (ver acima) |
| Tributario/Agua/CalculaConsumoTest.php | roda (7 testes) | lacuna (ver acima) |
| Tributario/Agua/CalcularConsumoLeituraTest.php | roda (3 testes) | lacuna (ver acima) |
| Tributario/Agua/CalculoPercentualTest.php | roda (4 testes) | lacuna (ver acima) |
| Tributario/Agua/CalculoTarifaBasicaTest.php | roda (2 testes) | lacuna (ver acima) |
| Tributario/Agua/Isencao/DescontoTest.php | roda (3 testes) | lacuna (ver acima) |
| Tributario/Agua/Isencao/ImuneTest.php | roda (1 testes) | lacuna (ver acima) |
| Tributario/Agua/Isencao/LeiOrganicaTest.php | roda (1 testes) | lacuna (ver acima) |
| Tributario/Agua/IsencaoFactoryTest.php | roda (4 testes) | lacuna (ver acima) |
| Tributario/Agua/Leitura/Regra/PenalidadeTest.php | roda (6 testes) | lacuna (ver acima) |
| Tributario/Agua/Leitura/RegraFactoryTest.php | roda (10 testes) | lacuna (ver acima) |
| Tributario/Agua/Processamento/CondominioTest.php | roda (2 testes) | lacuna (ver acima) |
| Tributario/Agua/Processamento/EconomiaTest.php | roda (10 testes) | lacuna (ver acima) |
| Tributario/Agua/Repository/LeituraTest.php | roda (5 testes) | lacuna (ver acima) |
| V3/Error/EntityFactoryTest.php | roda (1 testes) | roda |
| V3/Error/EntityTest.php | roda (18 testes) | roda |
| V3/Error/EventHandlerTest.php | roda (3 testes) | roda |
| V3/Error/Handler/ErrorTest.php | roda (2 testes) | roda |
| V3/Error/Handler/ExceptionTest.php | roda (1 testes) | roda |
| V3/Error/Handler/ShutdownTest.php | roda (1 testes) | roda |
| V3/Error/TraceTest.php | roda (1 testes) | roda |
| V3/Extension/ContainerTest.php | roda (5 testes) | lacuna (ver acima) |
| V3/Extension/LoggerTest.php | roda (5 testes) | lacuna (ver acima) |
| V3/Extension/ParameterBagTest.php | roda (31 testes) | lacuna (ver acima) |
| V3/Extension/RegistryTest.php | roda (1 testes) | roda |
| V3/Modification/Data/FileTest.php | roda (4 testes) | roda |
| V3/Modification/Parse/OperationTest.php | roda (39 testes) | roda |
