# Estrutura do código só do PHP 8.5 (PHP8-79, 20/11/2026)

**Resumo:** o PHP 8.5 ganha composer, trava e `vendor/` próprios, sem mudar nada que o 7.4 lê. A lista é
`ecidade/composer-85.json`, a trava `ecidade/composer-85.lock`, e o `vendor/` fica em `runtime-85/vendor/`, fora de
`ecidade/` e fora do git. A sobreposição de classes só do 8.5 fica em `ecidade/app-85/`: só o PSR-4 do
`composer-85.json` a enxerga. Hoje o `composer-85.json` é a cópia do `composer.json` do PR com uma linha a mais (a
sobreposição), e o `composer-85.lock` é a cópia byte a byte do `composer.lock` do PR. O `composer install` no 8.5 passa
com 165 pacotes, ignorando só o teto de versão do PHP, que 10 pacotes ainda pedem (lista abaixo). O desenho reaproveita
o do runtime novo da base anterior (`composer-runtime-novo.json`, `app-runtime-novo/`, `vendor/` montado por cima).

## Onde fica cada coisa

| O quê | Onde | Quem lê |
|---|---|---|
| lista do 8.5 | `ecidade/composer-85.json` | só o Composer chamado com `COMPOSER=composer-85.json` |
| trava do 8.5 | `ecidade/composer-85.lock` (o Composer dá a ela o nome da lista) | idem |
| `vendor/` do 8.5 | `runtime-85/vendor/` na raiz do repositório (`.gitignore`) | o contêiner do 8.5, montado em `/var/www/html/vendor` |
| sobreposição | `ecidade/app-85/` (PSR-4 `"App\\": ["app-85/", "app/"]`, só no `composer-85.json`) | o autoload do `vendor/` do 8.5 |
| imagem do Composer | `docker/composer-85/Dockerfile` | o comando abaixo |
| comando único | `docker/composer-85/composer-85.sh` | quem mexe na trava do 8.5 |

