# Agent report — pi sesija: A1 (npm skripte) + B2 log hygiene + D1/D2 security audit

**Datum:** 2026-07-08
**Izvršio:** pi (po briefu `docs/PI_SECURITY_AUDIT_BRIEF.md` i `docs/PI_TASK_A1_B2_BRIEF.md`)

## Scope

- **D1/D2** (read-only security audit): glasovna potvrda high-risk akcija + IPC handler payload validacija. Rezultat: `agent_reports/2026-07-07_pi-security-audit-d1-d2.md`.
- **A1** (stvarna izmjena): dodavanje `ci` i `audit` skripti u `package.json` (supply-chain, Blok A iz `docs/SECURITY_DELEGATION_PLAN.md`).
- **B2** (read-only audit): log hygiene audit. Rezultat: `agent_reports/2026-07-08_pi-log-hygiene-audit.md`.

## GitNexus impact

Nije pokretan `gitnexus_impact` — A1 mijenja samo `scripts` blok u `package.json` (nije izvršni simbol, ne ulazi u call graph); D1/D2 i B2 su read-only (nijedan fajl koda nije diran). Blast radius A1: nula za runtime ponašanje (nove skripte se ne pozivaju nigdje u kodu, samo izložene `npm run`-u). Ručna analiza: sigurno.

## Šta je urađeno

**A1 — `package.json`:**
- Dodato u `scripts` blok, iza `package:win`:
  ```json
  "ci": "npm ci",
  "audit": "npm audit --omit=dev"
  ```
- Postojeće skripte netaknute. Nema izmjena dependencija, `package-lock.json` netaknut.

**D1/D2 — `agent_reports/2026-07-07_pi-security-audit-d1-d2.md`:**
- D1: glas **NE** može odobriti high-risk — jedini `approveConfirmation` poziv je `src/App.tsx:286` vezan na `onClick` dugmeta u `ConfirmationDialog` (sa 250 ms `armed` rate-limit). Backend (`permission_engine.py:117-160`) provjerava status/tool_name/payload_hash/expiry.
- D2: tabela svih IPC handlera — "thin pass-through" ka Python backendu koji radi pravu validaciju (Pydantic). Slabost: `companion:voice-state-update` proslijeđuje proizvoljan objekat u drugi renderer.
- Otkriven **R2 (najozbiljnije)**: legacy fallback fail-OPEN na potvrdama (`main.cjs:989-1004`) — kad Python padne a `LEGACY_FLAG≠0`, `computer_type_text`/`computer_click` rade bez odobrenja.

**B2 — `agent_reports/2026-07-08_pi-log-hygiene-audit.md`:**
- Console logovi čisti — nijedan ne ispisuje transkript/screenshot base64/email/tajne.
- Najozbiljniji nalaz: `ActionLogService` (`action_log.py:23-25`) upisuje puni `input_payload`/`output_payload` u SQLite DB → relevantno za B3.
- Otvorena pitanja: `RICKY_DEBUG_CONSOLE` u produkciji (O1), backend stdout proslijeđivanje (O2).

## Zašto je urađeno

Prema preporučenom redoslijedu u `docs/SECURITY_DELEGATION_PLAN.md`: D-blok verifikacije (jeftino, brzo) → B2 + A1 (laki delegabilni dobici). Briefovi su explicitno delegirali ove zadatke na pi uz obavezu read-only za audit-e i ograničenje na jedan fajl za A1.

## Kako je urađeno

- Read tool za sve relevantne fajlove (`realtime.ts`, `realtimeEventRouter.ts`, `ConfirmationDialog.tsx`, `permission_engine.py`, `confirmation_service.py`, `confirmations.py`, `ipc.cjs`, `preload.cjs`, `main.cjs` handleri, `logging.py`, `action_log.py`, `screenshot.py`, `pythonProcess.cjs`).
- `grep`/`bash` za lociranje log poziva i `approveConfirmation` call-sajtova.
- Edit tool za `package.json` (jedna precizna izmjena u `scripts` bloku).
- Write tool za oba audit izvještaja.

## Šta nije dirano

- `electron/main.cjs` — **netaknut** (Claude radi na njemu).
- `src/App.tsx`, `src/styles.css`, `src/components/*` — netaknuti (Codex domen, lokalizacija).
- Nijedan `.py`, `.ts`, `.cjs` — netaknuti (B2 i D1/D2 su read-only).
- `package-lock.json` i dependencije — netaknuti.
- Jedini dirani fajlovi: `package.json` (A1) + dva nova izvještaja u `agent_reports/`.

## Verifikacija

- A1: `node -e "JSON.parse(...)"` → JSON OK. `npm run typecheck` → čisto (tsc --noEmit bez grešaka).
- D1/D2: svaki nalaz ima tačnu referencu `fajl:linija` provjerenu read-om. Nije pokretan test suite (read-only, bez izmjena koda).
- B2: svaki log poziv u tabeli provjeren grep-om/read-om; potvrda da `tools_legacy/powershell/*` i `src/lib/**` nemaju logova.
- **Nije komitovano** — izmjene su u radnom stablu (koordinacija sa Claude/Codex po pravilima iz `SECURITY_DELEGATION_PLAN.md`).

## Rizici/ograničenja

- A1: nema rizika (nove skripte nisu nigdje pozvane; `npm ci`/`npm audit` nisu pokretani po briefu da se ne mijenja lockfile).
- D1/D2: izvještaj otkriva R2 (legacy fail-open) koji je **van uže D1/D2 domene** ali bitan — ostavljeno Claude-u da odluči o popravci.
- B2: najozbiljniji nalaz (`ActionLogService` payload u DB) pripada B3, ne B2 popravci.

## Potreban follow-up (za Claude)

1. **R2 (legacy fail-open)** — zasebni **[C]** zadatak: činiti legacy fallback fail-closed za high-risk `computer_*` bez obzira na `LEGACY_FLAG` (dira `main.cjs` + S-4 dizajn → nedelegabilno).
2. **R3 (`companion:voice-state-update`)** — dodati allowlistu `VoiceState` stringova ili odbacivanje non-string (Electron-side, Claude domen).
3. **R1 (izvor odobrenja)** — dodati `source` polje u confirmation rezoluciju (backend schema, Claude).
4. **B3/O3 (`ActionLogService` payload)** — maskirati osjetljiva polja + DB enkripcija/0600.
5. **O1 (`RICKY_DEBUG_CONSOLE`)** — provjeriti `env.cjs`/packaging da env ne curi u produkciji.
6. **Commitovanje** — A1 izmjena + tri izvještaja trebaju commit; po koordinacionim pravilima, predlažem da Claude commituje svoj domen, a pi-jevi izvještaji idu u istom ili zasebnom commitu uz korisničku potvrdu (miješanje sa nekomitovanim lokalizacijskim radom na `App.tsx`/`styles.css` i dalje blokira čist commit tih fajlova).

## Potrebna korisnička potvrda

- Da li commitovati A1 + izvještaje sada, ili čekati razrješenje koordinacije (trenutni miks na `App.tsx`/`styles.css`/`AGENTS.md`/`CLAUDE.md` je i dalje nekomitovan — `git status` pokazuje modified te fajlove).
- Da li krenuti na R2 popravku (legacy fail-closed) — to dira `main.cjs`, što je Claude domen.
