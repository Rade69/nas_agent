# Agent report — companion orb startup visibility + connect() latency

**Datum:** 2026-07-10
**Povod:** korisnička prijava — mali orb se pojavljuje uz otvoren puni prozor
(trebao bi biti vezan samo za računarski mod), i inicijalizacija mikrofona
traje predugo.

## Bug 1 — companion orb vidljiv odmah pri startu

**Uzrok:** `createCompanionWindow()` (`electron/core/companionWindow.cjs`) se
poziva bezuslovno u `app.whenReady()` (`electron/main.cjs:747`), ali
`BrowserWindow` konstruktor nije imao `show: false`. Electron podrazumijevano
pravi nove prozore **vidljive** (`show: true` je default). Rezultat: orb je
iskakao odmah pri pokretanju app-a, prije bilo kakvog prelaska u računarski
mod — tačno ono što je korisnik vidio na screenshotu (puni prozor otvoren, a
orb ipak prisutan).

**Popravka:** dodato `show: false` u `BrowserWindow({...})` opcije. Prozor se
sad kreira skriven; vidljivost isključivo kontrolišu `showCompanion()`/
`hideCompanion()` (ručni toggle, `companion:show/hide` IPC, i auto-show/hide
na `set_mode` iz jučerašnjeg rada). Bez regresije — ta dva puta već rade
`if (!win.isVisible()) win.show()` odn. provjeravaju `isVisible()` prije
`hide()`, pa im ne smeta što prozor sad kreće skriven.

**Fajl:** `electron/core/companionWindow.cjs` (1 opcija dodana).

## Bug 2 — spora inicijalizacija glasa (connect())

**Uzrok:** `RickyRealtimeClient.connect()` (`src/lib/realtime.ts`) je tri
međusobno nezavisna async poziva izvršavao **redom** umjesto paralelno:
`getToolSpecs()` (lokalni IPC) → `createRealtimeToken()` (mrežni poziv:
Electron → Python backend → OpenAI, najsporiji korak) → `getUserMedia()`
(OS dozvola/inicijalizacija mikrofona). Nijedan od ta tri ne zavisi od
rezultata prethodnog, pa je serijalizacija čisto dodavala kašnjenje —
ukupno čekanje je bio zbir sva tri, umjesto trajanja najsporijeg.

**Popravka:** sva tri poziva sad idu kroz `Promise.all([...])`, izvršavaju se
konkurentno. `RTCPeerConnection`/`audio` element/`pc.ontrack` handler (koji ne
zavise od rezultata ta tri poziva) su pomjereni ISPRED `Promise.all` bloka, pa
se instanciraju dok se čeka. Isti error-handling (postojeći `try/catch` oko
cijelog bloka) — ako `getUserMedia()` odbije dozvolu, `Promise.all` odbacuje i
catch grana radi identično kao prije.

**Fajl:** `src/lib/realtime.ts` (`connect()` metoda, restrukturiran redoslijed
poziva — logika/rezultati identični, samo paralelno umjesto sekvencijalno).

## Treća stavka — "ne razumije me baš" (nije popravljeno, objašnjenje)

Ovo NIJE nešto što sam mogao dijagnostikovati/popraviti statičkom analizom
koda — kvalitet prepoznavanja govora dolazi od OpenAI Realtime modela
(`gpt-realtime-2`), ne od našeg koda. Provjerio sam da je audio pipeline
podešen po dobroj praksi (`echoCancellation`, `noiseSuppression`,
`autoGainControl` sva tri uključena). Jedina podesiva varijabla u našem kodu
je VAD osjetljivost:

```js
turn_detection: { type: "semantic_vad", eagerness: "medium", ... }
```

`eagerness: "medium"` može prerano presjeći govor prije nego model dobije
cijelu rečenicu, što bi se osjetilo kao "ne razumije me". Ovo je **UX
kompromis** (niže `eagerness` = strpljivije, ali sporiji odgovori) koje samo
korisnik treba isprobati kroz stvarnu upotrebu — nisam ga mijenjao bez tvoje
odluke. Ako i dalje smeta poslije bržeg connect()-a, probaj `eagerness: "low"`
kao sljedeći korak.

## Verifikacija

- `node --check electron/core/companionWindow.cjs` — čisto.
- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- Runtime smoke NIJE urađen (traži pokrenut app) — oba bug-a su UI/runtime
  ponašanje bez automatskih testova.

## Šta nije dirano

- `showCompanion`/`hideCompanion`/`toggleCompanion` logika — netaknuta.
- VAD `eagerness` postavka — namjerno neizmijenjena (korisnikova odluka).
- Ostatak `connect()` (WebRTC offer/answer, data channel handleri) — netaknut.

## Potreban follow-up

Runtime smoke: pokrenuti app, potvrditi (a) orb se NE pojavljuje pri startu
dok se ne uđe u računarski mod, (b) subjektivno primjetno brže povezivanje
glasa.

## Potrebna korisnička potvrda

Oba bug-a su UI/runtime ponašanje bez automatskih testova — treba ručna
potvrda prije commita.
