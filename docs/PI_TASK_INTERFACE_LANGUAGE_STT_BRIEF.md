# Brief za pi — interface_language u Settings + STT jezički hint za Dictation Mode

**Za:** pi · **Od:** Claude
**Jedan zadatak, mehanički rad po već postojećem obrascu** — `user_name` polje u
Settings-u (agent_reports/2026-07-11_settings-panel-foundation.md) i "Doradi"
meni (agent_reports/2026-07-11_dictation-rewrite-menu.md) su upravo završeni
istim putem: novo polje u `UserSettings`, novi propovi kroz iste slojeve.
Ovaj zadatak ponavlja taj obrazac za jedno novo polje: `interface_language`.

Pozadina/odluka je već donesena u `docs/RICKY_GUI_LOCALIZATION_PLAN.md` sekciji
"`interface_language` kao STT jezički hint (Dictation Mode)" (linije ~161–224) —
ne treba ponovo odlučivati ŠTA raditi, samo implementirati. **Ovaj zadatak NE
uključuje cloud-vs-lokalni STT izbor** (poseban, veći, još neodlučen backlog
item — vidi istu sekciju, ne diraj tu temu).

---

## Pravila (obavezno)

- **Dozvoljeni fajlovi za izmjenu** (tačna lista, ništa van nje):
  - `python_backend/app/schemas/settings.py`
  - `python_backend/tests/test_settings.py`
  - `electron/ipc_handlers/realtime.cjs`
  - `electron/preload.cjs`
  - `src/vite-env.d.ts`
  - `src/lib/realtime.ts`
  - `src/App.tsx` (SAMO dio gdje se poziva `clientRef.current?.connect()` — ne
    diraj dictation rewrite handlere dodane ranije danas, oko linija 375-460)
  - `src/components/pixel/SettingsPanel.tsx`
- **NE diraj:** `electron/main.cjs`, `python_backend/app/main.py`,
  `python_backend/app/core/config.py` (recurring collision fajlovi — ako ti
  zatreba nešto iz njih, javi umjesto da diraš), `app/api/settings.py`,
  `app/services/settings_service.py` (već su generički, provjereno da im NE
  treba izmjena za novo polje — vidi Korak 1 ispod).
- Prije bilo koje izmjene u fajlovima koje dijeliš sa drugim agentima, svježe
  ih pročitaj (`cat`, ne keširani prikaz) — vidi CLAUDE.md "Multi-agent
  higijena".
- Srpski/bosanski, latinica u komentarima/porukama. Reference `fajl:linija`.
  Ne pretpostavljaj — nejasno → "otvoreno pitanje" u izvještaju.
- **Ne mijenjaj postojeće ponašanje** — trenutni hardkodirani hint je
  `language: "sr"` (ne `"bs"`, iako plan to spominje kao opciju). Zadrži
  `"sr"` kao mapping za `sr-Latn` i default. Promjena na `"bs"` bila bi
  netestirana izmjena ponašanja izvan opsega ovog zadatka.

---

## Korak 1 — Backend: novo polje u `UserSettings`

`python_backend/app/schemas/settings.py`:
```python
class UserSettings(BaseModel):
    user_name: str = "Riley"
    interface_language: str = "sr-Latn"


class UserSettingsUpdateRequest(BaseModel):
    user_name: str | None = None
    interface_language: str | None = None
```
`app/services/settings_service.py` i `app/api/settings.py` su već potpuno
generički (rade preko `UserSettings.model_fields`) — **ne treba im nikakva
izmjena**, provjereno prije pisanja ovog brief-a. Ako primijetiš da ipak
treba nešto dirati tamo, STANI i javi umjesto da mijenjaš fajlove van liste.

`python_backend/tests/test_settings.py` — postojeći `_restore_user_name`
fixture čuva/vraća samo `user_name`. Dodaj analogan fixture (ili proširi
postojeći) da čuva/vraća i `interface_language`, isti razlog kao u komentaru
uz postojeći fixture (dijeljena prava SQLite baza, nema test-izolacije za
ovaj endpoint). Dodaj testove analogne postojećim `user_name` testovima:
default vrijednost `"sr-Latn"`, PATCH je mijenja, PATCH sa praznim body-jem
je ne dira.

**Provjeri:** `cd python_backend && python -m pytest -q` — svi testovi i
dalje prolaze (233 prije ovog zadatka + novi).

---

## Korak 2 — Electron: mapiranje jezika → STT hint, korišćeno na dva mjesta

`electron/ipc_handlers/realtime.cjs` trenutno ima hardkodiran
`language: "sr"` na **liniji ~93** (unutar `handleRealtimeCreateToken`,
`audio.input.transcription`). `src/lib/realtime.ts` ima **isti hardkod na
liniji ~215** (unutar `setDictationMode()`, drugi `session.update` poziv kad
se diktiranje uključi/isključi/ponovo poveže). Oba mjesta postoje namjerno,
odvojeno — vidi komentar iznad linije 93 u realtime.cjs zašto (partial
`session.update` možda ne radi deep-merge, pa je jezik ranije eksplicitno
dupliran na oba mjesta). I dalje treba postojati na oba mjesta — samo umjesto
literala treba doći iz `interface_language` postavke.

### 2a — `electron/ipc_handlers/realtime.cjs`

