# grill-tab

> Vendor từ [thanhan-a17/grill-tab](https://github.com/thanhan-a17/grill-tab) (MIT © 2026)

Plugin Hermes Desktop: nhấn **Tab** trước khi nhấn Enter để làm rõ intent qua từng câu hỏi
quyết định, rồi tổng hợp thành execution brief đặt vào composer.

## Cài đặt

`install.py` của repo này tự động cài plugin vào `$HERMES_HOME`. Sau khi chạy:

```yaml
# config.yaml
auxiliary:
  grill_tab:
    provider: antigravity
    model: gemini-3-flash-agent
    timeout: 15
```

Restart Hermes Desktop backend sau khi cài.

## Sử dụng

Type intent trong composer → nhấn **Tab** → trả lời từng câu → nhấn **Enter** khi xong.
Brief được đặt vào composer, bạn đọc và tự nhấn Enter để gửi.

Xem thêm: [docs/SPEC.md](docs/SPEC.md) · [docs/CONTRACT.md](docs/CONTRACT.md)

## Chạy tests

```bash
pip install fastapi pydantic httpx pytest
python -m pytest tests/ -q

node --test tests/desktop/
```

## License

MIT © 2026 thanhan-a17 — xem [upstream repo](https://github.com/thanhan-a17/grill-tab)
