# Audit — Projeto 2: ecommerce-api-legacy

> Saída das Fases 1 e 2 da skill `/refactor-arch` executada em `ecommerce-api-legacy/` (estado original, commit `6d1ce62`).

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js — version not pinned; validated with Node 20.18)
Framework:     Express ^4.18.2 (lockfile: 4.22.1)
Dependencies:  sqlite3 ^5.1.6 (lockfile: 5.1.7)
Database:      SQLite em memória (driver sqlite3, API de callbacks, SQL cru)
Domain:        LMS com fluxo de checkout (cursos, matrículas, pagamentos, usuários, auditoria)
Architecture:  Monolítica — classe AppManager concentra conexão, schema, seed, rotas, pagamento e relatórios
Source files:  3 files analyzed (~180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs
Entry point:   src/app.js (npm start → node src/app.js, porta 3000)
Endpoints:     3 endpoints
================================
```

| Method | Path | Declared at |
|---|---|---|
| POST | /api/checkout | src/AppManager.js:28 |
| GET | /api/admin/financial-report | src/AppManager.js:80 |
| DELETE | /api/users/:id | src/AppManager.js:131 |

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express 4.22.1
Files:   3 analyzed | ~180 lines of code
Date:    2026-10-18
```

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 5 | LOW: 4

## Findings

### [CRITICAL] Hardcoded Credentials (AP-01)
File: src/utils.js:1-7
Evidence: `dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_1234567890abcdef",`
Description: Senha de banco "de produção", chave *live* do gateway de pagamento e usuário SMTP estão fixos no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório pode usar a chave de pagamento real; segredos permanecem no histórico do git.
Recommendation: `src/config/index.js` lendo `process.env`, sem fallback literal para segredos; `.env.example` documentando as variáveis (playbook T-01).

### [CRITICAL] God Class (AP-03)
File: src/AppManager.js:4-139
Evidence: `class AppManager { constructor() { this.db = new sqlite3.Database(':memory:'); } initDb() {...} setupRoutes(app) {...} }`
Description: Uma única classe cria a conexão, define o schema, insere seeds, registra as rotas e implementa checkout, pagamento, auditoria, relatório financeiro e remoção de usuários.
Impact: Nenhuma parte pode ser testada ou reutilizada isoladamente; qualquer mudança toca o arquivo inteiro.
Recommendation: Separar em config/, models/, controllers/, routes/ (views), services/ e middlewares/ com composition root em app.js (playbook T-03).

### [CRITICAL] Unprotected Destructive / Admin Endpoints (AP-04)
File: src/AppManager.js:80
File: src/AppManager.js:131-137
Evidence: `app.delete('/api/users/:id', (req, res) => { ... DELETE FROM users WHERE id = ? ...`
Description: O relatório financeiro administrativo e a exclusão de usuários são acessíveis sem autenticação alguma.
Impact: Qualquer cliente anônimo pode apagar usuários e ler faturamento e nomes de alunos.
Recommendation: Middleware de autenticação administrativa com token vindo da configuração (playbook T-13).

### [CRITICAL] Sensitive Data Exposure in Logs (AP-05)
File: src/AppManager.js:45
Evidence: ``console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);``
Description: O número completo do cartão (PAN) e a chave do gateway são gravados no log a cada checkout.
Impact: Violação de PCI-DSS; vazamento de dados de cartão e da chave para qualquer um com acesso aos logs.
Recommendation: Nunca logar PAN/chaves; no máximo os 4 últimos dígitos (playbook T-09).

### [HIGH] Insecure Password Storage (AP-06)
File: src/utils.js:17-23
File: src/AppManager.js:68
Evidence: `hash += Buffer.from(pwd).toString('base64').substring(0, 2);` / `badCrypto(p || "123456")`
Description: A "criptografia" repete os 2 primeiros caracteres do base64 da senha e trunca em 10 caracteres — é reversível e sem salt; senhas ausentes viram "123456". O seed grava a senha em texto puro (AppManager.js:18).
Impact: Senhas triviais de recuperar; colisões massivas (toda senha que começa com o mesmo caractere gera o mesmo "hash").
Recommendation: `crypto.scrypt` com salt aleatório e comparação em tempo constante; rejeitar cadastro sem senha (playbook T-08).

