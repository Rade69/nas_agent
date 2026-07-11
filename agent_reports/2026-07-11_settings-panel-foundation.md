# Agent report — Settings panel temelj: personalizovano ime (proširivo)

**Datum:** 2026-07-11
**Povod:** korisnik primijetio da Riki uvijek zove korisnika "Riley"
(hardkodirano u sistem promptu). Eksplicitan zahtjev: uraditi "temeljno i
sistemski, jer ćemo svakako dograđivati settings panel" — dakle prava,
proširiva infrastruktura, ne jednokratna zakrpa.

## Šta je urađeno — sloj po sloj

### Backend (Python) — nova `UserSettings` infrastruktura
- **Otkriveno:** `settings` SQLite tabela (`key`/`value_json`/`updated_at`,
  key-value dizajn) je postojala u shemi još od FAZA 7, ali nikad nije imala
  repository/servis/API — čista neiskorištena infrastruktura.
- `app/schemas/settings.py` — `UserSettings` (trenutno samo `user_name: str = "Riley"`)
  + `UserSettingsUpdateRequest`. Namjerno NE zove se `Settings` — to ime je već
  zauzeto (`app/core/config.py` `Settings` = env/config, potpuno drugi koncept).
- `app/storage/repositories/settings_repo.py` — generički KV repository
  (`get`/`get_all`/`set` na proizvoljnom stringu ključa). Nova postavka =
  novo polje u `UserSettings` sa defaultom, BEZ DB migracije.
- `app/services/settings_service.py` — mapira KV storage u tipizovani
  `UserSettings` (nepoznati ključevi u bazi se tiho ignorišu, ne pucaju).
- `app/api/settings.py` — `GET /settings`, `PATCH /settings` (partial update
  preko `exclude_unset`).
- `app/main.py` — `app.state.user_settings_service` (namjerno DRUGO ime od
  `app.state.settings`, izbjegava zabunu) + `include_router(settings_router)`.
- `tests/test_settings.py` — 4 nova testa. **Bitna napomena:** `user_name` je
  JEDINSTVENA dijeljena vrijednost u pravoj `data/ricky.sqlite` bazi (za
  razliku od confirmations/plans koje prave nove redove sa unique ID-jem) —
  projekat nema `conftest.py` test-izolaciju, pa bi test koji promijeni ime
  bez čišćenja zagadio i buduće test-runove I stvarne korisničke podatke.
  Dodat `_restore_user_name` fixture koji čuva originalnu vrijednost i vraća
  je nakon testa.

### Electron — prenosi ime u sistem prompt
- `services/pythonClient.cjs` — `getSettings()`/`updateSettings()` (isti
  obrazac kao `listPlans`/`updatePlan`).
- `ipc_handlers/settings.cjs` (novi) — `handleSettingsGet`/`handleSettingsUpdate`,
  tanka passthrough (isti obrazac kao `plans.cjs`).
- `main.cjs` — registrovan `settings:get`/`settings:update` u IPC allowlist.
- `preload.cjs` — izloženo `window.ricky.getSettings/updateSettings`.
- `ipc_handlers/realtime.cjs` — **`RICKY_INSTRUCTIONS` pretvoren iz statičnog
  const stringa u `buildRickyInstructions(userName)` funkciju** — svih 8
  pojavljivanja "Riley" zamijenjeno sa `${userName}` interpolacijom.
  `handleRealtimeCreateToken` sad povuče `user_name` iz backend-a prije
  mintovanja tokena. **Fail-open, ne fail-closed:** ako `getSettings()`
  padne (backend nedostupan i sl.), tiho se vrati na default "Riley" umjesto
  da blokira cijelu glasovnu sesiju — ovo je kozmetička preferenca, ne
  sigurnosna postavka.

### Renderer — prava Settings forma (ne placeholder)
- `vite-env.d.ts` — `UserSettings` tip + `window.ricky.getSettings/updateSettings`.
- `components/pixel/SettingsPanel.tsx` (novi) — samostalna komponenta:
  učitava postavke pri montiranju, forma sa poljem "Tvoje ime", Sačuvaj
  dugme (onemogućeno dok nema izmjene), vidljiva potvrda/greška. **Namjerno
  strukturirano u `.pixel-settings-section` blokove** — dodavanje sljedeće
  postavke (npr. cloud/lokalni STT izbor iz `RICKY_GUI_LOCALIZATION_PLAN.md`
  backlog-a) znači nova sekcija u istoj komponenti, ne restrukturiranje.
- `PixelMockupBoard.tsx` — `activeDrawer === "settings"` sad renderuje
  `<SettingsPanel />` umjesto statičnog "Postavke nisu dostupne" teksta.
- `styles/11-pixel-shell.css` — novi `.pixel-settings-*` CSS blok, reuse
  postojećeg `.pixel-primary` dugmeta (već globalno definisano, ne dictation-
  specifično) za "Sačuvaj".

## Zašto ovako (arhitektonske odluke)

1. **Key-value storage, ne kolona-po-postavci** — buduće postavke (STT
   izbor, itd.) ne traže DB migraciju, samo novo polje u `UserSettings` +
   novu sekciju u `SettingsPanel.tsx`.
2. **`UserSettings` ≠ `Settings`** — izbjegnut sudar imena sa postojećom
   config klasom; `app.state.user_settings_service` ≠ `app.state.settings`.
3. **Fail-open u promptu** — ime je kozmetika, ne smije srušiti glasovnu
   sesiju ako backend na trenutak nije dostupan.
4. **`buildRickyInstructions()` funkcija umjesto const-a** — jedini način da
   se ime ubaci bez duplirane logike; sve postojeće ponašanje (dictation
   guardrails, mode instrukcije) ostaje bajt-identično, samo je "Riley"
   postao promjenljiva.

## Verifikacija

- `cd python_backend && python -m pytest -q` — **226 passed** (222 prije +
  4 nova settings testa), uklj. finalni run nakon SVIH izmjena u `main.py`.
- `node --check` na svih 5 dirani/nova `.cjs` fajla — čisto.
- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- Runtime NIJE testiran — potreban korisnički test (novi UI ekran + stvaran
  poziv Rikiju da provjeri da li koristi novo ime).

## Šta NIJE urađeno (namjerno, sljedeći koraci kad zatreba)

- Samo JEDNO polje (`user_name`) — namjerno, dokazuje da infrastruktura
  radi prije nego se doda više polja odjednom.
- Nema validacije dužine/formata imena (prazan string pada nazad na
  "Riley" na frontend strani; backend prima bilo koji string).
- `Postavke` sidebar stavka i dalje živi kao `Drawer` overlay preko Idle
  ekrana (isti mehanizam kao Aktivnost/Planovi) — nije dobio poseban
  full-screen tretman, u skladu sa postojećim dashboard designom.

## Test za korisnika

1. Otvori Postavke (sidebar) → treba se pojaviti prava forma sa "Tvoje ime"
   poljem (trenutno "Riley").
2. Promijeni ime, klikni Sačuvaj → treba se pojaviti "Sačuvano."
3. Zatvori app, ponovo pokreni, otvori Postavke → ime treba ostati
   sačuvano (perzistentno u SQLite).
4. Uđi u glasovnu sesiju, pozovi Rikija → **treba te oslovljavati novim
   imenom**, ne "Riley".

## Potrebna korisnička potvrda

Runtime test obavezan prije commita — ovo je najveći, višeslojni fix danas
(backend + Electron + renderer), prvi put testiran u praksi tek sad.
