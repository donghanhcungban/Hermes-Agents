---
name: antigravity-oauth-bridge
description: "Plugin Antigravity OAuth: Tự động chuyển đổi/xoay tài khoản Gemini/Claude."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [antigravity, oauth, model-provider, plugin, gemini, claude, failover, multi-account]
    related_skills: [hermes-agent, native-mcp]
---

# Plugin Antigravity OAuth Bridge cho Hermes Agent

## Khi nào cần dùng

Sử dụng khi người dùng muốn cài đặt, cấu hình, hoặc gỡ lỗi plugin **Antigravity OAuth model-provider** cho Hermes Agent, hoặc muốn thêm/xoay nhiều tài khoản Google để sử dụng hạn ngạch (quota) tốt hơn.

Plugin này cho phép Hermes Agent gọi các mô hình AI cao cấp như Gemini 3.7/3.6/3.5/3.1, Claude Sonnet/Opus 4.6, và GPT-OSS 120B thông qua đăng nhập **Google Antigravity IDE OAuth** (sử dụng hạn ngạch miễn phí hoặc trả phí đi kèm tài khoản của bạn, không cần mua API key riêng lẻ). Nó hoạt động bằng cách chạy một HTTP Bridge cục bộ (`127.0.0.1:8100`) tương thích với OpenAI Chat Completions API và dịch ngược request sang endpoint Code Assist nội bộ của Google.

## Cài đặt (Install)

```bash
python install.py
```

Lệnh này sẽ sao chép các thư mục tương ứng:
- `plugin/` → `$HERMES_HOME/plugins/model-providers/antigravity/` (Đăng ký provider `antigravity` với model picker của Hermes).
- `bridge/` → `$HERMES_HOME/bridge/antigravity/tools/antigravity_bridge/` (Mã nguồn chạy server bridge, OAuth và dịch request).
- `manage.py` → `$HERMES_HOME/bridge/antigravity/manage.py` (CLI quản lý).

Nếu chạy từ bên trong thư mục git clone của hermes-agent, nó cũng tự động đồng bộ vào các thư mục dev cục bộ để kiểm thử trực tiếp.

## Đăng nhập (Một hoặc nhiều tài khoản Google)

```bash
python "$HERMES_HOME/bridge/antigravity/manage.py" login
```

Trình duyệt sẽ mở trang Google OAuth PKCE. **Chạy lại lệnh `login` cho từng tài khoản Google bổ sung** mà bạn muốn thêm vào pool xoay vòng (chọn "Sử dụng tài khoản khác" trên trình duyệt). Mọi đăng nhập thành công sẽ được lưu trữ (theo email) vào file cấu hình tài khoản `$HERMES_HOME/auth/antigravity_tokens.json`. Cấu hình từ 2-3 tài khoản Google là lý tưởng cho nhu cầu cá nhân.

```bash
python "$HERMES_HOME/bridge/antigravity/manage.py" status   # Xem tài khoản chính + trạng thái token
python "$HERMES_HOME/bridge/antigravity/manage.py" start    # Khởi động bridge daemon tại cổng 8100
python "$HERMES_HOME/bridge/antigravity/manage.py" stop     # Dừng bridge daemon
```

Plugin tự động kích hoạt Bridge khi sử dụng qua hàm hook `ensure_antigravity_bridge_running()`, do đó bạn không cần khởi động Bridge thủ công thường xuyên.

## Tự động chuyển đổi nhà cung cấp ngoài (Cross-provider auto-failover)

Script `install.py` (hoặc `manage.py setup`) tự động thiết lập chuỗi `fallback_providers` trong cấu hình của Hermes để tự động dự phòng nếu toàn bộ tài khoản Google trong pool của bạn bị hết hạn ngạch:

```
Chính:    antigravity (gemini-3.7-flash) — Xoay vòng nội bộ tài khoản Google trước
Dự phòng 1: openai-codex (gpt-5-codex)
Dự phòng 2: anthropic (claude-sonnet-4-6)
```

Quy trình xử lý lỗi tự động không cần người dùng can thiệp:
1. Tài khoản Google #1 bị lỗi 429 hoặc hết quota.
2. Bridge tự động xoay sang tài khoản Google #2, #3 trong pool.
3. Khi toàn bộ tài khoản Google trong pool hết quota:
   * Kích hoạt cơ chế fallback của Hermes chuyển sang `openai-codex`.
   * Nếu `openai-codex` cũng lỗi hoặc rate limit, chuyển tiếp sang `anthropic`.

Cơ chế này được thực thi bởi hàm `configure_priority_fallback_preserving_existing_primary` trong `manage.py`, chỉnh sửa trực tiếp `$HERMES_HOME/config.yaml`. Nó không đè hoặc nhân bản các fallback có sẵn của người dùng.

