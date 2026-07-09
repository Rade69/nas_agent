# Agent report — CSS split refactor

**Datum:** 2026-07-09

## Scope

- Razbijen monolitni `src/styles.css` (5231 linija) na 15 tematskih CSS modula u `src/styles/`.
- `src/styles.css` je sad samo import manifest.
- Nije mijenjan dizajn ni selectors API — mehanički refactor.

## Files changed

- `src/styles.css` — postao import manifest (21 linija: komentar + 15 `@import` pravila)
- `src/styles/00-base.css` do `src/styles/14-responsive.css` — novi moduli

## Mapa modula (contiguous regioni po redoslijedu pojavljivanja)

| Fajl | Originalne linije | Dominantna tema |
| --- | --- | --- |
| `00-base.css` | 1–35 | `:root`, `*`, `body`, `button`, `input` |
| `01-window.css` | 37–137 | `.app-shell`, `.window-drag-*`, `.window-close-button`, `.app-shell-mini`, `.mini-companion`, `.mini-restore-button`, `.companion-window` |
| `02-legacy-shell.css` | 138–430 | artifacts-početak (`.artifact-panel`, `.entry p`) + legacy `.face`/`.eye`/`.mouth`/`.bottom-console`/`.prompt-box`/`.simple-button`/`.control-strip` |
| `03-artifacts.css` | 431–1301 | `.transcript`, `.entry`, `.activity-*`, `.image-*`, `.thumbnail-*`, `.mermaid-*`, `@media 900px`, keyframes (blink/eye-look/pupil/progress/image-*/edge-scan) |
| `04-voice.css` | 1302–1455 | `.voice-top-bar`, `.voice-state-*`, `.bottom-voice-*`, `.activity-timeline`, `.entry-voice`, `@keyframes voice-dot-pulse` |
| `05-confirmation.css` | 1457–1651 | FAZA 9 confirmation dialog |
| `06-plans.css` | 1653–1968 | plans panel, plan-card, plan-step |
| `07-companion-orb.css` | 1970–2233 | FAZA 12 companion orb (zasebni mini window) |
| `08-redesign-shell.css` | 2235–2949 | `.confirmation-icon-svg` + app-shell-redesign, sidebar, top-bar, idle, dictation, btn-*, companion-toggle |
| `09-ricky-orb.css` | 2950–3204 | Ricky orb triple-ring animacija (iz commita `db9fc39`) + `prefers-reduced-motion` |
| `10-confirmation-v2.css` | 3205–3356 | confirmation modal restyle, bottom-voice-bar, main-content-panel |
| `11-pixel-shell.css` | 3358–4283 | pixel-app-shell, pixel-window, pixel-top-bar, pixel-main, pixel-idle, pixel-dictation, pixel-drawer, kill-switch |
| `12-pixel-board.css` | 4284–5082 | pixel-board-shell, pixel-global-window-controls, pixel-mockup-board, pixel-section-*, pixel-window-idle/dictation overrides, pixel-confirm-card, pixel-preview, pixel-plan-row |
| `13-mini-avatar.css` | 5084–5203 | mini-computer-window (Computer Mode avatar) + keyframes |
| `14-responsive.css` | 5205–5231 | `@media 1366px`, `html/body/#root` |

## Safety rules followed

- Bez preimenovanja klasa — provjereno: identičan set selektora.
- Bez brisanja legacy CSS-a — `.face`, `.app-shell`, `.entry`, `.simple-button` svi sačuvani.
- Bez dizajn promjena — nijedna deklaracija nije izmijenjena.
- **Import redoslijed čuva postojeći cascade** — moduli su **contiguous regioni** po
  redoslijedu pojavljivanja u originalnom fajlu. Matematički garantovano: efektivni
  redoslijed selektora nakon splita = originalni redoslijed (svaki `@import` ubacuje
  fajl tamo gdje je bio u originalu, bez premještanja selektora naprijed/nazad).

## Zašto contiguous pristup umjesto striktno tematske podjele iz briefa

Brief predlaže 14 tematskih fajlova (00–13) sa specifičnim rasporedom selektora po
temi. Analiza originalnog `styles.css` pokazala je da su blokovi **izmiješani**:

- `.artifact-panel` (138) → legacy `.face` (179) → `.transcript` (432) → artifacts
  se nastavlja (564) — artifacts blok je razdvojen legacy-face i transcript blokovima.
