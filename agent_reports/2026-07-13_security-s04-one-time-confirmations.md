# Agent report — S-04: confirmations su sad jednokratne

**Datum:** 2026-07-13
**Scope:** `python_backend/app/storage/repositories/confirmation_repo.py`,
`python_backend/app/services/confirmation_service.py`,
`python_backend/app/agent/permission_engine.py`,
`python_backend/app/schemas/confirmation.py`, `src/vite-env.d.ts`,
`python_backend/tests/{test_permission_engine,test_tool_executor_permission}.py`.

**Povod:** Nastavak rada po `docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md`
nakon Security PR A (S-01/S-02, prethodni commit). Korisnik je izabrao S-04
(jednokratne confirmations) kao sljedeći P0 nalaz — manji, čisto backend
zahvat bez UX promjena, za razliku od S-03 (thumbnail/cloud) koji zahtijeva
arhitektonsku promjenu i file picker UX.

## GitNexus impact

`mcp__gitnexus__impact(target: "check_permission", direction: "upstream")`
prije izmjene — risk LOW, jedini pozivalac `ToolExecutor.execute()` (isti
gate za REST i agent runtime, po dizajnu). `detect_changes` prije commita —
risk "high", ručno provjereno: stvaran, namjeran diff u `check_permission`
(dvije nove provjere) plus rutinski line-shift artefakt na `_to_dict`/
`_resolve` (ConfirmationService) i na testne funkcije nakon umetanja novih
testova ranije u fajlu — potvrđeno `git diff`/`--numstat` da nema
neočekivanih brisanja ni izmjena sadržaja van namjeravanog obima.

## Šta je urađeno

- **Nalaz #1 (glavni):** odobrena confirmation je ostajala `approved`
  zauvijek (do TTL isteka) — ista confirmation je mogla autorizovati više
  identičnih izvršenja. Novi `ConfirmationRepository.consume()` — atomska
  `UPDATE ... WHERE id = ? AND status = 'approved'` tranzicija u `consumed`
  (compare-and-swap; SQLite serijalizuje pisanja, pa samo prvi pozivalac
  vidi `rowcount == 1`). `ConfirmationService.consume()` tanak wrapper.
  `permission_engine.check_permission()` sad poziva `consume()` kao
  POSLJEDNJI korak prije `return None` (odobrenje) — "prije commit faze" po
  audit preporuci, pošto `ToolExecutor` zove `tool.handler()` tek nakon što
  `check_permission` vrati `None`. Ako `consume()` vrati `None` (već
  potrošena), vraća se `CONFIRMATION_ALREADY_CONSUMED`.
- **Nalaz #2 (manji, u istoj funkciji):** confirmation BEZ `tool_name`
  vezanog je prije mogla proći `bound_tool_name` provjeru neopaženo (provjera
  se dešavala SAMO ako je `tool_name` bio postavljen) — "prazan ček" koji je
  mogao autorizovati bilo koji tool poziv čiji payload_hash slučajno
  poklopi. Provjera pooštrena: `if not bound_tool_name or bound_tool_name != tool.name`
  — sad ODBIJA i odsustvo tool_name-a, ne samo mismatch. `ConfirmationCreateRequest.tool_name`
  ostaje opciono na nivou kreiranja (dokumentovano da confirmations mogu
  postojati za ne-tool akcije), ali takva confirmation sad strukturalno ne
  može autorizovati NIJEDAN tool poziv.
- `ConfirmationStatus` Literal (Python schema + `src/vite-env.d.ts`) proširen
  sa `"consumed"` — provjereno da nijedan frontend switch/mapping ne zahtijeva
  exhaustive-case ažuriranje (typecheck čist), i da `ConfirmationDialog.tsx`
  samo provjerava `status === "pending"` (dialog se zatvara prije nego status
  ikad postane "consumed", pa ovo stanje nikad nije vidljivo korisniku kao
  poseban UI slučaj).
