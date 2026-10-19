---
name: stored-knowledge-base
description: "Dùng khi chọn repo/tool/skill ngoài; tra kho stored."
version: 1.0.0
author: liend
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [stored, catalog, research, adopt-from-outside, due-diligence]
    related_skills: [deep-research, web-research, security-and-hardening, source-driven-development]
---

# Tra cứu kho `stored`

Kho `seeker19110/stored` (public) là hồ sơ và đánh giá hơn 500 dự án AI/coding/agentic/design/UI-UX, chia 23 chuyên mục. Kho **không chứa code hay skill để dùng**, chỉ chứa đánh giá. Skill này chỉ cách tra cứu, không sao chép nội dung vào Hermes.

## Khi nào dùng

- Trước khi đề xuất hoặc cài một repo/tool/skill/MCP bên ngoài: xem kho đã có hồ sơ chưa, license, rủi ro, lựa chọn thay thế.
- Khi cần so sánh ứng viên cùng loại (framework agent, memory, eval, guardrails, design system...).
- Khi người dùng hỏi "kho của tôi có đánh giá X chưa".

## Cách tra

```bash
# lọc catalog (tự tải và cache 7 ngày tại $HERMES_HOME/cache/stored-projects.json)
python -I <skill_dir>/scripts/stored_query.py --q memory
python -I <skill_dir>/scripts/stored_query.py --category security --license Apache
python -I <skill_dir>/scripts/stored_query.py --section 12 --open-source --min-stars 1000
python -I <skill_dir>/scripts/stored_query.py --categories
python -I <skill_dir>/scripts/stored_query.py --refresh --q hermes
```

Sau khi chọn ứng viên, đọc chương `NN-.../README.md` tương ứng (cột `section`) để lấy đánh giá, bằng `web_extract` với
`https://raw.githubusercontent.com/seeker19110/stored/main/NN-<tên-chuyên-mục>/README.md`.
Tên thư mục: xem bảng mục lục ở README gốc của kho.

## Quy tắc khi dùng kết quả

1. Catalog là ảnh chụp ngày `meta.snapshot_date`; số sao là ước lượng. Nói rõ ngày khi trích số.
2. Mục ghi **(chưa xác minh)** không coi là sự thật; kiểm lại nguồn gốc trước khi tích hợp.
3. Kiểm license trước khi nhúng (AGPL, Elastic-2.0, CC BY-NC, không có LICENSE là cờ vàng).
4. Repo ngoài có hook/install script: đọc cổng đang chạy (settings, hook, CI, script), không tin README. Cân nhắc quét bằng agent-scan/SkillSpector (kho mục 12).
5. Chương 23 ghi bài học từ repo của chủ kho, gồm gợi ý tích hợp cho Hermes-Agents (§7b).
6. Kho chỉ đọc: không đẩy gì lên `stored` nếu người dùng chưa yêu cầu. Quy trình thêm link mới nằm ở `WORKFLOW.md` của kho (PR, bật auto-merge ngay khi tạo PR).
