# AGENTS.md — Development Guidelines & Skills

This repository integrates **Ponytail** (minimalism, YAGNI, senior developer pragmatism) and **ECC** (engineering rigor, security checklist, verification loops).

---

## 1. Operating Philosophy

### Ponytail: The Simplification Ladder
Before adding new code or abstractions, evaluate the ladder:
1. **Does this need to exist at all?** (YAGNI — You Ain't Gonna Need It)
2. **Already in this codebase?** Reuse existing helpers, queries, or utilities.
3. **Does the standard library do it?** Prefer Python stdlib over external libraries.
4. **Does an already-installed dependency solve it?** Never add a package if an existing one or few lines of code suffice.
5. **Can it be one line?** Make it concise.
6. **Only then:** Write the minimal code that reliably works.

> **Bug Fix Rule**: Fix root cause, not symptom. Grep callers and fix where logic originates.

---

### ECC: Quality & Security Guardrails
While keeping code minimal, never compromise on safety:
- **Zero Secrets in Code**: Secrets live strictly in `.env`.
- **Input Validation**: Validate amounts, dates, and commands at boundaries.
- **SQL Injection Prevention**: Parameterized queries only (`?` in SQLite).
- **Verification Loop**: Run syntax/compilation checks (`python -m py_compile`) and manual or automated tests before shipping.
- **Graceful Error Handling**: Do not allow unhandled exceptions to crash the bot or corrupt data.

---

## 2. Installed Skills (in `.agents/skills/`)

### Ponytail Suite:
- **`ponytail`**: Core skill enforcing the simplification ladder and YAGNI.
- **`ponytail-review`**: Review diffs for bloat, unnecessary abstractions, and complexity.
- **`ponytail-audit`**: Audit codebase for dead code and over-engineering.
- **`ponytail-debt`**: Track deliberate shortcuts and ceilings.
- **`ponytail-gain`**: Quantify complexity reduction and lines deleted.
- **`ponytail-help`**: Command reference and instructions.

### ECC Suite:
- **`python-patterns`**: Idiomatic Python, PEP 8, typing, and async best practices.
- **`python-testing`**: Python unit test patterns, pytest fixtures, and async test cases.
- **`security-review`**: Security review checklist for inputs, auth, secrets, and DB.
- **`tdd-workflow`**: Test-driven development workflow (Red-Green-Refactor).
- **`verification-loop`**: Systematic verification steps before completing tasks.
- **`backend-patterns`**: Database layer isolation, API contracts, error boundaries.
- **`coding-standards`**: Consistent code style and structural rules.
- **`error-handling`**: Robust error categorization and handling strategies.
- **`git-workflow`**: Clean git commit conventions and branching hygiene.

### Text & Writing Suite:
- **`humanizer`**: Menghapus pola tulisan kaku ala AI ("AI tells", overused cliches, formulaic triads, staging) agar teks dokumentasi, pesan bot, dan komunikasi terdengar natural layaknya ditulis manusia.
