# Anti-Patterns Catalog (Phase 2)

Each entry has: **ID**, **severity**, **what it is**, **detection signals** (concrete, grep-able when possible)
and the **playbook transformation** that fixes it (`T-xx` in `refactoring-playbook.md`).

## Severity scale

| Severity | Meaning |
|---|---|
| **CRITICAL** | Severe architecture or security flaw: breaks correct operation, exposes sensitive data (hardcoded credentials, SQL injection, arbitrary code/SQL execution) or completely violates separation of concerns (God class with DB + business + routing). |
| **HIGH** | Strong MVC/SOLID violation that makes maintenance and testing very hard: heavy business logic in controllers/routes, tight coupling without DI, mutable global state, non-atomic multi-step writes, weak crypto. |
| **MEDIUM** | Standardization, duplication or moderate performance problems: N+1 queries, missing validation, decentralized error handling, deprecated APIs, logging via print. |
| **LOW** | Readability: bad names, magic numbers/strings, dead code and unused imports, verbose conditionals. |

## Summary

| ID | Anti-pattern | Severity | Fix |
|---|---|---|---|
| AP-01 | Hardcoded credentials / secrets | CRITICAL | T-01 |
| AP-02 | SQL injection (query built by string concatenation/interpolation) | CRITICAL | T-02 |
| AP-03 | God Class / God File (routing + persistence + business in one unit) | CRITICAL | T-03 |
| AP-04 | Unprotected destructive or arbitrary-execution endpoint | CRITICAL | T-13 |
| AP-05 | Sensitive data exposure (passwords, secrets, card numbers in responses/logs) | CRITICAL | T-09 |
| AP-06 | Insecure password storage (plaintext, MD5/SHA1, base64, homemade "crypto") | HIGH (CRITICAL if plaintext) | T-08 |
| AP-07 | Fat Controller / business logic in routes or views | HIGH | T-04 |
| AP-08 | Tight coupling / no dependency injection | HIGH | T-05 |
| AP-09 | Mutable global state | HIGH | T-05 |
| AP-10 | Non-atomic multi-step writes / callback pyramid | HIGH | T-11 |
| AP-11 | Debug mode / insecure runtime configuration in code | HIGH | T-01 |
| AP-12 | N+1 queries | MEDIUM | T-06 |
| AP-13 | Duplicated code (serialization, validation, rules) | MEDIUM | T-04, T-14 |
| AP-14 | Missing or inconsistent input validation | MEDIUM | T-14 |
| AP-15 | Decentralized / swallowing error handling | MEDIUM | T-07 |
| AP-16 | Deprecated / legacy APIs | MEDIUM | T-10 |
| AP-17 | Missing referential integrity (orphans on delete) | MEDIUM | T-11 |
| AP-18 | `print`/`console.log` used as logging | LOW (MEDIUM if it logs sensitive data → then it is AP-05) | T-12 |
| AP-19 | Magic numbers / magic strings | LOW | T-12 |
| AP-20 | Poor naming (single letters, cryptic abbreviations) | LOW | T-12 |
| AP-21 | Dead code / unused imports / unused modules | LOW | T-12 |
| AP-22 | Verbose or deeply nested conditionals | LOW | T-12 |

---

## CRITICAL

### AP-01 — Hardcoded credentials / secrets
Secrets live in source code and therefore in git history.
**Detection signals**
- Assignments of literals to names containing `secret`, `key`, `password`, `pass`, `pwd`, `token`, `api_key`, `dbPass`, `smtp`:
  `grep -rniE "(secret|passw|pwd|token|api_?key|gateway).{0,20}[=:] *['\"][^'\"]{3,}" .`
- `app.config["SECRET_KEY"] = "..."`, `config = { dbPass: "...", paymentGatewayKey: "pk_live_..." }`
- Strings with known prefixes: `pk_live_`, `sk_live_`, `AKIA`, `ghp_`, `xox`.
- Secrets echoed by an endpoint (e.g. a health check returning `secret_key`) → also AP-05.
**Not a finding:** reading from `os.environ` / `process.env` without a literal fallback secret.

### AP-02 — SQL injection
User-controlled values concatenated/interpolated into SQL.
**Detection signals**
- Python: `execute("..." + var)`, `execute(f"... {var}")`, `execute("... %s" % var)`, `"... '" + nome + "'"`.
- JS: `` db.run(`... ${var}`) ``, `"SELECT ... " + req.body.x`.
- Dynamic `LIKE '%" + termo + "%'`, dynamic `WHERE` built with `+=`.
**Not a finding:** placeholders (`?`, `%s` as a parameter tuple, `:name`), ORM filters (`Model.query.filter(...)`).
List every vulnerable function with its line.

