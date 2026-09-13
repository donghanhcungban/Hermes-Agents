---
name: evidence-driven-delivery
description: "Use when shipping non-trivial software changes."
version: 0.3.0
author: seeker19110, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delivery, specification, evidence, quality-gates, brownfield]
    related_skills: [master-software-engineering, incremental-implementation, source-driven-development, test-driven-development]
---

# Evidence-Driven Delivery

Dùng quy trình này cho thay đổi phần mềm không tầm thường để biến yêu cầu thành kết quả có thể kiểm chứng, thay vì chỉ tạo code “trông hợp lý”. Skill không ép một stack hoặc scaffold; stack, lệnh kiểm tra và cổng chất lượng phải được suy ra từ repo thực tế rồi xác minh.

## When to Use

- Tính năng mới, thay đổi nhiều file, refactor có rủi ro, tích hợp, migration, hoặc chuẩn bị phát hành.
- Bắt đầu dự án mới, tiếp quản dự án có sẵn, hoặc khi yêu cầu chưa có acceptance criteria rõ.
- Khi cần chứng minh thay đổi đã chạy đúng, không chỉ báo cáo code đã được viết.
- Không dùng cho sửa chính tả, format thuần túy, hoặc thay đổi một dòng có hành vi hiển nhiên từ yêu cầu trực tiếp của người dùng.

## Principles

1. **Research trước lựa chọn.** Không suy ra stack, phiên bản, lệnh build/test hay API từ thói quen. Đọc repo; với quyết định công nghệ mới, kiểm tra tài liệu chính thức hiện hành.
2. **Brownfield tôn trọng hiện trạng.** Đo baseline trước; bổ sung hàng rào theo lát nhỏ và có rollback. Không rewrite/đổi stack hàng loạt chỉ để giống một template.
3. **Một nguồn sự thật cho mỗi loại trạng thái.** Spec giữ contract; Git/PR/CI giữ evidence thực thi; tài liệu tiến độ chỉ tóm tắt và phải đối chiếu Git trước khi tin.
4. **Không feature code trước contract đủ rõ.** Với thay đổi có hành vi mới hoặc rủi ro đáng kể, cần scope, non-goal, AC, rủi ro và approval rõ trước implementation. Sửa nhỏ theo yêu cầu trực tiếp được coi là contract tối giản nếu hành vi và tiêu chí pass đã rõ.
5. **Gate xanh là bằng chứng có phạm vi.** Lint của template không chứng minh app build đúng; unit test không chứng minh rollout an toàn. Chỉ tuyên bố điều mà command, CI, test, hoặc quan sát thực sự chứng minh.
6. **Không làm xanh bằng cách làm yếu hàng rào.** Không xóa test, hạ threshold, nới auth/validation hay bỏ qua lỗi để đổi kết quả gate.
7. **Cổng tỷ lệ với blast radius.** Dùng artifact nhỏ nhất vẫn đủ để kiểm soát rủi ro; không biến sửa typo thành feature program, cũng không xem feature lớn như một sửa nhỏ.
8. **Profile là tham chiếu, không phải mặc định ép buộc.** Chọn cổng theo sản phẩm và môi trường mục tiêu: Web/UI, backend/API, mobile/desktop, CLI/SDK, data/ML/AI, plugin/host integration, hoặc monorepo có failure mode khác nhau.

## Risk Control Level (R0–R3)

| Mức | Ví dụ | Contract tối thiểu | Xác minh trước hoàn tất |
| --- | --- | --- | --- |
| R0 — Cơ học | typo, format, đổi tên không ảnh hưởng hành vi | yêu cầu trực tiếp + phạm vi file | diff và command rẻ nhất liên quan, nếu có |
| R1 — Thay đổi nhỏ | bug cục bộ, UI copy, config an toàn | behavior/AC ngắn + regression expectation | targeted test hoặc manual check có thể lặp lại |
| R2 — Feature/risk vừa | nhiều file, API nội bộ, refactor, thay đổi workflow | mini spec: user/outcome, scope/non-goal, AC, touchpoint, test plan | targeted + required repo gates, self-review |
| R3 — High impact | auth, payment, data thật, migration, public API, release, AI autonomy | feature spec đầy đủ + ADR/approval khi có trade-off | integration/e2e phù hợp, security/risk review, rollout/rollback và evidence vận hành |

