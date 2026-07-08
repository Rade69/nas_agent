# Plan delegiranja — preostali sigurnosni rad

**Datum:** 2026-07-07
**Svrha:** Razbiti preostali posao na zadatke koje mogu izvršiti jeftiniji modeli, uz obavezu da **Claude nakon svake akcije uradi analizu/verifikaciju** prije nego se pređe na sljedeći. Izvor istine za statuse je [SECURITY_GAP_ANALYSIS_AND_PLAN.md](./SECURITY_GAP_ANALYSIS_AND_PLAN.md).

---

## Stanje (2026-07-07)

**Završeno i commitovano** (5 sigurnosnih commitova + Codex GUI):
- S-1 schema validacija (`dbbc9a8`) · S-2/S-9 prompt injection + red-team (`a77b0e8`) · S-3 CSP (`94b6e7c`) · S-4 fail-closed + kill-switch (`d319020`) · Codex GUI (`562db35`).
- **S-4 dopuna (Escape + Ctrl+Alt+K + banner, uklonjeni F10/F11): verifikovana, RADI, ali NEKOMITOVANA** — jer je u istim fajlovima (`App.tsx`, `styles.css`) sa paralelnim tuđim radom (lokalizacija). Vidi "Koordinacija" ispod.

---

## Koordinacija (OBAVEZNO — inače se modeli gaze)

Problem koji se već desio: dva modela edituju iste fajlove (`App.tsx`, `styles.css`, `realtime.ts`) → izmjene se miješaju, ne mogu se čisto commitovati, i postoji rizik da "rewrite" jednog modela obriše rad drugog (već se desilo sa pi/Codex ranije).

**Pravila:**
1. **Vlasništvo fajlova po domenu:**
   - **GUI/lokalizacija/CSS** (`src/App.tsx`, `src/styles.css`, `src/components/*`, `src/lib/realtime*.ts` stringovi) → jeftini modeli / Codex.
   - **Sigurnosni backend + Electron security** (`python_backend/app/agent/*`, `app/core/*`, `electron/core/secure*`, `securitySelfTest.cjs`, `permission_engine`, `tool_executor`, CSP, kill-switch) → **Claude**.
2. **Jedan zadatak = jedan model = commit prije predaje.** Ne ostavljati nekomitovane izmjene u fajlu koji drugi model treba dirati. Uvijek `git commit` na kraju zadatka (uz agent report).
3. **Prije editovanja fajla:** `git status` — ako fajl ima nekomitovane tuđe izmjene, STANI i prijavi korisniku umjesto da miješaš.
4. **Nakon svakog zadatka jeftinog modela → Claude verifikacija** (vidi dole) PRIJE sljedećeg zadatka.

**Hitno sad:** neko treba commitovati trenutni miks (moja S-4 dopuna + lokalizacija) da se stablo očisti. Preporuka: neka **Codex/lokalizacijski model commituje svoj lokalizacijski krug** (uključujući moju kill-switch dopunu, koja je verifikovana i radi), ili korisnik odobri da ja commitujem cijeli trenutni tree kao jedan commit. Dok se to ne razriješi, sigurnosni rad na `App.tsx` je blokiran.

---

## Šta Claude radi nakon SVAKE akcije (verifikacija)

Za svaki završen zadatak, prije "OK, dalje":
1. `git diff` — potvrditi da su dirani samo očekivani simboli/fajlovi.
2. `gitnexus_impact` na izmijenjeni simbol (ako je kod) + `gitnexus_detect_changes` (scope=staged).
3. Pokrenuti relevantne testove: `cd python_backend && python -m pytest -q` (backend) / `npm run typecheck && npm run check && npm run build` (frontend/electron) / `npm run smoke` (integracija).
4. Pregled logike izmjene naspram acceptance kriterija zadatka (ne samo "zeleno").
5. Kratak nalaz korisniku: urađeno / rizik / da li se nastavlja.

---

## Preostali zadaci (prioritet, delegabilnost, acceptance)

Oznake vlasnika: **[D]** = jeftini model može izvršiti · **[D+R]** = jeftini model izvrši, Claude obavezno review · **[C]** = Claude radi (security-critical dizajn).

