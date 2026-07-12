# Brief za pi — GUI lokalizacija PR-2 (DictationScreen, PlansPanel, ActivityTimeline, ConfirmationDialog)

**Za:** pi · **Od:** Claude
**Nastavak** `docs/PI_TASK_INTERFACE_LANGUAGE_STT_BRIEF.md` i i18n
infrastrukture iz `agent_reports/2026-07-11_i18n-foundation.md` (komitovano
`5b18431`) — ista mehanika, novi fajlovi. i18next + `useTranslation()` hook
+ `src/i18n/locales/*.json` već postoje i rade, ne treba ih ponovo praviti.

**Prije početka pročitaj** `agent_reports/2026-07-11_i18n-foundation.md` u
cjelini — tu su sve konvencije (namespace imenovanje, reuse pravilo, plain
funkcije koriste `i18n.t()` direktno umjesto hook-a, best-effort disclaimer
za de/es/fr) već objašnjene i ne ponavljam ih ovdje detaljno.

---

## Pravila (obavezno)

- **Dozvoljeni fajlovi:**
  - `src/components/pixel/DictationScreen.tsx`
  - `src/components/PlansPanel.tsx`
  - `src/components/ActivityTimeline.tsx`
  - `src/components/ConfirmationDialog.tsx`
  - `src/i18n/locales/{sr-Latn,en,de,es,fr}.json` (dodavanje novih key-eva,
    ne mijenjaj postojeće)
- **NE diraj:** bilo koji drugi fajl. Ako ti zatreba izmjena van ove liste
  (npr. da neki parent proslijedi novi prop), STANI i javi umjesto da
  proširuješ listu sam.
- Svježe pročitaj (`cat`) sve dozvoljene fajlove prije izmjene — mijenjani
  su više puta u zadnja 24h.
- **en/de/es/fr fraze koje pišeš su tvoj best-effort, NISU potvrđene od
  izvornog govornika** — isti princip kao ranije. Označi to eksplicitno u
  svom izvještaju.
- Srpski/bosanski, latinica u komentarima/porukama. Reference `fajl:linija`.

---

## OBAVEZNO pravilo: reuse prije nego što pišeš novi key

Nekoliko stringova u ovim fajlovima je **identično ili skoro identično**
tekstu koji već ima key iz PR-1 (`src/i18n/locales/sr-Latn.json`). Provjeri
svaki string protiv postojećih key-eva prije nego dodaš nov — dupliran
prevod je greška koju ćemo morati čistiti kasnije. Konkretni poznati
slučajevi (provjeri i ostale sam, ovo nije nužno potpuna lista):

| String u kodu | Fajl:linija | Postojeći key za reuse |
|---|---|---|
| "Ricky želi izvršiti ovu akciju" | `ConfirmationDialog.tsx:90` | `previews.confirmTitle` |
| "Pažljivo provjeri detalje prije potvrde." | `ConfirmationDialog.tsx:91` | `previews.confirmDefaultSummary` |
| "Akcija" (label) | `ConfirmationDialog.tsx:106` | `previews.actionLabel` |
| "Rizik" (label) | `ConfirmationDialog.tsx:122` | `previews.riskLabel` |
| "Prikaži cijelu historiju" | `ActivityTimeline.tsx:62` | `previews.showFullHistory` |
| "Aktivni" / "Predloženi" / "Završeni" (tab labele) | `PlansPanel.tsx:45-47` | `previews.tabActive` / `previews.tabProposed` / `previews.tabCompleted` |

**NE reuse-uj** `planStatus.*` (iz `Previews.tsx`) za `PlansPanel.tsx`-ov
`statusBadge()` (linija 50-55) — tekst je NAMJERNO drugačiji između ta dva
mjesta i prije i18n-a (npr. "ZAVRŠEN" u Previews vs "ZAVRŠENO" u PlansPanel,
i PlansPanel ima peti status "ODBAČENO" koji Previews nema) — ovo je
postojeća, pre-i18n nekonzistentnost u aplikaciji, tvoj posao je da je
vjerno prevedeš onakvu kakva jeste, ne da je "ispraviš" usput. Napravi nov,
zaseban namespace za ovo (npr. `plans.status.*`).

"Još nema aktivnosti." (`ActivityTimeline.tsx:40`, SA tačkom na kraju) je
skoro identično `previews.noActivityShort` ("Još nema aktivnosti", BEZ
tačke) — tvoja procjena: ili reuse-uj postojeći key (izbaci tačku iz JSX-a
da se poklopi) ili napravi nov ako smatraš da razlika opravdava zaseban
tekst. Zabilježi odluku u izvještaju.

---

## Fajl po fajl

### `src/components/pixel/DictationScreen.tsx`

