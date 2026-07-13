# Orb / prisutnost — spec (nacrt)

**Datum:** 2026-07-09
**Status:** dizajn nacrt (prije implementacije). Nastalo iz razgovora o tome kako
Riki treba da bude prisutan u različitim situacijama, a da ne smeta.
**Vlasnik:** korisnik (vodi viziju) + Claude (spec + implementacija).

## Vodeći princip

> **Dostupnost je odvojena od vidljivosti.**
> Rikija UVIJEK možeš pozvati (global hotkey), bez obzira da li je orb na ekranu.
> Koliko se Riki VIDI biraš prema situaciji.

Ovo je ključ: ne rješavamo svaki slučaj novim orb-stanjem. "Kako Riki izgleda"
(vidljivost) je nezavisno od "kako ga pozoveš" (dostupnost). Poziv je konstanta
(hotkey/glas); izgled je promjenljiv.

## Matrica načina rada

| # | Situacija | Šta se VIDI | Kako pozoveš Rikija | Kontrole na površini |
|---|---|---|---|---|
| 1 | **Normalni rad** | pun glavni prozor (UI) | direktno u UI | sve (voice bar, drawers, Stop) |
| 2 | **Računarski mod** (agent radi na računaru) | veliki orb (`MiniComputerWindow`) | orb je fokus | **Vrati** + **Stop** |
| 3 | **Minimiziran prozor** (radiš drugo, hoćeš brzi pristup) | mali plutajući orb (`CompanionOrb`) | klik na orb / dupli-klik vrati prozor | **Stop** (dupli-klik = vrati) |
| 4 | **Focus / pisanje** (treba ti cijeli ekran za drugu app) | ništa (samo tray) | **global hotkey** (brzi diktat) | nema na ekranu — hotkey |

Napomena uz #3 i #4: mali orb (#3) i sakriveno (#4) su dva različita nivoa
"nenametljivosti" — orb je tu ali malen, vs. orba nema uopšte. Korisnik bira.

## Global hotkey mapa

| Hotkey | Radnja | Status |
|---|---|---|
| `Ctrl+Alt+K` | Stop / kill-switch (zaustavi sve) | ✅ postoji (`registerKillSwitch`) |
| `Ctrl+Alt+Space` (prijedlog) | Brzi diktat — push-to-talk: drži, izgovori misao, pusti → Riki zapiše/izvrši | ⬜ ne postoji |
| toggle companion | ručno prikaži/sakrij mali orb | ✅ postoji (dugme u glavnom prozoru) |

Brzi diktat (#4 poziv): dok pišeš u drugoj aplikaciji, misao ti padne → držiš
hotkey, izgovoriš, pustiš. Pojavi se sićušan indikator "slušam" na sekundu, uhvati
tekst, nestane. Ne prekidaš se iz svog dokumenta; Riki hvata misao sa strane kao
zahtjev/notu (NE tipka u tvoj trenutni dokument — to je agentski capture, ne Win+H).

## Trenutno stanje vs. željeno (gap analiza)

| Ponašanje | Trenutno | Željeno | Radnja |
|---|---|---|---|
| Veliki orb ima Vrati + Stop (računarski mod) | ✅ (Stop nekomitovan, čeka smoke) | isto | commitovati poslije smoke |
| Mali orb ima Stop | ✅ (nekomitovan) | isto | commitovati poslije smoke |
| Mali orb "vrati prozor" | ✅ dupli-klik → `companionOpenMain` | isto (bez dugmeta — ne nakrcavati) | ništa |
| Mali orb se auto-pojavi kad minimiziraš prozor | ✅ **implementirano 2026-07-13** — `mainWindow.on("minimize", showCompanion)` u `electron/main.cjs` | isto | commitovano |
| Mali orb se sakrije kad vratiš prozor | ✅ **implementirano 2026-07-13** (odluka: sakriti — korisnik potvrdio) — `mainWindow.on("restore", hideCompanion)` | isto | commitovano |
| Focus mod: sakrij sve orbove, ostави tray | ⬜ ne postoji kao mod | eksplicitan toggle / stanje | **implementirati** |
| Global brzi-diktat hotkey | ⬜ | push-to-talk global capture | **implementirati** (koristi postojeći dictation + globalShortcut) |

## Postojeći gradivni blokovi (na šta se oslanjamo)

- `electron/core/companionWindow.cjs` — mali orb (show/hide/toggle), always-on-top.
- `src/components/pixel/MiniComputerWindow.tsx` — veliki orb (računarski mod).
- `registerKillSwitch` / `globalShortcut` (main.cjs) — infrastruktura za global hotkey.
- `DictationScreen` + `dictationText` (App.tsx) — dictation UI/logika (fali global ulaz).
- `ensureTray` (companionWindow.cjs) — tray, ostaje "Riki je tu" u focus modu.

Ništa od ovog nije novi sistem — sve četiri situacije nadograđuju postojeće komade.

## Otvorene odluke (za korisnika)

1. **Mali orb na restore prozora:** kad vratiš minimizirani prozor, da li mali orb
   nestane automatski, ili ostaje dok ga sam ne zatvoriš?
2. **Brzi-diktat hotkey:** `Ctrl+Alt+Space` ili neki drugi? (izbjeći sudar s
   Windows/drugim app-ovima — kao što je Ctrl+Alt+K izabran jer F10/F11 Windows guta).
3. **Push-to-talk vs toggle:** brzi diktat — držiš hotkey dok govoriš (push-to-talk),
   ili jedan pritisak start / drugi stop (toggle)?
4. **Focus mod okidač:** ručni toggle (dugme/hotkey), ili automatski kad glavni
   prozor izgubi fokus X sekundi? (auto može iznenaditi — ručno je predvidljivije).

## Prijedlog redoslijeda implementacije

Od najmanjeg/najsigurnijeg ka većem:

1. **Zaokružiti Stop na oba orba** (veliki + mali) — kod je gotov, čeka samo tvoj
   runtime smoke, pa commit. (Situacije #2, #3 kontrole.)
2. **Mali orb auto-show na minimize** — mali, vezuje `companion:show` za minimize
   event glavnog prozora. (Situacija #3.)
3. **Focus mod** — toggle koji sakrije orbove + ostavi tray. (Situacija #4 vidljivost.)
4. **Global brzi-diktat hotkey** — najveći; global capture → dictation. (Situacija #4 poziv.)

Svaki korak je zaseban, testabilan, i može se commitovati nezavisno. Ne radimo sve
odjednom — biramo sljedeći kad prethodni proradi.