### AP-03 — God Class / God File
One class/module concentrates routing, persistence, business rules, validation and formatting for several domains.
**Detection signals**
- A file/class with ≥3 responsibilities (see project-analysis.md §5), or serving ≥2 business domains.
- A class named `*Manager`, `*Handler`, `*Utils` that creates the DB connection, defines tables, registers routes and runs business flows.
- Entry point (`app.py`/`app.js`) that also contains SQL or business endpoints.
- A single `models.py`/`controllers.py` with functions for every entity (> ~250 lines or > 15 functions).

### AP-04 — Unprotected destructive / arbitrary-execution endpoint
**Detection signals**
- Routes under `/admin`, `/reset`, `/debug`, `/query`, `/exec` without any auth check.
- Endpoint executing SQL/commands received in the request body (`cursor.execute(dados["sql"])`, `eval`, `exec`, `child_process.exec(req...)`).
- `DELETE FROM <table>` with no `WHERE` reachable from HTTP.
- Admin/financial reports or user deletion reachable anonymously (severity HIGH when it only *reads* sensitive data).

### AP-05 — Sensitive data exposure
**Detection signals**
- Serializers/`to_dict()`/`SELECT *` results returned to the client containing `password`, `senha`, `pass`, `hash`, `token`, `secret`.
- Logs with card numbers, passwords or keys: `console.log(\`... ${cc} ... ${config.paymentGatewayKey}\`)`, `print("senha", ...)`.
- Health/info endpoints returning config values (`secret_key`, `db_path`, `debug`).
- Raw exception messages returned to clients (`return {"erro": str(e)}`) — leaks internals (also AP-15).

---

## HIGH

### AP-06 — Insecure password storage
**Detection signals**
- Plaintext: `INSERT INTO usuarios (... senha ...)` with the raw value; login comparing `senha = '<input>'` in SQL → **CRITICAL**.
- Weak hash: `hashlib.md5(`, `hashlib.sha1(`, `crypto.createHash('md5'|'sha1')` for passwords.
- Fake crypto: base64 encoding, loops that build "hashes", truncated strings (`badCrypto`).
- Default password fallback (`pwd || "123456"`).
**Fix:** salted adaptive KDF (`werkzeug.security.generate_password_hash` / `bcrypt` / Node `crypto.scrypt`).

### AP-07 — Fat Controller / business logic in routes
**Detection signals**
- Route handlers > ~30 lines, or that contain: price/discount/total calculations, status machines, overdue rules, aggregations, multi-entity orchestration.
- ORM queries or SQL inside route handlers/views (`Task.query...` inside `@bp.route` function).
- Notification/e-mail/payment side effects inline in the handler (`print("ENVIANDO EMAIL...")`).
- The same business rule implemented in a model method **and** re-implemented in routes (e.g. `is_overdue()` exists but routes recompute it).

### AP-08 — Tight coupling / no dependency injection
**Detection signals**
- Collaborators instantiated inside the code that uses them (`new sqlite3.Database(...)` in a constructor, `NotificationService()` inside a handler, `get_db()` called from every function).
- Modules importing the concrete DB/connection singleton everywhere; impossible to pass a test double.
- No app factory / composition root (`app = Flask(__name__)` at import time with side effects such as `db.create_all()`).

### AP-09 — Mutable global state
**Detection signals**
- Module-level mutable variables written at runtime: `global db_connection`, `let globalCache = {}`, `let totalRevenue = 0`, lists used as in-memory stores (`self.notifications = []` on a shared instance).
- `check_same_thread=False` shared connection across requests.

### AP-10 — Non-atomic multi-step writes / callback pyramid
**Detection signals**
- Several dependent `INSERT/UPDATE` statements for one business operation without `BEGIN/COMMIT/ROLLBACK` (or ORM transaction). A failure halfway leaves partial data (order without items, enrollment without payment).
- Validation loop followed by a write loop that re-reads the same rows (race + duplicated queries).
- Nested callbacks ≥3 levels (`db.get(..., () => db.run(..., () => db.run(...)))`), manual counters to know when async work finished (`pending--; if (pending === 0) res.json(...)`).
- Errors ignored inside callbacks (`(err) => { res.send(...) }` without checking `err`).

### AP-11 — Debug / insecure runtime configuration hardcoded
**Detection signals**
- `debug=True`, `app.config["DEBUG"] = True`, `app.run(debug=True, host="0.0.0.0")` hardcoded.
- `CORS(app)` / `cors()` with no origin restriction **and** credentials/admin routes (report as part of this finding, not separately).

---

## MEDIUM

### AP-12 — N+1 queries
**Detection signals**
- A query executed inside a loop over the results of another query:
  `for row in rows: cursor.execute("... WHERE id = " + row[...])`, `for t in tasks: User.query.get(t.user_id)`,
  `courses.forEach(c => db.all("... WHERE course_id = ?"...))`, `len(u.tasks)` lazy-loaded per user.
- Several `COUNT(*)` queries that could be one `GROUP BY` (`filter_by(status='pending').count()` × N).
- Loading every row to count in Python (`Task.query.all()` then loop to count overdue).

