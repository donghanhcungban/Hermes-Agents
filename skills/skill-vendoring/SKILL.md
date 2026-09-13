---
name: skill-vendoring
description: Vendor external MIT skills into Hermes with full compliance.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, vendoring, licensing, mit, import]
    related_skills: [hermes-agent-skill-authoring, requesting-code-review]
---

# Skill Vendoring

Procedure for importing external SKILL.md files from third-party GitHub repositories
into the local Hermes skill library. Covers license validation, content cleanup,
provenance documentation, and installer integration.

Does NOT cover writing original skills from scratch — see `hermes-agent-skill-authoring`.

## When to Use

- User asks to research and import skills from GitHub repos (e.g. `addyosmani/agent-skills`).
- Adding skills from a third-party repo to a plugin installer (`install.py`).
- Auditing whether an existing vendored skill is compliant.

**Don't use for:** skills the user or agent wrote from scratch; those go through `hermes-agent-skill-authoring`.

## Prerequisites

- Target repository must have a compatible open-source license (MIT, Apache-2.0, BSD).
- Confirm license file exists in the upstream repo before fetching any content.

## Procedure

### Step 1 — License check

1. Fetch the upstream `LICENSE` file via `web_extract` or `terminal("curl -sL ...")` — not just the repo description.
2. Confirm it is MIT (or another permissive license that allows redistribution).
3. Record the exact copyright line (year + holder name) — you will need it for provenance.

**Completion criterion:** you can quote the copyright holder and year without guessing.

### Step 2 — Fetch and inspect SKILL.md

```bash
curl -sL https://raw.githubusercontent.com/<owner>/<repo>/main/skills/<name>/SKILL.md
```

Check immediately:
- Does the frontmatter `name:` match the **directory name** the skill will live in?  
  If not, fix `name:` to match — mismatch causes the skill to be identified by the wrong name at runtime. This is the #1 vendoring bug.
- Are there `references/` or template files referenced in the body? Fetch those too.

### Step 3 — Content cleanup

- Strip trailing whitespace from every line (`git diff --check` will catch survivors).
- Remove or adapt any upstream-repo-relative paths that won't resolve locally (e.g., `../../references/shared.md`).
- If shared references were copied into per-skill `references/` directories, update the paths to be skill-local (e.g., `references/shared.md`).

**Completion criterion:** `git diff --check` reports zero trailing-whitespace violations.

### Step 4 — Write provenance (`VENDORED-SKILLS.md`)

Create `skills/VENDORED-SKILLS.md` (or add a section) with:

```markdown
## <owner>/<repo>
Source: https://github.com/<owner>/<repo> — MIT, Copyright (c) <year> <Holder>.

Skills installed:
- `<skill-name>`

Install path: `$HERMES_HOME/skills/<skill-name>/` (flat, no category subdirectory)

### MIT License Text

\`\`\`
MIT License

Copyright (c) <year> <Holder>

Permission is hereby granted, free of charge, to any person obtaining a copy
...[full standard MIT text]...
\`\`\`
```

**Key rules:**
- Include the **full MIT permission notice**, not just the copyright line. Copyright line alone does not satisfy the "include this notice in all copies" clause.
- Document the **flat install path** (`$HERMES_HOME/skills/<name>/`), NOT category subdirectories — the installer copies skills flat regardless of how you organise them locally.

**Completion criterion:** Every vendored upstream has its own section with full MIT text and correct install path.

### Step 5 — Integration in `install_bundled_skills()`

When bundling skills into a plugin installer (`install.py`), use this pattern:

```python
def install_bundled_skills(hermes_dir: Path) -> list[str]:
    """Sync packaged skills without modifying unrelated user-created skills."""
    source_root = PACKAGE_DIR / "skills"
    destination_root = hermes_dir / "skills"
    if not source_root.is_dir():
        return []

    installed: list[str] = []
    for source_skill in sorted(source_root.iterdir()):
        if not source_skill.is_dir() or not (source_skill / "SKILL.md").is_file():
            continue
        destination_skill = destination_root / source_skill.name
        destination_root.mkdir(parents=True, exist_ok=True)
        # Order matters on Windows — check symlink BEFORE is_dir():
        if destination_skill.is_symlink():
            destination_skill.unlink()
        elif destination_skill.is_dir():
            shutil.rmtree(destination_skill)
        elif destination_skill.exists():
            destination_skill.unlink()
        shutil.copytree(source_skill, destination_skill)
        installed.append(source_skill.name)
    return installed
```

**Completion criterion:** repeated invocation replaces same-name bundles without touching other skills.

### Step 6 — Regression tests

Add at minimum:

1. `test_installs_bundle_and_preserves_user_skills` — happy path, user skill survives.
2. `test_real_package_bundle_contains_expected_skills` — count == expected, every SKILL.md has `---` frontmatter.
3. `test_pipeline_design_frontmatter_name_matches_dir` — for any skill whose upstream `name:` was corrected.
4. `test_replaces_file_occupying_skill_slot` — regular file at dest is unlinked cleanly.
5. `test_replaces_symlink_occupying_skill_slot` — symlink at dest is unlinked before copytree.

**Completion criterion:** `python -m unittest discover -s tests -p 'test_*.py' -q` exits 0.

## Pitfalls

1. **`name:` ≠ directory name.** The upstream repo may name a skill `solution-design` but place it in a `pipeline-design/` directory (or vice versa). The directory name wins — fix the frontmatter.

2. **MIT copyright line ≠ MIT permission notice.** Writing only `Copyright (c) 2025 Addy Osmani` in provenance does NOT satisfy the license. You must include the full boilerplate "Permission is hereby granted...". The reviewer will catch this.

3. **Provenance documents wrong install path.** If you organise skills locally under `software-development/<name>/` but the installer copies them to `$HERMES_HOME/skills/<name>/` (flat), the VENDORED-SKILLS.md must document the flat path.

4. **`shutil.rmtree()` on a symlink on Windows/Python 3.11 raises `OSError`.** Always check `is_symlink()` and call `unlink()` before trying `rmtree()`. The safe order is: symlink → unlink; directory → rmtree; plain file → unlink.

5. **Shared reference files referenced with `../../references/` paths.** When copying a skill that originally loaded shared files from a repo-level `references/` dir, copy those files into the skill's own `references/` and update the relative paths.

6. **Trailing whitespace from upstream files.** Run `git diff --check` before committing. Four common offenders in Markdown: sentence-ending spaces, template placeholder lines, code-block preamble lines.

7. **Vendoring skills that modify `solution-design` canonical path.** If a prior `solution-design` skill is already installed, a new `pipeline-design` skill with `name: solution-design` in frontmatter will not replace it — the two coexist with mismatched identities.

## Reference Files

- `references/multi-repo-pr-pattern.md` — git worktree pattern for pushing the same change to multiple repos simultaneously.
- `references/skill-category-management.md` — how to move skills between categories without losing support files.

## Verification

- [ ] License confirmed permissive; copyright year and holder recorded.
- [ ] Frontmatter `name:` matches directory name for every vendored skill.
- [ ] `git diff --check` zero violations.
- [ ] `VENDORED-SKILLS.md` has full MIT permission notice for every upstream (not just copyright line).
- [ ] Install path documented as flat `$HERMES_HOME/skills/<name>/`.
- [ ] `install_bundled_skills()` handles symlink/file/dir collisions in the correct order.
- [ ] All regression tests pass including the real-bundle count assertion.