Nâng một mức khi không chắc blast radius. Không dùng R0/R1 để lách approval cho R2/R3; không bắt R3 cho một thay đổi R0 đã rõ. Ký hiệu R dành cho risk tier; ký hiệu C dành cho profile loại dự án.

## Delivery Lifecycle — 9 Gates

Dùng một luồng duy nhất; không tạo quy trình song song theo cảm tính:

| Gate | Mục tiêu | Điều kiện qua cổng |
| --- | --- | --- |
| Frame | Chốt vấn đề, người dùng, outcome, metric, guardrail, non-goal. | Có project/goal draft. |
| Research | Kiểm chứng code, data, nguồn, alternatives và unknowns. | Evidence đủ cho quyết định. |
| Approve | Duyệt contract/spec theo mức rủi ro. | Không còn quyết định blocking. |
| Plan | Chia slice, dependency, test, rollout/rollback và budget. | Slice đạt Definition of Ready. |
| Build | Làm một outcome trên branch/PR tập trung. | Draft PR có test cùng code. |
| Verify | Chạy gate, self-review và risk audit. | Evidence cho mọi AC. |
| Integrate | Review/CI xanh, merge/release theo quyền. | Thay đổi vào main/release có kiểm soát. |
| Observe | Theo dõi health, metric, cost, feedback và reconciliation. | Có evidence sau phát hành. |
| Reconcile | So outcome với goal, ghi gap và chọn lát tiếp theo. | Goal complete hoặc next slice rõ. |

Một iteration chỉ có **một outcome + một PR**. Nếu đang chờ CI, review, merge hoặc approval, trạng thái là `WAITING`; nếu thiếu thông tin/quyền/decision để tiến hành an toàn, là `BLOCKED` — không tự suy đoán để vượt cổng.

## Procedure

### 1. Phân loại đường đi và discovery

Chọn một đường:

- **Greenfield:** vấn đề → research → project contract → foundation → feature loop → release/observe.
- **Brownfield:** inventory → baseline → gap/risk → incremental adoption → feature loop.
- **Một feature:** đi thẳng vào contract, rồi slice/implement/verify.

Đọc trước khi hỏi người dùng: manifest/lockfile, config, script, CI, test, schema/migration, biến môi trường, cấu trúc source và tài liệu dự án. Lập bảng ngắn: *đã có / thiếu / chưa xác minh / rủi ro*. Chỉ hỏi về mục tiêu nghiệp vụ, ưu tiên, trade-off hoặc quyền hạn không thể suy ra từ repo.

**Hoàn thành khi:** stack, phiên bản liên quan, lệnh thật, baseline và các unknown blocking đều được ghi rõ hoặc đã hỏi.

### 2. Research và contract tỷ lệ với rủi ro

Trước quyết định khó đảo ngược (stack, data model, public API, auth, migration, rollout), lấy nguồn chính thức đúng phiên bản và so sánh alternatives. Ghi ADR hoặc phần “Decision” trong spec với: quyết định, lý do, alternatives không chọn, hệ quả và rollback/migration.

Với feature, tạo hoặc cập nhật spec/issue/PR description có tối thiểu:

- user/problem, outcome đo được, baseline/target và guardrail;
- scope, non-goal, dependency, dữ liệu/API/UI states;
- acceptance criteria map tới test hoặc cách quan sát;
- security, privacy, a11y, hiệu năng, reliability, cost và failure modes phù hợp;
- rollout, telemetry/reconciliation và rollback nếu thay đổi có tác động vận hành;
- ai phê duyệt và thời điểm phê duyệt khi cần quyết định sản phẩm/kiến trúc.

Không code feature khi còn quyết định blocking chưa được duyệt. Dừng để hỏi với thao tác phá hủy/khó đảo ngược, dữ liệu thật, secrets, payment, security-sensitive behavior, quyền deploy/merge, hoặc trade-off sản phẩm quan trọng.

**Hoàn thành khi:** không còn assumption blocking; acceptance criteria đủ để một reviewer xác định pass/fail.

### 3. Chọn lát thực thi

Chọn một lát tạo ra một outcome hoàn chỉnh hoặc giảm rủi ro lớn nhất. Giữ mỗi PR/commit tập trung, độc lập rollback được và không phụ thuộc vào base chưa merge nếu có thể tránh. Ưu tiên vertical slice; dùng contract-first cho boundary nhiều tầng và risk-first cho unknown lớn.

Tạo Definition of Ready trước code:

