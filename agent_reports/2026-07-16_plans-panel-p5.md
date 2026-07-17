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

## Dopuna — zatvaranje P5 do 100% (Codex, 2026-07-17)

P5 je dopunjen da rokovi/podsjetnici više ne zavise samo od title prefix-a.

### Pravi storage/API field
- Dodan `due_at` na `plans` tabelu i idempotentna SQLite migracija.
- `/plans` create/update/list/get sada prima i vraća `due_at`.
- `PlanService` i `PlanRepository` čuvaju rok kao zasebno polje.
- Stari format `[📅YYYY-MM-DD] Naslov` ostaje samo backward-compatible fallback za ranije kreirane planove.

### Agent reminder workflow
- `create_plan` tool sada prima `due_at` u `YYYY-MM-DD` formatu.
- Realtime tool spec oglašava `due_at` modelu.
- System prompt kaže agentu da za “podsjeti me”, “rok”, “danas”, “sutra” ili konkretan datum upiše `due_at` i korisniku kaže da je podsjetnik/rok vidljiv u plan panelu.

### UI
- PlansPanel koristi `plan.due_at` kao primarni izvor istine.
- Badge prikazuje status i datum (`PREKORAČEN`, `DANAS`, `USKORO`, `BUDUĆI`).
- Sortiranje koristi `due_at`, a title-prefix fallback samo za stare planove.

### Regression provjere
- `python -m pytest -q tests\test_plans.py --basetemp=.tmp-tests\pytest-plans-p5-close` → 9 passed
- `npm run typecheck` → passed
