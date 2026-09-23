---
name: grill-tab
description: "Dùng plugin grill-tab để làm rõ intent trước khi chạy agent."
version: 1.0.0
author: Hermes Agents Repo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, plugin, composer, briefing, ux]
    related_skills: [antigravity-oauth-bridge, hermes-provider-management]
---

# Grill Tab — Plugin Hỏi Rõ Intent Trước Khi Gửi

Plugin `grill-tab` (tác giả: thanhan-a17, MIT) được vendor vào repo này tại `plugins/grill-tab/`.
Nó chặn Tab trong composer Hermes Desktop, hỏi lần lượt từng câu quyết định quan trọng nhất,
rồi tổng hợp thành **execution brief** đặt vào composer — bạn tự nhấn Enter khi hài lòng.

## Cài đặt

Plugin được `install.py` cài tự động vào `$HERMES_HOME`. Sau khi `python install.py`:

```yaml
# config.yaml — chọn model auxiliary nhanh/rẻ cho grill-tab
auxiliary:
  grill_tab:
    provider: antigravity       # hoặc openrouter / anthropic
    model: gemini-3-flash-agent
    reasoning_effort: minimal
    timeout: 15
```

Hoặc chọn qua CLI: `hermes model` → *Configure auxiliary models* → **Grill Tab**

## Cách dùng

| Trạng thái | Tab | Enter | Esc | Backspace (trống) |
|---|---|---|---|---|
| Composer có text | Bắt đầu grill | Gửi bình thường | — | — |
| Đang hỏi | Commit câu trả lời (rỗng = chấp nhận gợi ý) | Viết brief → composer | Bỏ qua câu / Esc lần 2 thoát | Quay lại rung trước |
| Hết câu | Hỏi thêm 1 câu | Viết brief → composer | Thoát, khôi phục draft | — |

Click vào rung đã trả lời để sửa tại chỗ (Enter/blur lưu, Esc huỷ).

Palette: **Grill this draft** | Keybind: `⌘⇧G`

## Kiến trúc nội tại

```
plugins/grill-tab/
├── __init__.py             Đăng ký auxiliary task `grill_tab`
├── plugin.yaml             Manifest Hermes ≥ 0.20
├── dashboard/
│   ├── manifest.json       Route: /api/plugins/grill-tab/{interrogate,brief,health}
│   ├── plugin_api.py       FastAPI router, failure-safe
│   └── grill_engine.py     Engine thuần Python (28KB) — prompts, parse, fallback
├── desktop/
│   ├── plugin.js           ESM plugin React toàn bộ UI (35KB)
│   └── grill-core.mjs      Pure reducer/state được tách ra để test
├── docs/SPEC.md            Đặc tả thiết kế
├── docs/CONTRACT.md        REST contract đóng băng v1
└── tests/                  pytest + node --test
```

### Engine logic chính (`grill_engine.py`)

**Interrogate system prompt** cốt lõi:
- *Decision tree*: hỏi 1 quyết định từ frontier mỗi rung
- *Skip-if-same-plan*: nếu mọi câu trả lời dẫn đến cùng kế hoạch → không hỏi
- *Deferral*: "you decide" / "your call" → tự động accept recommendation, set `settled_from_recommendation=true`
- *Category priority*: goal → deliverable → scope → verification → architecture
- *≤18 words*, viết bằng ngôn ngữ của user

**Brief system prompt** cốt lõi:
- **Fidelity-first**: không mở rộng scope, không thêm deliverable ngoài yêu cầu
- Assumptions = lựa chọn nhỏ nhất, ít tham vọng nhất
- Luôn có `## Directive: Work autonomously...` ở cuối

**JSON parsing 3 lớp**: direct → markdown fence → raw_decode scan, + `_strip_thinking()` cho reasoning model.

**requestSerial pattern** tránh race condition Tab nhanh hơn model response.

## Chạy tests

```bash
# Python tests (yêu cầu fastapi, pydantic trong venv)
pip install fastapi pydantic httpx pytest
python -m pytest plugins/grill-tab/tests/ -q

# Desktop core tests (Node.js ≥ 22)
cd plugins/grill-tab
node --test tests/desktop/
```

## Cập nhật upstream

```bash
# Xem diff với upstream
git diff HEAD -- plugins/grill-tab/

# Vendor lại từ upstream (chỉ khi có breaking change)
# Tham khảo skill skill-vendoring để làm đúng quy trình
```

## Pitfalls

- Plugin cần **Hermes Desktop** (local backend). Remote backend: copy `desktop/plugin.js` vào `~/.hermes/desktop-plugins/grill-tab/plugin.js` trên máy chạy Hermes Desktop.
- `grill-core.mjs` là file được extract từ `plugin.js` (giữa `@core-start` / `@core-end`) để test pure logic — không import trực tiếp.
- Model auxiliary không set → fallback về main model (chậm hơn nhiều, mất mục đích "rung 1–3s").
