# Agent Report — interface_language u Settings + STT jezički hint za Dictation Mode

**Datum:** 2026-07-11
**Agent:** pi
**Brief:** `docs/PI_TASK_INTERFACE_LANGUAGE_STT_BRIEF.md`

---

## Scope

Dodavanje `interface_language` polja u `UserSettings` (backend + frontend) i korišćenje
te vrijednosti kao STT jezičkog hint-a (`whisper-1 language` parametar) na oba mjesta
gdje se on šalje — `electron/ipc_handlers/realtime.cjs` (inicijalno kreiranje sesije)
i `src/lib/realtime.ts` (session.update pri dictation mode toggle-u).

---

## GitNexus impact

GitNexus nije dostupan za ovaj repo. Ručni blast radius naveden ispod po fajlu.

---

## Šta je urađeno

### Korak 1 — Backend (`python_backend/`)

- **`app/schemas/settings.py`** — Dodano `interface_language: str = "sr-Latn"` u `UserSettings`
  i `interface_language: str | None = None` u `UserSettingsUpdateRequest`.
  `app/services/settings_service.py` i `app/api/settings.py` nisu dirani — već su potpuno
  generički (rade preko `UserSettings.model_fields` i `model_dump(exclude_unset=True)`).

- **`tests/test_settings.py`** — Dodan `_restore_interface_language` fixture (analogan
  postojećem `_restore_user_name`) + 3 nova testa:
  - `test_get_settings_default_interface_language` — default je `"sr-Latn"`
  - `test_patch_settings_updates_interface_language` — PATCH mijenja na `"en"`
  - `test_patch_settings_with_unset_field_does_not_overwrite_language` — prazan body ne briše
  - Ažuriran `test_unknown_stored_keys_are_ignored` da očekuje oba polja

### Korak 2 — Electron + Frontend STT hint

- **`electron/ipc_handlers/realtime.cjs`**:
  - Dodana `STT_LANGUAGE_HINTS` mapa (`sr-Latn→"sr"`, `en→"en"`, `de→"de"`, `es→"es"`, `fr→"fr"`)
    i `DEFAULT_STT_LANGUAGE_HINT = "sr"`
  - U `handleRealtimeCreateToken()`: čitanje `settings.interface_language` pored postojećeg
    `user_name` čitanja, mapiranje kroz `STT_LANGUAGE_HINTS`
  - `language: "sr"` (linija ~93) zamijenjen sa `language: sttLanguageHint`
  - Return vrijednost proširena sa `sttLanguageHint`

- **`electron/preload.cjs`** — Nije mijenjan. `createRealtimeToken` samo prosljeđuje IPC
  rezultat bez filtriranja, tako da `sttLanguageHint` automatski prolazi.

- **`src/vite-env.d.ts`**:
  - `UserSettings` tip proširen sa `interface_language: string`
  - `createRealtimeToken` povratni tip proširen sa `sttLanguageHint: string`

- **`src/lib/realtime.ts`**:
  - Dodano `private sttLanguageHint = "sr"` polje klase
  - U `connect()`: `this.sttLanguageHint = token.sttLanguageHint ?? "sr"`
  - U `setDictationMode()`: `language: "sr"` → `language: this.sttLanguageHint`

### Korak 3 — UI (`src/components/pixel/SettingsPanel.tsx`)

- Nova sekcija "Jezik" sa `<select>` dropdown-om, odvojena od postojeće "Lično" sekcije.
  Svaka sekcija ima svoj state (`nameStatus` / `languageStatus`) i svoje Save dugme —
  postojeće ponašanje za ime je potpuno netaknuto.
- Opcije: Srpski (latinica), English, Deutsch, Español, Français
- Hint tekst: "Jezik za prepoznavanje govora u Diktatu. Promjena se primjenjuje pri
  sljedećem povezivanju glasa."

### Blast radius (ručni)

| Fajl | Direktni pozivaoci / zavisni moduli |
|------|--------------------------------------|
| `app/schemas/settings.py` | `app/services/settings_service.py` (generički, ne dira se), `app/api/settings.py` (generički), svi testovi |
| `tests/test_settings.py` | Samo pytest runner, nema produkcijskih zavisnosti |
| `electron/ipc_handlers/realtime.cjs` | `electron/main.cjs` (registruje IPC handler `realtime:create-token`), `electron/preload.cjs` (izlaže kroz `window.ricky.createRealtimeToken`) |
| `src/vite-env.d.ts` | Sve `.ts`/`.tsx` datoteke koje koriste `UserSettings` i `createRealtimeToken` |
| `src/lib/realtime.ts` | `src/App.tsx` (kreira `RickyRealtimeClient` instancu i poziva `connect()`/`setDictationMode()`) |
| `src/components/pixel/SettingsPanel.tsx` | `src/components/pixel/Drawer.tsx` (ili ekvivalent — drawer panel renderovanje) |

