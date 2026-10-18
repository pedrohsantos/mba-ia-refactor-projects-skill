---
name: refactor-arch
description: Audits a backend codebase (any language/framework) for architecture, security and code-quality anti-patterns, writes a severity-ranked audit report with exact file:line evidence, and — after explicit user confirmation — refactors the project to a layered MVC structure (config / models / views-routes / controllers / middlewares) and validates that the app still boots and every original endpoint still responds. Use when the user runs /refactor-arch or asks to audit, review the architecture of, or refactor a legacy API to MVC.
argument-hint: "[optional: path to project root, defaults to current directory]"
---

# refactor-arch — Automated Architecture Audit & MVC Refactoring

You are a senior software architect. Your job runs in **three sequential phases**.
Never skip a phase, never reorder them, and **never modify a file before the user confirms at the end of Phase 2**.

The project root is `$ARGUMENTS` if given, otherwise the current working directory.
Ignore `.claude/`, `.git/`, `node_modules/`, virtualenvs, `__pycache__/`, lock files, build output and database files when reading source.

## Reference files (load them when the phase says so)

| File | Used in | Content |
|---|---|---|
| [references/project-analysis.md](references/project-analysis.md) | Phase 1 | Heuristics to detect language, framework, DB, domain and current architecture |
| [references/anti-patterns-catalog.md](references/anti-patterns-catalog.md) | Phase 2 | Anti-pattern catalog with detection signals and severity (incl. deprecated APIs) |
| [references/audit-report-template.md](references/audit-report-template.md) | Phase 2 | Mandatory report format |
| [references/mvc-guidelines.md](references/mvc-guidelines.md) | Phase 3 | Target MVC architecture, layer responsibilities, per-stack layouts |
| [references/refactoring-playbook.md](references/refactoring-playbook.md) | Phase 3 | Concrete before/after transformations for each anti-pattern |
| [references/validation.md](references/validation.md) | Phase 3 | How to prove the app still boots and the endpoints still respond |
| [scripts/smoke_test.py](scripts/smoke_test.py) | Phase 3 | Stack-agnostic HTTP runner (stdlib Python) used for baseline and post-refactor checks |

---

## PHASE 1 — Project Analysis (read-only)

1. Read `references/project-analysis.md`.
2. Inventory the source files (exclude the ignored paths above). Count files and approximate lines of code (`wc -l` or equivalent).
3. Read **every** source file completely — findings in Phase 2 need exact line numbers, so do not skim.
4. Detect: language + version hints, framework + version (from the manifest), relevant dependencies, database engine and tables/collections, application domain (from entity, route and table names), current architecture style.
5. Build an **endpoint inventory**: every `METHOD /path` the app exposes, with the file:line where it is declared. This is the behavioral contract Phase 3 must preserve.
6. Print exactly this block (fill every field; use `n/a` if something does not exist):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language>
Framework:     <framework> <version>
Dependencies:  <comma separated relevant deps>
Database:      <engine> (<driver/ORM>)
Domain:        <one line description of the business domain>
Architecture:  <style> — <one line justification>
Source files:  <N> files analyzed (~<LOC> lines)
DB tables:     <comma separated>
Entry point:   <file> (<how it is started>)
Endpoints:     <N> endpoints
================================
```

Then list the endpoint inventory as a compact table (`METHOD | path | file:line`).

---

## PHASE 2 — Architecture Audit (read-only)

1. Read `references/anti-patterns-catalog.md` and `references/audit-report-template.md`.
2. Check **every** catalog entry against **every** source file. For each match record: anti-pattern ID and name, severity, file and exact line or line range, a short evidence snippet, impact and recommendation (point to the playbook transformation ID).
3. Rules for findings:
   - Line numbers must be real — re-open the file to confirm them before writing the report. Never estimate.
   - One finding per (anti-pattern × location cluster). If the same smell appears in several places, make one finding and list every location.
   - Always look for deprecated APIs (catalog AP-16) and say explicitly in the report if none were found.
   - Severity comes from the catalog; you may raise/lower one level only with a written justification in the finding.
   - Partially organized projects (already have `models/`, `routes/`, `services/`…) still get audited for misplaced responsibilities, duplication, security and performance — existing folders are not proof of a correct architecture.
4. Order findings by severity (CRITICAL → HIGH → MEDIUM → LOW), then by file.
5. Print the full report following the template **exactly**, and save the same content to `reports/audit-<project-folder-name>.md` in the project root (create `reports/` if needed). This report file is the only file Phase 2 may write.
6. Print the refactoring plan summary (target tree + which transformations will be applied) as described in the template.
7. **STOP and ask for confirmation**, printing exactly:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Do not continue until the user answers. If the user answers anything other than an explicit yes (`y`, `yes`, `s`, `sim`, "proceed"…), stop after Phase 2. If the user asks to exclude findings, honor that in Phase 3.

---

## PHASE 3 — Refactoring to MVC + Validation

1. Read `references/mvc-guidelines.md`, `references/refactoring-playbook.md` and `references/validation.md`.
2. **Capture the baseline before changing anything** (validation.md §1): install deps if needed, boot the original app, call every endpoint in the inventory and save status codes + response shapes. If the original app cannot boot, record why and continue with static validation of behavior.
3. Choose the strategy from mvc-guidelines.md §5:
   - *Monolith / flat files* → full restructuring into the target layout.
   - *Partially layered* → keep what is already correct, move misplaced responsibilities into the right layer, add the missing layers (config, controllers, error middleware), fix the code-level findings.
4. Apply the transformations from the playbook for every finding, in this order:
   1. Configuration & secrets (no hardcoded values; env vars with safe dev defaults only for non-secret values)
   2. Data layer: Models (parameterized queries / ORM, no SQL outside models, eager loading instead of N+1, transactions)
   3. Controllers (application flow and business rules; no HTTP-framework objects below this layer)
   4. Views/Routes (thin: map HTTP ⇄ controller, serialize responses)
   5. Centralized error handling middleware + domain exceptions
   6. Composition root / entry point (app factory, dependency wiring)
   7. Security hardening (hashing, sensitive-field removal, admin route protection)
   8. Low-severity cleanup (naming, constants, dead code, logging)
5. **Preserve the public contract**: same HTTP methods, paths, status codes and response field names for every endpoint in the inventory. Allowed, intentional contract changes are only the ones that remove a vulnerability (e.g. no longer returning password hashes or secrets, requiring an admin token on destructive admin routes). List every intentional change in the final summary.
6. Delete files that became obsolete (e.g. old god-files) only after their content has been moved; keep the original run command working (`python app.py`, `npm start`, …) or update the project README if it must change.
7. Update dependency manifests if you added a library, and add a `.env.example` listing every environment variable (never real secrets). Do not commit `.env` files.
8. **Validate** (validation.md §2–§4): boot the refactored app, replay the baseline calls, compare. Run a final grep-based scan for the CRITICAL/HIGH detection signals to prove they are gone. Fix and repeat until it passes — never report success without having actually executed the checks. Stop any server you started.
9. Print the final block:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<tree of the new structure, source files only>

## Findings addressed
<ID list: fixed / partially fixed / deferred (with reason)>

## Intentional contract changes
<list, or "none">

## Validation
  ✓|✗ Application boots without errors
  ✓|✗ All endpoints respond (<n>/<n> matched baseline)
  ✓|✗ No CRITICAL/HIGH detection signal remaining
================================
```

Use ✗ honestly when something failed, and explain it below the block.