- contract approved hoặc yêu cầu trực tiếp đã đủ rõ;
- dependency và owner rõ;
- test strategy và lệnh xác minh thật đã biết;
- migration/rollout/rollback đã xác định nếu có;
- không có blocker cần người dùng quyết.

**Hoàn thành khi:** lát có phạm vi hữu hạn và một tiêu chí kết quả kiểm thử được.

### 4. Implement trong vòng lặp chặt

Cho từng hành vi: viết test tái hiện/failing test trước nếu áp dụng, chạy để xác nhận nó fail đúng nguyên nhân, thực hiện thay đổi nhỏ nhất, rồi chạy targeted verification. Giữ đúng convention sẵn có; validate input ở boundary; giữ thay đổi additive và idempotent với migration/automation nhạy cảm.

Sau mỗi increment có thay đổi code, chạy các command thực của repo liên quan (không bịa lệnh). Chỉ chạy full suite/gate khi scope hoặc policy yêu cầu; không lặp lại một command trên code không đổi chỉ để trấn an.

**Hoàn thành khi:** acceptance criteria của lát có evidence, code vẫn buildable và không còn thay đổi ngoài scope bị trộn vào.

### 5. Repair dựa trên nguyên nhân gốc

Khi gate đỏ: ghi failure thực tế và giả thuyết; sửa nguyên nhân nhỏ nhất; chạy lại test fail và gate liên quan. Với cùng một failure, tối đa ba vòng repair độc lập. Sau ba lần hoặc khi evidence mâu thuẫn, dừng ở `BLOCKED` với log ngắn gồm error, những gì đã thử và quyết định cần thiết.

Không coi retry mù, disable check hoặc sửa test để khớp implementation là repair.

**Hoàn thành khi:** gate pass có output thực, hoặc blocker được nêu đủ để người dùng quyết.

### 6. Verify trước commit/PR/release

Áp dụng Definition of Done theo profile dự án:

- implementation khớp contract; deviation được ghi và duyệt;
- AC có evidence; test mới chứng minh behavior/bug;
- targeted và required quality gates đều xanh;
- authz, validation, privacy, concurrency/idempotency và error recovery đã được xét khi phù hợp;
- docs, contracts, migrations, ADR, telemetry/runbook được cập nhật khi bị ảnh hưởng;
- không có secret, production data, debug artifact hoặc generated output ngoài ý muốn;
- review findings đã xử lý hoặc có trade-off được chấp nhận.

Trước khi tin file tiến độ, branch hay PR status, đối chiếu nó với Git/remote/CI hiện tại. Sau merge/release, cập nhật trạng thái ngay và đo lại outcome/guardrail nếu scope có metric.

**Hoàn thành khi:** bằng chứng đáp ứng từng AC và claim cuối cùng không vượt quá phạm vi evidence.

## Brownfield Adoption Order

1. Inventory và baseline: chạy lệnh hiện có, ghi debt/gap thay vì che chúng.
2. Hàng rào không đổi hành vi: format trong commit riêng; lint/type-check tăng dần; hooks chỉ áp file sửa; CI dùng lệnh thật của stack.
3. Chất lượng theo rủi ro: test luồng quan trọng/hay đổi trước; mỗi bug có regression test; baseline a11y/performance/coverage rồi chỉ siết dần.
4. Vận hành thường xuyên: feature mới dùng DoR → DoD; refactor theo “đụng đâu dọn đó”; quyết định lớn qua research + ADR.

Không áp scaffold, profile Web, stack hay strict threshold vì template có sẵn chúng. Với host/plugin (Revit, AutoCAD, IDE, desktop host), discovery phải thêm: phiên bản host/API hỗ trợ, contract của host, môi trường chạy thật, compatibility matrix, hành vi khi host unavailable và đường thử nghiệm có host/sandbox thật.

Không thêm CI/template chỉ để có badge: xác minh job đó chạy build/test/lint của ứng dụng, có quyền cần thiết và tác nhân tạo PR (kể cả bot) thực sự có thể làm check xanh.

## Artifact Hygiene and Freshness

Chỉ tạo artifact khi nó có một consumer và một nguồn sự thật rõ. Không copy cùng state vào PROJECT, progress, spec, issue và PR. Trước khi dùng state có nhánh/SHA/PR/CI, đối chiếu nguồn sống; sau merge/release cập nhật summary ngay trong cùng thay đổi nếu nó bị tác động.

