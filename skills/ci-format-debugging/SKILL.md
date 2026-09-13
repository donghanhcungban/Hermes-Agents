---
name: ci-format-debugging
description: "Use when a formatter CI check fails locally-passing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [CI, Prettier, GitHub-Actions, formatting, lint, debugging]
    related_skills: [github-pr-workflow, systematic-debugging]
---

# CI Formatter Debugging

Use this skill whenever a formatter or linter check (Prettier, ESLint, Black, Ruff…) fails in
CI but passes locally. Two traps account for the majority of these cases.

See `references/prettier-merge-preview-trap.md` for detailed recipes and a worked example.

## Trap 1 — The Merge-Preview Trap (most common)

**What happens:** GitHub Actions runs PR checks against
`refs/remotes/pull/NNN/merge` — a **synthetic merge commit** of your PR branch merged into the
current HEAD of `main`. If `main` contains any file that itself fails the formatter, CI
reports the error on your PR even though your branch is clean.

**Symptoms:**
- Prettier/ESLint fails on a file you never touched
- `npx prettier --check <file>` passes locally
- `gh run rerun --failed` re-fails without any code change

**Diagnosis:**
```bash
git fetch origin main
git show origin/main:<file> | npx prettier --check --stdin-filepath <file>
```
If this fails → the source of dirt is `main`, not your PR.

**Fix:**
```bash
git rebase origin/main           # rebase so merge preview uses clean base
npx prettier --write .           # fix anything newly introduced
npx prettier --check .           # verify (if still fails see Trap 2)
git add <files> && git commit -m "fix(format): pass Prettier after rebase"
git push --force-with-lease origin <branch>
```

> ⚠️ **`gh run rerun --failed` does NOT re-checkout code.** New job IDs, same old source
> checkout. Only a **new commit push** triggers a fresh checkout. Never rely on rerun alone.

---

## Trap 2 — Prettier Markdown Idempotency Loop

**What happens:** `npx prettier --write FILE.md` returns 0, but `npx prettier --check FILE.md`
still fails — endlessly.

**Root cause:** Prettier's Markdown list-item continuation indent is tied to list-marker
width. Backtick code spans near `printWidth` cause indent to alternate each pass
(6 → 4 → 2 → 0 spaces…) without stabilising.

**Diagnosis:**
```bash
npx prettier FILE.md > /tmp/formatted.md
diff FILE.md /tmp/formatted.md   # shows exact unstable lines
```

**Fix:** Rewrite the unstable list item so no backtick span crosses a line boundary.
Collapse continuation lines until `--write` says `(unchanged)` AND `--check` exits 0.

```python
# Targeted in-place replacement (get exact `old` from diff output)
data = open('FILE.md', 'r', encoding='utf-8').read()
old = '    unstable-indented `backtick/path` continuation'
new = '  collapsed `backtick/path` on single line'
open('FILE.md', 'w', encoding='utf-8', newline='').write(data.replace(old, new, 1))
# newline='' preserves LF on Windows
```

Idempotency check:
```bash
npx prettier --write FILE.md   # MUST print "(unchanged)"
npx prettier --check FILE.md   # MUST exit 0
```

---

## Diagnostic Decision Tree

```
Formatter fails in CI but passes locally
├── File you never touched?
│   └── git show origin/main:<file> | npx prettier --check --stdin-filepath <file>
│       ├── FAIL → Trap 1: rebase + format + push
│       └── PASS → check .prettierignore / version mismatch
└── prettier --write loops (write → check → still fail)?
    └── Trap 2: rewrite unstable Markdown list item
```

## Quick Checklist

```bash
# 1. Which file?
gh run view <RUN_ID> --log-failed | grep 'warn\|error'

# 2. Dirty on main? (Trap 1)
git show origin/main:<file> | npx prettier --check --stdin-filepath <file>

# 3. Version match?
npx prettier --version && grep '"prettier"' package-lock.json | head -3

# 4. Idempotent? (Trap 2)
npx prettier --write <file> && npx prettier --check <file>

# 5. Always push a NEW commit after fixing
git add <file> && git commit -m "fix(format): resolve Prettier CI failure"
git push --force-with-lease
```
