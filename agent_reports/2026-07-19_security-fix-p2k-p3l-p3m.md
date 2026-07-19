# Agent Report: P2-K, P3-L, P3-M sigurnosne ispravke

**Datum:** 2026-07-19
**Autor:** pi (co-authored)
**Plan:** `docs/SECURITY_FIX_PLAN_2026-07-19_FOR_PI.md` — preostali nalazi iz punog pregleda

## P2-K — external_content_seen per-conversation (tekstualni put)

**Problem:** `external_content_seen` se resetovao na `False` na početku svakog `handle_message` poziva (po turnu), ali tainted sadržaj ostaje u istoriji razgovora kroz turnove. Eskalacija na prompt-injection se gubila između poruka.

**Ispravka:**
- Dodata kolona `external_content_seen INTEGER NOT NULL DEFAULT 0` u `agent_conversations` tabelu (migracija u `db.py`)
- `agent_repo.py`: dodate metode `get_external_content_seen` i `set_external_content_seen` (atomirani SQL upiti)
- `conversation_state.py`: dodate `get_external_content_seen` i `set_external_content_seen` metode
- `runtime.py`: `external_content_seen` se čita iz `conversation_state` na početku `handle_message` i perzistira u bazi kad postane `True`

**Kriterij prihvatanja:** Poruka 1 pozove `web_search` (tainted), poruka 2 (novi `handle_message`, isti `conversation_id`) pozove `set_mode` → `set_mode` se eskalira u potvrdu (blokira se u autonomnom runtime-u), ne izvršava se tiho.

## P3-L — source: "ui" bypass kroz zaseban IPC kanal

**Problem:** `main.cjs` je vjerovao `source: "ui"` markeru koji dolazi iz renderera na generičkom `tools:execute` kanalu. Kompromitovan renderer je mogao da označi bilo koji tool call kao UI-porijeklo i zaobiđe permission engine.

**Ispravka:**
- `preload.cjs`: dodat `setModeFromUI(mode)` koji poziva IPC kanal `set_mode:ui-toggle`
- `main.cjs`: dodat handler za `set_mode:ui-toggle` koji primjenjuje mode switch direktno (bez backend-a)
- `main.cjs`: uklonjen `source === "ui"` bypass iz `handleToolsExecute`-ovog `set_mode` bloka
- `main.cjs`: pojednostavljen `set_mode` handler — više ne provjerava `toolContext.source`
- `App.tsx`: `switchMode` poziva `window.ricky.setModeFromUI` umjesto `window.ricky.executeTool` sa `source: "ui"`
- `vite-env.d.ts`: uklonjen `source?: "ui"` iz `RickyToolCall.context`, dodan `setModeFromUI` u `Window.ricky` tip

**Kriterij prihvatanja:** UI toggle i dalje radi bez backenda; poziv `tools:execute` sa `context.source="ui"` (ako ga neko pošalje) se više ne prepoznaje — uvijek ide kroz backend.

## P3-M — SQL f-string validacija identifikatora

**Problem:** `_existing_columns` i `_ensure_column` koriste f-string za SQL identifikatore. Iako su danas samo developer-konstante, budući pozivač sa spoljnim ulazom bi mogao da ih iskoristi za SQL injection.

**Ispravka:**
- `db.py`: dodat `_validate_identifier(name, context)` koji radi `assert` sa regex allowlistom `^[A-Za-z_][A-Za-z0-9_]*$`
- `_existing_columns` i `_ensure_column` sada validiraju sve identifikatore prije interpolacije
- `_ensure_column` takođe validira i tip kolone (prvi token definicije)

**Kriterij prihvatanja:** Allowlist/validacija na ulazu; test da neispravno ime tabele podiže `AssertionError`.

## Izmijenjeni fajlovi

| Fajl | Promjena |
|------|----------|
| `python_backend/app/storage/db.py` | P3-M + P2-K migracija |
| `python_backend/app/storage/repositories/agent_repo.py` | P2-K get/set external_content_seen |
| `python_backend/app/agent/conversation_state.py` | P2-K metode |
| `python_backend/app/agent/runtime.py` | P2-K per-conversation flag |
| `electron/main.cjs` | P3-L novi IPC kanal + uklonjen source:ui |
| `electron/preload.cjs` | P3-L setModeFromUI |
| `src/App.tsx` | P3-L switchMode koristi setModeFromUI |
| `src/vite-env.d.ts` | P3-L tipovi |

## Status

- **P2-K:** ✅ implementirano
- **P3-L:** ✅ implementirano
- **P3-M:** ✅ implementirano

Svi nalazi iz `SECURITY_FIX_PLAN_2026-07-19_FOR_PI.md` su sada zatvoreni.