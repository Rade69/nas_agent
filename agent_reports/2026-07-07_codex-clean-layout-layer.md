# 2026-07-07 — Codex clean layout layer

## Datum

2026-07-07

## Scope

Prvi čisti GUI layout sloj za Ricky aplikaciju prema `assets/Ricky-agent.png`, `assets/GUI-SETS/GUI-SET-1.png` do `GUI-SET-6.png` i `docs/CODEX_RICKY_PIXEL_CLOSE_GUI_PROMPT.md`.

## GitNexus impact

- Prije izmjene: `impact(App, src/App.tsx)` je vraćen kao LOW risk bez upstream dependents.
- Nakon izmjene: `detect_changes(scope=unstaged)` je vratio HIGH risk jer je `src/App.tsx` centralni renderer i rewrite je dotakao veliki broj render/helper simbola.
- Affected processes uključuju App render, activity polling, plan drawer, text prompt send, voice connect i RickyOrb render.

## Šta je urađeno

- `src/App.tsx` prebačen na čisti `pixel-*` shell:
  - `PixelMockupBoard` kao master struktura sa šest eksplicitnih DOM regiona,
  - `GUI-SET-1` region: idle/home window sa top barom, sidebarom, centralnim orbom i desnim karticama,
  - `GUI-SET-2` region: dictation window sa editor-first layoutom,
  - `GUI-SET-3` region: confirmation modal preview,
  - `GUI-SET-4` region: activity drawer preview,
  - `GUI-SET-5` region: plans drawer preview,
  - `GUI-SET-6` region: footer/principles/status blok,
  - postojeći confirmation modal i artifact panel zadržani su kao stvarni runtime overlay.
- `src/styles.css` dobio novi izolovani CSS sloj `Pixel-close Ricky shell rebuild`.
- `src/styles.css` dobio dodatni master-board sloj koji mapira master mockup na grid: `2+2` gornji red, `2+1+1` srednji red, footer preko pune širine.
- Nakon vizuelne provjere screenshotom `konfuzno.png`, urađen je tightening pass:
  - smanjen minimalni board/shell footprint,
  - zategnute širine top-row kolona,
  - smanjen sidebar u idle prozoru,
  - smanjeni idle right-card, orb, mic i input elementi da ne bježe iz sekcije,
  - topbar kontrole kompaktirane da se status i Computer mode ne sudaraju,
  - dictation editor/akcije smanjeni da ne preklapaju donji edge,
  - footer/principles i preview drawer-i kompaktirani.
- Nakon vizuelne provjere screenshotom `GUI-NOVI-1.png`, urađen je dodatni fine-tuning pass:
  - globalni app/root overflow podešen na hidden,
  - board prebačen na viewport-bound height/width bez globalnog scrollbara,
  - uklonjen CSS koji je skrivao minimize/maximize/close ikone u preview prozorima,
  - topbar kontrole dodatno smanjene da sve ikone stanu,
  - dictation textarea više ne forsira lokalni scrollbar,
  - Electron allowlisted IPC dopunjen za minimize i toggle maximize,
  - topbar dugmad sada pozivaju `quitApp`, `minimizeApp` i `toggleMaximizeApp`.
- Nakon korisničke prijave da je footer i dalje ostavljao ogroman prazan prostor:
  - `pixel-mockup-board` redovi su prebačeni sa procentualnog zbira na `fr` raspodjelu (`53fr 31fr 16fr`) da board popuni cijelu raspoloživu visinu,
  - dodan je globalni `pixel-global-window-controls` sloj iznad boarda, nezavisan od unutrašnjih preview topbarova,
  - početna Electron veličina prozora povećana je sa `1120x760` na `1440x900`,
  - minimalna veličina glavnog prozora povećana je na `1120x700` da se master mockup ne sabija u neupotrebljiv format.
- Nakon dodatnih izreza `3-4-5.png`, `spreman.png` i `footer-2.png`:
  - footer red je dodatno smanjen sa `16fr` na `10fr`,
  - gornji/srednji red su povećani na `55fr/35fr`,
  - section labeli su smanjeni da ostave više prostora panelima,
  - footer tekst je vertikalno centriran u status bandu,
  - activity/plans redovi su kompaktirani da manje ulaze u donje dugme,
  - idle panel je dobio dodatni donji padding, a mic/input su blago smanjeni da ne budu odsječeni.