Os dois arquivos ficam ao lado do `composer.json` do 7.4 para que `autoload` (arquivos de `app/Helpers`, `classmap` de
`database`, `psr-4` de `App\`, `Fpdf\` e `Tests\`) use os mesmos caminhos relativos.

**Como o 8.5 escolhe o autoload:** pela montagem, sem variável e sem mudar código. O código carrega
`vendor/autoload.php` (no `bootstrap.php`, no `artisan` e nas entradas do Laravel). No contêiner do 8.5,
`runtime-85/vendor` é montado sobre `/var/www/html/vendor`. O 7.4 continua montando `./ecidade` com o próprio `vendor/`.
O contêiner que roda o Laravel no 8.5 é da etapa da inicialização (PHP8-62). Para ele, falta acrescentar ao serviço do
8.5:

```yaml
    volumes:
      - ./ecidade:/var/www/html/
      - ./runtime-85/vendor:/var/www/html/vendor
      - ./runtime-85/bootstrap-cache:/var/www/html/bootstrap/cache   # o Laravel novo grava cache em outro formato
      - ./runtime-85/storage:/var/www/html/storage
```

No runtime da base anterior foi assim (`docker-compose.runtime-novo.yml`), inclusive com as duas chaves OAuth de
`ecidade/storage` montadas somente leitura por cima do `storage/` próprio.

**Sobreposição:** uma classe em `ecidade/app-85/` com o mesmo nome de uma de `ecidade/app/` vence no 8.5. O
`composer dump-autoload` do 8.5 põe no classmap o arquivo de `app-85/`, e a de `app/` fica para o 7.4. Hoje a pasta
não existe: a primeira classe sobreposta cria a pasta, e depois de criar ou mudar um arquivo nela é preciso rodar o
`dump-autoload` do 8.5 (comando abaixo).

## Comando único (o dono da trava do 8.5 é o time do banco)

Toda mudança de `composer-85.json`/`composer-85.lock` sai deste comando. A imagem é pinada por digest:
`php:8.5-cli@sha256:50956f094e90…` (PHP 8.5.12) mais o binário do `composer:2.11.2@sha256:919efe8e6217…`. As extensões
são as do runtime 8.5 (`docker/php85-apache`): `bcmath calendar gd intl mbstring pgsql pdo_pgsql soap zip exif`. Os
pacotes do sistema (`apt`) da imagem não são pinados, mas a trava depende só da versão do PHP, das extensões e da
versão do Composer, e essas são fixas.

```bash
# gerar/atualizar a trava (resolve no 8.5; nao instala)
bash docker/composer-85/composer-85.sh update --no-install --no-scripts --no-plugins --ignore-platform-req=php+ [pacotes]
# instalar o vendor/ do 8.5 a partir da trava (runtime-85/vendor)
bash docker/composer-85/composer-85.sh install --no-scripts --no-plugins --ignore-platform-req=php+
# depois de criar/mudar classe em ecidade/app-85/
bash docker/composer-85/composer-85.sh dump-autoload --no-scripts --no-plugins
# conferir
bash docker/composer-85/composer-85.sh validate --no-check-publish
bash docker/composer-85/composer-85.sh prohibits php 8.5.12 --locked
```

O script monta `ecidade/` em `/app`, `runtime-85/vendor` em `/app/vendor` e `runtime-85/composer-home` como cache.
Ele roda com o uid de quem chama e com `--network host`, porque a rede bridge desta máquina não resolve DNS. A rede
serve só para baixar pacotes: nada se conecta a banco. O `ecidade/vendor` do 7.4 nunca é montado.

**`--no-scripts` sempre, por enquanto:** os scripts do `composer.json` do PR chamam `$(which php7.4)`, e o
`package:discover` precisa do Laravel de pé. Ligar os scripts no 8.5 é da etapa da inicialização (PHP8-62).

**Revisão:** as tarefas PHP8-60 (`lcobucci/jwt`), PHP8-87 (os 9 pacotes) e a dos documentos mudam a trava com este
comando. O time do banco revisa cada mudança de `composer-85.json`/`.lock`. Ordem dos merges: esta estrutura primeiro,
depois PHP8-60, PHP8-87 e por fim a dos documentos. Cada uma regera a trava sobre a anterior: uma trava não se resolve
por merge de texto.

## `--ignore-platform-req=php+`: os 10 pacotes da trava que excluem o PHP 8.5

`php+` ignora só o teto da versão do PHP; o piso e os `ext-*` continuam conferidos. Saída de
`prohibits php 8.5.12 --locked`, 20/11/2026:

| Pacote (versão na trava) | Exige | Tarefa |
|---|---|---|
| `lcobucci/jwt` 3.4.0 | `^5.6 \|\| ^7.0` | PHP8-60 |
| `bacon/bacon-qr-code` 1.0.3 | `^5.4\|^7.0` | PHP8-87 |
| `dompdf/dompdf` v0.8.6 | `^7.1` | PHP8-87 |
| `ezyang/htmlpurifier` v4.17.0 | `… \|\| ~8.3.0` | PHP8-87 |
| `khanamiryan/qrcode-detector-decoder` 1 | `^5.6\|^7.0` | PHP8-87 |
| `laminas/laminas-escaper` 2.12.0 | `^7.4 \|\| ~8.0.0 \|\| ~8.1.0 \|\| ~8.2.0` | PHP8-87 |
| `mpdf/mpdf` v8.2.4 | `… \|\| ~8.3.0` | PHP8-87 |
| `nette/schema` v1.2.5 | `7.1 - 8.3` | PHP8-87 |
| `nette/utils` v3.2.10 | `>=7.2 <8.4` | PHP8-87 |
| `fzaninotto/faker` v1.9.2 (dev) | `^5.3.3 \|\| ^7.0` | PHP8-87 |

Quando essas tarefas tirarem os 10, o `--ignore-platform-req=php+` sai dos comandos acima e o `prohibits` não
lista nada.

## Medidas (20/11/2026)

- **7.4 intacto:** `sha256` antes e depois, iguais aos da `origin/base-php74`.
  ```
  69367bdca80e74f3c799dee85e20d0b6f40a6abbf03c35eef94259af44fc7420  ecidade/composer.json
  38fe5a633ff3ed8169e0d70c0d8301b54812d24ddb3c61ba68cb23adcb02cbf9  ecidade/composer.lock
  ```
  O PSR-4 do 7.4 continua `"App\\": "app/"`, e o classmap otimizado do 7.4 só varre as pastas desse PSR-4. Nenhum
  `.php` do sistema lê `composer*.json` (o único achado, `securimage/securimage.php:68`, é comentário).
- **Trava:** `composer-85.lock` tem o mesmo `sha256` do `composer.lock` (`38fe5a63…`, `content-hash`
  `5ef6154f379714faf53777f1d4c8d0d1`). O `validate` não acusa trava desatualizada: a linha a mais do
  `composer-85.json` é de `autoload`, que não entra no `content-hash`.
- **Instalação:** `install --no-scripts --no-plugins --ignore-platform-req=php+` com rc=0: 165 pacotes (136 + 29 de
  desenvolvimento, os mesmos do 7.4), 3 min 10 s, `runtime-85/vendor` com 264 MB. Os avisos de classe fora do PSR-4
  (`app/` e `tests/`) são os mesmos do 7.4 (código de hoje).
- **Sobreposição:** com uma cópia temporária de `app/Exceptions/Handler.php` em `app-85/Exceptions/Handler.php`
  (apagada depois, fora do commit), o classmap do 8.5 aponta `App\Exceptions\Handler` para `app-85/`, e
  `ReflectionClass` no 8.5 (contêiner `--network none`, código só leitura) devolve `/app/app-85/Exceptions/Handler.php`.
  `App\Http\Kernel`, que não foi sobreposta, continua em `/app/app/Http/Kernel.php`. Sem a pasta, o classmap não cita
  `app-85/`.
- **Carga do `vendor/autoload.php` no 8.5:** 12 `Deprecated` de parâmetro nulo implícito, nos arquivos de funções
  carregados pelo autoload: `guzzlehttp/promises` (6), `lcobucci/jwt` (3), `opis/closure` (1) e `laravel/framework`
  `helpers.php` (2). São pacotes das tarefas seguintes; aqui só se registra.

## Lint do grupo (CI) e a pergunta ao coordenador

O CI do grupo (`.github/workflows/testes-ci-lint.yml` da branch `testes-ci/lint-incremental-pedromax`) roda
`php -n -d short_open_tag=1 -l` no 7.4 e no 8.5 em **todo `.php` adicionado ou alterado** no PR, sem exceção de
caminho. `composer-85.json`/`.lock`, `docker/composer-85/` e este registro não são `.php`. O `runtime-85/` não é
versionado. O que o CI vai alcançar é a sobreposição `ecidade/app-85/`.

Regra adotada até a resposta: **classe em `app-85/` tem sintaxe válida no 7.4.** Ela pode chamar API só do 8.5/Laravel
13, porque o lint não executa, mas não pode usar sintaxe só do PHP 8 (tipos `mixed`/união/`static` de retorno,
`match`, argumentos nomeados, `readonly`, `enum`, promoção no construtor, atributos `#[...]` fora de comentário).

**Pergunta ao coordenador (levar pelo cliente):** quando uma classe sobreposta precisar implementar uma assinatura do
Laravel 13 que exige sintaxe só do PHP 8 (por exemplo, retorno `mixed` numa interface do framework), o job do 7.4 do
lint pode pular `ecidade/app-85/`? O 7.4 nunca carrega essa pasta. Ou o grupo prefere outro caminho (por exemplo, a
sobreposição fora de `ecidade/`, montada só no contêiner do 8.5)? Até a resposta vale a regra acima, e uma classe que
não couber nela fica registrada como pendente.

## Lacunas

- O contêiner do 8.5 com `runtime-85/vendor` montado ainda não existe: é da inicialização (PHP8-62). O 8.5 de hoje
  (`docker-compose.php85.yml`) continua com o `vendor/` do 7.4.
- Nada do Laravel foi exercitado no 8.5: só a carga do `vendor/autoload.php` e o autoload de uma classe.
- `runtime-85/` não é versionado: quem for usar roda o `install` acima (3 min).