---

## Zašto je urađeno

Trenutno je STT jezik hardkodiran na `"sr"` — korisnik ne može promijeniti jezik
prepoznavanja govora za Dictation Mode. Ovo dodaje `interface_language` kao
perzistentnu korisničku postavku koja se mapira u `whisper-1` language hint.

---

## Kako je urađeno

Prateći obrazac iz prethodnih taskova (`user_name` u Settings panelu, dictation
rewrite menu), isti slojevi:
1. Novo polje u `UserSettings` → automatski podržano od strane generičkog servisa/API-ja
2. Testovi analogni postojećim `user_name` testovima
3. Mapiranje `interface_language` → STT hint na dva mjesta (inicijalna sesija + dictation toggle)
4. Propagacija kroz IPC → preload → TypeScript tipove → `RickyRealtimeClient`
5. UI dropdown sa standardnim CSS klasama

---

## Šta nije dirano

- `electron/main.cjs` — nije dodavana nova logika (samo registruje postojeći IPC handler)
- `python_backend/app/main.py` — nije dodavan novi endpoint
- `python_backend/app/core/config.py` — nije mijenjan
- `app/services/settings_service.py` i `app/api/settings.py` — nisu mijenjani (već generički)
- `src/App.tsx` — nije diran (sve izmjene su unutar `realtime.ts` i `SettingsPanel.tsx`)
- CSS (`src/styles/11-pixel-shell.css`) — nije dodavan novi CSS. `<select>` element
  **ne nasljeđuje** stilove od `.pixel-settings-field input` (border, background, padding),
  pa će vizuelno odstupati od input polja. Ovo je svjesna odluka — CSS je van liste
  dozvoljenih fajlova. Prijavljeno u rizicima ispod.
- Cloud-vs-lokalni STT izbor — **nije diran**, to je poseban backlog item
  (`docs/RICKY_GUI_LOCALIZATION_PLAN.md` sekcija o cloud-vs-lokalni STT).

---

## Verifikacija

- ✅ `cd python_backend && python -m pytest -q` → **236 passed** (233 postojeća + 3 nova)
- ✅ `npx tsc --noEmit` → čisto, nema grešaka
- ✅ `npm run build` → uspješan build
- ✅ `node --check electron/ipc_handlers/realtime.cjs electron/preload.cjs` → čisto
- ✅ Postojeće ponašanje: srpski ostaje `"sr"` (ne `"bs"`), Cyrillic→Latin transliteracija,
  dikt trigger, exit fraze — netaknuti

---

## Rizici / ograničenja

1. **`<select>` styling:** Select element ne nasljeđuje stilove od `.pixel-settings-field input`
   (border, background, padding, fokus). U tamnoj temi će izgledati sa default OS/browser
   stilom (svijetla pozadina, default border). Nije dodavan CSS jer `11-pixel-shell.css`
   nije na listi dozvoljenih fajlova. **Potreban follow-up:** dodati `.pixel-settings-field select`
   pravila u CSS (identična input pravilima).

2. **Retroaktivna primjena:** Promjena jezika u Settings-u mijenja STT hint samo za
   **sljedeću** voice sesiju (novi `connect()`). Trenutna sesija nastavlja sa starim
   hintom. Ovo je po dizajnu iz brief-a ("ne retroaktivno").

3. **Nema validacije na backendu:** `interface_language` prima bilo koji string —
   mapiranje u STT hint se dešava na Electron strani sa fallback-om na `"sr"`.
   Ako korisnik pošalje nepodržani jezik (npr. `"zh"`), STT hint će biti `"sr"`,
   što je siguran default ali nije očigledno korisniku.

---

## Potreban follow-up

1. **Dodati CSS za `<select>` u `11-pixel-shell.css`** — `.pixel-settings-field select`
   sa istim border/background/padding/fokus stilovima kao `.pixel-settings-field input`.

2. **Cloud-vs-lokalni STT izbor** — poseban backlog item, nije dio ovog taska.

---

## Potrebna korisnička potvrda

Nije potrebna — mehanički zadatak po postojećem obrascu, sve verifikacije prolaze.