- `.confirmation-icon-svg` (2235) je izoliran između companion-orb i redesign-shell.
- Blok "app-shell-redesign / sidebar / top-bar / idle / dictation" (2235–3356, ~1120
  linija) **nije predviđen** briefovom strukturom 00–13 (vjerovatno je nastao nakon
  pisanja briefa).
- Blok "companion orb" (1970–2233) takođe nije u briefovoj listi 14 fajlova.

Tematska podjela koja bi razdvojila npr. artifacts u dva dijela (138–178 i 564–1148)
bi razbila cascade redoslijed: artifacts-2 (564) dolazi poslije transcripta (432) u
originalu, ali ako se artifacts-1 i artifacts-2 spoje u jedan fajl importovan poslije
transcript fajla, redoslijed bi postao art1, art2, face, transcript — što mijenja
redoslijed i može slomiti override-e.

Zato je odabran **contiguous pristup**: svaki fajl je jedan nepromijenjen region
linija iz originala, redoslijed importa prati redoslijed regiona. Cascade je
matematički identičan originalu. Nazivi fajlova prate dominantnu temu regiona.

Odstupanja od briefa (data ovdje transparentno):
- Dodata 3 fajla ko brief nije predvidio: `07-companion-orb`, `08-redesign-shell`,
  `10-confirmation-v2` (briefova struktura 00–13 nije pokrivala te blokove koji su
  nastali kasnijim fazama).
- Transcript (432–560) završio u `03-artifacts` (contiguous sa artifacts-nastavkom),
  ne u posebnom `04-transcript-activity` — pošto je između njih artifacts blok, razdvajanje
  bi slomilo redoslijed.
- `04-voice` sadrži i `.activity-timeline`/`.entry-voice` (activity tema) jer su
  contiguous sa voice blokom.
- Numeracija fajlova je 00–14 (15 fajlova), ne 00–13 (14) iz briefa.

Orb animacija (commit `db9fc39`) je premještena u `09-ricky-orb.css` kao i sav ostali
CSS — bez izmjena deklaracija, po korisnikovom uputstvu.

## Verification

- `npm run typecheck` (`tsc --noEmit`) — čisto. ✓
- `npm run build` (`vite build`) — uspješno (✓ built in 1.52s). ✓
- Brace balance provjera: svih 15 fajlova ima balansiran broj `{` i `}`. ✓
- Suma linija: 5223 (moduli) + 8 preskočenih praznih linija između regiona = 5231 =
  originalni `styles.css`. Sav sadržaj sačuvan. ✓
- Nijedan modul nije prazan (nonblank > 0 za sve). ✓

Napomena o bug-u uhvaćenom tokom rada: prvi pokušaj granice `431–1300` za
`03-artifacts.css` je odrezao zadnju `}` `@keyframes edge-scan-up` (original linija
1301) → postcss-import "Unclosed block" greška. Popravljeno granicom `431–1301`.

## Known risks

- Moguće sitne cascade razlike: iako je redoslijed matematički identičan, Vite/PostCSS
  `@import` inlining bi teoretski mogao minimalno promijeniti ponašanje source map-ova
  ili komentara `/*# sourceMappingURL */`. Nije zapažen vizuelni efekat u buildu.
- **Potrebna ručna vizuelna provjera GUI-ja** (agent nema screenshot pristup):
  glavni 6-section GUI, SPREMAN sekcija, DIKTIRANJE, confirmation modal/preview,
  activity/plans drawer, mini avatar Computer Mode, window kontrole.
- Imena fajlova ne prate 1:1 briefovu listu 00–13 (vidi obrazloženje iznad) — ako
  korisnik insistira na striktnoj briefovoj nomenklaturi, može se uraditi drugi prolaz
  sa preimenovanjem, ali to ne mijenja cascade.

## Potreban follow-up

- Ručna vizuelna provjera svih ekrana nakon `npm run dev`.
- Ako se želi čistija tematska podjela (npr. transcript odvojen od artifacts), to bi
  zahtijevalo pažljivu analizu override-a — preporuka: zasebni mali PR sa vizuelnim
  testom, ne u ovom mehaničkom refactoru.

## Potrebna korisnička potvrda

Ručna provjera da `npm run dev` prikazuje GUI identično kao prije refactora —
agent nije pokretao Electron GUI u ovoj sesiji.
