# Audit Report Template (Phase 2)

The report is printed to the user **and** saved as Markdown (`reports/audit-<project-folder>.md`).
Follow the structure below exactly. Text inside `<...>` is replaced; everything else is literal.
Write descriptions in the user's language (default: Portuguese pt-BR); keep headings, labels and severity tags in English.

## Rules

1. Findings are ordered **CRITICAL → HIGH → MEDIUM → LOW**; inside a severity, by file path then line.
2. Every finding has `File:` with **exact** `path:line` or `path:start-end` (path relative to project root).
   Several locations → one per line under `File:`.
3. `Evidence:` is a short literal snippet (≤ 3 lines) copied from the code — proof the line number is right.
4. `Summary` counts must equal the number of findings in each severity, and `Total` must equal their sum.
5. The `Deprecated APIs` section is mandatory, even if it only says "None found".
6. The report ends with the `Refactoring Plan` and the confirmation question. Nothing is modified before the answer.

## Template

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <project folder name>
Stack:   <Language> + <Framework> <version>
Files:   <N> analyzed | ~<LOC> lines of code
Date:    <YYYY-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [CRITICAL] <Anti-pattern name> (<AP-ID>)
File: <path>:<line or start-end>
Evidence: `<short code snippet>`
Description: <what is wrong, concretely, in this code>
Impact: <consequence for security / maintainability / correctness>
Recommendation: <what to do> (playbook <T-ID>)

### [HIGH] <...>
...

### [MEDIUM] <...>
...

### [LOW] <...>
...

## Deprecated APIs
| Location | Deprecated usage | Modern replacement |
|---|---|---|
| <path:line> | <call> | <replacement> |
<or the sentence: "None found — checked against catalog AP-16.">

## Architecture Assessment
Current: <style from project-analysis §5> — <1–2 lines>
Target:  MVC (config / models / views-routes / controllers / middlewares) — <1–2 lines on what changes>

================================
Total: <N> findings
================================

## Refactoring Plan
<target directory tree>

| Step | Transformation | Findings resolved |
|---|---|---|
| 1 | <T-ID name> | <AP-IDs / finding titles> |
| ... | ... | ... |

Intentional contract changes (if approved): <list or "none">

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
````

## Example finding (well-formed)

```markdown
### [CRITICAL] SQL Injection (AP-02)
File: models.py:28
File: models.py:47-50
File: models.py:109-111
Evidence: `cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))`
Description: 14 funções montam SQL concatenando valores vindos da requisição (nome, email, senha, termo de busca).
Impact: Bypass de login com `' OR '1'='1`, leitura/alteração arbitrária de dados.
Recommendation: Usar queries parametrizadas com placeholders `?` em todas as consultas (playbook T-02).
```

## Example of a bad finding (do not do this)

```markdown
### [HIGH] Código ruim
File: models.py
Description: O código tem problemas.
```
(no line, no evidence, no anti-pattern ID, vague description)
