---
name: donghanh
description: "Dùng khi phát triển dự án Đồng Hành (donghanhcungban.com)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [donghanh, typescript, monorepo, react, vitest, modular-monolith, ai-eval, curriculum-digitalization]
    related_skills: [curriculum-digitalization, safe-ai-state-authority, ai-eval-evidence-integrity, api-and-interface-design, architecture-patterns, documentation-and-adrs]
---

# Hướng dẫn Phát triển dự án Đồng Hành (donghanhcungban.com)

Tài liệu này chứa đựng các nguyên tắc cốt lõi, quy trình làm việc, tiêu chuẩn kiểm thử, số hóa nội dung học tập và thiết kế kiến trúc cho dự án Đồng Hành.

## 1. Tổng quan Dự án & Cấu trúc Monorepo

Đồng Hành đang chuyển đổi từ ứng dụng gia sư AI ngôn ngữ song ngữ Việt ⇄ Anh (V1) thành một **Personal AI Companion đa lĩnh vực** (V2).

### Cấu trúc mã nguồn (Monorepo):
- `apps/`:
  - `dhcb/`: Client frontend chính (React + Vite + Tailwind CSS v3.4).
  - `hub/`: Cổng thông tin/quản trị.
  - `server/`: Backend service (Express + Node 22).
- `packages/`:
  - `core-*/`: Các thư viện chia sẻ lõi (auth, ai, db, grading, contracts, ui, location, learner...).
  - `subject-*/`: Dữ liệu bài học và logic riêng cho từng môn học (physics, chemistry, english, programming...).
- `docs/`: Chứa các tài liệu thiết kế hệ thống, specs, changelog/progress.

---

## 2. Kiến trúc Hệ thống V2 & Quy tắc Bất biến (Invariants)

Kiến trúc V2 sử dụng mô hình **Modular Monolith + Explicit Contracts + Event Boundaries**.

### 5 Quy tắc Bất biến cốt lõi:
1. **Tách biệt Đề xuất và Thực thi**: Tác tử AI (Companion Layer) chỉ đề xuất (`proposal`), không được tự ý thực thi hoặc trực tiếp chỉnh sửa các bảng dữ liệu nghiệp vụ (Domain Layer) mà chưa được thẩm định.
2. **Kiểm soát Quyền & Ngữ cảnh**: Mọi truy vấn ngữ cảnh phải đi qua *Knowledge Fabric* và *Context Engine* để đảm bảo giới hạn token budget và quyền riêng tư theo vai trò.
3. **Thanh toán & Thẩm quyền**: Không cho phép AI tự động cập nhật trạng thái billing, permissions, mastery hoặc authoritative state mà không có authority thích hợp hoặc sự xác nhận của người dùng.
4. **Cô lập Dữ liệu Nhạy cảm**: Dữ liệu nhạy cảm của người dùng (trong Personal World Model) không được tự động đi xuyên qua các domain khác nhau khi chưa được phân scope rõ ràng.
5. **Độc quyền Ngôn ngữ**: Tiếng Việt là ngôn ngữ mặc định của mọi tài liệu kỹ thuật, hướng dẫn bài học và trải nghiệm người dùng.

---

## 3. Quy trình Di chuyển Kiến trúc (Migration V1 → V2)

Áp dụng chiến lược **Strangler Migration** để thay thế dần V1 mà không gây gián đoạn hệ thống đang vận hành:
- **Additive trước Destructive**: Luôn thêm schema, table hoặc contract mới trước; không xóa hoặc đổi tên cơ sở dữ liệu cũ trong cùng một pull request.
- **Dual-read/write có thời hạn**: Chỉ áp dụng khi cần so sánh dữ liệu cũ và mới; bắt buộc phải cấu hình metric đo độ lệch (mismatch) và đặt ngày kết thúc dual-path rõ ràng.
- **Shadow trước Cutover**: Chạy song song mô hình V2 trong chế độ bóng (shadow), không ảnh hưởng đến trải nghiệm người dùng cho đến khi vượt qua các acceptance gate.

