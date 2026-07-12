# Agent report — GUI i18n infrastruktura (Localization PR-1, prošireno)

**Datum:** 2026-07-11
**Scope:** `package.json` (i18next + react-i18next), `src/i18n/index.ts` (novo),
`src/i18n/locales/{sr-Latn,en,de,es,fr}.json` (novo), `src/main.tsx`,
`src/App.tsx`, `src/lib/voiceState.ts`, `src/components/Sidebar.tsx`,
`src/components/pixel/{TopBar,SettingsPanel,Drawer,IdleScreen,Previews,PixelMockupBoard}.tsx`.

**GitNexus impact:** pokrenuti `detect_changes` prije commita, po standardnoj
proceduri (nije rađeno tokom same izrade — planiranje + iterativna izmjena
puno komponenti u jednom prolazu).

## Šta je urađeno — dvije runde

### Runda 1 — infrastruktura + dokaz lanca (odobreno kroz Plan mode)

1. Instaliran `i18next` + `react-i18next` (nova dependency).
2. `src/i18n/index.ts` — i18next init, `lng: "sr-Latn"`, `fallbackLng: "en"`,
   uvezen jednom u `src/main.tsx` (dijele ga glavni prozor i companion orb
   renderer, isti bundle).
3. `interface_language` pokreće i18next uz postojeći STT hint mehanizam:
   - `src/App.tsx` mount-fetch `useEffect` (dodao pi za dictation cascade,
     `e075344`) proširen sa `i18n.changeLanguage(s.interface_language)`.
   - `SettingsPanel.tsx` `handleSaveLanguage()` poziva
     `i18n.changeLanguage(...)` odmah nakon snimanja — bez restarta app-a.
4. Konvertovane tri komponente: `Sidebar.tsx`, `TopBar.tsx`,
   `voiceState.ts` `voiceStateLabel()` (potonja je plain funkcija, koristi
   `i18n.t()` direktno umjesto `useTranslation()` hook-a).

**Korisnik je vizuelno potvrdio da runda 1 radi** — screenshotovi na sva 4
testirana jezika (en/fr/es/de) pokazuju Sidebar tabove, TopBar dugmad/status i
Settings jezički dropdown kako se ispravno mijenjaju uživo, bez restarta.

### Runda 2 — prošireno na osnovu tih screenshotova

Korisnik je primijetio da je ostatak dashboard-a i sam Settings panel (koji se
koristi da se promijeni jezik) ostao hardkodiran srpski u svakom jeziku —
vidljivo neusklađeno u demo-u. Prošireno na:

- **`SettingsPanel.tsx`** — puna konverzija: obje sekcije ("Lično"/"Jezik"),
  sve labele, hint tekstovi, status poruke (Čuvam/Sačuvano/Greška), loading
  tekst. (Napomena: opcije u language `<select>`-u — "Srpski (latinica)",
  "English", "Deutsch", itd. — namjerno OSTAJU neprevedene, standardna UI
  konvencija je da se imena jezika prikazuju u svom vlastitom, izvornom
  obliku bez obzira na trenutni jezik interfejsa.)
- **`Drawer.tsx`** — naslovi drawer-a (Aktivnost/Planovi/Memorija/Snimci
  ekrana/Postavke) sad reuse-uju iste `tabs.*` key-eve kao Sidebar (identičan
  tekst, jedan izvor istine, nema duplikata), + "Zatvori" aria-label.
- **`IdleScreen.tsx`** — cijeli ekran: "Ricky je spreman", mic dugme
  title-ovi, prompt placeholder, "Zadnja aktivnost"/"Prikaži sve", prazno
  stanje aktivnosti, "Brze komande" + sve 4 brze komande. Bitno: tekst brze
  komande je ISTOVREMENO i labela dugmeta i tekst koji se šalje kao
  `onQuickCommand(text)` — prevod labele automatski prevodi i poslatu
  komandu, što je namjerno i dosljedno sa "Prefer replying in languageName"
  dodatkom u system promptu (`agent_reports/2026-07-11_dictation-language-cascade.md`).
- **`Previews.tsx`** — `ConfirmationPreview`, `ActivityDrawerPreview`,
  `PlansDrawerPreview` (naslovi, tab labele, prazna stanja, dugmad) i
  `planStatusLabel()` (plain funkcija → `i18n.t()` direktno, isti pattern kao
  `voiceStateLabel()`). Iskorišten i18next pluralization (`stepsCount_one`/
  `stepsCount_other`) za "X koraka" — usput ispravlja postojeću gramatičku
  netačnost ("1 koraka" → sad ispravno "1 korak").
