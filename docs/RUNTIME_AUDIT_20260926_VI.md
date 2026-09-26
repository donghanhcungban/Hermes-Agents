# Audit runtime Hermes: bằng chứng, bản sửa và giới hạn

Ngày: 26/09/2026. Baseline main: `092ee16b975a9c99a9e81650d6fcf7a81aab127f` (PR #22 đã merge).
Bản sửa nằm trong PR #23, nhánh `fix/hermes-runtime-hardening-20260926`. Workbench 0.1.1.

## Kết quả chính

Mục tiêu là trợ lý/kỹ sư có hành vi kiểm chứng được, không tuyên bố “hoàn hảo”.
Audit tập trung vào bridge HTTP, hai CLI provider, account pool, đường khởi động,
Workbench và CI. Đã đọc mã, viết test tái hiện, sửa và chạy lại; không phải pentest
mọi dòng của hơn 500 file hay chứng nhận thiết kế MEP. Không gọi LLM trả phí, đọc
credential thật hoặc thay đổi máy Hermes/Revit/AutoCAD của người dùng.

## Lỗi đã sửa

| Ưu tiên | Lỗi và hệ quả | Sửa / kiểm thử |
|---|---|---|
| P1 | Cả hai vòng CLI tiếp tục sang tài khoản khác sau khi đã thành công | Dừng ở kết quả thành công đầu; fixture hai tài khoản xác nhận chỉ một lần gọi |
| P1 | Pool có tài khoản nhưng toàn bộ không khả dụng vẫn có thể dùng credential global | Trả 429/503, runner không được gọi; registry hỏng không được coi là pool rỗng |
| P1 | Codex chấp nhận tool ngoài allowlist khi danh sách rỗng, hoặc arguments không phải object | Kiểm tra tên đã được Hermes cung cấp, shape, tool_choice, duplicate keys và non-finite JSON; không “sửa hộ” output sai thành thành công |
| P1 | Claude dùng sai biến CLAUDE_HOME; `--tools ""` không vô hiệu MCP | Dùng CLAUDE_CONFIG_DIR và `--strict-mcp-config`; sửa lệnh login. Không suy diễn folder config chứng minh account identity trên macOS Keychain |
| P1 | Claude kế thừa ANTHROPIC_API_KEY của Hermes và có thể tính phí API thay gói tháng | Loại biến API/gateway khỏi env của tiến trình con; bỏ ambient OAuth khi đã chọn account; không sửa env cha |
| P1 | HTTP admin không có cổng quyền; Origin/Host/JSON sai có thể đến handler | Admin mặc định tắt, token admin riêng khi bật; chặn browser/forwarded requests; chỉ loopback; kiểm tra JSON trước handler |
| P1 | Lỗi provider/stream có thể lộ stderr hoặc kết thúc như thành công | Lỗi công khai đã rút gọn; stream lỗi có SSE error, không giả DONE; đóng generator/client |
| P1 | Hủy tác vụ CLI bỏ lại subprocess trực tiếp | Kill + wait rồi truyền CancelledError, không coi hủy là lỗi provider |
| P1 | Pool singleton chỉ theo provider, có thể dùng nhầm profile | Key theo provider + HERMES_HOME đã resolve; test hai profile riêng |
| P1 | Ghi registry thất bại bị nuốt, fallback ghi đè không nguyên tử | Temporary file riêng, fsync + replace; lỗi được truyền ra, khôi phục state đã commit; không ghi đè registry hỏng |
| P2 | Auto-start chỉ hiểu layout cài đặt và ghép host/path vào mã Python | Một builder argv dùng được cho source/installed; không nội suy đường dẫn; health không proxy/redirect và có giới hạn kích thước |
| P2 | Provider nuốt lỗi auto-start | Cảnh báo loại lỗi, không in raw error hoặc secret |
| P2 | XLSX/CSV bỏ qua phần sections | XLSX có Narrative sheet; CSV trả narrative.json có hash qua supplemental_files; không âm thầm mất giả thiết |
| P2 | Workbench báo workspace sẵn sàng chỉ vì biến env tồn tại | Tách workspace_declared khỏi workspace_configured hợp lệ |
| P2 | Thư mục staging của installer nằm trong cây plugin có thể được scanner phát hiện | Stage bên ngoài plugins, giữ rollback; từ chối source symlink |
| P2 | CI unittest bỏ qua test dạng hàm | Runtime Audit chạy pytest với toàn bộ dependency Office, JUnit và revision/source artifact |

Mức ưu tiên là đánh giá của audit, không phải CVSS hay chứng minh khai thác trên Internet.
Công cụ không kiểm tra toàn bộ JSON Schema nghiệp vụ của tool: Hermes vẫn phải xác
thực arguments theo schema trước khi thực thi. Không có cơ chế bypass approval.

## Bằng chứng kiểm thử

- Baseline CI pytest: 168 test case được báo cáo trong JUnit, không lỗi/skip.
- Các regression đầu tiên tái hiện lỗi: 23 failure theo pytest/subtest reporting.
- Sau sửa: báo cáo local `150 passed, 78 subtests passed`, Python 3.13.5; không skip.
  Đây là cách runner local đếm test/subtest, không cộng/trừ trực tiếp với con số
  của CI pytest phiên bản khác. JUnit và log lưu riêng để đối chiếu.
- HTTP dùng aiohttp TestServer/TestClient thật trên loopback, nhưng provider backend
  là giả lập. CLI runner dùng tài khoản giả; cancellation test kiểm tra kill/wait
  bằng subprocess mock. Không tuyên bố đã xác nhận subscription/account thật.
- Hermes Native Compatibility: checkout commit upstream
  `d0288be5b3330d2442e3907185b8e9d0958297bb`, cài core trên Python 3.14, dùng
  PluginContext/PluginManager/registry thật, đăng ký ba skill và gọi sáu handler.
  Không mock API plugin; không gọi model. Đây không phải kiểm thử discovery/enable
  từ đầu, phiên chat/gateway trọn vẹn hoặc bản Hermes/fork của người dùng.
- `compileall` và `git diff --check` được chạy. Runtime Audit + Office CI + native
  compatibility phải kiểm tra lại đúng head SHA sau khi push; không dùng kết quả
  của commit trước để tuyên bố commit sau đã qua CI.

## Thay đổi vận hành phải biết

### Bridge HTTP

Bridge chỉ bind loopback; không dùng `0.0.0.0`, reverse proxy công khai hoặc wildcard
CORS. Browser có Origin hoặc header forwarded bị chặn. Giới hạn JSON request 2 MiB,
8 handler đang xử lý, timeout đọc body 15 giây. Đây không phải rate limiter bền vững.

Để tương thích client cũ, inference loopback chưa bắt buộc token nếu chưa cấu hình.
**Điều này không bảo vệ khỏi tiến trình khác chạy trên cùng máy.** Với tài liệu
riêng tư, đặt `HERMES_BRIDGE_API_KEY` bằng secret ngẫu nhiên ít nhất 32 ký tự, dùng
cùng giá trị cho client và bridge. Provider profiles ưu tiên biến này; bridge không
chuyển secret nội bộ đó sang Google. Không dùng OAuth token làm secret nội bộ.

HTTP `/auth/*` và `/v1/accounts/*` mặc định trả 403. Quản lý tài khoản bằng CLI cục bộ
vẫn hoạt động. Chỉ bật HTTP admin khi thực sự cần: đặt `HERMES_BRIDGE_ADMIN_TOKEN`
riêng (32..512 ký tự ASCII không khoảng trắng), client gửi `X-Hermes-Admin-Token`.
Không nhúng token vào URL, tài liệu, log hoặc commit. Mỗi secret phải được đặt trong
đúng môi trường của bridge/service; shell khác không đổi env của tiến trình đã chạy.

### CLI và tài khoản

Nâng cấp bridge runtime đang cài thì mới có bản sửa; chỉ git pull source không đổi
bản trong `$HERMES_HOME/bridge/antigravity/tools/antigravity_bridge`. Đóng phiên và
backup trước khi chạy installer đã review. Installer tổng vẫn có các bước bridge,
provider và config chưa transactional toàn bộ; không chạy nó không kiểm soát.

Claude sử dụng `CLAUDE_CONFIG_DIR` và `claude auth login`. Provider subscription
loại các biến API/gateway kế thừa khỏi tiến trình con và dùng `--setting-sources ""`
để không nạp user/project/local settings. Env và cấu hình của Hermes cha không đổi;
managed settings policy của CLI vẫn áp dụng. Kiểm tra `claude auth status`
trong từng profile để xác nhận đúng danh tính; đặc biệt macOS giữ credential trong
Keychain. `--strict-mcp-config` cần CLI hỗ trợ; bản CLI quá cũ phải được nâng cấp có
chủ đích, không tự bỏ cờ bảo vệ để “chạy được”. Các hook/managed settings và sandbox
của CLI vẫn là một trust boundary riêng: không tuyên bố tool flags vô hiệu mọi hook,
đọc file, subprocess con hoặc mọi quyền của tiến trình. Codex read-only không đồng
nghĩa không đọc được tài liệu; không dùng bridge trong workspace không tin cậy.

Registry lỗi giờ trả lỗi thay vì âm thầm dùng tài khoản khác. Backup nguyên file,
khôi phục bản được kiểm tra, không xóa registry để né lỗi. Atomic replace tránh file
JSON bị ghi nửa chừng; registry vẫn là single-writer, chưa có transaction lock giữa
nhiều tiến trình. Không chạy hai bridge quản lý cùng một registry đồng thời.

### Workbench

Cài riêng, bằng Python của Hermes:

```bash
python install_workbench.py --upgrade          # chỉ xem trước khi đã có bản cũ
python install_workbench.py --apply --upgrade  # backup bản cũ và cài 0.1.1
```

Máy chưa cài thì bỏ `--upgrade`. Không tự thay model/provider. Sau cài, bật plugin
và mở phiên Hermes mới. Đặt HERMES_WORKBENCH_ROOT tới thư mục tuyệt đối đã tồn tại.
Gọi engineering_status; đọc workspace_configured và host_connections, không coi thư
viện được cài là host CAD đang live. Khi xuất CSV, bàn giao cả supplemental_files,
manifest và CSV để không mất phần giải thích. Bản XLSX giữ diễn giải ở Narrative.

## Các cổng chưa đạt / không được suy diễn

Chưa chạy trên máy người dùng hoặc bản fork Hermes của họ; chưa gọi Claude/Codex
thật với tài khoản của họ; chưa chứng minh full agent session/delegation hoàn thành
một dự án thật. Chưa có live CAD/BIM adapter, IFC clash, Office importer/render hoặc
email/calendar workflow. Không thể dùng số test xanh để khẳng định toàn năng.

MEP vẫn preliminary_not_for_construction, standards_verified=false: không chọn
thiết bị an toàn/PCCC, ký duyệt hồ sơ hoặc thay người chịu trách nhiệm kỹ thuật.
Office tests kiểm tra cấu trúc/nội dung, chưa phải visual acceptance mọi layout.
Workspace/path checks không phải OS sandbox và không chống TOCTOU của tiến trình
độc hại cùng user. Chưa audit/pin toàn bộ dependency, mọi skill vendor, tất cả OAuth
flows, stop-daemon PID reuse, multi-process account locking hoặc subprocess trees.

Để nghiệm thu vận hành: dùng bản sao dự án/tài liệu, test một yêu cầu phần mềm có
regression trước/sau; một tài liệu có tổng và nguồn đối chiếu; một bài MEP có kết quả
chuẩn do kỹ sư độc lập kiểm tra. Ghi exact host version/commit, lệnh, exit code,
artifact hash, review và rollback. Merge/deploy/email/share/live drawing writes là
những hành động riêng cần quyền rõ ràng, không được tự suy từ yêu cầu audit.

## Nguồn đối chiếu chính thức

- Hermes plugin API: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- Mã API upstream pin ở workflow: NousResearch/hermes-agent commit d0288be5b3330d2442e3907185b8e9d0958297bb.
- Claude environment variables: https://code.claude.com/docs/en/env-vars
- Claude CLI: https://code.claude.com/docs/en/cli-reference
- aiohttp middleware/cleanup: https://docs.aiohttp.org/en/stable/web_advanced.html
- Codex CLI source: openai/codex commit c9e25207073a88f1a3a4a885991b9143799a084f, codex-rs/exec/src/cli.rs.
