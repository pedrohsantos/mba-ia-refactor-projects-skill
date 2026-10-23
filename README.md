# refactor-arch — Skill de Auditoria e Refatoração Arquitetural para MVC

Skill para o **Claude Code** (`/refactor-arch`) que analisa uma codebase backend, audita anti-patterns com severidade e `arquivo:linha`, gera um relatório padronizado, **pede confirmação** e então refatora o projeto para MVC, validando que a aplicação continua de pé e que os endpoints originais continuam respondendo.

Executada nos 3 projetos legados do desafio (2× Python/Flask, 1× Node.js/Express). O enunciado original está em [ENUNCIADO.md](ENUNCIADO.md).

| Projeto | Stack | Findings (C/H/M/L) | Endpoints após refatoração |
|---|---|---|---|
| [code-smells-project](code-smells-project/) | Python + Flask 3.1 + sqlite3 | 6 / 4 / 4 / 4 = **18** | 22/22 status iguais ao baseline |
| [ecommerce-api-legacy](ecommerce-api-legacy/) | Node.js + Express 4 + sqlite3 | 4 / 5 / 5 / 4 = **18** | 7/7 status iguais ao baseline |
| [task-manager-api](task-manager-api/) | Python + Flask 3.0 + SQLAlchemy | 2 / 5 / 6 / 5 = **18** | 22/22 endpoints + 13 casos de segurança (42/42) |

---

## A) Análise Manual

Feita lendo todo o código dos 3 projetos **antes** de escrever a skill. Os achados viraram as entradas do catálogo de anti-patterns. Severidades seguem a escala do enunciado (CRITICAL → LOW).

### Projeto 1 — code-smells-project (Python/Flask, e-commerce)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **SQL Injection** em praticamente todas as queries (concatenação de strings) | `models.py:28, 47-50, 109-111, 289-299…` | O login aceita `' OR '1'='1' --`; qualquer dado pode ser lido/alterado. |
| 2 | CRITICAL | **Endpoint que executa SQL arbitrário** e reset do banco **sem autenticação** | `app.py:47-78` | Qualquer cliente anônimo destrói ou lê o banco inteiro. |
| 3 | CRITICAL | **Credenciais hardcoded** (SECRET_KEY) e **vazadas no /health** | `app.py:7`, `controllers.py:289` | Segredo no git e exposto publicamente. |
| 4 | CRITICAL | **Senhas em texto puro** e retornadas em `GET /usuarios` | `database.py:75-83`, `models.py:79-86` | Vazamento direto de credenciais de todos os usuários. |
| 5 | CRITICAL | **God modules**: `models.py` mistura SQL, regra de desconto, estoque e formatação de 4 domínios | `models.py:1-314` | Impossível testar/alterar uma parte sem afetar as outras. |
| 6 | HIGH | Conexão SQLite **global mutável** com `check_same_thread=False` | `database.py:4-11` | Concorrência entre requisições e transações vazando. |
| 7 | HIGH | Criação de pedido **sem transação** (pedido, itens e estoque) | `models.py:133-169` | Falha no meio deixa dados inconsistentes. |
| 8 | MEDIUM | **N+1** ao listar pedidos (1 query por pedido + 1 por item) | `models.py:171-233` | Escala linearmente com o volume. |
| 9 | MEDIUM | **Validação ausente**: preço string → 500; quantidade negativa *aumenta* estoque | `controllers.py:43-46`, `195-201` | Erros 500 e corrupção de estoque. |
| 10 | LOW | **Magic numbers** nas faixas de desconto (10000/0.1, 5000/0.05…) | `models.py:256-262` | Regra de negócio escondida. |
| 11 | LOW | `print()` como log (inclusive e-mail de usuários) e imports sem uso | `controllers.py:8…`, `models.py:2` | Observabilidade pobre e ruído. |

