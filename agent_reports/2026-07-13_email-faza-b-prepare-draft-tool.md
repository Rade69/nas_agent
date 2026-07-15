# Faza B — email_draft_stage / email_prepare_draft kroz ToolExecutor + confirmation

**Datum:** 2026-07-13
**Scope:** `python_backend/app/services/email_draft_store.py` (novo),
`python_backend/app/tools/messaging/` (novo), `python_backend/app/agent/tool_catalog/phase11.py`,
`python_backend/app/main.py`, `python_backend/pyproject.toml`,
`python_backend/tests/test_email_draft_store.py` (novo), `test_email_tools.py` (novo),
`electron/core/realtimeToolSpecs.cjs`, `electron/main.cjs`, `electron/ipc_handlers/realtime.cjs`,
`src/components/ConfirmationDialog.tsx`, `src/styles/05-confirmation.css`,
`src/i18n/locales/*.json` (5).
**Plan:** [`docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md`](../docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md)
poglavlje 11, Faza B.

## Incident usred rada: svi email-vezani necommitovani fajlovi obrisani

Prije nego što je ovaj rad završen, **svi** necommitovani email-vezani fajlovi
su nestali sa diska — sva tri `docs/EMAIL_COMPOSE_TOOL*.md` dokumenta (uključujući
korisnikov odobren V2 plan), oba prethodna agent izvještaja (Faza A0, Faza A),
`gmail_draft_adapter.py` i njegov test fajl. Potvrđeno da NIJE bilo opšte
`git clean`-stilsko brisanje — sve OSTALE necommitovane datoteke u repo-u
(pi-jev voice reliability rad, drugi Codex planovi, ostali agent izvještaji)
su ostale netaknute. Uzrok nepoznat. Korisnik je eksplicitno odobrio
rekonstrukciju iz konteksta razgovora prije nastavka — svih 7 fajlova je
rekonstruisano tačno (identičan sadržaj, uključujući sve popravke iz
manuelnog Gmail testiranja) prije nego što je Faza B nastavljena.
`pyproject.toml`-ova `websockets` zavisnost je posebno nestala i vraćena
odvojeno usred ranijeg rada — ista, vjerovatno povezana pojava.

## GitNexus impact

`detect_changes` — risk **LOW**, `affected_processes: []` nakon osvježavanja
indeksa. Ovo je značajno niže od prethodnih faza ove sesije (koje su često
bile HIGH zbog kumulativnog necommitovanog rada sa "pi" agentom na
`src/lib/realtime.ts`) — potvrđuje da trenutni diff više ne uključuje ništa
iz pi-jevog paralelnog rada. Ručno potvrđen `git status --short`: sve
izmjene tačno odgovaraju namjeravanom Faza B obimu.

## Šta je urađeno

### Arhitektonska odluka: dva alata umjesto jednog (odstupanje od plana 4.1)

