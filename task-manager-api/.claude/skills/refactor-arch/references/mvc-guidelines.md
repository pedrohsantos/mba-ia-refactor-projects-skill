# MVC Architecture Guidelines (Phase 3 target)

The target is a **layered MVC** adapted to HTTP APIs. In an API there is no HTML template, so the
**View** layer is the HTTP boundary: route declarations + response serialization (JSON shape).

```
HTTP request
   │
   ▼
[ Views / Routes ]  ── parse request, call controller, serialize response (status + JSON)
   │
   ▼
[ Controllers ]     ── application flow: validate input, orchestrate models & services, enforce business rules
   │
   ▼
[ Models ]          ── data + domain rules of one entity; all persistence (SQL/ORM) lives here
   │
   ▼
 Database
Cross-cutting: config (env), middlewares (errors, auth), services (external integrations), composition root
```

## 1. Layer responsibilities

| Layer | MUST | MUST NOT |
|---|---|---|
| **Config** (`config/`) | Read every setting from environment variables (with `.env` support), expose typed constants, provide safe *non-secret* dev defaults, generate an ephemeral random secret (with a warning) when a secret is absent in development | Contain real secrets, passwords, API keys |
| **Models** (`models/`) | Represent an entity; own its persistence (parameterized SQL or ORM); expose intention-revealing functions (`find_by_id`, `create`, `list_with_items`); hold entity rules (`is_overdue`, valid statuses, password hashing); serialize the entity to a dict **without sensitive fields**; run multi-step writes in a transaction | Import the web framework (`request`, `jsonify`, `req`, `res`); know HTTP status codes; print |
| **Controllers** (`controllers/`) | Receive plain data (dicts/DTOs), validate it, apply business rules (totals, discounts, status transitions), orchestrate models and services, raise domain exceptions (`NotFoundError`, `ValidationError`, `ConflictError`) | Touch `request`/`res` objects; build SQL; format HTTP responses; catch-all `except Exception` |
| **Views / Routes** (`views/` or `routes/`) | Declare endpoints (same paths/methods as before); extract params/body/query; call one controller function; return `status + JSON` | Contain business rules, SQL/ORM queries, loops over data, try/except returning 500 |
| **Middlewares** (`middlewares/`) | Centralized error handler mapping domain exceptions → HTTP status/JSON; 404/405/500 handlers; auth guards (admin token) | Business logic |
| **Services** (`services/`, optional) | Wrap external infrastructure (e-mail, SMS, payment gateway, cache) behind a small interface, configured from config, injected where used | Persist entities or contain HTTP handling |
| **Composition root** (`app.py` / `app.js` / `create_app()`) | Create the app, load config, init DB, register routes and middlewares, wire dependencies; be the **single entry point** | Contain endpoints with logic or SQL |

**Dependency rule:** arrows only point down. Views → Controllers → Models. Nothing imports a layer above it.
Controllers may call services; models never call services.

## 2. Target layout — Python / Flask

```
<project>/
├── app.py                      # entry point: app = create_app(); app.run(...) from config
├── src/                        # (or keep top-level packages if the project already uses them)
│   ├── app.py                  # create_app(): composition root
│   ├── config/settings.py      # env-based settings
│   ├── database.py             # connection / db object, init + schema + seed
│   ├── models/<entity>_model.py
│   ├── controllers/<entity>_controller.py
│   ├── views/<entity>_routes.py   # Blueprints
│   ├── middlewares/error_handler.py
│   ├── middlewares/auth.py     # if admin routes exist
│   └── utils/ (exceptions.py, validators.py, logging)
├── .env.example
└── requirements.txt
```

Flask specifics:
- Use **Blueprints** per domain in the views layer; register them in `create_app()`.
- Use `@app.errorhandler(AppError)` + `@app.errorhandler(Exception)` in `middlewares/error_handler.py`.
- Raw `sqlite3`: open one connection per request (`flask.g`) or per call; close on `teardown_appcontext`. No `global` connection.
- SQLAlchemy: keep `db = SQLAlchemy()` in `database.py`, `db.init_app(app)` in the factory, `db.session.get(Model, id)`, eager loading (`joinedload`/`selectinload`) and `func.count` + `group_by` for stats.
- Read config via `os.environ` (+ `python-dotenv` if available). `DEBUG` defaults to `False`.

