# Hermes Engineering Workbench: review, thiết kế và vận hành

Ngày review: 26/09/2026. Baseline: `185d239a11a789ae9e57c91d84ac027c0a40d65a`
trên `donghanhcungban/Hermes-Agents`. Bản bổ sung: 0.1.0.

## 1. Kết luận

Giữ Hermes làm runtime điều phối; phát triển repo này thành bộ công cụ chuyên môn
có kiểm thử, thay vì fork thêm một agent loop hoặc chỉ tăng số lượng skill.
“Kỹ sư toàn năng” là mục tiêu năng lực có tiêu chí nghiệm thu, không phải trạng thái
đã đạt được sau khi thêm prompt. Bản này hoàn thiện một nền tảng chạy được bằng
native plugin API, chưa phải sản phẩm tự hành hoàn chỉnh trong mọi lĩnh vực.

Phạm vi đã đọc: README, cây source/test, installer, provider registration, phần
khởi tạo và tuyến HTTP đầu của bridge, CI, tài liệu vận hành, nguồn vendor skills
và skill Autodesk. Đây là review kiến trúc cùng các đường tích hợp quan trọng,
không phải chứng nhận đã kiểm tra từng dòng của toàn repo hay pentest toàn hệ thống.
Không đăng nhập OAuth, không đọc secret, không chạy trên máy Hermes của chủ repo.

## 2. Phát hiện và trạng thái xử lý

| Mức | Bằng chứng baseline | Rủi ro | Xử lý trong bản này |
|---|---|---|---|
| P1 | `install.py:install_bundled_skills`, resolve trước is_symlink/rmtree | Có thể xóa target của symlink ngoài thư mục skill | Bỏ resolve ở đích; từ chối đường symlink; regression bằng thư mục giả |
| P1 | Cùng hàm, xóa skill trùng YAML name | Mất chỉnh sửa riêng/skill nằm trong category | Di chuyển bản cũ sang `skill-backups/`, publish từng skill và rollback khi lỗi |
| P1 | `bridge/server.py` phần Application/routes đã đọc | Chưa thấy lớp xác thực ở ranh giới HTTP đã xem; auth/account mutation cần audit toàn tuyến | Chưa sửa bridge trong PR này; không expose ra LAN/public; cần xác thực, origin/host checks, giới hạn payload/concurrency và redaction |
| P1 | `skills/autodesk-addin-development/SKILL.md` | Hướng dẫn net48 chung cho host hiện đại; ví dụ send 3 tham số nhưng query gọi 2 | Viết lại skill theo host+update+SDK; ví dụ query nhất quán và read-only có xác thực |
| P2 | `plugin/__init__.py` | Lỗi khởi động bridge bị `except Exception: pass` che đi | Ghi backlog: structured health và lỗi có redaction; chưa thay provider logic |
| P2 | `.github/workflows/tests.yml`, danh sách tests | Suite chủ yếu cho bridge/provider/skills; thiếu bằng chứng nghiệp vụ MEP/Office | Thêm numerical/validation/export/install tests và CI riêng có bốn dependency Office |
| P2 | `install.py` các bước bridge/grill/config còn lại | Installer tổng chưa transactional; có đường cảnh báo rồi báo thành công | Chỉ sửa hàm skill; Workbench dùng installer riêng dry-run/backup, không chạy installer tổng |

Các mức là đánh giá ưu tiên trong review này, không phải CVSS hoặc kết luận khai
thác thực tế. PR đang mở #21 là công việc UI/UX riêng; không merge/chỉnh sửa nó.

## 3. Kiến trúc đích

```text
Người dùng / Hermes CLI, gateway hoặc desktop
  -> Hermes core: model, native tools, delegation, approvals, session
  -> engineering-workbench (native plugin)
       -> engineering_plan -> skill theo software / office / mep
       -> static repository inventory
       -> deterministic SI calculation + Decimal BOQ
       -> draft export + SHA-256/provenance manifest
  -> Các adapter tương lai, khai báo riêng và kiểm chứng host thật
       -> Git/CI sandbox; email/calendar có scope; IFC; Windows CAD/BIM worker
```

Không thay model/provider/OAuth, không tự chuyển gói thuê bao hay thêm chi phí API.
Công cụ deterministic không gọi LLM. Hermes dùng provider người vận hành đã chọn.
Nếu làm router model sau này: chọn theo yêu cầu tool/vision/context/độ tin cậy,
đo trên bộ bài kiểm tra thực; chỉ dùng model/catalog được provider xác nhận.
Không giả định một model hay quota miễn phí cố định.

Một agent điều phối, các vai trò chuyên môn nạp khi cần; không nạp tất cả skill vào
mỗi lượt. Lập trình viên, reviewer, Office analyst và MEP reviewer là các vai trò,
không được báo “đã chạy nhiều agent” khi chỉ lập kế hoạch. Chỉ delegate file không
chồng lấn; tích hợp tuần tự và kiểm thử lại toàn kết quả. Tái dùng giới hạn ngân
sách/approval của Hermes, không tạo shell runner né cơ chế đó.

