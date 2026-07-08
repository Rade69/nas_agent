# Brief za pi — A1 (npm skripte) + B2 (log hygiene audit)

**Za:** pi · **Od:** Claude
**Dva zadatka:** A1 = mala stvarna izmjena (jedan fajl). B2 = SAMO izvještaj (bez izmjena koda).

---

## Pravila (obavezno)
- **Jedini fajl koda koji smiješ mijenjati je `package.json` (za A1).** Ništa drugo.
- **NE diraj:** `electron/main.cjs` (Claude trenutno radi na njemu), `src/App.tsx`, `src/styles.css`, `src/components/*` (Codex), nijedan `.py`, nijedan drugi `.cjs`/`.ts`.
- Za B2 praviš SAMO izvještaj: `agent_reports/2026-07-08_pi-log-hygiene-audit.md`. Bez izmjena koda.
- Srpski/bosanski, latinica. Reference `fajl:linija`. Ne pretpostavljaj — nejasno → "otvoreno pitanje".

---

## Zadatak A1 — npm supply-chain skripte (`package.json`)
Dodaj u `scripts` blok dvije nove skripte (ne mijenjaj postojeće):
- `"ci": "npm ci"`
- `"audit": "npm audit --omit=dev"`

**Acceptance:**
- `package.json` je validan JSON, postojeće skripte netaknute.
- `npm run typecheck` i dalje prolazi (potvrdi da nisi pokvario JSON).
- NE pokreći `npm ci` ni `npm audit` (mogu dugo trajati / mijenjati lockfile) — samo dodaj skripte.

**Napomena:** ne diraj `package-lock.json`, ne dodaj/uklanjaj dependencije.

---

## Zadatak B2 — Log hygiene audit (SAMO izvještaj)
**Pitanje:** Da li se igdje u logove ispisuje osjetljiv sadržaj — pun transkript glasa, tekst screenshot-a/base64, sadržaj emaila, payload sa korisničkim podacima, ili tajne?

Pregledaj (READ-ONLY) sve `console.log` / `console.warn` / `console.error` / `logger.*` / `print(` / `logging.*` u:
- `electron/**` (uključujući `main.cjs`, `core/*`, `services/*`, `tools_legacy/*`)
- `python_backend/app/**`
- `src/lib/**` (NE `src/App.tsx`/`components` — to je Codex)

Za svaki log koji ispisuje **promjenjiv/korisnički sadržaj** (ne statične poruke), zapiši:
`fajl:linija` → šta se ispisuje → rizik (Visoko: transkript/screenshot/email/tajna; Srednje: payload/argumenti; Nisko: id/status) → prijedlog (maskirati / ukloniti / ostaviti).

Posebno provjeri:
- Ispisuje li se ikad cijeli `transcript`, `args`/`arguments`, `payload`, `content`, screenshot base64, email `body`/`text`.
- Napomena: backend već ima `SecretRedactionFilter` za API ključeve/token (`python_backend/app/core/logging.py`) — to NE pokriva PII/transkript. Fokus je na PII/sadržaj.

**Format izvještaja:** `Datum`, `Scope`, `Tabela nalaza (fajl:linija/sadržaj/rizik/prijedlog)`, `Zaključak`, `Preporuka za Claude`. Bez izmjena koda za B2.

---

Kad završiš oba, javi. Claude verifikuje A1 (build/typecheck) i B2 izvještaj (provjera fajl:linija), pa primjenjuje popravke iz B2 (u svom domenu).