### Projeto 2 — ecommerce-api-legacy (Node.js/Express, LMS com checkout)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Chave live do gateway e senha de banco hardcoded** | `src/utils.js:1-7` | Credenciais de produção no repositório. |
| 2 | CRITICAL | **Log do número completo do cartão + chave do gateway** | `src/AppManager.js:45` | Violação de PCI-DSS. |
| 3 | CRITICAL | **God class `AppManager`** (conexão, schema, seed, rotas, pagamento, relatório) | `src/AppManager.js:4-139` | Nada é testável isoladamente. |
| 4 | CRITICAL | **Rotas admin abertas** (relatório financeiro e DELETE de usuário) | `src/AppManager.js:80, 131` | Qualquer um apaga usuários. |
| 5 | HIGH | **"Criptografia" caseira** (`badCrypto`: base64 truncado) e senha padrão "123456" | `src/utils.js:17-23`, `AppManager.js:68` | Senhas recuperáveis trivialmente. |
| 6 | HIGH | **Callback hell sem transação** no checkout (5 níveis) | `src/AppManager.js:37-77` | Matrícula sem pagamento em caso de falha. |
| 7 | MEDIUM | **N+1** no relatório financeiro com contadores manuais | `src/AppManager.js:83-128` | 1 + C + 2·M queries e ordem não determinística. |
| 8 | MEDIUM | **Erros ignorados**: `enrollments.length` com `err` derruba o processo | `src/AppManager.js:92-93` | Crash do servidor. |
| 9 | MEDIUM | **Integridade referencial**: delete deixa matrículas/pagamentos órfãos | `src/AppManager.js:131-136` | O próprio código admite "dados sujos". |
| 10 | LOW | **Nomes crípticos** (`u, e, p, cid, cc`) | `src/AppManager.js:29-33` | Legibilidade. |
| 11 | LOW | **Código morto** (`totalRevenue`, `dbUser`, `smtpUser`) e magic strings (`"4"`, `"PAID"`) | `src/utils.js:10`, `AppManager.js:46` | Ruído e regras escondidas. |

### Projeto 3 — task-manager-api (Python/Flask, Task Manager parcialmente em camadas)

| # | Severidade | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **SECRET_KEY e senha SMTP hardcoded** | `app.py:13`, `services/notification_service.py:7-10` | Segredos no git. |
| 2 | CRITICAL | **Hash da senha retornado** em `to_dict()` (GET/POST/PUT users, login) | `models/user.py:16-25` | Hash MD5 vaza para o cliente. |
| 3 | HIGH | **MD5 sem salt** para senhas | `models/user.py:27-32` | Quebrável por rainbow table. |
| 4 | HIGH | **Rotas gordas**: queries, regras e validação nos Blueprints (sem controllers) | `routes/*.py` | A "organização" em pastas esconde a falta de camadas. |
| 5 | HIGH | **Token falso** `fake-jwt-token-<id>` e qualquer um cria `role: admin` | `routes/user_routes.py:210, 71` | Escalada de privilégio trivial. |
| 6 | MEDIUM | **N+1** em `/tasks`, `/users`, `/reports/summary`, `/categories` | `routes/task_routes.py:41-57`… | Muitas queries por requisição. |
| 7 | MEDIUM | **APIs deprecated**: `datetime.utcnow()` (22×) e `Query.get()` (16×) | vários | Warnings hoje, quebra no futuro. |
| 8 | MEDIUM | **Regra de atraso duplicada 6×** apesar de existir `Task.is_overdue()` | `routes/task_routes.py:30-39`… | Divergência garantida. |
| 9 | MEDIUM | **`except:` sem tipo** e nenhum error handler | `routes/task_routes.py:62`… | Bugs silenciosos, respostas HTML 500. |
| 10 | LOW | **Imports e módulos mortos** (`utils/helpers.py`, `os, sys, json, time`) | `routes/task_routes.py:7`… | Ruído. |
| 11 | LOW | **Condicionais verbosas** (`if x: return True else: return False`) e magic strings de status | `models/task.py:38-60`, `models/user.py:34-38` | Legibilidade. |

---

## B) Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                              # o "prompt": 3 fases, regras e formatos de saída
├── references/
│   ├── project-analysis.md               # Fase 1 — heurísticas de linguagem/framework/DB/domínio/arquitetura
│   ├── anti-patterns-catalog.md          # Fase 2 — 22 anti-patterns com sinais de detecção e severidade
│   ├── audit-report-template.md          # Fase 2 — template obrigatório do relatório
│   ├── mvc-guidelines.md                 # Fase 3 — camadas, responsabilidades, layouts por stack
│   ├── refactoring-playbook.md           # Fase 3 — 14 transformações (+ T-13b autorização por papel) com código antes/depois
│   └── validation.md                     # Fase 3 — baseline, boot, replay dos endpoints, scan estático
└── scripts/
    └── smoke_test.py                     # runner HTTP agnóstico (stdlib) usado no baseline e na validação
