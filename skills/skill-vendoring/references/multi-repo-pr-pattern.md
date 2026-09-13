# Multi-Repo PR with Git Worktrees

Pattern used when the same change must land in two or more repos simultaneously,
each potentially on a different base branch.

## Setup

```bash
# Repo A: branch off its default branch
git -C /path/to/repo-a fetch origin
git -C /path/to/repo-a worktree add -b feat/my-feature /tmp/repo-a-pr origin/main

# Repo B (fork): branch off fork's current branch
git -C /path/to/repo-b fetch fork
git -C /path/to/repo-b worktree add -b feat/my-feature /tmp/repo-b-pr fork/main
```

## When base branches differ

Apply the commit from the first worktree to the second via cherry-pick instead of
repeating edits:

```bash
# Get the commit SHA from repo A's worktree
SHA=$(git -C /tmp/repo-a-pr rev-parse HEAD)

# Apply it to repo B's worktree (conflicts are normal when states diverge)
git -C /tmp/repo-b-pr cherry-pick $SHA
# Resolve conflicts in /tmp/repo-b-pr, then:
git -C /tmp/repo-b-pr cherry-pick --continue
```

## Push and create PRs

```bash
git -C /tmp/repo-a-pr push -u origin feat/my-feature
gh pr create --repo owner/repo-a --base main --head feat/my-feature --title "..."

git -C /tmp/repo-b-pr push -u fork feat/my-feature
gh pr create --repo fork-owner/repo-b --base main --head feat/my-feature --title "..."
```

## Cleanup

```bash
git -C /path/to/repo-a worktree remove /tmp/repo-a-pr
git -C /path/to/repo-b worktree remove /tmp/repo-b-pr
```

## Key pitfalls

- Confirm `fork` vs `origin` remote name per repo before pushing.
- `git worktree add` with a `-b` flag creates the branch; if it already exists locally,
  drop `-b` and use the branch name directly.
- A fork repo typically has `fork` → your fork and `target`/`origin` → upstream.
  Always run `git remote -v` in the worktree to confirm before pushing.
