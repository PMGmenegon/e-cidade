# Camada de sistema: rotas /v4, API V1 e login, 5.6 × novo (T-012, 12/11/2026)

Módulo novo em `ecidade/tests/sistema/`, plugado na camada **sistema** da suíte da T-008
(`tests/suite/camadas/sistema.lista`; entradas `|85`: o teste roda uma vez e fala com **os dois** runtimes por HTTP).
Não toca `scratchpad/cmp.py` (T-011) nem `rodar.sh` (T-008).

## Como rodar

```bash
bash <quadro>/ferramentas/sobe-ambiente.sh <Agente> <worktree> <porta-base>
echo <agente> > ecidade/tests/sistema/.agente        # ou SISTEMA_AGENTE=<agente> / SISTEMA_URL_56 + SISTEMA_URL_85 (gitignorado)
node <quadro>/ferramentas/suite.mjs bash ecidade/tests/suite/rodar.sh --camada sistema --agente <agente>
docker exec -w /var/www/html ecidade_<agente>_56 php tests/sistema/gera-rotas.php      # regenera dados/rotas-*.tsv do código
docker exec -w /var/www/html ecidade_<agente>_56 php tests/sistema/classifica-get.php  # regenera dados/get-classificacao.tsv
bash ecidade/tests/sistema/trava-leitura.sh <Agente> <porta-base> <pasta-saida>        # prova de não gravar (containers somente leitura)
```

Sem `.agente`/variáveis os testes saem **pulados** com a mensagem do que definir. (Sugestão à T-008: `rodar.sh` repassar
`-e SISTEMA_AGENTE=$AGENTE` no `docker exec`; hoje não repassa, por isso o arquivo `.agente`.) Relatório por rota em
`tests/suite/relatorios/sistema-rotas-*.tsv` (rota, resultado 5.6, resultado 8.5, igual/DIFERENTE).

## O que compara

- **Listas geradas do código** (`gera-rotas.php`, roda no 5.6, onde o Laravel 5.4 sobe): `dados/rotas-v4.tsv` = **562** rotas
  do Laravel (186 GET, 361 POST, 12 DELETE, 2 PUT, 1 PATCH; 543 `/v4/api`, 15 `/v4/oauth`, 4 `/rest/v1`) — o "138" do
  `laravel.md` estava defasado; `dados/rotas-api-v1.tsv` = **7** rotas da API V1 (Silex, lidas de `api/V1/Providers`).
- **Token válido** (pré-obtido por `prepara.php` e gravado em `/tmp/ecidade-sistema-segredos/{token,sessao-56,sessao-85}` dentro do container, modo 0600, fora do docroot e apagado ao fim da trava; em CLI apenas; o `.gitignore` de `tests/sistema/` só cobre `.agente`): `POST /v4/oauth/token` (password grant, usuário `dbseller`) no 5.6, enviado aos dois (banco e chave
  são compartilhados). Cliente/segredo lidos do config por `credenciais.php`, nunca impressos.
- **Comparação:** status + tipo + corpo normalizado (JSON sem token/expiração/stacktrace; HTML sem espaços e sem o `sid` do captcha).
- **Só GET, e só as comprovadamente de leitura** (decisão de 13/11): duas provas, ambas sem tocar no banco
  (proibidos: `log_statement`/`ALTER DATABASE` e cópia `_teste`):
  1. **Leitura estática dos controllers** (`classifica-get.php`, roda no 5.6): as 186 GET (`dados/get-classificacao.tsv`, rota,
     ação, classe, trecho) → **162 "leitura"** e **24 "grava/duvidosa"**: 17 com verbo de efeito no nome (`assinar`, `emitir`,
     `exclusao-geral`, `encerramento`, `inativar`, `processar`, `importar`…) cujo corpo só delega a serviço (não seguido), 6 cuja
     ação não existe ou é `Closure` (`Jetom\FuncaoController@all/find`, `ArquivoPontoController@index/show`, `ProcessarArquivoTefController@show`,
     `saude/ambulatorial/cid`, `user` — classe ausente: o 5.6 responde 500, defeito pré-existente) e `oauth/authorize` (`session()->put`).
     Limite honesto: o corpo do método do controller é lido, o que ele delega não.
  2. **Trava somente leitura em execução** (`trava-leitura.sh`): sobe o par de containers com `SOMENTE_LEITURA=1`
     (`PGOPTIONS=-c default_transaction_read_only=on`; o banco não é alterado) depois de pedir token e sessões nos containers normais
     (login grava log/token/sessão, exceção permitida; as sessões legadas, que vivem no filesystem do container, são copiadas para os
     travados) e roda a mesma bateria. **Resultado (13/11): nas GET cobertas (158 `/v4`, 4 `/rest/v1` e 4 da V1), a resposta do 5.6
     foi idêntica à da rodada normal — nenhuma tentou gravar**, nem tabela temporária.
  As 24 duvidosas ficam **fora da cobertura** (`dados/get-fora-da-cobertura.tsv`, com o motivo; não é regressão) e as **376 não-GET**
  também (escrevem). Cobertas hoje: **158 GET `/v4`**, 4 `/rest/v1`, 4 da V1.
