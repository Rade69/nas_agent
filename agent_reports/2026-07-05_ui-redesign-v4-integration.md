# Agent report — Integracija RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md (ispravka numeracije)

**Datum:** 2026-07-05

## Scope

- Izmjena: `docs/RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md` (fajl je već postojao na disku pri čitanju, sačuvan bez mojibake — samo ispravljena numeracija faza i dodane unakrsne reference).
- Izmjena: `docs/MIGRATION_PLAN.md` (novi red "UI Redesign" u "Backlog / Future Epics" tabeli, bez broja faze).

## GitNexus impact

Nije relevantno — samo dokumentacioni fajlovi, bez izmjene koda.

## Šta je urađeno

Korisnik je dostavio `RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md` — puni UI/Companion redizajn prompt sa "Post-Review Corrections" sekcijom. Prije integracije uređena je analiza: sekcija "Implementation Phases" u dokumentu dodjeljuje **FAZA 6/7/8/10** — provjereno protiv `docs/MIGRATION_PLAN.md` i potvrđen sudar: sve četiri te faze već postoje sa potpuno drugačijim, već završenim sadržajem (FAZA 6 = Realtime session security, FAZA 7 = SQLite storage, FAZA 8 = Voice-first UI refactor, FAZA 10 = Permission/cancellation engine). Ovo je isti obrazac sudara numeracije koji je već rješavan tri puta ranije u ovom projektu (voice-first VF-brojevi, Document Engine FAZA 11-17, sada ovaj dokument) — dokument je očigledno pisan protiv starije verzije plana.

Dodatno je primijećeno: sekcije E ("Stop/Interrupt UI Accuracy") i F ("Realtime Event Volume Rules") suštinski dupliraju `SECURITY_HARDENING_PLAN.md` sekciju 25 (integrisanu ranije istog dana), a sekcija B ("GUI Localization Integration") duplira `RICKY_GUI_LOCALIZATION_PLAN.md` (isto integrisan ranije istog dana) — bez sadržajnog sukoba, samo bez reference na kanonski izvor.

Nakon korisnikove potvrde ("Ispravi ako neće dugo trajati?"), urađeno:

1. **Fajl je već postojao na disku** (nezavisno sačuvan, čist UTF-8, bez mojibake — vjerovatno ranije spašen od strane drugog procesa/agenta prilikom prilaganja) — nije trebalo rekonstruisati enkoding, samo sadržajno ispraviti.
2. **Napomena na vrhu dokumenta** — objašnjava da je "Implementation Phases" sekcija ispravljena i da sekcije E/F/B upućuju na kanonske izvore.
3. **"Implementation Phases" sekcija prepravljena**: `FAZA 6/7/8/10` naslovi zamijenjeni sa `Redesign step 1-4`, uz eksplicitnu napomenu da je ovo redizajn postojećih komponenti (FAZA 8/9 već rade), ne prvi UI rad — svaki "Redesign step" sad referencira tačan postojeći fajl (`VoiceTopBar.tsx`, `BottomVoiceBar.tsx`, `ActivityTimeline.tsx`, postojeći `confirmation_id` tok) umjesto da implicira greenfield "Add X" zadatke. "Redesign step 4" (Companion orb) eksplicitno mapiran na stvarnu FAZU 12.
4. **Unakrsne reference dodane** u sekcijama B (→ `RICKY_GUI_LOCALIZATION_PLAN.md`), D (→ FAZA 10 permission_engine.py, već implementirano backend-side), E i F (→ `SECURITY_HARDENING_PLAN.md` sekcija 25).
5. **"Suggested First Agent Task"** — dodata napomena da ovaj generički greenfield zadatak nije stvarni prvi korak (jer shell već postoji), ostavljen kao istorijski referentni tekst.
6. **`docs/MIGRATION_PLAN.md`** — novi red "UI Redesign" u "Backlog / Future Epics" tabeli, bez broja faze, sa eksplicitnom napomenom "redizajn postojećeg, ne novi rad" i zavisnostima FAZA 8/9/10/12.

## Zašto je urađeno

Isti razlog kao i za prethodna dva plana (security hardening, lokalizacija) — korisnik razvija UI planove eksterno i traži repo-utemeljenu analizu/integraciju prije nego što se bilo šta proslijedi implementacionom agentu. Ključni rizik koji se sprječava: da neki budući agent (Codex/GLM/pi) dobije ovaj dokument i pokuša implementirati "FAZA 6" misleći da je to prvi voice-first UI rad, dok FAZA 6 zapravo znači nešto sasvim drugo i već je gotovo — što bi izazvalo ili zabunu ili duplirani/konfliktni rad nad već postojećim kodom.

## Kako je urađeno

`Grep` za potvrdu sudara brojeva faza protiv `MIGRATION_PLAN.md` prije bilo kakve izmjene. Pokušaj `Write` cijelog rekonstruisanog fajla je odbijen ("File has not been read yet") — `Glob`/`Read` je otkrio da fajl već postoji na disku, čist UTF-8, bez mojibake (za razliku od prethodna dva plana koja su stigla kao zalijepljen tekst sa pokvarenim enkodingom). Umjesto pune rekonstrukcije, urađene su ciljane `Edit` izmjene na stvarnom sadržaju fajla: napomena na vrhu, zamjena cijele "Implementation Phases" sekcije, četiri manje unakrsne reference, napomena kod "Suggested First Agent Task".

## Šta nije dirano

- Nijedan kod (`src/`, `python_backend/`, `electron/`) — čisto dokumentacioni zadatak, korisnik nije tražio implementaciju.
- Ostatak dokumenta (Visual Direction, Target Layout, Component Requirements, Companion Mode specifikacija, IPC/Event Boundaries, React Component Structure) — sadržajno netaknut, samo dodane napomene gdje se poklapa sa drugim kanonskim dokumentima.
- `docs/MIGRATION_PLAN.md` FAZA 0-19 numeracija — nepromijenjena.

## Verifikacija

Ručna provjera (`Grep`) da "Implementation Phases" sekcija više ne sadrži "FAZA 6/7/8/10" naslove, i da su svi dodati cross-referenceovi ispravno pozicionirani.

## Rizici / ograničenja

- Ovo je i dalje samo specifikacija/plan — implementacija (stvarni redizajn `VoiceTopBar.tsx`/`BottomVoiceBar.tsx`/`ActivityTimeline.tsx` u tab-based workspace) nije urađena, niti tražena u ovom koraku.
- Fajl je zatečen već sačuvan na disku prije nego što sam ja pokušao da ga sačuvam — nije poznato ko/šta ga je tamo stavio (moguće drugi agent u paralelnoj sesiji, ili mehanizam prilaganja dokumenta). Sadržaj se poklapao sa onim što je korisnik zalijepio u chat, pa je tretiran kao pouzdan izvor za ciljane izmjene.

## Potreban follow-up

- Kad korisnik odluči da UI Redesign epic uđe u aktivan rad, dodijeliti mu broj faze isključivo u `MIGRATION_PLAN.md` (ne u ovom dokumentu).
- Prije implementacije, agent treba pročitati postojeće `VoiceTopBar.tsx`/`BottomVoiceBar.tsx`/`ActivityTimeline.tsx`/FAZA 9 confirmation UI da redizajnira, ne duplira.

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — dokumentacioni zadatak.
