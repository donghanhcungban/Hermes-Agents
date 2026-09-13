# PR Policy Patterns

Chứa các pattern cụ thể của PR policy gate đã gặp trong thực tế.

## Donghanh / donghanhcungban.com — Metadata Gate

Workflow: `.github/workflows/pr-policy.yml`

### 6 Section bắt buộc (exact string match):

```
## Tóm tắt
## Issue / outcome
## Research / spec
## Validation
## Rủi ro, rollout và rollback
## Definition of Done
```

> **Pitfall**: Dùng section tiếng Anh như `## Summary` hay `## Risk` sẽ KHÔNG khớp. Section tiếng Việt là exact match.

### Với PR `feat` — thêm 3 điều kiện:

1. **Spec file link** — regex: `docs/(?:specs/\d{4}-\d{2}-\d{2}-[a-z0-9-]+|research/[a-z0-9._-]+)\.md`
   - Chấp nhận: `docs/specs/2026-09-01-feature-name.md` hoặc `docs/research/ten-nghien-cuu.md`
   - Spec file phải **tồn tại thật** trên nhánh đầu PR (CI kiểm qua GitHub API)

2. **Chuỗi `Approved for implementation`** (case-insensitive) phải xuất hiện trong body.

3. **Dependabot PR**: bỏ qua tất cả (chỉ kiểm Conventional Commits tiêu đề).

### CI đọc PR description LIVE

Workflow sử dụng `github.rest.pulls.get()` tại runtime — không dùng `context.payload.pull_request`.
Update `gh pr edit --body` rồi `gh run rerun --failed` là đủ, không cần push commit mới.

---

## Donghanh — UI Policy Gate

Test: `scripts/ui-policy.test.ts`

Check regex: `/text-\[(9|10)px\]/` trên toàn bộ `apps/dhcb/src/`.

| Class | Trạng thái |
|---|---|
| `text-[9px]` | CẤM |
| `text-[10px]` | CẤM |
| `text-[11px]` | OK (sàn tối thiểu) |
| `text-xs` (12px) trở lên | OK |
