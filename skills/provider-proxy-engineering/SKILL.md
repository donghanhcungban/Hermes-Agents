---
name: provider-proxy-engineering
description: "Use when building LLM provider proxies safely."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [proxy, llm, provider, openai-compatible, oauth, credential-pool]
    related_skills: [hermes-provider-management, cli-provider-bridges]
---

# Provider Proxy Engineering

Dùng khi xây hoặc sửa proxy LLM/provider: OpenAI-compatible endpoints, catalog model động, OAuth/API credential pool, failover và cache.

## Mục tiêu

Proxy phải phản ánh năng lực upstream thật mà không rò secret, không làm cạn account pool, và không để endpoint discovery bị lạm dụng.

## Luồng làm việc

1. Đọc endpoint, cache, credential resolver và tất cả đường non-stream/stream trước khi sửa.
2. Viết test RED cho một bất biến hẹp; chạy để chứng minh lỗi.
3. Sửa tối thiểu, chạy test hẹp rồi toàn bộ suite.
4. Trước commit: `git diff --check`, scan secret trên dòng thêm, và independent review fail-closed.
5. Không gọi production-ready khi review còn blocking findings hoặc chưa xác minh endpoint thật.

## Bất biến

- Catalog public có thể là **union** của nhiều account, nhưng năng lực routing phải lưu theo credential/project.
- `unsupported model` (400/404) là negative capability của cặp account-model; không phải lý do cooldown toàn bộ account.
- 401/403/429 và quota exhaustion mới có thể làm account-wide failover/cooldown, theo chính sách provider.
- Unknown model cần bounded refresh path ngay cả khi catalog đang warm; throttle/coalesce vẫn phải giới hạn upstream.
- Refresh dùng credential hoặc spawn CLI phải chỉ cho caller local/đã xác thực, có minimum interval và lock/coalescing.
- Luồng streaming và non-stream phải dùng cùng logic lựa chọn account/model.

## Kiểm thử bắt buộc

- cold cache, warm cache và concurrent refresh;
- model mới từ account sau xuất hiện trong catalog;
- account A không hỗ trợ model X nhưng vẫn hỗ trợ Y; account B hỗ trợ X;
- failover cho X không làm A bị loại khỏi Y;
- repeated forced refresh không tạo nhiều upstream request/subprocess;
- handler-level authorization hoặc local-only policy của refresh endpoint.

Xem checklist chi tiết tại `references/model-catalog-and-pool-checklist.md`.
