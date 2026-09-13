---
name: taste-skill
description: "Use when building landing pages/portfolios. Anti-slop rules."
version: 1.0.0
author: "Leonxlnx, Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [design, frontend, anti-slop, landing-page, portfolio]
    related_skills: [frontend-design, redesign-skill, claude-design]
---

> Nguồn: vendored từ https://github.com/Leonxlnx/taste-skill (skills/taste-skill/SKILL.md, MIT license, ~17.6k sao GitHub), giới thiệu qua bài viết https://www.donniechu.com/posts/taste-skill-anti-slop-frontend-ai .
> Dùng cho: landing page, portfolio, redesign marketing site. KHÔNG dùng cho: dashboard, data table dày đặc, wizard nhiều bước, code editor, native mobile, realtime collab UI (xem mục "OUT OF SCOPE" bên dưới).
> Mỗi rule đều **contextual** — không tự động áp dụng mù quáng. Đọc brief trước, chỉ lấy phần phù hợp.
>
> Kỹ năng này **bổ sung** cho `frontend-design` (đã có sẵn trong Hermes): `frontend-design` cho tư duy thiết kế tổng thể (process, self-critique, viết copy), còn `taste-skill` cho **danh sách quy tắc/ban cụ thể + checklist máy móc** để tránh các "AI tells" (font Inter mặc định, gradient tím AI, 3 card đều nhau, em-dash, eyebrow lạm dụng, v.v.). Dùng cả hai cùng lúc khi build/redesign frontend. Nếu đang NÂNG CẤP một site/app đã tồn tại (không phải xây mới), dùng skill `redesign-skill` thay vì skill này.

# tasteskill: Anti-Slop Frontend Skill

See the full vendored ruleset in `references/full-rules.md` (13 sections: brief inference, 3 dials, design-system map, architecture defaults, bias-correction directives, motion patterns, a11y guardrails, AI-tell bans, redesign protocol, and a mandatory pre-flight checklist). ALWAYS load that file before doing frontend design work under this skill — do not rely on this summary alone.

## Quick summary

1. **Read the brief first** (page kind, vibe words, audience, brand assets, quiet constraints), state a one-line "Design Read", then set three dials: `DESIGN_VARIANCE` (1 symmetry → 10 chaos), `MOTION_INTENSITY` (1 static → 10 cinematic), `VISUAL_DENSITY` (1 airy → 10 cockpit). Baseline `8/6/4`, adjust to the brief.
2. **Pick a real design system when the brief calls for one** (Fluent, Material, Carbon, Polaris, Atlaskit, Primer, GOV.UK, USWDS, Radix, shadcn) — don't hand-roll CSS that a real package already solves.
3. **Avoid AI-slop defaults**: Inter font, AI-purple gradients, centered hero + 3 equal feature cards, beige+brass+espresso "premium" palette, generic glassmorphism, infinite micro-animations, em-dashes (banned completely), eyebrows on every section, Jane Doe names / Acme brand names / filler verbs ("Elevate", "Seamless", "Unleash").
4. **Hard layout rules**: hero fits initial viewport (≤ 2-line headline, ≤ 20-word subtext, CTA visible without scroll), nav on one line ≤ 80px tall, no 3+ consecutive zigzag sections, max 1 eyebrow per 3 sections, no duplicate-intent CTAs, real images (gen-tool → picsum seed → explicit placeholder, never div-based fake screenshots).
5. **Before shipping, run the full Pre-Flight Check** (Section 14 in the reference file) — zero em-dashes, color/shape consistency locks, contrast checks, copy self-audit, reduced-motion support, dark mode tested. If a checkbox can't be honestly ticked, the page is not done.

This skill is NOT for dashboards, dense data tables, multi-step wizards, code editors, native mobile, or realtime collab UI — say so explicitly and point to the right tool (Fluent/Carbon/Atlaskit/Polaris, TanStack Table, etc.) if the brief is one of those.
