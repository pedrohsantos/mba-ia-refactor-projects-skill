# Refactoring Playbook (Phase 3)

Concrete transformations. Each one says which anti-patterns it fixes, the steps, and a **before/after** example
(Python/Flask and/or Node/Express — translate the idea to other stacks). Apply them in the order given in SKILL.md.

| ID | Transformation | Fixes |
|---|---|---|
| T-01 | Extract configuration & secrets to environment | AP-01, AP-11 |
| T-02 | Parameterize every query | AP-02 |
| T-03 | Split God file into MVC layers per domain | AP-03 |
| T-04 | Move business logic from routes to controllers / models | AP-07, AP-13 |
| T-05 | App factory + dependency injection, remove global state | AP-08, AP-09 |
| T-06 | Remove N+1 with JOIN / eager loading / aggregation | AP-12 |
| T-07 | Centralized error handling with domain exceptions | AP-15 |
| T-08 | Secure password hashing (with legacy migration) | AP-06 |
| T-09 | Safe serialization & no secrets in logs/responses | AP-05 |
| T-10 | Replace deprecated APIs | AP-16 |
| T-11 | Transactions, async/await and referential integrity | AP-10, AP-17 |
| T-12 | Constants, naming, logging, dead code | AP-18 … AP-22 |
| T-13 | Protect dangerous admin endpoints + role-based authorization (T-13b) | AP-04 |
| T-14 | Validation layer | AP-13, AP-14 |

---

## T-01 — Extract configuration & secrets to environment

1. Create `config/settings.py` (or `config/index.js`) that reads `os.environ` / `process.env`.
2. Non-secret values may have dev defaults (port, DB path). Secrets have **no literal default**: generate an ephemeral
   random value with a warning, or disable the feature that needs it.
3. `DEBUG` defaults to false. Add `.env.example`. Never commit `.env`.

**Before (Flask)**
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
app.run(host="0.0.0.0", port=5000, debug=True)
```
**After**
```python
# config/settings.py
import os, secrets, logging
from dotenv import load_dotenv
load_dotenv()

def _bool(name, default=False):
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)   # ephemeral if absent
    DEBUG = _bool("FLASK_DEBUG")
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")  # admin routes disabled when unset

if not os.getenv("SECRET_KEY"):
    logging.getLogger(__name__).warning("SECRET_KEY not set — using an ephemeral key (dev only)")
```
**Before (Express)**
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_1234567890abcdef", port: 3000 };
```
**After**
```js
// src/config/index.js
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  databaseUrl: process.env.DATABASE_URL || ':memory:',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || null, // no literal secret
  adminToken: process.env.ADMIN_TOKEN || null,
});
```

---

## T-02 — Parameterize every query

Replace every concatenation/interpolation with placeholders. Dynamic filters: build the SQL **structure** from a
whitelist and pass **values** as parameters.

**Before**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"
```
**After**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))   # password checked with hash, see T-08

clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    clauses.append("categoria = ?"); params.append(categoria)
cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)  # structure is whitelisted
```
**Express**
```js
// before
db.get(`SELECT * FROM users WHERE email = '${email}'`);
// after
await db.get('SELECT * FROM users WHERE email = ?', [email]);
```

---

## T-03 — Split God file into MVC layers per domain

1. List every function of the God file and tag it: route / flow+rules / persistence / formatting / config.
2. Group by domain (produto, usuario, pedido, relatorio…).
3. Persistence → `models/<domain>_model.py`; flow + rules → `controllers/<domain>_controller.py`;
   route declarations + request parsing + `jsonify` → `views/<domain>_routes.py`; config → `config/`.
4. Wire everything in `create_app()`; delete the God file once empty.

**Before** (`models.py` with SQL + rules for 4 domains, `controllers.py` reading `request` and printing, `app.py` with routes + raw SQL admin endpoints)

