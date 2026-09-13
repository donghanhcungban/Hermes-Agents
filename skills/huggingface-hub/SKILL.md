---
name: huggingface-hub
description: "HuggingFace hf CLI: search/download/upload models, datasets."
version: 1.0.1
author: Hugging Face, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [huggingface, hf, models, datasets, hub, mlops]
    related_skills: [llama-cpp, weights-and-biases]
---

# Hugging Face CLI (`hf`) Reference Guide

The `hf` command is the modern command-line interface for interacting with the Hugging Face Hub, providing tools to manage repositories, models, datasets, and Spaces.

> **IMPORTANT:** The `hf` command replaces the now deprecated `huggingface-cli` command.

## Quick Start
*   **Installation:** `curl -LsSf https://hf.co/cli/install.sh | bash -s`
*   **Help:** Use `hf --help` to view all available functions and real-world examples.
*   **Authentication:** Recommended via `HF_TOKEN` environment variable or the `--token` flag.

---

## Core Commands

### General Operations
*   `hf download REPO_ID`: Download files from the Hub.
*   `hf upload REPO_ID`: Upload files/folders (recommended for single-commit; also handles resumable uploads of large directories).
*   `hf upload-large-folder REPO_ID LOCAL_PATH`: **[Deprecated]** — use `hf upload` instead.
*   `hf sync`: Sync files between a local directory and a bucket.
*   `hf env` / `hf version`: View environment and version details.

### Authentication (`hf auth`)
*   `login` / `logout`: Manage sessions using tokens from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
*   `list` / `switch`: Manage and toggle between multiple stored access tokens.
*   `whoami`: Identify the currently logged-in account.

### Repository Management (`hf repo`)
*   `create` / `delete`: Create or permanently remove repositories.
*   `duplicate`: Clone a model, dataset, or Space to a new ID.
*   `move`: Transfer a repository between namespaces.
*   `branch` / `tag`: Manage Git-like references.
*   `delete-files`: Remove specific files using patterns.

---

## Specialized Hub Interactions

### Datasets & Models
*   **Datasets:** `hf datasets list`, `info`, and `parquet` (list parquet URLs).
*   **SQL Queries:** `hf datasets sql SQL` — Execute raw SQL via DuckDB against dataset parquet URLs.
*   **Models:** `hf models list` and `info`.
*   **Papers:** `hf papers ls` — View daily papers.

### Discussions & Pull Requests (`hf discussions`)
*   Manage the lifecycle of Hub contributions: `list`, `create`, `info`, `comment`, `close`, `reopen`, and `rename`.
*   `diff`: View changes in a PR.
*   `merge`: Finalize pull requests.

### Infrastructure & Compute
*   **Endpoints:** Deploy and manage Inference Endpoints (`deploy`, `pause`, `resume`, `scale-to-zero`, `catalog`).
*   **Jobs:** Run compute tasks on HF infrastructure. Includes `hf jobs uv` for running Python scripts with inline dependencies and `stats` for resource monitoring.
*   **Spaces:** Manage interactive apps. Includes `dev-mode` and `hot-reload` for Python files without full restarts.

### Storage & Automation
*   **Buckets:** Full S3-like bucket management (`create`, `cp`, `mv`, `rm`, `sync`).
*   **Cache:** Manage local storage with `list`, `prune` (remove detached revisions), and `verify` (checksum checks).
*   **Webhooks:** Automate workflows by managing Hub webhooks (`create`, `watch`, `enable`/`disable`).
*   **Collections:** Organize Hub items into collections (`add-item`, `update`, `list`).

---

## Advanced Usage & Tips

### Global Flags
*   `--format json`: Produces machine-readable output for automation.
*   `-q` / `--quiet`: Limits output to IDs only.

### Extensions & Skills
*   **Extensions:** Extend CLI functionality via GitHub repositories using `hf extensions install REPO_ID`.
*   **Skills:** Manage AI assistant skills with `hf skills add`.

## 🌟 Cổng Chất Lượng Thượng Thừa (Supreme Quality Gate)

Khi vận hành kỹ năng này, agent phải tuân thủ nghiêm ngặt các nguyên tắc sau:
1. **Tuyệt đối không đoán mò**: Không bao giờ tự bịa ra dữ liệu, nội dung file hay kết quả kiểm thử. Mọi báo cáo phải dựa trên output thực tế từ công cụ.
2. **Kiểm tra trước khi sửa**: Luôn sử dụng `read_file`/`search_files` để xác minh nội dung hiện tại và cấu trúc thư mục trước khi sửa đổi.
3. **Sửa đổi targeted**: Ưu tiên dùng `patch` (thay vì ghi đè hoàn toàn bằng `write_file`) cho các chỉnh sửa cục bộ để giữ lại cấu hình nguyên bản và tránh lỗi cú pháp không mong muốn.
4. **Xác minh đầu ra**: Sau khi chỉnh sửa code hoặc tệp cấu hình, bắt buộc phải chạy bộ test suite hoặc lệnh build/compile để kiểm tra tính đúng đắn.
5. **Tối ưu hóa token**: Giới hạn phạm vi đọc tệp bằng cách sử dụng `offset` và `limit` để tiết kiệm token ngữ cảnh.
