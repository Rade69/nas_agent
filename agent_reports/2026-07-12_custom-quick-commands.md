# Agent report — Brze komande su sad editabilne iz Postavki

**Datum:** 2026-07-12
**Scope:** `python_backend/app/schemas/settings.py`, `python_backend/tests/test_settings.py`,
`src/vite-env.d.ts`, `src/components/pixel/{IdleScreen,PixelMockupBoard,SettingsPanel}.tsx`,
`src/App.tsx`, `src/i18n/locales/*.json` (5 fajlova), `src/styles/11-pixel-shell.css`.

**Povod:** FABLE-5 GUI pregled (2026-07-12), tačka #2 — "hardkodovane brze
komande, korisnik ih ne može mijenjati". Potvrđeno u kodu: `IdleScreen.tsx`
je prije izmjene uvijek renderovao 4 fiksna dugmeta (`idle.cmdEmail`,
`idle.cmdScreenshot`, `idle.cmdNotepad`, `idle.cmdMeeting`), bez ikakve veze
sa postavkama korisnika.

## GitNexus impact

`mcp__gitnexus__detect_changes(repo: "nas_agent", scope: "all")` prije
commita — risk level "medium", ali svi promijenjeni simboli tačno
odgovaraju očekivanom obimu izmjene (`UserSettingsUpdateRequest` polja,
`App`/`IdleScreen`/`PixelMockupBoard`/`SettingsPanel` komponente, njihovi
testovi) — nema neočekivanih pogođenih simbola. "Medium" dolazi od širine
grafa oko `App`/`PixelMockupBoard` kao centralnih komponenti (poznat
artefakt iz ranijih izmjena ove sesije), ne od stvarnog rizika.

## Šta je urađeno

- Backend: `UserSettings.quick_commands: list[str] = []` i
  `UserSettingsUpdateRequest.quick_commands: list[str] | None = None`.
  `SettingsRepository` već generički serijalizuje/deserijalizuje JSON
  (`json.dumps`/`json.loads`) po key-u — nula izmjena u repo/service sloju
  je bilo potrebno.
- `IdleScreen.tsx`: novi `quickCommands: string[]` prop. Prazna lista →
  isti 4 podrazumijevana i18n dugmeta kao prije (bez regresije za postojeće
  korisnike). Neprazna lista → renderuje tačno te komande, tekst dugmeta je
  istovremeno i komanda poslata agentu (isti princip kao postojeći default
  case).
- `SettingsPanel.tsx`: nova sekcija "Brze komande" — lista input polja sa
  dugmetom za uklanjanje po redu, "+ Dodaj komandu", Save sa standardnim
  saving/saved/error feedbackom (isti obrazac kao Lično/Jezik sekcije).
  Prazni stringovi se tiho izbacuju pri snimanju (ne blokiraju save).
- `App.tsx`/`PixelMockupBoard.tsx`: `quickCommands` state učitan pri mount-u
  (proširen postojeći settings-fetch effect), proslijeđen do `IdleScreen`,
  i `onQuickCommandsChange` callback od `SettingsPanel` do `App.tsx` state-a
  — promjena se primjenjuje odmah, bez restarta (isti princip kao
  `interface_language`).
- Novi i18n key-evi (`settings.quickCommandsSection/Hint`,
  `addQuickCommand`, `removeQuickCommand`, `quickCommandPlaceholder`) u svih
  5 locale fajlova.
- Backend testovi: `test_get_settings_default_quick_commands_is_empty`,
  `test_patch_settings_updates_quick_commands`,
  `test_patch_settings_can_clear_quick_commands_back_to_empty` (eksplicitno
  provjerava da prazna lista `[]` stvarno očisti vrijednost, razlikuje
  "unset" `None` od "eksplicitno prazno" `[]`).

## Zašto ovako

- Prazna lista kao "koristi default" umjesto npr. `null` — jednostavnije za
  frontend (jedan tip, jedna provjera `.length > 0`), a i dalje razlikuje
  "korisnik nije ništa podesio" od "korisnik je namjerno obrisao sve" jer
  oba slučaja treba da vrate iste defaultne komande u UI-ju.
- Dva odvojena testa za "update" i "clear back to empty" — bez drugog testa
  bi promjena koja slučajno tretira `[]` kao "ignoriši" (umjesto "postavi na
  prazno") prošla neopaženo.

## Šta nije dirano

- `SettingsRepository`/`SettingsService` — generički JSON storage sloj već
  radi za proizvoljne tipove, nije trebalo mijenjati.
- Ikone dugmadi (Email/Screenshot/Notepad/Calendar) — custom komande koriste
  generičku `IconChevronRight`, nema mapiranja teksta na ikonu (namjerno,
  van obima ovog nalaza).

## Verifikacija

- `npm run typecheck` — čisto.
- `npm run build` — čisto.
- `python -m pytest -q` (cijeli `python_backend` suite) — 245 passed.
- Runtime NIJE testiran — Electron desktop app, nema browser-automation
  alata u ovom okruženju. Potreban korisnički test: otvoriti Postavke →
  Brze komande, dodati/ukloniti/snimiti, provjeriti da se lista odmah
  promijeni u Idle ekranu i da klik na custom komandu šalje tačno taj tekst
  agentu.

## Rizici/ograničenja

- Nema validacije dužine/broja komandi (korisnik teoretski može dodati
  proizvoljno dugu listu) — nisko-rizično za single-user desktop app, ali
  vrijedi napomenuti.

## Potreban follow-up

Runtime test korisnika (gore). Ovim je zatvoren cijeli FABLE-5 GUI punch
list iz 2026-07-12 pregleda (#1 hero tekst, #2 brze komande, #3 screenshot
privacy, #6 dead mic button već ranije završeni istog dana; #4 kontrast
matematički opovrgnut, #5 potvrđivanje kroz tabove već riješeno
arhitekturom).

## Potrebna korisnička potvrda

Runtime test prije nego se smatra potpuno gotovim.