Template/drop-in, workflow và script phát hành phải có verification path thật với môi trường đích. Static parse, YAML review hay unit test đơn lẻ không chứng minh integration, quyền CI, version drift hoặc host compatibility. Thêm smoke/integration test phù hợp, và với dependency/latest-sensitive template thì có lịch chạy định kỳ cùng việc xem lại failure.

## Evidence Report

Khi kết thúc, báo cáo ngắn theo mẫu:

```text
Delivered: <outcome>
Evidence: <tests/build/CI/manual/metric đã chạy và kết quả>
Risk or limitation: <còn lại, hoặc none đã xác minh>
Status: COMPLETE | WAITING | BLOCKED
```

Không ghi “đã hoàn thành” nếu đang chờ CI/review/approval; dùng `WAITING`. Không suy ra quyền merge/deploy từ quyền sửa code.

## Pitfalls

- Bắt người dùng khai stack/lệnh mà repo có thể tự cho biết.
- Áp scaffold hoặc strict gate ngay lập tức lên repo cũ; phải baseline và tăng dần.
- Tin tài liệu trạng thái cũ mà không đối chiếu branch/SHA/PR thật.
- Claim “production-ready”, “secure”, “compliant”, hoặc “complete” khi chưa có evidence tương ứng.
- Cổng chỉ được đọc YAML/chạy local; integration, permission và bot compatibility thường chỉ lộ khi chạy PR thật.
- Test harness/drop-in chưa từng compile với môi trường mục tiêu; luôn thêm smoke/integration path thật khi phát hành template.

## Provenance and Sources

Đã đối chiếu trực tiếp repository tại commit `a41ed632403460625001ae6146f2a0e2e035a35e` (`main`, commit lúc `2026-09-13T02:33:31Z`; kiểm tra ngày `2026-09-13`). Repository dùng MIT License, copyright © 2026 `seeker19110`.

Phần lấy trực tiếp về mặt nguyên tắc từ project-template: Greenfield/Brownfield routing, lifecycle 9 gate, feature approval, một outcome/PR, giới hạn repair ba lần, evidence discipline, freshness và traps. Phần mở rộng riêng của skill: R0–R3 proportional control và profile host/plugin cho Revit/AutoCAD/IDE; đây không phải tuyên bố rằng repository nguồn có sẵn các profile đó.

Nguồn theo đúng snapshot đã kiểm tra:

- https://github.com/seeker19110/project-template/blob/a41ed632403460625001ae6146f2a0e2e035a35e/docs/framework/standard-delivery.md
- https://github.com/seeker19110/project-template/blob/a41ed632403460625001ae6146f2a0e2e035a35e/docs/framework/quickstart.md
- https://github.com/seeker19110/project-template/blob/a41ed632403460625001ae6146f2a0e2e035a35e/docs/framework/existing-project-adoption.md
- https://github.com/seeker19110/project-template/blob/a41ed632403460625001ae6146f2a0e2e035a35e/docs/framework/03-tech-selection-and-proactive-advice.md
- https://github.com/seeker19110/project-template/blob/a41ed632403460625001ae6146f2a0e2e035a35e/TRAPS.md
- https://github.com/seeker19110/project-template/blob/a41ed632403460625001ae6146f2a0e2e035a35e/LICENSE

Khi cập nhật skill từ repository trong tương lai, lấy HEAD mới, đọc diff từ commit trên và chỉ nhận thay đổi sau khi kiểm tra chúng không làm yếu các invariant hiện tại.

## Verification

- [ ] Đường Greenfield/Brownfield/feature đã chọn theo hiện trạng thật.
- [ ] Mức R0–R3 đã được chọn theo blast radius; scope nhỏ không bị over-process và scope lớn không lách gate.
- [ ] Stack, versions, scripts và baseline đã được discovery thay vì đoán.
- [ ] Cổng chất lượng được chọn theo profile và môi trường đích; không áp profile Web/scaffold mặc định lên brownfield.
- [ ] Feature/rủi ro đáng kể có contract, AC và approval phù hợp trước code.
- [ ] Mỗi claim hoàn thành có evidence tương ứng từ command/CI/quan sát.
- [ ] Với template, CI, drop-in hoặc host integration: có đường verify thực, không chỉ static check.
- [ ] Không có gate bị làm yếu để đạt trạng thái xanh.
- [ ] Artifact state có consumer/nguồn sự thật rõ; state sau PR/merge/release đã được đối chiếu và cập nhật.
