# pi — GUI rebuild sa pravim branding assetima (2026-07-06)

## Izvor

Dva dokumenta u `assets/brending/`:

1. [`RICKY_ASSETS_BRANDING_REMINDER.md`](../assets/brending/RICKY_ASSETS_BRANDING_REMINDER.md) — puna specifikacija asset-a, imenovanja, organizacije.
2. [`RICKY_PRECISE_GUI_REBUILD_PROMPT.md`](../assets/brending/RICKY_PRECISE_GUI_REBUILD_PROMPT.md) — strog "pixel-close rebuild" prompt. Pročitaj ga PRVI, u cjelini, prije nego što diraš kod — eksplicitno kaže da trenutni izgled (stari sidebar, prost R avatar, debug artifact panel) NIJE prihvatljiv i mora se obnoviti.

Korisnik je vizuelno potvrdio da je trenutna realizacija daleko od odobrenog mockup-a (nema mikrofon CTA dugmeta, orb je prost krug bez glow prstena, "Zadnja aktivnost" pokazuje sirovi "Backend ready" log, vidljiv debug artifact panel sa putanjom fajla). Ovaj rebuild treba to riješiti sa pravim, gotovim assetima — ne novom improvizacijom.

## Gdje se stvarno nalaze asseti (bitno — putanja NIJE ona iz dokumenta)

Dokument opisuje strukturu `assets/brending/logo/...`, `assets/brending/orb/...`, `assets/brending/icons/...` — ali stvarni fajlovi trenutno sjede JEDAN NIVO DUBLJE:

```txt
assets/brending/ricky_brending_assets/logo/...
assets/brending/ricky_brending_assets/orb/...
assets/brending/ricky_brending_assets/icons/...
```

Provjereno, stvarno postoji: `logo/` (4 fajla), `orb/` (10 PNG/WEBP fajlova — main/mini/idle/listening/speaking/thinking/warning/error), `icons/` (58 SVG-ova u 8 kategorija). `ricky_brending_assets/README.md` sam kaže da ovaj sadržaj treba kopirati u `assets/brending/` direktno. **Prvi korak: premjesti sadržaj `ricky_brending_assets/{logo,orb,icons}` direktno u `assets/brending/{logo,orb,icons}`**, tako da putanje u oba prompt dokumenta budu tačne. `ricky_brending_assets.zip` i sam `ricky_brending_assets/` folder poslije toga više nisu potrebni u toj lokaciji (ili ih ostavi kao arhivu, ne referenciraj ih iz koda).

## Kako ih stvarno ožičiti u Vite/Electron (projekat trenutno nema `public/` folder)

Provjereno: `vite.config.ts` nema `publicDir` override i ne postoji `public/` folder u projektu — svi ikoni do sada dolaze iz `lucide-react` biblioteke (React komponente), nijedan custom image asset još nije uvezen.

**Preporučen pristup — ES import, ne `public/` folder:**

```tsx
import rickyOrbMain from "../../assets/brending/orb/ricky-orb-main.png";
// <img src={rickyOrbMain} ... />
```

Razlog: `electron-builder.yml` (FAZA 19) trenutno pakuje samo `dist/**/*` (Vite build output). Ako se slike uvezu preko ES `import` u komponentama, Vite ih automatski bundluje u `dist/assets/` i electron-builder ih pokupi bez ikakve dodatne konfiguracije. Ako se umjesto toga napravi `public/brending/...` folder, treba i `electron-builder.yml` dopuniti da to uključi u paket — nepotreban dodatni posao. Koristi import pristup.

**Za SVG ikonice:** brending dokument eksplicitno traži da SVG-ovi koriste `currentColor` da CSS kontroliše boju (provjereno, stvarni SVG fajlovi to imaju). Dvije opcije:

1. **`vite-plugin-svgr`** (novi devDependency) — omogućava `import { ReactComponent as IconHome } from ".../icon-home.svg"`, ponaša se kao lucide-react ikone (boja kroz `color`/`fill="currentColor"` CSS), najbliže postojećem stilu koda. Ako ovo biraš, isti obrazac kao `electron-builder` ranije — reci korisniku prije instalacije novog devDependency-ja.
2. Jednostavnije, bez nove zavisnosti: `<img src={iconUrl} />` — radi odmah, ali gubi per-instance CSS color kontrolu (SVG boja ostaje ono što je u fajlu).

Preporuka: probaj opciju 1 ako je brzo; ako komplikuje build, padni na opciju 2 za prvu rundu i zapiši kao follow-up.

## Kritično upozorenje — ne ponoviti prošlu grešku

Prošli put je "potpuno prepisivanje" (`App.tsx`) iz jednog zadatka pregazilo popravku iz drugog
zadatka koji je bio urađen u međuvremenu (Confirmation Bridge auto-retry provjera je nestala kad je
UI redesign prepisao fajl iz starije verzije). **Prije nego počneš, pročitaj trenutno stanje
`App.tsx`, `src/lib/realtime.ts` — Confirmation Bridge logika (auto-propose kad je
`CONFIRMATION_REQUIRED`, auto-retry nakon odobrenja, provjera `retryResult.ok` prije ispisa uspjeha)
MORA preživjeti ovaj rebuild netaknuta.** Ne pravi svjež fajl od nule — modifikuj postojeći, ili ako
prepisuješ, prenesi tu logiku ručno, provjeri liniju po liniju da je ništa nije izgubljeno.

## Šta koristiti odakle

```txt
Idle/main ekran orb          -> orb/ricky-orb-main.png (ili odgovarajuće stanje: idle/listening/speaking/thinking/warning/error)
Minimized/floating companion -> orb/ricky-orb-mini.png (u CompanionOrb.tsx — vidi napomenu ispod)
Header/mala ikonica          -> logo/ricky-logo-r.svg
Windows app icon             -> logo/ricky-app-icon.ico (electron-builder.yml, taskbar/installer)
Sidebar navigacija           -> icons/navigation/*.svg
Voice/mikrofon/stop           -> icons/voice/*.svg
Confirmation/rizik           -> icons/safety/*.svg (warning ikonica SAMO za rizik/potvrdu, ne za obične statuse)
Status indikatori            -> icons/status/*.svg
Window kontrole (min/max/close) -> icons/window/*.svg
```

## Bonus — Companion prozor

Ranije je utvrđeno (agent_reports/2026-07-06_confirmation-bridge-ui-redesign-verification.md) da
`CompanionOrb.tsx` i dalje koristi staru `CompanionFace` komponentu (ručno iscrtane oči/usta), ne
novi orb dizajn. Ako stigneš, zamijeni je sa `orb/ricky-orb-mini.png` (mala, providnija verzija) —
nije obavezno u ovom krugu, ali je poznat, već zapisan gap i logično se uklapa u ovaj isti posao.

## Acceptance (iz RICKY_PRECISE_GUI_REBUILD_PROMPT.md, skraćeno)

- Veliki brendirani orb (`ricky-orb-main.png`) u centru idle ekrana, ne prost krug sa slovom.
- Nema debug/artifact panela u glavnom layout-u.
- "Zadnja aktivnost" prikazuje smislene korisničke akcije, ne sirove backend log redove.
- Mikrofon CTA stvarno postoji i klikljiv je.
- Sve ikonice iz `assets/brending`, nijedna nova/izmišljena, nijedan emoji.
- Confirmation Bridge logika netaknuta i dalje radi.

## Poslije završetka

Napiši agent_report, ažuriraj `docs/MIGRATION_PLAN.md`, javi da si gotov. Claude Code radi
verifikaciju (kod + realan `npm run dev` boot test) prije commit-a — isti obrazac kao do sada.
