---
name: master-software-engineering
description: "Dùng khi viết/sửa/review code thật — chuẩn kỹ sư trưởng."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [engineering, architecture, quality-gate, security, testing, principal-engineer]
    related_skills: [evidence-driven-delivery, requesting-code-review, systematic-debugging]
---

# Kỹ sư Phần mềm Thượng Thừa (Principal Engineer Standard)

Skill này nâng chuẩn lập trình mặc định lên mức **Principal/Staff Engineer**: không chỉ code chạy được, mà phải đúng kiến trúc, an toàn, có bằng chứng kiểm thực và sống được lâu dài trong hệ thống thật. Đúc kết từ thực chiến trên các dự án sản xuất quy mô lớn (donghanh, xboss) và quy trình audit 11 tầng.

## When to Use

- Mọi tác vụ viết code sản xuất, thiết kế kiến trúc, refactor, xử lý database hoặc review code.
- Khi người dùng yêu cầu "code chuẩn", "chuyên nghiệp", "thượng thừa", hoặc không nói rõ tiêu chuẩn (mặc định dùng skill này).

## 1. Nguyên tắc Bất biến về Kiến trúc & Type Safety

```
[UI/Client Layer]
    │ (Strict DTO / API Contract)
    ▼
[API/Boundary Layer (Auth + Validation Middleware)]
    │ (Zod/Pydantic Schema — không tin dữ liệu thô)
    ▼
[Domain Services (business logic thuần)]
    │ (Atomic Transactions & Idempotency)
    ▼
[Data Layer (DB Pool / Storage)]
```

1. **Type Safety Tuyệt đối:** không dùng `any`/`as unknown as Type` trừ khi có Type Guard bọc rõ. Mọi dữ liệu đi vào hệ thống từ bên ngoài (network, form, AI output, webhook, DB) **bắt buộc** phải parse/validate qua schema (Zod/Pydantic/tương đương).
2. **Schema-First Contract-Driven:** định nghĩa hợp đồng dữ liệu (DTO/API contract) TRƯỚC khi viết logic/UI. Contract có version tường minh.
3. **Không bao giờ đoán số.** Mọi công thức tính toán nghiệp vụ nằm trong code xác định, không để LLM tự suy ra con số — AI chỉ chọn tool và diễn giải kết quả.

## 2. Quản trị Dữ liệu & Giao dịch Bất biến

- **Giao dịch nguyên tử:** mọi thao tác ghi nhiều bảng hoặc cần tính nhất quán (trừ tiền, cấp quyền, đếm lượt) **bắt buộc** chạy qua transaction wrapper; luôn giải phóng kết nối trong `finally`.
- **Migration:** đặt tên theo thứ tự số; **cộng thêm trước, không phá vỡ sau** (additive-first) — không xóa cột/bảng đang chạy mà chưa qua giai đoạn deprecation; dùng `IF NOT EXISTS`/`IF EXISTS`.
- **Tính lũy đẳng:** mọi migration/script phải chạy lại lần 2 mà không gây lỗi hoặc đổi thêm gì.

## 3. Lá chắn Chống Ảo giác AI (Anti-Hallucination Guardrails)

```
[Raw AI Response] → [Strict Schema Parser] → [Deterministic Business Validator] → [DB Persistence]
                              │ (Parse Error)                    │ (Invalid State)
                              ▼                                  ▼
                     [Deterministic Fallback]           [Deterministic Fallback]
```

- AI Output chỉ là **dữ liệu thô chưa được tin cậy**. Tuyệt đối không để AI output trực tiếp thay đổi số dư tài khoản, cấp quyền, hay cập nhật trạng thái định danh mà không qua bộ lọc logic tất định.
- Khi AI trả về JSON lỗi/không khớp schema → tự động kích hoạt fallback quy tắc (rule-based), không crash luồng người dùng.

## 4. Cổng Chất lượng Bắt buộc (Quality Gates — Dung sai = 0)

Mọi thay đổi code trước khi coi là hoàn thành phải chạy đủ bộ gate liên quan tới dự án đang làm (tham chiếu đúng lệnh thật của repo, không bịa lệnh):

```bash
# Ví dụ chuẩn Node/TS — thay bằng lệnh thật của repo
npm run typecheck   # 0 lỗi
npm run lint         # 0 warning
npm run format:check
npm test             # 100% pass, không flaky (chạy ≥ 3 lần nếu nghi ngờ)
npm run build
```

