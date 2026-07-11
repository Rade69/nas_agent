# Agent Report — Dictation language cascade: trigger/exit po jeziku + agent jezik odgovora

**Datum:** 2026-07-11
**Agent:** pi
**Brief:** `docs/PI_TASK_DICTATION_LANGUAGE_CASCADE_BRIEF.md`

---

## Scope

Dva "cascade" zadatka koja nastavljaju `interface_language` rad (`1b3740e`):
- **Deo A:** Okidači za ulazak u Dictation Mode i exit fraze sada zavise od `interface_language`,
  umjesto da su hardkodirani na srpski.
- **Deo B:** System prompt (Ricky instrukcije) sada eksplicitno traži od modela da odgovara
  na jeziku koji odgovara `interface_language` postavci.

---

## GitNexus impact

GitNexus nije dostupan za ovaj repo. Ručni blast radius ispod.

---

## Šta je urađeno

### Deo A — `src/App.tsx`

**1. Zamjena pljosnatih konstanti mapama po jeziku:**

- `DICTATION_EXIT_PHRASES`: iz pljosnatog `string[]` u `Record<string, string[]>`
  sa frazama za svih 5 jezika (`sr-Latn`, `en`, `de`, `es`, `fr`).
  Dodan `DEFAULT_DICTATION_EXIT_PHRASES` fallback na srpski.
  - en: "go back to normal", "exit dictation", "stop dictating", "end dictation"
  - de: "zurück zum normalen modus", "diktat beenden", "diktat verlassen"
  - es: "volver al modo normal", "salir del dictado", "terminar el dictado"
  - fr: "retour au mode normal", "quitter la dictée", "arrêter la dictée"

- `DICTATION_TRIGGER_WORDS`: nova mapa `Record<string, string>` sa substring
  okidačima za svaki jezik. Dodan `DEFAULT_DICTATION_TRIGGER_WORD = "dikt"`.
  - en: "dictat" (hvata "dictate"/"dictation")
  - de: "diktier" (hvata "diktieren"/"Diktat")
  - es: "dict" (hvata "dictar"/"dictado")
  - fr: "dict" (hvata "dicter"/"dictée")

**⚠️ BEST-EFFORT UPOZORENJE:** Sve en/de/es/fr fraze i trigger riječi su najbolji
pokušaj — **NISU potvrđene od izvornog govornika.** Korisnik treba da ih
verifikuje prije stvarnog korišćenja na tim jezicima.

**2. State + ref za `interfaceLanguage`:**

- Dodan `const [interfaceLanguage, setInterfaceLanguage] = useState("sr-Latn")` i
  `const interfaceLanguageRef = useRef(interfaceLanguage)` sa mirroring `useEffect`-om —
  isti obrazac kao postojeći `screenRef` (zbog stale closure-a u mount-only `useEffect`-u
  koji sadrži `onTranscript` callback sa `[]` deps nizom).
- Dodan fetch `useEffect` pri mount-u: `window.ricky.getSettings().then(...)` sa
  `.catch(() => {})` — fail-open, isto kao `user_name` u `realtime.cjs`.

**3. Tri mjesta upotrebe ažurirana:**

| Lokacija | Prije | Poslije |
|----------|-------|---------|
| `onTranscript` — voice entry (linija ~311) | `text.toLowerCase().includes("dikt")` | `text.toLowerCase().includes(DICTATION_TRIGGER_WORDS[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_TRIGGER_WORD)` |
| `onTranscript` — voice exit (linija ~323) | `DICTATION_EXIT_PHRASES.some(...)` | `(DICTATION_EXIT_PHRASES[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_EXIT_PHRASES).some(...)` |
| `onQuickCommand` — text entry (linija ~688) | `text.toLowerCase().includes("dikt")` | `text.toLowerCase().includes(DICTATION_TRIGGER_WORDS[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_TRIGGER_WORD)` |

Sva tri mjesta koriste `interfaceLanguageRef.current` (ref, ne state) —
sigurnije za sve slučajeve, uključujući `onQuickCommand` koji je van
mount-only efekta ali može biti pozvan u bilo kom render ciklusu.

### Deo B — `electron/ipc_handlers/realtime.cjs`

**1. Nova mapa `LANGUAGE_NAMES`:**

```js
const LANGUAGE_NAMES = {
  "sr-Latn": "Serbian (Latin script)",
  en: "English",
  de: "German",
  es: "Spanish",
  fr: "French",
};
const DEFAULT_LANGUAGE_NAME = "Serbian (Latin script)";
```