Plan (poglavlje 4.1) ilustrativno prikazuje `email_prepare_draft` sa
`to`/`subject`/`body` DIREKTNO kao tool argumentima. U praksi, postojeći
generički confirmation bridge (`src/lib/realtime.ts`'s `executeFunctionCalls`,
van dosega ove sesije — dijeljen sa "pi" agentom) prosljeđuje TAČNO te
argumente kao `payload` u `createConfirmation()`, koji `ConfirmationService.propose()`
trajno upisuje u SQLite (`payload_json`) — potvrđeno čitanjem koda ovu
sesiju. Da bi se ispoštovao plan poglavlje 4.6 ("nikad stvarne adrese/subject/
body" u trajnom zapisu) BEZ diranja `realtime.ts`-a, alat je podijeljen:

- **`email_draft_stage`** (`risk="low"`, bez confirmation-a, bez Computer Mode-a)
  — prima `to`/`subject`/`body`, čuva ih ISKLJUČIVO u memoriji
  (`EmailDraftStore`, TTL 5 min, `time.monotonic()`-bazirano, nikad na disk),
  vraća `draft_id` + bezbjedan sažetak (`to`, `subject`, `body_length`,
  `has_cc`/`has_bcc` — nikad tijelo).
- **`email_prepare_draft`** (`risk="high"`, `requires_confirmation=True`,
  `requires_computer_mode=True`, `logs_action_receipt=True`) — prima SAMO
  `draft_id`. Pošto je to jedini argument, generički bridge nikad ne vidi
  niti trajno čuva stvarni sadržaj emaila — potvrđeno testom
  (`test_email_prepare_draft_confirmation_payload_is_just_draft_id`) da
  `confirmation.payload == {"draft_id": draft_id}` tačno, bez traga
  primaoca/predmeta/tijela.

### `EmailDraftStore` (`app/services/email_draft_store.py`)

Thread-safe, in-memory, TTL 5 minuta (plan: "2-5 minuta"). `stage()` vraća
nasumičan `draft_id` (`draft_<16 hex>`), `get()` briše istekle zapise prije
pretrage (lazy expiry), `discard()` uklanja eksplicitno. Nikad ne piše na
disk — cijeli poen je da restart procesa NE ostavlja trag.

### `email_prepare_draft` handler (`app/tools/messaging/email.py`)

Vodi `GmailDraftAdapter` (Faza A) kroz punu sekvencu: `launch_isolated_chrome`
→ `open_compose` → `set_subject_field` → `set_body_field` →
`set_recipient_field` → `verify_draft_values`, sa `finally` blokom koji UVIJEK
zove `close_isolated_chrome` i `draft_store.discard(draft_id)` — bez obzira
na ishod (uspjeh ili AppError iz adaptera), draft se troši tačno jednom,
isti princip kao S-04 jednokratna potvrda. Testirano (mock adapter): uspješan
put i put sa `AppError` iz `open_compose` OBA ispravno gase Chrome i brišu
draft.

Cc/Bcc: NAMJERNO odbačeni na `email_draft_stage` nivou (prije nego korisnik
uopšte potvrdi bilo šta) — `GmailDraftAdapter.set_recipient_field` (Faza A)
i dalje ne podržava Cc/Bcc, pa je bolje da to zakaže rano i jasno nego da
korisnik odobri confirmation koja bi kasnije pukla.

### `_def` proširen sa `logs_action_receipt` parametrom

`tool_catalog/phase11.py`'s `_def()` helper je ranije HARDKODOVAO
`logs_action_receipt=False` za sve alate (nijedan trenutni alat to nije
trebao). Dodat je kao opcioni parametar (default nepromijenjen — `False`)
da bi `email_prepare_draft` mogao eksplicitno tražiti receipt (plan 6.3) bez
mijenjanja ponašanja bilo kog postojećeg alata.

### Electron wiring

Isti obrazac kao `filesystem_search`/`set_mode` ranije ove sesije:
- `realtimeToolSpecs.cjs` — oba alata dodana kao model-facing spec-ovi.
- `main.cjs`'s `PHASE11_DELEGATED_TOOLS` — oba imena dodana.
- `main.cjs`'s `LEGACY_FAIL_CLOSED_TOOLS` — **samo** `email_prepare_draft`
  dodan (isti razlog kao `computer_click`/`computer_type_text`: zahtijeva
  potvrdu koju samo Python permission_engine može verifikovati; nema legacy
  ekvivalenta uopšte za ovaj potpuno nov alat, pa bi pad Python backend-a
  inače završio na "Unknown tool" grešci umjesto jasne poruke).
- System prompt (`realtime.cjs`) — nova instrukcija: prikupi to/subject/body
  kroz razgovor → `email_draft_stage` → pročitaj sažetak korisniku →
  `email_prepare_draft(draft_id)` tek nakon jasne potvrde. Eksplicitno kaže
  modelu da alat NIKAD ne šalje i da Cc/Bcc nisu podržani.

### `ConfirmationDialog.tsx` — ispravljen review nalaz 4.5

Stara logika: `/email|mail/i.test(confirmation.action_name)` → prikaz
"Pošalji email" labele. Pošto je novi alat doslovno nazvan
`email_prepare_draft`, ovaj substring bi ga POGREŠNO označio kao "Send"
akciju — tačno rizik koji je review identifikovao (nijedan POSTOJEĆI alat
prije ovog nije aktivirao tu heuristiku, provjereno prije uklanjanja).
Zamijenjeno tačnim `confirmation.tool_name === "email_prepare_draft"`
provjerom → "Pripremi draft" labela + trajna upozoravajuća poruka "Ricky
neće poslati email" u posebnom redu dijaloga. Novi i18n ključevi
(`confirmation.prepareDraft`, `confirmation.emailNeverSent`) dodani u svih
5 lokala.

## Zašto ovako

- Dvo-alatni dizajn je jedini način da se ispoštuje plan 4.6 (privatnost
  sadržaja) bez diranja `src/lib/realtime.ts`/`src/App.tsx` (pi-jeva aktivna
  teritorija ove sesije) — dokumentovano kao svjesno odstupanje od plana
  4.1-ovog ilustrativnog koda, ne od plana 4.6-ovog zahtjeva.
- `draft_id` kao jedini argument je efektivno JAČA garancija od "hash
  kanonskog sadržaja" koncepta iz plana — confirmation je vezana za tačan,
  nasumičan, jednokratan identifikator, ne za hash koji bi neko teoretski
  mogao pokušati pogoditi/reprodukovati.

## Šta nije dirano

- `src/lib/realtime.ts`, `src/App.tsx`, `docs/MIGRATION_PLAN.md` — pi-jev
  paralelni rad, potvrđeno odsutan iz ovog diff-a (GitNexus risk LOW).
- `GmailDraftAdapter` (Faza A kod) — nula izmjena, samo pozvan iz novog
  handlera.
- `permission_engine.py`, `confirmation_service.py`, `tool_executor.py` —
  nula izmjena; postojeći mehanizmi ponovo iskorišteni bez modifikacije.
- Nema voice-first UI-ja, nema `EmailDraftPanel`-a, nema onboarding toka za
  izolovani profil — sve to je Faza C/D iz plana, van obima ove faze.
- Cc/Bcc podrška — namjerno odbačena, ne implementirana.

## Verifikacija

- `python -m pytest tests/test_email_draft_store.py tests/test_email_tools.py -v`
  — **22 passed** (TTL expiry, safe-summary redakcija, fail-closed permission
  gate, i KLJUČNI test da je confirmation payload tačno `{draft_id}`).
- `python -m pytest -q` (cijeli suite) — **316 passed** (294 prije + 22 nova).
- `npm run typecheck`, `npm run build` — čisto.
- `npm run check` + eksplicitan `node --check` na `realtimeToolSpecs.cjs`/
  `realtime.cjs` (nisu u default `check` listi) — čisto.
- `mcp__gitnexus__detect_changes` — risk LOW, `affected_processes: []`.
- Runtime kroz stvarni Electron UI NIJE testiran (agent nema GUI pristup) —
  logika je verifikovana kroz `/tools/execute` HTTP sloj direktno.

## Rizici/ograničenja

- Confirmation dijalog i dalje ne prikazuje živi preview to/subject prije
  potvrde (plan poglavlje 3 to predviđa tek za Fazu C, kroz `EmailDraftPanel`
  koji drži draft u renderer state-u) — za sada, korisnik vidi
  to/subject/body kroz RAZGOVOR (model ih pročita nazad prije nego zatraži
  `email_prepare_draft`), ne kroz sam dijalog. Prihvatljivo za Fazu B, ali
  slabija transparentnost od pune plan vizije.
- `EmailDraftStore` je proces-lokalan — restart Python backend-a između
  `email_draft_stage` i `email_prepare_draft` poziva gubi draft (očekivano
  ponašanje po dizajnu, ali vrijedi imati na umu ako se testira uz česte
  backend restarte).
- Faza A-ovi poznati rizici (To polje bez chip konverzije, Cc/Bcc
  nepodržano) ostaju nepromijenjeni.

## Potreban follow-up

Faza C iz plana: `EmailDraftPanel` + `email_dictation` voice state, glasovni
readback prije potvrde, pristupačnost. Prije toga, vrijedi razmotriti:
runtime test kroz stvaran glasovni razgovor (korisnik nije još probao ovaj
tok uživo kroz UI, samo kroz direktne HTTP pozive u testovima).

## Potrebna korisnička potvrda

Runtime test: zatražiti glasom/tekstom "napiši email X" kroz stvarnu
aplikaciju, potvrditi da se draft ispravno prikuplja kroz razgovor, da
confirmation dijalog ispravno kaže "Pripremi draft" (ne "Pošalji"), i da se
nakon odobrenja stvarno otvori izolovan Chrome prozor sa popunjenim draftom.
