# CSS Split Refactor Agent Brief

## Cilj

Razbiti veliki `src/styles.css` na manje, tematske CSS fajlove bez promjene trenutnog izgleda i ponasanja aplikacije.

Ovo je mehanicki refactor. Ne raditi dizajn cleanup, ne mijenjati vizuelne vrijednosti, ne preimenovati klase i ne uklanjati CSS koji izgleda mrtav.

Trenutno je `src/styles.css` veoma velik i mjesa:

- global reset/theme
- window chrome
- legacy app shell
- artifacts
- transcript/activity
- voice UI
- confirmation modal
- plans
- Ricky orb
- pixel/mockup GUI
- mini avatar companion
- responsive pravila
- keyframes

Glavni rizik je promjena CSS cascade redoslijeda. Zbog toga import red mora zadrzati isti efektivni redoslijed kao trenutni `src/styles.css`.

## Stroga pravila

1. Ne mijenjati CSS deklaracije u prvom prolazu.
2. Ne preimenovati klase.
3. Ne brisati stare/legacy selektore.
4. Ne premjestati selektor u fajl koji se importuje ranije ako je prethodno bio kasnije u `styles.css`.
5. Ne popravljati dizajn u istom commitu.
6. Ne dirati Python/backend/security fajlove.
7. Ne dirati Electron logic osim ako build jasno zahtijeva import path korekciju, sto ne bi trebalo.
8. Nakon split-a `src/styles.css` treba ostati samo import manifest.

## Predlozena struktura

Kreirati folder:

```txt
src/styles/
```

Kreirati fajlove:

```txt
src/styles/
  00-base.css
  01-window.css
  02-legacy-shell.css
  03-artifacts.css
  04-transcript-activity.css
  05-voice.css
  06-confirmation.css
  07-plans.css
  08-ricky-orb.css
  09-pixel-shell.css
  10-pixel-sections.css
  11-pixel-drawers.css
  12-mini-avatar.css
  13-responsive.css
```

`src/styles.css` treba postati:

```css
@import "./styles/00-base.css";
@import "./styles/01-window.css";
@import "./styles/02-legacy-shell.css";
@import "./styles/03-artifacts.css";
@import "./styles/04-transcript-activity.css";
@import "./styles/05-voice.css";
@import "./styles/06-confirmation.css";
@import "./styles/07-plans.css";
@import "./styles/08-ricky-orb.css";
@import "./styles/09-pixel-shell.css";
@import "./styles/10-pixel-sections.css";
@import "./styles/11-pixel-drawers.css";
@import "./styles/12-mini-avatar.css";
@import "./styles/13-responsive.css";
```

## Kako podijeliti postojece blokove

### `00-base.css`

Prebaciti:

- `:root`
- `*`
- `body`
- osnovni `button`, `input`, `html`, `#root`
- globalne utility deklaracije ako su za cijelu aplikaciju

Ne prebacivati component-specific klase ovdje osim ako su trenutno u samom vrhu i globalne su.

### `01-window.css`

Prebaciti:

- `.window-drag-strip`
- `.window-drag-left-zone`
- `.window-close-button`
- globalne custom window chrome kontrole
- `.pixel-global-window-controls` ako je trenutno u dijelu window/global kontrola

Paziti: ako postoje kasniji override-i za window kontrole u pixel sekcijama, ostaviti override u kasnijem pixel fajlu.

### `02-legacy-shell.css`

Prebaciti legacy shell i stare face/companion strukture:

- `.app-shell`
- `.app-shell-mini`
- `.mini-companion`
- `.companion-window`
- `.face-stage`
- `.face`
- `.eye`
- `.mouth`
- `.mood-row`
- `.bottom-console`
- `.prompt-box`
- `.simple-button`
- `.control-strip`

Ne brisati ih, cak i ako izgledaju zamijenjeni novim GUI-jem.

### `03-artifacts.css`

Prebaciti sve artifact related blokove:

- `.artifact-panel`
- `.artifact-header`
- `.artifact-actions`
- `.artifact-body`
- `.artifact-tab`
- `.empty-artifact`
- `.progress-card`
- `.text-artifact`
- `.code-artifact`
- `.markdown-artifact`
- `.table-wrap`
- `.notes-grid`
- `.note-card`
- `.artifact-image`
- `.image-loading-*`
- `.thumbnail-*`
- `.mermaid-*`

Keyframes koji sluze samo artifact/image loading UI-ju mogu ici u ovaj fajl, ali samo ako su jasno vezani za taj blok.

### `04-transcript-activity.css`

Prebaciti:

