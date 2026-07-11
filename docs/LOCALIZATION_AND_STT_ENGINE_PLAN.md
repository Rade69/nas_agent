# Lokalizacija + STT engine izbor — plan za kasniju implementaciju

**Status:** priprema/plan, ne implementacija. Napisano dok `pi` radi na
`docs/PI_TASK_INTERFACE_LANGUAGE_STT_BRIEF.md` (interface_language polje +
STT jezički hint za Dictation Mode) — taj zadatak je mali, mehanički presjek
onoga što je ovaj dokument planira u punom obimu. Ovaj dokument NE mijenja
kod, samo konsoliduje odluke za kad se stvarno krene u implementaciju.

## Odnos prema postojećim dokumentima

- `docs/RICKY_GUI_LOCALIZATION_PLAN.md` — već postoji, pokriva **samo GUI
  tekst** (i18n string prevod), i eksplicitno (linije 7-17) isključuje STT/
  TTS/agent jezik iz svog obima. Taj dokument ostaje izvor istine za GUI
  string lokalizaciju (react-i18next, `src/i18n/locales/*.json`,
  `sr-Latn`/`en`/`de`/`es`/`fr`) — ne duplira se ovdje.
- Ovaj dokument pokriva ono što `RICKY_GUI_LOCALIZATION_PLAN.md` namjerno
  ostavlja po strani: STT engine izbor (cloud/lokalni) i puna lista mjesta
  gdje `interface_language` treba imati efekat van same GUI labele.

## Trenutno stanje (nakon pi-jevog zadatka)

- `interface_language` postoji kao polje u `UserSettings` (backend), sa
  dropdown-om u Settings panelu.
- Mijenja STT `language` hint koji se šalje OpenAI Realtime API-ju za
  Dictation Mode (`electron/ipc_handlers/realtime.cjs`,
  `src/lib/realtime.ts` `setDictationMode()`), preko malog mapping-a
  (`sr-Latn→"sr"`, `en→"en"`, itd.).
- Sam GUI tekst (dugmad, labele, poruke) **ostaje na srpskom, hardkodiran**
  — `interface_language` polje trenutno ne pokreće nikakav i18n loader, jer
  taj loader još ne postoji (to je `RICKY_GUI_LOCALIZATION_PLAN.md` posao,
  još nije počet).

## Otvoreno pitanje: jedno polje ili više nezavisnih?

`RICKY_GUI_LOCALIZATION_PLAN.md` (linije 9-17) tretira GUI jezik, STT jezik,
TTS glas i jezik agentovog odgovora kao **četiri odvojena koncepta** koja se
slučajno mogu poklapati, ali ne moraju. Pi-jev zadatak sad vezuje
`interface_language` direktno na STT hint — pragmatično za MVP (jedno polje,
jedan dropdown), ali dugoročno vrijedi razmisliti da li:

```txt
- jedno polje "interface_language" upravlja svim sa istom vrijednošću
  (jednostavnije za korisnika, manje kontrola), ILI
- GUI jezik i STT jezik ostaju odvojena polja
  (korisnik npr. čita UI na engleskom ali diktira na srpskom).
```

Preporuka: krenuti sa JEDNIM poljem (već urađeno) dok ne postoji stvaran
korisnički zahtjev za razdvajanjem — ne graditi kontrolu koja nikom ne
treba. Zabilježiti ovdje da je to bila svjesna odluka, ne previd.

## Šta SVE treba da se promijeni kad korisnik promijeni jezik (cascade lista)

Ovo je odgovor na "šta se time izborom dalje mijenja u samom prozoru" —
puna lista mjesta koja zavise od jezika, mnoga trenutno hardkodirano na
srpski i van dosega pi-jevog trenutnog zadatka:

1. **GUI tekst** (dugmad, labele, poruke o grešci) — `RICKY_GUI_LOCALIZATION_PLAN.md`,
   nije počet. Najveći posao — cijeli `src/components/**` treba i18n key-eve
   umjesto hardkodiranog teksta.
2. **STT jezički hint za Dictation Mode** — pi-jev trenutni zadatak, gotovo.
3. **Dictation glasovni okidači — TRENUTNO HARDKODIRANI NA SRPSKI, van
   obima pi-jevog zadatka, stvaran gap:**
   - `src/App.tsx` — supstring `"dikt"` kao okidač za ulazak u Dictation
     Mode (provjerava se u transkriptu korisnika). Na engleskom bi trebalo
     biti npr. `"dictat"` ili slično — ovo je string match, ne prevod fraze
     jednu-na-jednu preko i18n-a, treba posebna mapa po jeziku.
   - `DICTATION_EXIT_PHRASES` konstanta (`src/App.tsx`) — sve fraze su na
     srpskom ("vrati se u normalan", "prekini diktat", itd.). Za druge
     jezike treba paralelna lista po `interface_language`.
   - `src/lib/cyrillicToLatin.ts` transliteracija — specifična za srpski
     ćirilica/latinica problem, nije primjenjiva niti štetna za druge
     jezike (samo se ne bi imala šta transliterisati), ne treba mijenjati.
4. **TTS glas** — trenutno fiksno `voice: "cedar"`
   (`electron/ipc_handlers/realtime.cjs`, `session.audio.output.voice`).
   OpenAI Realtime glasovi nisu striktno jezički vezani (isti glas govori
   više jezika), ali vrijedi provjeriti da li neki glas zvuči prirodnije za
   dati jezik prije nego se ovo proglasi "nema potrebe za promjenom".
