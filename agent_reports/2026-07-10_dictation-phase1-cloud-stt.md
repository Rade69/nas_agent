# Agent report — Diktiranje Faza 1: Cloud STT (reuse postojeće sesije)

**Datum:** 2026-07-10
**Izvršilac:** Claude Code.
**Referenca:** `docs/RICKY_GUI_LOCALIZATION_PLAN.md` linije 206–227 (backlog stavka
"izbor cloud vs. lokalni STT za Dictation Mode", eksplicitno odobreno danas od
korisnika: implementirati obje opcije, korisnik bira u Settings).

## Scope

Faza 1 = **cloud** dio dvojnog STT plana, isključivo za **postojeći in-app
`DictationScreen`** (ne global-hotkey "brzi diktat" iz `ORB_PRESENCE_SPEC.md` —
to je zaseban, kasniji zadatak).

## Dizajn odluka — odstupanje od doslovnog teksta backlog napomene, obrazloženo

Backlog napomena predviđa "OpenAI transkripcija (ne puna Realtime sesija, samo
transcribe poziv radi cijene)" — implicitno pretpostavljajući scenario gdje
diktat NEMA već otvorenu Realtime sesiju (tačno scenario global-hotkey
diktata). Provjereno u kodu: `DictationScreen` se **jedino** otvara iz
`onQuickCommand` handlera dok je korisnik već u aktivnoj glasovnoj sesiji
(grep potvrdio: samo jedno mjesto poziva `setScreen("dictation")` u cijelom
`App.tsx`). U TOM kontekstu, otvaranje DRUGE paralelne mikrofon-hvatalice +
poziv posebnog transcribe endpointa bi:
- dupliralo trošak (STT se već plaća/računa kroz otvorenu Realtime sesiju),
- riskiralo dva istovremena mic capture-a (echo/resursi),
- tražilo nov Python backend endpoint + IPC + audio-blob prenos.

Umjesto toga: **reuse već-otvorene sesije ugrađenu transkripciju** (event
`conversation.item.input_audio_transcription.completed`, koji već postoji i
već se koristi za glavni transcript). Jeftinije (nula dodatnih poziva),
jednostavnije (nula novih backend/IPC površina), nula rizika od dva mic
capture-a. Doslovni "transcribe poziv" pristup ostaje ispravan izbor za
BUDUĆI global-hotkey diktat (gdje nema otvorene sesije) — ne za ovaj ekran.

## Otkriven tehnički problem i rješenje

Realtime sesija je konfigurisana sa `turn_detection.create_response: true`
(`electron/ipc_handlers/realtime.cjs`) — model automatski pokušava GLASOM
odgovoriti nakon svake detektovane pauze u govoru. Bez izmjene, Riki bi
pokušavao da "razgovara" nakon svake izdiktirane rečenice umjesto da samo
tiho hvata tekst.

**Rješenje:** nova javna metoda `RickyRealtimeClient.setDictationMode(active)`
šalje `session.update` event preko već-otvorenog data channela, mijenjajući
SAMO `turn_detection.create_response` (true↔false), zadržavajući ostatak
konfiguracije identičnim originalnoj. Ovo NE gasi transkripciju korisnikovog
govora (koja je odvojen mehanizam od auto-odgovora) — samo sprječava model da
sam inicira odgovor dok je diktat aktivan.

## Šta je urađeno (fajl po fajl)

1. **`src/lib/realtime.ts`** — nova javna metoda `setDictationMode(active: boolean)`
   (koristi postojeći privatni `sendEvent`, isti no-op-ako-nije-povezan guard
   kao `sendText`).
2. **`src/App.tsx`**:
   - `screenRef` (novi `useRef` + prateći `useEffect`) — `onTranscript`
     callback je definisan u mount-only `useEffect([])`, pa direktno čitanje
     `screen` state-a bi bilo zastarjelo (stale closure) zauvijek na "home".
     Ref rješava ovo (potvrđeno provjerom prije pisanja koda).
   - `onTranscript`: dok je `screenRef.current === "dictation"` i poruka je od
     korisnika (`entry.role === "user"`), tekst se dodaje u `dictationText`
     (uz postojeće ponašanje — i dalje ide u glavni transcript, nije uklonjeno).
   - `onQuickCommand`: kad tekst sadrži "dikt", poziva `setDictationMode(true)`
     uz postojeći `setScreen("dictation")`.
   - `onDictationCancel`/`onDictationSend`: oba pozivaju `setDictationMode(false)`
     prije povratka na "home" — vraća normalno konverzacijsko ponašanje.

