# FAZA 17 — Deaktivacija legacy PowerShell toolova (feature flag)

## Datum

2026-07-06

## Scope

Implementirana je FAZA 17 iz `docs/MIGRATION_PLAN.md`: feature flag mehanizam `RICKY_USE_LEGACY_POWERSHELL_TOOLS` koji kontroliše pristup legacy PowerShell/JSON-db toolovima.

Nije implementirana FAZA 13/14 (computer-use Python v1/v2) — ova faza priprema infrastrukturu za njih. Legacy computer_* toolovi i dalje rade (default=1) do FAZA 13/14. Alati sa postojećim Python ekvivalentima (note_*, records_*, artifact_*, screen_snapshot, ui_inspect, web_search, image_generate) već automatski preferiraju Python kroz `PHASE11_DELEGATED_TOOLS` mehanizam (FAZA 11/16); flag kontroliše da li smiju pasti natrag na legacy kad Python faila.

## GitNexus impact

Prije izmjene pokrenut je `npx gitnexus impact` (CLI, `--repo nas_agent`):

- `handleToolsExecute` → risk **LOW**, 0 impaktovanih, 0 procesa.

Sve izmjene su aditivne (novi `legacyTools.cjs` modul + gate-ovi u postojećem handler-u). Nakon izmjene indeks je osvježen (`npx gitnexus analyze`).

## Šta je urađeno

### `electron/core/legacyTools.cjs` (novi modul)

- **Feature flag**: `RICKY_USE_LEGACY_POWERSHELL_TOOLS` env var — default `1` (enabled). Kada je `0` ili `false`, svi legacy putevi su blokirani.
- **`isLegacyEnabled()`** — čita flag jednom po sesiji.
- **`hasPythonEquivalent(name)`** — vraća `true` ako tool već ima Python zamjenu (note_*, records_*, artifact_*, screen_snapshot, ui_inspect, web_search, image_generate).
- **`hasNoPythonYet(name)`** — vraća `true` za computer_* alate bez Python zamjene (computer_open_app, computer_type_text, computer_press_key, computer_click, computer_scroll). Ovi čekaju FAZU 13/14.
- **`blockLegacyResponse(name)`** — gradi strukturiran `{ok: false, error: "...", errorCode: "LEGACY_DISABLED"}` odgovor sa uputom da korisnik uključi flag ili čeka FAZU 13/14.
- **`LEGACY_FLAG`** — izvezen string za error poruke.

### `electron/main.cjs` — `handleToolsExecute` gate-ovi

1. **PHASE11 fallback gate** — unutar `if (PHASE11_DELEGATED_TOOLS.has(name))` catch bloka: ako `isLegacyEnabled()` vrati `false`, ne pada natrag na legacy handler — vraća `{ok: false, errorCode: "PYTHON_FAILED_LEGACY_DISABLED"}`.

2. **computer_* gate** — u bloku `if (name.startsWith("computer_") || name === "screen_snapshot" || name === "ui_inspect")`: ako `isLegacyEnabled()` vrati `false` i `hasNoPythonYet(name)` vrati `true`, vraća `blockLegacyResponse(name)`. `requireComputerMode()` poziva se tek nakon ove provjere (computer_* alati bez Python ekvivalenta se blokiraju prije nego što bi ušli u computer mode logiku).

3. **Import**: `isLegacyEnabled`, `hasNoPythonYet`, `blockLegacyResponse`, `LEGACY_FLAG` importovani na vrhu fajla.

### `docs/LEGACY_TOOLS.md` (novi dokument)

- Objašnjenje zašto legacy toolovi postoje
- Feature flag dokumentacija (`RICKY_USE_LEGACY_POWERSHELL_TOOLS`, vrijednosti `0`/`1`)
- Tabela toolova sa Python ekvivalentom (koja faza, koja putanja)
- Tabela toolova bez Python ekvivalenta (koji čekaju FAZA 13/14)
- Tabela toolova isključivo u Electron-u (ne migriraju se)
- Kratka istorija faza (0-17)

### `docs/MIGRATION_PLAN.md`

- FAZA 17 red označen kao ✅ urađeno.

## Zašto je urađeno

FAZA 17 je pripremni korak za potpuno gašenje legacy PowerShell toolova. Implementacioni plan traži:

- "After Python replacements are verified, disable legacy PowerShell computer-use tools by default."
- "Keep a documented fallback flag for development only."
- "Default: Python tools. Legacy: samo ako env flag uključen."

Problem je što FAZA 13/14 (Python computer-use v1/v2) još nije implementirana — pa bi potpuno gašenje legacy-a slomilo computer use. Zato je default postavljen na `1` (enabled) sa eksplicitnim komentarom da se flip-uje na `0` nakon FAZE 13/14. Infrastruktura je tu, dokumentovana, i odmah primjenjiva — korisnik može sada postaviti `RICKY_USE_LEGACY_POWERSHELL_TOOLS=0` i vidjeti koje toolove bi izgubio (computer_*).

## Kako je urađeno

