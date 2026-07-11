# Agent report — Diktiranje popravke + dashboard arhitektura (UI mockup-grid bug)

**Datum:** 2026-07-10
**Povod:** korisnička prijava — diktiranje ne radi ("nema dugmeta", glasovna
komanda "uđi u diktat mod" se pogrešno tumači kao računarski mod, potvrda se
traži dva puta, "nije baš intuitivan, konfuzan je").

## Sažetak — dva sloja problema, oba riješena

1. **Dictation-specifični bugovi** (nema eksplicitnog trigera, model brka mod).
2. **Veći arhitektonski nalaz otkriven usput:** `PixelMockupBoard` (live render
   put u `App.tsx`, ne dizajn-mockup kako sam prvo pogrešno pretpostavio) je
   **stalno prikazivao svih 5 "stanja" odjednom** u fiksnom gridu koji ispunjava
   cijeli prozor (`.pixel-mockup-board { display:grid; width:calc(100vw-24px);
   height:calc(100vh-18px); ... }`), uključujući **statičan lažni primjer**
   potvrde ("Pošalji email... sef@firma.com") koji se nikad nije mijenjao.
   Ovo je direktan uzrok "dupla potvrda" prijave — lažni stalni panel +
   pravi `ConfirmationDialog` modal izgledaju kao dva pitanja odjednom.

Korisnik je nakon razgovora eksplicitno potvrdio ciljanu arhitekturu:
**dashboard princip — sve sekcije ostaju vidljive, ali Idle/Diktiranje su
međusobno isključivi (glavna radna površina), dok Potvrda/Aktivnost/Planovi
ostaju kao periferni "na prvi pogled" paneli sa STVARNIM podacima.**

## GitNexus impact

`RickyRealtimeClient` (centralna klasa, 11 importera po ranijoj impact analizi
danas) — dodata nova javna metoda, ne mijenja postojeće. `PixelMockupBoard`/
`Previews.tsx`/`TopBar.tsx` — dirane prop signature i JSX struktura, provjereno
ručno (nema testova za ove komponente). Nizak-srednji rizik: aditivne izmjene +
jedna strukturna promjena (Idle/Diktiranje mutual exclusivity) koja je upravo
namjeravana popravka, ne slučajna regresija.

## 1. Dictation-specifične popravke

