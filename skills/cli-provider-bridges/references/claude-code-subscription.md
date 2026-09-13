# Claude Code subscription bridge notes

## Verified invocation pattern

```bash
claude -p \
  --tools '' \
  --no-session-persistence \
  --output-format json \
  --json-schema '<schema>' \
  --model sonnet \
  '<prompt>'
```

- `--output-format json` returns a JSON envelope. With `--json-schema`, read the model payload from `structured_output`.
- `--tools ''` prevents Claude Code from executing its own tools; the parent agent can still receive validated tool-call intents and execute its own tools.
- `--no-session-persistence` avoids storing the bridge request as a reusable Claude Code session.
- Do **not** add `--bare` for subscription-backed invocations: a verified local run reported “Not logged in” despite `claude auth status` showing a signed-in Pro account. Removing `--bare` restored successful subscription execution.

## Model aliases

Claude Code CLI accepts stable aliases such as `fable`, `opus`, `sonnet`, and `haiku`; the CLI resolves them to the current available model versions.

A live bridge test succeeded for `sonnet`, `opus`, and `haiku` using a one-token `OK` response. `fable` was accepted but returned an explicit entitlement error: it required additional usage credits. Preserve that message for the user; it is a plan/credit condition, not a bridge failure.

## Install smoke test

After installation, restart the loopback bridge and verify:

```bash
python manage.py setup-claude-code --model sonnet
python manage.py stop
python manage.py start
curl http://127.0.0.1:<port>/v1/claude-code/models
```

Then POST an OpenAI-compatible non-stream completion and assert the response has a `choices[0].message.content` value. Also run `python manage.py setup-claude-code --help`: this catches command-dispatch typos that import-level or unit tests may not exercise.