- `.transcript`
- `.transcript-list`
- `.entry`
- `.entry-ricky`
- `.entry-user`
- `.entry-tool`
- `.entry-voice`
- `.entry-status`
- `.entry-transcript`
- `.entry-error`
- `.activity-*`
- `.activity-timeline`

Oprez: `.entry` je genericka klasa. Ako se koristi i u artifact dijelu, redoslijed importa mora ostati takav da vizuelno ne promijeni nista.

### `05-voice.css`

Prebaciti:

- `.voice-top-bar`
- `.voice-brand`
- `.voice-top-status`
- `.voice-state-pill`
- `.voice-state-dot`
- `.voice-console`
- `.bottom-voice-status`
- `.voice-control-strip`
- `@keyframes voice-dot-pulse`

### `06-confirmation.css`

Prebaciti:

- `.confirmation-overlay`
- `.confirmation-dialog`
- `.confirmation-header`
- `.confirmation-icon`
- `.confirmation-title-block`
- `.confirmation-close`
- `.confirmation-body`
- `.confirmation-row`
- `.confirmation-label`
- `.confirmation-value`
- `.confirmation-risk-*`
- confirmation action/footer/button klase

Acceptance check: confirmation modal mora ostati dominantan i bez layout promjene.

### `07-plans.css`

Prebaciti:

- plan panel klase
- plan row/card/status klase
- plan drawer klase koje nisu dio pixel preview-a
- step/status/action klase vezane za planove

Ako je neka plans klasa dio pixel mockup preview-a (`.pixel-plan-*`), ostaviti je u pixel fajlovima, ne ovdje.

### `08-ricky-orb.css`

Prebaciti:

- `.ricky-orb`
- `.ricky-orb-*`
- `.ricky-orb-img`
- `.ricky-orb-ring`
- orb state animacije
- orb keyframes
- `prefers-reduced-motion` dio za orb ako postoji

Ovo je priprema za kasniju implementaciju `docs/RICKY_ORB_ANIMATION_PLAN.md`.

Ne uvoditi novu orb animaciju u ovom refactor commitu.

### `09-pixel-shell.css`

Prebaciti osnovni pixel/mockup layout:

- `.pixel-app-shell`
- `.pixel-board-shell`
- `.pixel-mockup-board`
- `.pixel-section-*` osnovne layout klase
- `.pixel-window`
- `.pixel-topbar`
- `.pixel-brand`
- `.pixel-state`
- `.pixel-top-actions`
- `.pixel-icon-button`
- `.pixel-mode-pill`
- `.pixel-top-stop-all`

Ovo je osjetljiv dio. Redoslijed zadrzati sto blize trenutnom.

### `10-pixel-sections.css`

Prebaciti sadrzaj konkretnih mockup sekcija:

- idle/home section
- dictation section
- confirmation preview section
- activity preview section
- plans preview section
- sidebar unutar pixel GUI-ja
- quick commands
- text input / mic zone u pixel GUI-ju

Primjeri klasa:

- `.pixel-window-idle`
- `.pixel-idle`
- `.pixel-hero`
- `.pixel-side-panel`
- `.pixel-window-dictation`
- `.pixel-editor-*`
- `.pixel-confirmation-*`
- `.pixel-preview-*`
- `.pixel-plan-row`
- `.pixel-plan-tabs`

### `11-pixel-drawers.css`

Prebaciti runtime drawer/panel stilove ako postoje odvojeno od static preview-a:

- active drawer shell
- activity drawer runtime
- plans drawer runtime
- memory/screens/settings drawer shell ako postoje

Ako nije jasno da li selector pripada preview-u ili runtime drawer-u, ostaviti ga tamo gdje je po trenutnom redoslijedu sigurnije, ili u `10-pixel-sections.css`.

### `12-mini-avatar.css`

Prebaciti samo Computer Mode avatar companion:

- `.mini-computer-window`
- `.mini-avatar-stage`
- `.mini-avatar-restore`
- `.mini-avatar-status`
- `.mini-computer-window.is-talking`
- `.mini-computer-window.is-idle`
- `@keyframes mini-avatar-breathe`
- `@keyframes mini-avatar-talk`

Ne mijenjati avatar velicinu, poziciju, tekst ili animacije.

### `13-responsive.css`

Prebaciti:

- `@media` blokove koji su na kraju fajla i odnose se na vise komponenti
- globalni responsive override-i

Ako je media query usko vezan za jednu komponentu i trenutno stoji odmah uz taj blok, moze ostati u fajlu te komponente. Ako nije jasno, staviti u `13-responsive.css` i zadrzati redoslijed.

## Preporuceni workflow

### Korak 1: snapshot prije rada

Pokrenuti:

