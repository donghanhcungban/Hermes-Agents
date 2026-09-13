# Kiểm thử host Autodesk thật bằng harness

Dùng khi người dùng yêu cầu điều khiển máy để kiểm Revit/AutoCAD và repository đã có harness chạy trong host.

## Nguyên tắc

- Ưu tiên harness của repository hơn bấm Ribbon thủ công: harness vẫn chạy API Autodesk thật, tạo artifact xác định và trả mã thoát dùng được trong CI.
- Dùng computer-use để quan sát cửa sổ khi có, nhưng không bấm hoặc gõ trong lúc harness cảnh báo không tương tác.
- AutoCAD có thể chạy bằng `accoreconsole.exe`; không có cửa sổ GUI là hành vi dự kiến, không phải bằng chứng test giả.
- Revit harness có thể tự mở, chạy add-in rồi tự đóng; cửa sổ đôi khi không được lớp accessibility liệt kê. Khi đó xác minh bằng tiến trình, mã thoát và báo cáo do add-in sinh, không cố giành foreground.

## Quy trình

1. Kiểm working tree và xem có tiến trình `acad`, `accoreconsole` hoặc `Revit` đang chạy để tránh đè phiên người dùng.
2. Đọc script test và tham số suite/version trước khi gọi; không đoán tên suite.
3. Chạy AutoCAD và Revit nối tiếp, không song song, vì cả hai host nặng và có thể tranh tài nguyên/license.
4. Với tác vụ dài, chạy nền có notification; thử capture scoped theo app sau khi host khởi động. Nếu harness headless/ẩn và capture không thấy cửa sổ, tiếp tục theo artifact path từ stdout.
5. Chờ đúng mã thoát. Đọc báo cáo Markdown/TRX để lấy tổng pass/fail/skip; không suy tổng từ output terminal bị cắt.
6. Kiểm không còn tiến trình host và working tree không bị thay đổi ngoài ý muốn.
7. Báo đường dẫn artifact, model/host version, tổng chính xác và mọi skip/failure. Một lượt xanh không phủ định lỗi hiệu năng từng tái hiện nhiều lần; giữ issue flaky mở cho tới khi có đủ lượt lặp hoặc sửa nguyên nhân.

## Phân biệt bằng chứng

- **Host-real:** command chạy trong Revit/AutoCAD hoặc accoreconsole với Autodesk API thật.
- **GUI-observed:** computer-use nhìn thấy/có thể tương tác cửa sổ.
- **MCP-live:** `/health` và ít nhất một query thật thành công khi host đang mở.

Không dùng một loại bằng chứng để tuyên bố thay cho loại khác. Nếu người dùng yêu cầu test MCP end-to-end, harness host-real chưa đủ; phải giữ host mở và probe Bridge riêng.
