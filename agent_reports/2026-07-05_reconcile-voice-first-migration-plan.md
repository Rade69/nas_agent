# Agent report — Usklađivanje voice-first faza sa MIGRATION_PLAN.md

**Datum:** 2026-07-05

## Scope

- Izmjena: `docs/MIGRATION_PLAN.md` (potpuno prepisan tracker, novi redoslijed faza 0-19, tabela mapiranja stari→novi brojevi, dopunjena pravila rada i definicija uspjeha).
- Izmjena: `docs/ARCHITECTURE_VOICE_FIRST.md`, `docs/RICKY_UI_REDESIGN_AGENT_PROMPT_V2_COMPANION_MODE.md` — dodana napomena "zamijenjeno/superseded" na vrh, sa linkom ka revidiranim verzijama.

## GitNexus impact

Nije relevantno — samo dokumentacioni fajlovi, nema izmjene koda.

## Šta je urađeno

Korisnik je tražio da spojim voice-first dokumente (`ARCHITECTURE_VOICE_FIRST_REVISED.md`, `RICKY_UI_REDESIGN_AGENT_PROMPT_V3_REALTIME_COMPANION.md`) sa postojećim `docs/MIGRATION_PLAN.md` tracker-om i da samostalno odlučim kako, bez dodatnog pitanja ("Poravnaj ti to da se sada ne gnjavim sa Codexom" — korisnik eksplicitno traži da ja donesem odluku).

Problem: revidirani voice-first dokumenti su tražili "spoji u jedan tracker, ne uvodi zasebnu numeraciju", ali su istovremeno predlagali **iste brojeve faza (5-10)** sa potpuno drugim sadržajem od originalnog `RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md` (npr. stara FAZA 6 = "Tool bridge", nova FAZA 6 = "Voice-first UI").

## Odluka i obrazloženje

Napravio sam sljedeći redoslijed (0-19), sa punom tabelom mapiranja stari→novi broj u `docs/MIGRATION_PLAN.md`:

```text
0-5   nepromijenjeno (baseline, docs, agent workflow, main.cjs split, python skeleton, electron starta python)
6     NOVO — Realtime session security (voice-first, iz REVISED dokumenta)
7     SQLite storage (zadržan broj, sadržaj proširen voice-first MVP tabelama)
8     NOVO — Voice-first UI refactor (iz REVISED/V3 dokumenata)
9     NOVO — Confirmations + Plans/Proposals (iz REVISED/V3 dokumenata)
10    Permission system (bio 11, pomjeren ranije — mora postojati prije bilo kog tool execution-a)
11    Tool registry + safe local tools (spojene stare faze 6/8/9/10: tool bridge, memory migracija, event bridge, screenshot/ui_inspect)
12    NOVO — Companion orb voice integracija (iz V3 dokumenta)
13-19 pomjereno sa starih 12-18 (computer-use v1/v2, agent runtime, AI integracije, disable legacy, testovi, packaging) — sadržaj nepromijenjen, samo broj +1
```

Logika odluke:

1. **Ništa iz originalnog plana nije odbačeno** — svaka stara faza ili je zadržala broj, ili je pomjerena, ili je spojena sa preklapajućom voice-first fazom (npr. "SQLite storage" faza 7 sad eksplicitno uključuje voice-first MVP tabele umjesto da budu dvije odvojene faze koje bi obje dirale isti `storage/db.py`).
2. **Voice-first je prioritet odmah nakon osnovne infrastrukture** (FAZA 4-5: Python skeleton + Electron ga starta) — logično, jer ni jedna voice-first faza ne može početi prije nego što Python backend uopšte postoji i Electron zna da ga pokrene.
3. **Permission system (nova FAZA 10) pomjeren ranije** nego u originalnom planu (bio 11, nakon event bridge-a) — sada dolazi prije "Tool registry + safe local tools" (nova FAZA 11) i prije computer-use faza, jer ne smije postojati tool execution bez permission sloja iznad njega. Ovo je stroža verzija originalnog redoslijeda, ne labavija.
4. **Event nazivi i pravila rada dopunjeni** direktno u `MIGRATION_PLAN.md` (dvotačka za IPC, tačka za interne evente, zabrana zamjene `src/lib/realtime.ts` Python audio pipeline-om) — prenešeno iz voice-first dokumenata u glavni tracker kao trajno pravilo, ne samo kao napomena u posebnom fajlu.
5. **Stari `ARCHITECTURE_VOICE_FIRST.md` i `RICKY_UI_REDESIGN_AGENT_PROMPT_V2_COMPANION_MODE.md`** — nisu obrisani (istorijski zapis odluke da se ispravi pristup), samo označeni "zamijenjeno" sa linkom na aktuelnu verziju, da budući čitalac slučajno ne implementira po zastarjeloj verziji.

## Šta nije dirano

- Sadržaj samih voice-first dokumenata (`ARCHITECTURE_VOICE_FIRST_REVISED.md`, `RICKY_UI_REDESIGN_AGENT_PROMPT_V3_REALTIME_COMPANION.md`) — netaknut, samo referenciran.
- Kod (`electron/`, `src/`) — bez izmjena, ovo je čisto planning/dokumentacioni zadatak.
- `docs/RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md` — originalni master fajl netaknut, ostaje kao izvor detaljnih koraka/acceptance kriterijuma za faze koje su samo pomjerene (13-19), uz napomenu u `MIGRATION_PLAN.md` da su brojevi tamo zastarjeli za faze 6+.

## Verifikacija

Ručna provjera da tabela mapiranja pokriva svih 19 originalnih faza (0-18 → 0-19) bez rupa i bez duplog mapiranja. IDE markdownlint upozorenje (MD060, stil tabele) primijećeno i ispravljeno.

## Rizici / ograničenja

- `docs/RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md` sada ima "zastarjele" brojeve faza za sve što je iza FAZE 5 — čitalac mora znati da gleda `MIGRATION_PLAN.md` tabelu mapiranja da nađe tačan broj. Ovo je eksplicitno napomenuto na vrhu `MIGRATION_PLAN.md`, ali je i dalje potencijalni izvor konfuzije ako neko otvori samo originalni master fajl.
- Ovo je moja jednostrana odluka o redoslijedu (korisnik je eksplicitno tražio da ja odlučim) — ako se pokaže da neki drugi redoslijed bolje odgovara stvarnom radu (npr. permission system praktično treba doći kasnije zbog zavisnosti), tracker se lako mijenja jer je u pitanju samo dokumentacija, ne već napisan kod.

## Dopuna (isti dan) — zastarjeli master prompt u originalnom dokumentu

Korisnik je pitao da li i "master prompt" (sekcija 10, "Copy-paste master prompt za Codex ili Claude Code") u `RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md` treba ažurirati zbog istog razloga — stari brojevi faza i nedostatak voice-first pravila. Odgovor: taj prompt je zaista zastario, ali je ažurirana verzija već postojala (napisana u istom koraku kad je `MIGRATION_PLAN.md` prepisan — vidi sekciju "Master prompt za novi agent session" tamo, koja već referencira `docs/MIGRATION_PLAN.md` i sadrži voice-first pravilo). Dodana je samo napomena "zastarjelo — ne koristiti direktno" iznad stare verzije u originalnom fajlu, sa linkom na ažuriranu. Sekcija 11 ("Phase-specific prompt template") nije dirana — generički je template bez ugrađenih brojeva/naziva faza, i dalje ispravno upotrebljiv.

## Potreban follow-up

Sljedeći korak po novom redoslijedu: FAZA 4 (Python backend skeleton) — prvi korak koji stvarno pokreće Python stranu migracije.

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — dokumentacioni zadatak.