- **API V1:** exige sessão legada, não bearer — o teste faz login (`login.php` + `abrir.php`) em cada runtime e envia o cookie.
  As 3 POST (`auth/login`, `matriculaonline/inscricao`, `tributario/recibo`) não são chamadas (escrevem).
- **Login (legado, regra 3 do cliente de 13/11):** tela, cookie de sessão, token sem credenciais, `abrir.php` com senha certa e errada,
  `inicio.php` com a sessão e emissão de token no runtime novo; mesmas respostas nos dois. Fica por último. Não usa a bateria de
  segurança de `nucleo/login-seguranca` (testa correções que não entram: T-013 revertida).

## Não coberta pela bateria (critério 3) — `dados/nao-cobertas.tsv`, conferido contra o código por `SistemaNaoCobertasTest`

- **5 relatórios que sobem o kernel** (`con2_lrfdivida002_2018`, `con2_lrfgarantias002_2018`, `con2_lrfresumido002_2018`,
  `con2_opercredito002_2018`, `con2_anexovirgf_002`): `require bootstrap/app.php` + `Http\Kernel::handle()` dentro da página;
  só rodam no 5.6 e não expõem rota `/v4` a comparar.
- **30 arquivos que chamam `/v4` por JavaScript/XHR** (lista no `.tsv`): exigem navegador (sessão + DOM); por linha de comando
  só se exercita a rota (já nos testes de rota), não a tela. Cobertos por camada de navegador, se houver.

## Linha de base de hoje (critério 4), medida em 12/11/2026

| Teste | Resultado | Detalhe |
|---|---|---|
| Rotas `/v4/*` GET (158) | **0 iguais, 158 diferem** | o 8.5 responde `500 text/html` vazio em todas (Laravel 5.4 não roda em PHP 8); no 5.6 (158 GET, medido 3 vezes em 13/11, idêntico): 84 × 200, 32 × 500, 20 × 422, 16 × 406, 5 × 400, 1 × 410 |
| `/rest/v1/*` GET (4) | 0 iguais | 5.6: `403 {"error":true,"message":"Acesso negado!"}` nas 4; 8.5: `500 text/html` vazio |
| API V1 Silex (4 GET) | **4 iguais** (2 × 200, 2 × 500 nos dois) | a V1 já funciona no 8.5 com a sessão compartilhada |
| Login | difere | `POST /v4/oauth/token`: 5.6 `400 json`, 8.5 `500 html`; tela e `abrir.php` (certa/errada) **iguais**; o 8.5 não emite token |
| Não cobertas (5 + 30) | confere com o código | |

**500 do 5.6 são linha de base.** As 32 rotas `/v4` que já respondem 500 no 5.6 (defeito pré-existente ou parâmetro de teste `1`
que não existe) estão em `dados/get-500-base-5.6.tsv`. Depois do Laravel novo, **500 igual nos dois é o esperado** para elas; só é
regressão se uma delas passar a diferir de forma diferente (ex.: 500 no 5.6 e 200 no novo é divergência a examinar, não ganho a comemorar).

**Lacuna — `/rest/v1`:** com o bearer do password grant, as 4 rotas respondem `403 Acesso negado!` no 5.6 (o token do login não dá
o escopo/permissão que o grupo `rest/v1` exige). Logo a cobertura de `/rest/v1` compara hoje **só a recusa de acesso, não o conteúdo**
das respostas. Cobrir o conteúdo exigiria um cliente/token com acesso a esse grupo, que não existe no ambiente de teste (e criar um
seria gravar no banco: Regra 2).

Resultado da camada: 6 testes, 2 aprovados (V1, lista de não cobertas), 4 reprovados — a suíte fica vermelha até o Laravel novo
subir; é a linha de base esperada, não regressão.
