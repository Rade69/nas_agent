# Agent Report — Pokušaj usklađivanja GUI-ja sa mokapom (idle + drawer arhitektura)

**Datum:** 2026-07-07
**Agent:** Claude Code (claude-sonnet / opus u dijelu sesije)
**Status:** NEUSPJEŠNO u glavnom cilju (vizuelno poklapanje sa mokapom). Radne izmjene su tačne pojedinačno, ali rezultat NE konvergira ka mokapu. Korisnik je zatražio zaustavljanje i predaju sljedećem agentu.

---

## Scope

Zadatak (backlog, bez broja faze): učiniti da **stvarni pokrenuti GUI vizuelno odgovara** odobrenom mokapu, koji je korisnik razbio na 6 slika:

- `assets/GUI-SETS/GUI-SET-1.png` — **IDLE / SPREMAN** (glavni ekran, korisnik ga najviše provjerava)
- `assets/GUI-SETS/GUI-SET-2.png` — **DICTATION MODE**
- `assets/GUI-SETS/GUI-SET-3.png` — **CONFIRMATION MODAL**
- `assets/GUI-SETS/GUI-SET-4.png` — **ACTIVITY DRAWER**
- `assets/GUI-SETS/GUI-SET-5.png` — **PLANS DRAWER**
- `assets/GUI-SETS/GUI-SET-6.png` — legenda: status indikatori, ključni principi, responsive pravila, orb logo

**Ove 4 slike su autoritativna referenca.** Sve ostalo (stariji kombinovani mokap, `docs/RICKY_PRECISE_GUI_REBUILD_PROMPT.md`) je podređeno njima.

---

## GitNexus impact

`gitnexus_detect_changes` (unstaged): **risk_level = critical**, 64 changed symbols, 16 affected processes.

**VAŽNO — critical NIJE od GUI izmjena.** Critical dolazi od co-mingled izmjena u sigurnosnom putu (`handleRealtimeCreateToken`, `handleToolsExecute`, `executeFunctionCalls` u `realtime.ts`) — to je **pi-jev confirmation-bridge rad koji je već verifikovan** u `agent_reports/2026-07-06_confirmation-bridge-ui-redesign-verification.md`. Moje GUI izmjene diraju isključivo render funkcije (`renderIdleScreen`, `renderMainContent`, `PlansPanel`, `ActivityTimeline`, `ConfirmationDialog`, `voiceStateLabel`) — nizak stvarni rizik, čisto prezentacioni sloj.

---

## Šta je urađeno (moje GUI izmjene ove sesije)

### Strukturne (ne kozmetičke)
1. **Drawer arhitektura** (`src/App.tsx`): razdvojen `screen` (`home`/`dictation` — stalni state-machine sadržaj) od `activeDrawer` (`activity`/`plans`/`memory`/`screens`/`settings` — overlay panel koji klizne preko ekrana). Ranije je `activeTab` potpuno ZAMJENJIVAO glavni sadržaj (tab-router), što je bilo suprotno mokapovom principu "Jedan sadržaj po ekranu (state machine)" + "Paneli dostupni po potrebi (drawers)". Dodat generički `.drawer-backdrop`/`.drawer-panel`/`.drawer-header` wrapper u CSS.
2. **Full-width top bar** (`src/styles.css`): `.top-bar` → `grid-column: 1 / 3` (preko cijele širine), `.sidebar` → `grid-row: 2 / 4` (ispod trake). Uklonjen duplirani brend iz `Sidebar.tsx` (bio i u sidebaru i u top baru; mokap ga ima samo jednom u top baru).

### Sadržajne / lokalizacija
3. Orb: `RickyOrb.tsx` koristi `ricky-orb-main.png` (nazubljena aura) umjesto `ricky-orb-idle.png` (gladak krug) za idle/muted.
4. `voiceStateLabel()` preveden na bosanski.
5. `ConfirmationDialog.tsx`: prevedeno, `PAYLOAD_FIELD_LABELS` (Prima/Predmet/Sadržaj), dinamički confirm label, uklonjen leaked engleski dev-note.
6. `PlansPanel.tsx`: tabovi (Aktivni/Predloženi/Završeni), status badge-ovi, prevedeno, "Novi plan" dugme, uklonjen dupli header (sad ga daje drawer wrapper).
7. `ActivityTimeline.tsx`: shared `categoryForActivity` ikone, "Prikaži cijelu historiju" dugme.
8. Idle ekran: rečenični naslovi kartica, "Prikaži sve" link, dvolinijske stavke aktivnosti (naslov+podnaslov+vrijeme), 4 brze komande sa tačnim mokap tekstovima i uniformnim ▷ (chevron), veći orb (300px), omekšan prsten, veće mic dugme (64px), "Computer mode: ISKLJUČEN", "Upiši umjesto govora...".

### Bug fix-evi (usput nađeni, stvarni)
- `pollEvents()` replay-guard (stale event replay na svakom svježem startu).
- `recentActivity` filter je provjeravao `.detail` umjesto `.title`.
- `refreshPlans()` se nikad nije pozivao (Planovi uvijek prazni).
- Uklonjen mrtav state (`showTypeInput`, `showPlans`).

