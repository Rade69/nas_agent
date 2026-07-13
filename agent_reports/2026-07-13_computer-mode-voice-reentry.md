# Agent report — glasovni ulazak u Computer Mode vraćen, sa S-2 escalation gate-om

**Datum:** 2026-07-13
**Scope:** `electron/core/realtimeToolSpecs.cjs`, `electron/main.cjs`,
`electron/ipc_handlers/realtime.cjs`, `electron/tools_legacy/legacyMedia.cjs`,
`python_backend/app/tools/system/mode.py` (novo),
`python_backend/app/agent/tool_catalog/phase11.py`, `src/App.tsx`, `src/vite-env.d.ts`.

**Povod:** Korisnik je prijavio da je S-01 popravka (ista sesija,
`agent_reports/2026-07-13_security-pr-a-set-mode-and-open-app.md`) potpuno
uklonila glasovni ulazak u Computer Mode — smatra to nepotrebnim trenjem kad
je pored računara i radi nešto drugo. Ponuđene su tri opcije kroz
AskUserQuestion; korisnik je izabrao **escalation-based** pristup: `set_mode`
ostaje dostupan glasom/tekstom, ALI ako je model u istoj sesiji već pročitao
eksterni sadržaj (web/ekran), ulazak u Computer Mode tada traži potvrdu.

## GitNexus impact

`detect_changes` prije commita — risk **HIGH** (dodirnut `handleToolsExecute`,
centralna dispatch funkcija za SVE alate, plus `toolSpecs` koji hrani i
OpenAI Realtime sesiju i renderer-ov `knownTool` gate). Ovo je legitiman rizik
s obzirom na sigurnosnu prirodu izmjene, ne lažna alarma — ručno provjeren
`git diff` potvrđuje da je izmjena u `main.cjs` čisto premještanje i
proširenje POSTOJEĆEG `set_mode` bloka (bio unconditional, sad gated), ništa
drugo u `handleToolsExecute`-u nije dirano. Korisnik je unaprijed odobrio
smjer (AskUserQuestion), ali ovaj risk nivo se eksplicitno prijavljuje ovdje
u skladu sa CLAUDE.md/GitNexus pravilom.

## Šta je urađeno

### Arhitektura

Prije S-01: `set_mode` je bio uklonjen iz `toolSpecs` (model ga uopšte nije
mogao vidjeti/pozvati) — jedini put je bio UI toggle (`App.tsx`'s
`switchMode()`), koji direktno poziva `handleToolsExecute` bez ikakve
provjere.

Sada: `set_mode` je vraćen u `toolSpecs` (model ga vidi i može pozvati), ali
`electron/main.cjs`'s `handleToolsExecute` sad razlikuje DVA izvora istog
tool imena preko `context.source`:

