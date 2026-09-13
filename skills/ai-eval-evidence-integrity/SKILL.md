---
name: ai-eval-evidence-integrity
description: "Dùng khi đánh giá AI; đòi bằng chứng và chặn hồi quy."
version: 0.1.0
author: liend, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ai-evaluation, evidence, regression, red-team]
    related_skills: [systematic-debugging, evidence-driven-delivery]
---

# Liêm chính bằng chứng khi đánh giá AI

Skill này ngăn eval “tự tuyên bố đạt”, baseline rỗng và test chỉ kiểm chính mock của nó. Nó áp dụng cho prompt, model, router, memory, privacy, red-team và acceptance audit.

## When to Use

- Thêm hoặc sửa eval, golden set, baseline, red-team hay privacy drill.
- Thay prompt/model/provider/guardrail hoặc structured-output schema.
- Chuẩn bị tuyên bố một invariant AI đã được kiểm chứng.
- Không dùng để thay thế test logic tất định thông thường.

## Procedure

1. **Lập claim matrix.** Với từng tuyên bố, ghi claim, observable behavior, runner, production function, fixture, metric và threshold. Hoàn tất khi mọi claim có một đường chứng minh truy ngược được.
2. **Phân loại bằng chứng.** Gắn mỗi tiêu chí một nhãn: `real-path`, `faithful-fixture`, `static-assertion`, hoặc `asserted-not-measured`. Tiêu chí cuối không được tính là pass.
3. **Giữ production parity.** Eval phải dùng cùng prompt builder, model config, provider order, key pool, parser và guardrail như production; khác biệt phải ghi rõ. Hoàn tất khi không có cấu hình bị chép đôi âm thầm.
4. **Thêm negative control.** Cố tình tạo ít nhất một vi phạm cho mỗi hard gate và chứng minh suite đỏ. Nếu vi phạm vẫn xanh thì eval vô hiệu.
5. **Tách hard gate và soft signal.** Hard gate dùng cho quyền, bí mật, schema, lộ lời giải, cross-user và destructive action. Soft signal dùng cho chất lượng diễn đạt hoặc score nhiễu.
6. **Đo đúng mẫu số.** Báo tổng fixture, số chấm được, provider error, TP/FP/FN/TN, recall, precision, specificity và false-positive rate khi phù hợp.
7. **Xử lý tính ngẫu nhiên.** LLM nondeterministic phải chạy nhiều lượt hoặc cố định điều kiện; báo phân phối/dải, không kết luận từ một mẫu.
8. **Quản lý baseline.** Chỉ cập nhật khi coverage đủ và không có tỷ lệ provider error đáng kể. Không ghi đè baseline tốt bằng lượt chạy rỗng/hỏng.
9. **Xuất evidence table.** Mỗi kết luận phải chỉ tới command, commit, fixture set và output của chính lượt chạy hiện tại.

## Hard Invariants

- CI không gọi provider trả phí hay dữ liệu production.
- Mock không được tự trả chính kết luận cần chứng minh.
- `expect(true).toBe(true)` và việc chỉ đếm phần tử không phải acceptance evidence.
- Không tuyên bố “100%”, “zero residual” hoặc “all blocked” nếu thiếu negative control/truy vấn thực.
- Không xóa fixture, skip test, hạ threshold hoặc đổi mẫu số để làm cổng xanh.
- Provider error phải hiện rõ và không được tính thành pass.

## Pitfalls

- Một script exit 0 không có nghĩa mọi metric đạt; đọc điều kiện exit thật.
- Fixture giống hệt implementation có thể chỉ kiểm sự đồng thuận của hai bản sao sai.
- Mock DB không chứng minh transaction, constraint, rollback hoặc cross-process concurrency.
- Static scan không chứng minh hành vi runtime.

## Verification

- [ ] Mọi hard gate có negative control đỏ.
- [ ] Eval gọi đúng production path hoặc ghi rõ divergence.
- [ ] Báo cáo có mẫu số và provider errors.
- [ ] Baseline gắn commit/config/fixture version.
- [ ] Mọi claim pass có bằng chứng chạy được, không phải câu mô tả.
