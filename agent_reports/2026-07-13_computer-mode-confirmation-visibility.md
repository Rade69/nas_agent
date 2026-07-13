# Agent report — Computer Mode confirmation nevidljiva u mini prozoru + image_generate dijalog istraga

**Datum:** 2026-07-13
**Scope:** `src/App.tsx`, `src/components/pixel/MiniComputerWindow.tsx`,
`src/styles/13-mini-avatar.css`, `src/i18n/locales/*.json`, `src/lib/realtime.ts`.

**Povod:** Korisnik je prijavio četiri problema u jednoj poruci. Ovaj izvještaj
pokriva dva riješena (confirmation nevidljiva u Computer Mode; "Vrati" gasi
mod prije nego se stigne odobriti) i istragu trećeg (image_generate save
dijalog "ne radi"). Četvrti (glasovni ulazak u Computer Mode isključen S-01
fixom) je namjerno OSTAVLJEN nedirnut — to je bezbjednosni trade-off koji
zahtijeva eksplicitnu korisničku odluku, ne kod prije razgovora.

## GitNexus impact

`detect_changes` prije commita — risk "medium" (dodirnuti `App`,
`MiniComputerWindow`, `RickyRealtimeClient.executeFunctionCalls`, svi u
centralnim tokovima). Ručno provjeren `git diff --stat`: `App.tsx` +4/-0,
`MiniComputerWindow.tsx` +66/-2 (novi confirm-card grana), `realtime.ts` +8/-1
(samo `.catch` log poboljšanje) — čisto aditivno, bez izmjene postojećeg
ponašanja van tražene funkcionalnosti.

## Šta je urađeno

### 1) Confirmation vidljiva i djelotvorna u Computer Mode (mini prozor)

Root cause: `App.tsx`'s `if (isMini) return <MiniComputerWindow .../>` je
rani return PRIJE `<ConfirmationDialog>` (koji se renderuje samo u
ne-mini grani). Sav `pendingConfirmation` state je već ispravno praćen u mini
prozoru (odvojen React proces, ali ista polling `useEffect` logika izvršava
se bezuslovno prije early-return-a) — nedostajao je samo render.

- `MiniComputerWindow.tsx` — nova grana: kad je `pendingConfirmation` na
  `status: "pending"`, prikazuje kompaktnu karticu (naziv akcije + Odobri/Odbij)
  umjesto avatar prikaza. Repliciran isti 250ms "armed" delay pattern kao
  `ConfirmationDialog.tsx` (FAZA S-4/S30 — sprječava trenutni/programski klik).
- `App.tsx` — proslijeđeni novi propovi (`pendingConfirmation`,
  `confirmationBusy`, `onApproveConfirmation`, `onRejectConfirmation`) uz
  ponovnu upotrebu postojećih `handleApproveConfirmation`/`handleRejectConfirmation`.
- Novi i18n key-evi `mini.confirmNeeded`/`mini.reject`/`mini.approve` dodani u
  svih 5 locale fajlova (`sr-Latn`, `en`, `de`, `es`, `fr`).
- CSS (`13-mini-avatar.css`) — `.mini-computer-window-confirm`/`.mini-confirm-card`/
  itd., isti vizuelni jezik (staklo + glow) kao postojeći mini avatar prikaz.

Posljedično rješava i drugi prijavljeni problem: korisnik više NE MORA
kliknuti "Vrati" (što gasi Computer Mode kao nuspojavu) da bi odobrio
potvrdu — odobravanje se sad dešava in-place, bez napuštanja moda.
"Vrati" i dalje gasi mod kad se eksplicitno klikne — to ponašanje nije
mijenjano, samo više nije jedina jedina praktična rezultat cesta do
konfirmacije.

### 2) image_generate save-dijalog — istraga (bez pronađenog koda-bug-a)

