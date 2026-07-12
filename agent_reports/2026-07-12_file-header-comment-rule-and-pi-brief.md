# Agent report — pravilo o file header komentarima + brief za pi

**Datum:** 2026-07-12
**Scope:** `CLAUDE.md` (novo pravilo), `docs/PI_TASK_FILE_HEADER_COMMENTS_BRIEF.md` (novo).

**Povod:** Korisnik je pitao da li je negdje formalno uspostavljeno pravilo da
svaki fajl na vrhu ima kratak docstring/komentar (šta fajl radi, koji problem
rješava) — da bi se smanjilo nepotrebno čitanje cijelih fajlova u potrazi za
konkretnim podatkom.

## Šta je urađeno

- **Provjera prije odgovora:** pretražio `CLAUDE.md`/`AGENTS.md`/`docs/` — pravilo
  nikad nije formalno postojalo (jedino ad-hoc spominjanje bilo je za 3
  specifična fajla u `docs/refactor_plan.md`, ne opšte pravilo). Izmjerio
  stvarnu pokrivenost u kodu: Python backend 27/85, frontend 12/32, Electron
  17/31 fajlova je imalo header — organska posljedica rada na tim fajlovima
  ove sesije, ne primjena sistematskog pravila.
- Dodao novo pravilo u `CLAUDE.md` "Rad po fazama" sekciju — svaki kreiran ili
  značajno mijenjan kod fajl (`.py`/`.ts`/`.tsx`/`.cjs`) ubuduće mora imati
  kratak header (2-5 linija) na vrhu.
- Napisao `docs/PI_TASK_FILE_HEADER_COMMENTS_BRIEF.md` — jednokratni retroaktivni
  zadatak za pi da dopuni preostalih 91 fajl (53 Python + 20 frontend + 14
  Electron, prazni `__init__.py` fajlovi isključeni) po istom obrascu, sa
  format specifikacijom po tipu fajla, primjerima dobrog/lošeg header-a, i
  acceptance kriterijumima (typecheck/build/node --check/pytest čisti, git
  diff isključivo aditivan).

## Zašto ovako

- Retroaktivno popunjavanje 91 fajla je mehanički, nisko-rizičan ali dosadan
  posao — dobar kandidat za pi po ustaljenoj podjeli rada (vidi
  `agent_reports/2026-07-05_codex-claude-split.md`). Korisnik je eksplicitno
  to i predložio.
- Pravilo samo (u CLAUDE.md) je dovoljno jeftino da se doda odmah, umjesto da
  čeka da pi završi retroaktivni prolaz — sprječava da se u međuvremenu doda
  novi fajl bez header-a.

## Šta nije dirano

- Nijedan kod fajl — ovaj prolaz je samo pravilo + brief dokument, sama
  retroaktivna izmjena je delegirana pi-ju.
- `AGENTS.md` je ostao netaknut iako sadrži isto pravilo implicitno preko
  reference na `CLAUDE.md` — nije provjeravano da li i taj fajl treba
  duplirati pravilo (vjerovatno ne, `AGENTS.md` referencira `CLAUDE.md` kao
  izvor pravila rada).

## Verifikacija

- `mcp__gitnexus__detect_changes(scope: "all")` — risk "low", nema affected
  processes (dokumentacija, nema koda).
- Nema build/test uticaja (markdown-only izmjena).

## Rizici/ograničenja

Nijedan — čisto dokumentaciona izmjena. Stvarni rizik (ako ga ima) je u
pi-jevom retroaktivnom izvršenju, koje Claude verifikuje prije commita po
brief-ovim acceptance kriterijumima.

## Potreban follow-up

Čeka se pi da izvrši `docs/PI_TASK_FILE_HEADER_COMMENTS_BRIEF.md`.

## Potrebna korisnička potvrda

Nije potrebna za ovaj korak (pravilo + brief). Retroaktivni rad će biti
pregledan i komitovan tek nakon što pi javi da je gotov.