Dodaj na vrh fajla (ispod postojećih `require`-ova i `DEFAULT_USER_NAME`):
```js
// STT jezički hint za Dictation Mode (OpenAI Realtime whisper-1 language
// param). Mapiranje po docs/RICKY_GUI_LOCALIZATION_PLAN.md — sr-Latn ostaje
// "sr" (NE "bs"), zadržava postojeće, već testirano ponašanje.
const STT_LANGUAGE_HINTS = { "sr-Latn": "sr", en: "en", de: "de", es: "es", fr: "fr" };
const DEFAULT_STT_LANGUAGE_HINT = "sr";
```

U `handleRealtimeCreateToken()`, u istom `try` bloku gdje se već čita
`settings.user_name` (oko linije 52-61), dodaj čitanje
`settings.interface_language` i izračunaj hint:
```js
let sttLanguageHint = DEFAULT_STT_LANGUAGE_HINT;
// ... unutar postojećeg try bloka, pored user_name čitanja:
if (settings && typeof settings.interface_language === "string") {
  sttLanguageHint = STT_LANGUAGE_HINTS[settings.interface_language] ?? DEFAULT_STT_LANGUAGE_HINT;
}
```
Zamijeni literal `language: "sr"` na liniji ~93 sa `language: sttLanguageHint`.

Na kraju funkcije (linija ~110-111), proširi povratnu vrijednost:
```js
return { value, expiresAt: expiresAt ?? null, sttLanguageHint };
```

### 2b — `electron/preload.cjs` i `src/vite-env.d.ts`

`preload.cjs` samo prosljeđuje IPC rezultat — provjeri da
`createRealtimeToken` handler ne skraćuje/filtrira povratni objekat (ako
skraćuje, dodaj `sttLanguageHint` u ono što se vraća). `vite-env.d.ts` linija
139:
```ts
createRealtimeToken: () => Promise<{ value: string; expiresAt: number | null; sttLanguageHint: string }>;
```

### 2c — `src/lib/realtime.ts`

U `connect()` (linija ~84-86), destrukturiraj i sačuvaj hint kao instance
polje klase (npr. `this.sttLanguageHint`), default `"sr"` ako ga token ne
vrati iz nekog razloga:
```ts
const [toolSpecs, token, micStream] = await Promise.all([...]);
this.sttLanguageHint = token.sttLanguageHint ?? "sr";
```
(Dodaj `private sttLanguageHint = "sr";` kao polje klase pored ostalih
postojećih privatnih polja.)

U `setDictationMode()` (linija ~215), zamijeni `language: "sr"` sa
`language: this.sttLanguageHint`.

**Provjeri:** `npm run typecheck` i `npm run build` — čisto.

---

## Korak 3 — UI: dropdown u Settings panelu

`src/components/pixel/SettingsPanel.tsx` trenutno ima jednu sekciju "Lično"
sa poljem za ime (linije 56-77). Dodaj **novu sekciju** "Jezik" istim
obrascem (isti `nameInput`/`dirty`/`handleSave` princip, ali za
`interface_language` — može biti ista `handleSave` funkcija proširena da
šalje oba polja, ili zaseban state + save dugme po analognom principu, tvoja
procjena koja je manja izmjena uz zadržavanje postojećeg ponašanja za ime).

Opcije u dropdown-u (`<select>`), vrijednost = ključ iz `STT_LANGUAGE_HINTS`
mape iznad:
- `sr-Latn` → "Srpski (latinica)"
- `en` → "English"
- `de` → "Deutsch"
- `es` → "Español"
- `fr` → "Français"

Koristi postojeći `.pixel-settings-section`/`.pixel-settings-field` CSS
(već postoji u `src/styles/11-pixel-shell.css`, ne treba nova CSS pravila za
select element — provjeri da li `<select>` naslijedi razumne stilove iz
postojećeg `.pixel-settings-field` konteksta; ako izgleda potpuno razbijeno,
javi u izvještaju umjesto da dodaješ novi CSS blok van liste dozvoljenih
fajlova).

**Provjeri:** `npm run dev`, otvori Postavke, promijeni jezik, Sačuvaj,
zatvori/otvori app, provjeri da je perzistentno (isto kao test za ime u
agent_reports/2026-07-11_settings-panel-foundation.md).

---

## Acceptance criteria

- `cd python_backend && python -m pytest -q` — prolazi, uklj. nove testove.
- `npm run typecheck` i `npm run build` — čisto.
- `node --check electron/ipc_handlers/realtime.cjs electron/preload.cjs` — čisto.
- Runtime: promjena jezika u Settings-u mijenja STT hint za SLJEDEĆU
  dictation sesiju (ne retroaktivno), srpski ostaje `"sr"` (ne `"bs"`),
  postojeće ponašanje (Cyrillic→Latin transliteracija, dikt trigger, exit
  fraze) i dalje radi nepromijenjeno za `sr-Latn`.
- Agent report: `agent_reports/2026-07-11_interface-language-stt-hint.md` po
  standardnom obrascu iz CLAUDE.md (Datum, Scope, Šta/Zašto/Kako, Šta nije
  dirano, Verifikacija, Rizici, Potreban follow-up).

Kad završiš, javi — Claude verifikuje (build/test/GitNexus impact) prije
commita, isti obrazac kao dosad.
