# Hermes state.db — Schema Reference

SQLite database at `$HERMES_HOME/state.db`. Read-only from outside Hermes.

## Table: `sessions`

One row per conversation/chat session.

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT PK | e.g. `20260902_084324_a82f35`; cron jobs prefix with `cron_` |
| `title` | TEXT | Auto-generated or null |
| `model` | TEXT | e.g. `claude-sonnet-4-6` |
| `billing_provider` | TEXT | e.g. `anthropic` |
| `billing_base_url` | TEXT | API base URL used |
| `billing_mode` | TEXT | Usually empty string |
| `started_at` | REAL | Unix timestamp (float) |
| `ended_at` | REAL | Unix timestamp; NULL if session still active |
| `end_reason` | TEXT | Why session ended |
| `message_count` | INTEGER | Total messages in session |
| `tool_call_count` | INTEGER | Total tool calls |
| `api_call_count` | INTEGER | Total API round-trips |
| `input_tokens` | INTEGER | Raw user-turn tokens (NOT counting cache) |
| `output_tokens` | INTEGER | Generated tokens |
| `cache_read_tokens` | INTEGER | Cache HIT tokens (dominant for long sessions) |
| `cache_write_tokens` | INTEGER | Cache WRITE tokens |
| `reasoning_tokens` | INTEGER | Thinking/reasoning tokens |
| `estimated_cost_usd` | REAL | Estimated USD cost |
| `actual_cost_usd` | REAL | Reported actual cost (often 0 if not billed directly) |
| `cost_status` | TEXT | `estimated`, `actual`, or NULL |
| `cost_source` | TEXT | e.g. `official_docs_snapshot` |
| `archived` | INTEGER | 0=active, 1=archived (filter with `WHERE archived=0`) |
| `hidden` | INTEGER | 0=visible |
| `pinned` | INTEGER | 0/1 |
| `profile_name` | TEXT | Hermes profile (e.g. `default`) |
| `cwd` | TEXT | Working directory when session started |
| `git_branch` | TEXT | Git branch if in a repo |
| `git_repo_root` | TEXT | Repo root path |
| `source` | TEXT | Platform source |
| `chat_id` | TEXT | Platform chat ID |
| `parent_session_id` | TEXT | For sub-sessions |
| `last_activity_at` | REAL | Timestamp of last message |

## Table: `session_model_usage`

Per-model breakdown within a session (a session can use multiple models).

| Column | Type | Notes |
|--------|------|-------|
| `session_id` | TEXT | FK → sessions.id |
| `model` | TEXT | Model name |
| `billing_provider` | TEXT | |
| `billing_base_url` | TEXT | |
| `task` | TEXT | Task type (e.g. `background_review`, empty for main) |
| `api_call_count` | INTEGER | |
| `input_tokens` | INTEGER | |
| `output_tokens` | INTEGER | |
| `cache_read_tokens` | INTEGER | |
| `cache_write_tokens` | INTEGER | |
| `reasoning_tokens` | INTEGER | |
| `estimated_cost_usd` | REAL | |
| `actual_cost_usd` | REAL | |
| `first_seen` | REAL | Unix timestamp |
| `last_seen` | REAL | Unix timestamp |

## Table: `messages`

Full message log. Key columns:

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `session_id` | TEXT | FK → sessions.id |
| `role` | TEXT | `user`, `assistant`, `tool` |
| `content` | TEXT | Message text / JSON |
| `tool_calls` | TEXT | JSON array of tool calls |
| `tool_name` | TEXT | For tool-result rows |
| `timestamp` | REAL | Unix timestamp |
| `token_count` | INTEGER | Token count for this message |
| `finish_reason` | TEXT | e.g. `end_turn`, `tool_use` |
| `active` | INTEGER | 1=in current context window |
| `compacted` | INTEGER | 1=compacted/summarised |

## Sample Queries

```python
import sqlite3, datetime

db_path = r'C:\Users\liend\AppData\Local\hermes\state.db'
conn = sqlite3.connect(db_path)

# Today's summary
today_start = datetime.datetime.now().replace(
    hour=0, minute=0, second=0, microsecond=0).timestamp()
today = conn.execute('''
    SELECT COALESCE(SUM(estimated_cost_usd),0),
           COALESCE(SUM(input_tokens),0),
           COALESCE(SUM(output_tokens),0),
           COALESCE(SUM(cache_read_tokens),0),
           COALESCE(COUNT(*),0),
           COALESCE(SUM(api_call_count),0)
    FROM sessions WHERE archived=0 AND started_at >= ?
''', (today_start,)).fetchone()
# Returns: (cost, input, output, cache_read, session_count, api_calls)

# Recent sessions with token data
rows = conn.execute('''
    SELECT id, title, model, started_at, ended_at,
           input_tokens, output_tokens, cache_read_tokens,
           estimated_cost_usd, api_call_count, message_count
    FROM sessions
    WHERE archived = 0
    ORDER BY started_at DESC
    LIMIT 30
''').fetchall()

# All-time totals
total = conn.execute('''
    SELECT COALESCE(SUM(estimated_cost_usd),0),
           COALESCE(SUM(input_tokens),0),
           COALESCE(SUM(output_tokens),0),
           COALESCE(COUNT(*),0)
    FROM sessions WHERE archived=0
''').fetchone()

conn.close()
```

## Notes

- `input_tokens` is usually very small (a few dozen) because most context is served from cache — the real "tokens processed" is `input_tokens + cache_read_tokens + cache_write_tokens`
- `estimated_cost_usd` is calculated by Hermes using official pricing snapshots; `actual_cost_usd` is often 0 unless the provider reports it back
- Active sessions have `ended_at = NULL`; detect with `WHERE ended_at IS NULL AND started_at IS NOT NULL`
- Cron job sessions have IDs like `cron_<hash>_<timestamp>`
- Always use `WHERE archived = 0` to exclude deleted/archived sessions