```txt
git status --short
npm run typecheck
npm run build
```

Ako build vec pada prije refactora, zaustaviti se i prijaviti korisniku.

### Korak 2: napraviti mapu linija

Koristiti `Select-String` ili `rg -n` da se oznace pocetci blokova.

Primjer:

```txt
rg -n "^/\\*|^\\.[A-Za-z0-9_-]+|^#[A-Za-z0-9_-]+|^@media|^@keyframes|^:root|^html|^body" src/styles.css
```

Napraviti kratku internu mapu:

```txt
1-36 base
37-128 window/mini legacy
129-...
```

Ne mora u commit, ali treba koristiti tokom rada.

### Korak 3: prvo izdvojiti blokove koji su najsigurniji

Prvi split:

- `12-mini-avatar.css`
- `08-ricky-orb.css`
- `06-confirmation.css`

Pokrenuti:

```txt
npm run typecheck
npm run build
```

### Korak 4: izdvojiti pixel GUI

Drugi split:

- `09-pixel-shell.css`
- `10-pixel-sections.css`
- `11-pixel-drawers.css`

Pokrenuti:

```txt
npm run typecheck
npm run build
```

Ovo je najkriticniji dio za trenutni GUI.

### Korak 5: izdvojiti legacy/artifact/voice/plans

Treci split:

- `02-legacy-shell.css`
- `03-artifacts.css`
- `04-transcript-activity.css`
- `05-voice.css`
- `07-plans.css`

Pokrenuti:

```txt
npm run typecheck
npm run build
```

### Korak 6: finalni responsive/base pass

Izdvojiti:

- `00-base.css`
- `01-window.css`
- `13-responsive.css`

Pokrenuti:

```txt
npm run typecheck
npm run build
```

## Vizuelna provjera

Nakon build-a korisnik ili agent treba provjeriti:

1. Glavni 6-section GUI.
2. `SPREMAN` sekcija.
3. `DIKTIRANJE` sekcija.
4. Confirmation modal/preview.
5. Activity drawer/preview.
6. Plans drawer/preview.
7. Mini avatar Computer Mode:
   - ukljucenje mode-a
   - avatar prikaz
   - status `UKLJUČEN`
   - dugme `Vrati`
8. Window kontrole.
9. Nema scrollbarova u glavnom mockup layoutu.

Ako postoji screenshot workflow, uporediti sa trenutnim stanjem prije refactora. Ako nema, barem rucno otvoriti app i provjeriti glavne ekrane.

## Agent report

Prije commita dodati report:

```txt
agent_reports/YYYY-MM-DD_css-split-refactor.md
```

Minimalni format:

```md
# Agent report — CSS split refactor

## Scope

- Razbijen `src/styles.css` na tematske CSS module.
- Nije mijenjan dizajn ni selectors API.

## Files changed

- `src/styles.css`
- `src/styles/*.css`

## Safety rules followed

- Bez preimenovanja klasa.
- Bez brisanja legacy CSS-a.
- Bez dizajn promjena.
- Import redoslijed cuva postojeći cascade.

## Verification

- `npm run typecheck`
- `npm run build`

## Known risks

- Moguce sitne cascade razlike ako neki selector zavisi od kasnijeg override-a.
- Potrebna rucna vizuelna provjera GUI-ja.
```

## Commit

Commit tek nakon uspjesnog build-a.

Predlozena commit poruka:

```txt
Split global styles into focused CSS modules
```

## Sta ne raditi u ovom zadatku

- Ne implementirati novu Ricky orb animaciju.
- Ne optimizovati `Riki-avatar.png`.
- Ne brisati legacy `.face`, `.app-shell`, `.entry`, `.simple-button` stilove.
- Ne mijenjati React komponente.
- Ne mijenjati Electron mini-window logiku.
- Ne raditi Prettier/format churn nad cijelim repo-om.
- Ne kombinovati ovaj refactor sa UI promjenama.

## Kada stati i pitati korisnika

Stati ako:

- `npm run build` pocne padati nakon mehanickog premjestanja.
- Nije jasno gdje pripada veliki blok koji ima genericke selektore i moze uticati na vise ekrana.
- Vizuelno se promijeni glavni GUI.
- Import redoslijed zahtijeva promjenu koja nije ocigledna.

## Finalna napomena

Ovaj refactor treba da bude dosadan i precizan. Ako nakon commita `git diff` izgleda kao cista distribucija CSS blokova iz jednog fajla u vise fajlova, zadatak je uspio.

Ako diff pokazuje masovne promjene vrijednosti, rename klasa ili dizajn korekcije, zadatak je otisao predaleko.
