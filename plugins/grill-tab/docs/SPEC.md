# grill-tab — Spec

Standalone Hermes plugin. Press **Tab** in the Desktop composer to interrogate a draft before it
becomes the first message of a session; **Enter** synthesizes an execution brief and places it in
the composer for the user to review and send. One folder, no core patches.

## Design decisions

- The engine may declare the ladder done ("nothing critical left"). Enter still writes the brief;
  Tab forces one more question.
- The brief is **synthesized** by the auxiliary model from the original intent and the settled
  ladder. The local template is a fallback only (engine unreachable, unusable output).
- **Enter never auto-sends.** The brief is placed into the composer with the caret at the end; the
  user reads it and presses Enter themselves.
- While the ladder is open the composer is cleared (the first dimmed row carries the draft); a full
  exit restores the draft untouched.
- The recommended answer lives only in the ghost placeholder (Tab/Enter on an empty answer accepts
  it); option chips exclude it. No buttons duplicate a keyboard hint.
- General agentic work first: research, writing, planning, operations, design, analysis, personal
  errands — and code. Nothing in the prompts presumes software.

## Fidelity contract (the brief)

The brief is a faithful restatement, not an improved idea:

- **Goal** restates the original intent as an outcome, at the user's stated ambition.
- **Settled** means: stated in the intent, answered in the ladder, or a recommendation the user
  accepted (including by deferring — "you decide", "which is simplest?"). Nothing else is settled.
- No added deliverables, steps, audiences, channels, features, or polish. No change of medium, tone,
  length, or language.
- Every line under *Settled decisions* traces to a settled item and is written as a directive.
- Anything the work still needs but nobody settled goes under *Assumptions*, phrased conservatively
  (smallest, least surprising option)