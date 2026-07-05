# Agent report — Integracija "Realtime Event Flow and Cancellation Safety" (Gemini analiza, ChatGPT review)

**Datum:** 2026-07-05

## Scope

- Izmjena: `docs/SECURITY_HARDENING_PLAN.md` (nova sekcija 25 "Realtime Event Flow and Cancellation Safety"; cross-reference dodat u sekciju 9 "Computer-use security").
- Izmjena: `docs/ARCHITECTURE_VOICE_FIRST_REVISED.md` (napomena u "Interruption / Stop" sekciji, upućuje na novu sekciju 25).
- Izmjena: `docs/MIGRATION_PLAN.md` (Security Gate 0 checklist proširen sa "execution_id/cancellation_token state mašina"; status kolona ažurirana).

## GitNexus impact

Nije relevantno — samo dokumentacioni fajlovi, bez izmjene koda.

## Šta je urađeno

Korisnik je dostavio analizu koju je uradio Gemini, a pregledao i potvrdio ChatGPT — identifikuje dva rizika: (1) "interruption desync" (glasovni prekid ne prekida automatski tool koji Python/PowerShell izvršava) i (2) "IPC/event volume" (rizik od slanja svakog Realtime delta eventa u Python backend bez throttling-a).

Prije integracije provjereno je stanje protiv stvarnog koda (ne samo teoretski):

- `src/lib/realtime.ts` — `toolRunning` je prost boolean, `disconnect()` ne dira tekuće `executeFunctionCalls()`/`window.ricky.executeTool(...)` pozive. Nema cancellation infrastrukture. **Rizik #1 je potvrđeno stvaran i reproduktivan.**
- `electron/tools_legacy/powershell/computerTypeText.cjs` — jedan atomski `SendKeys::SendWait()` poziv za cijeli string, bez segmentacije/checkpointa. Potvrđuje konkretan primjer iz analize.
- `src/lib/realtime.ts` trenutno **ne šalje nijedan raw Realtime event Python backend-u** (sve ostaje u rendereru) — rizik #2 (event volume) trenutno nije aktivan bug, ali je tačna preventivna mjera za FAZA 8/11 event bridge koji `ARCHITECTURE_VOICE_FIRST_REVISED.md` već najavljuje ("renderer šalje relevantne evente Python backendu") bez konkretnih pravila.
- `docs/ARCHITECTURE_VOICE_FIRST_REVISED.md` već pominje cancellation temu (sekcija "Interruption / Stop") ali samo kao tri neimplementirane stub funkcije (`cancel_pending_confirmation()`, `cancel_safe_before_tool_execution()`, `mark_activity_interrupted()`) bez state mašine.

Zaključak: analiza je tehnički tačna i utemeljena u stvarnim rupama, ne kozmetička. Integrisano bez izmjene značenja korisnikovog teksta:

1. **`docs/SECURITY_HARDENING_PLAN.md` sekcija 25** (nova, dodana na kraj da se izbjegne renumeracija postojećih sekcija 10-24 čije brojeve referenciraju `TOOL_CONTRACTS.md` i `MIGRATION_PLAN.md`): puna `execution_id`/`cancellation_token` state mašina (stanja `planned → waiting_confirmation → approved → preflight → running → commit_started → completed/cancel_requested/cancelled_before_commit/cannot_cancel_commit_started/failed`), preflight/commit split primjer za `computer_type_text`, event volume pravila (šta ide samo u renderer vs. Python backend), throttling/backpressure pravila sa prioritetima (CRITICAL/HIGH/MEDIUM/LOW), UI pravilo da se "Cancelled" ne prikazuje dok backend ne potvrdi, i dopuna finalnih pravila (11-20, nastavak numeracije iz sekcije 24).
2. **Cross-reference u sekciji 9** ("Computer-use security") koja upućuje na sekciju 25.
3. **`docs/ARCHITECTURE_VOICE_FIRST_REVISED.md`** — dodata napomena da tri postojeće stub funkcije treba implementirati prema specifikaciji iz `SECURITY_HARDENING_PLAN.md` sekcija 25, ne proizvoljno.
4. **`docs/MIGRATION_PLAN.md`** — Security Gate 0 checklist eksplicitno dodaje "execution_id/cancellation_token state mašina" kao stavku, vezanu za FAZU 10 (ne nova faza — proširuje obim postojeće). Status kolona ažurirana da navede konkretne kodne dokaze (`toolRunning`, `computerTypeText.cjs`) zašto je ovo stvaran, ne teoretski gap.

