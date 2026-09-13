# Model Catalog & Credential Pool Checklist

## Discovery cache

- Tách TTL (độ mới catalog) khỏi minimum refresh interval (chống burst).
- Unknown model: refresh cưỡng bức có giới hạn sau minimum interval.
- Sau lỗi discovery, giữ safe static catalog; không xóa catalog tốt gần nhất.
- Dùng lock/task coalescing để caller đồng thời cùng chờ một refresh.

## Entitlement routing

- Key capability theo stable account/project ID, không dùng token làm key persistent.
- Public catalog = union các capability đã validate.
- Chọn account hỗ trợ model trước khi gửi request.
- 400/404 chỉ thêm negative capability cho model đó; không gọi account-wide cooldown.
- Khi không còn account hỗ trợ model, trả lỗi rõ ràng thay vì map âm thầm sang default khác.

## Refresh endpoint safety

- Chỉ bind loopback mặc định và xác nhận request local; nếu remote binding được hỗ trợ, yêu cầu auth riêng.
- Không tin `?refresh=1` như bypass TTL. Áp minimum interval và coalesce.
- Với CLI subprocess, đặt timeout hợp lý và không spawn process song song cho cùng refresh.

## Evidence before release

- Test non-stream và stream.
- Test cache cold/warm/concurrent.
- Test entitlement heterogeneity và retention after unsupported response.
- Test HTTP handler policy cho refresh.
- Run full suite, diff check, secret scan, independent review.
