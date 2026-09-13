---
name: restoring-deleted-code-from-git-history
description: "Restore deleted code/packages intact from git history."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, git-history, monorepo, recovery, restore, typescript, refactor]
    related_skills: [systematic-debugging, github]
---

# Restoring Deleted Code From Git History

## When to use

A file, module, or whole package existed at some point, got deleted in a refactor or cleanup
commit, and is needed again — exactly as it was, not hand-reconstructed from memory or guesswork.
Common triggers: "we used to have an engine/package for X", "this was removed in a restructure",
"bring back the old implementation of Y".

**Never hand-retype or approximate deleted code from memory/context.** If it once existed in the
repo, it exists in git history — pull the literal bytes back out.

## The core technique

```bash
# 1. Find the commit that deleted the path
git log --diff-filter=D --oneline -- path/to/deleted-thing
# => e.g. 011a567 refactor(arch): split api/ into subject packages (#627)

# 2. The content you want lived in the PARENT of that deletion commit.
#    Restore it straight into the working tree (this also stages it):
git checkout <deletion_commit>^ -- path/to/deleted-thing
# equivalently: git checkout <parent_commit_sha> -- path/to/deleted-thing

# 3. Verify what came back matches expectations
ls path/to/deleted-thing          # file count sane?
cat path/to/deleted-thing/package.json  # composite package? tsconfig present?
```

This restores the EXACT last-known-good version, not a re-derived approximation — the whole
point of going to history instead of rewriting from scratch.

## Caveats and pitfalls

- **Renamed-then-deleted paths**: `--diff-filter=D` on the current/expected path may find
  nothing if the path was moved before deletion. Fall back to
  `git log --follow --oneline -- <path>` to find the real history, or loosen the match with
  `git log --diff-filter=D --oneline -- '*<basename>*'`.
- **Multiple deletions of the same basename**: don't trust the first hit blindly — diff the
  restored content against a second known-good reference point before building on it:
  `git show <parent_commit_sha>:path/to/file | head`.
- **Re-wire into the build, don't just restore the files.** In monorepos the deletion commit
  usually ALSO dropped the entry from a workspace/tsconfig "references"/"projects" list (e.g.
  `tsconfig.packages.json`, `pnpm-workspace.yaml`, a root `package.json` `workspaces` array).
  Restoring the directory alone leaves it silently excluded from build/test/typecheck. Find and
  restore that registration too, in the same change.
- **Restoring old code doesn't mean it's still correct for the current codebase.** Run its own
  test suite and a scoped typecheck (`tsc -b path/to/package`) immediately after restoring,
  BEFORE building any new work on top of it.
- **Don't trust a whole-workspace `tsc -b` / lint / test run to tell you whether your restore is
  clean** in a large/aging monorepo — there can be hundreds of pre-existing unrelated errors in
  other packages (build-order, stale deps, drift). Scope the check to the restored package path
  first. If a whole-workspace run shows failures and you're not sure they're pre-existing, prove
  it: `git stash` (or check out the commit before your restore), re-run the exact same
  whole-workspace command, and compare error counts before/after. Report the delta, not the raw
  count — claiming "0 errors" when the baseline already had 400 is misleading even if none of
  them are yours.

## Worked example (subject-matter agnostic)

Asked to bring back a deleted `packages/core-grading` engine so new content packages could depend
on it again:

```bash
git log --diff-filter=D --oneline -- packages/core-grading
# 011a567 refactor(arch): split api/ by subject + core-domains (#627)

# the commit that deleted it stripped package.json/tsconfig.json too (pure delete, not a move) —
# confirmed by diffing 011a567 itself against its parent and seeing no rename entries for the path

git checkout 011a567^ -- packages/core-grading
ls packages/core-grading   # package.json, tsconfig.json, source + test files all present

# re-register in the workspace project list it had been dropped from
# (tsconfig.packages.json "references" array)

npx vitest run packages/core-grading     # scoped test run: all pre-existing tests still pass
npx tsc -b packages/core-grading         # scoped typecheck: clean

# whole-workspace tsc -b surfaced ~400 errors in unrelated packages — proved pre-existing by
# git stash + re-running the same command on baseline before concluding the restore was clean
```

## Verification checklist

- [ ] Restored content matches the parent-of-deletion commit exactly (not retyped)
- [ ] Workspace/build registration (tsconfig references, workspaces array, etc.) restored too
- [ ] Scoped test suite for the restored package passes
- [ ] Scoped typecheck/build for the restored package is clean
- [ ] Any whole-workspace failures are proven pre-existing (baseline comparison), not assumed