```

| Área exigida | Arquivo |
|---|---|
| Análise de projeto | `references/project-analysis.md` |
| Catálogo de anti-patterns | `references/anti-patterns-catalog.md` |
| Template de relatório | `references/audit-report-template.md` |
| Guidelines de arquitetura | `references/mvc-guidelines.md` |
| Playbook de refatoração | `references/refactoring-playbook.md` |

### Decisões de design

- **SKILL.md enxuto e procedural.** Ele diz *o que fazer e em que ordem* (fases, regras, blocos de saída exatos, quando parar). O conhecimento de domínio fica nas referências, carregadas **somente na fase que precisa** — progressive disclosure, para não gastar contexto com o playbook durante a análise.
- **Contrato de endpoints como primeira classe.** A Fase 1 gera um inventário `METHOD /path → arquivo:linha`; a Fase 3 captura um **baseline executando a aplicação original** antes de mudar qualquer arquivo, e compara status por status depois. Isso transforma "a aplicação continua funcionando" em algo verificável.
- **Mudanças de contrato só para remover vulnerabilidade**, e sempre listadas (ex.: não retornar mais senha; rotas admin exigirem token).
- **Linha exata obrigatória + evidência.** Cada finding traz `Evidence:` com o trecho copiado; isso força o agente a reabrir o arquivo e impede números de linha "estimados".
- **Confirmação explícita** com a frase exata `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`; qualquer coisa diferente de "sim" encerra.
- **Honestidade no resultado.** O bloco final usa ✓/✗ e uma seção "Findings addressed" com *fixed / partially fixed / deferred*, em vez de prometer "zero anti-patterns".
- **CRITICAL/HIGH não podem ser adiados.** Se a correção remove uma vulnerabilidade, ela é aplicada mesmo que mude o contrato (a mudança é listada). "Partially fixed"/"deferred" só vale para MEDIUM/LOW ou para itens cuja correção não fecha uma vulnerabilidade (ex.: upgrade de framework).

### Anti-patterns do catálogo (22) e por quê

| Severidade | IDs | Motivação |
|---|---|---|
| CRITICAL | AP-01 credenciais hardcoded · AP-02 SQL injection · AP-03 God class/file · AP-04 endpoint destrutivo/arbitrário sem auth · AP-05 exposição de dados sensíveis | Encontrados nos 3 projetos; são os que causam dano real imediato. |
| HIGH | AP-06 hash de senha inseguro · AP-07 fat controller/rotas · AP-08 sem DI · AP-09 estado global · AP-10 escrita não atômica/callback hell · AP-11 debug hardcoded | Violações MVC/SOLID que impedem testes e manutenção. |
| MEDIUM | AP-12 N+1 · AP-13 duplicação · AP-14 validação ausente · AP-15 erro descentralizado · **AP-16 APIs deprecated** · AP-17 integridade referencial | Performance, padronização e robustez. AP-16 traz tabela "deprecated → moderno" (Python, Flask, SQLAlchemy, Node, Express). |
| LOW | AP-18 print/console.log · AP-19 magic numbers · AP-20 nomes ruins · AP-21 código morto · AP-22 condicionais verbosas | Legibilidade. |

Cada entrada tem **sinais de detecção concretos** (regex/padrões como `execute("..." + var)`, `for row in rows: cursor.execute(...)`, `hashlib.md5(`, `.query.get(`, `` db.run(`...${x}`) ``) e o que *não* é finding, para reduzir falsos positivos.

### Como a skill é agnóstica de tecnologia

- **Detecção por manifesto + imports** (tabelas para Python, Node, Java, Go, PHP, Ruby, C#), não por nomes de arquivo fixos.
- **Catálogo descrito por conceito**, com sinais para mais de uma stack em cada item.
- **Guidelines com layout-alvo por stack** (Flask, Express) e tabela de mapeamento para FastAPI, Django, Spring e NestJS.
- **Estratégia por ponto de partida**: monólito → reestruturação completa; parcialmente em camadas → manter o que já está certo (`routes/` vira a camada View, `models/` continua), adicionar o que falta (`config/`, `controllers/`, `middlewares/`) e mover responsabilidades.
- **Validação por HTTP** com `smoke_test.py` (só stdlib), que funciona para qualquer servidor.

### Desafios encontrados e como resolvi

| Desafio | Solução |
|---|---|
| Garantir que a refatoração não quebra nada | Baseline executado **antes** da Fase 3 com os mesmos casos replayados depois (`validation.md`). |
| **Feedback da 1ª entrega:** no task-manager-api a escalada de privilégio (AP-04, HIGH) ficou "partially fixed" — só o token foi assinado | Playbook ganhou o **T-13b** (token assinado + `require_auth`/`require_admin` + cadastro público sem `role`), o SKILL.md passou a proibir adiar CRITICAL/HIGH e o `validation.md` exige casos negativos de segurança. O `smoke_test.py` ganhou `capture` (reusar o token do login) e `expect` (status esperado). A skill foi executada de novo no projeto 3, e AP-04 agora está *fixed* (13/13 casos de segurança). |
| Endpoints perigosos que "devem continuar respondendo" (`/admin/query`) | Regra T-13: manter a rota, exigir token de config (403 se não configurado) e limitar a um `SELECT` executado com `PRAGMA query_only`. |
| Senhas legadas (MD5) já gravadas no banco | Playbook T-08 com **migração transparente**: valida o MD5 uma vez e re-hasheia com scrypt. |
| `datetime.utcnow()` deprecated, mas colunas SQLite guardam datetime *naive* | Helper `utcnow()` = `datetime.now(timezone.utc).replace(tzinfo=None)`, mantendo comparações e formato. |
| Projeto 3 já "parece organizado" | O catálogo e o SKILL.md deixam explícito que pastas existentes não provam arquitetura correta. A skill encontrou 18 problemas e criou a camada de controllers que faltava. |
| Seeds com senhas fixas no código | Senha dos usuários de exemplo vem de `SEED_USER_PASSWORD` (aleatória se ausente). |
| Windows: `localhost` resolvendo IPv6 primeiro (~2 s por request) | `validation.md` instrui usar `127.0.0.1`. |
| Dois projetos Flask com versões conflitantes | `validation.md` instrui um ambiente virtual por projeto. |

---

## C) Resultados

### Resumo das auditorias

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Deprecated APIs | Relatório |
|---|---|---|---|---|---|---|---|
| code-smells-project | 6 | 4 | 4 | 4 | 18 | nenhuma (declarado explicitamente) | [audit-project-1.md](reports/audit-project-1.md) |
| ecommerce-api-legacy | 4 | 5 | 5 | 4 | 18 | `sqlite3.verbose()`, API de callbacks, Express 4 | [audit-project-2.md](reports/audit-project-2.md) |
| task-manager-api | 2 | 5 | 6 | 5 | 18 | `datetime.utcnow()` ×22, `Query.get()` ×16, `backref` | [audit-project-3.md](reports/audit-project-3.md) |

Todos os itens da Análise Manual acima aparecem nos relatórios (≥ 5 por projeto).

### Antes × depois

**Projeto 1 — code-smells-project**
```
ANTES                         DEPOIS
app.py        (rotas + SQL)   app.py                    # entry point
controllers.py (HTTP+regras)  src/app.py                # create_app() — composition root
models.py     (SQL+regras)    src/config/settings.py
database.py   (conexão global)src/database.py           # conexão por request, schema, seed
                              src/models/{produto,usuario,pedido,admin}_model.py
                              src/controllers/{produto,usuario,pedido,relatorio,sistema}_controller.py
                              src/views/{produto,usuario,pedido,relatorio,sistema}_routes.py
                              src/middlewares/{error_handler,auth}.py
                              src/services/notification_service.py
                              src/utils/{exceptions,validators}.py
```

**Projeto 2 — ecommerce-api-legacy**
```
ANTES                         DEPOIS
src/app.js                    src/app.js                # composition root (buildApp) + listen
src/AppManager.js (God class) src/config/{index,database,schema}.js
src/utils.js (config+crypto)  src/models/{user,course,enrollment,payment,auditLog}Model.js
                              src/controllers/{checkout,report,user}Controller.js
                              src/routes/{checkout,admin,user}Routes.js
                              src/middlewares/{errorHandler,adminAuth}.js
                              src/services/paymentGateway.js
                              src/utils/{errors,password,asyncHandler,logger}.js
```

**Projeto 3 — task-manager-api**
```
ANTES                              DEPOIS
app.py (app global, config fixa)   app.py                 # create_app() + entry point
models/  (to_dict com senha, MD5)  config/settings.py     # novo
routes/  (queries + regras)        models/                # regras de entidade + consultas agregadas
services/ (não usado, senha fixa)  controllers/           # novo: task, user, report, category
utils/helpers.py (não usado)       routes/                # finas + category_routes.py extraído
                                   middlewares/error_handler.py   # novo
                                   services/notification_service.py  # via env, injetado
                                   utils/{exceptions,validators,time_utils}.py
```

### Checklist de validação

| Item | P1 code-smells | P2 ecommerce | P3 task-manager |
|---|---|---|---|
| **Fase 1** — Linguagem detectada | ✅ Python | ✅ JavaScript/Node | ✅ Python |
| Framework detectado | ✅ Flask 3.1.1 | ✅ Express 4.22.1 | ✅ Flask 3.0.0 + SQLAlchemy |
| Domínio descrito | ✅ E-commerce | ✅ LMS com checkout | ✅ Task Manager |
| Nº de arquivos condiz | ✅ 4 | ✅ 3 | ✅ 15 |
| **Fase 2** — Segue o template | ✅ | ✅ | ✅ |
| Arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Ordenado CRITICAL → LOW | ✅ | ✅ | ✅ |
| ≥ 5 findings | ✅ 18 | ✅ 18 | ✅ 18 |
| APIs deprecated | ✅ (nenhuma, declarado) | ✅ | ✅ |
| Pausa para confirmação | ✅ | ✅ | ✅ |
| **Fase 3** — Estrutura MVC | ✅ | ✅ | ✅ |
| Config extraída (sem hardcoded) | ✅ | ✅ | ✅ |
| Models abstraem dados | ✅ | ✅ | ✅ |
| Views/Routes separadas | ✅ | ✅ | ✅ |
| Controllers com o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ `app.py` | ✅ `src/app.js` | ✅ `app.py` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ 22/22 | ✅ 7/7 | ✅ 22/22 (42/42 casos) |

### Logs das aplicações rodando

Saída completa (antes e depois, com o corpo das respostas) em [`reports/logs/`](reports/logs/): `project-{1,2,3}-smoke.txt` e `boot-logs.txt`. Trecho:

```
# Projeto 1 — após refatoração (python app.py)
GET    /produtos                                     200  {"dados":[{"ativo":1,"categoria":"informatica",...
POST   /pedidos                                      201  {"dados":{"pedido_id":1,"total":479.7},...
POST   /login  (' OR '1'='1' --)                     401  {"erro":"Email ou senha inválidos","sucesso":false}
POST   /admin/query (sem token)                      401  {"erro":"Token administrativo inválido",...
--- 34 cases, 0 failures (5xx/network)

# Projeto 2 — após refatoração (ADMIN_TOKEN=... npm start)
2026-10-18T18:18:19.333Z INFO LMS API rodando na porta 3000
POST   /api/checkout                                 200  {"msg":"Sucesso","enrollment_id":2}
GET    /api/admin/financial-report (com token)       200  [{"course":"Clean Architecture","revenue":997,...
DELETE /api/users/1 (com token)                      200  Usuário deletado
INFO Processando pagamento de 497 no cartão ****4444 (gateway simulado)
--- 13 cases, 0 failures (5xx/network)

# Projeto 3 — após refatoração, iteração 2 (python seed.py && python app.py)
GET    /tasks/stats                                  200  {"cancelled":1,"completion_rate":10.0,"done":1,...
POST   /login                                        200  {"message":"Login realizado com sucesso","token":"eyJ1c2VyX2lkIjo0fQ...
POST   /users  (anônimo, role admin)                 403  {"error":"Apenas administradores podem definir role"}
PUT    /users/4 (sem token)                          401  {"error":"Autenticação necessária"}
PUT    /users/4 (Bearer fake-jwt-token-1)            401  {"error":"Token inválido ou expirado"}
PUT    /users/4 (usuário comum, role admin)          403  {"error":"Apenas administradores podem alterar role ou active"}
DELETE /users/1 (usuário comum)                      403  {"error":"Apenas administradores"}
DELETE /users/4 (admin)                              200  {"message":"Usuário deletado com sucesso"}
--- 42 cases, 0 failures (5xx/network/unexpected status)
```

### Comportamento em stacks diferentes

- **Monólito Python (P1):** reestruturação completa em `src/`. O maior trabalho foi a SQL: parametrização total, JOIN único para pedidos e `with conn:` para a transação. A baixa de estoque passou a ser condicional (`estoque >= ?`).
- **Node/Express (P2):** o catálogo pegou riscos próprios de JS (callback hell, erro ignorado que derruba o processo, log de PAN). A guideline Express levou ao wrapper de promises com `transaction()` serializada, `asyncHandler` e o middleware de erro registrado por último. O nível de exigência foi o mesmo das stacks Python.
- **Flask parcialmente organizado (P3):** a estratégia "partially layered" manteve `models/` e `routes/` e adicionou `controllers/`, `config/` e `middlewares/`. A skill encontrou mais itens MEDIUM (deprecations, N+1, duplicação) e menos CRITICAL, o que reflete o estado real do código.
- **Pendências declaradas nos relatórios:** só a migração para Express 5 (P2, MEDIUM) ficou como *deferred*, porque é um upgrade de framework e não fecha nenhuma vulnerabilidade. Todos os CRITICAL/HIGH dos 3 projetos estão *fixed*. A autorização por papel do P3, adiada na 1ª iteração, foi implementada na 2ª.

> **Como as execuções foram feitas:** as fases foram executadas por um agente Claude Code (app desktop) seguindo as instruções do `SKILL.md` e das referências em cada projeto. A CLI `claude` não estava instalada no ambiente, então o comando `claude "/refactor-arch"` não foi usado nesta rodada. A confirmação da Fase 2 foi respondida com "y" (registrado em cada relatório). A validação usou Python 3.14 e Node 20.18 no Windows 11.

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (`claude --version`)
- Python 3.10+ (projetos 1 e 3) e Node.js 18+ (projeto 2)
- Recomendado: um virtualenv por projeto Python (as versões de Flask são diferentes)

### Rodar a skill

A skill fica em `.claude/skills/refactor-arch/` dentro de cada projeto e é descoberta automaticamente pelo Claude Code ao abrir a pasta.

```bash
cd code-smells-project
claude "/refactor-arch"
```

```bash
cd ecommerce-api-legacy
claude "/refactor-arch"
```

```bash
cd task-manager-api
claude "/refactor-arch"
```

A skill imprime a Fase 1 e o relatório da Fase 2, salva em `reports/` e para em `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`. Responda `y` para refatorar.

> Os projetos deste repositório **já estão refatorados**. Para reproduzir do zero, use o estado original do commit `6d1ce62`: `git worktree add ../original 6d1ce62`, copie a pasta `.claude/` para o projeto desejado e rode a skill.

### Validar a refatoração

Projeto 1:
```bash
cd code-smells-project && pip install -r requirements.txt && ADMIN_TOKEN=dev-admin-token python app.py
```

Projeto 2:
```bash
cd ecommerce-api-legacy && npm install && ADMIN_TOKEN=dev-admin-token npm start
```

Projeto 3:
```bash
cd task-manager-api && pip install -r requirements.txt && python seed.py && python app.py
```

Com a aplicação no ar, rode o smoke test com uma lista de casos (formato em `references/validation.md`):

```bash
python .claude/skills/refactor-arch/scripts/smoke_test.py http://127.0.0.1:5000 cases.json
```

O script imprime `METHOD PATH STATUS corpo` por caso e termina com código ≠ 0 se algum endpoint responder 5xx ou não responder.