- Nakon pregleda `full.png`:
  - uklonjene su minimize/maximize/close kontrole iz unutrašnjih `SPREMAN` i `DICTATION` topbarova,
  - globalni `pixel-global-window-controls` ostaje jedini owner za window close/minimize/maximize,
  - unutrašnji topbarovi sada predstavljaju samo stanje sekcije i brze utility akcije.
- Nakon pregleda `1-3.png`:
  - `SPREMAN` hero layout je prebačen na kompaktniji top-aligned raspored,
  - orb/mic/input u `SPREMAN` sekciji su dodatno smanjeni da input/send ne budu odsječeni,
  - right card spacing u `SPREMAN` sekciji je dodatno zbijen,
  - confirmation preview card je pomjeren ka vrhu i dodatno kompaktiran,
  - confirmation tabela, link i dugmad su smanjeni da donji action row stane u sekciju.
- Sačuvani su postojeći realtime, confirmation, plans, artifact i backend event callback tokovi.

## Zašto je urađeno

Claude report `agent_reports/2026-07-07_gui-mockup-match-attempt.md` pokazuje da incremental CSS tweakovima nije moguće doći blizu mokapa. Nakon korisničke primjedbe dodatno je ispravljeno da DOM prvo mora pratiti šest cjelina iz master mockupa, a ne samo jedan single-app shell.

## Kako je urađeno

- Reuse postojećih React komponenti gdje su već korisne: `RickyOrb`, `Sidebar`, `ActivityTimeline`, `PlansPanel`, `ConfirmationDialog`, `ArtifactPanel`.
- Novi layout je uveden kroz `pixel-*` klase da ne zavisi od starog `app-shell`/`idle-screen` CSS-a.
- Mockup assets iz `assets/brending/icons/*` su korišteni za top bar, voice akcije i UI kontrole.
- Statičke preview komponente su dodate za confirmation/activity/plans/footer sekcije da master mockup ima istu strukturnu podjelu u HTML-u.

## Šta nije dirano

- Backend/Python sigurnosni tokovi.
- Electron IPC i preload layer.
- Confirmation poslovna logika, osim što je render prebačen u novi shell.
- Security hardening backlog.
- Packaging/test infrastruktura.

## Verifikacija

- `npm run typecheck` — prolazi.
- `npm run build` — prolazi nakon master-board prelamanja i tightening pass-a.
- Vite prijavljuje postojeći warning za chunkove veće od 500 kB; nije uveden ovim layout slojem.

## Rizici/ograničenja

- Ovo je strukturalni clean layout pass, ne finalni pixel-perfect pass.
- Nije urađen Playwright/screenshot vizuelni diff.
- Top bar close/minimize/maximize kontrole su povezane na allowlisted Electron IPC.
- I dalje treba ručna vizuelna provjera u stvarnom Electron prozoru jer CSS je podešen prema screenshot feedbacku, ne Playwright pixel diffu.
- Responsive sloj je osnovni i treba ga dotjerati nakon desktop provjere.
- Master-board trenutno favorizuje poklapanje sa odobrenom kompozitnom slikom; ako se kasnije vrati production-only state view, treba zadržati iste komponente ali mijenjati routing/render pravilo.

## Potreban follow-up

- Pokrenuti aplikaciju i uporediti screenshot sa `Ricky-agent.png` plus `GUI-SET-1.png` do `GUI-SET-6.png`.
- Dotjerati spacing, visine redova, veličine orb-a, right cards i drawer širine nakon vizuelne provjere.
- Dodati stvarne Electron window akcije za top bar kontrole ako se potvrdi da custom chrome ostaje.
- Nakon vizuelnog prolaza, odvojeno raditi confirmation modal pixel pass (`GUI-SET-3.png`).

## Potrebna korisnička potvrda

Potrebno je da korisnik pregleda prvi layout pass u aplikaciji i potvrdi da se nastavlja na pixel-perfect korekcije umjesto vraćanja na prethodni UI.
