# Audit — Projeto 3: task-manager-api

> Saída das Fases 1 e 2 da skill `/refactor-arch` executada em `task-manager-api/` (estado original, commit `6d1ce62`).

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (version not pinned; validated with 3.14)
Framework:     Flask 3.0.0
Dependencies:  flask-sqlalchemy 3.1.1 (SQLAlchemy 2.x), flask-cors 4.0.0, marshmallow 3.20.1 (não usado), requests 2.31.0 (não usado), python-dotenv 1.0.0 (não usado)
Database:      SQLite (Flask-SQLAlchemy ORM, sqlite:///tasks.db)
Domain:        Task Manager API (tasks, usuários, categorias, relatórios de produtividade)
Architecture:  Parcialmente em camadas — models/, routes/, services/, utils/ existem, mas as rotas concentram queries, regras e validação; não há controllers, config nem tratamento de erro central; services/ e utils/ praticamente não são usados
Source files:  15 files analyzed (3 __init__.py vazios; ~1.160 lines, incluindo seed.py)
DB tables:     tasks, users, categories
Entry point:   app.py (python seed.py && python app.py → porta 5000)
Endpoints:     22 endpoints
================================
```

| Method | Path | Declared at |
|---|---|---|
| GET | /health | app.py:22 |
| GET | / | app.py:26 |
| GET | /tasks | routes/task_routes.py:11 |
| GET | /tasks/<task_id> | routes/task_routes.py:65 |
| POST | /tasks | routes/task_routes.py:85 |
| PUT | /tasks/<task_id> | routes/task_routes.py:156 |
| DELETE | /tasks/<task_id> | routes/task_routes.py:225 |
| GET | /tasks/search | routes/task_routes.py:240 |
| GET | /tasks/stats | routes/task_routes.py:273 |
| GET | /users | routes/user_routes.py:10 |
| GET | /users/<user_id> | routes/user_routes.py:27 |
| POST | /users | routes/user_routes.py:42 |
| PUT | /users/<user_id> | routes/user_routes.py:92 |
| DELETE | /users/<user_id> | routes/user_routes.py:134 |
| GET | /users/<user_id>/tasks | routes/user_routes.py:153 |
| POST | /login | routes/user_routes.py:185 |
| GET | /reports/summary | routes/report_routes.py:12 |
| GET | /reports/user/<user_id> | routes/report_routes.py:103 |
| GET | /categories | routes/report_routes.py:157 |
| POST | /categories | routes/report_routes.py:167 |
| PUT | /categories/<cat_id> | routes/report_routes.py:190 |
| DELETE | /categories/<cat_id> | routes/report_routes.py:211 |

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1)
Files:   15 analyzed | ~1.160 lines of code
Date:    2026-10-18
```

## Summary
CRITICAL: 2 | HIGH: 5 | MEDIUM: 6 | LOW: 5

## Findings

### [CRITICAL] Hardcoded Credentials (AP-01)
File: app.py:13
File: services/notification_service.py:7-10
Evidence: `app.config['SECRET_KEY'] = 'super-secret-key-123'` / `self.email_password = 'senha123'`
Description: SECRET_KEY do Flask e credenciais SMTP (usuário e senha do Gmail) fixos no código. `python-dotenv` está nas dependências mas nunca é usado.
Impact: Segredos no histórico do git; qualquer pessoa com acesso ao código pode forjar sessões e usar a conta de e-mail.
Recommendation: `config/settings.py` lendo variáveis de ambiente (com `.env`), serviço de notificação configurado por injeção (playbook T-01).

### [CRITICAL] Sensitive Data Exposure — password hash in responses (AP-05)
File: models/user.py:16-25
File: routes/user_routes.py:33, 85, 129, 209
Evidence: `'password': self.password,`
Description: `User.to_dict()` inclui o hash da senha, e é usado nas respostas de GET /users/<id>, POST /users, PUT /users/<id> e POST /login.
Impact: Hashes MD5 (sem salt) vazam para qualquer cliente e são quebráveis por rainbow tables em segundos.
Recommendation: Serializador público sem o campo `password` (playbook T-09).

### [HIGH] Insecure Password Hashing — MD5 (AP-06)
File: models/user.py:27-32
Evidence: `self.password = hashlib.md5(pwd.encode()).hexdigest()`
Description: Senhas com MD5 sem salt; comparação sem tempo constante; senha mínima de 4 caracteres (routes/user_routes.py:64).
Impact: Recuperação trivial das senhas em caso de vazamento.
Recommendation: `werkzeug.security` (scrypt) com migração transparente dos hashes MD5 legados no login (playbook T-08).

### [HIGH] Fat Routes — business logic and queries in the view layer (AP-07)
File: routes/task_routes.py:11-63, 85-154, 156-223, 273-299
File: routes/user_routes.py:42-90, 153-183
File: routes/report_routes.py:12-101, 103-155, 157-223
Evidence: `if t.due_date: if t.due_date < datetime.utcnow(): if t.status != 'done' and t.status != 'cancelled':`
Description: Não existe camada de controller: os Blueprints fazem queries ORM, validação, regras (atraso, estatísticas, produtividade), serialização e commit. `Task.is_overdue()` existe no model mas é reimplementado nas rotas. O CRUD de categorias está dentro de `report_routes.py`.
Impact: Regras duplicadas e divergentes, rotas impossíveis de testar sem HTTP, responsabilidades misturadas.
Recommendation: Criar `controllers/` por domínio, mover queries para métodos dos models, rotas finas; separar `category_routes.py` (playbook T-04, T-03).

### [HIGH] Missing Authentication / Privilege Escalation (AP-04)
File: routes/user_routes.py:52, 71-72
File: routes/user_routes.py:119-122
File: routes/user_routes.py:210
Evidence: `'token': 'fake-jwt-token-' + str(user.id)`
Description: O "token" de login é previsível (`fake-jwt-token-<id>`); qualquer cliente anônimo pode criar um usuário com `role: admin` ou promover/remover usuários. Severidade HIGH (e não CRITICAL) porque não há execução arbitrária de código/SQL.
Impact: Qualquer pessoa vira administrador; tokens podem ser forjados para qualquer usuário.
Recommendation: Token assinado com a SECRET_KEY (itsdangerous) e, em seguida, autorização nas rotas sensíveis (playbook T-13).

### [HIGH] Debug Mode Hardcoded (AP-11)
File: app.py:34
Evidence: `app.run(debug=True, host='0.0.0.0', port=5000)`
Description: Debugger do Werkzeug habilitado e exposto em todas as interfaces; CORS aberto (app.py:15).
Impact: Execução remota de código via console de debug se a porta estiver acessível.
Recommendation: DEBUG/HOST/PORT via ambiente, DEBUG=false por padrão (playbook T-01).

### [HIGH] No App Factory / Tight Coupling (AP-08)
File: app.py:9-31
File: seed.py:2
File: services/notification_service.py:5-10
Evidence: `app = Flask(__name__)` … `with app.app_context(): db.create_all()` no import do módulo
Description: A aplicação é criada e o banco é inicializado como efeito colateral do import; `seed.py` depende desse efeito. O serviço de notificação instancia a própria configuração SMTP e nunca é injetado (nem usado).
Impact: Impossível criar instâncias com configuração de teste; acoplamento entre script de seed e servidor.
Recommendation: `create_app(settings)` como composition root, dependências injetadas nos controllers (playbook T-05).

### [MEDIUM] N+1 Queries (AP-12)
File: routes/task_routes.py:41-57
File: routes/user_routes.py:22
File: routes/report_routes.py:53-68
File: routes/report_routes.py:159-164
File: routes/task_routes.py:275-281, routes/report_routes.py:15-30
Evidence: `user = User.query.get(t.user_id)` e `cat = Category.query.get(t.category_id)` dentro do laço de tasks
Description: Listar tasks faz 2 queries por task; listar usuários carrega `u.tasks` por usuário; o resumo faz 1 query por usuário e 12 `count()` separados; categorias fazem 1 count por categoria; tasks atrasadas são calculadas carregando todas as tasks em memória.
Impact: Número de queries cresce linearmente com os dados.
Recommendation: `joinedload`, `func.count` + `group_by`, filtro de atraso no SQL (playbook T-06).

### [MEDIUM] Duplicated Code (AP-13)
File: routes/task_routes.py:30-39, 71-80, 283-287
File: routes/user_routes.py:171-180
File: routes/report_routes.py:33-43, 132-135
File: routes/task_routes.py:17-28 ≈ models/task.py:23-36
File: routes/task_routes.py:92-144 ≈ routes/task_routes.py:166-213
File: routes/user_routes.py:61, 106 ≈ utils/helpers.py:19-23
Evidence: bloco de 9 linhas de "overdue" repetido 6×
Description: Regra de atraso copiada 6 vezes (apesar de `Task.is_overdue()`); serialização de task duplicada; validação de create/update duplicada; regex de e-mail em 3 lugares; `utils/helpers.process_task_data` e constantes `VALID_STATUSES`/`VALID_ROLES` existem mas não são usados.
Impact: Correções precisam ser replicadas; alto risco de divergência.
Recommendation: Uma fonte de verdade por regra (model/validators) reutilizada pelos controllers (playbook T-04, T-14).

### [MEDIUM] Missing / Inconsistent Input Validation (AP-14)
File: routes/task_routes.py:113, 182
File: routes/task_routes.py:260-264
File: routes/report_routes.py:196-202
File: routes/user_routes.py:102-103, 124-125
Evidence: `if priority < 1 or priority > 5:` (priority string → TypeError → 500)
Description: Prioridade não-numérica gera 500; `int(priority)`/`int(user_id)` na busca geram 500 com valores inválidos; PUT /categories não verifica corpo vazio (`'name' in None` → 500) nem cor; PUT /users aceita nome vazio e `active` não-booleano.
Impact: Erros 500 em entradas comuns, dados inválidos persistidos.
Recommendation: Validadores reutilizáveis nos controllers (playbook T-14).

### [MEDIUM] Bare except / No Central Error Handling (AP-15)
File: routes/task_routes.py:62, 137, 204, 236
File: routes/user_routes.py:130, 149
File: routes/report_routes.py:186, 207, 221
File: utils/helpers.py:46, 49, 88
Evidence: `except:` → `return jsonify({'error': 'Erro interno'}), 500`
Description: `except:` sem tipo engole qualquer erro (inclusive bugs e KeyboardInterrupt); não há `errorhandler` — erros fora dos try viram páginas HTML 500 do Flask.
Impact: Bugs silenciosos, respostas inconsistentes (JSON vs HTML).
Recommendation: Exceções de domínio + `register_error_handlers` (playbook T-07).

### [MEDIUM] Deprecated APIs (AP-16)
File: models/task.py:15, 16, 52 · models/category.py:11 · models/user.py:14
File: routes/task_routes.py:31, 72, 215, 285 · routes/user_routes.py:172 · routes/report_routes.py:35, 42, 45, 71, 133
File: services/notification_service.py:35 · utils/helpers.py:38 · seed.py:66-74
File: routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227 · routes/user_routes.py:29, 94, 136, 155 · routes/report_routes.py:105, 192, 213
Evidence: `datetime.utcnow()` / `Task.query.get(task_id)`
Description: `datetime.utcnow()` está deprecated desde Python 3.12 (DeprecationWarning observado no seed); `Query.get()` é API legada no SQLAlchemy 2.x (LegacyAPIWarning).
Impact: Quebra em versões futuras; warnings em runtime.
Recommendation: `datetime.now(timezone.utc)` (helper `utcnow()` naive-UTC para manter o formato salvo) e `db.session.get(Model, id)` (playbook T-10).

### [MEDIUM] Missing Referential Integrity (AP-17)
File: routes/user_routes.py:140-142
File: routes/report_routes.py:211-223
File: models/task.py:20-21
Evidence: `for t in tasks: db.session.delete(t)`
Description: A remoção de tasks do usuário é feita manualmente na rota; ao deletar uma categoria, as tasks ficam apontando para um `category_id` inexistente; os relacionamentos não declaram cascade.
Impact: Dados órfãos e lógica de integridade espalhada pelas rotas.
Recommendation: `cascade="all, delete-orphan"` em User.tasks e desassociação explícita de Category.tasks (playbook T-11).

### [LOW] Unused Imports / Dead Code (AP-21)
File: app.py:7
File: routes/task_routes.py:7
File: routes/user_routes.py:6
File: routes/report_routes.py:7-8
File: models/task.py:3
File: utils/helpers.py:3-7, 9-116
File: services/notification_service.py:1-48
Evidence: `import os, sys, json, datetime` (só datetime é usado)
Description: Diversos imports sem uso; `utils/helpers.py` e `NotificationService` não são chamados por nenhuma rota; marshmallow/requests nunca importados.
Impact: Ruído e dependências desnecessárias.
Recommendation: Remover ou integrar ao fluxo (playbook T-12).

### [LOW] print() as Logging (AP-18)
File: routes/task_routes.py:149, 153, 219, 234
File: routes/user_routes.py:83, 89, 147
File: services/notification_service.py:21, 24
Evidence: `print(f"Task criada: {task.id} - {task.title}")`
Description: Logs via print, sem nível.
Impact: Observabilidade pobre.
Recommendation: `logging` (playbook T-12).

### [LOW] Magic Numbers / Strings (AP-19)
File: routes/task_routes.py:110, 113, 177, 182
File: routes/user_routes.py:64, 71, 115, 120
File: routes/report_routes.py:129
File: models/task.py:39, 46
Evidence: `if status not in ['pending', 'in_progress', 'done', 'cancelled']:`
Description: Listas de status/roles, faixa de prioridade 1..5, limiar `priority <= 2` e tamanho mínimo de senha repetidos como literais (as constantes de utils/helpers.py:110-116 não são usadas).
Impact: Regras espalhadas e fáceis de divergir.
Recommendation: Constantes nos models (playbook T-12).

### [LOW] Verbose / Nested Conditionals (AP-22)
File: models/task.py:38-60
File: models/user.py:34-38
File: routes/task_routes.py:141, 210
Evidence: `if self.role == 'admin': return True else: return False`
Description: Retornos booleanos verbosos, 3 níveis de `if` aninhados, `type(tags) == list`.
Impact: Legibilidade.
Recommendation: Expressões booleanas diretas e `isinstance` (playbook T-12).

### [LOW] Poor Naming (AP-20)
File: routes/report_routes.py:24-28
File: models/category.py:14
File: routes/task_routes.py:16, routes/user_routes.py:14
Evidence: `p1 = Task.query.filter_by(priority=1).count()`
Description: Nomes como `p1..p5`, `d`, `t`, `u`, `cat`.
Impact: Legibilidade.
Recommendation: Nomes intencionais (playbook T-12).

## Deprecated APIs
| Location | Deprecated usage | Modern replacement |
|---|---|---|
| models/*.py, routes/*.py, services, utils, seed.py (22 ocorrências, ver AP-16) | `datetime.utcnow()` | `datetime.now(timezone.utc)` via helper `utcnow()` |
| routes/*.py (16 ocorrências, ver AP-16) | `Model.query.get(id)` | `db.session.get(Model, id)` |
| models/task.py:20-21 | `db.relationship(..., backref=...)` (estilo legado) | `back_populates` explícito |

## Architecture Assessment
Current: Parcialmente em camadas — há pastas de models/routes/services/utils, mas a camada de rotas faz o papel de controller e de acesso a dados; config hardcoded; sem error handler; categorias misturadas aos relatórios.
Target:  MVC mantendo os nomes existentes — `config/` (novo), `models/` (dados + regras de entidade + queries), `controllers/` (novo: fluxo e regras), `routes/` (views finas, + `category_routes.py`), `middlewares/` (novo), `services/` (notificação injetada), `utils/` (validators, exceptions, time); `create_app()` em app.py.

```
================================
Total: 18 findings
================================
```

## Refactoring Plan
```
task-manager-api/
├── app.py                      # create_app() + entry point
├── config/settings.py          # novo
├── database.py
├── seed.py                     # usa create_app()
├── models/  task.py, user.py, category.py      # + queries, constantes, hashing seguro
├── controllers/  task_controller.py, user_controller.py, report_controller.py, category_controller.py   # novo
├── routes/  task_routes.py, user_routes.py, report_routes.py, category_routes.py                       # finas
├── middlewares/error_handler.py  # novo
├── services/notification_service.py   # config via env, injetado
└── utils/  exceptions.py, validators.py, time_utils.py   # helpers.py removido (código morto)
```

| Step | Transformation | Findings resolved |
|---|---|---|
| 1 | T-01 Config via env | AP-01, AP-11 |
| 2 | T-05 App factory + DI | AP-08 |
| 3 | T-04 Controllers + regras nos models | AP-07, AP-13 |
| 4 | T-06 Eager loading / group_by | AP-12 |
| 5 | T-14 Validators | AP-14 |
| 6 | T-07 Error handler central | AP-15 |
| 7 | T-10 utcnow / session.get | AP-16 |
| 8 | T-11 Cascades | AP-17 |
| 9 | T-08 / T-09 / T-13 Hash seguro, to_dict sem senha, token assinado | AP-05, AP-06, AP-04 (parcial) |
| 10 | T-12 Limpeza | AP-18 … AP-22 |

Intentional contract changes (if approved):
- Respostas de usuário não contêm mais `password`.
- `token` do login passa a ser assinado (itsdangerous) em vez de `fake-jwt-token-<id>`.
- Entradas com tipo inválido retornam 400 em vez de 500; erros não tratados retornam JSON `{"error": ...}`.
- Deletar categoria desassocia as tasks (`category_id = null`).

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]

> Resposta à confirmação: **y**

---

## Phase 3 — Execution log

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
task-manager-api/
├── app.py                       # create_app() — composition root + entry point
├── database.py                  # db + PersistenceMixin (save/delete)
├── seed.py                      # usa a app factory, senhas via SEED_USER_PASSWORD
├── .env.example
├── config/settings.py           # novo
├── models/
│   ├── task.py                  # constantes, is_overdue, consultas agregadas
│   ├── user.py                  # scrypt + migração MD5, to_dict sem senha, cascade
│   └── category.py
├── controllers/                 # novo
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── report_controller.py
│   └── category_controller.py
├── routes/                      # views finas
│   ├── task_routes.py
│   ├── user_routes.py
│   ├── report_routes.py
│   └── category_routes.py       # extraído de report_routes.py
├── middlewares/error_handler.py # novo
├── services/notification_service.py  # config via env, injetado no TaskController
└── utils/
    ├── exceptions.py
    ├── validators.py
    └── time_utils.py
(removido: utils/helpers.py — código morto)

## Findings addressed
AP-01 fixed · AP-05 fixed · AP-06 fixed (scrypt + migração transparente do MD5) · AP-07 fixed · AP-11 fixed · AP-08 fixed
AP-04 partially fixed — token agora assinado (itsdangerous); autorização por papel nas rotas deferida
      (exige decisão de produto e quebraria todos os clientes atuais)
AP-12 fixed (joinedload + group_by) · AP-13 fixed · AP-14 fixed · AP-15 fixed · AP-16 fixed · AP-17 fixed
AP-18 fixed · AP-19 fixed · AP-20 fixed · AP-21 fixed (helpers.py, imports, marshmallow/requests removidos) · AP-22 fixed

## Intentional contract changes
- Respostas de usuário não contêm mais `password`
- `token` do login é assinado (itsdangerous) em vez de `fake-jwt-token-<id>`
- Tipos inválidos → 400 (antes 500); erros não tratados e 404 → JSON {"error": ...}
- Deletar categoria desassocia as tasks (category_id = null); cor de categoria validada (#RRGGBB)

## Validation
  ✓ Application boots without errors (python seed.py && python app.py, com DeprecationWarning como erro)
  ✓ All endpoints respond (29/29 casos de baseline com o mesmo status; 39/39 casos sem 5xx)
  ✓ No CRITICAL/HIGH detection signal remaining (hit de "salt=" no URLSafeTimedSerializer é falso positivo)
================================
```
