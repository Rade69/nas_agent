# Agent report — Integracija RICKY_GUI_LOCALIZATION_PLAN.md (dokumentacioni korak)

**Datum:** 2026-07-05

## Scope

- Novi: `docs/RICKY_GUI_LOCALIZATION_PLAN.md`.
- Izmjena: `docs/MIGRATION_PLAN.md` (novi red u "Backlog / Future Epics" tabeli — bez broja faze).

## GitNexus impact

Nije relevantno — samo dokumentacioni fajlovi, bez izmjene koda.

## Šta je urađeno

Korisnik je dostavio `RICKY_GUI_LOCALIZATION_PLAN.md` (zalijepljen tekst, mojibake enkoding) — prijedlog i18n lokalizacije GUI-ja (sr-Latn/en/de/es/fr) preko `react-i18next`. Prije integracije uradio sam kratku analizu protiv stvarnog stanja koda: `package.json` nema nijednu i18n biblioteku, a `src/components/VoiceTopBar.tsx`, `BottomVoiceBar.tsx` i `src/lib/voiceState.ts` (`voiceStateLabel()`) već imaju hardkodirane engleske stringove — tačno anti-pattern koji plan upozorava da se izbjegne. Korisnik je potvrdio da nastavim integraciju (dokumentacija samo), uz napomenu da ćemo odluku o pristupu implementaciji donijeti kasnije.

Implementirano:

1. **`docs/RICKY_GUI_LOCALIZATION_PLAN.md`** — sačuvan sa ispravnim enkodingom, sadržaj rekonstruisan ručno iz konteksta (mojibake → ispravna dijakritika), bez izmjene značenja. Isti obrazac kao ranije za `SECURITY_HARDENING_PLAN.md`.
2. **`docs/MIGRATION_PLAN.md`** — dodat novi red u "Backlog / Future Epics" tabeli: "GUI Localization (i18n: sr-Latn/en/de/es/fr)", status "Not active MVP work — implementation approach not yet decided", zavisnost eksplicitno navodi FAZA 8 (jer su `VoiceTopBar.tsx`/`BottomVoiceBar.tsx`/`voiceState.ts` već postojeći hardkodirani izvor koji bi Localization PR-1 trebao dirati), link na novi fajl. Nije dodijeljen broj faze — poštuje isto pravilo kao Document Engine epic (samo `MIGRATION_PLAN.md` dodjeljuje brojeve, arhitektonski dokumenti to ne rade sami).

## Zašto je urađeno

Isti razlog kao i za sigurnosni plan — korisnik razvija planove eksterno (ovaj put nije eksplicitno rečeno sa kim, ali format je identičan ChatGPT/Codex-style planovima ranije) i traži da Claude Code uradi repo-utemeljenu analizu prije integracije. Korisnik eksplicitno traži da implementacija sačeka dok ne odluči najbolji pristup (retrofit na postojeću FAZA 8 UI vs. kombinovano sa UI redizajnom o kojem je ranije razgovarano).

## Kako je urađeno

`Write` za novi `RICKY_GUI_LOCALIZATION_PLAN.md` (ručna rekonstrukcija iz mojibake izvora). `Edit` na `MIGRATION_PLAN.md` Backlog tabelu — ovaj edit je dva puta odbijen sa "File has been modified since read" prije nego što je uspio, jer je GLM-5.2 (preko `pi` agenta, FAZA 9) u tom trenutku paralelno i vrlo učestalo upisivao u isti fajl (vjerovatno inkrementalno ažurirajući FAZA 9 status). Riješeno ponovnim čitanjem neposredno prije svakog pokušaja dok se nije poklopilo.

## Šta nije dirano

- Nijedan kod (`src/`, `python_backend/`) — potvrđeno, ovo je čisto dokumentacioni zadatak po korisnikovoj instrukciji ("kad završiš onda ćemo vidjeti šta je najbolje za implementaciju").
- Postojeći hardkodirani stringovi u `VoiceTopBar.tsx`/`BottomVoiceBar.tsx`/`voiceState.ts` — nisu mijenjani, samo referencirani u epic tabeli kao poznat postojeći dug.
- FAZA 8/9 status redovi u `MIGRATION_PLAN.md` — nisu dirani (GLM/pi ih ažurira paralelno za FAZU 9).

## Verifikacija

Ručna provjera da novi red u Backlog tabeli ne dodjeljuje broj faze i da link ka `RICKY_GUI_LOCALIZATION_PLAN.md` radi.

## Rizici / ograničenja

- `docs/MIGRATION_PLAN.md` je sada aktivna tačka konkurentnih izmjena od tri strane (ja, Codex ranije, sada GLM/pi) — potvrđeno u praksi ovim editom (dva odbijena pokušaja zbog concurrent write-a). Buduće izmjene ovog fajla trebaju očekivati re-read/retry ciklus.
- Nema stvarnog rizika po runtime — ovo je samo dokumentacija bez koda.

## Potreban follow-up

- Korisnik treba odlučiti pristup implementaciji (retrofit sada vs. kombinovano sa UI redizajn mockupom) prije nego se dodijeli Localization PR-1 bilo kom agentu.
- Kad se odluči, ovaj epic dobija broj faze isključivo kroz `MIGRATION_PLAN.md`, po istom pravilu kao Document Engine.

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — dokumentacioni zadatak.