**After**
```python
# models/produto_model.py
class ProdutoModel:
    def __init__(self, get_connection):
        self._conn = get_connection
    def find_by_id(self, produto_id):
        row = self._conn().execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        return _to_dict(row) if row else None

# controllers/produto_controller.py
class ProdutoController:
    def __init__(self, produtos: ProdutoModel):
        self._produtos = produtos
    def obter(self, produto_id):
        produto = self._produtos.find_by_id(produto_id)
        if not produto:
            raise NotFoundError("Produto não encontrado")
        return produto

# views/produto_routes.py
def create_produto_blueprint(controller):
    bp = Blueprint("produtos", __name__)
    @bp.get("/produtos/<int:produto_id>")
    def buscar_produto(produto_id):
        return jsonify({"dados": controller.obter(produto_id), "sucesso": True}), 200
    return bp
```
**Express — splitting a `*Manager` class**
```js
// before: class AppManager { constructor(){ this.db = new sqlite3.Database(':memory:') } initDb(){...} setupRoutes(app){ app.post('/api/checkout', ...150 lines...) } }
// after
// routes/checkoutRoutes.js (View)
router.post('/api/checkout', asyncHandler(async (req, res) => {
  const result = await checkoutController.checkout(req.body);
  res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
}));
// controllers/checkoutController.js: validation + flow; models/*Model.js: SQL; config/database.js: connection
```

---

## T-04 — Move business logic from routes to controllers / models

Rules that belong to one entity (overdue, valid statuses, total of an order) go to the **model**; flows that
coordinate several entities or side effects (create order + decrement stock + notify) go to the **controller**.
Remove duplicates: one implementation, called everywhere.

**Before (logic copied in 4 routes)**
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
        else:
            task_data['overdue'] = False
    ...
```
**After**
```python
# models/task.py
CLOSED_STATUSES = ("done", "cancelled")
def is_overdue(self, now=None):
    now = now or utcnow()
    return bool(self.due_date and self.due_date < now and self.status not in CLOSED_STATUSES)

# routes: data = task.to_dict(); data["overdue"] = task.is_overdue()
```
**Before (discount rule inside the data function)**
```python
desconto = 0
if faturamento > 10000: desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
```
**After**
```python
# controllers/relatorio_controller.py
DISCOUNT_TIERS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))
def calcular_desconto(faturamento):
    return next((faturamento * taxa for limite, taxa in DISCOUNT_TIERS if faturamento > limite), 0)
```

---

## T-05 — App factory + dependency injection, remove global state

**Before**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("loja.db", check_same_thread=False)
    return db_connection
```
**After**
```python
# database.py — one connection per request, stored in flask.g
def get_connection():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_connection(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

# app.py — composition root
def create_app(settings=Settings):
    app = Flask(__name__)
    app.config.from_object(settings)
    app.teardown_appcontext(close_connection)
    produtos = ProdutoModel(get_connection)
    app.register_blueprint(create_produto_blueprint(ProdutoController(produtos)))
    register_error_handlers(app)
    return app
```
**Express**
```js
// before: let globalCache = {}; function logAndCache(k, v){ globalCache[k] = v }
// after: inject a cache instance; state lives in an object owned by the composition root
function buildApp({ db, cache = new Map() }) {
  const enrollmentModel = createEnrollmentModel(db);
  const checkoutController = createCheckoutController({ db, enrollmentModel, cache });
  ...
}
```

---

## T-06 — Remove N+1 queries

**Before**
```python
for row in pedidos:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in cursor2.fetchall():
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
**After (one JOIN, grouped in memory)**
```python
rows = conn.execute("""
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    ORDER BY p.id""").fetchall()
pedidos = {}
for r in rows:
    pedido = pedidos.setdefault(r["id"], {...campos do pedido..., "itens": []})
    if r["produto_id"] is not None:
        pedido["itens"].append({...})
```
**SQLAlchemy**
```python
# before: for t in Task.query.all(): User.query.get(t.user_id); Category.query.get(t.category_id)
tasks = db.session.execute(
    db.select(Task).options(joinedload(Task.user), joinedload(Task.category))
).scalars().all()
# counts: one GROUP BY instead of N count() calls
rows = db.session.execute(db.select(Task.status, func.count()).group_by(Task.status)).all()
```
**Express**
```js
// before: courses.forEach(c => db.all('SELECT * FROM enrollments WHERE course_id = ?', ...nested user/payment lookups))
const rows = await db.all(`
  SELECT c.id AS course_id, c.title, u.name AS student, p.amount, p.status
  FROM courses c
  LEFT JOIN enrollments e ON e.course_id = c.id
  LEFT JOIN users u ON u.id = e.user_id
  LEFT JOIN payments p ON p.enrollment_id = e.id
  ORDER BY c.id, e.id`);