## Zašto je urađeno

Korisnik je zajedno sa ChatGPT-jem i Gemini-jem razvio ovu analizu i eksplicitno tražio da se doda u plan kao obavezno arhitektonsko pravilo, nakon što sam potvrdio (na njegov zahtjev za mišljenje) da je analiza tehnički utemeljena. Cilj: spriječiti da voice UI izgleda kao da je Ricky stao dok OS akcija nastavlja "iza leđa" korisnika — pitanje povjerenja i sigurnosti, direktno vezano za FAZU 13/14 (computer-use) koje su već blokirane iza Security Gate 0.

## Kako je urađeno

`Read` na `src/lib/realtime.ts`, `electron/tools_legacy/powershell/computerTypeText.cjs`, `docs/ARCHITECTURE_VOICE_FIRST_REVISED.md` (grep za interrupt/cancel) prije integracije, da se analiza utemelji na stvarnom kodu, ne samo prihvati na riječ. `Edit` na tri dokumenta — nova sekcija dodana na kraj `SECURITY_HARDENING_PLAN.md` (ne u sredinu) da se izbjegne renumeracija postojećih referenciranih sekcija.

## Šta nije dirano

- Nijedan kod (`src/lib/realtime.ts`, `electron/tools_legacy/powershell/computerTypeText.cjs`, `python_backend/`) — ovo je i dalje samo dokumentacija, korisnik nije tražio implementaciju u ovom koraku.
- Postojeća numeracija sekcija 1-24 u `SECURITY_HARDENING_PLAN.md` — nepromijenjena.
- FAZA 9 (confirmations/plans, upravo završena i committovana od GLM-5.2/pi agenta) — nije dirana, samo je Security Gates status red za Gate 1 (koji je GLM/pi već ažurirao) ostavljen netaknut.

## Verifikacija

Ručna provjera da nova sekcija 25 ne renumeriše postojeće sekcije i da svi novi cross-referenceovi (sekcija 9 → 25, `ARCHITECTURE_VOICE_FIRST_REVISED.md` → sekcija 25, `MIGRATION_PLAN.md` → sekcija 25) pokazuju na tačan naslov. Markdownlint upozorenje (MD025, multiple H1) je očekivano i postojeće za cijeli fajl (svaka numerisana sekcija je `#`, ne greška uvedena ovom izmjenom).

## Rizici / ograničenja

- Ovo i dalje samo proširuje **specifikaciju** — implementacija (execution_id/cancellation_token u Python tool executoru, segmentacija `computer_type_text`, event throttling u budućem event bridge-u) ostaje FAZA 10/11 posao, još nezapočet.
- `docs/MIGRATION_PLAN.md` je bio nepromijenjen između mog posljednjeg čitanja i ovog edita (za razliku od ranijih pokušaja kad je GLM/pi paralelno pisao) — FAZA 9 rad je već završen/committovan u trenutku ovog koraka, pa nije bilo concurrent-write kolizije ovaj put.

## Potreban follow-up

- Kad FAZA 10 (permission/risk layer, Claude Code) krene, mora eksplicitno implementirati state mašinu iz sekcije 25, ne generički permission sloj bez cancellation koncepta.
- Kad FAZA 8/11 event bridge stvarno počne slati evente Python backend-u, primijeniti throttling/prioritet pravila iz sekcije 25.4-25.5 od početka, ne naknadno.

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — dokumentacioni zadatak.