---

## Zašto je urađeno

Korisnik je prenio vlasništvo nad implementacijom na mene nakon što ChatGPT-jev prompt za redizajn nije dao rezultat. Cilj: zatvoriti jaz između pokrenutog GUI-ja i 6 mokap slika.

---

## Kako je urađeno

Iterativno: čitanje mokap slike → CSS/TSX izmjena → `npm run typecheck` → korisnik šalje screenshot → poređenje. HMR (Vite hot-reload) je aktivan tokom `npm run dev`, pa izmjene idu uživo bez restarta.

---

## Šta NIJE dirano
- Python backend, IPC, realtime glasovni pipeline (`realtime.ts` core logika — samo pi-jeve već-verifikovane izmjene su tu).
- Legacy PowerShell toolovi.
- Nijedan mokap/asset fajl (samo čitani).

---

## Verifikacija
- `npm run typecheck` — čist (više puta).
- `npm run build` — čist.
- **KLJUČNO DOKAZANO:** pipeline isporuke koda RADI. Ubačen je privremeni `outline: 6px solid #ff00ff` na `.ricky-orb-ring`; korisnik je potvrdio da se magenta prsten ODMAH pojavio na ekranu. Time je **definitivno oborena** hipoteza da "nešto blokira kod / caching / zamrznuti prozor". Svaka izmjena stiže na ekran. (Test-okvir je uklonjen.)
- Očišćeni: Electron disk cache (`%APPDATA%\rileyjarvis\Cache` itd.), `node_modules/.vite`. Ranije u sesiji: ubijeni stale procesi, preimenovana pogrešna desktop prečica (`Ricky.lnk` → `RileyJarvis-Windows`).

---

## Rizici / ograničenja — ZAŠTO OVAJ PRISTUP NIJE USPIO (za sljedećeg agenta)

**Glavni nalaz:** Radio sam desetak tačnih pojedinačnih CSS/TSX izmjena, ali rezultat i dalje **strukturno i osjećajno** odudara od mokapa. Sitni inkrementalni CSS koraci NE zatvaraju jaz.

Ono što mokap ima a moj rezultat nema:
- **Cjelokupni "polished / lebdeća kartica" osjećaj** — dubina, sjajevi (glow), zaobljena kontejnerska kartica na tamnom gradijentu, precizni razmaci i tipografska hijerarhija.
- **Bogata aura orba** koja dominira centrom (mokap orb + aura zauzima veći, "hero" prostor sa vidljivim slojevima).
- Fina refinacija: sjene kartica, unutrašnji glow, konzistentni radiusi, kontrast naslova.

Moj pristup (gađanje pojedinačnih property-ja) daje "funkcionalno tačno ali ploško". Korisnik je s pravom zaključio da to nije konvergencija i zatražio prekid.

---

## Potreban follow-up — PREPORUKA ZA SLJEDEĆEG AGENTA

1. **NE nastavljati inkrementalne CSS tweakove na postojećem idle ekranu.** To je već iscrpljeno i ne konvergira.
2. **Preporučeni pristup:** rebuild ekrana IZ NULE direktno prema `assets/GUI-SETS/GUI-SET-1.png` (pa 2–5), tretirajući sliku kao pixel-referencu — po mogućnosti alatom/agentom specijalizovanim za "slika → kod" ili frontend developerom sa dizajnerskim okom. Postaviti mokap i live prozor jedan pored drugog i gađati vizuelnu jednakost, ne property-po-property.
3. **Iskoristiti dokazane činjenice** (da se ne gubi vrijeme):
   - HMR isporuka RADI (magenta test dokaz). Nema caching problema.
   - `ricky-orb-main.png` je "hero" orb sa aurom; `ricky-orb-idle.png` je gladak (za male kontekste).
   - Ispravno pokretanje: `Ricky (Nas-agent).lnk` ILI `npm run dev` u repo folderu. NE `Ricky.lnk` (preimenovana, pokazivala na zamrznuti `RileyJarvis-Windows`).
   - Backend/health/glasovni pipeline su OK — problem je čisto prezentacioni.
4. **Struktura koju treba potvrditi/dovršiti** (djelimično urađeno): full-width top bar + sidebar ispod; drawer overlay za Activity/Plans; kontejnerska "kartica" cijele aplikacije sa radiusom i glow-om (NIJE urađeno — vjerovatno najveći preostali "osjećaj" jaz).
5. Dictation Mode (#2), Confirmation Modal (#3) fina do04rada, Companion floating orb — ostaju uglavnom neurađeni prema mokapu.

---

## Potrebna korisnička potvrda
- Korisnik je već odlučio: **stani**. Ovaj commit + report su predaja štafete.
- Korisnik bira dalje: (a) ostaviti kako jeste, (b) `git revert` na stanje prije GUI izmjena, ili (c) angažovati drugi pristup/agenta za "slika → kod" rebuild.
