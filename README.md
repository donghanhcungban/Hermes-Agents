# Plugin Google Antigravity OAuth cho Hermes Agent

Plugin model-provider + local OAuth bridge cho [Hermes Agent](https://github.com/NousResearch/hermes-agent).
Giúp Hermes Agent gọi các mô hình AI cao cấp: Gemini 3.7/3.6/3.5/3.1, Claude Sonnet/Opus 4.6, và GPT-OSS 120B thông qua đăng nhập **Google Antigravity IDE** OAuth. Hỗ trợ tự động **xoay tài khoản** (multi-account failover) khi bị giới hạn rate limit/hết hạn ngạch (quota) và tự động chuyển đổi model dự phòng trong cùng một tài khoản (in-account model fallback).

Xem hướng dẫn chi tiết tại [`README_DETAILED_VI.md`](README_DETAILED_VI.md), bản tổng hợp cấu hình đang dùng tại [`docs/CURRENT_SETUP_VI.md`](docs/CURRENT_SETUP_VI.md), và các skill trong thư mục [`skills/`](skills/).

## Claude Code gói tháng (CLI local)

Plugin cũng có provider `claude-code-cli`: Hermes gọi `claude -p` trên chính máy cục bộ và dùng phiên đăng nhập Claude Code subscription, **không cần `ANTHROPIC_API_KEY`**. Claude Code bị chạy với `--tools ""`; mọi tool call vẫn do Hermes quyết định và thực thi.

```bash
claude auth login
python manage.py setup-claude-code --model sonnet  # hoặc opus / haiku
hermes chat -q "Phản hồi chính xác chữ: OK" --provider claude-code-cli -m sonnet
```

## 📌 Tính Năng Mới (v1.0)
- **🔄 In-Account Model Fallback**: Tự động thử model dự phòng (`claude-sonnet-4-6`) trên cùng một tài khoản Google khi model chính (`gemini-3.7-flash`) hết quota, giúp tiết kiệm tài khoản trước khi xoay tài khoản hoặc dùng provider ngoài.
- **🛡️ Cải Tiến Priority Fallback**: Tự động gộp cấu hình dự phòng theo nhà cung cấp (provider-level deduplication) tránh trùng lặp cấu hình mặc định và bảo toàn các tùy chọn model thủ công của người dùng khi nâng cấp plugin.

## 🚀 Khởi Động Nhanh

```bash
python install.py
python "$HERMES_HOME/bridge/antigravity/manage.py" login    # Tài khoản Google thứ nhất
python "$HERMES_HOME/bridge/antigravity/manage.py" login    # Thêm tài khoản Google phụ (tùy chọn)
python "$HERMES_HOME/bridge/antigravity/manage.py" start
hermes chat -q "Phản hồi chính xác chữ: OK" --provider antigravity -m gemini-3.7-flash
```

## 📂 Cấu Trúc Dự Án

```
plugin/                    Hermes model-provider plugin (ProviderProfile)
bridge/                    Local OAuth + Code Assist translation bridge
tests/                     Bộ test suite (unittest, không cần kết nối mạng)
skills/antigravity-oauth-bridge/   Skill vận hành plugin và rotation OAuth
skills/hermes-provider-management/ Skill quản lý provider/fallback/compression
skills/project-harness-engineering/ Skill thiết kế và audit project harness
skills/ui-ux-pro-max/          Searchable UI/UX intelligence + Hermes design routing
config/hermes-rotation.example.yaml Cấu hình mẫu đã loại bí mật
docs/CURRENT_SETUP_VI.md            Tổng hợp cấu hình vận hành hiện tại
install.py                           Script cài plugin + bridge + skill vào $HERMES_HOME
manage.py                  CLI: login / start / stop / status / install / setup
.hermes/environment.json   Cấu hình `hermes verify` tự động cho dự án
```

## 🔬 Kiểm Thử (Testing)

```bash
# Chạy toàn bộ unit tests
python -m unittest discover -s tests -p "test_*.py" -v

# Chạy test kiểm thử tích hợp
python tests/verify_integration.py
```

## 📄 Giấy phép (License)
Phát triển cho cộng đồng Hermes Agent & Antigravity. Bản quyền thuộc về giấy phép MIT — xem file [LICENSE](LICENSE).