## 4. Những gì đã có mã thực thi

Sáu tool đăng ký qua `register(ctx)` và ba namespaced skill:

| Tool | Làm được | Không được suy diễn |
|---|---|---|
| engineering_status | Báo thư viện tùy chọn và phạm vi implementation | Không probe host/credential hay khẳng định CAD đang live |
| engineering_plan | Tạo workflow, deliverables, approval và skill phù hợp | Không tự chạy plan hoặc tạo PR |
| engineering_repo_inspect | Tìm tên manifest/CI/instructions trong workspace | Không đọc code hoặc chạy test/build |
| engineering_mep_calculate | 5 công thức SI, kiểm tra input, ghi basis/formula/unit/limitations | Không sizing thiết bị hoặc chứng nhận tiêu chuẩn |
| engineering_boq | Decimal quantity x price, tổng, trùng ID và nguồn mỗi dòng | Không xác nhận giá/scope/đơn vị/thuế hay khối lượng bóc tách |
| engineering_export | Tạo MD/CSV/DOCX/XLSX/PPTX/PDF và manifest mới | Không nhập file, render, gửi email hoặc sửa file gốc |

Skill: `engineering-workbench:software`, `engineering-workbench:office`,
`engineering-workbench:mep`. Hermes nạp bằng `skill_view` với tên đầy đủ; skill
plugin không thay thế bare skill có sẵn. Đây là hướng dẫn workflow, không phải
lớp cưỡng chế toàn cục áp lên mọi tool khác trong Hermes.

MEP gồm dòng ba pha cân bằng, lưu lượng gió theo tải sensible, lưu lượng nước theo
cân bằng nhiệt, vận tốc ống tròn đầy và tổn thất áp Darcy đoạn thẳng. Tất cả dùng
input SI có tên đơn vị; thiếu basis, số âm/0, NaN/Infinity, PF > 1 hoặc sai trường
sẽ trả lỗi. Không tự đặt hệ số thiết kế, properties môi chất hay tiêu chuẩn.
Điện dùng công suất điện đầu vào, không nhầm công suất cơ trục động cơ.
Kết quả luôn `preliminary_not_for_construction`, `standards_verified: false`.

Office là exporter bản nháp cơ bản, chưa phải trình chế bản cao cấp. PDF/PPTX
chưa hỗ trợ bảng và báo lỗi rõ; DOCX/XLSX dùng cho bảng. PDF Unicode cần font TTF
hợp pháp do operator cấu hình. XLSX giữ chuỗi thành literal để không thực thi
formula; CSV escape chuỗi giống công thức. Đây không phải engine tính công thức
Excel. Kiểm tra layout/render còn phải làm bằng công cụ khác.

## 5. Cài và chạy trong Hermes

Chỉ thực hiện với nhánh/commit đã review, trong môi trường Python của Hermes.
Bước này chưa được chạy trên máy người dùng trong phiên review.

```bash
# Từ root bản repo có thay đổi này, với Python của Hermes:
python -m pip install -r requirements-office.txt  # tùy chọn, cho Office/PDF
python -m unittest discover -s tests -p "test_*.py" -v
python install_workbench.py                     # dry-run, không sửa gì
python install_workbench.py --apply             # copy plugin, không tự enable

mkdir -p "$HOME/hermes-projects/demo"
export HERMES_WORKBENCH_ROOT="$HOME/hermes-projects/demo"
hermes plugins list
hermes plugins enable engineering-workbench
# Mở phiên Hermes mới để nạp plugin và biến môi trường.
hermes chat -q "Gọi engineering_status, sau đó engineering_plan cho domain software với mục tiêu audit dự án. Chỉ báo những bước thực sự đã chạy."
```

Trên PowerShell dùng `$env:HERMES_WORKBENCH_ROOT = 'C:\\HermesProjects\\demo'`
với thư mục đã tồn tại. Cho gateway/service, đặt biến trong môi trường của service
và restart có kiểm soát; `export` ở shell khác không cấu hình service đang chạy.
Dùng `--hermes-home` để chọn profile đã xác nhận. Không lấy cả thư mục home làm
workspace. Plugin chứa mã chạy với quyền tiến trình Hermes: chỉ enable mã đã review.

Cài đè cần `python install_workbench.py --apply --upgrade`; bản cũ được giữ ở
`$HERMES_HOME/workbench-backups/<id>`. Không đổi config model, token hay provider.
Rollback: disable plugin qua Hermes; đóng session; kiểm tra đường backup rồi khôi
phục thư mục plugin cũ với thao tác có chủ đích; mở phiên mới. Không xóa artifacts
hay credential. Sửa installer skill cũ lưu backup ở `skill-backups/<id>`; không tự
phục hồi/xóa các backup đó khi một bản upgrade đã thành công.

## 6. Smoke test và nghiệm thu trên host thật

