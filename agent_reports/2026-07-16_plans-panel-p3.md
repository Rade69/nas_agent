# Agent Report — Plans Panel P3 (confirmation-plan binding)

- Datum: 2026-07-16
- Agent: pi
- Faza: P3 — potvrde vezane za planove

## Šta je urađeno

### 1. ConfirmationDialog prikazuje plan i korak
- Kada `confirmation.plan_id` postoji, traži plan iz `plans` liste
- Prikazuje ime plana + aktivni korak (prvi pending/in_progress)
- CSS: `.confirmation-row-plan` — plavo-istaknuta referenca

### 2. Auto-update plan step poslije approvala
- U `handleApproveConfirmation`: nakon retry rezultata
- Ako `approved.plan_id` postoji → nađi aktivan korak → ažuriraj:
  - `completed` ako je retry uspio
  - `failed` ako nije
- `details.retryResult` sačuvan u step details

### 3. i18n
- `plans.planLabel` / `plans.stepLabel` u 5 locale fajlova

## Fajlovi
- `src/components/ConfirmationDialog.tsx` — plan/step prikaz
- `src/App.tsx` — step update poslije approvala
- `src/i18n/locales/{5}.json` — planLabel, stepLabel

## Provjere
- tsc čist, build OK