### a) Nema dugmeta → dodato eksplicitno "Diktiranje" dugme
`TopBar.tsx`: novo `onEnterDictation` prop + vidljivo dugme (plava, uz "Stop
sve"/mode-pill), prikazano samo kad NIJE već u diktatu. 100% pouzdano, ne
zavisi od modela.

### b) Glasovna komanda pogrešno tumačena kao računarski mod
**Uzrok:** nijedan mehanizam nije pratio ŽIVI izgovoreni transkript za "dikt"
— jedini "dikt" check je bio na KLIK quick-command putu (`onQuickCommand`).
Model, čuvši "diktat **mod**", nije imao pojma o "diktiranju" kao konceptu i
posegnuo je za jedinim alatom vezanim za riječ "mod" (`set_mode`).

**Popravka (dva sloja, ne oslanjanje samo na model):**
- `App.tsx` `onTranscript`: sad prati živi korisnički transkript za "dikt" i
  **lokalno, deterministički** aktivira diktat (`setScreen` + `setDictationMode`)
  — bez obzira šta model odluči da pozove. Bug uhvaćen i ispravljen usput:
  prva verzija je progutala rečenicu koja sadrži "dikt" ako je izgovorena
  DOK JE korisnik već u diktatu (npr. riječ "diktafon" bi obrisala tu rečenicu
  umjesto da je doda u tekst) — ispravljeno da se provjera "dikt" radi SAMO
  prije ulaska, ne i unutar aktivnog diktata.
- `electron/ipc_handlers/realtime.cjs` (`RICKY_INSTRUCTIONS`): dodata
  eksplicitna napomena — diktat NIJE računarski mod, model ne treba zvati
  `set_mode` niti bilo koji tool za to, samo kratko potvrditi i ušutjeti.

### c) "Dupla potvrda" — vidi tačku 2 ispod (korijen je bio šire od diktata)

## 2. Arhitektonski nalaz i popravka: stalni "sve odjednom" grid

**Otkriveno:** `App.tsx` renderuje `<PixelMockupBoard>` kao JEDINI glavni
sadržaj. Ta komponenta je bezuslovno renderovala svih 5 `MockupSection`
blokova (Idle, Dictation, **ConfirmationPreview — statična, 0 propsa,
hardkodirani lažni email primjer**, ActivityDrawerPreview, PlansDrawerPreview)
u fiksnom CSS gridu koji ispunjava cijeli prozor — bez IKAKVOG mehanizma da
sakrije/umanji neaktivne sekcije. Screenshot koji je korisnik poslao NIJE bio
dizajn-referenca kako sam prvo pretpostavio — to je stvarni, svaki-put izgled
app-a.

**Odluka (korisnik eksplicitno potvrdio nakon dvije runde pojašnjenja):**
dashboard princip, ne single-screen. Idle/Diktiranje dijele jedan
"glavni" grid-area (međusobno isključivi — ne postoji smisleno "napola
diktiraš, napola si na početnom ekranu"), dok Potvrda/Aktivnost/Planovi ostaju
periferni paneli koji legitimno koegzistiraju (za razliku od Idle/Diktiranje).

**Popravka:**
- `PixelMockupBoard.tsx`: Idle i Dictation `MockupSection` blokovi sad
  međusobno isključivi (`screen === "dictation" ? <Dictation/> : <Idle/>`),
  dijele CSS klasu `pixel-section-main`.
- `Previews.tsx` `ConfirmationPreview`: **potpuno prepravljena** — prima
  `confirmation: Confirmation | null` (postojeći `pendingConfirmation` state,
  isti koji koristi pravi `ConfirmationDialog`). Prazno stanje
  ("Nema aktivne potvrde") preko `EmptyPreviewState` kad ništa ne čeka; stvarni
  `action_name`/`risk_level`/`summary` kad nešto čeka. Uklonjena lažna
  hardkodirana polja (email/primalac/predmet, dugmad Izmijeni/Otkaži/Pošalji —
  te akcije ostaju ISKLJUČIVO na pravom `ConfirmationDialog` modalu, panel je
  sad čisto read-only "na prvi pogled" prikaz, ne drugi akcioni put).
  Uklonjeni sad-neupotrebljeni importi (`IconChevronDown`, `IconSend`).
- `12-pixel-board.css`: `grid-template-areas` promijenjen sa
  `"idle idle dictation dictation"` na `"main main main main"` (glavna sekcija
  sad zauzima punu širinu gornjeg reda umjesto polovine, pošto se samo jedna
  od dvije renderuje). Novo `.pixel-top-dictation` dugme stil (plava, isti
  obrazac kao postojeći crveni `.pixel-top-stop-all`).

**Nije dirano (namjerno, van scope-a):**
- Aktivnost/Planovi periferni paneli — VEĆ su bili real-data-driven
  (`activityEvents`/`plans` props, ne hardkodirano) — provjereno prije
  zaključka da NE trebaju popravku, za razliku od Potvrde.
- Vizuelna "veličina po aktivnosti" logika za periferni red (Potvrda/
  Aktivnost/Planovi) — te tri legitimno koegzistiraju po dizajnu, gridov
  postojeći omjer visina (59/41) već izražava "glavna sekcija veća,
  periferne manje" — nije trebalo novu logiku.
- Numerisani naslovi sekcija ("1. SPREMAN", "3. POTVRDA"...) — kozmetički
  ostatak dizajn-review formata, nisu uzrok prijavljenih bugova, ostavljeno
  za eventualni budući polish (naslovi/opisi trenutno čitaju kao dizajn-
  anotacije, ne kao runtime UI tekst — vrijedno preimenovati kasnije).

## Verifikacija

- `node --check electron/ipc_handlers/realtime.cjs` — čisto.
- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- `git diff --stat` — 7 kod-fajlova, 226 dodano/112 obrisano — veći ali
  koherentan diff (dva usko povezana problema riješena zajedno).

**Runtime smoke NIJE urađen — kritično prije commita**, jer:
1. `setDictationMode` (session.update event) i dalje čeka nezavisnu potvrdu
   iz prošlog kruga (Faza 1 cloud STT) — sad se dodatno oslanja i na to da
   sistem prompt izmjena stvarno spriječi model da poziva `set_mode`.
2. Nova mutual-exclusivity logika i CSS grid promjena nisu vizuelno
   provjereni (nemam screenshot pristup).

## Test koraci za korisnika

1. Pokreni app — potvrdi da se prikazuje SAMO Idle ekran (ne i prazan/skriven
   "Diktiranje" prostor) preko pune širine gornjeg reda.
2. Klikni novo plavo "Diktiranje" dugme u top baru — potvrdi da se ekran
   prebaci na Diktiranje, da Potvrda/Aktivnost/Planovi paneli ostanu vidljivi
   dolje.
3. Otkaži diktiranje — potvrdi povratak na Idle, opet preko pune širine.
4. Aktivnom glasovnom sesijom izgovori "uđi u diktat mod" (bez klika) —
   potvrdi (a) NE minimizira prozor / NE ulazi u računarski mod, (b) ekran se
   ipak prebaci na Diktiranje, (c) Riki kratko potvrdi i ne prekida te dalje
   dok pričaš.
5. Izazovi stvarnu potvrdu (bilo koju high-risk akciju) — potvrdi da se
   pojavi TAČNO JEDAN dijalog (pravi `ConfirmationDialog`), a da periferni
   "Potvrda" panel dolje pokaže STVARNE podatke te akcije (ne lažni email),
   i da nestane/vrati se na "Nema aktivne potvrde" nakon odluke.

## Potreban follow-up

- Ako runtime test pokaže da je Riki i dalje prekida diktat ili i dalje zove
  `set_mode` — sistem prompt izmjena možda nije dovoljna, treba dodatna
  provjera OpenAI Realtime API ponašanja uživo.
- Numerisani naslovi sekcija (kozmetika) — kandidat za budući polish.
- Puni "veličina po aktivnosti" vizuelni sistem (ako se ispostavi da treba
  više od trenutnog fiksnog 59/41 omjera) — zaseban budući zadatak.

## Potrebna korisnička potvrda

Runtime smoke obavezan prije commita — ovo je najveći, najviše-međusobno-
zavisan skup izmjena danas (dictation trigger + prompt fix + strukturna UI
promjena), sve zajedno prvi put testirano u praksi tek sad.
