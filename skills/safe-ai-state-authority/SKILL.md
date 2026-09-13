---
name: safe-ai-state-authority
description: "Dùng khi AI ghi nhớ, đổi trạng thái hoặc hành động."
version: 0.1.0
author: liend, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    related_skills: []
    tags: [authority, memory, consent, automation, audit]
---

# Quyền và trạng thái an toàn cho AI

Skill này thiết kế ranh giới giữa lời đề xuất của AI và state có thẩm quyền. Nó áp dụng cho memory, personal facts, domain state, external actions và automation.

## When to Use

- AI muốn ghi nhớ thông tin về người dùng.
- Planner muốn cập nhật database hoặc gọi tool có side effect.
- Xây capability registry, consent, policy hoặc automation grant.
- Audit một agent có quyền quá rộng.

## Authority Priority

```text
security/law
> authorization
> domain invariant
> explicit consent
> personal policy
> workflow policy
> agent proposal
> LLM wording
```

Mức điển hình: `READ`, `SUGGEST`, `DRAFT`, `WRITE_INTERNAL`, `EXECUTE_WITH_CONFIRMATION`, `AUTOMATE`, `DENY`.

## Memory Procedure

1. AI chỉ tạo candidate, không ghi authoritative fact.
2. Parse schema và gắn origin, provenance, confidence, sensitivity, purpose, freshness và expiry.
3. Dedup/conflict check với record hiện hành.
4. Áp policy: `ACCEPT`, `MERGE`, `REJECT`, `ASK_USER`, `EXPIRE`.
5. Derived inference không được đè user declaration.
6. Ghi append/supersede cùng audit; hỗ trợ inspect, correct, expire, delete và export.

## Action Procedure

1. Phân biệt plan, proposal, execution và domain mutation.
2. Tra capability/tool manifest: schema, permission, risk, side effect, timeout, cost và audit.
3. Tính effective authority qua toàn bộ priority chain.
4. Hành động external/high-risk cần confirmation hoặc grant `AUTOMATE` hợp lệ.
5. Grant phải có subject, capability/action, scope, purpose, budget, review/expiry và revoke path.
6. Validate input trước executor; validate result trước state proposal.
7. Owning domain engine mới được commit state.
8. Dùng idempotency key, transaction, immutable receipt và compensation khi cần.

## Hard Invariants

- LLM không trực tiếp đổi auth, permission, billing, entitlement, mastery hoặc authoritative fact.
- `AUTOMATE` không vượt security, authorization, consent hay domain invariant.
- Không policy nghĩa là chưa có quyền, không phải quyền mặc định.
- Cross-user/cross-domain access phải qua contract và policy.
- External side effect phải audit được và retry an toàn.
- Secret/sensitive context chỉ được đưa vào model theo purpose tối thiểu.

## Pitfalls

- Policy cá nhân `AUTOMATE` không phải giấy phép bỏ qua consent.
- Append-only audit không hữu ích nếu actor/provenance thiếu.
- Tool registry chỉ có manifest nhưng executor bypass registry vẫn không an toàn.
- Mock receipt không chứng minh side effect thật đã xảy ra.

## Verification

- [ ] DENY không có đường bypass.
- [ ] Missing policy/consent fail closed.
- [ ] User declaration thắng derived candidate.
- [ ] Retry cùng idempotency key không lặp side effect.
- [ ] Revoke/expiry có hiệu lực ngay.
- [ ] Transaction failure không để state terminal nửa chừng.
