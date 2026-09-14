# Nguồn các skill đã vendor

Các skill dưới đây được sao chép từ mã nguồn MIT để dùng cục bộ trong Hermes. Khi cập nhật, kiểm tra source gốc và license trước khi ghi đè.

## addyosmani/agent-skills
Nguồn: https://github.com/addyosmani/agent-skills — MIT, Copyright (c) 2025 Addy Osmani.

Được cài vào `software-development/`:
- `incremental-implementation`
- `source-driven-development`
- `doubt-driven-development`
- `security-and-hardening`
- `api-and-interface-design`
- `documentation-and-adrs`
- `frontend-ui-engineering`
- `context-engineering`

Các tài liệu dùng chung của source được sao chép vào `references/` của các skill cần chúng.

## wshobson/agents
Nguồn: https://github.com/wshobson/agents — MIT, Copyright (c) 2024 Seth Hobson.

Được cài vào `software-development/`:
- `architecture-patterns`
- `python-project-structure`

## ghostinthedata-info/skills
Nguồn: https://github.com/ghostinthedata-info/skills — MIT, Copyright (c) 2026 Chris Hillman.

Được cài vào `data-engineering/`:
- `data-modelling`
- `profile-data`
- `pipeline-design`
- `test-data`
- `data-security-classification`

## rlaope/oh-my-hermes
Source: https://github.com/rlaope/oh-my-hermes — MIT, Copyright (c) 2026 oh-my-hermes contributors.

Skills installed (flat `$HERMES_HOME/skills/<name>/`):
- `accessibility-audit`
- `adversarial-consensus`
- `ai-slop-cleaner`
- `codebase-onboarding`
- `codebase-uml`
- `data-analysis`
- `deploy-and-monitor`
- `idea-to-deploy`
- `inference-serving`
- `jit-learn`
- `llm-app-dev`
- `native-debugging`
- `paper-learning`
- `refactor-plan`
- `rules-distill`
- `run-efficiency`
- `tech-debt-audit`
- `verification-gate`
- `web-research`
- `workspace-audit`
- `context-budget`
- `work-loop`
- `perf-tuning`
- `delivery-plan`
- `qa-gate`
- `deep-research`
- `parallel-work`

### MIT License Text

```
MIT License

Copyright (c) 2026 oh-my-hermes contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

_Note: Skills renamed to generic names (no external brand prefix) upon vendoring into Hermes-Agents._