Sau khi enable, xác nhận sáu tools xuất hiện; đọc ba skill đúng namespace. Thử
`engineering_mep_calculate` với power_W=10000, line_voltage_V=400,
power_factor=0.8 và basis “synthetic smoke test”: kỳ vọng khoảng 18.042195912 A,
không phải chứng nhận cáp/CB. Lặp lại input lỗi để xác nhận fail-closed.

Xuất tài liệu tiếng Việt và bảng synthetic; kiểm tra manifest/hash; mở bằng phần
mềm đích và kiểm tra toàn bộ layout. Không dùng dữ liệu confidential cho lần smoke
test đầu. Chạy một task phần mềm nhỏ trên repo giả, có test lỗi trước và pass sau.
Lưu command/exit code, revision, phiên bản Hermes/Python, tool output và screenshot
khi phù hợp. Host Autodesk chỉ đạt live khi có read-only query thực trên model giả.

Test offline được chạy trong môi trường xây dựng, Python 3.13; không phải bằng
chứng test trong runtime Hermes. Các test đăng ký dùng Context giả theo API chính
thức. Bốn exporter DOCX/XLSX/PPTX/PDF đã tạo file thực trong test; Office ZIP/XML
được kiểm tra ở mức cấu trúc, chưa kiểm tra bố cục bằng mắt. Suite gốc toàn repo
chờ GitHub CI vì môi trường local không clone được đầy đủ repo. Không dùng trạng
thái “CI pending”, test mock hay output draft để tuyên bố production-ready.

## 7. Lộ trình hoàn thiện theo cổng nghiệm thu

### P0/P1: nền tảng tin cậy

Đưa PR qua suite gốc và Office CI, chạy smoke test trên đúng Hermes build; audit
bridge auth từ handler đến middleware, chặn non-loopback không xác thực, origin/host
validation, payload/concurrency limits và redaction. Hoàn thiện toàn installer với
backup/transaction, exit code trung thực. Gate: regression bao phủ permission denial,
symlink, corruption, timeout và rollback; không mở mạng trước khi đạt gate.

### P2: kỹ sư phần mềm có bằng chứng

Tái dùng terminal/git/delegation của Hermes trong sandbox; thêm task ledger bền vững
(JSON/SQLite có task_id, owner, state, input/output hashes, test evidence, approvals),
resume/idempotency và budget. Xây bộ task thật có regression, refactor, API, UI,
migration, CI và bảo mật. Đánh giá success rate theo acceptance tests, lỗi hồi quy,
chi phí/task và tỷ lệ can thiệp; không đánh giá bằng số dòng code hoặc số skill.
Gate: patch/test/review/rollback đầy đủ; merge/deploy chỉ sau authorized approval.

### P3: văn phòng vận hành

Thêm parser DOCX/XLSX/PDF, quản lý schema dữ liệu, template công ty, render/visual
QA, Excel recalculation và kiểm tra totals. Sau đó mới thêm email/calendar/storage
adapter có OAuth scopes tối thiểu, recipient validation, dry-run và idempotency.
Gate: không mất nội dung, không lỗi layout/tính toán, đối chiếu nguồn, đúng quyền
chia sẻ. Importer không chạy macro, remote images hay link external tự động.

### P4: MEP/BIM đọc trước, ghi sau

Chuẩn hóa design basis + unit service + source/standards register; tăng numerical
kernels cùng golden tests do kỹ sư độc lập kiểm. Thêm IFC adapter trích xuất system,
level, properties, quantities; kiểm tra tính đầy đủ trước khi làm clash detection.
Windows worker riêng cho Revit/AutoCAD; xác nhận full version/update/SDK/license.
Giao thức có authentication, allowlist, preview digest, document revision, token
hết hạn/dùng một lần, audit và rollback. Gate: sample models có expected results,
read-only host-real pass; writes thử trên bản sao; qualified reviewer chấp nhận.
Không dùng plugin như chữ ký thiết kế hoặc thay người chịu trách nhiệm PCCC.

## 8. Ranh giới bảo mật và nguồn kỹ thuật

Workspace check là giới hạn ở mức ứng dụng, không phải sandbox hệ điều hành và
không chống được tiến trình cục bộ độc hại thay symlink đồng thời (TOCTOU).
Chạy single-user workspace; tách quyền OS/container cho repo và tài liệu không tin
cậy. Không mở URL, gọi shell, tải dependency hay gửi nội dung từ exporter. Manifest
chứng minh bytes/hash và nguồn được khai báo, không chứng minh nguồn chính xác.

Nguồn chính thức dùng để đối chiếu thiết kế native/host version:
- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Revit--Requirements-for-products-affected-by-the-Microsoft--NET-10-transition.html
- https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Customization/files/GUID-A6C680F2-DE2E-418A-A182-E4884073338A.htm

Không bundle tiêu chuẩn bản quyền, font hoặc khóa truy cập. Dependency Office hiện
được giới hạn major version, chưa có lockfile/hash pinning; cần lock theo môi trường
triển khai đã nghiệm thu. Không hứa tương thích với mọi phiên bản Hermes/Autodesk.
