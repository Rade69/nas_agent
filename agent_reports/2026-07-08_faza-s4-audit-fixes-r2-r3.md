# Agent Report — S-4 audit popravke (R2 fail-closed legacy, R3 companion validacija)

**Datum:** 2026-07-08
**Agent:** Claude Code
**Scope:** Popravke nalaza R2 i R3 iz pi audita (`agent_reports/2026-07-07_pi-security-audit-d1-d2.md`), verifikovanih od strane Claude.

---

## Kontekst
pi je uradio read-only audit (D1/D2). Claude je verifikovao njegove `fajl:linija` tvrdnje u stvarnom kodu — tačne. Dva nalaza su tražila popravku (oba `electron/main.cjs`, sigurnosni domen = Claude).

## GitNexus impact
`handleToolsExecute` upstream: **LOW** (0 direktnih pozivalaca — IPC handler, registrovan ne pozvan). Izmjene aditivne.

## R2 — Legacy fallback fail-OPEN za high-risk (SREDNJE) — POPRAVLJENO
**Nalaz:** `handleToolsExecute` catch-fallthrough (`main.cjs`) je, kad Python padne + legacy uključen (`RICKY_USE_LEGACY_POWERSHELL_TOOLS≠0`), izvršavao `computer_type_text` (i sl.) preko legacy PowerShell puta **bez provjere odobrenja**. Legacy put ne može verifikovati `confirmation_id` (backend — jedini koji ga provjerava — je nedostupan). Suprotno S-4 fail-closed cilju.
**Napomena o ozbiljnosti:** legacy je **isključen po defaultu** (`isLegacyEnabled()` default `"0"`), pa nije eksploatabilno u standardnoj konfiguraciji — latentan rizik samo ako korisnik ručno uključi legacy.
**Popravka:** nova `LEGACY_FAIL_CLOSED_TOOLS` lista (`computer_type_text`, `computer_click`, `computer_click_element`, `computer_set_text_element` — svi `requires_confirmation=true` u Python definicijama). U catch bloku, čak i sa uključenim legacy-jem, ovi se **odbijaju** (`HIGH_RISK_LEGACY_BLOCKED`) umjesto da se izvrše nepotvrđeni. Low-risk alatke (open_app, screenshot, ui_inspect) i dalje smiju fallback.

## R3 — `companion:voice-state-update` prosljeđivao proizvoljan objekat (NISKO/SREDNJE) — POPRAVLJENO
**Nalaz:** `handleCompanionVoiceStateUpdate` je slao `state` (iz potencijalno XSS-kompromitovanog glavnog renderera) u **drugi renderer** (companion orb) bez ikakve provjere.
**Popravka:** `VALID_VOICE_STATES` allowlist (mirror `voiceState.ts` union); handler odbacuje sve što nije poznat string prije `forwardVoiceStateToCompanion`.

## Šta NIJE dirano
- Python backend, GUI (`App.tsx`/`styles.css` — Codex domen), permission_engine core.
- R1 (audit source) i R4/R5 — niski prioritet, odgođeno (vidi delegation plan).

## Verifikacija
- `npm run check` (node --check svih electron cjs) — čisto.
- `npm run smoke` — **SVE PROŠLO** (backend + tools end-to-end; R2 guard se ne okida jer Python radi, potvrđuje da nisam pokvario normalni put).
- R2 guard je u catch grani (Python fail) — ne utiče na normalno izvršavanje.

## Rizici / ograničenja
- R2 fail-closed znači: ako korisnik uključi legacy i Python padne, high-risk computer akcije NEĆE raditi (namjerno — sigurnost > dostupnost za high-risk). Low-risk fallback ostaje.
- Runtime provjera legacy puta nije rađena (traži uključen legacy + oboren backend); logika je jednostavna i pokrivena čitanjem.

## Follow-up
- Sljedeće po delegation planu. R1 (confirmation source polje) uz B1/keyring fazu.