---

## 4. Quy trình Git & Tiêu chuẩn Mã nguồn

### Quy định Git Flow nghiêm ngặt:
- **KHÔNG ĐƯỢC push hoặc merge trực tiếp vào nhánh `main`**.
- Luôn tạo nhánh tính năng (`feature/*` hoặc `fix/*`) từ `main`.
- Đẩy nhánh lên remote, tạo Pull Request (PR).
- Chỉ được merge sau khi tất cả các kiểm tra tích hợp liên tục (CI) đạt trạng thái xanh (green) và có sự phê duyệt (approve).

### Khóa cứng phiên bản (Runtime & Tooling):
- Node.js version `>=22`.
- React `18.3`.
- Tailwind CSS `v3.4`.
- ESLint `8` (`.eslintrc.cjs`).
- Prettier định dạng code.
- *Lưu ý:* Không tự ý nâng cấp framework/tooling khi chưa đánh giá độ tương thích toàn hệ thống.

---

## 5. Quy trình Số hóa Bài học (Curriculum Digitalization)

Mỗi bài học số hóa trong thư mục `packages/subject-*/lessons/` cần tuân thủ cấu trúc 5 phần:
1. **Hook**: Kết nối nội dung lý thuyết với đời sống thực tế hoặc hiện tượng tự nhiên.
2. **Theory**: Trình bày lý thuyết cốt lõi bằng Markdown ngắn gọn. Định dạng công thức bằng subscript/superscript (ví dụ: $H_2O$, $C_nH_{2n}$) hoặc LaTeX nếu phức tạp.
3. **Worked Example**: Ví dụ mẫu kèm lời giải từng bước rõ ràng.
4. **Check Questions**: Tối thiểu 2 câu hỏi đánh giá nhanh (`numeric`, `choice`, `formula`, `chemEquation`). Đăng ký đáp án chính xác theo engine chấm.
5. **SRS Cards**: Từ 2 đến 4 câu Q&A cực kỳ ngắn gọn phục vụ thuật toán Spaced Repetition System.

---

## 6. Đảm bảo Liêm chính trong Kiểm định AI (AI Evaluation)

Khi điều chỉnh Prompt, Model, Gateway hoặc Provider (ví dụ: tối ưu hóa Gemini làm engine chính):
- **Tập Golden Set & Baseline**: Phải chạy qua benchmark kiểm định, so sánh chi phí/độ trễ (cost/latency evidence) so với baseline hiện tại.
- **Giữ Production Parity**: Môi trường đánh giá phải dùng chung cấu hình prompt builder, model config và provider order như production.
- **Negative Control**: Cố tình tạo ra một ca vi phạm nghiêm trọng (ví dụ: rò rỉ secret, vượt quyền truy cập) để kiểm tra xem hệ thống kiểm thử có báo lỗi (đỏ) hay không.

---

## 7. Quy trình Kiểm thử & Mô phỏng (Vitest & Playwright)

- **Kiểm thử Unit & Integration**: Chạy bằng Vitest (`npm run test` hoặc `vitest run`).
- **Kiểm thử E2E**: Chạy bằng Playwright (`npm run test:e2e`).
- **Mô phỏng hermesSim (môn Lập trình)**: 
  - Đảm bảo tính tất định tuyệt đối (cùng chuỗi lệnh đầu vào bắt buộc sinh ra đầu ra giống nhau 100% từng byte).
  - Luôn in dòng tự khai `DONG_TU_KHAI_HERMES` (chứa tiền tố `[GIA LAP]`) ở dòng đầu tiên để học viên không nhầm lẫn với AI/agent thật.
  - Tuân thủ Ba Luật Sư Phạm:
    1. Trạng thái `cho-duyet` chỉ chuyển sang `xong` khi có lệnh `duyet` của học viên (không tự động hoàn thành).
    2. Chặn các lệnh nguy hiểm hoặc tiết lộ bí mật.
    3. Cảnh báo và yêu cầu xác nhận trước các tác vụ khó hoàn tác.
