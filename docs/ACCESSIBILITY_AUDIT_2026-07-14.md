# Analiza pristupačnosti za slijepe i slabovidne korisnike

**Datum:** 2026-07-14
**Tip:** Read-only audit trenutnog stanja koda — bez izmjena.
**Metod:** Grep/čitanje kroz sve `src/**/*.tsx` (23 komponente), `src/styles/**/*.css`
(16 fajlova), system prompt (`electron/ipc_handlers/realtime.cjs`).
**Namjena:** Baza za odluku o pristupačnosti i za buduće funkcionalnosti
(npr. najavljena "neka druga funkcionalnost" — isti nalazi važe).

> Napomena o pouzdanosti: ovo je audit na nivou koda (grep + čitanje), NE
> testiranje sa stvarnim screen reader-om (NVDA/JAWS) niti sa stvarnim
> korisnicima. Nalazi su tačni za "šta kod sadrži", ali stvarno iskustvo se
> mora potvrditi živim testom prije bilo kakve tvrdnje o pristupačnosti.

---

## 0. Izvršni rezime

Aplikacija ima **snažnu strukturnu prednost** za slijepe korisnike koju
većina aplikacija nema: voice-first arhitektura (OpenAI Realtime STT+TTS +
dictation mode) znači da su ULAZ i glavni razgovorni IZLAZ već govorni. To je
~60-70% posla za "slijepa osoba može voditi osnovni razgovor" već urađeno
samim dizajnom.

Ali postoje tri sistemska jaza:

1. **Vizuelni izlaz mnogih funkcija je NAMJERNO tih** — system prompt
   eksplicitno kaže modelu da ne opisuje vizuelne događaje. Slijepa osoba
   dobije sliku/grafikon/tabelu koju niko ne opiše.
2. **Nema "objava stanja"** (ARIA live regions) — samo 1 u cijeloj aplikaciji.
   Screen reader ne saznaje "povezujem se", "alat traje", "stigla je potvrda".
3. **Slabovidni sloj skoro ne postoji** — 161 fiksnih `px` veličina fonta, 0
   skalabilnih; reduced-motion pokriva samo 2 od ~10 animiranih površina.

Procjena: upotrebljiv MVP za slijepe je blizu (1-2 sedmice fokusiranog rada
na 3 stvari niže). Puna WCAG pristupačnost + slabovidni vizuelni sloj +
testiranje je znatno veći, kontinuiran poduhvat.

---

## 1. Šta je VEĆ dobro (ne dirati, samo znati)

| Prednost | Dokaz u kodu |
|---|---|
| Voice-first ulaz/izlaz | OpenAI Realtime WebRTC audio; dictation mode; `src/lib/realtime.ts` |
| Nativna dugmad, ne div-onClick | 71 `<button>` naspram samo 1 `<div onClick>` (`Drawer.tsx` backdrop) — nativna dugmad su tastaturno operabilna i screen-reader-najavljena besplatno |
| ConfirmationDialog ima osnovni ARIA | `role="dialog"`, `aria-modal="true"`, `aria-label` (`ConfirmationDialog.tsx:101`) |
| Neke dekorativne komponente imaju aria-label | `RickyFace.tsx:24` (`aria-label={mood}`), `MiniComputerWindow` stage aria |
| Kill-switch objava POSTOJI | Jedina live region: `App.tsx:649` `role="status"` |
| Reduced-motion se poštuje (djelimično) | `09-ricky-orb.css:265`, `07-companion-orb.css:211` |
| Escape = kill switch (globalno) | `App.tsx:343-348`, uz ispravno preskakanje kad je fokus u INPUT/TEXTAREA |
| i18n postoji (5 jezika) | Olakšava dodavanje govornih/ARIA stringova bez hardkodiranja |

---

## 2. Nalazi za SLIJEPE korisnike (audio / screen reader)

### K-1 (KRITIČNO) — Vizuelni izlaz je namjerno tih
**Dokaz:** `electron/ipc_handlers/realtime.cjs:58` — system prompt doslovno:
> "When a thumbnail finishes generating or editing, do not announce it
> verbally. The UI updates silently."

Sekcija `# Artifacts` (linija 64-66) kaže modelu da KORISTI artifacts za
vizuelni prikaz (slike, tabele, grafikoni, kod) ali ga NIGDJE ne uputi da
govorno opiše taj sadržaj. Za slijepu osobu, svaka slika/grafikon/tabela/
thumbnail je "crna rupa" — postoji na ekranu, niko je ne opisuje.

