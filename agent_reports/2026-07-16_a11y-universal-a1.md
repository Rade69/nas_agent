# Agent Report — A1 revizija (BLOKERI + HIGH popravljeni)

- Datum: 2026-07-16
- Agent: pi
- Faza: A1 — čitljivo, objavljeno stanje (revizija nakon Opus 4.8 pregleda)

## Pregled nalaza i popravke

| # | Nalaz | Popravka |
|---|-------|----------|
| 🔴 B1 | Build slomljen — .sr-only presjekao komentar u 12-pixel-board.css | Vraćen originalni komentar; .sr-only premješten u 00-base.css |
| 🔴 B2 | Pogrešna CSS lokacija + kolizija sa tuđim radom | .sr-only sad u 00-base.css (bazni layer, "first import") — nema kolizije |
| 🟠 H3 | key-remount trik krhk; NVDA netestiran | Perszistentni čvor + useState/useEffect mijenja textContent (standardni pattern). NVDA i dalje zahtijeva ručno testiranje recenzenta. |
| 🟠 H4 | Hardkodirani srpski stringovi | `a11y.announcer.*` ključevi u svih 5 locale fajlova |
| 🟠 H5 | Substring-match po lokalizovanom labelu | Grananje po sirovom `VoiceState` enumu; App.tsx šalje enum, ne label |
| 🟡 M6 | Ref mutacija tokom rendera | `useState` + `useEffect` (čist render, StrictMode-safe) |
| 🟡 M7 | Dedup netestiran | Testovi pokrivaju prioritet, dedup ugovor, locale-nezavisnost |

## Detalji popravki

### B1 + B2 — CSS
- `12-pixel-board.css`: vraćen originalni file-header komentar (presječeni `Sidebar/window chrome)...` je opet unutar komentara)
- `00-base.css`: dodata `.sr-only` kao globalni utility (prvi u kaskadi, "every other stylesheet builds on this")
- `12-pixel-board.css` više nema mojih izmjena → nema kolizije sa tuđim `.pixel-window-idle` radom

### H3 — mehanizam objave
Prije (krhko): `key={politeKey.current}` → remontira čvor → screen reader često NE objavi početni sadržaj svježeg čvora.

Poslije (standardni): perszistentni `<div role="status" aria-live="polite">{politeMessage}</div>` — čvor uvijek u DOM-u, `useState` + `useEffect` mijenja textContent. Screen readeri pouzdano objavljuju IZMJENU teksta u postojećem live-region čvoru.

Dedup: `setPoliteMessage((prev) => prev === message ? prev : message)` — React bails-out na istu vrijednost, DOM se ne mijenja, screen reader šuti. Prirodan dedup.

### H4 + H5 — i18n + enum grananje
- App.tsx šalje `voiceState` (sirovi enum: "error", "waiting_confirmation", "listening"...) umjesto `voiceStateLabel(voiceState)`
- `deriveAnnouncement(voiceState, status, connectionState, t)` graná po enum vrijednosti
- Vlastiti stringovi ("Povezujem se…", "Greška — ponovno povezivanje nije uspjelo") sad koriste `t("a11y.announcer.*")` ključeve
- `voiceStateLabel()` se poziva interno (već koristi i18n) za non-enum poruke
- 5 locale fajlova: sr-Latn (autoritativan), en, de, es, fr (best-effort)

### M6 — render čistoća
Prije: `lastPolite.current = message` direktno u render tijelu (StrictMode double-render rizik).
Poslije: `useEffect` + `setPoliteMessage` — standardan React pattern, StrictMode-safe.

## Provjere (sve tri obavezne iz brifa)

| Provjera | Rezultat |
|----------|---------|
| `npm run build` | ✅ built (BLOKER 1 popravljen) |
| `npx tsc --noEmit` | ✅ čist |
| `npx vitest run` | ✅ 231/231 (uključujući 14 za StatusAnnouncer) |

## NVDA — još uvijek zahtijeva ručno testiranje

Pi ne može pokrenuti NVDA (agent, nema screen reader pristup). Mehanizam je sad standardni/robusni, ali konačnu potvrdu da screen reader stvarno objavljuje mora uraditi recenzent/korisnik po smoke matrix iz brifa (sekcija 7, tačke 1-3, 10).

## Fajlovi
- `src/components/StatusAnnouncer.tsx` — prepisan (enum, i18n, state, useEffect)
- `src/components/StatusAnnouncer.test.tsx` — prepisan (14 testova)
- `src/styles/00-base.css` — +.sr-only
- `src/styles/12-pixel-board.css` — vraćen originalni komentar, .sr-only uklonjen
- `src/App.tsx` — šalje voiceState enum
- `src/i18n/locales/{sr-Latn,en,de,es,fr}.json` — a11y.announcer.* ključevi

## Šta NIJE dirano
- ConfirmationDialog.tsx, realtime.ts, main.cjs, browser-tab — netaknuti
- 12-pixel-board.css nema mojih izmjena više (samo vraćen komentar)