- **Không bao giờ hạ ngưỡng test/coverage để gate xanh.** Nếu gate đỏ, sửa code hoặc test đúng nguyên nhân gốc, không weaken điều kiện.
- **Deterministic tests là trọng tài chính**, AI không tự đánh giá pass/fail của chính mình.
- **Không viết "change-detector tests"** — test phải kiểm tra bất biến (invariant), không đóng băng giá trị hiện tại (danh sách model, số phiên bản…).

## 5. Kiểm thử Hoài nghi (Skeptical Testing) — từ Quy trình Audit 11 Tầng

Build xanh + test xanh + coverage 100% **vẫn có thể sai** — đây là loại lỗi không cổng nào bắt được:

1. **Logic ngẫu nhiên:** mọi chỗ dùng `sort(() => Math.random() - 0.5)` là SAI (không phải thuật toán trộn) — luôn dùng **Fisher–Yates**. Đo phân bố bằng ≥ 100.000 lượt thực nghiệm, không suy luận cảm tính.
2. **Bất biến (Invariants):** viết test kiểm tính chất phải luôn đúng — lũy đẳng (chạy 2 lần = 1 lần), cộng tính (chia đôi rồi cộng = xử lý một lần), khép kín (ghi rồi đọc lại phải đúng).
3. **Ca biên bắt buộc:** mảng rỗng, `null` vs `0`, race condition khi gọi 2 lần song song, ranh giới UTC/múi giờ, giá trị ngay dưới/ngay trên mỗi hằng số/ngưỡng.
4. **Đối chiếu độc lập:** tính tay hoặc dùng thư viện khác để so sánh kết quả — một cài đặt tự đối chiếu với chính nó không chứng minh được gì.
5. **Mỗi lỗi phát hiện phải có test tái hiện:** FAIL trước khi sửa, PASS sau khi sửa — chưa thấy nó fail thì chưa chắc test đang kiểm đúng thứ.

## 6. Bảo mật (OWASP Checklist Rút gọn)

- **SQLi:** mọi câu query dùng tham số hóa (`$1, $2…`), không bao giờ nối chuỗi trực tiếp giá trị người dùng.
- **AuthZ/IDOR:** mọi handler đọc/sửa dữ liệu theo `id` từ URL/body phải đối chiếu `user_id` từ token, không tin giá trị client gửi lên.
- **Secret:** không hardcode API key/secret; `.env` không được commit; scan trước mọi commit.
- **Idempotency:** webhook thanh toán/xử lý tác vụ nhạy cảm phải kiểm tra "đã xử lý chưa" trước khi thao tác — không cộng tiền/quyền 2 lần nếu request gửi lại.
- **Error handling:** response lỗi cho client không bao giờ kèm stack trace/chi tiết nội bộ (tên bảng, path server) ở production.

## 7. Quy trình Làm việc

1. **Đọc trước khi sửa:** dùng `read_file`/`search_files` xác minh nội dung/cấu trúc thật trước khi động vào.
2. **Sửa đủ phạm vi:** một fix phải sửa hết cả họ lỗi (sibling call paths), không chỉ điểm báo lỗi đầu tiên.
3. **Xóa nhiều hơn thêm:** phức tạp tích tụ là thảm họa — ưu tiên đơn giản hóa.
4. **Theo pattern sẵn có** trong codebase, đừng phát minh cách làm mới khi đã có chuẩn.
5. **Báo cáo trung thực:** nếu chưa chạy thử được (thiếu key/Docker/quyền) — nói rõ là chưa chạy, không bịa kết quả.

## Hard Invariants

- Không để AI output ghi trực tiếp vào billing/permissions/trạng thái định danh mà không qua bộ xác thực tất định.
- Không commit secret, không hạ quality gate để merge nhanh.
- Không báo "hoàn thành" khi chưa có bằng chứng thực thi (output lệnh thật).
- Mọi migration phải additive-first và lũy đẳng.

## Pitfalls

- Tin docstring/comment mà không đọc code thật bên dưới — chúng có thể mô tả sai.
- Coi "một lượt test xanh" là đủ bằng chứng — test flaky có thể ẩn nhiều tuần.
- Sửa triệu chứng thay vì nguyên nhân gốc để gate xanh nhanh.
- Thêm hook/extension point không có consumer cụ thể (speculative infrastructure).

## Verification

- [ ] Type safety: không `any` trần, mọi input ngoài được validate qua schema.
- [ ] Quality gate đủ bộ (typecheck/lint/format/test/build) xanh với output thật.
- [ ] Không có secret hardcode, mọi handler nhạy cảm có auth + scope check.
- [ ] Mọi lỗi đã sửa đều có test tái hiện FAIL→PASS.
- [ ] Không có logic ngẫu nhiên sai (đã kiểm Fisher–Yates nếu có shuffle).
