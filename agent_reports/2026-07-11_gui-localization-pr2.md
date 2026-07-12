# Agent Report — GUI lokalizacija PR-2 (DictationScreen, PlansPanel, ActivityTimeline, ConfirmationDialog)

**Datum:** 2026-07-12
**Agent:** pi
**Brief:** `docs/PI_TASK_GUI_LOCALIZATION_PR2_BRIEF.md`
**Konvencije:** `agent_reports/2026-07-11_i18n-foundation.md`

---

## Scope

Četiri komponente dobijaju punu i18n podršku (`useTranslation()` hook za React
komponente, `i18n.t()` direktno za plain funkcije van stabla):

- `src/components/pixel/DictationScreen.tsx` — 22 nova key-a (`dictation.*`)
- `src/components/PlansPanel.tsx` — 10 novih key-eva (`plans.*`) + 4 reuse-a
- `src/components/ActivityTimeline.tsx` — 1 novi key (`activity.empty`) + 1 reuse
- `src/components/ConfirmationDialog.tsx` — 16 novih key-eva (`confirmation.*`) + 4 reuse-a
- `src/i18n/locales/{sr-Latn,en,de,es,fr}.json` — dodani svi novi key-evi

---

## GitNexus impact

Nije pokrenut (nije dostupan). Ručni blast radius:
- 4 komponente izmijenjene, sve importuju i18n
- 5 JSON locale fajlova prošireno (samo dodati key-evi, postojeći netaknuti)
- Nema izmjena ni u jednom drugom fajlu

---

## Šta je urađeno

### 1. Novi i18n key-evi — 4 nova namespace-a

**`dictation.*` (22 key-a):** `badge`, `processing`, `autoSave`, `cancel`,
`placeholder`, `wordCount_one`/`wordCount_other` (pluralizacija), `continueDictating`,
`continueTitle`, `refine`, `formalize`, `shorten`, `proofread`, `translateEn`,
`more`, `moreTitle`, `copy`, `clear`, `undo`, `download`, `send`

- `"Undo"` je zadržano kao `"Undo"` i u sr-Latn — namjerno, iz postojećeg koda
  (`agent_reports/2026-07-11_dictation-rewrite-menu.md`), isti pristup u svim jezicima
  osim de/es/fr gdje je prevedeno standardnom UI terminologijom (`"Rückgängig"` /
  `"Deshacer"` / `"Annuler"`)
- `wordCount_one`/`wordCount_other` koristi i18next pluralizaciju, isti obrazac
  kao `previews.stepsCount` iz PR-1

**`plans.*` (10 key-eva + 5 pod-ključeva za `stepStatus` + 5 pod-ključeva za `status`):**
`stepStatus.{pending,inProgress,completed,skipped,failed}`, `status.{active,pending,completed,cancelled,rejected}`,
`empty`, `advanceTo`, `approve`, `run`, `complete`, `reject`

- `plans.status.*` je **NAMJERNO zaseban namespace** od `planStatus.*` (Previews.tsx).
  Tekst je bio drugačiji već u originalnom kodu prije i18n-a: `"ZAVRŠEN"` vs
  `"ZAVRŠENO"`, a PlansPanel ima peti status `"ODBAČENO"` koji Previews nema.
  Vjerno prevedeno onakvo kakvo jeste — nije "ispravljano" usput.
- `statusBadge()` i `stepStatusLabel()` su plain funkcije van stabla → koriste
  `i18n.t()` direktno (isti pattern kao `voiceStateLabel()` / `planStatusLabel()`)

**`activity.*` (1 key):** `empty` — `"Još nema aktivnosti."` sa tačkom.

- NIJE reuse-ovan `previews.noActivityShort` (`"Još nema aktivnosti"` bez tačke)
  jer su dva različita UI konteksta (preview kartica vs. puna timeline lista).
  Razlika je mala (samo tačka), ali i18n najbolja praksa je da različiti konteksti
  imaju različite key-eve — prevodilac može odlučiti da li tačka treba ili ne.

**`confirmation.*` (16 key-eva):** `field.{to,subject,content,app}`,
`risk.{low,medium,high,critical}`, `summary`, `plan`, `details`, `cancel`,
`sendEmail`, `run`, `discardAria`, `discard`, `dialogAria`, `wait`

- `fieldLabel()` i `riskLabel()` su plain funkcije → `i18n.t()` direktno
- Risk labele **nisu skraćivane/mijenjane** — bezbjednosno značajne poruke,
  vjerno prevedene sa istim značenjem na sve jezike

### 2. Reuse-ovani postojeći key-evi (9 key-eva, bez dupliranja)

