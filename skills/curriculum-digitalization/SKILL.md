---
name: curriculum-digitalization
description: "Digitize textbooks and validate structured lessons."
version: 1.0.0
author: liend, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [curriculum, education, digitalization, lesson-validation, textbook]
    related_skills: [donghanh]
---

# Quy trình số hóa sách giáo khoa và kiểm thử bài học tự động

Tài liệu này hướng dẫn cách thực hiện số hóa nội dung sách giáo khoa (SGK), thiết kế cấu trúc bài học tiêu chuẩn chất lượng cao, tích hợp vào registry và thiết lập quy trình kiểm thử tự động để bảo đảm chất lượng dữ liệu.

## 1. Cấu trúc bài học tiêu chuẩn (5 bước)

Mỗi bài học số hóa cần tuân thủ cấu trúc 5 phần rõ ràng:

1. **Hook (Móc nối thực tế)**:
   - Một đoạn văn ngắn liên hệ nội dung bài học với đời sống thực tiễn, hiện tượng tự nhiên hoặc ứng dụng quen thuộc để kích thích trí tò mò của học sinh.
2. **Theory (Lý thuyết cốt lõi)**:
   - Trình bày kiến thức trọng tâm ngắn gọn, súc tích, định dạng Markdown rõ ràng.
   - Định dạng ký hiệu/công thức bằng subscript/superscript (vd: $C_nH_{2n}O_2$, $Cu(OH)_2$) hoặc LaTeX nếu cần.
3. **Worked Example (Ví dụ mẫu)**:
   - Bài toán hoặc câu hỏi tình huống kèm lời giải chi tiết theo từng bước rõ ràng để học sinh học phương pháp giải.
4. **Check Questions (Câu hỏi kiểm tra nhanh)**:
   - Tối thiểu 2 câu hỏi để học sinh tự đánh giá ngay sau khi học lý thuyết.
   - Phân loại câu hỏi:
     - `numeric`: Trả lời bằng số (có thể đi kèm đơn vị).
     - `choice`: Trắc nghiệm một hoặc nhiều lựa chọn đúng.
     - `formula`: Trả lời bằng công thức hóa học/toán học (cho Hoá học).
     - `chemEquation`: Cân bằng phương trình hóa học.
   - **Bắt buộc**: Phải khai báo đáp án rõ ràng và chính xác theo định dạng engine chấm.
5. **SRS Cards (Thẻ nhớ ôn tập)**:
   - Từ 2 đến 4 câu hỏi dạng Hỏi - Đáp (Q&A) cực kỳ ngắn gọn để phục vụ thuật toán lặp lại ngắt quãng (Spaced Repetition System).

## 2. Quy tắc lập trình & Tránh lỗi Linting

Khi định nghĩa bài học, cần đảm bảo:
- ID bài học tuân theo biểu thức chính quy (Regex) quy định cho từng môn học (vd môn Hoá: `/^chem(10|11|12)-c\d+-b\d+$/`, môn Lý: `/^ly(10|11|12)-c\d+-b\d+$/`).
- Thuộc tính `reviewStatus` luôn được gán giá trị `'draft'` cho các bài học mới soạn thảo chưa qua giáo viên phê duyệt thực tế.
- Chạy `npm run typecheck`, `npm run lint` và `npm run format` để định dạng file sạch sẽ trước khi commit.

## 3. Môn Sinh học — Đặc thù thiết kế (PA B: Trắc nghiệm + SRS)

Sinh học khác Toán/Lý/Hoá: ~85% nội dung là mô tả, không tính toán được → chỉ làm theo **PA B** (đã chốt 2026-08-01):
- `checkQuestions`: Dùng `choice` là chủ yếu. Câu hỏi `numeric` chỉ dùng cho phần di truyền (công thức ADN, nguyên phân/giảm phân) và sinh thái (hiệu suất).
- `srsCards`: 2-4 thẻ Q&A ngắn gọn — đây là phần mang lại giá trị chính của package Sinh học.
- `workedExample.steps`: Mảng string; mỗi phần tử là một bước ngắn. KHÔNG cần `\n` ở cuối từng phần tử (khác với `theory` cần `\\n` để xuống dòng).
- `reviewStatus`: Luôn là `'draft'` — phải có giáo viên Sinh duyệt trước khi public.

