# Prettier Merge-Preview Trap — Worked Example

**Project:** donghanh (donghanhcungban.com)  
**PR:** #797 `feat(ui): animated subject illustrations`  
**Date:** September 2026  
**CI check:** Type + Lint + Format (Prettier)

## What Happened

1. PR #797 opened on branch `feat/subject-illustrations`.
2. CI reported `[warn] CLAUDE.md` / `Code style issues found` — exit code 1.
3. Locally, `npx prettier --check CLAUDE.md` passed. File was LF, valid UTF-8, no BOM.
4. `gh run rerun --failed` ran a new job — **same failure**. (Rerun re-uses the checkout.)
5. Discovery: CI checks against `refs/remotes/pull/797/merge` (the synthetic merge commit),
   not the branch HEAD.
6. `main` had diverged: 10 new commits merged while the branch was open, and one of those
   commits had added an unstable list item in `CLAUDE.md` (backtick paths near printWidth).
7. `git show origin/main:CLAUDE.md | npx prettier --check --stdin-filepath CLAUDE.md` → **FAIL**.

## Idempotency Loop Detail

After `git rebase origin/main`, `CLAUDE.md` inherited the unstable content from `main`.

```
- [x] **Cụm 6 khoá…** — chuỗi `pyai`…
      `prerequisites` trỏ khoá trước. File khoá: `packages/subject-programming/courses/
    {pyai,mathai,mlds,cv1,cv2,llmagent}.ts`, nội dung bài: `packages/subject-programming/
    lessons/`.
```

Prettier wanted indent 4 → write gave indent 2 → check wanted indent 0 → endless loop.

**`diff` after `--write`:**
```
481,482c481,482
<   {pyai,...}.ts`, …  (2-space indent after write)
---
> {pyai,...}.ts`, …    (0-space — what Prettier wanted NEXT pass)
```

## Fix Applied

Collapsed the continuation so no backtick path broke across a line:

```python
old = (
    '  {pyai,mathai,mlds,cv1,cv2,llmagent}.ts`, n\u1ed9i dung b\u00e0i: '
    '`packages/subject-programming/\n'
    '  lessons/`. \u0110\u1eb7c t\u1ea3 khung: '
    '`docs/specs/2026-09-01-cum-6-khoa-ai-engineer.md` + \u0111\u1eb7c t\u1ea3 n\u1ed9i'
)
new = (
    '  {pyai,mathai,mlds,cv1,cv2,llmagent}.ts`, n\u1ed9i dung b\u00e0i: '
    '`packages/subject-programming/lessons/`. \u0110\u1eb7c t\u1ea3 khung:\n'
    '  `docs/specs/2026-09-01-cum-6-khoa-ai-engineer.md` + \u0111\u1eb7c t\u1ea3 n\u1ed9i dung'
    ' ri\u00eang t\u1eebng kho\u00e1 c\u00f9ng\n  th\u01b0 m\u1ee5c `docs/specs/`.'
)
```

After replacement: `npx prettier --write CLAUDE.md` → `(unchanged)`, `--check` → exit 0.

## Timeline

| Step | Outcome |
|------|---------|
| Initial CI run | FAIL: `CLAUDE.md` (Prettier) |
| `gh run rerun --failed` | FAIL: same (re-uses old checkout) |
| push empty commit to force new run | FAIL: same root cause (main still dirty) |
| `git rebase origin/main` | surfaced idempotency loop in CLAUDE.md |
| Rewrite unstable paragraph, push | ✅ 13/13 checks green, merged |

## Key Lessons

1. **Check if main itself is dirty** before blaming your branch:
   `git show origin/main:<file> | npx prettier --check --stdin-filepath <file>`
2. **`gh run rerun` ≠ new checkout.** Use it only for infrastructure flakes, not for
   code-content failures.
3. **Prettier idempotency** must be verified with `--write` (must say `unchanged`) AND
   `--check` (must exit 0), not just one of them.
4. **Empty commit trick** creates a new run but doesn't fix the merge-preview base if
   `main` is the dirty party. Rebase is the correct action.