### Blok A — Supply chain (S-5) 🟠
- **A1 [D]** — `package.json`: dodati `"ci": "npm ci"` i `"audit": "npm audit --omit=dev"` skripte; u `package:win`/`package:dir` promijeniti `npm run build` da mu prethodi `npm ci` u CI kontekstu (ne u lokalnom dev-u). *Acceptance:* `npm run ci` radi iz čistog stanja; lockfile committed. *Test:* `npm run typecheck`.
- **A2 [C]** — Python hash-pinning: instalirati `pip-tools`/`uv`, generisati `requirements.txt --generate-hashes` (ili `uv.lock`), i u `ricky_backend.spec`/packaging koristiti `--require-hashes`. *Zašto Claude:* dodaje tooling + mijenja build lanac, lako pokvari packaging. *Acceptance:* zaključan set sa hash-evima; `pip install --require-hashes` prolazi.

### Blok B — Tajne i podaci (S-6) 🟡
- **B1 [C]** — API ključevi u OS keyring: Electron `safeStorage` (DPAPI) umjesto `.env.local` plaintext; backend dobija ključ preko env-a pri spawn-u (isti obrazac kao `RICKY_LOCAL_TOKEN`). *Zašto Claude:* dira `electron/main.cjs` secret handling + `config.py`, security-critical. *Acceptance:* nema OPENAI/EXA ključa u plaintext fajlu na disku; app radi.
- **B2 [D+R]** — Log hygiene audit: pronaći sve `console.log`/`logger.*` koji mogu ispisati transkript/screenshot base64/email sadržaj; maskirati ili ukloniti. *Acceptance:* grep ne nalazi ispis punog transkripta/payload-a. *Test:* `npm run smoke` + `pytest -q` (bez regresije).
- **B3 [C]** — DB enkripcija (SQLCipher) ili min. file permisije `0600` na `data/ricky.sqlite`. *Acceptance:* baza nije world-readable / šifrovana.

### Blok C — Capture privatnost + TOCTOU (S-7) 🟡
- **C1 [C]** — Screenshot: slati aktivni prozor umjesto cijelog ekrana + prikaz preview-a prije slanja modelu + blacklist prozora za capture (banking/password manager). *Zašto Claude:* privacy-critical, dira `screenshot.py` + permission sloj.
- **C2 [C]** — Kad se doda prvi tool koji prima putanju → obavezno `path_sandbox.resolve_within_roots` + re-verifikacija fajla u trenutku izvršenja (TOCTOU). *Acceptance:* symlink-swap test odbijen.

### Blok D — Verifikacije postojećeg (brzo, vrijedno) 🟡
- **D1 [D+R]** — Potvrditi da glasovna "da/pokreni" NE može odobriti high-risk akciju (samo klik). Pregledati `src/lib/realtime*.ts` confirmation flow. *Acceptance:* dokumentovan nalaz + test ako treba.
- **D2 [D+R]** — Audit da svaki IPC handler u `electron/core/ipc.cjs`/`main.cjs` validira payload (ne vjeruje rendereru). *Acceptance:* lista handlera + nalaz.
- **D3 [D]** — Offline degradacija: ručni test — ugasiti net, potvrditi da diktat/lokalne akcije rade a LLM javlja nedostupnost (ne cijela app mrtva). *Acceptance:* zabilježeno ponašanje.
- **D4 [D]** — Mic indikator: potvrditi da odražava stvarno stanje mikrofona bez kašnjenja (getUserMedia track aktivan ⇔ indikator gori). *Acceptance:* zabilježeno.

### Blok E — Niži prioritet
- **E1 [C]** — Network egress allowlist na nivou aplikacije (dozvoljeni domeni: OpenAI + update server).
- **E2 [C]** — Named pipe umjesto TCP 127.0.0.1 (jače od token-only). Opciono.
- **E3 [C]** — Ako se doda auto-update: potpisivanje buildova obavezno. (Trenutno N/A.)
- **E4 [D+R]** — Proširiti red-team test set (`test_security_redteam.py`) novim injection payloadima prije uvođenja novih akcijskih alatki.

---

## Preporučeni redoslijed
1. **Razriješiti koordinaciju / commitovati trenutni miks** (blokira sve na `App.tsx`).
2. D-blok verifikacije (jeftino, brzo daje sliku) → D1, D2, D3, D4.
3. B2 (log hygiene) + A1 (npm skripte) — laki delegabilni dobici.
4. B1 (keyring) — Claude, visoka vrijednost.
5. C1 (screenshot privatnost) — Claude.
6. A2, B3, C2, E-blok — po potrebi.

## Nedelegabilno (samo Claude)
B1, B3, C1, C2, A2, E1–E3 — sve što mijenja sigurnosni sloj, secret handling, ili packaging. Jeftini modeli tu smiju samo čitati/predlagati, ne mijenjati bez Claude reviewa.