**2. `buildRickyInstructions` proširen:**

- Drugi parametar: `languageName`
- Jedna nova rečenica u sekciji "Personality and Tone":
  ```
  Prefer replying in ${languageName} unless ${userName} clearly speaks
  a different language during the conversation.
  ```
- **Ništa drugo u promptu nije mijenjano** — samo dodata ta jedna linija.

**3. `handleRealtimeCreateToken` ažuriran:**

- Deklaracija: `let languageName = DEFAULT_LANGUAGE_NAME;`
- Čitanje iz settings: `languageName = LANGUAGE_NAMES[settings.interface_language] ?? DEFAULT_LANGUAGE_NAME;`
- Poziv: `buildRickyInstructions(userName, languageName)`

### Blast radius (ručni)

| Fajl | Direktni pozivaoci |
|------|-------------------|
| `src/App.tsx` | Samostalna komponenta — `DICTATION_EXIT_PHRASES` i `DICTATION_TRIGGER_WORDS` su modul-level konstante, koriste se samo unutar `App` komponente. `interfaceLanguage` state se koristi samo interno. |
| `electron/ipc_handlers/realtime.cjs` | `electron/main.cjs` (IPC handler `realtime:create-token`), `electron/preload.cjs` (izlaže kroz `window.ricky.createRealtimeToken`). Prompt utiče na ponašanje modela u voice sesijama. |

---

## Zašto je urađeno

Kad korisnik promijeni `interface_language` (npr. na `en`), očekuje se da:
1. Može **glasom** ući i izaći iz Dictation Mode-a na tom jeziku (ne samo na srpskom)
2. Ricky **odgovara** na tom jeziku (ne samo na osnovu korisnikovog govora, već
   eksplicitno po postavci)

Bez ovih izmjena, promjena jezika u Settings-u mijenja samo STT hint, ali ne i
dictation interakciju niti agentovo ponašanje.

---

## Kako je urađeno

Prateći obrazac iz prethodnog `interface_language` taska:
1. Konstante pretvorene iz pljosnatih nizova u mape po jeziku sa fallbackom na srpski
2. `interfaceLanguage` state + ref pattern (identičan `screenRef`-u) za stale-closure problem
3. Fetch `getSettings()` pri mount-u, fail-open
4. `languageName` proslijeđen u prompt na isti način kao `userName`

---

## Šta nije dirano

- `cyrillicToLatin.ts` — transliteracija ostaje ista, bezopasno za ne-ćirilične jezike
- `electron/main.cjs`, `python_backend/app/main.py`, `python_backend/app/core/config.py`
- Bilo koji drugi fajl osim `src/App.tsx` i `electron/ipc_handlers/realtime.cjs`

---

## Verifikacija

- ✅ `npx tsc --noEmit` — čisto
- ✅ `npm run build` — uspješan
- ✅ `node --check electron/ipc_handlers/realtime.cjs` — čisto
- ✅ Srpski put (default `"sr-Latn"`) je ponašajno identičan — iste fraze, isti
  trigger substring `"dikt"`, ista prompt linija ("Prefer replying in Serbian
  (Latin script)...")

---

## Rizici / ograničenja

1. **en/de/es/fr fraze su best-effort, NISU native-speaker potvrđene.**
   - Exit fraze mogu biti neprirodne ili imati lažne okidače na običan diktirani sadržaj
   - Trigger riječi mogu promašiti uobičajene kolokvijalne izraze za "dictation" na tim jezicima
   - **Potrebna provjera izvornog govornika prije produkcijske upotrebe ne-srpskih jezika**

2. **Prompt linija je minimalna.** Ne specificira nijanse (npr. da li da odgovara
   na srpskom ako korisnik priča mješovito). Model može interpretirati "prefer"
   slobodno. Za sada dovoljno — može se iterirati kasnije.

3. **Nema runtime testa za ne-srpske jezike** — nije moguće bez stvarnog govora
   na tim jezicima. Dovoljno je da srpski default put ostane identičan.

---

## Potreban follow-up

1. **Native-speaker review:** Sve en/de/es/fr fraze i trigger riječi treba da
   pregleda izvorni govornik prije nego korisnik aktivno koristi te jezike.
2. **Iteracija prompt-a:** Ako model ne poštuje dovoljno "prefer replying in X",
   pojačati formulaciju (npr. "Always reply in X").

---

## Potrebna korisnička potvrda

Nije potrebna za srpski default put (ponašajno identičan). Korisnik treba biti
svjestan da su en/de/es/fr fraze best-effort i da ih treba provjeriti prije
upotrebe.