Novi namespace `dictation.*`. Stringovi za prevod: `"DIKTIRANJE"` badge,
`"obrađujem..."` / `"auto-čuvanje uključeno"`, `"Otkaži diktiranje"`,
textarea placeholder `"Diktirani tekst će se pojaviti ovdje..."`, word count
`"{{count}} riječi"` (koristi i18next pluralization `_one`/`_other`, isti
obrazac kao `previews.stepsCount` iz PR-1), `"Nastavi diktiranje"` + title
`"Ponovo poveži glas ako je prekinut i nastavi diktiranje"`, `"Doradi"`,
`"Formalizuj"` / `"Skrati"` / `"Provjeri pravopis"` / `"Prevedi na
engleski"`, `"Više"` + title `"Više opcija"`, `"Kopiraj tekst"` / `"Obriši
sve"` / `"Undo"` / `"Preuzmi kao .txt"`, `"Pošalji agentu"`.

**Napomena:** `"Undo"` je već englesko-zvučeća riječ čak i u srpskoj verziji
(namjerno, iz `agent_reports/2026-07-11_dictation-rewrite-menu.md`) — može
ostati `"Undo"` u sr-Latn key-u, ne prevoditi na silu ("Poništi" zvuči
neprirodno u ovom kontekstu, tvoja procjena ako se ne slažeš).

### `src/components/PlansPanel.tsx`

Novi namespace `plans.*`. `STEP_STATUS_LABEL` (linija 26-32): "Na čekanju" /
"U toku" / "Završeno" / "Preskočeno" / "Neuspješno". `TAB_LABEL` (44-47):
reuse iz tabele iznad. `statusBadge()` (50-55): nov `plans.status.*`
namespace, vidi napomenu iznad. `"Nema planova u ovoj kategoriji."` (97).
`"Pomjeri na: {{status}}"` title (130, ima interpolaciju — koristi
`t("plans.advanceTo", { status: t(...) })` ili slično, tvoja procjena kako
najčistije komponovati). Dugmad: `"Odobri plan"` / `"Pokreni"` / `"Označi
završenim"` / `"Odbaci"` (145-176). `"Novi plan"` (186) — **provjeri da li
ovo treba reuse `previews.newPlan`** (ista riječ, iz PR-1 `Previews.tsx`
`PlansDrawerPreview`) — vjerovatno da.

### `src/components/ActivityTimeline.tsx`

Reuse gdje je označeno u tabeli iznad. Ostalo: `entry.role === "ricky" ?
"Ricky" : entry.role` (linija 30) — `"Ricky"` je brend ime, NE prevoditi
(isto pravilo kao svuda drugo u projektu).

### `src/components/ConfirmationDialog.tsx`

Ovo je STVARNI modal za odobravanje/odbijanje akcija (za razliku od
`Previews.tsx` `ConfirmationPreview` koji je samo pregled bez akcija — vidi
komentar na vrhu tog fajla). Reuse gdje je označeno. Novo:
- `PAYLOAD_FIELD_LABELS` (11-20): "Prima" / "Predmet" / "Sadržaj" /
  "Aplikacija" — nov `confirmation.field.*` namespace.
- `RISK_LABEL` (30-35): "Nizak rizik" / "Srednji rizik" / "Visok rizik —
  potrebna potvrda" / "Kritičan rizik — potrebna potvrda" — nov
  `confirmation.risk.*` namespace. **NE mijenjaj/skraćuj tekst**, samo
  prevedi — ovo su bezbjednosno značajne poruke (S-2/permission_engine
  kontekst), zadrži isto značenje doslovno.
- `"Sažetak"`, `"Plan"`, `"Detalji"` labele (111, 129, 135).
- `"Otkaži"` / `confirmLabel` (`"Pošalji email"` / `"Pokreni"`, linija
  78-80 — dinamički izabran tekst, prevedi oba, zadrži istu heuristiku).
- `"Odbaci potvrdu"` aria-label (97), `"Odbaci"` title (98), `"Ricky
  predlaže akciju"` aria-label (83), `"Pričekaj trenutak…"` title (154).

---

## Acceptance criteria

- `npm run typecheck` i `npm run build` — čisto.
- Svaki reuse-ovan key mora biti IDENTIČAN postojećoj vrijednosti u sva 5
  jezika (provjeri da nisi slučajno pisao novi tekst za key koji već
  postoji).
- Agent report: `agent_reports/2026-07-11_gui-localization-pr2.md`,
  standardni CLAUDE.md obrazac. Eksplicitno navedi: (1) koje si key-eve
  reuse-ovao vs napravio nove, (2) odluku o "Još nema aktivnosti."
  tačka-razlici, (3) best-effort disclaimer za de/es/fr.

Kad završiš, javi — Claude verifikuje (build, GitNexus impact, provjera
reuse-a) prije commita.