```

---

## T-07 — Centralized error handling with domain exceptions

**Before (in every handler)**
```python
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
**After**
```python
# utils/exceptions.py
class AppError(Exception):
    status_code = 400
    def __init__(self, message, status_code=None):
        super().__init__(message); self.message = message
        if status_code: self.status_code = status_code
class ValidationError(AppError): status_code = 400
class NotFoundError(AppError):   status_code = 404
class ConflictError(AppError):   status_code = 409

# middlewares/error_handler.py
def register_error_handlers(app, error_key="erro"):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({error_key: err.message, "sucesso": False}), err.status_code
    @app.errorhandler(HTTPException)
    def handle_http(err):
        return jsonify({error_key: err.description}), err.code
    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Unhandled error")
        return jsonify({error_key: "Erro interno do servidor"}), 500
```
**Express**
```js
// utils/asyncHandler.js
module.exports = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
// middlewares/errorHandler.js — registered LAST
module.exports = (logger) => (err, req, res, next) => {
  const status = err.statusCode || 500;
  if (status >= 500) logger.error(err);
  res.status(status).send(status >= 500 ? 'Erro interno' : err.message);
};
```
Keep the error body shape the project already used (`{"erro": ...}`, `{"error": ...}` or plain text).

---

## T-08 — Secure password hashing (with legacy migration)

**Before**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
```
```js
function badCrypto(pwd){ let h=""; for(let i=0;i<10000;i++){ h += Buffer.from(pwd).toString('base64').substring(0,2) } return h.substring(0,10) }
```
**After (Python — werkzeug ships with Flask)**
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, raw):
    self.password = generate_password_hash(raw)

def check_password(self, raw):
    if self.password.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(self.password, raw)
    # legacy MD5 rows: verify once, then upgrade the hash
    if hmac.compare_digest(self.password, hashlib.md5(raw.encode()).hexdigest()):
        self.set_password(raw)
        return True
    return False
```
**After (Node — built-in crypto)**
```js
const crypto = require('crypto');
function hashPassword(plain) {
  const salt = crypto.randomBytes(16).toString('hex');
  return `scrypt:${salt}:${crypto.scryptSync(plain, salt, 64).toString('hex')}`;
}
function verifyPassword(plain, stored) {
  const [, salt, hash] = stored.split(':');
  return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), crypto.scryptSync(plain, salt, 64));
}
```
Never default a missing password to a constant (`pwd || "123456"`): reject the request instead.
Login: fetch by e-mail with a parameterized query, then verify the hash in code.

---

## T-09 — Safe serialization & no secrets in logs/responses

**Before**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password, ...}
```
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**After**
```python
PUBLIC_FIELDS = ("id", "name", "email", "role", "active", "created_at")
def to_dict(self):
    return {"id": self.id, "name": self.name, "email": self.email, "role": self.role,
            "active": self.active, "created_at": str(self.created_at)}   # no password
```
```js
logger.info(`Processing payment for card ****${card.slice(-4)}`); // never the full PAN, never the key
```
Health checks return status + counts only — no `secret_key`, `db_path`, `debug`.

---

## T-10 — Replace deprecated APIs

| Before | After |
|---|---|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` — if columns store naive UTC (SQLite), use a helper `utcnow()` returning `datetime.now(timezone.utc).replace(tzinfo=None)` to keep comparisons valid |
| `Task.query.get(task_id)` | `db.session.get(Task, task_id)` |
| `Task.query.filter_by(user_id=x).all()` | `db.session.execute(db.select(Task).filter_by(user_id=x)).scalars().all()` |
| `new Buffer(str)` | `Buffer.from(str)` |
| `app.use(bodyParser.json())` | `app.use(express.json())` |
| `res.send(404, 'x')` | `res.status(404).send('x')` |
| `require('sqlite3').verbose()` always on | `verbose()` only when `NODE_ENV !== 'production'` |

**Before**
```python
created_at = db.Column(db.DateTime, default=datetime.utcnow)
user = User.query.get(user_id)
```
**After**
```python
# utils/time.py
def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, same storage format as before

created_at = db.Column(db.DateTime, default=utcnow)
user = db.session.get(User, user_id)
```

---

## T-11 — Transactions, async/await and referential integrity

