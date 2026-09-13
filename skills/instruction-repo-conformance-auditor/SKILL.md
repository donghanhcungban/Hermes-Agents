---
name: instruction-repo-conformance-auditor
description: "Dùng khi tài liệu lệch repo; đối chiếu mọi tuyên bố."
version: 0.1.0
author: liend, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [documentation, conformance, audit, drift]
    related_skills: [evidence-driven-delivery, documentation-and-adrs]
---

# Audit độ khớp giữa hướng dẫn và repo

Skill này kiểm tra AGENTS.md, CLAUDE.md, README, runbook, skill nội bộ và workflow có còn mô tả đúng code hiện tại không. Nó không đánh giá văn phong; nó tìm instruction drift có thể làm agent thao tác sai.

## When to Use

- Sau refactor/move thư mục/đổi script, workflow hoặc branch protection.
- Khi nhiều tài liệu đưa quy tắc mâu thuẫn.
- Trước khi tin một skill nội bộ hoặc runbook cũ.
- Khi onboarding agent mới vào repo lâu năm.

## Procedure

1. **Xác định thứ bậc nguồn thật.** Ghi nguồn thi hành hiện hành, tài liệu tham khảo, tài liệu lưu trữ và code/runtime authority. Hoàn tất khi biết nguồn nào thắng khi mâu thuẫn.
2. **Trích claim.** Thu thập đường dẫn, lệnh, tên job/check, API, schema, permission, model/provider, trạng thái tính năng và invariant từ tài liệu.
3. **Đối chiếu bằng công cụ.** Dùng `search_files`, `read_file`, CLI `--help`, workflow và source code để kiểm từng claim. Không suy ra “không tồn tại” từ một query hẹp.
4. **Phân loại drift.** Dùng `valid`, `moved/renamed`, `stale`, `contradictory`, `aspirational`, `unverifiable`.
5. **Đánh giá tác động.** Xếp `critical` nếu có thể gây push/merge/deploy sai, lộ secret, mất dữ liệu, gọi production, thanh toán sai hoặc bằng chứng giả.
6. **Đề xuất bản sửa nhỏ nhất.** Chọn một nguồn canonical; cập nhật link/path/rule và xóa lời cũ thay vì chồng thêm ngoại lệ.
7. **Re-scan.** Chạy lại tất cả claim bị sửa; hoàn tất khi không còn claim critical chưa giải quyết.

## Report Format

| Claim | Nguồn hướng dẫn | Bằng chứng repo | Phân loại | Tác động | Sửa đề xuất |
|---|---|---|---|---|---|

## Hard Invariants

- Không coi tài liệu thiết kế/draft là tính năng đã triển khai.
- Không coi file tồn tại là chứng minh luồng runtime đang dùng nó.
- Không thay quy tắc bảo vệ hiện hành bằng tài liệu cũ.
- Không sửa code để khớp tài liệu nếu code hiện tại mới là nguồn được duyệt.
- Không chạm file untracked/unrelated trong audit read-only.

## Pitfalls

- Path cũ có thể đã được move; tìm theo basename/symbol trước khi kết luận mất.
- Workflow có thể xanh nhưng required-check contract đã gãy.
- Comment và skill có thể mô tả mục tiêu tương lai bằng thì hiện tại.
- Hai tài liệu đều có thể sai; xác minh source/runtime.

## Verification

- [ ] Mọi claim critical được đối chiếu.
- [ ] Mâu thuẫn có nguồn thắng rõ ràng.
- [ ] Path/command được kiểm trực tiếp.
- [ ] Không còn hướng dẫn có thể gây thao tác destructive sai.
