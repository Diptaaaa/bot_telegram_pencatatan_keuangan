# ECC (Everything Claude Code) Engineering Standards

This rule defines engineering excellence, verification discipline, and security standards adapted from ECC.

## 1. Core Workflow
1. **Plan before editing**: Trace the complete flow and impact before touching code.
2. **Test-first / Verification**: Write or run targeted tests/checks to verify bug fixes and new functionality.
3. **Security Review**: Check security boundaries before shipping.
4. **Clean Commits & Diffs**: Self-contained, readable, easy to revert.

## 2. Coding Standards
- **Small & Focused**: Keep functions small and modules single-responsibility.
- **Explicit over Implicit**: Type hints everywhere, avoid hidden side-effects.
- **Fail Loudly & Gracefully**: Handle exceptions at proper boundaries without silent data corruption.
- **Zero Hardcoded Secrets**: Always load secrets from environment variables.
- **Database Safety**: Always use parameterized queries (prepared statements); never concatenate strings into SQL.

## 3. Security Checklist
Before finalizing changes:
- [ ] No API keys, tokens, or credentials in source code.
- [ ] Input validation applied at all user entrypoints.
- [ ] Safe database access (no SQL injection possible).
- [ ] Error messages do not leak internal system details or credentials.
- [ ] Authentication / Authorization enforced where applicable.

## 4. Delivery & Verification Loop
- Verify code compiles and passes syntax checks (`py_compile`).
- Run relevant unit/integration checks before considering work complete.
- Follow conventional commit style: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`.