**Before (Python: write loop without transaction, re-reading rows)**
```python
for item in itens:  # validate
    cursor.execute("SELECT * FROM produtos WHERE id = " + ...)
cursor.execute("INSERT INTO pedidos ...")
for item in itens:  # write
    cursor.execute("SELECT preco FROM produtos ...")   # second read
    cursor.execute("INSERT INTO itens_pedido ...")
    cursor.execute("UPDATE produtos SET estoque = estoque - ...")
db.commit()
```
**After**
```python
def criar(self, usuario_id, itens):
    conn = self._conn()
    with conn:  # BEGIN … COMMIT / ROLLBACK on exception
        produtos = {i["produto_id"]: self._lock_produto(conn, i["produto_id"]) for i in itens}
        ...validate stock using the already-loaded rows...
        cur = conn.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)", (usuario_id, total))
        conn.executemany("INSERT INTO itens_pedido (...) VALUES (?, ?, ?, ?)", linhas)
        conn.executemany("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", baixas)
    return cur.lastrowid
```
**Before (Express callback pyramid)**
```js
db.run("INSERT INTO enrollments ...", [userId, cid], function (err) {
  self.db.run("INSERT INTO payments ...", [this.lastID, ...], function (err) {
    self.db.run("INSERT INTO audit_logs ...", [...], (err) => { res.json(...) });
  });
});
```
**After**
```js
// config/database.js
async function transaction(work) {
  await run('BEGIN');
  try { const r = await work(); await run('COMMIT'); return r; }
  catch (e) { await run('ROLLBACK'); throw e; }
}
// controllers/checkoutController.js
const enrollmentId = await db.transaction(async () => {
  const id = await enrollmentModel.create(userId, courseId);
  await paymentModel.create(id, course.price, 'PAID');
  await auditLogModel.record(`Checkout curso ${courseId} por ${userId}`);
  return id;
});
```
**Referential integrity** — delete children in the same transaction (or declare `ON DELETE CASCADE` / ORM `cascade="all, delete-orphan"`):
```js
await db.transaction(async () => {
  await db.run('DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', [id]);
  await db.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
  await db.run('DELETE FROM users WHERE id = ?', [id]);
});
```
```python
tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan")
```

---

## T-12 — Constants, naming, logging, dead code

**Before**
```python
import os, sys, json, datetime          # only datetime used
if len(password) < 4: ...
print("Produto criado com ID: " + str(id))
def is_admin(self):
    if self.role == 'admin':
        return True
    else:
        return False
let u = req.body.usr; let e = req.body.eml; let cid = req.body.c_id;
```
**After**
```python
import datetime
MIN_PASSWORD_LENGTH = 4                  # models/user.py (single source of truth)
logger = logging.getLogger(__name__)
logger.info("Produto criado com ID %s", produto_id)
def is_admin(self):
    return self.role == ROLE_ADMIN
```
```js
const { usr: name, eml: email, pwd: password, c_id: courseId, card } = req.body; // public field names unchanged
```

---

## T-13 — Protect or neutralize dangerous admin endpoints

- Endpoint that executes arbitrary SQL/commands from the request: **remove the capability**. If the route must keep
  responding, keep it behind the admin guard and restrict it to a single read-only `SELECT` statement.
- Destructive/admin routes: require an admin token from config (`X-Admin-Token`); when `ADMIN_TOKEN` is not configured the
  routes answer `403` (feature disabled) instead of being open.

**Before**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json().get("sql"))
```
**After**
```python
# middlewares/auth.py
def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        provided = request.headers.get("X-Admin-Token", "")
        if not expected:
            raise ForbiddenError("Rotas administrativas desabilitadas (ADMIN_TOKEN não configurado)")
        if not hmac.compare_digest(provided, expected):
            raise UnauthorizedError("Token administrativo inválido")
        return view(*args, **kwargs)
    return wrapper

@bp.post("/admin/query")
@require_admin
def executar_query():
    return jsonify({"dados": controller.consulta_somente_leitura(request.get_json(silent=True) or {}), "sucesso": True})
```
```js
// middlewares/auth.js
module.exports = (config) => (req, res, next) => {
  if (!config.adminToken) return res.status(403).send('Rotas administrativas desabilitadas');
  if (req.get('X-Admin-Token') !== config.adminToken) return res.status(401).send('Não autorizado');
  next();
};
```

### T-13b — Role-based authorization for user management (fixes broken auth / privilege escalation)

When the app has users with roles, closing AP-04 requires **all three** steps — a signed token alone is only step 1:

1. **Signed, expiring token** issued by login (`itsdangerous`/JWT in Python, `jsonwebtoken` or HMAC in Node), verified on every protected request (`Authorization: Bearer <token>`).
2. **Authorization middleware**: `require_auth` loads the current user from the token (401 if missing/invalid/expired/inactive); `require_admin` additionally checks the role (403 if not admin). Apply them to user-management routes:
   - `DELETE /users/<id>` → admin only.
   - `PUT /users/<id>` → the user themself or an admin; only an admin may change `role` or `active`.
   - any route that lists/changes other users' privileges → admin only.
3. **No privileged fields on public endpoints**: public sign-up (`POST /users`) creates `role = "user"`; a request that sends another `role` without an authenticated admin is rejected (403). Never trust `role`, `is_admin`, `active` from an anonymous body.

Keep the first admin reachable: the seed / a bootstrap env var creates it — never a public endpoint.

**Before**
```python
@user_bp.route('/users', methods=['POST'])
def create_user():
    role = data.get('role', 'user')            # anonymous caller chooses "admin"
    ...
