# Agent report — Security PR A: model ne može uključiti Computer Mode, uklonjen shell=True

**Datum:** 2026-07-13
**Scope:** `electron/core/realtimeToolSpecs.cjs`, `electron/main.cjs`,
`electron/ipc_handlers/realtime.cjs`, `electron/tools_legacy/legacyMedia.cjs`,
`python_backend/app/tools/system/computer.py`,
`python_backend/app/agent/tool_catalog/phase13.py`,
`python_backend/tests/test_phase13_computer_tools.py`.

**Povod:** Korisnik je zatražio čitanje `docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md`
i `agent_reports/2026-07-13_security-and-improvement-audit.md` (audit drugog agenta —
Codex, necommitovan, read-only pregled). Nezavisno sam provjerio sva tri CRITICAL/P0
nalaza direktno u kodu prije nego što sam prihvatio bilo šta; sva tri su potvrđena
tačna. Korisnik je izabrao da odmah počne Security PR A (S-01 + S-02).

## GitNexus impact

`mcp__gitnexus__impact(target: "_handle_open_app", direction: "upstream")` prije
izmjene — risk LOW, 0 direktnih pozivalaca u statičkom grafu (poziva se preko
handler dict-a u tool registry-ju, ne direktnim importom, pa GitNexus-ov
call-graph to ne hvata — očekivano za ovaj obrazac registracije). Ručno
potvrđen jedini stvarni pozivalac (`register_phase13_tools`'s handler dict).

## Šta je urađeno

### S-01 — model je mogao sam uključiti Computer Mode

- `electron/core/realtimeToolSpecs.cjs`: `set_mode` uklonjen iz `toolSpecs`
  niza koji se šalje modelu. Ovaj niz je JEDINI izvor i za OpenAI Realtime
  sesijin `tools:` parametar (`realtime.cjs:92`) i za renderer-ov
  `knownTool` gate (`src/lib/realtime.ts:309`) — uklanjanjem odavde model
  više ne može ni saznati da `set_mode` postoji, a čak i kad bi pokušao,
  renderer bi odbio poziv prije nego stigne do IPC-a.
- Provjereno (ručno, `node -e`) da `toolSpecs` više ne sadrži `set_mode`
  (22 preostala alata).
- UI toggle (`App.tsx`'s `switchMode()`) je netaknut — poziva
  `window.ricky.executeTool({name: "set_mode", ...})` DIREKTNO, što ide u
  `electron/main.cjs`'s `handleToolsExecute` (linija ~344) potpuno odvojenim
  putem od modelovog function-calling toka. `handleToolsExecute` i dalje
  prihvata `name === "set_mode"` bezuslovno — to je namjerno, jer je taj put
  sad JEDINI put kojim se `set_mode` uopšte može pozvati.
- `requireComputerMode()` poruka (`main.cjs`) promijenjena sa "Ask Ricky to
  switch to computer use mode first" (uputstvo modelu da SAM sebe uključi)
  u "Ask the user to enable Computer Mode from the app" (uputstvo modelu da
  zamoli ČOVJEKA).
- System prompt (`realtime.cjs`) ažuriran: eksplicitno kaže modelu da ne
  postoji tool poziv za Computer Mode i da mora reći korisniku da ga sam
  uključi iz aplikacije.
- Help meni (`legacyMedia.cjs`'s `buildMenuMarkdown()`) — uklonjen primjer
  glasovne komande "Switch to computer use mode." (više ne radi nakon ovog
  fix-a) i zamijenjen uputstvom da se Computer Mode uključuje iz aplikacije.

### S-02 — `computer_open_app` shell injection

- `python_backend/app/tools/system/computer.py`: novi `_APP_ALIASES: dict[str, str]`
  — fiksna mapa 9 poznatih aliasa (notepad, calc/calculator, mspaint/paint,
  wordpad, explorer, chrome, edge) na tačne, developer-kontrolisane target
  stringove. `_handle_open_app()` sad traži `app_name.lower()` u toj mapi;
  ako nije nađen, baca `ValueError` (isti error-handling put kao postojeća
  "appName is required" provjera → `INVALID_ARGUMENTS`). Ako JEST nađen,
  poziva `subprocess.Popen([target], shell=False)` — `target` je UVIJEK
  jedna od 9 fiksnih vrijednosti, nikad sirovi model-kontrolisan string.
  `os.startfile()` fallback (koji je bio "srećan put" ali je i dalje
  primao proizvoljan string prije nego padne na `shell=True`) je uklonjen
  u potpunosti — allowlist provjera se dešava PRIJE bilo kakvog pokušaja
  launch-a.
- `phase13.py`: tool opis ažuriran da odražava allowlist (bio je "must be
  in PATH or have an App Execution Alias" — implicirao da bilo šta u PATH-u
  radi, što više nije tačno).
- Testovi (`test_phase13_computer_tools.py`): dva stara testa koja su
  testirala STARO (ranjivo) ponašanje (`os.startfile`/`shell=True`)
  zamijenjena sa: `test_opens_allowlisted_app_with_popen_shell_false`,
  `test_allowlist_lookup_is_case_insensitive`, `test_unlisted_app_is_rejected`,
  i parametrizovan `test_shell_metacharacter_payloads_are_rejected` (5
  payload-a: `&`/`;`/`|`/`cmd /c`/`--` injection pokušaji) — tačno red-team
  test paket koji je audit tražio za S-02.

## Zašto ovako

- Allowlist umjesto sanitizacije/escaping-a ulaznog stringa — sanitizacija
  shell metaznakova je notorno lako pogriješiti (blacklist pristup uvijek
  kasni za novim zaobilaznim tehnikama); fiksna, mala allowlist od 9 aliasa
  eliminiše cijelu klasu problema umjesto da je pokušava filtrirati.
- `set_mode` je uklonjen iz DIJELJENOG `toolSpecs` niza umjesto da se doda
  posebna provjera "da li je ovaj poziv od modela ili od UI-ja" — Electron
  main proces strukturno ne može pouzdano razlikovati ta dva izvora na
  `tools:execute` IPC kanalu (oba dolaze iz istog renderer procesa). Jedini
  pouzdan način da se modelu oduzme mogućnost je da se `set_mode` nikad ne
  ni najavi kao dostupan alat u Realtime sesiji — OpenAI-jev Realtime API
  strukturno ne dozvoljava modelu da pozove funkciju koja nije u `tools:`
  listi sesije.

## Šta nije dirano

- S-03 (thumbnail arbitrary path → cloud), S-04 (confirmation replay), i
  preostalih 11 nalaza iz audita — van obima ovog PR-a, čekaju odvojen rad
  po prioritetnoj mapi iz audit dokumenta.
- `computer_type_text`/`computer_click`/`computer_press_key`/`computer_scroll` —
  nisu bili dio S-01/S-02 nalaza, nedirani.
- Legacy PowerShell `computer_openApp.cjs` (van Python-a) — nije provjeravan
  u ovom prolazu; ako je `RICKY_USE_LEGACY_POWERSHELL_TOOLS=1` eksplicitno
  postavljen (default je 0), taj put i dalje postoji nezavisno od ovog fix-a.
  Vrijedi zaseban nalaz/provjeru.

## Verifikacija

- `node --check` na sva 4 dotaknuta `.cjs` fajla — čisto.
- Ručna provjera (`node -e`) da `set_mode` nije u `toolSpecs` — potvrđeno,
  22 preostala alata.
- `npm run typecheck`, `npm run build` — čisto (nema TS izmjena, sanity provjera).
- `python -m pytest -q` (cijeli `python_backend` suite) — **257 passed**
  (251 prije + 6 novih iz `test_phase13_computer_tools.py`, neto nakon
  zamjene 2 stara testa sa 8 novih).

## Rizici/ograničenja

- `_APP_ALIASES` je namjerno mala i konzervativna (9 unosa) — korisnici koji
  su ranije mogli otvoriti bilo koju PATH-registrovanu app glasom sad ne
  mogu; ovo je namjerna funkcionalna regresija u zamjenu za sigurnost, ne
  previd. Proširenje liste je jednostavno (dodati red u mapu) kad se pojavi
  stvarna potreba.
- Help meni tekst (`legacyMedia.cjs`) je ažuriran, ali sistem prompt i help
  meni su dvije odvojene tekstualne površine koje se moraju ručno održavati
  usklađeno — nema jedinstvenog izvora istine za "šta model smije reći da
  može uraditi".

## Potreban follow-up

Sljedeći u redu po audit prioritetnoj mapi: Security PR B (S-03, thumbnail
file/cloud boundary) ili Security PR C (S-04, jednokratne confirmations) —
korisnik treba izabrati redoslijed. Runtime test preporučen: pokušati reći
"Ricky, switch to computer use mode" glasom i potvrditi da model odgovori da
korisnik mora sam uključiti (ne da to uradi tool pozivom).

## Potrebna korisnička potvrda

Runtime test (gore) prije nego se S-01 smatra potpuno zatvorenim — automatski
testovi pokrivaju backend logiku, ali stvaran glasovni tok (da li model
zaista poštuje novi system prompt umjesto da halucinira tool poziv) zahtijeva
live provjeru.
