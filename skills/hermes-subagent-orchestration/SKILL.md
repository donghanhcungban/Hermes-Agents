---
name: hermes-subagent-orchestration
description: "Điều phối nhiều tác vụ code song song qua delegate_task."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [orchestration, subagents, delegation, parallel-work]
    related_skills: [hermes-agent, safe-ai-state-authority]
---

# Hermes Subagent Orchestration

Thay cho việc gọi Claude Code hoặc Codex CLI ngoài (tốn PTY, tmux, dialog handling), dùng thẳng tool `delegate_task` sẵn có của Hermes để điều phối công việc lập trình song song. Không cần CLI ngoài, không cần cài đặt, không có rủi ro PTY treo.

## Khi nào dùng

- Cần sửa nhiều file/module độc lập cùng lúc (backend + tests + docs).
- Cần review PR mà không muốn tốn context chính.
- Cần thử nhiều hướng giải quyết song song rồi so sánh kết quả.
- Việc nặng về suy luận, sinh ra nhiều dữ liệu trung gian không cần giữ trong context chính.

Không dùng cho: một lệnh tool đơn lẻ, việc cơ học không cần suy luận (dùng `execute_code`), việc cần hỏi lại người dùng giữa chừng (subagent không hỏi được).

## Cách dùng

```
delegate_task(tasks=[
  {"goal": "Sửa bug X trong module Y", "context": "Đường dẫn file, lỗi cụ thể, ràng buộc cần biết — subagent không thấy hội thoại này"},
  {"goal": "Viết test cho module Y", "context": "..."}
])
```

- Mỗi `task` là một subagent độc lập, có terminal + toolset riêng, tối đa 10 task song song (giới hạn theo `delegation.max_concurrent_children`).
- `context` phải tự đủ — subagent không biết gì về hội thoại hiện tại, phải truyền toàn bộ thông tin cần thiết (đường dẫn, ngôn ngữ trả lời, ràng buộc).
- Nếu không có người tiêu thụ kết quả về sau sẽ chờ trong cùng lệnh gọi; việc chạy nền sẽ trả kết quả vào tin nhắn mới giữa các lượt — không polling, không chờ vòng lặp.
- Dùng `action="list"/"steer"/"stop"` để theo dõi/can thiệp subagent đang chạy.

## Cảnh báo quan trọng

- Kết quả subagent trả về là **tự báo cáo**, không phải sự thật đã xác minh. Với side-effect ra ngoài (upload, publish, ghi remote), luôn yêu cầu handle xác minh được (URL/ID/đường dẫn tuyệt đối) và tự kiểm tra lại trước khi báo thành công cho người dùng.
- Subagent không gọi được `delegate_task`, `clarify`, `memory`, `cronjob` — việc cần hỏi người dùng phải giữ ở agent chính.
- Song song hoá theo workstream độc lập (VD: `git worktree` riêng cho mỗi task) để tránh xung đột file khi nhiều subagent sửa cùng repo.

## So với claude-code/codex CLI

Không cần: tmux, PTY dialog handling (trust dialog, permissions bypass), cài đặt CLI ngoài, quản lý session ID thủ công. `delegate_task` là tool nội bộ Hermes, không có rủi ro treo do thiếu PTY và không phụ thuộc gói ngoài.