- **`legacyTools.cjs`** je izolovan modul bez import-a na `main.cjs` (bez cirkularnih zavisnosti). Flag logika je centralizovana — svaka buduća izmjena legacy ponašanja ide kroz ovaj modul.
- **Gate logika** je dodana na dvije tačke u `handleToolsExecute`: (1) PHASE11 fallback (ne dopušta pad na legacy), (2) computer_* blok (blokira alate bez Python zamjene). Sve ostale legacy putanje (note_add, records_*, artifact_*, web_search, image_generate, screen_snapshot, ui_inspect) automatski su pokrivene PHASE11 gate-om jer su u `PHASE11_DELEGATED_TOOLS`.
- **Error kodovi** su konzistentni: `LEGACY_DISABLED` (alat nema Python zamjenu) vs `PYTHON_FAILED_LEGACY_DISABLED` (Python fail-ovao, fallback blokiran). Oba uključuju naziv flag-a i uputstvo.

## Šta nije dirano

- Nije dirana Python backend logika (bez regresije — 78 testova prolazi).
- Nije diran `src/lib/realtime.ts` (audio pipeline).
- Nisu obrisani legacy fajlovi (`electron/tools_legacy/powershell/*.cjs`). Ostaju kao dev-only fallback.
- Nije implementirana FAZA 13/14 (computer-use Python v1/v2) — ovo je samo flag infrastruktura koja će se aktivirati kad te faze budu gotove.
- Nisu dirani Electron-only toolovi koji se ne migriraju (`set_mode`, `artifact_show`, `show_menu`, `mermaid_render`, `thumbnail_*`).

## Verifikacija

Pokrenuto:

```text
node smoke legacy module test (svi assertion-i)
npm run typecheck
npm run build
node --check electron/main.cjs && node --check electron/core/legacyTools.cjs
cd python_backend && python -m pytest -q
```

Rezultati:

```text
legacy module unit: 9/9 assertions passed
  - default=1: isLegacyEnabled() === true ✓
  - computer_open_app hasNoPythonYet ✓
  - screen_snapshot hasPython ✓
  - blockLegacyResponse vraca {ok:false, errorCode:LEGACY_DISABLED} ✓
  - flag=0: isLegacyEnabled() === false ✓
typecheck: prošao (tsc --noEmit bez grešaka)
build: prošao (vite/rolldown)
node --check: čist za oba .cjs fajla
pytest: 78 passed (bez regresije)
```

`pytest` warning je postojeći FastAPI/Starlette `TestClient` deprecation (nevezan za FAZU 17).

## Rizici/ograničenja

- **Default flag = 1**: dokumentovano je da se flip-uje na 0 nakon FAZE 13/14. Ako neko zaboravi, legacy computer_* alati ostaju aktivni zauvijek — rizik je mali jer su FAZA 13/14 sljedeća prirodna faza.
- **Flag je globalan**: ili su SVI legacy alati uključeni ili isključeni. Nema per-tool fine-grained kontrole. Ovo je namjerno — za dev/testing, developer može jednostavno obrisati alat iz `TOOLS_PENDING_PYTHON_EQUIVALENT` seta.
- **Flag se čita jednom pri import-u modula**: ako se proces-u promijeni env var nakon prvog poziva `isLegacyEnabled()`, vrijednost se neće osvježiti. Ovo je acceptable jer Electron main proces ne mijenja env varse runtime-u.
- **Legacy fajlovi nisu obrisani**: `electron/tools_legacy/powershell/*.cjs` i dalje postoje. Konačno čišćenje je odluka za post-1.0 (FAZA 19 packaging plan).

## Potreban follow-up

- **FAZA 13/14** (computer-use Python v1/v2) — nakon implementacije i end-to-end verifikacije:
  1. Dodati `computer_*` alate u `TOOLS_WITH_PYTHON_EQUIVALENT` (ili ukloniti iz `TOOLS_PENDING_PYTHON_EQUIVALENT`)
  2. Flip-ovati default `RICKY_USE_LEGACY_POWERSHELL_TOOLS` sa `1` na `0` u `legacyTools.cjs`
  3. Verifikovati da svi computer_* pozivi idu kroz Python backend
- **Post-1.0 cleanup**: obrisati `electron/tools_legacy/powershell/` i legacy JSON db handler-e iz `main.cjs`.
- **CI test**: dodati CI job koji pokreće `RICKY_USE_LEGACY_POWERSHELL_TOOLS=0` i verifikuje da alati bez Python zamjene ispravno vraćaju `LEGACY_DISABLED`.

## Potrebna korisnička potvrda

Prije commita treba potvrditi:

1. Da li je prihvatljivo da default ostane `1` (legacy enabled) dok FAZA 13/14 ne dodaju Python computer_* alate? Alternativa bi bila default `0`, ali bi computer use bio potpuno slomljen.
2. Da li da dodam per-tool fine-grained kontrolu (npr. `RICKY_LEGACY_ENABLE=computer_click,computer_type_text`) ili je globalni flag dovoljan za dev/production?
3. Worktree sadrži nepratene asset fajlove (slike) — ostaju van commit-a kao i ranije?