Tùy chỉnh khi cài đặt:
```bash
python manage.py setup-free                       # Cấu hình 100% Zero-Cost Free Tier (Google Antigravity -> Groq Cloud Free -> Ollama Offline)
python manage.py setup --free-tier                # Tương đương lệnh trên
python manage.py setup --no-fallback              # Chỉ dùng antigravity làm chính, không tạo chuỗi dự phòng
python manage.py setup --as-fallback-only         # Giữ provider chính hiện tại của bạn, chỉ THÊM chuỗi dự phòng antigravity + openai-codex + anthropic
python manage.py setup --groq-model llama-3.3-70b-versatile     # Thêm Groq Cloud sau anthropic (vẫn cần mạng)
python manage.py setup --ollama-model qwen2.5-coder:7b          # Thêm Ollama LOCAL làm nấc dự phòng CUỐI CÙNG (offline)
# Có thể dùng chung: antigravity -> openai-codex -> anthropic -> groq -> ollama
```

**Chế độ Free Tier "0 Đồng" (`setup-free` / `--free-tier`):** Thiết lập chuỗi dự phòng hoàn toàn miễn phí không đòi hỏi thẻ tín dụng hay tài khoản trả phí:
1. `antigravity` (`gemini-3.7-flash` chính, xoay vòng tài khoản Google OAuth).
2. `antigravity` (`gemini-3.7-flash-medium`, `gemini-3.5-flash` dự phòng nội bộ).
3. `groq` (`llama-3.3-70b-versatile` qua Groq Cloud Free API - đăng ký miễn phí tại `https://console.groq.com`).
4. `ollama` (`qwen2.5-coder:7b` chạy offline trực tiếp trên máy qua Ollama - hoàn toàn 0đ).

**Groq Cloud (tùy chọn, KHÔNG bật mặc định trong chuỗi trả phí):** cũng không phải provider xây sẵn của Hermes — nó ánh xạ theo *host* của `base_url` (`api.groq.com` → biến môi trường `GROQ_API_KEY`, xem `hermes_cli/runtime_provider.py::_host_derived_api_key`), nên chỉ cần điền `GROQ_API_KEY` vào `~/.hermes/.env`, không phải khai gì thêm trong `config.yaml`. `manage.py` gắn nó **sau** `anthropic` — Groq nhanh/rẻ nhưng vẫn là dịch vụ trên mạng, không dùng được khi offline, nên đứng trước Ollama chứ không phải nấc cuối.

**Ollama local làm nấc dự phòng cuối cùng (tùy chọn, KHÔNG bật mặc định):** Hermes không có provider "ollama" xây sẵn — nó ánh xạ "ollama" sang provider chung `custom` (endpoint OpenAI-compatible tự khai `base_url`), và tự điền `api_key="no-key-required"` cho endpoint local không cần xác thực (xem `hermes_cli/runtime_provider.py` trong mã nguồn Hermes) — không cần biến môi trường nào thêm. `manage.py` gắn nó vào SAU CÙNG, sau cả `groq`: model 7B chạy local **không đủ tin cậy để điều phối** (gọi tool nhiều bước, tuân thủ JSON Schema) so với antigravity/openai-codex/anthropic/groq, nên chỉ nên dùng khi TẤT CẢ nấc trên mạng đều lỗi hoặc máy đang offline hoàn toàn. Yêu cầu `ollama serve` đang chạy và đã `ollama pull <model>` model tương ứng.

Bạn cũng có thể điều chỉnh bất kỳ lúc nào bằng CLI của Hermes:
```bash
hermes fallback list      # Liệt kê chuỗi dự phòng hiện tại
hermes fallback remove    # Xóa một cấu hình dự phòng
hermes fallback clear     # Xóa toàn bộ chuỗi dự phòng
hermes fallback add       # Thêm cấu hình dự phòng mới bằng giao diện tương tác
```

## Tự động xoay tài khoản & model nội bộ (Failover hoạt động thế nào)

Cơ chế xoay vòng tài khoản và model được cài đặt trong `AntigravityAuthManager` (`bridge/auth.py`) và `AntigravityClient` (`bridge/client.py`):

