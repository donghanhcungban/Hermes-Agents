# Gợi ý nâng cấp — rà soát 2026-10-13

> Lấy từ đợt rà soát chéo 19 repo của chủ sở hữu (ma trận vệ sinh ở [seeker19110/stored, mục 23 §8.1](https://github.com/seeker19110/stored/blob/main/23-own-repos-lessons/README.md); gợi ý tích hợp ở §7b của cùng file). Số liệu đo bằng lệnh trên HEAD (đếm `uses:` ghim SHA 40 ký tự, khối `permissions:`, `dependabot.yml`, `.claude/settings.json`), không suy ra từ văn xuôi. Đây là **đề xuất**, chưa sửa code. Mỗi mục kèm bằng chứng để kiểm lại trước khi làm; mục nào đã xử lý thì đánh dấu hoặc xoá.

## Hiện trạng đo được

| HEAD đọc | Action ghim SHA | Workflow thiếu `permissions:` cấp đầu | Dependabot | LICENSE · SECURITY | File test |
|---|---|---|---|---|---|
| `99fe522` (2026-10-05) | 0/11 | – | **không có** | có · không | 22 |

## Đề xuất (🔴 cao · 🟠 trung bình · 🟢 nhẹ)

| # | Mức | Đề xuất | Bằng chứng | Kiểm xong khi |
|---|---|---|---|---|
| 1 | 🟠 | Ghim **11** action theo SHA và thêm `.github/dependabot.yml` (pip, github-actions) | Ghim 0/11; repo không có Dependabot | Grep `uses:` không ghim trả về 0 |
| 2 | 🟢 | Chuyển nguồn vendor của `skills/sketch` và `skills/spike` từ `gsd-build/get-shit-done` (đã archive 26/6/2026) sang `open-gsd/gsd-core`, rồi cập nhật `skills/VENDORED-SKILLS.md` | `grep -rl gsd-build skills/` → `sketch/SKILL.md`, `spike/SKILL.md` | Grep trả về rỗng; provenance ghi commit của gsd-core |
| 3 | 🟢 | Thêm `SECURITY.md` (bridge giữ token OAuth) | Không có SECURITY.md | Có file |

## Giữ nguyên (điểm mạnh)

- `bridge/http_security.py` là **mẫu biên mạng tốt nhất** trong các repo của bạn: mặc định loopback, kiểm Host, `hmac.compare_digest`, giới hạn body và số request đồng thời. Nên port sang Plugin-4-Hermes và ai-gateway.
- Vendoring có provenance (`VENDORED-SKILLS.md`).

## Gợi ý tích hợp từ catalog `stored`

- codegraph hỗ trợ Hermes Agent: thử MCP server của nó với bridge :8100 (stored mục 16 §2d).
- Quét 112 SKILL.md bằng SkillSpector hoặc agent-scan trước mỗi lần vendor mới (stored mục 12 §3d–§3e).

## Ghi chú chung

- Ghim action theo SHA bằng [pinact](https://github.com/suzuki-shunsuke/pinact) hoặc [ratchet](https://github.com/sethvargo/ratchet), giữ comment tag (`# v7.0.1`), rồi để Dependabot `github-actions` tự nâng SHA. Đây là cách projects-template, xboss và Sales-Hunter đang làm.
- Chuẩn tham chiếu là `seeker19110/projects-template`: 25/25 action ghim SHA, mọi workflow có `permissions:` cấp đầu, Dependabot cho npm, github-actions và pip.