5. **Jezik agentovog govornog odgovora** — `buildRickyInstructions()`
   (`realtime.cjs`) je engleski-pisani prompt (uputstva modelu su na
   engleskom, model i dalje odgovara na jeziku korisnika jer je Realtime
   multilingual). Nije nužno da instrukcije budu prevedene — ali ako
   `interface_language` postane npr. `en`, vrijedi eksplicitno dodati
   liniju u prompt da agent odgovara na `interface_language`, umjesto da se
   oslanja isključivo na auto-detekciju jezika korisnikovog govora (ova dva
   se mogu razići: korisnik postavi UI na engleski ali povremeno govori
   srpski).
6. **"Doradi" meni (text rewrite)** — `python_backend/app/api/text.py`
   prompti za formalize/shorten/proofread/translate_en su hardkodirani na
   srpski i pretpostavljaju srpski ulazni tekst. `translate_en` posebno
   pretpostavlja da se uvijek prevodi NA engleski, bez obzira na
   `interface_language` — trebalo bi razmisliti da li "Prevedi" treba da
   cilja neki drugi jezik kad `interface_language` nije srpski (npr. ako je
   korisnikov interface jezik njemački, da li "Prevedi" cilja engleski ili
   srpski ili nešto treće — otvoreno pitanje, ne pretpostavljati).
7. **Aktivnost/log tekstovi** (`createActivityEvent` pozivi kroz cijeli
   `App.tsx`) — hardkodirani srpski nizovi kao user-facing tekst u Activity
   panelu. Isti posao kao stavka 1 (GUI tekst), samo drugi sloj komponenti.

## Plan A — Cloud vs. lokalni STT engine izbor (backlog stavka iz
`RICKY_GUI_LOCALIZATION_PLAN.md` linije 206-224)

Arhitektura (moj dio, ne pi-jev):

- **Cloud (postojeće)** — OpenAI Realtime `whisper-1`, ništa se ne mijenja,
  ostaje default.
- **Lokalno (novo)** — `faster-whisper`, poseban Python proces/model, NE
  Realtime WebRTC put. Zahtijeva:
  - Novi backend endpoint ili lokalni proces koji prima audio chunk-ove i
    vraća transkript (van OpenAI Realtime data channel-a potpuno — Dictation
    Mode bi u lokalnom režimu morao snimati audio lokalno i slati ga na
    lokalni STT, ne kroz postojeći WebRTC voice pipeline).
  - "Lijeno" preuzimanje modela — model fajl (stotine MB do par GB, zavisno
    od veličine) preuzima se tek kad korisnik prvi put izabere "Lokalno" u
    Settings, ne pakuje se unaprijed uz instalaciju (izbjegava veći
    installer za sve korisnike koji ovo nikad ne koriste).
  - **Izbor veličine modela** (korisnikovo pitanje iz razgovora) — faster-
    whisper nudi `tiny`/`base`/`small`/`medium`/`large` — trade-off brzina
    (CPU) vs. tačnost. Settings dropdown pored jezika: "Veličina modela"
    sa napomenom o očekivanoj brzini/tačnosti/veličini preuzimanja po
    opciji, prikazano PRIJE preuzimanja (korisnik zna šta bira).
  - Poseban proces lifecycle (start/stop), sličan `pythonProcess.cjs`
    obrascu ali NIJE isti proces (STT inference ne treba dijeliti resurse
    sa FastAPI backend-om koji servira sve ostalo).
  - Isti Cyrillic/Latin problem kao cloud whisper (dokumentovano u
    `RICKY_GUI_LOCALIZATION_PLAN.md` linije 166-167, testirano u
    `whisper-test/whisper_bcs_test.py`) — `cyrillicToLatin.ts` safety net
    već postoji i pokriva oba slučaja (cloud i lokalni), ne treba duplirati.
- **Trade-off koji treba imati na umu** (već zabilježeno u backlog-u): dva
  paralelna STT koda znače duplo održavanje/testiranje, ne samo dodatno UI
  pitanje. Ne raditi ovo dok ne postoji jasan razlog (offline korištenje,
  trošak) da cloud-only više nije dovoljan.

## Redoslijed rada (kad se krene)

1. Sačekati da pi završi i ja komitujem trenutni interface_language/STT
   hint zadatak (izbjeći sudar na `SettingsPanel.tsx`/`realtime.cjs`).
2. GUI i18n rollout (`RICKY_GUI_LOCALIZATION_PLAN.md`) — najveći, ali
   najmanje rizičan posao (čisto UI, bez novih procesa/modela). Dobar
   kandidat za dalje delegiranje pi-ju/Codex-u po komponenti, isti obrazac
   kao dosadašnji brief-ovi.
3. Cascade lista stavke 3, 5, 6 iznad (dictation trigeri/exit fraze,
   agent-jezik u promptu, "Doradi" prompti) — manji, ciljani zadaci, mogu
   ići paralelno sa #2 pošto diraju različite fajlove.
4. Cloud/lokalni STT izbor — zadnje, najveći arhitektonski rizik, radim
   sam (ne mehanički delegiranje) prvi prolaz.
