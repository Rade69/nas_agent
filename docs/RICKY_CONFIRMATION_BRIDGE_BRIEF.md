# Ricky — Confirmation Bridge Implementation Brief

## Status

Not a numbered FAZA (all of FAZA 0-19 are done) — this is a bug-fix-sized backlog item that
surfaced during FAZA 13/14 security verification (`agent_reports/2026-07-06_faza13-14-security-verification-fix.md`).
Assign to: pi.

## The real problem (verified in code, not assumed)

`computer_type_text`, `computer_click`, `computer_click_element`, `computer_set_text_element`, and
`records_delete` all require an approved `confirmation_id` before the backend permission engine
(`app/agent/permission_engine.py` `check_permission()`) will let them run.

When a tool call is missing one, the backend correctly returns `ok: false, error: {code:
"CONFIRMATION_REQUIRED"}`. That code IS forwarded all the way to the renderer —
`electron/main.cjs`'s `adaptPythonToolResponse()` (line ~545) puts it on `result.errorCode`, and
`src/lib/realtime.ts` (line ~296) receives that `result` and hands it straight back to the model as
`function_call_output`.

**Nothing reads `result.errorCode` anywhere.** Checked with `grep -rn "errorCode" src/` — zero
matches outside the one place that sets it. The model gets a JSON error and has no tool it can call
to propose or approve a confirmation (no `propose_confirmation`-style entry exists in `toolSpecs`
in `electron/main.cjs`). `ConfirmationDialog.tsx` and the `/confirmations` REST API
(`ConfirmationService`, FAZA 9/10) work correctly, but nothing ever calls them automatically — the
existing `confirmations:create` IPC channel is only used if something *manually* proposes one.

Net effect: **every confirmation-required tool call from voice is a dead end today.** This was
already true for `records_delete` before this brief; FAZA 13/14's security fix just made it true
for 4 more tools, which makes it visible immediately since typing/clicking are core to Computer
Mode.

## What to build

Two pieces, both needed — half a fix (just the popup) leaves the retry silently broken.

### 1. Auto-propose a confirmation when a tool call is blocked

In `src/lib/realtime.ts`, where `executeTool()`'s result is handled (~line 296-303): if
`result.errorCode === "CONFIRMATION_REQUIRED"`, call a new bridge function instead of just
returning the raw error to the model. That function should:

- Call `window.ricky.createConfirmation({ action_name: name, payload: parsedArgs, risk_level:
  <tool's risk>, tool_name: name })` — this is the existing FAZA 9 IPC channel
  (`confirmations:create` → `POST /confirmations`). The `risk_level` needs to come from somewhere —
  either look it up from `handleToolsList()`'s tool specs (already fetched, has `risk`), or thread
  it through from the tool call site. Don't hardcode `"high"`.
- Reply to the model with a distinct, honest result — e.g. `{ ok: false, waiting_confirmation:
  true, message: "Waiting for your approval before doing this." }` — NOT the raw
  `CONFIRMATION_REQUIRED` error, so the model doesn't retry blindly in a loop. It should say
  something like "I need your OK first" and stop (`shouldCreateResponse` handling already exists
  for this pattern — see how `silent`/other result flags are used nearby).
- The existing `/confirmations/pending` poll (already running in `App.tsx`, see
  `agent_reports/2026-07-06_consolidate-backend-polling.md`) will pick this up automatically and
  `ConfirmationDialog` will render it — no changes needed there.

### 2. Auto-retry the original tool call once approved

This is the part that's easy to miss: approving the confirmation today just flips its status in
storage. Nothing re-runs the tool. The confirmation record already has everything needed to retry —
`ConfirmationService` stores `tool_name` and `payload` (see `app/schemas/confirmation.py`,
`ConfirmationResponse`). Wherever the current `onApprove` handler lives (trace from
`ConfirmationDialog`'s `onApprove` prop back to its caller in `App.tsx`), after a successful
`POST /confirmations/{id}/approve`:

- Read `tool_name` and `payload` off the now-approved confirmation.
- Call `executeTool({ name: tool_name, arguments: payload, context: { confirmation_id: id,
  computer_mode: true } })` — same IPC path every other tool call already uses.
- Handle the result the same way other tool results are handled (show artifact if any, log to
  Activity). Follow the existing "silent completion" pattern already used for thumbnails
  (RICKY_INSTRUCTIONS: "When a thumbnail finishes... do not announce it verbally. The UI updates
  silently.") — don't try to re-inject this into the Realtime voice turn, that turn is likely
  already closed by the time a human clicks approve. A silent UI update (Activity log entry +
  artifact if any) is enough; it doesn't need Ricky to say it out loud afterward.

## What NOT to do

- Don't touch `permission_engine.py`, `tool_executor.py`, or `tool_registry.py` — the backend side
  of this is correct and already tested (180 tests passing as of
  `agent_reports/2026-07-06_faza13-14-security-verification-fix.md`).
- Don't build a new dialog component — `ConfirmationDialog.tsx` already exists and works; reuse it.
- Don't add a `propose_confirmation` tool to the voice model's `toolSpecs` — that would let the
  model create arbitrary confirmations for anything, which is a bigger design question than this
  fix. The bridge described above creates the confirmation from the *already-attempted* tool call's
  exact arguments, which is what the payload_hash binding in `check_permission()` expects anyway.

## Acceptance criteria

- Asking Ricky (voice or text) to do something that needs `computer_type_text` with Computer Mode
  on results in: a confirmation dialog appearing (not a silent failure), Ricky saying it's waiting
  for approval (not retrying in a loop).
- Clicking "Pokreni" in the dialog actually performs the typing/click — not just marks the
  confirmation approved with nothing happening.
- Clicking "Otkaži" leaves nothing pending and the model is told the action was declined.
- `records_delete` (the pre-existing confirmation-required tool) works end-to-end through the same
  bridge — this fix isn't computer-use-specific.

## Test plan

- Unit/integration test for the auto-propose step (mock `executeTool` returning
  `CONFIRMATION_REQUIRED`, assert `createConfirmation` gets called with the right payload).
- Test for the auto-retry step (mock an approved confirmation, assert `executeTool` gets called
  again with the stored `tool_name`/`payload` and the new `confirmation_id`).
- Manual verification: run the app, enable Computer Mode, ask Ricky to type something into Notepad,
  confirm the dialog appears and approving it actually types the text.