1. **In-Account Model Fallback (Tính năng mới)**: Khi request mô hình chính (`gemini-3.7-flash`) bị lỗi hết quota (HTTP 429 / RESOURCE_EXHAUSTED) trên một tài khoản, bridge sẽ tự động thử mô hình dự phòng (`claude-sonnet-4-6`) trên **cùng tài khoản đó** trước khi quyết định chuyển sang tài khoản Google khác. Điều này do Gemini và Claude sử dụng hạn ngạch độc lập trên cùng một tài khoản Antigravity.
2. **Xoay tài khoản Google**: Nếu cả hai mô hình trên tài khoản hiện tại đều không sử dụng được, bridge sẽ tìm tài khoản tiếp theo không nằm trong thời gian cooldown để thực hiện request (cả chế độ thường lẫn streaming).
3. **Thời gian Cooldown**: Lỗi 401 → Cooldown 5 phút; Lỗi 402/403/429 → Cooldown 1 giờ (hoặc theo header `Retry-After` từ server); Các lỗi khác → 60 giây. Trạng thái cooldown được lưu trên đĩa cứng (`unavailable_until`) để duy trì ngay cả khi khởi động lại bridge.
4. **Endpoint Fallback**: Nếu gặp lỗi hệ thống `5xx` từ endpoint chính, bridge sẽ thử gọi endpoint dự phòng (`cloudcode-pa.googleapis.com`) với cùng tài khoản trước khi xoay tài khoản, tránh việc lãng phí thời gian cooldown do lỗi mạng tạm thời.

## Kiểm tra hoạt động (Verifying it works)

```bash
export ANTIGRAVITY_API_KEY=antigravity-local-token   # Giá trị bất kỳ không rỗng
hermes chat -q "Phản hồi chính xác chữ: OK" --provider antigravity -m gemini-3.7-flash
```

Hoặc gọi trực tiếp vào Bridge cục bộ:
```bash
curl http://127.0.0.1:8100/health
curl http://127.0.0.1:8100/v1/models       # Trả về 9 models khả dụng
curl http://127.0.0.1:8100/auth/status     # Trạng thái đăng nhập, email, thời hạn token
```

## Danh mục mô hình (9 IDs khớp với Antigravity IDE thật)

`gemini-3.7-flash`, `gemini-3.7-flash-medium`, `gemini-3.7-flash-low`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.1-pro`, `claude-sonnet-4-6`, `claude-opus-4-6`, `gpt-oss-120b`. 

*(Lưu ý: Không tồn tại mô hình `gemini-3.7-pro` trên hệ thống thật nên mô hình này đã bị loại bỏ).*

## Một số điểm lưu ý (Pitfalls)

- **Đường dẫn import trên Windows**: Tiến trình daemon bridge khởi động qua `manage.py start` cần xác định đúng đường dẫn import của `bridge` tùy vào việc chạy từ thư mục cài đặt hay thư mục source code. Nếu bridge không khởi động được, hãy kiểm tra file log tại `$HERMES_HOME/logs/antigravity_bridge.log`.
- **is_expired**: Thuộc tính `AntigravityCredentials.is_expired` là một **property**, không phải method — gọi không kèm cặp ngoặc đơn `()`.
- **Cấu hình ProviderProfile**: Để Hermes nhận diện provider qua CLI/Dashboard, `auth_type` bắt buộc phải là `"api_key"` với biến môi trường giả lập là `env_vars=("ANTIGRAVITY_API_KEY",)`, dù thực tế quá trình xác thực OAuth được xử lý hoàn toàn bên trong bridge cục bộ.
- **Rủi ro sử dụng**: Đây là plugin bên thứ ba sử dụng API nội bộ `v1internal` của Google. Sử dụng với tần suất quá cao (24/7 qua gateway) có thể dẫn đến rủi ro bị hạn chế tài khoản từ phía Google.

## 🌟 Cổng Chất Lượng Thượng Thừa (Supreme Quality Gate)

Khi vận hành kỹ năng này, agent phải tuân thủ nghiêm ngặt các nguyên tắc sau:
1. **Tuyệt đối không đoán mò**: Không bao giờ tự bịa ra dữ liệu, nội dung file hay kết quả kiểm thử. Mọi báo cáo phải dựa trên output thực tế từ công cụ.
2. **Kiểm tra trước khi sửa**: Luôn sử dụng `read_file`/`search_files` để xác minh nội dung hiện tại và cấu trúc thư mục trước khi sửa đổi.
3. **Sửa đổi targeted**: Ưu tiên dùng `patch` (thay vì ghi đè hoàn toàn bằng `write_file`) cho các chỉnh sửa cục bộ để giữ lại cấu hình nguyên bản và tránh lỗi cú pháp không mong muốn.
4. **Xác minh đầu ra**: Sau khi chỉnh sửa code hoặc tệp cấu hình, bắt buộc phải chạy bộ test suite hoặc lệnh build/compile để kiểm tra tính đúng đắn.
5. **Tối ưu hóa token**: Giới hạn phạm vi đọc tệp bằng cách sử dụng `offset` và `limit` để tiết kiệm token ngữ cảnh.
