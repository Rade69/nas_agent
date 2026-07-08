# Agent report — pi sesija: D1 + D2 sigurnosni audit (read-only)

**Datum:** 2026-07-07

## Scope

- **D1** — Read-only audit: može li glasovna potvrda ("da"/"pokreni") odobriti high-risk akciju (slanje emaila, `computer_type_text`, `computer_click`), ili je za high-risk obavezan klik?
- **D2** — Read-only audit: da li svaki Electron IPC handler validira payload iz renderera (ne vjeruje mu slijepo), s obzirom na mogući XSS u rendereru?
- Izvor zadatka: `docs/PI_SECURITY_AUDIT_BRIEF.md`. Plan: `docs/SECURITY_DELEGATION_PLAN.md` (Blok D), `docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md`.
- Output: jedan izvještaj sa nalazima `agent_reports/2026-07-07_pi-security-audit-d1-d2.md`. **Nijedan fajl koda nije mijenjan.**

## GitNexus impact

Nije pokretan `gitnexus_impact` — sesija je isključivo read-only (čitanje i grep izvornog koda, bez ijedne izmjene simbola). Blast radius: nula za runtime ponašanje, jer se ništa nije diralo. Po briefu, rezultat je dokumentovani nalaz, ne izmjena.

## Šta je urađeno

**D1 — utvrđeno da glas NE može odobriti high-risk akciju:**
- grep-om potvrđeno da je `src/App.tsx:286` (`handleApproveConfirmation` → `window.ricky.approveConfirmation`) jedini renderer poziv `approveConfirmation` u cijelom repo-u.
- `handleApproveConfirmation` se proslijeđuje kao `onApprove` u `ConfirmationDialog` (`src/App.tsx:463`); odobrenje se dešava isključivo preko `onClick` dugmeta u `src/components/ConfirmationDialog.tsx`, uz 250 ms `armed` rate-limit (`ConfirmationDialog.tsx` ~red 38) — nema `onKeyDown`, nema voice listenera, nema kratice.
- Potvrđeno da glasovni unos (`src/lib/realtime.ts`) ide kao `conversation.item` modelu i ne okida approval — Realtime samo *predlaže* confirmation (`realtime.ts:~266`) kad backend vrati `CONFIRMATION_REQUIRED`.
- Potvrđeno da model ne može forge-ati `confirmation_id`: backend `check_permission` (`python_backend/app/agent/permission_engine.py:117-160`) provjerava `status == approved`, `tool_name` match, `payload_hash` match i expiry.
- Zabilježena slabost u dubini obrane: backend ne bilježi izvor odobrenja (R1) — danas neeksploatabilno, ali rizik za buduće glasovne/auto-approve feature.

**D2 — tabela svih IPC handlera sa validacijom payloada:**
- Pročitani svi handleri u `electron/main.cjs` (585–740) + `electron/core/ipc.cjs` + `electron/preload.cjs` (spisak kanala) + `electron/core/companionWindow.cjs` + `electron/services/pythonClient.cjs`.
- Sastavljena tabela `kanal → validira li → napomena` za svih ~22 kanala.
- Zaključak: handleri su "thin pass-through" ka Python backendu koji radi pravu validaciju (Pydantic). Slabost: `companion:voice-state-update` (`main.cjs:694` → `companionWindow.cjs:124`) proslijeđuje proizvoljan objekat u drugi renderer bez provjere (R3).

**Otkriven R2 (van uže D1/D2 domene, ali najozbiljniji nalaz):**
- `handleToolsExecute` (`main.cjs:778-825`) za `PHASE11_DELEGATED_TOOLS` (uklj. `computer_type_text`, `computer_click`) delegira na Python; ako Python padne a `isLegacyEnabled()` (LEGACY_FLAG≠0), pada na legacy if-chain (`main.cjs:989-1004`) koji **ne provjerava `confirmation_id`/odobrenje**. Kompromitovani renderer/model može izvršiti high-risk akciju bez odobrenja kad god je backend nedostupan — direktno suprotno S-4 fail-closed cilju.

**Napisan završni izvještaj:** `agent_reports/2026-07-07_pi-security-audit-d1-d2.md` (D1 nalaz, D2 tabela, R1–R5, preporuka za Claude).

## Zašto je urađeno