- **UI toggle** (`App.tsx`'s `switchMode()`) — označava svoj poziv sa
  `context: { source: "ui" }`. Ovo je direktan ljudski klik, jači pristanak
  od confirmation dijaloga, pa se mod mijenja ODMAH, bez ikakvog Python
  poziva — mora raditi i kad je backend ugašen.
- **Model (glas/tekst)** — `src/lib/realtime.ts`'s `executeFunctionCalls()`
  poziva `executeTool` bez `source` markera (nepromijenjeno), pa
  `handleToolsExecute` taj poziv prvo šalje Python backend-u
  (`python_backend/app/tools/system/mode.py` — čisto validacioni handler,
  BEZ efekta na prozor, jer Python ne može upravljati Electron BrowserWindow
  instancama). Python `set_mode` je registrovan (`phase11.py`) sa
  `risk="medium"`, `requires_confirmation=False` — genuine zahtjev izvršava
  se odmah. Postojeće S-2 escalation pravilo u `permission_engine.check_permission`
  (`external_content_seen and risk in medium/high/critical`) automatski
  eskalira na `CONFIRMATION_REQUIRED` AKO je model ovu sesiju već pročitao
  eksterni sadržaj — ništa novo nije dodano u `permission_engine.py`, samo
  iskorišteno postojeće pravilo registracijom `set_mode`-a kao medium-risk
  tool-a. Tek nakon što Python odobri (ili nakon odobrene potvrde), Electron
  stvarno izvršava `setWindowMode()`/`showCompanion()`/`hideCompanion()`.

Ako backend nije dostupan, model-inicirani `set_mode` **fail-closed**-uje
(isti obrazac kao `LEGACY_FAIL_CLOSED_TOOLS`) — bez backend-a nema ko
provjeriti escalation pravilo, pa je sigurnije odbiti nego tiho ponovo
otvoriti S-01 rupu. UI toggle ostaje potpuno nezavisan od backend statusa.

### Prateće izmjene teksta

- `realtime.cjs`'s system prompt: uklonjeno "you cannot turn it on... no tool
  call for it", vraćeno uputstvo da model pozove `set_mode` i da eventualni
  zahtjev za potvrdom znači da treba sačekati korisnika.
- `main.cjs`'s `requireComputerMode()` poruka: "Ask the user to enable..." →
  "Call set_mode with mode 'computer' first."
- `legacyMedia.cjs`'s `buildMenuMarkdown()` help meni: dodato da se Computer
  Mode može uključiti i glasom, plus napomena o safety-check potvrdi nakon
  čitanja eksternog sadržaja.

## Zašto ovako

- Python-only permission gating (umjesto ručne Electron-side confirmation
  verifikacije) — CLAUDE.md arhitektonsko pravilo i postojeći komentar u
  `main.cjs` ("backend's permission_engine is the ONLY place a
  confirmation_id is verified") već su uspostavili da Electron ne smije sam
  verifikovati confirmation_id-jeve. Umjesto duplirati tu logiku, `set_mode`
  je registrovan kao pravi Python tool sa trivijalnim (no-op) handler-om čija
  jedina svrha je da prođe kroz `permission_engine` — stvarni efekat
  (window switch) ostaje u Electron-u jer Python fizički ne može kontrolisati
  BrowserWindow instance.
- `context.source: "ui"` kao razlikovni signal — jedini pouzdan način da se
  razdvoje "čovjek je kliknuo" od "model je pozvao" na istom IPC kanalu,
  pošto oba dolaze iz istog renderer procesa na `tools:execute`. UI toggle je
  JEDINO mjesto u kodu koje postavlja ovaj marker (provjereno grep-om —
  `switchMode()` u `App.tsx` je jedini poziv `executeTool({name: "set_mode"})`
  van modelovog function-calling toka).
- `risk="medium"` (ne "low") za `set_mode` u Python registraciji — namjerno,
  jer to je upravo prag koji uključuje eskalaciono pravilo 1 u
  `permission_engine.py` (`risk in ("medium","high","critical")`). Nije
  korišten `outbound=True` (kao web_search/image_generate) jer set_mode ne
  šalje ništa trećoj strani — to je "acts on the system" slučaj, ne
  "outbound" slučaj; postojeće razdvajanje ta dva pravila u
  `permission_engine.py` je tačno pogodilo ovaj scenario bez izmjene.

## Šta nije dirano

- `permission_engine.py` — nula izmjena, postojeće escalation pravilo je
  ponovo iskorišteno bez modifikacije.
- `computer_click`/`computer_type_text`/ostali Phase 13/14 alati — netaknuti.
- S-02 (shell injection fix) — netaknut, odvojen nalaz iz istog audita.

## Verifikacija

- `python -m pytest -q` (cijeli `python_backend` suite) — **273 passed**
  (nema regresije; novi `set_mode` handler nema poseban test fajl — trivijalan
  no-op, pokriven implicitno kroz postojeće `test_permission_engine.py`
  escalation testove koji već testiraju generičko `risk`/`external_content_seen`
  ponašanje na proizvoljnom medium-risk tool-u).
- `npm run typecheck`, `npm run build` — čisto.
- `npm run check` (node --check na sve `.cjs`) — čisto.
- `mcp__gitnexus__detect_changes` — risk HIGH (očekivano, obrazloženo gore),
  ručno potvrđen `git diff` kao čisto premještanje/proširenje postojećeg bloka.
- Runtime NIJE testiran (agent nema Electron GUI pristup).

## Rizici/ograničenja

- **Poznat gap:** kad se escalation OKINE (rijedak slučaj — samo nakon
  čitanja eksternog sadržaja) i korisnik odobri potvrdu, retry put
  (`App.tsx`'s `handleApproveConfirmation`, generički za SVE alate) poziva
  `executeTool` direktno i ažurira `artifact` iz odgovora, ali NE poziva
  `setMode()` — React `mode` state u prozoru koji je odobrio potvrdu neće se
  kozmetički osvježiti, iako Electron stvarno izvrši window switch ispravno
  (window management je u potpunosti Electron-side, neovisan o React state-u
  u DRUGOM prozoru). Namjerno ostavljeno — popravka bi zahtijevala
  specijalizaciju generičkog retry handler-a samo za ovaj rijedak slučaj.
- Nije dodat poseban pytest za `set_mode`-ov Python handler (trivijalan) niti
  za novu escalation putanju end-to-end (zahtijeva Electron+Python integraciju,
  van dosega jediničnih testova).
- `_APP_ALIASES` (S-02, odvojen nalaz) i ostali audit nalazi ostaju netaknuti.

## Potreban follow-up

Korisnički test: (1) reći "uđi u computer mode" bez prethodnog čitanja weba —
potvrditi da se izvršava odmah bez potvrde; (2) zatražiti web_search pa odmah
zatim glasom reći "uđi u computer mode" — potvrditi da se PRVI PUT traži
potvrda (u glavnom prozoru ili mini prozoru, zavisno gdje se desi), i da
odobravanje stvarno uključi Computer Mode.

## Potrebna korisnička potvrda

Runtime test (gore) prije nego se ovo smatra potpuno zatvorenim.
