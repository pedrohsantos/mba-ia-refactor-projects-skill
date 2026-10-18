# Audit — Projeto 1: code-smells-project

> Saída das Fases 1 e 2 da skill `/refactor-arch` executada em `code-smells-project/` (estado original, commit `6d1ce62`).

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (version not pinned; validated with 3.14)
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1
Database:      SQLite (driver sqlite3 nativo, SQL cru, arquivo loja.db)
Domain:        E-commerce API (produtos, usuários, pedidos, relatório de vendas)
Architecture:  Pseudo-camadas / monolítica — models.py e controllers.py existem, mas misturam SQL, regras, validação, formatação e efeitos colaterais para 4 domínios; app.py tem rotas + SQL administrativo
Source files:  4 files analyzed (~780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Entry point:   app.py (python app.py → porta 5000)
Endpoints:     19 endpoints
================================
```

| Method | Path | Declared at |
|---|---|---|
| GET | /produtos | app.py:11 |
| GET | /produtos/busca | app.py:12 |
| GET | /produtos/<id> | app.py:13 |
| POST | /produtos | app.py:14 |
| PUT | /produtos/<id> | app.py:15 |
| DELETE | /produtos/<id> | app.py:16 |
| GET | /usuarios | app.py:18 |
| GET | /usuarios/<id> | app.py:19 |
| POST | /usuarios | app.py:20 |
| POST | /login | app.py:21 |
| POST | /pedidos | app.py:23 |
| GET | /pedidos | app.py:24 |
| GET | /pedidos/usuario/<usuario_id> | app.py:25 |
| PUT | /pedidos/<pedido_id>/status | app.py:26 |
| GET | /relatorios/vendas | app.py:28 |
| GET | /health | app.py:30 |
| GET | / | app.py:32 |
| POST | /admin/reset-db | app.py:47 |
| POST | /admin/query | app.py:59 |

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-10-18
```

## Summary
CRITICAL: 6 | HIGH: 4 | MEDIUM: 4 | LOW: 4

## Findings

### [CRITICAL] Hardcoded Credentials (AP-01)
File: app.py:7
File: controllers.py:289
Evidence: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"`
Description: A SECRET_KEY do Flask está fixa no código e é repetida literalmente na resposta do `/health`.
Impact: Qualquer pessoa com acesso ao repositório (ou ao endpoint público de health) pode forjar sessões/cookies assinados; o segredo fica para sempre no histórico do git.
Recommendation: Ler a chave de variável de ambiente via módulo `config/settings.py`, sem fallback literal (playbook T-01).

### [CRITICAL] SQL Injection (AP-02)
File: models.py:28
File: models.py:47-50
File: models.py:57-61
File: models.py:68
File: models.py:92
File: models.py:109-111
File: models.py:126-129
File: models.py:140, 148-151, 155-166
File: models.py:174, 188, 192, 220, 224
File: models.py:279-281
File: models.py:289-299
Evidence: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`
Description: Praticamente todas as queries são montadas por concatenação de strings com dados da requisição (nome, descrição, email, senha, termo de busca, status). O login (models.py:109-111) é vulnerável a `' OR '1'='1' --`.
Impact: Bypass de autenticação, leitura/alteração/remoção arbitrária de dados.
Recommendation: Placeholders `?` em todas as queries; filtros dinâmicos com cláusulas whitelisted + parâmetros (playbook T-02).

### [CRITICAL] God File / God Module (AP-03)
File: models.py:1-314
File: controllers.py:1-292
File: app.py:47-78
Evidence: `def criar_pedido(usuario_id, itens):` / `def relatorio_vendas():` / `def login_usuario(email, senha):` no mesmo módulo
Description: `models.py` concentra persistência, regras de negócio (desconto, estoque), validação e formatação de 4 domínios diferentes; `controllers.py` mistura parsing HTTP, validação, regras e notificações para todos os domínios; `app.py` além de registrar rotas executa SQL diretamente.
Impact: Impossível testar em isolamento; qualquer mudança afeta todos os domínios; sem fronteiras de camada.
Recommendation: Separar por domínio em models/, controllers/, views/ com composition root (playbook T-03).

### [CRITICAL] Unprotected Destructive / Arbitrary SQL Endpoints (AP-04)
File: app.py:47-57
File: app.py:59-78
Evidence: `cursor.execute(query)` com `query = dados.get("sql", "")`
Description: `/admin/query` executa qualquer SQL enviado no corpo e `/admin/reset-db` apaga todas as tabelas — ambos sem nenhuma autenticação.
Impact: Qualquer cliente anônimo pode ler a tabela de usuários (com senhas), alterar preços ou destruir o banco.
Recommendation: Proteger com token administrativo vindo da configuração e restringir `/admin/query` a um único SELECT somente-leitura (playbook T-13).

### [CRITICAL] Sensitive Data Exposure (AP-05)
File: models.py:79-86
File: models.py:95-102
File: controllers.py:276-290
Evidence: `"senha": row["senha"],` / `"secret_key": "minha-chave-super-secreta-123"`
Description: `GET /usuarios` e `GET /usuarios/<id>` devolvem a senha de cada usuário; `GET /health` expõe secret_key, caminho do banco, flag de debug e "ambiente".
Impact: Vazamento de credenciais de todos os usuários e de configuração interna para qualquer cliente.
Recommendation: Serializadores sem campos sensíveis; health retornando apenas status e contagens (playbook T-09).

### [CRITICAL] Plaintext Password Storage (AP-06)
File: database.py:27-35
File: database.py:75-83
File: models.py:109-111
File: models.py:126-129
Evidence: `("Admin", "admin@loja.com", "admin123", "admin"),`
Description: Senhas são gravadas e comparadas em texto puro (no SQL do login). As senhas seed também estão no código.
Impact: Um vazamento do banco (ou do endpoint `/admin/query`) expõe todas as senhas reutilizáveis dos usuários.
Recommendation: `werkzeug.security.generate_password_hash/check_password_hash`; login busca por email e valida o hash em código (playbook T-08).

### [HIGH] Debug Mode / Insecure Runtime Config Hardcoded (AP-11)
File: app.py:8-9
File: app.py:88
Evidence: `app.run(host="0.0.0.0", port=5000, debug=True)`
Description: Debug ligado e bind em todas as interfaces fixos no código; CORS liberado para qualquer origem.
Impact: O debugger do Werkzeug permite execução remota de código se exposto; stack traces vazam para clientes.
Recommendation: DEBUG/HOST/PORT vindos do ambiente, com DEBUG=false por padrão (playbook T-01).

### [HIGH] Mutable Global State / No Dependency Injection (AP-09, AP-08)
File: database.py:4-11
File: models.py:5, 25, 44, 55, 66, 73, 90, 106, 123, 134, 172, 204, 236, 276, 286
Evidence: `global db_connection` … `sqlite3.connect(db_path, check_same_thread=False)`
Description: Uma única conexão SQLite global, compartilhada entre threads, criada sob demanda e acessada por `get_db()` em todas as funções. Não há app factory: tudo é instanciado no import.
Impact: Condições de corrida entre requisições, transações vazando de uma requisição para outra, impossível substituir o banco em testes.
Recommendation: Conexão por requisição via `flask.g` + `teardown_appcontext`; models recebem a fábrica de conexão por injeção; `create_app()` como composition root (playbook T-05).

### [HIGH] Business Logic in the Wrong Layer (AP-07)
File: models.py:256-262
File: controllers.py:43-54
File: controllers.py:208-210
File: controllers.py:247-250
Evidence: `if faturamento > 10000: desconto = faturamento * 0.1`
Description: A regra de desconto do relatório vive na camada de dados; regras de validação de produto e efeitos colaterais de notificação (email/SMS/push, "devolver estoque") estão inline nos handlers HTTP. O cancelamento promete devolver estoque mas apenas imprime uma mensagem.
Impact: Regras não reutilizáveis nem testáveis; bug funcional (estoque nunca é devolvido no cancelamento).
Recommendation: Regras de negócio nos controllers por domínio, persistência pura nos models, notificações via serviço injetado (playbook T-04).

### [HIGH] Non-Atomic Multi-Step Write (AP-10)
File: models.py:133-169
Evidence: `cursor.execute("INSERT INTO pedidos ...")` … `db.commit()` só no final, sem rollback
Description: Criar pedido faz INSERT do pedido, INSERT dos itens e UPDATE de estoque sem transação explícita nem rollback; o preço é relido do banco no segundo laço (models.py:155) e o estoque não é revalidado no UPDATE.
Impact: Uma falha no meio deixa transação pendente na conexão global, que será commitada pela próxima requisição (pedido sem itens / estoque inconsistente).
Recommendation: Bloco `with conn:` (BEGIN/COMMIT/ROLLBACK), reutilizar os produtos carregados na validação, `executemany` para itens e baixa de estoque (playbook T-11).

### [MEDIUM] N+1 Queries (AP-12)
File: models.py:171-201
File: models.py:203-233
File: models.py:239-254
Evidence: `cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))` dentro de dois laços
Description: Listar pedidos executa 1 query por pedido + 1 query por item; o relatório faz 5 consultas separadas que caberiam em uma agregação.
Impact: Crescimento linear de queries com o volume de pedidos/itens.
Recommendation: Um único SELECT com JOIN pedidos/itens/produtos agrupado em memória; relatório com `SUM/COUNT CASE` (playbook T-06).

### [MEDIUM] Duplicated Code (AP-13)
File: models.py:12-21, 31-40, 304-313
File: models.py:79-86, 95-102
File: models.py:171-201 ≡ models.py:203-233
File: controllers.py:28-50 ≈ controllers.py:72-90
Evidence: bloco `"id": row["id"], "nome": row["nome"], ...` repetido 3×
Description: Mapeamento linha→dict copiado em várias funções; `get_pedidos_usuario` e `get_todos_pedidos` são idênticas exceto pelo WHERE; validação de produto duplicada em criar/atualizar.
Impact: Correções precisam ser feitas em vários lugares; divergências já existem (update não valida categoria nem tamanho do nome).
Recommendation: Um serializer por entidade e um validador reutilizado (playbook T-04, T-14).

### [MEDIUM] Missing / Inconsistent Input Validation (AP-14)
File: controllers.py:43-46
File: controllers.py:81-90
File: controllers.py:169-170, 239-240
File: controllers.py:195-201
Evidence: `if preco < 0:` (preco pode ser string → TypeError → 500)
Description: Tipos não são verificados (preço/estoque string geram 500); update não valida categoria/nome; `request.get_json()` pode ser `None` em login e status (500); quantidade dos itens do pedido não é validada (quantidade negativa *aumenta* o estoque) e o usuário do pedido não é verificado.
Impact: Erros 500 para entradas inválidas e corrupção de estoque.
Recommendation: Camada de validação nos controllers com mensagens e status 400 existentes (playbook T-14).

### [MEDIUM] Decentralized Error Handling Leaking Internals (AP-15)
File: controllers.py:10, 21, 60, 95, 108, 125, 133, 143, 164, 185, 218, 226, 234, 254, 261, 291
File: app.py:77-78
File: models.py:143, 145
Evidence: `except Exception as e: return jsonify({"erro": str(e)}), 500`
Description: 17 blocos try/except genéricos devolvem a mensagem crua da exceção ao cliente; models sinalizam erro de negócio retornando dicts `{"erro": ...}`.
Impact: Vazamento de detalhes internos (SQL, paths), código repetitivo, erros de negócio misturados com dados.
Recommendation: Exceções de domínio + `errorhandler` centralizado em middlewares/error_handler.py (playbook T-07).

### [LOW] print() Used as Logging (AP-18)
File: app.py:56, 83-86
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Evidence: `print("Login bem-sucedido: " + email)`
Description: Toda observabilidade é feita com print, incluindo emails de usuários em tentativas de login.
Impact: Sem níveis de log, sem destino configurável, PII em stdout.
Recommendation: `logging.getLogger(__name__)` com níveis (playbook T-12).

### [LOW] Magic Numbers / Strings (AP-19)
File: models.py:257-262
File: controllers.py:52
File: controllers.py:242
File: controllers.py:285-286
Evidence: `elif faturamento > 5000: desconto = faturamento * 0.05`
Description: Faixas de desconto, lista de categorias válidas, lista de status, versão e "ambiente" são literais soltos.
Impact: Regras de negócio escondidas e repetidas; difícil alterar com segurança.
Recommendation: Constantes nomeadas nos models/controllers do domínio (playbook T-12).

### [LOW] Poor Naming (AP-20)
File: models.py:24, 54, 65, 89 (parâmetro `id`)
File: controllers.py:56, 160 (`id = models.criar_...`)
File: models.py:187-191, 219-223 (`cursor2`, `cursor3`, `prod`)
Evidence: `def get_produto_por_id(id):`
Description: `id` sobrescreve o builtin; cursores numerados e abreviações dificultam a leitura.
Impact: Legibilidade.
Recommendation: Nomes intencionais (`produto_id`, `itens_cursor`) (playbook T-12).

### [LOW] Unused Imports (AP-21)
File: models.py:2
File: database.py:2
Evidence: `import sqlite3` (models.py) / `import os` (database.py) nunca usados
Description: Imports sem uso.
Impact: Ruído e falsa sensação de dependência.
Recommendation: Remover (playbook T-12).

## Deprecated APIs
None found — checked against catalog AP-16 (Flask 3.1 APIs usadas — `add_url_rule`, `jsonify`, `request.get_json` — são atuais; sem `datetime.utcnow`, `before_first_request` ou `flask.escape`).

## Architecture Assessment
Current: Pseudo-camadas — nomes "models"/"controllers" existem, mas cada arquivo acumula todas as responsabilidades de todos os domínios; estado global de conexão e nenhuma composition root.
Target:  MVC — `src/config`, `src/models` (persistência por domínio), `src/controllers` (regras e fluxo), `src/views` (Blueprints finos), `src/middlewares` (erros + auth admin), `create_app()` como composition root; `app.py` na raiz continua sendo o ponto de entrada.

```
================================
Total: 18 findings
================================
```

## Refactoring Plan
```
code-smells-project/
├── app.py                          # entry point (python app.py)
├── .env.example
├── requirements.txt                # + python-dotenv
└── src/
    ├── app.py                      # create_app() — composition root
    ├── config/settings.py
    ├── database.py                 # conexão por request, schema, seed com hash
    ├── models/  produto_model.py, usuario_model.py, pedido_model.py, admin_model.py
    ├── controllers/  produto_controller.py, usuario_controller.py, pedido_controller.py, relatorio_controller.py, sistema_controller.py
    ├── views/  produto_routes.py, usuario_routes.py, pedido_routes.py, relatorio_routes.py, sistema_routes.py (/, /health, /admin/*)
    ├── middlewares/  error_handler.py, auth.py
    ├── services/notification_service.py
    └── utils/  exceptions.py, validators.py
```

| Step | Transformation | Findings resolved |
|---|---|---|
| 1 | T-01 Config & secrets to env | AP-01, AP-11 |
| 2 | T-02 Parameterized queries | AP-02 |
| 3 | T-03 Split god files per domain (MVC) | AP-03 |
| 4 | T-05 App factory + per-request connection | AP-08, AP-09 |
| 5 | T-04 / T-14 Business rules & validation in controllers | AP-07, AP-13, AP-14 |
| 6 | T-06 / T-11 JOIN instead of N+1, transactional order creation | AP-10, AP-12 |
| 7 | T-07 Central error handler | AP-15 |
| 8 | T-08 / T-09 / T-13 Hashing, safe serialization, admin guard | AP-04, AP-05, AP-06 |
| 9 | T-12 Logging, constants, naming, dead code | AP-18 … AP-21 |

Intentional contract changes (if approved):
- `GET /usuarios`, `GET /usuarios/<id>` deixam de retornar o campo `senha`.
- `GET /health` deixa de retornar `secret_key`, `db_path`, `debug`, `ambiente`.
- `/admin/*` exigem header `X-Admin-Token` (= `ADMIN_TOKEN`); sem a variável configurada respondem 403. `/admin/query` aceita apenas um SELECT.
- Erros 500 retornam mensagem genérica; entradas com tipo inválido passam a retornar 400 em vez de 500.
- `PUT /pedidos/<id>/status` para status `cancelado` devolve os itens ao estoque (antes só imprimia a intenção).

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]

