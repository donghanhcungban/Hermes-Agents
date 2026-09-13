---
name: vitest-test-environment
description: "Debug Vitest setup failures: global stub, Node env."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [vitest, testing, node, happy-dom, global-stub, localStorage, test-environment]
    related_skills: [systematic-debugging, test-driven-development, donghanh]
---

# Vitest Test Environment — Pitfalls & Patterns

Ski này tổng hợp các bẫy phổ biến trong môi trường test Vitest, đặc biệt khi
dự án dùng Node 22+, `happy-dom`, và `vitest.setup.ts` với `vi.stubGlobal()`.

## Khi nào dùng skill này

- 50+ tests fail đột ngột với cùng một lỗi trong `beforeEach`
- `localStorage`, `fetch`, hoặc global browser API bỗng nhiên là `undefined`
- Test đầu tiên trong `describe` PASS, các test tiếp theo FAIL
- Setup file (`vitest.setup.ts`) có `vi.stubGlobal()` nhưng test file có `vi.unstubAllGlobals()`
- Node 22+ / 26+ cảnh báo `ExperimentalWarning: localStorage is not available`

---

## Bẫy 1: `vi.unstubAllGlobals()` phá vỡ stub từ setup file

### Triệu chứng

```
TypeError: Cannot read properties of undefined (reading 'clear')
  ❯ progressSync.test.ts:10  localStorage.clear()
```

116/9975 tests fail từ đúng 1 nguyên nhân — điển hình khi dự án có
`vitest.setup.ts` tạo stub `localStorage` và các test file dùng
`vi.unstubAllGlobals()` trong `afterEach`.

### Root cause

`vi.unstubAllGlobals()` xóa **tất cả** global stub, kể cả những stub được tạo
trong `vitest.setup.ts`. Sau mỗi test, `localStorage` biến thành `undefined`,
khiến `beforeEach` của test tiếp theo crash ngay dòng `localStorage.clear()`.

Test đầu tiên PASS vì `beforeEach` chạy trước khi bất kỳ `afterEach` nào phá vỡ stub.

### Chẩn đoán nhanh

```bash
# Tìm thủ phạm trong toàn bộ codebase
rg 'unstubAllGlobals' apps/ packages/ --type ts
```

Nếu `vitest.setup.ts` có `vi.stubGlobal(...)` và bất kỳ file test nào có
`vi.unstubAllGlobals()` → đây là vấn đề.

### Fix

```ts
// TRƯỚC (sai)
afterEach(() => {
  vi.unstubAllGlobals()  // ← xóa dòng này
  vi.restoreAllMocks()
})

// SAU (đúng)
afterEach(() => {
  vi.restoreAllMocks()  // chỉ reset mock/spy, không đụng global stub
})

// Nếu cần unstub một global cụ thể:
// Instead of vi.unstubGlobal (which does not exist), restore the original value:
// const orig = globalThis.fetch; ... afterEach(() => { globalThis.fetch = orig; })
// — or call vi.unstubAllGlobals() in afterEach.
```

### Quy tắc chung

| API | Tác dụng | Dùng trong `afterEach`? |
|-----|----------|--------------------------|
| `vi.restoreAllMocks()` | Restores spyOn implementations to originals — does **not** clear call history (use `clearAllMocks` for that) | ✅ An toàn |
| `vi.clearAllMocks()` | Xóa call history của mock | ✅ An toàn |
| `vi.unstubGlobal('x')` | Unstub đúng một global | ✅ An toàn nếu biết |
| `vi.unstubAllGlobals()` | Xóa **tất cả** global stub | ⚠️ Nguy hiểm nếu setup file có stub |

---

## Bẫy 2: `vitest.setup.ts` mock `fetch` trỏ vào `public/` — ENOENT noise

Khi setup file mock `fetch('/api/...')` bằng cách đọc file từ `public/`,
các test kiểm tra error path (HTTP 4xx/5xx, network fail) sẽ gây hàng loạt
cảnh báo `ENOENT` trong console — đây là **noise hợp lệ**, không phải lỗi thật.
Diệt noise: `console.warn.mockImplementation(() => {})` trong `beforeEach` của
cac test file kiểm tra error path.

---

## Bẫy 3: Package untracked + test assertion vượt số lượng thực tế

Khi thêm `packages/subject-<môn>/` mới mà **chưa commit vào git**, nếu
`lessons.test.ts` có assertion kiểu:

```ts
expect(BIOLOGY_LESSONS.length).toBeGreaterThanOrEqual(80)  // yêu cầu 80 bài
```

nhưng thực tế chỉ có 8 bài → test sẽ fail ngay khi package được include trong CI.

**Quy tắc:** Khi thêm package mới, hoặc commit ngay với assertion phù hợp số
bài hiện tại, hoặc thêm vào `.gitignore` nếu chưa muốn đưa vào repo.

---

## Cấu hình vitest.setup.ts cho localStorage (Node 22+)

```ts
// Kiểm tra trước khi stub — đừng để happy-dom có thể hoặc không có
try {
  globalThis.localStorage?.clear()
} catch {
  delete (globalThis as Record<string, unknown>).localStorage
}

if (typeof globalThis.localStorage === 'undefined') {
  const store = new Map<string, string>()
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => { store.set(k, v) },
    removeItem: (k: string) => { store.delete(k) },
    clear: () => { store.clear() },
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() { return store.size },
  })
}
```

---

## Checklist Audit Test Environment

- [ ] Không có `vi.unstubAllGlobals()` trong `afterEach` khi setup file có `vi.stubGlobal()`
- [ ] `vitest.setup.ts` kiểm tra `typeof globalThis.X === 'undefined'` trước khi stub
- [ ] Package mới trong `packages/` đã được commit hoặc gitignore
- [ ] Assertion số lượng bài học / dữ liệu khớp với số thực tế hiện có
- [ ] `coverage.thresholds` không bị hạ để gate xanh (sàn 90% cho cả 4 chỉ số)
