# AGENTS.md：接手开发原则

以下开发原则来自项目所有者在本聊天中提供的 `AGENTS.md` 指令；它们是工作方式，不是业务功能或验收证据。

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them; don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No flexibility or configurability that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't improve adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style.
- Mention unrelated dead code; don't delete it unless asked.
- Remove imports, variables and functions that your own changes made unused.
- Every changed line should trace directly to the request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

- Turn a change into a concrete, checkable outcome.
- For bug fixes, reproduce the issue, fix it, and run relevant tests.
- For refactors, ensure tests pass before and after.
- For multi-step work, state a brief plan with a verification step for each stage.
- Keep unit tests, real browser reading, Mac Scheduled and later Windows real-device acceptance distinct.

项目需求的权威顺序与旧文冲突另见 `docs/DECISIONS_AND_CONFLICTS.md`。