### Sơ đồ ánh xạ chương → id cho package Sinh học 10

Sinh 10 có **Phần mở đầu** (3 bài) + 7 Chương, cần ánh xạ chương như sau:
```
Phần mở đầu → chapterNumber: 1 (chapterTitle: 'Phần mở đầu')
Chương 1     → chapterNumber: 2
Chương 2     → chapterNumber: 3
Chương 3     → chapterNumber: 4
Chương 4     → chapterNumber: 5
Chương 5     → chapterNumber: 6  
Chương 6     → chapterNumber: 7
Chương 7     → chapterNumber: 8
```
ID pattern: `sinh${grade}-c${chapterNumber}-b${lessonNumber}` — lessonNumber tiếp tục liên tục xuyên suốt toàn sách (không reset về 1 ở mỗi chương).

### Phân bố bài học Sinh học theo lớp
- Sinh 10: 26 bài (Phần mở đầu + C1-8: tế bào, vi sinh vật, virus)
- Sinh 11: 26 bài (C1-5: trao đổi chất, cảm ứng, sinh trưởng, sinh sản)
- Sinh 12: 30 bài (C1-5 di truyền học; C6 tiến hoá; C7-10 sinh thái)

### Sơ đồ ánh xạ chương → id cho package Sinh học 12

Sinh 12 có cấu trúc 2 file (`sinh12c1.ts` và `sinh12c2.ts`) với các chương:
```
File sinh12c1.ts:
  Chương 1 (Cơ chế DT & BD)         → chapterNumber: 1  (Bài 1-7)
  Chương 2 (Tính quy luật DT)         → chapterNumber: 2  (Bài 8-13)
  Chương 3 (DT học quần thể)          → chapterNumber: 3  (Bài 14-15)
  Chương 4 (Ứng dụng DT học)         → chapterNumber: 4  (Bài 16-18)
  Chương 5 (DT học người)            → chapterNumber: 5  (Bài 19)

File sinh12c2.ts:
  Chương 6 (Bằng chứng & cơ chế tiến hoá) → chapterNumber: 6  (Bài 20-23)
  Chương 7 (Phát sinh sự sống)       → chapterNumber: 7  (Bài 24)
  Chương 8 (Sinh thái học cá thể)    → chapterNumber: 8  (Bài 25-26)
  Chương 9 (Quần xã sinh vật)        → chapterNumber: 9  (Bài 27)
  Chương 10 (Hệ sinh thái & bảo vệ)  → chapterNumber: 10 (Bài 28-30)
```
**Lưu ý**: Trong một phép viết phân tán qua nhiều file, lessonNumber tiếp tục liên tục xuyên suốt toàn sách (không reset về 1 khi sang file mới).

---

## 4. Khắc phục lỗi phổ biến khi viết kiểm thử bài học

Khi viết bài học mới và chạy kiểm thử tự động với `core-grading`, hãy chú ý các lỗi sau:

### Lỗi PARSE_ERROR (Không tìm thấy hoặc không khớp đơn vị)
- **Nguyên nhân**: Bạn khai báo `unit` cho câu hỏi `numeric` nhưng đơn vị này chưa được định nghĩa trong `packages/core-grading/units.ts` (ví dụ: `m/s²`, `kg.m/s`, `N/m`...).
- **Giải pháp**: 
  1. Mở `packages/core-grading/units.ts`.
  2. Định nghĩa đơn vị mới vào bảng hằng số `UNITS` kèm hệ số quy đổi `factor` và vectơ 7 chiều của đơn vị SI tương ứng `dim` (ví dụ: `dim: D(1, 1, -1)` cho động lượng).
  3. Chạy `npm run build:packages` để cập nhật file build trước khi test lại.