## 3. Target layout — Node.js / Express

```
<project>/
├── src/
│   ├── app.js                  # composition root: buildApp(deps) + listen (entry from package.json)
│   ├── config/index.js         # env-based settings
│   ├── config/database.js      # connection + promise helpers (run/get/all/transaction) + schema/seed
│   ├── models/<entity>Model.js
│   ├── controllers/<entity>Controller.js
│   ├── routes/<entity>Routes.js   # express.Router() — the View layer
│   ├── middlewares/errorHandler.js, auth.js
│   ├── services/<integration>Service.js
│   └── utils/ (errors.js, password.js, asyncHandler.js)
├── .env.example
└── package.json
```

Express specifics:
- Wrap callback DB APIs in promises once (`config/database.js`), use `async/await` everywhere.
- Every async route goes through `asyncHandler` so rejections reach the error middleware `(err, req, res, next)` registered **last**.
- Controllers are factories receiving their dependencies: `createCheckoutController({ userModel, courseModel, paymentService })`.

## 4. Other stacks (mapping)

| Stack | Views/Routes | Controllers | Models | Error handling |
|---|---|---|---|---|
| FastAPI | `APIRouter` modules | plain functions/classes | SQLAlchemy/Pydantic models + repository | `@app.exception_handler` |
| Django | `urls.py` + DRF views (thin) | `services.py` | `models.py` (ORM) | DRF exception handler / middleware |
| Spring | `@RestController` (thin) | `@Service` | `@Entity` + `Repository` | `@ControllerAdvice` |
| NestJS | `@Controller` | `@Injectable` service | entities/repositories | Exception filters |

## 5. Strategy by starting point

| Starting point | Strategy |
|---|---|
| **Monolith / flat files** (everything in 1–4 files, or one God class) | Full restructuring: create every layer, split per domain, delete the old god files after moving their content. |
| **Pseudo-layered** (`models.py`/`controllers.py` exist but leak) | Split per domain into the folders above; move request parsing out of "controllers" into views; move SQL out of controllers into models. |
| **Partially layered** (`models/`, `routes/`, `services/` exist) | Keep the existing folder names that already match a layer (`routes/` = views, `models/` = models). Add the missing layers (`config/`, `controllers/`, `middlewares/`). Move business logic and queries out of routes into controllers/models; reuse/repair existing helpers instead of duplicating them; split files that mix domains (e.g. category CRUD inside report routes). Do not rename things just for taste. |

## 6. Contract preservation rules

- Same paths, methods and success/error status codes for every endpoint in the Phase 1 inventory.
- Same response envelope and field names (`{"dados": ..., "sucesso": true}` stays that way even if not ideal).
- Same port and same start command (or README updated).
- Allowed **intentional** changes (must be listed in the Phase 3 summary): removing sensitive fields from responses,
  requiring an admin token on destructive/admin routes, requiring an authenticated user/admin on user-management routes
  (T-13b), rejecting privilege fields (`role`, `is_admin`, `active`) on public endpoints, returning a generic message
  instead of raw exception text on 500, rejecting input that previously caused a 500.
- Contract preservation never justifies keeping a CRITICAL/HIGH vulnerability open (see SKILL.md Phase 3, step 4).
- Seed data must still be created so the app is usable after boot.

## 7. Definition of done (checked in validation)

- [ ] `config/` exists and no secret literal remains in code
- [ ] Models own all persistence; zero SQL/ORM calls in views/routes
- [ ] Views/routes only map HTTP ⇄ controller
- [ ] Controllers hold the application flow and business rules
- [ ] One centralized error handler; no `try/except` returning 500 in handlers
- [ ] Single clear entry point / composition root
- [ ] App boots; every baseline endpoint responds with the same status
