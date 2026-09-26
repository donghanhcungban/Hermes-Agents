# Hermes-Agents engineering workspace

This repository is a Hermes extension package, not the Hermes core runtime.
Read `docs/ENGINEERING_WORKBENCH_VI.md` for the implemented capability boundaries,
installation, audit findings and staged engineering roadmap.

Preserve provider configuration, credentials and user skill edits. Never run
installers against a real Hermes home during tests; use temporary directories.
Workbench installation is separate: `install_workbench.py` is dry-run by default.
New native tools live in `plugins/engineering-workbench`; keep handlers JSON-returning,
with strict validation, no hidden network/subprocess calls and no false completion.

For parallel work, assign disjoint file ownership to native Hermes subagents when
available. One integrator reviews shared-file changes and runs assembled tests.
Do not claim a subagent was invoked when only a plan was created.

Validation:
```
python -m unittest discover -s tests -p "test_*.py" -v
```
Optional office dependencies are in `requirements-office.txt`; the dedicated
workbench workflow installs them. Label skips and distinguish unit/contract tests
from live Hermes, CAD/BIM or visual Office verification. MEP outputs stay preliminary;
no construction approval, automatic deployment or production mutation is implied.
