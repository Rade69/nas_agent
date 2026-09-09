# QM-2 — Companion orb integracija

## Datum

2026-09-09

## Scope

QM-2 iz `docs/QT_MIGRATION_PLAN_2026-07-20.md` — prenijeti `spikes/pyside6_orb_spike.py` u pravu app strukturu (`desktop/ui/`), ožičen na stvarni VoiceState umjesto spike auto-ciklusa.

## GitNexus impact

GitNexus MCP alati nisu dostupni. Ručna analiza: **čisto aditivna promjena**, sve u novom `desktop/ui/` sloju + `desktop/main.py` (`--orb` grana). Ne dira `python_backend/`, `electron/`, `src/`. Jedini dodir sa postojećim sistemom je port konstanti iz `companionWindow.cjs` (MENU_LABELS) i `RickyOrb.tsx`/`voiceState.ts` (mapiranje stanja) — read-only referenca, bez izmjene izvora. Rizik ~nula.

## Šta je urađeno

1. **`desktop/ui/voice_state.py`** — VoiceState enum (9 vrijednosti, identično `voiceState.ts`) + `map_voice_state_to_orb_state()` (port `mapVoiceStateToOrbState` iz `RickyOrb.tsx`: transcribing→listening, interrupted/waiting_confirmation→warning) + `is_valid_voice_state()`.
2. **`desktop/ui/orb.py`** — `RickyOrbWidget` (QWidget) portovan iz spike-a: frameless/transparent/always-on-top, avatar + tri pulsirajuća prstena po stanju (STANJA/7 vizuelnih stanja), drag cijelim licem, minimize/restore (dupli klik + toggle), multi-monitor odbrana (`screenChanged`), position lock (`set_locked`). Uklonjen spike-only kod (auto-ciklus, keyboard test, screenshot režim). `waiting_confirmation` ključ preimenovan u `warning` da odgovara vizuelnom orb stanju.
3. **`desktop/ui/orb_window.py`** — `OrbWindow` menadžer: kontekst meni (desni klik — Open/Toggle voice/Lock position/Minimize/Quit), `MENU_LABELS` (port iz `companionWindow.cjs`, 5 jezika, fail-open sr-Latn), `VoiceStatePoller` (QTimer 1s → `state_changed` signal), `HttpVoiceStateProvider` (poll `GET /voice/state`, fail-close idle).
4. **`desktop/main.py`** — `--orb` grana (`run_orb()`) za dev/vizuelnu provjeru orb-a.
5. **Testovi** — `test_voice_state.py` (5) + `test_orb.py` (10) = 15 novih; `conftest.py` sada postavlja `QT_QPA_PLATFORM=offscreen`.

## Zašto je urađeno

Companion orb je drugi najveći subjektivni rizik migracije (uz glas) — providan always-on-top prozor sa živom animacijom. Spike je dokazao da je izvodljivo; ovo ga pretvara u održavan, testiran app modul. Voice-state polling infrastruktura se pravi sada (QM-2) da QM-3 samo dodijeli stvarni izvor (WebSocket glas) bez ponovnog rada na orb-u.

## Kako je urađeno

- Orb widget je 1:1 port spike-a (STANJA, RING_INSET, `_puls`/`_puls_organski`, redoslijed crtanja avatar→prstenovi sa `CompositionMode_Screen`). Jedina izmjena logike: `waiting_confirmation`→`warning` da se uskladi sa `map_voice_state_to_orb_state`.
- Kontekst meni preko `setContextMenuPolicy(CustomContextMenu)` + `QMenu`; callback-ovi (open main/toggle voice/quit) lazy-bound (isti obrazac kao `companionWindow.cjs`).
- Provider fail-close: `GET /voice/state` ne postoji do QM-3 → 404/mrežna greška/nevalidan state → `idle`.

## Šta nije dirano

- `python_backend/` — netaknut. `/voice/state` endpoint NAMJERNO nije dodat (to je QM-3 glasovni posao).
- `electron/core/companionWindow.cjs`, `src/components/RickyOrb.tsx`, `src/lib/voiceState.ts` — netaknuti (referenca za port, ostaju dok Qt ne zamijeni Electron).
- Tray — nije portovan (QM-4/po potrebi).

## Verifikacija

- `python -m pytest desktop/tests -m "not integration"` → **24 passed** (15 QM-2 + 9 QM-1).
- Orb widget se kreira offscreen (`qapp` fixture): 144×160, VoiceState mapiranje (speaking→speaking, transcribing→listening, garbage→idle), minimize toggle 144↔28.
- Provider fail-close testiran: 200+valid→state, 404→idle, nevalidan→idle, `ConnectError`→idle.
- MENU_LABELS: 5 jezika, fail-open sr-Latn, svi ključevi prisutni.

## Rizici/ograničenja

- **Stvarni VoiceState još nije ožičen** — orb prikazuje idle dok QM-3 ne doda glas i `/voice/state`. Gate "orb prati stvarne promjene stanja" se ne može ispuniti do QM-3 (inherentno u redoslijedu faza).
- **Multi-monitor providnost** — odbrambena popravka (`screenChanged` hide/show) je portovana iz spike-a ali **nije potvrđena uživo** (agent nema drugi monitor). Zahtijeva korisničku runtime potvrdu.
- Animacija na 60fps QTimer bez stvarne audio amplitude — "organski" puls je aproksimacija (dokumentovano u spike-u).

## Potreban follow-up

- QM-3 — Glasovna integracija (WebSocket): dodaje `GET /voice/state` + stvarni glas koji proizvodi VoiceState; orb polling tada dobija stvarne vrijednosti.
- Korisnička vizuelna provjera orb-a (`python -m desktop --orb`) i multi-monitor test.

## Potrebna korisnička potvrda

- Vizuelni izgled orb-a (drag/minimize/kontekst meni) — korisnik treba da pokrene `python -m desktop --orb` i potvrdi.
- Multi-monitor providnost (ako korisnik ima drugi monitor).