### [HIGH] Callback Pyramid / Non-Atomic Multi-Step Write (AP-10)
File: src/AppManager.js:37-77
Evidence: `this.db.run("INSERT INTO enrollments ...", function(err) { self.db.run("INSERT INTO payments ...", function(err) { self.db.run("INSERT INTO audit_logs ...", (err) => {`
Description: O checkout aninha 5 níveis de callbacks e grava usuário, matrícula, pagamento e auditoria sem transação; o erro do audit_log é ignorado (linha 57). O usuário é criado antes do pagamento ser recusado.
Impact: Falhas no meio deixam matrícula sem pagamento ou usuário órfão; fluxo difícil de ler e manter.
Recommendation: Wrapper de promises + `async/await` e `transaction()` (BEGIN/COMMIT/ROLLBACK) (playbook T-11).

### [HIGH] Business Logic in Route Handlers (AP-07)
File: src/AppManager.js:46-48
File: src/AppManager.js:108-110
Evidence: `let status = cc.startsWith("4") ? "PAID" : "DENIED";`
Description: Decisão de pagamento (regra do gateway simulado) e cálculo de receita estão dentro dos handlers HTTP.
Impact: Regras não testáveis sem subir o servidor; impossível trocar o gateway.
Recommendation: Controller de checkout orquestrando um `paymentGateway` injetado; agregação de receita no controller de relatórios (playbook T-04).

### [HIGH] Mutable Global State (AP-09)
File: src/utils.js:9-15
Evidence: `let globalCache = {};` / `let totalRevenue = 0;`
Description: Cache global mutável em nível de módulo e uma variável `totalRevenue` exportada como primitivo (nunca atualizável por quem importa).
Impact: Estado compartilhado invisível, vazamento de memória sem limite, comportamento difícil de testar.
Recommendation: Estado pertencente a objetos criados na composition root e injetados (playbook T-05).

### [HIGH] Tight Coupling / No Dependency Injection (AP-08)
File: src/AppManager.js:7
File: src/app.js:8-10
Evidence: `this.db = new sqlite3.Database(':memory:');`
Description: A conexão é criada dentro da classe que a usa; app.js não consegue fornecer outra implementação (ex.: banco de teste) nem um gateway de pagamento diferente.
Impact: Testes isolados impossíveis; troca de infraestrutura exige editar a regra de negócio.
Recommendation: Factories que recebem dependências (`createCheckoutController({ db, userModel, paymentGateway })`) (playbook T-05).

### [MEDIUM] N+1 Queries (AP-12)
File: src/AppManager.js:83-128
Evidence: `courses.forEach(c => { this.db.all("SELECT * FROM enrollments WHERE course_id = ?" ... this.db.get("SELECT name, email FROM users WHERE id = ?" ... this.db.get("SELECT amount, status FROM payments ...`
Description: Para cada curso, 1 query de matrículas; para cada matrícula, 1 query de usuário e 1 de pagamento, coordenadas por contadores manuais.
Impact: 1 + C + 2·M queries por requisição; ordem do resultado não determinística.
Recommendation: Um único SELECT com LEFT JOIN courses/enrollments/users/payments agregado em memória (playbook T-06).

### [MEDIUM] Missing Referential Integrity (AP-17)
File: src/AppManager.js:12-15
File: src/AppManager.js:131-136
Evidence: `res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");`
Description: Tabelas sem FOREIGN KEY; deletar um usuário deixa matrículas e pagamentos órfãos (o próprio código admite). Também responde "deletado" para ids inexistentes.
Impact: Dados inconsistentes; relatórios exibem "Unknown" com receita de usuários removidos.
Recommendation: FKs com `ON DELETE CASCADE` + `PRAGMA foreign_keys = ON`, remoção dentro de transação e 404 para id inexistente (playbook T-11).

### [MEDIUM] Decentralized / Swallowing Error Handling (AP-15)
File: src/AppManager.js:57
File: src/AppManager.js:92-93
File: src/AppManager.js:104-106
File: src/AppManager.js:133-135
Evidence: `this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => { let enrPending = enrollments.length;`
Description: Erros de callback são ignorados; em 92-93 um erro de banco faz `enrollments.length` lançar TypeError dentro do callback, derrubando o processo. Não existe middleware de erro do Express.
Impact: Respostas incorretas ("sucesso" mesmo com falha) e crash do servidor.
Recommendation: `asyncHandler` + middleware de erro centralizado + classes de erro de domínio (playbook T-07).

