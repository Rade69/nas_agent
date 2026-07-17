# Agent Report — Plans Panel P5 (podsjetnici)

- Datum: 2026-07-16
- Agent: pi
- Faza: P5 — rokovi i sortiranje

## Šta je urađeno

### Rok u inline formi
- Date input polje pored naslova
- Rok se kodira u title: `[📅2026-07-20] Originalni naslov`
- `parseDueDate(title)` — parsira i uklanja prefix iz prikaza
- `dueBadge(date)` — vraća badge na osnovu razlike u danima

### Badge po hitnosti
- 🔴 PREKORAČEN (diffDays < 0) — crveni
- 🟠 DANAS (diffDays = 0) — narandžasti
- 🟡 USKORO (diffDays 1-3) — žuti
- ⚪ BUDUĆI (diffDays > 3) — sivi

### Sortiranje
- Planovi se sortiraju: prekoračeni prvi → po datumu → bez roka zadnji

## Fajlovi
- PlansPanel.tsx — parseDueDate, dueBadge, date input, sort
- 11-pixel-shell.css — plan-due-* klase
- sr-Latn.json, en.json — 6 novih ključeva

## Provjere
- tsc čist, build OK