- **`PixelMockupBoard.tsx`** — svih 5 `MockupSection` naslova/opisa
  (SPREMAN/DIKTIRANJE/POTVRDA/AKTIVNOST/PLANOVI), memory/screens drawer
  placeholder tekstovi, i dva aria-labela koja reuse-uju postojeće key-eve
  (`topBar.dictation`, `voice.state.idle`).

## Zašto ovako

- Doc-ov primjer translation key spisak (`RICKY_GUI_LOCALIZATION_PLAN.md`
  linije 480-604) je iz starijeg redizajna i ne poklapa se doslovno sa
  trenutnim "pixel" komponentama — zadržana je doc-ova konvencija imenovanja
  (namespaced dot key-evi), ali vrijednosti su uzete iz STVARNOG trenutnog
  teksta u komponentama.
- Gdje je tekst identičan između komponenti (npr. "Aktivnost" u Sidebar tabu
  i u Drawer naslovu i u Previews card headeru), key se reuse-uje umjesto
  duplira — jedan izvor istine, manje šanse da prevodi divergiraju vremenom.
- Plain funkcije van React stabla (`voiceStateLabel`, `planStatusLabel`)
  koriste `i18n.t()` direktno — hook nije opcija, ovo je dokumentovan
  react-i18next pattern za non-component kod.

## Šta NIJE dirano (namjerno, sljedeća runda)

- `DictationScreen.tsx` (editor labele, "Doradi"/"Više" meniji, word count) —
  nije bio u screenshotovima koje je korisnik pregledao, ostaje za PR-2.
- `PlansPanel.tsx` / `ActivityTimeline.tsx` — PUNI prikazi unutar otvorenog
  drawer-a (ne mockup preview kartice), nisu bili vidljivi u screenshotovima,
  ostaju za PR-2.
- Error poruke, tool labele, risk labele van onoga što je već konvertovano —
  PR-3 iz doc-a.
- `electron/ipc_handlers/realtime.cjs` STT hint / agent jezik odgovora — već
  urađeno u prošloj rundi (`e075344`), nepromijenjeno ovdje.

## Verifikacija

- `npm run typecheck` — čisto (obje runde).
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning; glavni
  `index-*.js` chunk porastao ~65kB ukupno zbog i18next + lokalizovanog
  sadržaja — očekivano).
- **Runda 1 runtime potvrđena od korisnika** — 4 screenshot-a (en/fr/es/de),
  Sidebar/TopBar/Settings dropdown rade uživo bez restarta.
- **Runda 2 runtime NIJE testirana** — ista ograničenja okruženja kao ranije
  (nema browser-automation alata za Electron u ovom okruženju).

## Rizici / ograničenja

- de/es/fr vrijednosti (sve, uklj. rundu 2) nisu native-speaker potvrđene.
- `previews.stepsCount` pluralizacija oslanja se na i18next-ov default
  one/other bucket preko `Intl.PluralRules` za dati jezik — nije eksplicitno
  testirano da li "sr-Latn" kod ispravno pada na srpska pluralizaciona
  pravila u JS Intl-u (očekivano radi jer se "sr-Latn" BCP-47 tag razumno
  svodi na "sr" pravila, ali nepotvrđeno uživo).

## Potreban follow-up

- PR-2/PR-3 (DictationScreen, PlansPanel, ActivityTimeline, error/tool/risk
  labele) — dobar kandidat za pi delegaciju, isti obrazac (namespace-ovani
  key-evi, reuse gdje je tekst identičan, `useTranslation()` za komponente /
  `i18n.t()` za plain funkcije).

### Runda 3 — sitne UI popravke otkrivene runtime testom + window drag saga

Korisnik je runtime testirao rundu 2 uživo (screenshotovi na 4 jezika) i
prijavio nekoliko sitnih problema, popravljenih u istom prolazu:

