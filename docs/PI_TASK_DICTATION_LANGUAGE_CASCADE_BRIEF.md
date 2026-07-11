# Brief za pi — dictation okidači/exit fraze po jeziku + agent jezik odgovora

**Za:** pi · **Od:** Claude
**Dva mala, mehanička zadatka koja nastavljaju `interface_language` rad koji si
upravo završio** (`docs/PI_TASK_INTERFACE_LANGUAGE_STT_BRIEF.md`, komitovano u
`1b3740e`). Ovo su "cascade" stavke iz `docs/LOCALIZATION_AND_STT_ENGINE_PLAN.md`
sekcije "Šta SVE treba da se promijeni kad korisnik promijeni jezik", stavke
3 i 5 — trenutno hardkodirano na srpski, van dosega prethodnog zadatka.

**Deo A i Deo B su nezavisni, mogu se raditi bilo kojim redom.**

---

## Pravila (obavezno)

- **Dozvoljeni fajlovi:** `src/App.tsx` (Deo A), `electron/ipc_handlers/realtime.cjs` (Deo B).
  Ništa drugo.
- **NE diraj:** `electron/main.cjs`, `python_backend/app/main.py`,
  `python_backend/app/core/config.py` (recurring collision fajlovi).
- Svježe pročitaj (`cat`) `src/App.tsx` i `realtime.cjs` prije izmjene — oba
  su mijenjana u zadnjih par sati.
- **Fraze za en/de/es/fr koje pišeš niže su MOJ najbolji pokušaj, NE
  potvrđene od izvornog govornika.** Označi ih u svom izvještaju kao
  "best-effort, treba provjeru izvornog govornika prije nego korisnik stvarno
  koristi taj jezik" — ne predstavljaj ih kao gotove/tačne. Ako primijetiš
  očigledan problem (npr. fraza koja je apsurdno bukvalan prevod), ispravi
  je i to zabilježi.
- Srpski/bosanski, latinica u komentarima/porukama. Reference `fajl:linija`.

---

## Deo A — `src/App.tsx`: dictation okidač i exit fraze po `interface_language`

### Trenutno stanje

- `DICTATION_EXIT_PHRASES` (linija 64-72) je pljosnat niz srpskih fraza,
  provjeren na liniji ~268 (`DICTATION_EXIT_PHRASES.some(phrase => lowerText.includes(phrase))`).
- Supstring `"dikt"` je hardkodiran okidač za ulazak u Dictation Mode, provjeren
  na **DVA mjesta**: linija ~256 (`onTranscript`, glasovni ulaz) i linija ~633
  (`onQuickCommand`, tekstualni brzi unos).
- `App.tsx` trenutno **uopšte ne poziva** `window.ricky.getSettings()` — nema
  pristupa `interface_language` vrijednosti nigdje u ovom fajlu.

### Šta uraditi

1. **Dodaj state + ref za trenutni jezik**, isti obrazac kao postojeći
   `screenRef` (linija ~109, mirroring pattern zbog stale closure-a u
   mount-only `useEffect`-u koji sadrži `onTranscript`, taj efekat ima prazan
   `[]` deps niz na liniji ~292):
   ```ts
   const [interfaceLanguage, setInterfaceLanguage] = useState("sr-Latn");
   const interfaceLanguageRef = useRef(interfaceLanguage);
   useEffect(() => {
     interfaceLanguageRef.current = interfaceLanguage;
   }, [interfaceLanguage]);
   ```
   Fetch jednom pri mount-u (novi mali `useEffect`, ili dodaj u postojeći
   koji već nešto fetch-uje pri mount-u ako nađeš zgodan — tvoja procjena):
   ```ts
   useEffect(() => {
     window.ricky.getSettings().then((s) => setInterfaceLanguage(s.interface_language)).catch(() => {});
   }, []);
   ```
   Namjerno fail-open (`.catch(() => {})`) — ako fetch ne uspije, ostaje
   default `"sr-Latn"`, ne blokira ništa (isti princip kao `user_name`
   fail-open u `realtime.cjs`).

2. **Zamijeni `DICTATION_EXIT_PHRASES` pljosnat niz mapom po jeziku**, isti
   nivo pouzdanosti/opreza kao postojeći srpski niz (višerječne, distinktivne
   fraze, izbjegavaj jednu uobičajenu riječ koja bi lažno okinula na obično
   diktirano sadržaj):
   ```ts
   const DICTATION_EXIT_PHRASES: Record<string, string[]> = {
     "sr-Latn": [
       "vrati se u normalan",
       "vrati u normalan",
       "izađi iz diktat",
       "izadji iz diktat",
       "prekini diktat",
       "završi diktiranje",
       "zavrsi diktiranje",
     ],
     en: [
       "go back to normal",
       "exit dictation",
       "stop dictating",
       "end dictation",
     ],
     de: [
       "zurück zum normalen modus",
       "diktat beenden",
       "diktat verlassen",
     ],
     es: [
       "volver al modo normal",
       "salir del dictado",
       "terminar el dictado",
     ],
     fr: [
       "retour au mode normal",
       "quitter la dictée",
       "arrêter la dictée",
     ],
   };
   const DEFAULT_DICTATION_EXIT_PHRASES = DICTATION_EXIT_PHRASES["sr-Latn"];
   ```
   Na liniji ~268, zamijeni `DICTATION_EXIT_PHRASES.some(...)` sa
   `(DICTATION_EXIT_PHRASES[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_EXIT_PHRASES).some(...)`.

