# Agent report — Integracija Codex dodatka: Voice Input UX, Dictation Mode, No-Notepad Rule

**Datum:** 2026-07-05

## Scope

- Izmjena: `docs/RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md` (nova sekcija G, dopuna "Important Engineering Rules" 19-26, ažurirane reference na click-to-talk u "Redesign step 1" i "Suggested First Agent Task").
- Izmjena: `docs/MIGRATION_PLAN.md` (dopunjen naziv "UI Redesign" backlog reda).

## GitNexus impact

Nije relevantno — samo dokumentacioni fajlovi, bez izmjene koda.

## Šta je urađeno

Codex je dostavio dodatak za `RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md` — tri voice UX moda (Ephemeral Command / Dictation Draft / Confirmation Review), `VoiceSessionState` model, "No Notepad" pravilo, i click-to-talk umjesto hold-to-talk kao primarni UX. Prije integracije provjereno: "No Notepad" pravilo nije novo — već je politika i implementacija iz FAZE 9 (planovi su SQLite zapisi, ne fajlovi). `VoiceSessionState` se dodaje kao ortogonalan sloj postojećem `VoiceState` (`src/lib/voiceState.ts`), ne zamjenjuje ga. Confirmation Review mod se poklapa sa već izgrađenim FAZA 10 permission engine-om (`confirmation_id` vezan za tool_name/payload_hash/expires_at). Dodatak ne uvodi nove brojeve faza — nema sudara numeracije.

Integrisano:

1. **Nova sekcija G** ("Voice Input UX, Dictation Mode and No-Notepad Rule") dodata nakon sekcije F, prije "Suggested React Component Structure" — puni sadržaj dodatka (tri moda, VoiceSessionState, backend/event pravila, Output tab ponašanje po modu, Settings dodatak), uz napomenu da je No-Notepad već FAZA 9 politika i da Confirmation mod već ima backend iz FAZE 10.
2. **"Important Engineering Rules"** — dodana pravila 19-26 direktno u glavnu numerisanu listu (gdje je Codex i tražio), uz napomenu koja pravila su iz originalnog V4 dokumenta a koja iz dodatka.
3. **"Redesign step 1"** (task 3) i **"Suggested First Agent Task"** (istorijski referentni tekst) — ažurirani da referenciraju click-to-start umjesto "Hold to talk", i da pominju VoiceSession/Dictation panel/Confirmation review komponente, po Codex-ovom eksplicitnom zahtjevu za tu zamjenu.
4. **`docs/MIGRATION_PLAN.md`** — naziv "UI Redesign" backlog reda dopunjen da pomene Voice Input UX dodatak, radi lakšeg pronalaska.

## Zašto je urađeno

Isti razlog kao prethodne integracije — korisnik i Codex razvijaju UI plan iterativno, Claude Code radi repo-utemeljenu provjeru konzistentnosti prije nego što se dodatak uvrsti kao trajna specifikacija.

## Kako je urađeno

`Grep`/`Read` za pronalazak tačnih mjesta umetanja (kraj sekcije F, "Important Engineering Rules" lista, "Redesign step 1" task 3, "Suggested First Agent Task" bullet lista). Ciljani `Edit` pozivi, bez pune rekonstrukcije fajla.

## Šta nije dirano

- Nijedan kod (`src/`, `python_backend/`) — čisto dokumentacioni zadatak.
- Ostatak V4 dokumenta (sekcije A-F, Companion Mode specifikacija, IPC boundaries) — sadržajno netaknut.
- `docs/MIGRATION_PLAN.md` FAZA numeracija — nepromijenjena.

## Verifikacija

Ručna provjera da sekcija G ispravno referencira postojeće FAZA 9/10 implementacije (ne izmišlja nove), i da su sve izmjene "Hold to talk" → "click-to-start" reference konzistentne unutar dokumenta.

## Rizici / ograničenja

- I dalje samo specifikacija — implementacija (VoiceSession state, Voice Draft panel, Ephemeral/Confirmation UI) nije urađena niti tražena.
- `BottomVoiceBar.tsx` (FAZA 8) trenutno koristi toggle-dugme, ne doslovan hold-gest — napomenuto u sekciji G da je ova ispravka manja u praksi nego što tekst dodatka sugeriše.

## Potreban follow-up

Kad UI Redesign epic dobije broj faze, implementacija sekcije G treba ići zajedno sa "Redesign step 1" (isti fajlovi se diraju).

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — dokumentacioni zadatak.