- Testovi: `test_approved_confirmation_is_consumed_after_first_use` (osnovni
  acceptance test — status stvarno postaje "consumed"),
  `test_replaying_a_consumed_confirmation_is_rejected` (sekvencijalni replay
  — pogađa raniji "not approved" check, poruka eksplicitno kaže "consumed"),
  `test_consume_is_atomic_a_second_direct_call_is_rejected` (direktan
  repository-level test atomske brane — ovo je pravi test za
  `CONFIRMATION_ALREADY_CONSUMED` putanju, koja je inače dostiživa samo kroz
  pravu trku), `test_confirmation_without_tool_name_cannot_gate_a_tool_call`,
  i end-to-end `test_replaying_the_same_confirmation_id_is_blocked_end_to_end`
  kroz pravi `ToolExecutor`.

## Zašto ovako

- **Dva odvojena error koda** (`CONFIRMATION_NOT_APPROVED` za sekvencijalni
  replay, `CONFIRMATION_ALREADY_CONSUMED` za pravu trku) nisu bila planirana
  unaprijed — otkriveno tek kad je prvi test pao: sekvencijalni drugi poziv
  radi svjež `confirmation_service.get()` koji već vidi `status="consumed"`
  i pada na POSTOJEĆU `if confirmation["status"] != "approved"` provjeru
  PRIJE nego stigne do mog novog `consume()` poziva. Ovo je zapravo ispravno
  i dovoljno — poruka već eksplicitno kaže "is 'consumed', not approved".
  `CONFIRMATION_ALREADY_CONSUMED` ostaje kao odbrana u dubini za usku trku
  (dva zahtjeva čitaju "approved" prije nego ijedan upiše) — testirana
  direktno na repository nivou, ne kroz sekvencijalni poziv koji je ionako
  ne bi dostigao.
- Pooštrena `tool_name` provjera je urađena u `check_permission` (gate
  trenutku), ne kao obavezno polje na `ConfirmationCreateRequest` (kreiranje
  trenutku) — manje invazivno, ne kvari postojeću, dokumentovanu upotrebu
  confirmations za ne-tool akcije (npr. plan odobrenja), samo zatvara rupu
  tamo gdje se stvarno koristi za gate-ovanje tool izvršenja.

## Šta nije dirano

- S-03 (thumbnail/cloud privacy) i preostalih 11 nalaza iz audita — čekaju
  odvojen rad.
- `ConfirmationDialog.tsx`/`PlansPanel.tsx` — nije bilo potrebno mijenjati
  frontend (provjereno, "consumed" stanje se nikad ne renderuje kao poseban
  slučaj).
- Postojeći `propose()`/`ConfirmationCreateRequest` API — `tool_name` ostaje
  opciono polje na kreiranju, namjerno.

## Verifikacija

- `mcp__gitnexus__impact` prije izmjene (LOW) i `detect_changes` prije
  commita (HIGH, ručno potvrđen kao artefakt + očekivan diff).
- `npm run typecheck`, `npm run build` — čisto.
- `python -m pytest -q` (cijeli `python_backend` suite) — **262 passed**
  (257 prije + 5 novih).

## Rizici/ograničenja

- Confirmation koja je "consumed" ostaje u SQLite bazi trajno (isto kao i
  ostala terminalna stanja approved/rejected/expired/cancelled) — nema
  cleanup/retention politike za stare confirmations, ali to je postojeći,
  nepromijenjen aspekt sistema (van obima ovog fix-a).
- Ako neki BUDUĆI kod pozove `propose()` bez `tool_name` namjeravajući da
  gate-uje tool izvršenje (greška developera, ne runtime bug), sad će dobiti
  jasnu `CONFIRMATION_MISMATCH` grešku umjesto tihog sigurnosnog propusta —
  ovo je namjerna promjena ponašanja ("fail loud" umjesto "fail silent").

## Potreban follow-up

Sljedeći u redu po audit prioritetnoj mapi: S-03 (thumbnail/cloud privacy,
najveći preostali P0 privacy rizik) — zahtijeva native file picker + Python
file sandbox migraciju, veći zahvat koji mijenja korisničko iskustvo.

## Potrebna korisnička potvrda

Nije potrebna za ovaj korak — potpuno pokriveno backend test suite-om
(262/262 prolazi), nema UX/runtime promjene koju treba ručno provjeriti.
