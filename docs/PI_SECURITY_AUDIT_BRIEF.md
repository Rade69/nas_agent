# Brief za pi — Sigurnosni audit (D1 + D2), SAMO IZVJEŠTAJ

**Za:** pi (coding agent)
**Od:** Claude (koordinira sigurnosni rad)
**Tip zadatka:** READ-ONLY audit. **Ne mijenjaš nijedan fajl koda.** Rezultat je JEDAN markdown izvještaj.

---

## Kontekst
Radimo sigurnosno ojačavanje Ricky aplikacije (Electron + React + Python backend) po planu u `docs/SECURITY_DELEGATION_PLAN.md` i `docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md`. Tvoj zadatak su dvije verifikacije (D1, D2) iz tog plana. Cilj: utvrditi STVARNO stanje u kodu i napisati nalaz — NE popravljati (popravke radi/odobrava Claude).

## Pravila (obavezno)
- **NE mijenjaš kod.** Ni jedan `.ts`, `.tsx`, `.cjs`, `.py` fajl. Samo čitaš.
- **NE diraš GUI fajlove** (`src/App.tsx`, `src/styles.css`, `src/components/*`) — na njima radi Codex.
- Jedini fajl koji KREIRAŠ je izvještaj: `agent_reports/2026-07-07_pi-security-audit-d1-d2.md`.
- Piši na srpskom/bosanskom (latinica). Svaki nalaz sa tačnom referencom `fajl:linija`.
- Ako nešto nije jasno ili nađeš rizik — zapiši u izvještaj kao "otvoreno pitanje", ne pretpostavljaj.

## Zadatak D1 — Glasovna potvrda ne smije odobriti high-risk akciju
**Pitanje:** Može li se high-risk akcija (npr. slanje emaila, `computer_type_text`, `computer_click`) odobriti SAMO glasom ("da"/"pokreni"), ili je za high-risk obavezan klik?

Pregledaj:
- `src/lib/realtime.ts` i `src/lib/realtimeEventRouter.ts` — kako se obrađuje glasovni odgovor korisnika i da li on može okinuti `approveConfirmation` / confirmation flow.
- `src/components/ConfirmationDialog.tsx` — kako se odobrava (dugme vs. nešto glasovno).
- `python_backend/app/agent/permission_engine.py` i `confirmation_service` — da li backend razlikuje izvor potvrde.

**U izvještaj napiši:** da li glas može odobriti high-risk (DA/NE/DJELIMIČNO), tačne linije koje to pokazuju, i ako postoji rupa — opiši je (bez popravke).

## Zadatak D2 — IPC handleri validiraju payload
**Pitanje:** Da li svaki Electron IPC handler validira ulaz iz renderera (ne vjeruje mu slijepo), s obzirom da renderer može biti kompromitovan XSS-om?

Pregledaj:
- `electron/preload.cjs` — spisak izloženih kanala.
- `electron/core/ipc.cjs` i `electron/main.cjs` — svaki `ipcMain.handle(...)` / handler: da li provjerava tip/oblik argumenata prije upotrebe.

**U izvještaj napiši:** tabelu `kanal → validira li payload (DA/NE) → kratka napomena`. Istakni handlere koji slijepo prosljeđuju renderer podatke dalje (npr. u `executeTool`, `set_mode`, plan/confirmation pozive).

## Format izvještaja
Sekcije: `Datum`, `Scope`, `D1 nalaz`, `D2 nalaz`, `Rizici/otvorena pitanja`, `Preporuka za Claude`. Bez izmjena koda. Kad završiš, javi da je izvještaj spreman — Claude ga verifikuje i odlučuje o popravkama.
