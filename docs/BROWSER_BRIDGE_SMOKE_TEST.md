# Browser Bridge — Smoke Test Checklist (C3)

Ručni E2E testovi za sve podržane Chromium browsere. Svaki browser mora proći
sve scenarije prije nego što se označi kao "verifikovan".

## Preduslovi

1. Ricky backend pokrenut (`python_backend` ili `npm run dev`)
2. Ekstenzija učitana u browser (`Load unpacked` iz `browser_extension/` foldera)
3. Browser ima najmanje 6 otvorenih tabova sa poznatim naslovima
4. Settings → Browseri i kartice → status prikazuje browser

## Tier 1 — Brave, Chrome, Edge

### Brave

- [ ] Discovery: `GET /browser-bridge/browsers` prikazuje Brave kao `installed: true`
- [ ] Pairing: Settings → Poveži → kod se prikazuje → unijet u ekstenziju → status "Povezano"
- [ ] List: Agent tačno kaže koliko tabova ima (npr. "6 tab(s) in brave: 1. YouTube, 2. GitHub...")
- [ ] Activate 1st tab: "Otvori prvi tab" → fokus na prvi tab
- [ ] Activate 5th tab: "Otvori peti tab" → fokus na peti tab
- [ ] Activate last tab: "Otvori posljednji tab" → fokus na posljednji
- [ ] Stale activate: Zatvori tab ručno između list i activate → agent prijavljuje TAB_SNAPSHOT_STALE
- [ ] Open new tab: "Otvori youtube.com u novom tabu" → novi tab sa youtube.com
- [ ] Close: "Zatvori treći tab" → confirmation dialog → OK → tab zatvoren
- [ ] Close rejected: "Zatvori drugi tab" → confirmation dialog → Cancel → tab ostaje
- [ ] Close stale: Promijeni redoslijed prije approvala → TAB_SNAPSHOT_STALE
- [ ] Disconnect: Ugasi Brave → status "Nije povezano"
- [ ] Reconnect: Pokreni Brave ponovo → automatski auth, status "Povezano"
- [ ] Brejv alias: "Koliko tabova imam u Brejvu?" → radi isto kao Brave

### Chrome

- [ ] Discovery: prikazuje Chrome kao `installed: true`
- [ ] Pairing kroz Settings (isti flow kao Brave)
- [ ] List, Activate, Open, Close (isti scenariji kao Brave)
- [ ] Chrome i Brave istovremeno povezani → naredbe idu pravom browseru
- [ ] Profile routing: "Koliko tabova u Chromeu?" → samo Chrome tabovi
- [ ] "Koliko tabova u Braveu?" → samo Brave tabovi

### Edge

- [ ] Discovery: prikazuje Edge kao `installed: true`
- [ ] Pairing (edge://extensions)
- [ ] List, Activate, Open, Close
- [ ] Tri browsera istovremeno → naredbe precizno rutirane

## Tier 2 — Vivaldi, Opera, Opera GX, Chromium

### Vivaldi

- [ ] Discovery: prikazuje Vivaldi kao `installed: true` (ako je instaliran)
- [ ] Pairing: vivaldi://extensions → Load unpacked → isti flow
- [ ] List, Activate, Open, Close (minimalno: list + activate + open)
- [ ] Ako nije instaliran: preskočiti uz napomenu, ne tvrditi "verifikovano"

### Opera

- [ ] Discovery + pairing (opera://extensions)
- [ ] Minimalno: list + activate
- [ ] Ako nije instaliran: dokumentovati korake, ne tvrditi "verifikovano"

### Opera GX

- [ ] Discovery + pairing (opera://extensions)
- [ ] Minimalno: list + activate
- [ ] Alias "Opera GX" / "opera ge-iks" testiran

### Chromium

- [ ] Discovery + pairing (chrome://extensions, isti API)
- [ ] Minimalno: list + activate
- [ ] Ako nije instaliran: dokumentovati

## Multi-profile testovi

- [ ] Dva Brave profila istovremeno (Default + Work)
- [ ] "Koliko tabova u Braveu?" → BROWSER_PROFILE_AMBIGUOUS (agent treba pitati koji)
- [ ] "Zatvori prvi tab u Brave Default" → tačan profil
- [ ] Snapshot iz profila A ne može se koristiti na profilu B → TAB_PROFILE_MISMATCH

## Edge case testovi

- [ ] Incognito tabovi nisu vidljivi u listi
- [ ] Incognito tab ne može biti aktiviran/zatvoren
- [ ] Pinned tabovi prikazani sa `pinned: true`
- [ ] Tab sa audio prikazan sa `audible: true`
- [ ] Prazan prozor → count=0, poruka "No tabs open"
- [ ] `about:blank` interno mapiran, ne prolazi kroz model
- [ ] file:// URL odbijen u browser_tab_open

## Rezultati

| Browser | Verzija | Discovery | Pairing | List | Activate | Open | Close | Multi-profile | Verifikovan |
|---------|---------|-----------|---------|------|----------|------|-------|---------------|-------------|
| Brave   |         |           |         |      |          |      |       |               |             |
| Chrome  |         |           |         |      |          |      |       |               |             |
| Edge    |         |           |         |      |          |      |       |               |             |
| Vivaldi |         |           |         |      |          |      |       |               |             |
| Opera   |         |           |         |      |          |      |       |               |             |
| Opera GX|         |           |         |      |          |      |       |               |             |
| Chromium|         |           |         |      |          |      |       |               |             |