### Lỗi WRONG_VALUE khi test tự động câu hỏi dùng đơn vị
- **Nguyên nhân**: Giá trị `value` khai báo trong bài học là giá trị lưu theo hệ SI cơ sở (ví dụ: `0.8` cho hiệu suất `80%`), nhưng kiểm thử mô phỏng học sinh nhập thô `80` khiến so sánh bị lệch.
- **Giải pháp**: Trong test file (ví dụ `lessons.test.ts`), khi mô phỏng học sinh nhập, hãy chia giá trị SI cho `factor` của đơn vị đó để tạo ra chuỗi nhập chính xác:
  ```typescript
  const unitDef = q.answer.unit ? UNITS[q.answer.unit] : undefined
  const factor = unitDef ? unitDef.factor : 1
  const offset = unitDef ? (unitDef.offset ?? 0) : 0
  const displayValue = (q.answer.value - offset) / factor
  studentInput = q.answer.unit ? `${displayValue} ${q.answer.unit}` : `${displayValue}`
  ```

### Lỗi ESLint `no-useless-escape` trong chuỗi bài học
- **Nguyên nhân**: Dùng `\"` (escaped double-quote) bên trong string single-quoted trong TypeScript → ESLint báo lỗi `Unnecessary escape character`.
- **Giải pháp A** (đơn giản nhất): Trong chuỗi single-quoted, dùng dấu nháy kép trực tiếp `"` thay vì `\"`:
  ```ts
  // SAI
  explain: 'đóng vai trò như \"người phiên dịch\".'
  // ĐÚNG  
  explain: 'đóng vai trò như "người phiên dịch".'
  ```
- **Giải pháp B**: Dùng template literal để tránh xung đột nháy:
  ```ts
  explain: `đóng vai trò như "người phiên dịch".`
  ```
- **Chú ý**: Lỗi này không block test nhưng block `npm run lint` → phải sửa trước khi commit.

### Chẩn đoán id mismatch hàng loạt (id không khớp chapterNumber/lessonNumber)
- **Nguyên nhân**: Khi viết nhiều bài trong cùng file, dễ sao chép id cũ mà quên cập nhật số chương.
- **Phát hiẹn tụ đọng**: Chạy script Python qua `execute_code` để scan toàn bọ file:

  > Script đã có: `scripts/check_lesson_ids.py` trong skill này — chạy lại và truyền `--fix` để tự đọng vá id.

  ```python
  from hermes_tools import read_file
  import re
  
  r = read_file("packages/subject-biology/lessons/sinh12c1.ts", offset=1, limit=2000)
  lines = [l.split("|", 1)[1] for l in r["content"].split("\n") if "|" in l]
  raw = "\n".join(lines)
  
  ids = list(re.compile(r"id: '(sinh\d+-c(\d+)-b(\d+))'").finditer(raw))
  cns = list(re.compile(r"chapterNumber: (\d+)").finditer(raw))
  lns = list(re.compile(r"lessonNumber: (\d+)").finditer(raw))
  
  for i, m in enumerate(ids):
      id_c, id_b = int(m.group(2)), int(m.group(3))
      actual_c = int(cns[i].group(1)) if i < len(cns) else -1
      actual_b = int(lns[i].group(1)) if i < len(lns) else -1
      if id_c != actual_c or id_b != actual_b:
          print(f"MISMATCH: id={m.group(1)} → should be c{actual_c}-b{actual_b}")
  ```
- **Sửa tự động**: Dùng `raw.replace(old_id, new_id)` rồi `write_file(path, raw)` sau khi đọc file vào biến `raw`.

### Lỗi localStorage is not available (Node.js 22+ / 26+)
- **Nguyên nhân**: Môi trường chạy Vitest trên các phiên bản Node.js mới có sẵn `globalThis.localStorage` ở dạng thực nghiệm nhưng chưa cấu hình file, gây crash khi gọi `.clear()`.
- **Giải pháp**: Thêm đoạn cấu hình sau vào đầu `vitest.setup.ts` để xóa thuộc tính lỗi của Node và stub in-memory mock sạch cho Happy-DOM:
  ```typescript
  try {
    globalThis.localStorage?.clear()
  } catch {
    delete (globalThis as any).localStorage
  }
  ```
