---
title: "OpenAI Realtime gpt-realtime-2.1-mini A/B test priprema"
date: 2026-09-09
branch: qt-desktop-migration
commit: f3e00fb
---

# OpenAI Realtime 2.1-mini — A/B test priprema

## 1. Početni branch i SHA
- branch: `qt-desktop-migration`
- start SHA: `20171b4`

## 2. SHA
- implementation SHA: `f3e00fb` (feat + test + report)
- final HEAD: `60a0b1c` (nakon fail-closed korekcije)

## 3. git status
- Čist (sve commit-ovano). `docs/openai-api-key.txt` više NIJE prisutan (korisnik ga je uklonio).

## 4. Izmijenjeni fajlovi
- `python_backend/app/core/config.py` — `openai_realtime_model` + allowlist + `resolve_openai_realtime_model`
- `python_backend/app/schemas/realtime.py` — `RealtimeSessionResponse.model`
- `python_backend/app/api/realtime.py` — backend override modela + model u response
- `desktop/voice/session.py` — desktop koristi backend-returned model
- `.env.example` — `OPENAI_REALTIME_MODEL` primjer
- testovi: `python_backend/tests/test_realtime.py`, `test_realtime_model.py`, `desktop/tests/test_realtime_model.py`

## 5. Šta je implementirano
- Konfigurabilni OpenAI Realtime model, backend-owned (source of truth).
- Allowlist `{gpt-realtime, gpt-realtime-2.1-mini}`, fail-closed (nepoznat model = ValueError, NEMA silent fallback).
- Backend overrideuje desktop-ov session model na `settings.openai_realtime_model` — konstrukcijski onemogućeno da desktop otvori WebSocket prema modelu B dok je token mintan za model A.
- Response `/realtime/session` vraća `model` (authoritative) + ephemeral `value`.
- Desktop koristi backend-returned model za WebSocket URL i `session.update`.

## 6. OPENAI_API_KEY
- **Nije mijenjan, nije brisan, nije kopiran, nije ispisan.** YES.

## 7. Drugi OpenAI ključ
- **Nije dodat.** NO. (koristi se postojeći `OPENAI_API_KEY`)

## 8. Gdje se bira OPENAI_REALTIME_MODEL
- `python_backend/app/core/config.py` (`resolve_openai_realtime_model`, čita `OPENAI_REALTIME_MODEL` env; `.env.local` učitava samo backend).

## 9. Default vrijednost
- `gpt-realtime`

## 10. Kako se aktivira mini
- U `.env.local`: `OPENAI_REALTIME_MODEL=gpt-realtime-2.1-mini` (već dodato lokalno). Restart.

## 11. Automatski testovi
- focused Realtime/config: backend 9 passed, desktop 3 passed
- backend suite: **425 passed** (bio 419)
- desktop suite: **67 passed** (bio 63)

## 12. Live preflight
- backend `/health`: OK
- `/realtime/session`: OK, `model=gpt-realtime-2.1-mini`
- WebSocket `session.created` + audio: **NIJE testirano** (potreban stvarni audio — dio ručnog A/B testa)

## 13. OpenAI API/WebSocket greške
- Nema. Mini model je dostupan postojećem ključu (credential mint uspio).

## 14. Security invarijante
- INV-RT-1 (permanent ključ backend-only): PASS
- INV-RT-2 (desktop samo ephemeral): PASS
- INV-RT-3 (nema drugog ključa): PASS
- INV-RT-4 (ne učitava .env.local u desktop voice): PASS
- INV-RT-5 (ToolExecutor/PermissionEngine/confirmation netaknuti): PASS
- INV-RT-6 (model switch ne zaobilazi confirmation): PASS (isti ToolBridge/guards)
- INV-RT-7 (ne loguje key/credential): PASS
- INV-RT-8 (nema silent fallback): PASS (fail-closed allowlist + test)

## 15. Spremno za ručni A/B test
- DA (env switch + restart; isti `OPENAI_API_KEY`, isti mikrofon/zvučnik/prompt/toolovi).

## 15b. Fail-closed korekcija (C-1/C-3, naknadno)
- Desktop `_resolve_credential` više NEMA silent fallback na `gpt-realtime`. Ako backend ne vrati authoritative `model` (ili `value`), desktop emituje grešku i session NE počinje. Vraća `(value, model)` samo ako su OBA prisutna. Testovi: `test_resolve_credential_fails_if_backend_model_missing`, `..._credential_missing`, `..._both_missing`.

## 16. Variant A (gpt-realtime)
1. U `.env.local`: `OPENAI_REALTIME_MODEL=gpt-realtime`
2. Restartuj Ricky.
3. Pokreni A/B scenarije AB-1…AB-10.

## 17. Variant B (gpt-realtime-2.1-mini)
1. U `.env.local`: `OPENAI_REALTIME_MODEL=gpt-realtime-2.1-mini`
2. Restartuj Ricky.
3. Pokreni iste A/B scenarije AB-1…AB-10.

## 18. A/B tabela (za subjektivno popunjavanje)

| Metrika | gpt-realtime | gpt-realtime-2.1-mini |
| --- | ---: | ---: |
| Session connect | | |
| Median turn → first audio | | |
| Srpski STT | /5 | /5 |
| Srpski izgovor | /5 | /5 |
| Kvalitet odgovora | /5 | /5 |
| Tool selection | /5 | /5 |
| Tool arguments | /5 | /5 |
| Confirmation flow | PASS/FAIL | PASS/FAIL |
| Barge-in | x/3 | x/3 |
| Errors | | |
| Reconnects | | |
| Usage (ako API daje) | | |

## 19. Rizici/ograničenja
- WebSocket + audio pipeline NIJE end-to-end testiran automatski (headless); mini A/B je ručni test.
- `docs/openai-api-key.txt` je potencijalna tajna — treba obrisati.

## 20. Preporuka
- Nema dovoljno evidence za preporuku dok se A/B test ne uradi. Tehnički mini je dostupan i prolazi credential mint — kvalitet je stvar ručnog A/B testa.