| Key | Koristi se u | Originalna komponenta |
|-----|-------------|----------------------|
| `previews.confirmTitle` | ConfirmationDialog | Previews.tsx — ConfirmationPreview |
| `previews.confirmDefaultSummary` | ConfirmationDialog | Previews.tsx — ConfirmationPreview |
| `previews.actionLabel` | ConfirmationDialog | Previews.tsx — ConfirmationPreview |
| `previews.riskLabel` | ConfirmationDialog | Previews.tsx — ConfirmationPreview |
| `previews.showFullHistory` | ActivityTimeline | Previews.tsx — ActivityDrawerPreview |
| `previews.tabActive` | PlansPanel | Previews.tsx — PlansDrawerPreview |
| `previews.tabProposed` | PlansPanel | Previews.tsx — PlansDrawerPreview |
| `previews.tabCompleted` | PlansPanel | Previews.tsx — PlansDrawerPreview |
| `previews.newPlan` | PlansPanel | Previews.tsx — PlansDrawerPreview |

Svi reuse-ovani key-evi imaju identične vrijednosti u svih 5 jezika — provjereno
sa postojećim JSON fajlovima. Nijedan prevod nije dupliran.

### 3. NE prevodi se

- **"Ricky"** u `ActivityTimeline.tsx` (brend ime, isto pravilo svuda)
- **Plan titles / summaries / action names** — korisnički sadržaj, dolazi od
  backend-a, nije UI prevod
- **`confirmation_id` / `plan.id`** — sistemski identifikatori

---

## Zašto je urađeno

Nastavak GUI lokalizacije — PR-1 je pokrio Sidebar, TopBar, Settings, Drawer,
IdleScreen, Previews i PixelMockupBoard. Preostalih 8 komponenti i dalje ima
hardkodiran srpski tekst. PR-2 pokriva 4 od tih 8 — DictationScreen (najvažniji,
direktno vidljiv korisniku), PlansPanel (puni prikaz, ne mockup preview kartica),
ActivityTimeline (puni prikaz), ConfirmationDialog (stvarni modal za
odobravanje/odbijanje, ne preview kartica).

---

## Kako je urađeno

1. **Locale JSON fajlovi** prošireni skriptom (`_patch_locales.cjs`) — dodati
   novi key-evi u svih 5 jezika, postojeći netaknuti
2. **React komponente** koriste `useTranslation()` hook za `t()` pozive
3. **Plain funkcije** (`statusBadge`, `stepStatusLabel`, `fieldLabel`,
   `riskLabel`) koriste `i18n.t()` direktno, uvoz iz `"../i18n"` modula
4. Reuse provjeren protiv postojećih JSON vrijednosti prije implementacije

---

## Šta nije dirano

- Svih 9 reuse-ovanih key-eva — postojeće vrijednosti nisu mijenjane
- `planStatus.*` namespace — potpuno netaknut (to koristi Previews.tsx)
- Bilo koji fajl van dozvoljene liste
- `cyrillicToLatin.ts`, `realtime.ts`, `App.tsx` — nisu dirani

---

## Verifikacija

- ✅ `npx tsc --noEmit` — čisto
- ✅ `npm run build` — uspješan
- ✅ Svi reuse-ovani key-evi imaju identične vrijednosti u svih 5 jezika
- ✅ `plans.status.*` namjerno odvojen od `planStatus.*` (postojeća nekonzistentnost)
- ✅ Risk labele nisu skraćivane

---

## Rizici / ograničenja

1. **de/es/fr prevodi su best-effort, NISU native-speaker potvrđeni.**
   Svi prevodi u novim namespace-ovima (`dictation.*`, `plans.*`, `activity.*`,
   `confirmation.*`) za de/es/fr su najbolji pokušaj. Treba native-speaker review
   prije produkcijske upotrebe na tim jezicima.

2. **"Još nema aktivnosti." odluka** — nije reuse-ovan `previews.noActivityShort`
   (bez tačke) za `activity.empty` (sa tačkom). Ako se kasnije odluči da je ovo
   preterano cijepanje, lako se spoji.

3. **`confirmation.field.app`** — ključ `appName` mapira u `"Aplikacija"` /
   `"Application"` na svim jezicima. Aplikacija kao pojam nema istu težinu na
   svim jezicima (npr. njemačko `"Anwendung"` je preciznije od `"App"`, ali
   konzistentno sa ostatkom UI-a).

---

## Potrebna korisnička potvrda

Nije potrebna za commit — sve verifikacije prolaze, sr-Latn default put je
ponašajno identičan (iste riječi, samo kroz i18n sloj). Korisnik može runtime
testirati promjenu jezika u Settings-u i provjeriti da li se DictationScreen,
PlansPanel, ActivityTimeline i ConfirmationDialog ispravno prevode uživo.