- **Sidebar dugi prevodi** (npr. njemački "Bildschirmaufnahmen") su se
  prelamali u više redova jer sidebar kolona ima fiksnu širinu. Umjesto
  ellipsis-a (prvi pokušaj, korisnik ga nije htio — "samo si odsjekao
  riječi"), kolona sad koristi `minmax(trenutna-širina, max-content)` u oba
  mjesta gdje se definiše (`11-pixel-shell.css` `.pixel-window`,
  `12-pixel-board.css` `.pixel-window-idle`) — automatski se širi da stane
  najduži naziv, umjesto da siječe tekst.
- **Razmak header→kutija** na svih 5 dashboard sekcija — `.pixel-mockup-section`
  nije imao `gap` između naslova/opisa i kutije ispod (samo 3px padding na
  labeli). Dodano `gap: 10px`.
- **Unutrašnji padding prazne kutije** (`.pixel-confirmation-preview`) — bio
  2px, sad 22px (kartica je sjedila skoro nalijepljena na gornju ivicu).
- **Fontovi** — pažljivo, ne globalni sweep: `.pixel-section-label p`
  (11→12px), `.pixel-empty-preview strong/span` (11→13px, 10→12px),
  `.pixel-window-idle .pixel-card h2`/"Brze komande" dugmad (13→15px,
  11→13px) + ikonice (12→14px). Badže/pilule (Computer mode, risk badge)
  namjerno NISU dirane — fiksna širina, rizik da tekst ne stane.
- **"Brze komande" tekst skraćen** ("Napiši email šefu" → "Napiši email",
  "Planiraj sastanak sutra u 10h" → "Planiraj sastanak") na svih 5 jezika —
  korisnikova ocjena da je originalni tekst neintuitivan/predugačak. Bitno:
  ovaj tekst je i labela dugmeta i sadržaj koji se šalje kao brza komanda
  (`onQuickCommand`), pa je skraćivanje promijenilo i stvarnu komandu, ne
  samo prikaz.

**Window drag (frame:false prozor, electron/core/window.cjs) — zaseban,
duži problem, 4 iteracije:**

Korisnik je prijavio da se glavni prozor ne može pomjerati/prebaciti na drugi
monitor. Uzrok: trenutni "pixel" redizajn nikad nije dobio
`-webkit-app-region: drag` — postojeći `01-window.css` drag CSS cilja klase
(`.window-drag-strip` i sl.) koje više ne postoje nigdje u JSX-u, čist mrtav
kod od prije redizajna.

Iteracije (svaka testirana uživo od korisnika, popravljena na osnovu
stvarnog rezultata, ne teorije):
1. Drag na `.pixel-top-bar` (unutar "1. SPREMAN" kartice) + `no-drag` na
   dugmad unutra → radilo je za pomjeranje, ali korisnik je htio i širu
   traku (naslov "1. SPREMAN" iznad nje) kao hvataljku.
2. Drag dodan i na `.pixel-section-label` (svih 5 kartica) → pokvario
   minimize/maximize/close dugmad (main kartica se proteže preko cijelog
   gornjeg reda grid-a, `grid-template-areas: "main main main main"`, pa
   njen header direktno preklapa `.pixel-global-window-controls` u
   gornjem desnom uglu).
3. Isključen drag samo na `.pixel-section-main`-ovoj labeli (window-controls
   ponovo rade) → ali *cijeli* top-bar drag je prestao da radi, ne samo u
   uglu — neočekivano, jer izmjena teorijski nije trebala uticati na
   nepovezan element.
4. Pretpostavka da je `-webkit-app-region: drag` na elementu sa
   `backdrop-filter: blur()` (`.pixel-top-bar`) nepouzdan u kombinaciji sa
   drugom `no-drag` regijom u dokumentu — uklonjen drag sa top bara,
   prebačen na `.pixel-brand` (logo/status, bez blur-a, bez dugmadi,
   veličina prati sadržaj). Radilo je, ali korisnik je ponovo tražio da i
   "1. SPREMAN" traka bude hvataljka (najintuitivnije mjesto).
5. Vraćen drag na `.pixel-section-label` (svih 5 kartica) izolovano, bez
   diranja top bara → **ponovo pokvario window-controls dugmad**, dokazujući
   da blur NIJE bio pravi uzrok iz koraka 3 — pravi uzrok je specifično
   preklapanje `.pixel-section-main`-ove labele i
   `.pixel-global-window-controls`, bez obzira na `no-drag` + viši z-index
   na potonjem.
6. **Konačno rješenje:** Electron-ov algoritam za preklapajuće
   drag/no-drag regije izgleda da prati DOM/render redoslijed (kasnije
   pobjeđuje), ne z-index/stacking context — suprotno standardnom CSS
   hit-testing ponašanju. `.pixel-global-window-controls` je premješten da
   se renderuje POSLIJE `<PixelMockupBoard>` i `<ConfirmationDialog>` u
   `src/App.tsx` (čisto JSX reordering, vizuelno nema promjene jer je
   `position: fixed`). Ovo je bio zadnji test koji je korisnik potvrdio.

**Lekcija:** `-webkit-app-region` preklapanje u Electron-u se ne ponaša po
"očekivanoj" CSS logici (z-index/stacking context) — render/DOM redoslijed
je bio odlučujući faktor, otkriveno isključivo kroz iterativno testiranje
uživo, ne kroz čitanje dokumentacije/teoriju unaprijed.

## Potrebna korisnička potvrda

Korisnik je potvrdio da radi nakon zadnje izmjene (koraka 6) prije nego što
je zatražen commit.