## Šta NIJE dirano (namjerno, van scope-a ove faze)

- `Nastavi diktiranje`, `Doradi ▾` meni (Formalizuj/Skrati/Provjeri
  pravopis/Prevedi), `...` dugme u `DictationScreen.tsx` — i dalje
  neožičeni, planiran zaseban mehanički zadatak.
- Sistem prompt (`RICKY_INSTRUCTIONS`) — nije dodana posebna "kad si u
  diktatu, budi kratak" instrukcija. `create_response: false` strukturno
  sprječava neželjene auto-odgovore; prva potvrda (kad `sendText` eksplicitno
  zatraži `response.create`) ostaje pod postojećim opštim tonom uputstva
  ("Concise, calm, useful"). Ako runtime test pokaže da je prva potvrda
  predugačka, to je jeftina naknadna dopuna.
- Lokalni STT (faster-whisper) — Faza 2, zaseban zadatak.
- Global-hotkey brzi diktat — zaseban zadatak iz `ORB_PRESENCE_SPEC.md`.

## Verifikacija

- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- `git diff --stat` — 2 fajla, 56 dodanih/3 obrisanih linija, mali i čist diff.

**Runtime smoke NIJE urađen — ovo je najvažnija stavka za potvrdu.** Tačan
oblik `session.update` eventa (nested `audio.input.turn_detection`) je
izveden po analogiji sa POSTOJEĆOM, dokazano-radnom inicijalnom konfiguracijom
sesije (ista struktura, samo `create_response` promijenjen) — ali OpenAI
Realtime API-jevo tačno ponašanje na ovaj konkretan event nisam mogao
nezavisno testirati (nemam live pristup). Treba ručno provjeriti:
1. Uđi u aktivnu glasovnu sesiju, izgovori komandu koja sadrži "dikt".
2. Potvrdi da se ekran prebaci na Diktiranje.
3. Izgovori nekoliko rečenica — potvrdi da se pojavljuju u textarea-i I da
   Riki NE pokušava odgovoriti glasom nakon svake.
4. Klikni "Pošalji agentu" — potvrdi da se normalno konverzacijsko ponašanje
   vrati (Riki opet odgovara na sljedeći govor).

## Rizici/ograničenja

- Ako `session.update` sa ovim tačnim oblikom ne bude prihvaćen/ispravno
  primijenjen od OpenAI Realtime API-ja, `create_response` možda ostane
  `true` i Riki će nastaviti prekidati diktat — to bi runtime test odmah
  otkrio (vidljivo ponašanje, ne tih neuspjeh).
- `dictationText` se gradi isključivo appendovanjem (`prev + " " + text`) —
  nema mehanizma za brisanje/ispravku pojedinačne rečenice iz teksta osim
  ručne izmjene u samoj textarea-i (već postojeća `onChange`/`onDictationChange`
  putanja to omogućava).

## Potreban follow-up

- Runtime smoke (korisnik) — kritično prije bilo kakvog daljeg rada na ovoj
  temi, jer *cijeli* dizajn zavisi od toga da li `session.update` stvarno
  mijenja server-side ponašanje kako se očekuje.
- Ako radi: preostala dugmad u `DictationScreen.tsx`, pa Faza 2 (lokalni STT).
- Ako ne radi: istražiti tačan OpenAI Realtime `session.update` schema
  (trenutno izveden po analogiji, ne po zvaničnoj dokumentaciji koju nisam
  mogao dohvatiti uživo).

## Potrebna korisnička potvrda

Runtime smoke je obavezan prije commita — ovo je jedina izmjena danas gdje
ne mogu sam nezavisno potvrditi da server-side ponašanje radi kako očekujem
(za razliku od Electron/TS izmjena ranije koje sam mogao potvrditi
node --check/typecheck/build).
