# Security docs — indeks (mapa, ne izvor pravila)

**Datum:** 2026-07-16
**Svrha:** Jedan ulaz koji rješava "koja je od ~10 security dokumenata izvor
istine za šta". Ovo je **mapa**, ne novi izvor pravila — ne dodavati pravila
ovdje, samo pokazivati na dom svakog. (Ručni harness cleanup, vidi
`docs/ACCESSIBILITY_AUDIT_2026-07-14.md` diskusiju o harness higijeni;
ne postoji `harness_cleaner` skill i nije potreban na ovoj veličini projekta.)

## Ako ti treba samo jedno
- **Produkcijska sigurnosna istina:** `SECURITY_HARDENING_PLAN.md`. Autoritativan
  za produkcijski build (Security Gates 0/1/2, threat model, tool executor
  provjere, self-test). Ako se bilo koji drugi dokument razilazi s njim — on važi.

## Puna mapa

| Dokument | Šta je | Uloga / status |
|---|---|---|
| `SECURITY_HARDENING_PLAN.md` | Produkcijski sigurnosni plan | **IZVOR ISTINE** (produkcija). Sve ostalo mu je podređeno. |
| `SECURITY_MODEL.md` | Sažetak risk levela + permission pravila (referencira ga `TOOL_CONTRACTS.md`) | Podređen HARDENING_PLAN-u (već sam to deklariše na vrhu). Brz pregled, ne konačna riječ. |
| `SECURITY_GAP_ANALYSIS_AND_PLAN.md` (07-07) | Gap-analiza + plan implementacije 07-07 talasa | Izvor **statusa** za 07-07 hardening talas (tako kaže DELEGATION_PLAN). |
| `SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md` | Codex-ov read-only audit (S-01…S-15) | Aktivan audit, **djelimično izvršen** (S-01/02/03/04 urađeni ove sesije — vidi tracker unutar dokumenta). |
| `SECURITY_AND_VOICE_HARDENING_BACKLOG.md` (07-07) | PR1–PR15 backlog za naredne agente | Forward-looking lista zadataka. Ne status, nego "šta tek treba". |
| `SECURITY_DELEGATION_PLAN.md` (07-07) | Kako delegirati preostali 07-07 posao jeftinijim modelima | Procesni artefakt 07-07 talasa; uglavnom izvršen. Istorijski. |
| `PI_SECURITY_AUDIT_BRIEF.md` | Task brief za pi (read-only D1+D2 audit) | Delegacioni brief; istorijski nakon izvršenja. |
| `EMAIL_COMPOSE_TOOL_SECURITY_REVIEW_2026-07-13.md` | Sigurnosni review email alata | Scope-specific (samo email feature). Vidi i `EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md`. |
| `MULTI_AGENT_SECURITY_ARCHITECTURE_MAP.md` (07-10) | Vizuelna mapa hijerarhije + mjera + multi-agent toka | Reference/overview (drugi agent). |
| `MULTI_AGENT_SECURITY_ARCHITECTURE_VISUAL.html` | HTML render gornje mape | Reference (vizuelni pratilac gornjeg). |

## Kategorije (za brzu orijentaciju)
- **Izvor istine:** HARDENING_PLAN → (podređen sažetak) SECURITY_MODEL.
- **Dated audit/plan talasi:** GAP_ANALYSIS (07-07), IMPROVEMENT_AUDIT (07-13).
- **Backlog:** VOICE_HARDENING_BACKLOG.
- **Procesni/delegacioni (istorijski):** DELEGATION_PLAN, PI_SECURITY_AUDIT_BRIEF.
- **Scope-specific:** EMAIL_COMPOSE_TOOL_SECURITY_REVIEW.
- **Reference/vizuelno:** MULTI_AGENT_SECURITY_ARCHITECTURE_MAP (+ .html).

## Higijensko pravilo
Novo sigurnosno pravilo ima **jedan dom** (najčešće HARDENING_PLAN ili
SECURITY_MODEL za risk/permission stvari). Ne kopirati isto pravilo u više
dokumenata — dodati ga na njegov dom i, ako treba, referencirati odavde.
