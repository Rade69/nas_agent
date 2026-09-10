# MiniMax provider — MM-0…MM-3 (tekst/text agent)

## Datum

2026-09-09

## Scope

Uvođenje provider abstrakcije (OpenAI + MiniMax) — zadatak "provider selection". Urađeni MM-0 (discovery), MM-1 (contracts), MM-3 (MiniMax M3 text client). Voice dio (MM-2 refactor / MM-4 TTS / MM-5 STT) je BLOCKED — vidi STOP-6 niže.

## GitNexus impact

Nije dostupno. Ručna analiza: `python_backend/` izmjene (config/model_client/main/providers) su čist refaktor + dodavanje — `ModelClient` Protocol već postojao, ponašanje OpenAI-a nepromijenjeno (parsiranje izdvojeno, HTTP logika izdvojena, factory umjesto direktnog `OpenAIModelClient`). Rizik ~nula (dokazano: 419 backend testova zeleno).

## Šta je urađeno (po fazi)

### MM-0 — Discovery ✅
- `docs/MINIMAX_PROVIDER_FINDING.md` — verifikacija zvanične MiniMax dokumentacije (`llms.txt`, `api-overview`, `text-chat-openai`).

### MM-1 — Provider contracts ✅
- `python_backend/app/agent/providers.py` — `AIProvider` enum, `ProviderCapabilities` (frozen, capability-based), `CAPABILITIES` mapa, `create_model_client` factory.
- `config.py` — `RICKY_AI_PROVIDER`, `MINIMAX_API_KEY`, `MINIMAX_MODEL`, `OPENAI_MODEL`.

### MM-2 — OpenAI refactor ✅ (samo text; već je bio iza `ModelClient` Protocol-a)
- `model_client.py` — izdvojena zajednička `_post_chat_completions` + `_parse_chat_completion_response`; `OpenAIModelClient` ponašanje nepromijenjeno.

### MM-3 — MiniMax M3 model client ✅
- `MiniMaxModelClient` — OpenAI-compatible endpoint (`https://api.minimax.io/v1/chat/completions`), `thinking: {type: disabled}` (Ricky ne treba reasoning blok), MiniMax `base_resp` error surfacing (1002/1004/…).

## Verifikacija

- Backend: **419 passed** (412 + 7 novih).
- `test_provider_selection.py`: factory (openai/minimax/bogus→openai), capabilities (MiniMax nema realtime_audio_input/interruption), MiniMax parsing (tool_calls, thinking disabled, base_resp error, MISSING_API_KEY).

## Status (iskreno, po planu §39)

| Stavka | Status |
|---|---|
| MiniMax M3 text agent (backend, tool calling kroz isti ToolExecutor) | ✅ IMPLEMENTED + TESTED WITH MOCK (ne LIVE — nema ključa) |
| Provider selection (env `RICKY_AI_PROVIDER`) | ✅ IMPLEMENTED |
| MiniMax native Realtime voice | ❌ NOT AVAILABLE (nema ga u zvaničnoj dokumentaciji) |
| MiniMax composite voice (STT→M3→T2A) | 🟡 BLOCKED — STOP-6 (vidi niže) |
| Settings UI (Qt) | ⬜ MM-6, zavisi od QM-5 (još ne postoji) |

## STOP-6 — ključno otkriće za voice

MiniMax NEMA ephemeral-token mehanizam kao OpenAI (`client_secrets`). Za OpenAI voice, desktop dobija kratkoživući token — nikad trajni ključ (INV-5). Za MiniMax voice (STT + M3 + T2A), desktop proces bi morao držati **trajni MiniMax API ključ** (audio je klijentski resurs), što krši INV-5 ("Qt UI nikad ne dobija API ključ direktno").

Dvije opcije (arhitektonska odluka, ne kod):
1. **Backend proxy** — desktop šalje audio/tekst backend-u, backend drži MiniMax ključ i proxy-uje STT/M3/T2A. Nova arhitektura (voice kroz backend, latencija), ali čuva INV-5.
2. **Desktop drži MiniMax ključ** — jednostavno, ali krši INV-5 (bezbjednosna regresija u odnosu na OpenAI ephemeral obrazac).

Ne implementiram voice dok korisnik ne odluči (STOP-6 = "API key would need to cross an insecure UI/process boundary").

## Potreban follow-up

- Odluka korisnika o STOP-6 (backend proxy vs desktop ključ).
- MM-2 voice refactor (OpenAI session iza RealtimeProvider), MM-4 (T2A streaming), MM-5 (STT), MM-6 (settings UI), MM-7 (parity testovi), MM-8 (latency).

## Potrebna korisnička potvrda

- Kako riješiti MiniMax voice secret problem (STOP-6)?
- Da li je env-based provider selection prihvatljiv privremeno (dok QM-5 ne doda Settings UI)?