3. **Zamijeni hardkodirani `"dikt"` okidač mapom po jeziku**:
   ```ts
   const DICTATION_TRIGGER_WORDS: Record<string, string> = {
     "sr-Latn": "dikt",
     en: "dictat", // hvata "dictate"/"dictation"
     de: "diktier", // hvata "diktieren"/"Diktat" (case-insensitive provjera)
     es: "dict", // hvata "dictar"/"dictado"
     fr: "dict", // hvata "dicter"/"dictée"
   };
   const DEFAULT_DICTATION_TRIGGER_WORD = "dikt";
   ```
   Na OBA mjesta (linija ~256 i ~633), zamijeni
   `text.toLowerCase().includes("dikt")` sa
   `text.toLowerCase().includes(DICTATION_TRIGGER_WORDS[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_TRIGGER_WORD)`.
   **Pažnja:** linija ~633 (`onQuickCommand`) je van `onTranscript` mount-only
   efekta — provjeri da li tamo treba `interfaceLanguageRef.current` ili je
   dovoljan direktan `interfaceLanguage` (state) jer taj handler možda nije
   zahvaćen istim stale-closure problemom. Ako nisi siguran, koristi ref
   svuda — sigurnije, nikad pogrešno.

4. **Ne diraj** `cyrillicToLatin.ts` poziv niti transliteraciju — ta logika
   ostaje ista za sve jezike (samo neće imati šta da transliteriše za
   ne-ćirilične jezike, bezopasno).

**Provjeri:** `npm run typecheck` i `npm run build` čisto. Runtime test nije
moguć bez stvarnog govora na drugom jeziku — dovoljno je da srpski put
(default `"sr-Latn"`) ostane bajt-identičan ponašanju prije ove izmjene.

---

## Deo B — `electron/ipc_handlers/realtime.cjs`: agent jezik odgovora

### Trenutno stanje

`handleRealtimeCreateToken()` (linija ~52-61) već čita `settings.interface_language`
za STT hint (tvoj prethodni rad). `buildRickyInstructions(userName)` (linija
~15-47) je engleski-pisan prompt — model svejedno odgovara multilingualno
prema jeziku korisnikovog govora, ali se ne oslanja eksplicitno na
`interface_language` postavku.

### Šta uraditi

1. Dodaj mapu jezičkog imena (za umetanje u engleski prompt):
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
2. U `handleRealtimeCreateToken()`, pored postojećeg čitanja
   `settings.interface_language` za `sttLanguageHint`, izračunaj i
   `languageName = LANGUAGE_NAMES[settings.interface_language] ?? DEFAULT_LANGUAGE_NAME`.
3. Proslijedi `languageName` u `buildRickyInstructions(userName, languageName)`
   (dodaj drugi parametar funkciji) i dodaj JEDNU rečenicu u prompt (u
   sekciji "Personality and Tone" ili na kraju "Role and Objective" — tvoja
   procjena gdje prirodnije stoji), npr.:
   ```txt
   Prefer replying in ${languageName} unless ${userName} clearly speaks a different language during the conversation.
   ```
   **Ne mijenjaj ništa drugo u promptu** — samo dodaj tu jednu liniju, ne
   preformulišavaj postojeće instrukcije.

**Provjeri:** `node --check electron/ipc_handlers/realtime.cjs` čisto.
Postojeće ponašanje za `sr-Latn` (default) treba ostati suštinski isto —
model već po defaultu odgovara na srpskom kad se korisnik obraća na srpskom,
ova linija je eksplicitna potvrda te pretpostavke, ne promjena ponašanja.

---

## Acceptance criteria

- `npm run typecheck` i `npm run build` — čisto.
- `node --check electron/ipc_handlers/realtime.cjs` — čisto.
- Agent report: `agent_reports/2026-07-11_dictation-language-cascade.md`,
  standardni CLAUDE.md obrazac. **Eksplicitno navedi u izvještaju** da su
  en/de/es/fr fraze best-effort, ne native-speaker potvrđene.

Kad završiš, javi — Claude verifikuje (build/GitNexus impact) prije commita.