Po preporučenom redoslijedu iz `docs/SECURITY_DELEGATION_PLAN.md`, D-blok verifikacija su jeftini, brzi zadaci koji daju brzu sliku stvarnog stanja prije skupljih popravki. Brief `docs/PI_SECURITY_AUDIT_BRIEF.md` je eksplicitno delegirao D1/D2 na pi kao read-only audit (pi smije čitati/predlagati, ne mijenjati kod), sa obavezom da Claude verifikuje nalaz i odlučuje o popravkama — u skladu sa koordinacionim pravilima (sigurnosni sloj = Claude domen).

## Kako je urađeno

- `read` za: `src/lib/realtime.ts`, `src/lib/realtimeEventRouter.ts`, `src/lib/voiceState.ts`, `src/components/ConfirmationDialog.tsx`, `python_backend/app/services/confirmation_service.py`, `python_backend/app/api/confirmations.py`, `python_backend/app/agent/permission_engine.py`, `python_backend/app/agent/tool_registry.py` (relevantni dijelovi), `electron/core/ipc.cjs`, `electron/preload.cjs`, `electron/main.cjs` (handleri 585–740, `handleToolsExecute` 775–825, legacy chain 985–1025, `asObject` 446, kill-switch/self-test 1798–1864), `electron/core/companionWindow.cjs`, `electron/services/pythonClient.cjs`.
- `bash`/`grep` za: lociranje svih `approveConfirmation` call-sajtova (potvrda jedinstvenosti renderer poziva), spisak `ipcMain.handle` kanala, `PHASE11_DELEGATED_TOOLS`, `requires_confirmation`/`risk` u tool definicijama.
- `write` za finalni izvještaj `agent_reports/2026-07-07_pi-security-audit-d1-d2.md`.

## Šta nije dirano

- **Nijedan fajl koda** nije mijenjan — read-only audit po briefu.
- `electron/main.cjs`, `src/App.tsx`, `src/styles.css`, `src/components/*`, svi `.py` — netaknuti.
- Nije pokretan test suite niti build (bez izmjena koda, nije bilo potrebe).
- Nije komitovano — samo kreiran novi izvještaj u `agent_reports/`.

## Verifikacija

- Svaki nalaz u izvještaju ima tačnu referencu `fajl:linija` provjerenu `read`-om (npr. `App.tsx:286`, `ConfirmationDialog.tsx` onClick + `armed`, `permission_engine.py:117-160`, `main.cjs:989-1004`).
- D1 tvrdnja "jedini renderer `approveConfirmation` poziv" potvrđena grep-om po `src/`, `electron/`, `python_backend/`.
- D2 tabela pokriva sve kanale iz `preload.cjs` izložene površine i `main.cjs` handler mape (redovi 1734–1761).
- Nema automatskog testa za D1/D2 (audit prirode), pa verifikacija počiva na code-tracingu i cross-checku renderer↔backend↔Electron lanca.

## Rizici/ograničenja

- **R2 (Visoko)** otkriven ali **nije popravljeno** — ostavljeno Claude-u jer dira `main.cjs` + S-4 fail-closed dizajn (nedelegabilno). Ovo je najvažniji otvoreni rizik iz ove sesije.
- **R3 (Nisko–Srednje)** — `companion:voice-state-update` proslijeđuje proizvoljan payload u companion renderer; audita konzumacije u `CompanionOrb.tsx` nije urađen (izvan D1/D2 briefa, ali logično povezano).
- **R1 (Srednje)** — backend ne bilježi izvor odobrenja; danas neeksploatabilno, rizik za buduće feature.
- D1/D2 su audit-i — ne dokazuju ispravnost testovima, već statičkom analizom koda. Ako se kasnije doda voice→approve path, D1 nalaz prestaje važiti i treba ga ponoviti.

## Potreban follow-up (za Claude)

1. **R2** — zasebni **[C]** zadatak: legacy fallback fail-closed za high-risk `computer_*` bez obzira na LEGACY_FLAG (ili eksplicitna dokumentacija zašto je fail-open prihvatljivo). Dirao `main.cjs` → nedelegabilno.
2. **R3** — dodati Electron-side tip validaciju za `companion:voice-state-update` (allowlista `VoiceState` stringova); provjeriti `CompanionOrb.tsx` konzumaciju.
3. **R1** — dodati `source` polje u confirmation rezoluciju (backend schema) — može se kombinovati sa B1/keyring fazom.
4. **R4** — provjeriti tip validaciju u legacy `computerTypeText`/`computerClick`.

## Potrebna korisnička potvrda

- Da li krenuti na popravku R2 (legacy fail-closed) — to preuzima Claude i dira `main.cjs`.
- Izvještaj `2026-07-07_pi-security-audit-d1-d2.md` čeka Claude verifikaciju nalaza prije primjene bilo kakvih popravki.
