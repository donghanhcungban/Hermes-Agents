---
name: ci-gate-debugging
description: "Use when a CI check fails on a PR. Fix and re-run."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [CI, GitHub Actions, PR policy, prettier, debugging, github]
    related_skills: [github-pr-workflow, github-code-review]
---

# CI Gate Debugging

Kỹ năng này áp dụng khi một CI check đỏ trên PR và cần xác định nguyên nhân, sửa, và re-run mà không cần push code thừa.

## 1. Triage nhanh — Đọc log lỗi

```bash
# Xem tóm tắt status của tất cả checks
gh pr checks <PR_NUMBER>

# Xem log chỉ của các jobs thất bại
gh run view <RUN_ID> --log-failed

# Lọc ra các dòng lỗi thực sự
gh run view <RUN_ID> --log-failed 2>&1 | grep -E '##\[error\]|AssertionError|Error:|FAIL ' | head -30
```

## 2. Re-run jobs thất bại KHÔNG cần push code mới

Dùng khi: lỗi là do PR description, flaky test, network timeout — không phải do code.

```bash
# Re-run failed jobs của run mới nhất trên nhánh hiện tại
gh run rerun $(gh run list --branch $(git branch --show-current) --limit 1 --json databaseId -q '.[0].databaseId') --failed

# Hoặc re-run bằng run ID cụ thể
gh run rerun <RUN_ID> --failed

# Re-run một workflow cụ thể (ví dụ: PR policy)
RUN_ID=$(gh run list --branch $(git branch --show-current) --workflow 'PR policy' --limit 1 --json databaseId -q '.[0].databaseId')
gh run rerun $RUN_ID --failed
```

## 3. PR Metadata / Policy Gate

Job tên `metadata` hoặc tương tự chạy một GitHub Script để validate PR description.

**Dấu hiệu lỗi trong log:**
```
##[error]PR Ready for review còn thiếu: ## Tóm tắt
##[error]PR feat phải liên kết đặc tả tại docs/specs/...
##[error]PR feat phải xác nhận spec đã Approved for implementation.
```

**Nguyên tắc quan trọng**: Hầu hết các metadata gate **đọc PR description LIVE qua GitHub API** tại thời điểm job chạy — không phải từ webhook payload. Điều này có nghĩa:
- Sửa description → re-run job (không cần push code) là đủ.
- Dùng `gh pr edit --body` để update, sau đó `gh run rerun --failed`.

**Quy trình fix:**
```bash
# 1. Xem log để biết thiếu section nào
gh run view <RUN_ID> --log-failed 2>&1 | grep '##\[error\]'

# 2. Xem nội dung workflow để biết section nào bắt buộc
cat .github/workflows/pr-policy.yml

# 3. Update description
gh pr edit <PR_NUMBER> --body "<body-with-all-required-sections>"

# 4. Verify đã lưu
gh pr view <PR_NUMBER> --json body -q '.body' | grep '## RequiredSection'

# 5. Re-run chỉ job thất bại
gh run rerun <RUN_ID> --failed
```

**Với PR feat yêu cầu spec file:** Spec file phải tồn tại thật trên nhánh (CI verify qua GitHub API). Cần commit spec file rồi mới link vào description.

## 4. Prettier / Format Fails on CI nhưng Pass Local

**Dấu hiệu:**
```
[warn] SOME_FILE.md
[warn] Code style issues found in the above file.
```
Nhưng `npx prettier --check .` chạy local sạch hoàn toàn.

**Triage:**
```bash
# Kiểm tra CRLF
python3 -c "d=open('file.md','rb').read(); print('CRLF:', d.count(b'\r\n'))"
# Kiểm tra prettier version
node -e "console.log(require('./node_modules/prettier/package.json').version)"
# Thử write explicit LF
npx prettier --write --end-of-line lf <file> && git diff
```

**Nếu tất cả pass local và file không đổi so với main**: Đây là flaky CI cache. Giải pháp: `gh run rerun <ID> --failed`. Không nên tiếp tục debug.

## 5. UI Policy / Tailwind Class Rule Tests

**Dấu hiệu:**
```
FAIL scripts/ui-policy.test.ts
AssertionError: expected [ Array(1) ] to deeply equal []
+   "apps/dhcb/src/pages/SomePage.tsx:342",
```

**Fix:**
```bash
# Mở file tại dòng được báo, tìm và sửa class vi phạm
# Ví dụ: text-[10px] → text-[11px]
npm run test -- scripts/ui-policy.test.ts  # Verify xanh sau khi sửa
```

## 6. Merge khi tất cả xanh

```bash
gh pr checks <PR_NUMBER>  # confirm all pass
gh pr merge <PR_NUMBER> --squash --delete-branch
```

Xem thêm: `references/pr-policy-patterns.md`