> Resposta à confirmação: **y**

---

## Phase 3 — Execution log

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
code-smells-project/
├── app.py                         # entry point (python app.py)
├── .env.example
├── requirements.txt               # + python-dotenv
└── src/
    ├── app.py                     # create_app() — composition root
    ├── database.py                # conexão por app context (flask.g), schema, seed com hash
    ├── config/settings.py
    ├── models/
    │   ├── produto_model.py
    │   ├── usuario_model.py
    │   ├── pedido_model.py
    │   └── admin_model.py
    ├── controllers/
    │   ├── produto_controller.py
    │   ├── usuario_controller.py
    │   ├── pedido_controller.py
    │   ├── relatorio_controller.py
    │   └── sistema_controller.py
    ├── views/
    │   ├── produto_routes.py
    │   ├── usuario_routes.py
    │   ├── pedido_routes.py
    │   ├── relatorio_routes.py
    │   └── sistema_routes.py
    ├── middlewares/
    │   ├── error_handler.py
    │   └── auth.py
    ├── services/notification_service.py
    └── utils/
        ├── exceptions.py
        └── validators.py
(removidos: models.py, controllers.py, database.py)

## Findings addressed
AP-01 fixed · AP-02 fixed · AP-03 fixed · AP-04 fixed (token + SELECT somente-leitura em query_only)
AP-05 fixed · AP-06 fixed (werkzeug scrypt) · AP-11 fixed · AP-08/AP-09 fixed · AP-07 fixed
AP-10 fixed (transação + baixa condicional de estoque) · AP-12 fixed (JOIN único / agregação única)
AP-13 fixed · AP-14 fixed · AP-15 fixed · AP-18 fixed (logging) · AP-19 fixed · AP-20 fixed · AP-21 fixed

## Intentional contract changes
- /usuarios e /usuarios/<id> não retornam mais `senha`
- /health não retorna mais secret_key, db_path, debug, ambiente
- /admin/* exigem X-Admin-Token (403 se ADMIN_TOKEN não configurado; 401 se token inválido); /admin/query só aceita um SELECT
- Respostas de erro ganham `"sucesso": false`; erros 500 não expõem mais a mensagem da exceção
- Entradas com tipo inválido (preço string, quantidade ≤ 0) → 400 em vez de 500/corrupção de estoque
- PUT /pedidos/<id>/status: 404 para pedido inexistente; cancelamento devolve estoque
- Usuários seed recebem senha de SEED_USER_PASSWORD (hash) em vez de senhas fixas no código

## Validation
  ✓ Application boots without errors (python app.py — sem traceback no log)
  ✓ All endpoints respond (22/22 casos de baseline com o mesmo status; 34/34 casos sem 5xx)
  ✓ No CRITICAL/HIGH detection signal remaining (2 hits de f-string SQL são falsos positivos:
    placeholders gerados e nomes de tabela constantes)
================================
```
