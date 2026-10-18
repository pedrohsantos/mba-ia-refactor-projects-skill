# Project Analysis Heuristics (Phase 1)

Goal: build an accurate picture of the stack, the domain, the current architecture and the
public contract (endpoints) **without modifying anything**.

## 1. Language detection

Decide by manifest first, file extensions second.

| Signal (file present at root or subfolder) | Language |
|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `*.py` | Python |
| `package.json` + `*.js`/`*.mjs`/`*.cjs` | JavaScript (Node.js) |
| `package.json` + `tsconfig.json` / `*.ts` | TypeScript (Node.js) |
| `pom.xml`, `build.gradle`, `*.java` | Java |
| `go.mod`, `*.go` | Go |
| `composer.json`, `*.php` | PHP |
| `Gemfile`, `*.rb` | Ruby |
| `*.csproj`, `*.sln`, `*.cs` | C# |

Version hints: `python_requires`, `.python-version`, `engines.node` in `package.json`, `.nvmrc`,
Dockerfile `FROM` lines. If none exists, write "version not pinned".

## 2. Framework detection

Read the dependency manifest and confirm with imports in the code.

| Manifest entry | Import / usage signal | Framework |
|---|---|---|
| `flask` | `from flask import Flask`, `Flask(__name__)`, `@app.route`, `Blueprint` | Flask |
| `django` | `django.conf`, `urls.py`, `views.py`, `INSTALLED_APPS` | Django |
| `fastapi` | `FastAPI()`, `@app.get`, `APIRouter` | FastAPI |
| `express` | `require('express')`, `express()`, `app.get(`, `express.Router()` | Express |
| `@nestjs/core` | `@Controller`, `@Module` | NestJS |
| `koa` / `fastify` / `hapi` | `new Koa()`, `fastify()`, `Hapi.server` | Koa / Fastify / Hapi |
| `spring-boot-starter-web` | `@RestController`, `@SpringBootApplication` | Spring Boot |
| `laravel/framework` | `Route::get`, `artisan` | Laravel |
| `gin-gonic/gin` / `labstack/echo` | `gin.Default()`, `echo.New()` | Gin / Echo |

Report the **exact version** from the manifest (`flask==3.1.1` → `Flask 3.1.1`; `"express": "^4.18.2"` → `Express ^4.18.2`).
List the other runtime dependencies that matter architecturally (CORS, ORM, validation, auth, HTTP clients, env loaders).

## 3. Database detection

| Signal | Engine / access style |
|---|---|
| `import sqlite3`, `sqlite3.connect(`, `require('sqlite3')`, `new sqlite3.Database(` | SQLite, raw driver |
| `':memory:'` as DB path | SQLite in-memory (data lost at restart) |
| `flask_sqlalchemy`, `SQLAlchemy()`, `db.Model`, `SQLALCHEMY_DATABASE_URI` | SQLAlchemy ORM (engine from URI) |
| `psycopg2`, `pg`, `postgres://` | PostgreSQL |
| `pymysql`, `mysql2`, `mysql://` | MySQL |
| `mongoose`, `pymongo`, `mongodb://` | MongoDB |
| `sequelize`, `typeorm`, `prisma`, `knex` | Node ORMs / query builders |

Tables: collect from `CREATE TABLE` statements, `__tablename__`, model class names, migrations, schema files.

## 4. Domain detection

Infer the business domain from nouns in table names, model classes, route paths and seed data.
Examples: `produtos/pedidos/usuarios` → E-commerce; `courses/enrollments/payments` → LMS with checkout;
`tasks/categories/users` → Task manager. Write one line: `<Domain> (<main entities>)`.

## 5. Architecture mapping

Classify the current architecture and justify in one line:

| Style | Signals |
|---|---|
| **Monolithic / flat** | Few files at root, a single file mixes routing + SQL + business rules; or one "Manager"/"Utils" class does everything |
| **Pseudo-layered** | Files named `models.py` / `controllers.py` exist but responsibilities leak (controllers read the request *and* contain rules; models format HTTP output) |
| **Partially layered** | Folders `models/`, `routes/`, `services/`, `utils/` exist, but routes contain business logic/queries, services are unused, config is hardcoded, no central error handling |
| **Layered MVC** | Config module, models/data access, controllers with flow, thin routes/views, error middleware, composition root |

For each source file note its **current responsibilities** (routing, persistence, business rules, validation,
serialization, config, infrastructure). A file with ≥3 responsibilities is a God-file candidate for Phase 2.

## 6. Endpoint inventory (the contract)

Find every route declaration:

| Stack | Patterns to search |
|---|---|
| Flask | `@app.route(`, `@<bp>.route(`, `app.add_url_rule(`, `methods=[...]` (default method = GET) |
| FastAPI | `@app.get/post/put/delete(`, `@router.<method>(` |
| Django | `path(`, `re_path(` in `urls.py` |
| Express | `app.get/post/put/patch/delete(`, `router.<method>(`, `app.use('/prefix', router)` (prefix!) |
| Spring | `@GetMapping`, `@PostMapping`, `@RequestMapping` |

Record `METHOD /path` + `file:line`. Remember blueprint/router prefixes.
Also record how the app is started (`python app.py`, `npm start` → `package.json` scripts) and its port,
and whether a seed step is required (`seed.py`, migrations, in-memory seeds at boot).

## 7. Useful commands (adapt to the shell available)

```bash
# file inventory + LOC (exclude noise)
find . -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' \) \
  -not -path '*/node_modules/*' -not -path '*/.claude/*' -not -path '*/venv/*' | xargs wc -l
# routes
grep -rnE "@(app|[a-z_]+_bp|router)\.(route|get|post|put|patch|delete)\(|add_url_rule\(|app\.(get|post|put|patch|delete)\(" --include=*.py --include=*.js .
# tables
grep -rnE "CREATE TABLE|__tablename__" .
```
