#!/usr/bin/env python3
"""Scan a subject-* lesson file and report id mismatches.

Usage (inside execute_code or terminal):
  python check_lesson_ids.py packages/subject-biology/lessons/sinh12c1.ts

Detects cases where the id string (e.g. 'sinh12-c1-b10') does not match
the actual chapterNumber / lessonNumber declared in the same lesson object.
"""
import re
import sys

def check_ids(path: str) -> list[tuple[str, str]]:
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    id_pat   = re.compile(r"id: '([a-z]+\d+-c(\d+)-b(\d+))'")
    cn_pat   = re.compile(r"chapterNumber: (\d+)")
    ln_pat   = re.compile(r"lessonNumber: (\d+)")

    ids = list(id_pat.finditer(raw))
    cns = list(cn_pat.finditer(raw))
    lns = list(ln_pat.finditer(raw))

    mismatches = []
    for i, m in enumerate(ids):
        full_id = m.group(1)
        id_c, id_b = int(m.group(2)), int(m.group(3))
        actual_c = int(cns[i].group(1)) if i < len(cns) else -1
        actual_b = int(lns[i].group(1)) if i < len(lns) else -1
        if id_c != actual_c or id_b != actual_b:
            correct = full_id.rsplit("-c", 1)[0] + f"-c{actual_c}-b{actual_b}"
            mismatches.append((full_id, correct))
    return mismatches


def fix_ids(path: str, mismatches: list[tuple[str, str]]) -> int:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    for old, new in mismatches:
        raw = raw.replace(f"id: '{old}'", f"id: '{new}'")
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw)
    return len(mismatches)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: check_lesson_ids.py <path-to-ts-file> [--fix]")
        sys.exit(1)
    path = sys.argv[1]
    fix  = "--fix" in sys.argv
    mismatches = check_ids(path)
    if not mismatches:
        print(f"{path}: OK — no id mismatches found")
    else:
        for old, new in mismatches:
            print(f"  MISMATCH: {old!r} should be {new!r}")
        if fix:
            n = fix_ids(path, mismatches)
            print(f"Fixed {n} mismatches in-place.")
        else:
            print("Re-run with --fix to patch automatically.")
            sys.exit(1)