### [MEDIUM] Missing Input Validation (AP-14)
File: src/AppManager.js:29-35
Evidence: `if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");`
Description: Apenas presença é verificada: sem validação de formato de e-mail, tipo do `c_id` ou formato do cartão; `pwd` opcional; `:id` do DELETE não é validado.
Impact: Dados inválidos persistidos; comportamento imprevisível com tipos inesperados.
Recommendation: Validação no controller com as mesmas respostas 400 (playbook T-14).

### [MEDIUM] Deprecated / Legacy APIs (AP-16)
File: src/AppManager.js:1
File: src/AppManager.js:37-77, 83-128
Evidence: `const sqlite3 = require('sqlite3').verbose();`
Description: Modo `verbose()` (stack traces longos, overhead) habilitado incondicionalmente; uso exclusivo da API legada de callbacks do driver. Express 4.x está em modo manutenção (Express 5 é a linha atual).
Impact: Overhead em produção e código em estilo legado que induz à pirâmide de callbacks.
Recommendation: `verbose()` só fora de produção; wrapper de promises com async/await; planejar migração para Express 5 (playbook T-10, T-11).

### [LOW] Poor Naming (AP-20)
File: src/AppManager.js:29-33
File: src/utils.js:12, 17
File: src/app.js:13
Evidence: `let u = req.body.usr; let e = req.body.eml; let p = req.body.pwd; let cid = req.body.c_id; let cc = req.body.card;`
Description: Variáveis de uma letra, funções `badCrypto`/`logAndCache`, classe genérica `AppManager`, mensagem "Frankenstein LMS".
Impact: Legibilidade.
Recommendation: Desestruturar com nomes intencionais mantendo os campos públicos do contrato (playbook T-12).

### [LOW] Dead Code / Unused Imports (AP-21)
File: src/AppManager.js:2
File: src/utils.js:2-5, 10
Evidence: `const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');`
Description: `totalRevenue` importado e nunca usado; `dbUser`, `dbPass`, `smtpUser` nunca lidos; alias `self` misturado com `this`.
Impact: Ruído e confusão sobre o que é usado.
Recommendation: Remover (playbook T-12).

### [LOW] console.log as Logging (AP-18)
File: src/utils.js:13
File: src/app.js:13
Evidence: ``console.log(`[LOG] Salvando no cache: ${key}`);``
Description: Logs sem nível nem estrutura (o log de cartão está no finding CRITICAL AP-05).
Impact: Observabilidade pobre.
Recommendation: Logger com níveis (playbook T-12).

### [LOW] Magic Numbers / Strings (AP-19)
File: src/AppManager.js:46
File: src/utils.js:6, 19
Evidence: `cc.startsWith("4")` / `port: 3000` / `i < 10000`
Description: Prefixo de cartão aprovado, status "PAID"/"DENIED", porta e contagem do laço são literais soltos.
Impact: Regras escondidas e repetidas.
Recommendation: Constantes nomeadas (playbook T-12).

## Deprecated APIs
| Location | Deprecated usage | Modern replacement |
|---|---|---|
| src/AppManager.js:1 | `require('sqlite3').verbose()` sempre ligado | `verbose()` apenas quando `NODE_ENV !== 'production'` |
| src/AppManager.js:37-128 | API de callbacks do sqlite3 (estilo legado) | wrapper de Promises + `async/await` |
| package.json:10 | Express 4.x (manutenção) | Express 5.x (migração planejada, fora do escopo desta refatoração) |

## Architecture Assessment
Current: Monolítica — God class `AppManager` + `utils.js` com config, crypto e cache globais.
Target:  MVC — `src/config` (env + conexão/schema), `src/models` (SQL por entidade), `src/controllers` (checkout, relatórios, usuários), `src/routes` (views/Routers finos), `src/middlewares` (erros + auth admin), `src/services` (gateway de pagamento), `src/app.js` como composition root.

```
================================
Total: 18 findings
================================
```