### AP-13 — Duplicated code
**Detection signals**
- Identical dict-building blocks for the same entity in several functions (row → dict mapping repeated).
- The same validation (`len(title) < 3`, `status in [...]`, e-mail regex) copied across create/update handlers.
- Same rule (overdue computation, status list) in 3+ places. Helpers that exist (`utils/helpers.py`) but are not used.

### AP-14 — Missing or inconsistent input validation
**Detection signals**
- `request.get_json()` / `req.body` fields used without type checks (`preco < 0` on a string raises 500).
- Update endpoint validates less than create (e.g. category only validated on create).
- `int(request.args[...])` without try/except → 500 on bad input. No existence check before using FK ids.
- `request.get_json()` result used without `None` check (`dados.get` on `None`).

### AP-15 — Decentralized / swallowing error handling
**Detection signals**
- `try/except Exception` (or bare `except:`) in every handler returning `jsonify({"erro": str(e)}), 500`.
- Bare `except:` that hides programming errors. Errors ignored in callbacks.
- No `@app.errorhandler` / Express error middleware (`(err, req, res, next)`).
- Business errors signalled by returning `{"erro": ...}` dicts from models instead of exceptions.

### AP-16 — Deprecated / legacy APIs
Always check; report "none found" explicitly if clean. Recommend the modern equivalent.

| Deprecated usage (signal) | Stack | Modern equivalent |
|---|---|---|
| `datetime.utcnow()`, `datetime.utcfromtimestamp()` | Python ≥3.12 | `datetime.now(timezone.utc)` |
| `Model.query.get(id)` (SQLAlchemy `Query.get`, legacy since 2.0) | Flask-SQLAlchemy 3 / SQLAlchemy 2 | `db.session.get(Model, id)` / `db.get_or_404(Model, id)` |
| `Model.query.filter_by(...).all()` style (legacy Query API) | SQLAlchemy 2 | `db.session.execute(db.select(Model).filter_by(...)).scalars()` (recommendation; LOW priority) |
| `@app.before_first_request` | Flask ≥2.3 (removed) | run in app factory / `with app.app_context()` |
| `flask.json.JSONEncoder`, `app.json_encoder` | Flask ≥2.3 | `app.json = CustomJSONProvider(app)` |
| `from flask import escape/Markup` | Flask ≥3 | `from markupsafe import escape, Markup` |
| `new Buffer(x)` / `Buffer(x)` | Node | `Buffer.from(x)` / `Buffer.alloc(n)` |
| `body-parser` package for JSON | Express ≥4.16 | `express.json()` / `express.urlencoded()` |
| `req.param('x')` | Express 4 (removed in 5) | `req.params.x` / `req.query.x` / `req.body.x` |
| `res.send(status, body)`, `res.json(status, obj)` | Express 4 deprecated | `res.status(code).json(obj)` |
| `crypto.createCipher(` | Node | `crypto.createCipheriv(` |
| `url.parse(` | Node | `new URL(` |
| Callback-only DB APIs where a promise API exists (e.g. `sqlite3` callbacks) | Node | promise wrapper + `async/await` (legacy style, report under AP-10 if it causes pyramids) |
| `sqlite3.verbose()` in production code | Node sqlite3 | only enable in development |

Also flag pinned dependency versions with known end-of-life when obvious (e.g. Flask 1.x, Express 3.x).

### AP-17 — Missing referential integrity
**Detection signals**
- Delete of a parent row without deleting/blocking children (`DELETE FROM users` while `enrollments.user_id` references it); comments/messages admitting "dados sujos".
- Tables with `*_id` columns but no `FOREIGN KEY`, `ON DELETE` rule or ORM `cascade`.
- Manual child deletion loops in routes (`for t in tasks: db.session.delete(t)`) instead of a cascade.

---

## LOW

### AP-18 — print / console.log as logging
`print(`, `console.log(` in request flow. No log levels, no logger. (If it prints secrets/card data → AP-05 CRITICAL.)

### AP-19 — Magic numbers / magic strings
Unnamed literals with business meaning: discount tiers `10000/0.1/5000/0.05`, `priority <= 2`, `len(password) < 4`,
status lists repeated as literals `['pending','in_progress','done','cancelled']`, ports, `'#000000'`, card prefix `"4"`.

### AP-20 — Poor naming
Single-letter or cryptic identifiers outside tiny lambdas: `u, e, p, cid, cc, t, c, d, p1..p5`, request fields `usr/eml/pwd/c_id`,
generic names `data`, `result`, `manager`, `utils`, functions named `badCrypto`, `logAndCache`.
(Do not rename public request/response fields — that would break the contract; rename internal variables only.)

### AP-21 — Dead code / unused imports
Imports never referenced (`import os, sys, json, time`), unused exported functions/constants (`totalRevenue`, helpers never called),
unused services, commented-out blocks.

### AP-22 — Verbose / deeply nested conditionals
`if cond: return True else: return False`, 3+ nested `if` that could be a single boolean expression or guard clauses,
`type(x) == list` instead of `isinstance`.
