# Skill Category Management

Hermes skill categories are **filesystem directories**. Every action that touches
category membership must account for support files.

## Moving a skill to a different category

Use `mv` on the filesystem, not `skill_manage delete + create`.

```bash
# Move a skill (and ALL its support files) from one category to another
mv C:/Users/<user>/AppData/Local/hermes/skills/<old-cat>/<name> \
   C:/Users/<user>/AppData/Local/hermes/skills/<new-cat>/<name>

# Verify it still loads
# skills_list() should show the skill under the new category
```

**Why:** `skill_manage(action='delete')` removes the entire directory tree, including
`references/`, `scripts/`, `assets/`, and `templates/`. Re-creating via `create` only
writes SKILL.md — all support files are permanently lost.

The `create` action only accepts `category` at creation time. There is no `move` action.
`mv` is the only safe way to re-categorise.

## Bulk re-categorisation of many skills

```python
import os, shutil
skills_dir = r"C:\Users\<user>\AppData\Local\hermes\skills"

# Example: move a list of skills to 'engineering' category
for skill_name in ["cad-editor", "ee-ai-toolkit", "mepf-cad-workflows"]:
    src = os.path.join(skills_dir, skill_name)          # currently top-level
    dst = os.path.join(skills_dir, "engineering", skill_name)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.move(src, dst)
        print(f"Moved {skill_name} -> engineering/")
```

## Verifying categories after a move

```python
# skills_list() is the canonical source of truth — trust it over ls
skills = skills_list()  # hermes tool
for s in skills:
    print(s["category"], s["name"])
```

## Pitfall: empty category directories

After moving all skills out of a category, the parent directory remains. Hermes
implicitly hides empty category directories from `skills_list()`, but they take
up space. Remove with:

```bash
rmdir C:/path/to/skills/<empty-category>  # only if truly empty
```
