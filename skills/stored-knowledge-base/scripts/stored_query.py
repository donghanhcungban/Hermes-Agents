#!/usr/bin/env python3
"""Tra cứu data/projects.json của seeker19110/stored (cache 7 ngày, chỉ stdlib)."""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/seeker19110/stored/main/data/projects.json"
TTL = 7 * 86400


def cache_path():
    home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
    return Path(home) / "cache" / "stored-projects.json"


def load(refresh):
    p = cache_path()
    if refresh or not p.exists() or time.time() - p.stat().st_mtime > TTL:
        try:
            with urllib.request.urlopen(URL, timeout=30) as r:
                raw = r.read()
            json.loads(raw)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        except Exception as e:
            if not p.exists():
                sys.exit(f"Không tải được catalog: {e}")
            print(f"(dùng cache cũ, tải lỗi: {e})", file=sys.stderr)
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", help="từ khoá trong name/repo/notes")
    ap.add_argument("--category")
    ap.add_argument("--license", help="chứa chuỗi này (không phân biệt hoa thường)")
    ap.add_argument("--section", help="số chuyên mục, vd 12")
    ap.add_argument("--open-source", action="store_true")
    ap.add_argument("--min-stars", type=int, default=0)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--categories", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    d = load(a.refresh)
    meta, projects = d.get("meta", {}), d.get("projects", [])
    print(f"# snapshot {meta.get('snapshot_date')} · {len(projects)} dự án")
    if a.categories:
        print("\n".join(meta.get("categories", [])))
        return

    out = []
    for p in projects:
        hay = f"{p.get('name','')} {p.get('repo','')} {p.get('notes','')}".lower()
        if a.q and a.q.lower() not in hay:
            continue
        if a.category and p.get("category") != a.category:
            continue
        if a.license and a.license.lower() not in str(p.get("license") or "").lower():
            continue
        if a.section and p.get("section") != a.section.zfill(2):
            continue
        if a.open_source and not p.get("open_source"):
            continue
        if (p.get("stars") or 0) < a.min_stars:
            continue
        out.append(p)

    out.sort(key=lambda p: -(p.get("stars") or 0))
    for p in out[: a.limit]:
        print(f"- {p['name']} | {p.get('repo') or p.get('url')} | {p['category']} | "
              f"{p.get('license')} | ★{p.get('stars')} | mục {p['section']}\n    {p.get('notes','')}")
    print(f"# {len(out)} kết quả (hiển thị {min(len(out), a.limit)})")


if __name__ == "__main__":
    main()