**Zašto je najvažniji:** aplikacija je voice-first za ULAZ, ali IZLAZ mnogih
funkcija je silent-visual po dizajnu. Ovo je jaz #1.

**Popravka (srednje):** dodati "accessibility mode" granu u system prompt —
kad je uključena, model MORA govorno sažeti svaki vizuelni artifact
(npr. "Prikazao sam tabelu sa 4 reda: ..."; "Grafikon pokazuje..."; "Thumbnail
je gotov, prikazuje..."). Ovo je promjena prompta + jedan settings toggle, ne
arhitektonski rad. Postojeći `image_generate`/thumbnail već imaju prompt kao
metapodatak koji se može pročitati nazad.

### K-2 (KRITIČNO) — Nema objava stanja (live regions)
**Dokaz:** grep `aria-live|role="status"|role="alert"` → samo 1 pogodak u
cijeloj aplikaciji (kill-switch). Voice state indikator (`TopBar.tsx:50`
`pixel-state`), connection state, "alat traje", "čekam potvrdu" — sve su
vizuelni tekst BEZ live region.

**Posljedica:** screen reader korisnik ne čuje kad se stanje promijeni. Ne
zna da se agent povezuje, da alat traje duže, da je stigla potvrda za
odobrenje. Za voice sesiju gdje TTS govori odgovore, ovo je manje bolno nego
u tekstualnoj aplikaciji, ali "čekam potvrdu" i "greška u povezivanju" su
kritični trenuci koji se moraju čuti.

**Popravka (srednje):** jedna dijeljena `<div role="status" aria-live="polite">`
komponenta u koju se preusmjeravaju statusni stringovi (već postoje kao
`onStatus`/`voiceStateLabel` — pi-jev voice reliability rad ih je već
standardizovao). `waiting_confirmation` i `error` treba `aria-live="assertive"`.

### K-3 (VISOKO) — ConfirmationDialog nema focus management
**Dokaz:** `ConfirmationDialog.tsx` ima `role="dialog"`/`aria-modal` ali:
- ne poziva `focus()` na sebe pri otvaranju (grep `.focus()` → nema u fajlu),
- nema focus trap (Tab može izaći iz dijaloga u pozadinu),
- nema Escape-to-cancel handler,
- 250ms "armed" delay onemogući Odobri dugme na početku (dobro za
  bezbjednost) ALI screen reader ne dobije objavu zašto je dugme onemogućeno.

**Posljedica:** za NAJKRITIČNIJI bezbjednosni tok (odobravanje high-risk
akcije, uključujući email_prepare_draft), slijepa osoba možda ni ne SAZNA da
se dijalog pojavio (fokus ostaje gdje je bio, nema live objave). Sigurnosni
review email alata (`EMAIL_COMPOSE_TOOL_SECURITY_REVIEW`, sekcija 7) je ovo
već predvidio kao zahtjev — ovdje je potvrđeno da još nije implementirano.

**Popravka (srednje):** focus na dijalog pri otvaranju + focus trap + Escape =
odbaci + live objava sadržaja. Ovo je izolovana izmjena jedne komponente.

### K-4 (VISOKO) — Drawer paneli nisu dijalozi za screen reader
**Dokaz:** `Drawer.tsx:29` — `<aside>` bez `role="dialog"`, bez `aria-modal`,
bez `aria-labelledby` na naslov, bez focus trap, bez Escape-to-close (samo
click-outside preko `pixel-drawer-backdrop` div-onClick, koji nema tastaturni
ekvivalent). Drawer omotava Activity, Plans, Memory, Screenshots, Settings —
5 glavnih ekrana.

**Popravka (nisko-srednje): ** dodati dialog semantiku + Escape + focus. Jedna
komponenta, koristi je 5 ekrana odjednom.

### K-5 (SREDNJE) — Icon-only dugmad se oslanjaju na `title`, ne `aria-label`
**Dokaz:** `TopBar.tsx:83-93` — `pixel-icon-button` (voice toggle, plans) i
`MiniComputerWindow` restore dugme koriste `title` bez `aria-label`. `title`
JESTE fallback accessible name, ali nepouzdan kroz screen reader-e i ne
prikazuje se na fokus tastaturom (samo na hover mišem). Ostala icon dugmad su
bolja (imaju vidljiv tekst pored ikone).

**Popravka (nisko):** dodati `aria-label` na svako icon-only dugme (mehanički,
i18n stringovi već postoje kao `title` vrijednosti). Također `aria-hidden="true"`
na dekorativne SVG ikone unutar dugmadi sa tekstom.

### K-6 (SREDNJE) — Transkript nije live region
**Dokaz:** `App.tsx:88,267` transkript se drži u state-u i renderuje, ali nije
u grep-u za live region. Kako TTS govori odgovore, transkript je vizuelni
backup — ali za "šta je Ricky upravo rekao" ponavljanje, screen reader ga ne
najavljuje automatski.

**Popravka (nisko):** manje hitno od K-1/K-2 jer je audio primarni kanal.

---

## 3. Nalazi za SLABOVIDNE korisnike (djelimičan vid)

Ovo je **drugi korisnik** sa drugačijim potrebama (vide djelimično, trebaju
kontrast/uvećanje/mirovanje). Ovdje je pixel-art estetika aktivno protiv njih.

### S-1 (VISOKO) — Fiksne px veličine, ne skaliraju se
**Dokaz:** 161 `font-size: ...px`, 0 `rem`/`em`. Kad slabovidni korisnik
poveća OS/browser veličinu teksta, NIŠTA se ne mijenja — sve je hardkodovano.

**Popravka (srednje-visoko):** migracija na `rem` uz `:root` bazu, ili makar
globalni zoom faktor u Settings. Dodirna mnogo CSS fajlova, ali mehanički.

### S-2 (VISOKO) — Reduced-motion pokriva samo 2 od ~10 animiranih površina
**Dokaz:** `prefers-reduced-motion` postoji samo za `.ricky-orb` i
`.companion-orb`. NIJE pokriveno: `13-mini-avatar.css` (`mini-avatar-breathe`,
`mini-avatar-talk` — avatar "diše"/"priča"), pixel state dot pulsiranje,
shell tranzicije, confirmation modal animacije (`modal-in`/`overlay-in`).

**Popravka (nisko):** jedan globalni `@media (prefers-reduced-motion: reduce)`
blok koji gasi sve animacije/tranzicije, ne po-komponenti.

### S-3 (SREDNJE — nepotvrđeno) — Kontrast neon-na-tamnom
**Dokaz (indirektan):** estetika je neon/glow na tamnoj pozadini (npr.
`13-mini-avatar.css` koristi `rgba(169,189,213,...)` sivo-plavi tekst na
tamnoj, glow sjenke). Nisam mjerio stvarne kontrast-omjere — ovo zahtijeva
alat (npr. axe DevTools) protiv renderovanog UI-ja. Sumnja je visoka da dio
sekundarnog teksta pada ispod WCAG AA 4.5:1.

**Popravka:** zahtijeva mjerenje prvo, pa high-contrast temu kao opciju.

### S-4 (SREDNJE) — Nema focus indikatora provjere
**Dokaz:** nisam našao eksplicitne `:focus-visible` stilove u brzom pregledu
(default browser outline se često potisne u custom UI). Tastaturni korisnik
(i slabovidni) mora VIDJETI gdje je fokus. Treba potvrditi da custom dugmad
imaju jasan focus prsten.

---

## 4. Pregled po ekranu

| Ekran / komponenta | Status za slijepe | Glavni jaz |
|---|---|---|
| Glavni razgovor (voice) | ✅ Dobro | K-1 (vizuelni artifacts tihi), K-2 (bez state objava) |
| ConfirmationDialog | ⚠️ Djelimično | K-3 (bez focus/trap/Escape/objave) — bezbjednosno kritično |
| Drawer (Activity/Plans/Memory/Screens/Settings) | ⚠️ Slabo | K-4 (nije dialog, bez focus/Escape) |
| TopBar kontrole | ⚠️ Djelimično | K-5 (icon-only na `title`) |
| IdleScreen / brze komande | ⚠️ Nepotvrđeno | Treba provjera labeliranja |
| Dictation ekran | ✅ Vjerovatno dobro | Voice-native po prirodi; treba live objava ulaska/izlaska |
| ArtifactPanel (slike/grafikoni/thumbnail board) | ❌ Loše za slijepe | K-1 direktno — vizuelni sadržaj bez opisa |
| SettingsPanel | ⚠️ Nepotvrđeno | Ima `<label>` polja (dobro), treba provjera |
| MiniComputerWindow (Computer Mode) | ❌ Fundamentalno teško | Vidi sekciju 6 |

---

## 5. Fazni plan (procjena truda)

### Faza A — "Slijepa osoba može voditi pun razgovor" (MVP, ~1-2 sedmice)
1. **K-1**: accessibility-mode toggle u Settings + prompt grana koja tjera
   govorni opis svakog vizuelnog artifact-a. *(prompt + 1 setting)*
2. **K-2**: jedna dijeljena live-region komponenta za statusne poruke;
   `waiting_confirmation`/`error` kao `assertive`. *(1 komponenta + wiring)*
3. **K-3**: focus management + Escape + live objava u ConfirmationDialog.
   *(1 komponenta, bezbjednosno najvažnije)*

**Kriterij:** slijepa osoba može pitati, dobiti govorni odgovor, čuti šta je
prikazano, i bezbjedno odobriti/odbiti akciju — bez gledanja u ekran.

### Faza B — Navigacija cijele aplikacije screen reader-om (~1 sedmica)
4. **K-4** Drawer dialog semantika + Escape/focus.
5. **K-5** aria-label na svu icon-only dugmad + aria-hidden na dekorativne SVG.
6. **K-6** transkript kao opciona live region.
7. Provjera labeliranja IdleScreen/Settings/ArtifactPanel dugmadi.

### Faza C — Slabovidni vizuelni sloj (~1-2 sedmice)
8. **S-2** globalni reduced-motion blok.
9. **S-1** migracija px→rem ili globalni zoom faktor u Settings.
10. **S-3** izmjeriti kontrast (axe/Lighthouse), dodati high-contrast temu.
11. **S-4** eksplicitni `:focus-visible` prsten svugdje.

### Faza D — Verifikacija (kontinuirano, obavezno prije tvrdnje)
12. Testiranje sa NVDA (besplatan, Windows) kroz sve ekrane.
13. Testiranje sa stvarnim slijepim/slabovidnim korisnikom.
14. Automatski axe-core prolaz u CI.

---

## 6. Šta je fundamentalno teško (ne "još nije urađeno", nego suštinski)

**Computer Mode** (klikanje po koordinatama, čitanje tuđeg ekrana) je
inherentno vizuelan. Slijepa osoba ne može verifikovati šta agent radi na
ekranu druge aplikacije. Ovo NIJE popravljivo ARIA-om — to je drugačiji
threat/UX model. Opcije:
- ostaviti Computer Mode van pristupačnog obima (dokumentovati kao "vizuelna
  funkcija"), ILI
- za slijepe, zamijeniti ga strukturisanim alatima (npr. `email_prepare_draft`
  je već primjer — ne klikće slijepo, nego popunjava poznata polja i opisuje
  ishod govorno; isti obrazac za druge zadatke umjesto koordinatnog klikanja).

Zanimljivo: **email_prepare_draft dizajn je slučajno već accessibility-friendly
obrazac** — deterministički popunjava poznata polja umjesto vizuelnog klikanja,
i vraća govorno-opisiv ishod. Buduće funkcionalnosti koje slijede taj obrazac
(strukturisan tool umjesto računarskog klikanja) biće pristupačne skoro
besplatno; one koje se oslanjaju na Computer Mode neće.

---

## 7. Preporuka za "neku drugu funkcionalnost" (korisnikov nagovještaj)

Ako uvodiš novu funkcionalnost i želiš je odmah držati pristupačnom, tri
pravila iz ovog audita koja koštaju malo ako se rade OD POČETKA (a skupo
retroaktivno):

1. **Svaki vizuelni izlaz ima govorni ekvivalent** — ako alat prikaže nešto,
   njegov `result`/prompt mora biti govorno-opisiv, i prompt mora reći modelu
   da ga opiše u accessibility modu (K-1 obrazac).
2. **Strukturisan tool, ne koordinatno klikanje** — kao email_prepare_draft.
   Deterministička polja se mogu opisati i verifikovati; slijepi klik ne može.
3. **Svaki novi status/dijalog koristi dijeljenu live-region + dialog
   infrastrukturu** iz Faze A — ne izmišljati novi vizuelni-only indikator.

Ako se ta tri pravila poštuju na ulasku, nova funkcionalnost je pristupačna
bez zasebnog "accessibility PR-a" kasnije.
