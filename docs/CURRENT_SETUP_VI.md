# Cấu hình vận hành hiện tại: proxy, xoay tài khoản và skill

Tài liệu này ghi lại phần cấu hình có thể chia sẻ an toàn của môi trường Hermes đã kiểm chứng. Các token OAuth, API key, email tài khoản và cookie không nằm trong repository.

## Kiến trúc

```text
Hermes
  -> antigravity @ 127.0.0.1:8100/v1
       -> model fallback trong cùng tài khoản
       -> xoay qua pool Google OAuth còn khả dụng
  -> fallback_providers của Hermes
       -> OpenAI Codex
       -> các mức Gemini Antigravity
       -> Anthropic
       -> OpenAI Codex model khác
       -> OpenCode Free
```

- Pool OAuth được lưu cục bộ tại `$HERMES_HOME/auth/antigravity_tokens.json`.
- Môi trường đã kiểm chứng có **3 tài khoản**, nhưng repository chỉ ghi số lượng, không ghi email hay token.
- Khi toàn bộ pool nhận 429, Hermes tiếp tục theo `fallback_providers`.
- `compression.threshold: 0.7` nén context trước khi fallback sang model có cửa sổ context nhỏ hơn.

## Tự phát hiện model mới

Bridge không còn phụ thuộc hoàn toàn vào danh sách model đóng cứng:

- `GET /v1/models` gọi `v1internal:fetchAvailableModels`, xác thực payload và hợp nhất model mới vào catalog runtime.
- `GET /v1/claude-code/models` đọc model/alias mà bản Claude Code CLI đang cài quảng bá qua `claude --help`.
- Catalog được cache 5 phút; thêm `?refresh=1` để ép làm mới ngay, không cần sửa mã nguồn hay khởi động lại bridge.
- Hermes cũng cache catalog endpoint; dùng `hermes model --refresh` khi cần thấy model mới ngay trong picker.
- Nếu upstream discovery lỗi, bridge giữ catalog tốt gần nhất/danh sách an toàn đóng gói sẵn thay vì làm hỏng chat.

## Pool nhiều tài khoản theo provider

Chính sách chuẩn là `fill_first`: tiếp tục dùng tài khoản ưu tiên; chỉ chuyển sang tài khoản kế tiếp khi gặp quota, rate-limit hoặc lỗi xác thực. Hermes quản lý pool chung trong `auth.json`; riêng Antigravity quản lý pool Google OAuth trong `auth/antigravity_tokens.json`.

| Provider | Cách thêm nhiều credential/instance | Ghi chú |
|---|---|---|
| Antigravity | Chạy `manage.py login` lặp lại | Bridge xoay nội bộ theo thứ tự |
| OpenAI Codex | `hermes auth add openai-codex` lặp lại | OAuth, Hermes tự xoay pool |
| Anthropic API/OAuth | `hermes auth add anthropic` lặp lại (OAuth, mặc định); dùng `hermes auth add anthropic --type api-key` cho API key | Prompt nhập key/token được che; không truyền secret trên command line |
| Groq | Khai báo provider `groq`, rồi chạy `hermes auth add groq` lặp lại | Mỗi API key là một credential trong pool |
| Ollama | Khai báo nhiều provider/URL như `ollama-lan-1`, `ollama-lan-2` và thêm từng instance vào fallback | Ollama không có tài khoản/API quota; đơn vị failover đúng là server instance |
| OpenCode Free | Không cần credential | Keyless nên không có pool tài khoản |

Đặt chiến lược tuần tự cho các pool do Hermes quản lý:

```yaml
credential_pool_strategies:
  openai-codex: fill_first
  anthropic: fill_first
  groq: fill_first
```

Kiểm tra pool mà không in secret:

```bash
hermes auth list
hermes auth status openai-codex
hermes auth status anthropic
hermes auth status groq
```

## Áp dụng cấu hình

File [`config/hermes-rotation.example.yaml`](../config/hermes-rotation.example.yaml) là mẫu tối giản đã loại bí mật. Không ghi đè toàn bộ `config.yaml` của người dùng. Nên dùng `hermes config set`, `hermes model` và picker `hermes fallback add/remove` để cập nhật có kiểm soát.

Cài plugin và các skill đi kèm:

```bash
python install.py
python "$HERMES_HOME/bridge/antigravity/manage.py" login
python "$HERMES_HOME/bridge/antigravity/manage.py" login  # lặp lại cho từng tài khoản bổ sung
python "$HERMES_HOME/bridge/antigravity/manage.py" status
```

## Skill được đóng gói

| Skill | Mục đích |
|---|---|
| `antigravity-oauth-bridge` | Cài đặt, đăng nhập, chạy bridge và chẩn đoán xoay tài khoản |
| `hermes-provider-management` | Quản lý provider, fallback picker, credential pool và context compression |
| `project-harness-engineering` | Thiết kế/audit harness cho dự án dùng coding agent |

`install.py` đồng bộ các skill trên vào `$HERMES_HOME/skills/<tên-skill>/`, thay thế đúng skill cùng tên và giữ nguyên skill khác của người dùng.

## Kiểm tra

```bash
curl http://127.0.0.1:8100/health
curl http://127.0.0.1:8100/v1/models
hermes fallback list
python -m unittest discover -s tests -p "test_*.py" -v
```

## Dữ liệu tuyệt đối không đồng bộ

- `$HERMES_HOME/auth/antigravity_tokens.json`
- `$HERMES_HOME/.env`
- access token, refresh token, cookie, API key thật
- log bridge có thể chứa email hoặc metadata tài khoản