@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id): ...                 # no auth at all
return {'token': 'fake-jwt-token-' + str(user.id)}   # forgeable
```
**After**
```python
# middlewares/auth.py
from functools import wraps
from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

def _signer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth-token")

def issue_token(user):
    return _signer().dumps({"user_id": user.id})

def load_current_user():
    """Return the authenticated user or None (anonymous). Invalid tokens raise 401."""
    header = request.headers.get("Authorization", "")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Token inválido")
    try:
        payload = _signer().loads(token, max_age=current_app.config["AUTH_TOKEN_MAX_AGE_SECONDS"])
    except (BadSignature, SignatureExpired):
        raise UnauthorizedError("Token inválido ou expirado")
    user = User.get(payload.get("user_id"))
    if not user or not user.active:
        raise UnauthorizedError("Token inválido ou expirado")
    return user

def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = load_current_user()
        if g.current_user is None:
            raise UnauthorizedError("Autenticação necessária")
        return view(*args, **kwargs)
    return wrapper

def require_admin(view):
    @require_auth
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.current_user.is_admin():
            raise ForbiddenError("Apenas administradores")
        return view(*args, **kwargs)
    return wrapper

# routes/user_routes.py — the view passes the actor; the controller decides
@user_bp.post("/users")
def create_user():
    return jsonify(controller.create_user(request.get_json(silent=True), actor=load_current_user())), 201

@user_bp.put("/users/<int:user_id>")
@require_auth
def update_user(user_id):
    return jsonify(controller.update_user(user_id, request.get_json(silent=True), actor=g.current_user)), 200

@user_bp.delete("/users/<int:user_id>")
@require_admin
def delete_user(user_id): ...

# controllers/user_controller.py
def create_user(self, data, actor=None):
    role = data.get("role", ROLE_USER)
    if role != ROLE_USER and not (actor and actor.is_admin()):
        raise ForbiddenError("Apenas administradores podem definir role")

def update_user(self, user_id, data, actor):
    if not actor.is_admin() and actor.id != user_id:
        raise ForbiddenError("Sem permissão para alterar este usuário")
    if not actor.is_admin() and ({"role", "active"} & data.keys()):
        raise ForbiddenError("Apenas administradores podem alterar role/active")
```
**Express equivalent**
```js
// middlewares/auth.js
const requireAuth = ({ verifyToken, userModel }) => async (req, res, next) => {
  const [scheme, token] = (req.get('Authorization') || '').split(' ');
  if (scheme !== 'Bearer' || !token) return next(new UnauthorizedError());
  const payload = verifyToken(token);                    // throws on bad signature / expiry
  req.currentUser = await userModel.findById(payload.userId);
  return req.currentUser ? next() : next(new UnauthorizedError());
};
const requireAdmin = (req, res, next) => (req.currentUser.role === 'admin' ? next() : next(new ForbiddenError()));
router.delete('/users/:id', requireAuth(deps), requireAdmin, asyncHandler(...));
```
Validation must include the negative cases: anonymous `POST /users` with `role: admin` → 403, anonymous `PUT`/`DELETE /users/<id>` → 401,
non-admin token on `DELETE` → 403, non-admin changing own `role` → 403, admin token → success.

---

## T-14 — Validation layer

Validate in the controller (or a `validators` module used by controllers), once per rule, with the same messages
and status codes the API already returned.

**Before (duplicated in create and update, crashes on wrong types)**
```python
if "preco" not in dados: return jsonify({"erro": "Preço é obrigatório"}), 400
if preco < 0: return jsonify({"erro": "Preço não pode ser negativo"}), 400   # TypeError → 500 if preco is "abc"
```
**After**
```python
# utils/validators.py
def require_fields(data, messages):
    if not isinstance(data, dict) or not data:
        raise ValidationError("Dados inválidos")
    for field, message in messages.items():
        if field not in data:
            raise ValidationError(message)

def non_negative_number(value, message):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValidationError(message)
    return value
```
```js
// Express
function requireFields(body, fields) {
  if (fields.some((f) => !body || !body[f])) throw new ValidationError('Bad Request');
}
```
