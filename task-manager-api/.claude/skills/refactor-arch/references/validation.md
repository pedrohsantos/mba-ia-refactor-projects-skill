# Validation Procedure (Phase 3)

Success is only reported after these checks were **actually executed**. Use 127.0.0.1 instead of `localhost`
(on Windows `localhost` may try IPv6 first and add seconds per request).

## 1. Baseline (before touching any file)

1. Install dependencies in an isolated environment (`python -m venv .venv && pip install -r requirements.txt`, `npm ci`/`npm install`).
   If two projects pin conflicting versions, use one environment per project.
2. Run required setup steps (seed scripts, migrations) exactly as the project README says.
3. Start the app in the background, capture stdout/stderr to a log file, wait until the port answers.
4. Build a cases file from the Phase 1 endpoint inventory: **every endpoint at least once**, plus one error case per
   validation branch you saw (404 for missing id, 400 for invalid body). Order the cases so that creates run before
   updates/deletes of the created ids. Use a fresh database for each run (delete the SQLite file / restart in-memory DB) so ids are deterministic.
5. Run the cases with the bundled runner and save the output as the baseline:
   ```bash
   python .claude/skills/refactor-arch/scripts/smoke_test.py http://127.0.0.1:<port> cases.json > baseline.txt
   ```
   (No Python? Use one `curl -s -o /dev/null -w "%{http_code}" -X <METHOD> ...` per case.)
6. Stop the server (kill the process listening on the port).

Case file format:
```json
[
  {"method": "GET",  "path": "/produtos"},
  {"method": "POST", "path": "/produtos", "body": {"nome": "Livro", "preco": 50, "estoque": 5}},
  {"method": "DELETE", "path": "/admin/x", "headers": {"X-Admin-Token": "dev-token"}},
  {"method": "POST", "path": "/login", "body": {"email": "admin@x.com", "password": "..."}, "capture": {"admin_token": "token"}},
  {"method": "DELETE", "path": "/users/2", "headers": {"Authorization": "Bearer {{admin_token}}"}}
]
```
`capture` stores a top-level field of the JSON response in a variable; `{{name}}` is replaced in later paths, headers and bodies.
Use it to test authenticated routes (login once, reuse the token).

## 2. Boot check (after refactoring)

- Same start command as before (`python app.py`, `npm start`). Start with a fresh DB and the env vars from `.env.example`.
- Pass criteria: process stays alive, port answers, **no traceback / unhandled error** in the log.
- Also import-check every new module (Python: `python -c "import <module>"` for each; Node: `node -e "require('./src/...')"`),
  so unused-at-boot modules are not broken.

## 3. Endpoint check

- **Security negative cases are mandatory** for every auth fix: anonymous call → 401, authenticated non-admin on an
  admin route → 403, anonymous sign-up with `role: admin` → 403, then the same call with an admin token → success.
  A CRITICAL/HIGH auth finding is only "fixed" when these cases pass.

- Replay the same cases file against the refactored app → `after.txt`.
- Compare `METHOD PATH STATUS` per line with the baseline (`diff` the first three columns).
  Every line must match, except for the **intentional contract changes** declared in the plan
  (e.g. admin routes now need `X-Admin-Token` — add the header in the case, and add one extra case without the
  header expecting 401/403).
- Spot-check response bodies: same envelope and field names (`dados`, `sucesso`, `erro`, …), sensitive fields gone.

## 4. Static check — no CRITICAL/HIGH signal left

Run the detection greps from the catalog on the refactored source (exclude `.claude/`, deps, `reports/`):

```bash
# AP-01 hardcoded secrets
grep -rniE "(secret|passw|pwd|token|api_?key|gateway).{0,20}[=:] *['\"][^'\"]{6,}" --include=*.py --include=*.js src/ app.py
# AP-02 SQL built by concatenation / interpolation
grep -rnE "execute\(\s*f?[\"'].*(\+|\{)|\b(run|get|all)\(\s*\`.*\\$\{" --include=*.py --include=*.js .
# AP-07 queries inside the view layer
grep -rnE "\.query\.|execute\(|db\.(run|get|all)\(" views/ routes/ src/views src/routes
# AP-16 deprecated APIs
grep -rnE "utcnow\(|\.query\.get\(|new Buffer\(|bodyParser" --include=*.py --include=*.js .
# AP-15 handler-level catch-all
grep -rnE "except Exception|except:" views/ routes/ controllers/ src/
```
Each hit must be either fixed or explained as a false positive in the Phase 3 summary.

## 5. Cleanup

Stop every process you started, delete temporary DB files / logs that are not part of the project,
and make sure `.env`, virtualenvs, `node_modules/` and `*.db` are not staged for commit.
