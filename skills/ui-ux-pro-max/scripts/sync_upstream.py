#!/usr/bin/env python3
"""Pin and mirror the runtime subset of nextlevelbuilder/ui-ux-pro-max-skill.

No third-party Python dependencies. Each downloaded file is verified against its
Git blob SHA from upstream commit dcc40ff5133ef78276117db0cc34e7b83cc8aeba.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

UPSTREAM_REPO = "nextlevelbuilder/ui-ux-pro-max-skill"
UPSTREAM_COMMIT = "dcc40ff5133ef78276117db0cc34e7b83cc8aeba"
MANIFEST = [
  [
    ".claude/skills/ui-ux-pro-max/references/pro-rules.md",
    "b2ce233287e37ec9ca13476c4014b922e9d5a0e9",
    10909
  ],
  [
    ".claude/skills/ui-ux-pro-max/references/quick-reference.md",
    "7acc7e7540ca6981d878a90aae4455c1638e2385",
    24526
  ],
  [
    "src/ui-ux-pro-max/data/app-interface.csv",
    "95e328c807a23be02c9c32c736d0fa19109c6076",
    11046
  ],
  [
    "src/ui-ux-pro-max/data/charts.csv",
    "c6f4f875fd5b34379f24dbb541539492366a1058",
    23365
  ],
  [
    "src/ui-ux-pro-max/data/colors.csv",
    "5d2bf7389105f8a824b504b57cc93c00dc1d7e0a",
    37940
  ],
  [
    "src/ui-ux-pro-max/data/google-fonts.csv",
    "d7f87e3e0159b1caba083b9954793d9852256aa0",
    747241
  ],
  [
    "src/ui-ux-pro-max/data/icons.csv",
    "cfc3f1eccd7e5aee15d8d70f86d8fa17ba737958",
    57945
  ],
  [
    "src/ui-ux-pro-max/data/landing.csv",
    "34858160aa2789c49dca274d48bb116d51dd3f0a",
    25449
  ],
  [
    "src/ui-ux-pro-max/data/motion.csv",
    "8e0ca9ceb0e4cd4832aee60ac74713e1e1830de8",
    14679
  ],
  [
    "src/ui-ux-pro-max/data/products.csv",
    "9f40f1d1f9743c4a81603076dfbfd115bbb55246",
    75623
  ],
  [
    "src/ui-ux-pro-max/data/react-performance.csv",
    "425a8e76c6b3bae40e8c633ffbf7ad6222c9f73a",
    15080
  ],
  [
    "src/ui-ux-pro-max/data/stacks/angular.csv",
    "5a1878dbee2b3c55c6468cbb18699b84d1a8c4d2",
    19863
  ],
  [
    "src/ui-ux-pro-max/data/stacks/astro.csv",
    "1fd2492420b20a0b311295ab883597fadb8245a6",
    14591
  ],
  [
    "src/ui-ux-pro-max/data/stacks/avalonia.csv",
    "c67f4117105865587eda9020c57d8c209f3a929a",
    27327
  ],
  [
    "src/ui-ux-pro-max/data/stacks/flutter.csv",
    "731805c4076bd9f2755ca4bd7def5be6f6df7e9c",
    14192
  ],
  [
    "src/ui-ux-pro-max/data/stacks/html-tailwind.csv",
    "9089eb0fc821ff0c8d135f8ee503be345e8fcb84",
    16551
  ],
  [
    "src/ui-ux-pro-max/data/stacks/javafx.csv",
    "744bd80f437f12bfb5bb9c84630a58022604675a",
    33577
  ],
  [
    "src/ui-ux-pro-max/data/stacks/jetpack-compose.csv",
    "8daa0b8f9a2ca3f0f1711664d9d677cd1c38dd9e",
    12295
  ],
  [
    "src/ui-ux-pro-max/data/stacks/laravel.csv",
    "ed11b0fba457e02857f996d1542fb0b8e1271756",
    20163
  ],
  [
    "src/ui-ux-pro-max/data/stacks/nextjs.csv",
    "acdaf097dff26ba0d3b22ab4544bf6169c87afd4",
    18687
  ],
  [
    "src/ui-ux-pro-max/data/stacks/nuxt-ui.csv",
    "e2aaeca45faa8b987bf94010162b14d458811dde",
    28700
  ],
  [
    "src/ui-ux-pro-max/data/stacks/nuxtjs.csv",
    "ceab9cf3358d2788af0bd7dc14cb3fab769740d0",
    23014
  ],
  [
    "src/ui-ux-pro-max/data/stacks/react-native.csv",
    "a5aea45dc1d0341b11ee42076a86db842d4d2a19",
    14049
  ],
  [
    "src/ui-ux-pro-max/data/stacks/react.csv",
    "fe8f001e695a978733449e04e99d7135af0f1bf3",
    21166
  ],
  [
    "src/ui-ux-pro-max/data/stacks/shadcn.csv",
    "0e8bedf3084e7a40d6310bcd3011c437efcb1700",
    23184
  ],
  [
    "src/ui-ux-pro-max/data/stacks/svelte.csv",
    "51684fe70448e15333cd16207db7da8aea0508e6",
    15078
  ],
  [
    "src/ui-ux-pro-max/data/stacks/swiftui.csv",
    "ea9b95e8922e663b2adf27a7346e2c2f44c7a215",
    15323
  ],
  [
    "src/ui-ux-pro-max/data/stacks/threejs.csv",
    "2e2cefe996c7c0622f58442bea4d11c333c4d616",
    46051
  ],
  [
    "src/ui-ux-pro-max/data/stacks/uno.csv",
    "9cab32326b4ad3a3cf43451a3c24553a41126cc1",
    30091
  ],
  [
    "src/ui-ux-pro-max/data/stacks/uwp.csv",
    "04a84ea092a7657fef11e5daa97982be52dc6f59",
    24692
  ],
  [
    "src/ui-ux-pro-max/data/stacks/vue.csv",
    "83997c515775170f22b638635aae0a67a46dfc87",
    12813
  ],
  [
    "src/ui-ux-pro-max/data/stacks/winui.csv",
    "107ecead11728a83ec0ea10d815a9d1f43a35792",
    27890
  ],
  [
    "src/ui-ux-pro-max/data/stacks/wpf.csv",
    "4e88d6750833a74f85ba487cf2b8f4ff6ebd2f4a",
    24158
  ],
  [
    "src/ui-ux-pro-max/data/styles.csv",
    "d1eb2c216e453005ffa8232ffb94491c183afe3c",
    149478
  ],
  [
    "src/ui-ux-pro-max/data/typography.csv",
    "70d107d107de30150863c965767320ec33ef29ad",
    49997
  ],
  [
    "src/ui-ux-pro-max/data/ui-reasoning.csv",
    "8931d4c809f8e22ddac00ce612ce0c35f34a59b6",
    77360
  ],
  [
    "src/ui-ux-pro-max/data/ux-guidelines.csv",
    "4e7d52b296537a03513b18b2c3f2b946cc802051",
    27516
  ],
  [
    "src/ui-ux-pro-max/scripts/core.py",
    "670fe33070cfe706401da4ff276831257dbf1e25",
    41236
  ],
  [
    "src/ui-ux-pro-max/scripts/design_system.py",
    "1114088ea5886c7e5b8986fb22aef61acecc83ea",
    70937
  ],
  [
    "src/ui-ux-pro-max/scripts/reasoning_contract.py",
    "63652a666b130c249ea1e2954316f1ac8a5a73d5",
    5824
  ],
  [
    "src/ui-ux-pro-max/scripts/search.py",
    "5038aa875a0d39f24dea803a4c73b38f8f56915f",
    9373
  ]
]

SKILL_ROOT = Path(__file__).resolve().parents[1]

def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()

def destination(source_path: str) -> Path:
    if source_path.startswith("src/ui-ux-pro-max/"):
        rel = source_path[len("src/ui-ux-pro-max/"):]
        return SKILL_ROOT / rel
    marker = ".claude/skills/ui-ux-pro-max/"
    if source_path.startswith(marker):
        return SKILL_ROOT / source_path[len(marker):]
    raise ValueError(source_path)

def main() -> int:
    failures = []
    for source_path, expected_sha, expected_size in MANIFEST:
        url = (
            "https://raw.githubusercontent.com/"
            f"{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{source_path}"
        )
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
        except Exception as exc:
            failures.append(f"download {source_path}: {exc}")
            continue

        actual_sha = git_blob_sha(data)
        if actual_sha != expected_sha:
            failures.append(
                f"sha mismatch {source_path}: {actual_sha} != {expected_sha}"
            )
            continue
        if len(data) != expected_size:
            failures.append(
                f"size mismatch {source_path}: {len(data)} != {expected_size}"
            )
            continue

        dst = destination(source_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        print(f"synced {source_path} -> {dst.relative_to(SKILL_ROOT)}")

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        return 1

    print(f"\nOK: synced {len(MANIFEST)} pinned upstream files.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