## Refactoring Plan
```
ecommerce-api-legacy/src/
├── app.js                       # composition root + listen
├── config/  index.js, database.js (promises + transaction), schema.js (DDL + seed)
├── models/  userModel.js, courseModel.js, enrollmentModel.js, paymentModel.js, auditLogModel.js
├── controllers/  checkoutController.js, reportController.js, userController.js
├── routes/  checkoutRoutes.js, adminRoutes.js, userRoutes.js
├── middlewares/  errorHandler.js, adminAuth.js
├── services/  paymentGateway.js
└── utils/  errors.js, password.js, asyncHandler.js, logger.js
```

| Step | Transformation | Findings resolved |
|---|---|---|
| 1 | T-01 Config via env | AP-01 |
| 2 | T-03 Split AppManager into MVC | AP-03 |
| 3 | T-05 Factories + DI, no global state | AP-08, AP-09 |
| 4 | T-11 Promises/async + transaction + FK cascade | AP-10, AP-17, AP-16 |
| 5 | T-04 / T-14 Rules and validation in controllers | AP-07, AP-14 |
| 6 | T-06 JOIN for financial report | AP-12 |
| 7 | T-07 Central error middleware | AP-15 |
| 8 | T-08 / T-09 / T-13 scrypt, no PAN logging, admin guard | AP-04, AP-05, AP-06 |
| 9 | T-12 Naming, constants, logger, dead code | AP-18 … AP-21 |

Intentional contract changes (if approved):
- `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem header `X-Admin-Token` (403 se `ADMIN_TOKEN` não configurado, 401 se inválido).
- `DELETE /api/users/:id` remove matrículas/pagamentos em cascata, responde 404 para id inexistente e a mensagem passa a ser "Usuário deletado".
- Checkout de usuário novo sem `pwd` → 400 (antes usava a senha "123456"); pagamento recusado não cria mais o usuário.
- Relatório financeiro ordenado por id do curso (antes ordem dependia da conclusão dos callbacks).

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]

> Resposta à confirmação: **y**

---

## Phase 3 — Execution log

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
ecommerce-api-legacy/
├── .env.example
├── api.http                       # + header X-Admin-Token
├── package.json
└── src/
    ├── app.js                     # composition root (buildApp) + listen
    ├── config/
    │   ├── index.js
    │   ├── database.js            # promises + transaction()
    │   └── schema.js              # DDL com FKs ON DELETE CASCADE + seed
    ├── models/
    │   ├── userModel.js
    │   ├── courseModel.js
    │   ├── enrollmentModel.js
    │   ├── paymentModel.js
    │   └── auditLogModel.js
    ├── controllers/
    │   ├── checkoutController.js
    │   ├── reportController.js
    │   └── userController.js
    ├── routes/
    │   ├── checkoutRoutes.js
    │   ├── adminRoutes.js
    │   └── userRoutes.js
    ├── middlewares/
    │   ├── errorHandler.js
    │   └── adminAuth.js
    ├── services/paymentGateway.js
    └── utils/
        ├── errors.js
        ├── password.js
        ├── asyncHandler.js
        └── logger.js
(removidos: src/AppManager.js, src/utils.js)

## Findings addressed
AP-01 fixed · AP-03 fixed · AP-04 fixed · AP-05 fixed (cartão mascarado, chave nunca logada)
AP-06 fixed (scrypt + salt) · AP-10 fixed (async/await + transação) · AP-07 fixed · AP-09 fixed · AP-08 fixed
AP-12 fixed (1 query com JOIN) · AP-17 fixed (FK cascade) · AP-15 fixed · AP-14 fixed
AP-16 partially fixed (verbose só fora de produção, API de promises; migração para Express 5 deferida — fora do escopo)
AP-20 fixed · AP-21 fixed · AP-18 fixed · AP-19 fixed

## Intentional contract changes
- Rotas admin exigem X-Admin-Token (403 sem ADMIN_TOKEN configurado; 401 token inválido)
- DELETE /api/users/:id: cascata em matrículas/pagamentos, 404 p/ id inexistente, 400 p/ id inválido, mensagem "Usuário deletado"
- Checkout de usuário novo sem pwd → 400; pagamento recusado não cria usuário
- Relatório financeiro ordenado por curso; erros 500 retornam "Erro interno"

## Validation
  ✓ Application boots without errors (npm start)
  ✓ All endpoints respond (7/7 casos de baseline com o mesmo status; 13/13 casos sem 5xx)
  ✓ No CRITICAL/HIGH detection signal remaining
================================
```