Ručno praćen cijeli lanac: `generate.py` (Python handler vraća
`{"path": str, "artifact": {...}}` kad OpenAI vrati `b64_json` — gpt-image
modeli po defaultu VRAĆAJU base64, ne URL, pa je ova grana normalan slučaj) →
`tool_executor.py` (`result = tool.handler(...)`, prosljeđen bez transformacije)
→ `adaptPythonToolResponse()` u `main.cjs` (sprejduje `result` polja uključujući
`path` na top-level, `ok: true`) → `realtime.ts`'s `executeFunctionCalls()`
provjera `result.ok && typeof result.path === "string"` → `window.ricky.saveThumbnailAs`
IPC → `handleThumbnailSaveAs` u `thumbnails.cjs` (allowlist provjera protiv
`dataDir`, pa `dialog.showSaveDialog`). Svaka karika je provjerena polje-po-polje
i **sve se poklapaju** — nema pronađenog loгičkog bug-a u trenutnom kodu.

Provjeren i legacy fallback put (`legacyMedia.cjs`'s `generateImage()`, koristi
se samo ako Python poziv baci grešku) — i on vraća isti `{ok: true, path}`
oblik, pa ni taj put ne bi tiho progutao provjeru.

Najvjerovatniji uzrok: `RickyRealtimeClient` je JS klasa instancirana JEDNOM
po glasovnoj sesiji i držana u `useRef` (`App.tsx:148/248`) — to je obična TS
klasa bez `import.meta.hot.accept()` granice, ne React komponenta. Ako je
korisnik testirao unutar iste dev sesije u kojoj je `e5857d2` commit napravljen
(bez punog restarta aplikacije), postojeća instanca u memoriji je mogla
zadržati STARU verziju metode dok Vite HMR ne izvrši pun page reload za taj
modul. Ovo nije potvrđeno (agent nema GUI pristup za runtime test), samo
najplauzibilnije objašnjenje nakon isključivanja svih koda-nivoa uzroka.

**Popravljeno usput:** `.catch(() => {})` je gutao SVAKU grešku bez traga —
sad loguje (`console.error("[image_generate] auto save-as dialog failed:", error)`)
tako da, ako se problem ponovi nakon punog restarta, greška bude vidljiva u
devtools konzoli umjesto nevidljiva.

## Šta nije dirano

- Glasovni ulazak u Computer Mode (S-01 fix) — namjerno neizmijenjen, čeka
  eksplicitnu korisničku odluku o trade-offu (bezbjednost vs. UX).
- `thumbnailGenerate`/`thumbnailEdit`/board tok — netaknuto (van scope-a).
- `handleThumbnailSaveAs`/`dataDir` allowlist logika — netaknuta, samo
  potrošena kroz bolje logovanje na pozivnoj strani.

## Verifikacija

- `npm run typecheck`, `npm run build` — čisto.
- `node --check` na `main.cjs`, `ipc_handlers/thumbnails.cjs`, `preload.cjs` — čisto.
- `mcp__gitnexus__detect_changes` — risk medium, ručno potvrđen kao čisto
  aditivan diff ograničen na tražene izmjene.
- Runtime NIJE testiran (agent nema Electron GUI pristup) — oba dijela
  zahtijevaju korisnički test.

## Rizici/ograničenja

- Confirmation kartica u mini prozoru je nova UI površina, netestirana u
  stvarnom 236×236 prozoru — moguće da tekst akcije (`action_name`) za duže
  nazive tool-ova ne stane lijepo (CSS ima `overflow: hidden` + `max-height`
  kao zaštitu, ali nije vizuelno provjereno).
- image_generate uzrok ostaje nepotvrđen nagađanje (HMR teorija) — ako se
  ponovi i NAKON punog restarta aplikacije, treba dalja istraga (konkretna
  greška će sad biti vidljiva u konzoli zahvaljujući loggingu).

## Potreban follow-up

1. Korisnički test: ući u Computer Mode, zatražiti akciju koja traži potvrdu
   (npr. `computer_click`), potvrditi da se kartica pojavi u mini prozoru i
   da odobravanje radi bez gašenja moda.
2. Korisnički test: **pun restart aplikacije** (ne samo reload), zatim
   "generiši sliku X" i potvrditi da se "Sačuvaj kao..." dijalog otvori
   automatski. Ako i dalje ne radi, provjeriti devtools konzolu za
   `[image_generate] auto save-as dialog failed:` log.
3. Diskusija sa korisnikom o S-01 trade-off-u (glasovni ulazak u Computer Mode)
   — odvojen razgovor, van scope-a ovog izvještaja.

## Potrebna korisnička potvrda

Oba runtime testa iz "Potreban follow-up" prije nego se ovo smatra potpuno
gotovim.
