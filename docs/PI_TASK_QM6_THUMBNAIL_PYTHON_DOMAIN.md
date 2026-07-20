# PI Task: QM-6T — Thumbnail domen u Python backend

## Cilj

Migrirati thumbnail domen iz Electron legacy sloja u Python backend tako da Qt migracija ne zavisi od `electron/tools_legacy/legacyMedia.cjs` niti od Electron JSON `thumbnailBoard` state-a.

Ovo nije opcioni cleanup. `docs/QT_MIGRATION_PLAN_2026-07-20.md` u QM-6 eksplicitno kaže da je ovo naslijeđeni nezavršeni posao iz starog Electron plana: Image API pozivi za thumbnail board i board state nikad nisu prebačeni u Python. Qt verzija neće imati `legacyMedia.cjs`, pa mora dobiti Python API/tool domen prije QM-9 cutover-a.

## Kontekst koji moraš pročitati prije rada

Obavezno pročitati:

- `CLAUDE.md`
- `AGENTS.md`
- `docs/QT_MIGRATION_PLAN_2026-07-20.md`, posebno QM-6
- `docs/ELECTRON_MIGRATION_ANALYSIS.md`, posebno `legacyMedia.cjs`/thumbnail dijelove
- `docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md`, S-03 thumbnail file/privacy nalaz
- `agent_reports/2026-07-13_security-s03-thumbnail-reference-file-picker.md`
- `electron/tools_legacy/legacyMedia.cjs`
- `electron/main.cjs`
- `electron/ipc_handlers/realtime.cjs`
- `electron/core/realtimeToolSpecs.cjs`
- `electron/ipc_handlers/thumbnails.cjs`
- `electron/services/pythonClient.cjs`
- `python_backend/app/api/thumbnails.py`
- `python_backend/app/services/thumbnail_reference_service.py`
- `python_backend/app/storage/repositories/thumbnail_reference_repo.py`
- `python_backend/app/schemas/thumbnail.py`
- `python_backend/app/services/openai_image_client.py`
- `python_backend/app/tools/images/generate.py`
- `python_backend/app/agent/tool_catalog/phase11.py`
- `python_backend/tests/test_thumbnail_references.py`
- `src/components/ArtifactPanel.tsx`

## Trenutno stanje

Trenutno postoje samo Python thumbnail reference:

- `POST /thumbnail-references`
- `GET /thumbnail-references/{id}/resolve`
- `thumbnail_references` SQLite tabela
- model više ne može dodati proizvoljnu lokalnu putanju; referenca ide samo preko native file pickera

Ali glavni thumbnail domen je i dalje Electron legacy:

- board state je u legacy JSON DB `thumbnailBoard`
- Realtime prompt čita JSON DB kroz `electron/ipc_handlers/realtime.cjs` + `buildThumbnailBoardInstructions()`
- `thumbnail_loading_prepare`
- `thumbnail_generate`
- `thumbnail_edit`
- `thumbnail_select`
- `thumbnail_grid`
- generisanje/editovanje slika direktno poziva OpenAI Images API iz `legacyMedia.cjs`

Ključni problem: `thumbnail_*` nisu u Python tool registryju, pa zaobilaze standardni Python tool/permission/audit tok i drže Qt migraciju vezanu za Electron.

## Opseg

Implementirati Python vlasništvo nad thumbnail domenom:

1. SQLite storage za thumbnail board.
2. Python servis za board operacije.
3. Python Image API podršku za thumbnail generate/edit.
4. Python tool handlere za postojeće model-facing thumbnail alate.
5. Python API za Qt/Electron UI potrebe.
6. Electron delegaciju `thumbnail_*` toolova na Python.
7. Backward-compatible artifact shape za postojeći `ArtifactPanel`.
8. Testove.

## Van opsega

Ne raditi:

- Qt UI port thumbnail panela u ovom zadatku.
- Redizajn `ArtifactPanel.tsx`.
- Brisanje cijelog `electron/` ili `src/`.
- Brisanje `legacyMedia.cjs` prije potvrđenog pariteta.
- Dodavanje model-facing alata koji prima raw filesystem path.
- Slanje screenshotova/privatnih slika u cloud bez postojećih sigurnosnih ograničenja.
- Veliki rewrite `electron/main.cjs`.

## Predložena podjela na male commit pakete

### QM-6T1 — Python storage i board servis

Dodati SQLite tabele u `python_backend/app/storage/db.py`:

```sql
thumbnail_images (
  id TEXT PRIMARY KEY,
  number INTEGER NOT NULL UNIQUE,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  path TEXT,
  prompt TEXT NOT NULL,
  size TEXT NOT NULL,
  parent_id TEXT,
  run_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)

thumbnail_board_state (
  id TEXT PRIMARY KEY,
  selected_id TEXT,
  view TEXT NOT NULL DEFAULT 'grid',
  page INTEGER NOT NULL DEFAULT 1,
  page_size INTEGER NOT NULL DEFAULT 9,
  updated_at TEXT NOT NULL
)
```

Zadržati postojeću `thumbnail_references` tabelu.

Dodati:

- `python_backend/app/storage/repositories/thumbnail_board_repo.py`
- `python_backend/app/services/thumbnail_board_service.py`
- proširenje `python_backend/app/schemas/thumbnail.py`

Servis mora podržati:

- `loading_prepare(mode, target number/id optional) -> board artifact`
- `generate(prompt, run_id optional) -> board artifact`
- `edit(prompt, number optional, target_id optional, run_id optional) -> board artifact`
- `select(number) -> board artifact`
- `grid(page optional) -> board artifact`
- `summary()`
- `artifact(view)`
- `clear_startup_loading()`

Invarijante:

- `number` je permanentan i nikad se ne renumeriše.
- `selected_id` uvijek pokazuje na postojeći ready image ili je `null`.
- loading placeholder se čisti na startup-u.
- edit ne prepisuje postojeći thumbnail nego pravi novi record sa `parent_id`.

### QM-6T2 — Python Image API podrška za thumbnail

Proširiti `python_backend/app/services/openai_image_client.py`:

- postojeći `generate()` ostaje kompatibilan
- dodati `edit_with_inputs(prompt, input_paths, size="1536x1024", quality="medium", model="gpt-image-2")`
- endpoint za edit je `https://api.openai.com/v1/images/edits`
- koristiti multipart form data kroz `httpx`
- ne logovati prompt, API key, raw pathove ni base64

Dodati helper za snimanje output slike u kontrolisani data dir:

- npr. `data/thumbnails/thumbnail-<uuid>.png`
- ne miješati sa standalone `data/images/`
- vratiti lokalni path samo kao app-internal path, isti obrazac koji postojeći `ArtifactPanel` koristi za "Sačuvaj kao..."

Thumbnail prompt logiku portovati iz `legacyMedia.cjs`:

- `thumbnailPrompt()`
- `editThumbnailPrompt()`
- 16:9 `1536x1024`
- reference image ako postoje
- za edit koristiti target thumbnail path + reference image pathove

Reference putanje se ne smiju primati od modela. Koristiti postojeći `ThumbnailReferenceService.resolve(id)`.

### QM-6T3 — Python tool registry

Dodati novi modul:

- `python_backend/app/tools/images/thumbnails.py`

Registrovati alate u `phase11.py` ili izdvojiti novi catalog modul ako je čistije:

- `thumbnail_loading_prepare`
- `thumbnail_generate`
- `thumbnail_edit`
- `thumbnail_select`
- `thumbnail_grid`

Schema mora ostati kompatibilna sa `electron/core/realtimeToolSpecs.cjs`.

Preporučeni risk metadata:

- `thumbnail_loading_prepare`: low, no confirmation, timeout 10000
- `thumbnail_select`: low, no confirmation, timeout 10000
- `thumbnail_grid`: low, no confirmation, timeout 10000
- `thumbnail_generate`: low or medium, `outbound=True`, timeout 120000
- `thumbnail_edit`: medium, `outbound=True`, timeout 120000

Napomena: `thumbnail_edit` čita lokalnu target sliku i reference slike te šalje ih OpenAI Images servisu. Ako se zadrži low risk, mora biti eksplicitno obrazloženo u agent reportu. Moja preporuka je `medium + outbound=True`; S-2 prompt-injection escalation tada traži confirmation ako je model već čitao eksterni sadržaj u istom turnu.

Tool response mora ostati Realtime-compatible:

```json
{
  "ok": true,
  "board": { "...": "summary" },
  "artifact": {
    "title": "Thumbnail Board",
    "kind": "thumbnailBoard",
    "content": "{...JSON string...}"
  },
  "silent": true,
  "thumbnailReady": true
}
```

Za `thumbnail_loading_prepare`, `thumbnailReady` nije obavezan. Za greške vratiti strukturisani error, ne bacati raw exception prema rendereru.

### QM-6T4 — REST API za UI/Qt

Proširiti `python_backend/app/api/thumbnails.py`:

- `GET /thumbnails/board`
- `POST /thumbnails/loading`
- `POST /thumbnails/generate`
- `POST /thumbnails/edit`
- `POST /thumbnails/select`
- `POST /thumbnails/grid`
- `POST /thumbnails/clear-loading`

Ovo nije model-facing API; služi UI/Qt/Electron shell-u. Ipak mora koristiti isti servis kao tool handleri, da nema dva izvora istine.

Ako je endpoint samo za internu app upotrebu, ostaje iza postojećeg local auth tokena.

### QM-6T5 — Electron delegacija i legacy smanjenje

U `electron/main.cjs`:

- dodati `thumbnail_*` u Python delegated set
- ukloniti direktne grane koje zovu `thumbnailGenerate()`, `thumbnailEdit()`, `thumbnailSelect()`, `thumbnailLoadingPrepare()`, `thumbnail_grid` preko legacy DB-a
- ostaviti fallback samo privremeno ako je potreban, ali default mora biti Python

U `electron/core/legacyTools.cjs`:

- dodati thumbnail toolove u `TOOLS_WITH_PYTHON_EQUIVALENT`

U `electron/ipc_handlers/realtime.cjs`:

- prestati čitati `legacyDb.cjs` za thumbnail board instructions
- dobiti thumbnail board instructions iz Python-a, npr. `GET /thumbnails/board` ili poseban `GET /thumbnails/instructions`
- ako backend nije dostupan, fail closed ili dati prazan board tekst bez legacy JSON fallback-a

U `electron/ipc_handlers/thumbnails.cjs`:

- `add reference` ostaje native file picker + Python `/thumbnail-references`
- poslije dodavanja reference, refreshed board artifact treba doći iz Python thumbnail board servisa, ne iz `legacyMedia.cjs`
- `save-as` može ostati Electron native save dialog, ali path validacija mora dozvoliti samo app-internal thumbnail paths

Ne brisati `legacyMedia.cjs` u istom commit-u dok testovi i ručni smoke ne potvrde paritet. Nakon potvrde može se zasebno svesti na minimum ili ukloniti.

## Artifact shape za postojeći UI

`src/components/ArtifactPanel.tsx` očekuje:

```ts
{
  view?: "grid" | "selected";
  selectedId?: string | null;
  references?: Array<{ id?: string; label?: string }>;
  page?: {
    page?: number;
    pageSize?: number;
    totalImages?: number;
    totalPages?: number;
  };
  images?: Array<{
    id?: string;
    number?: number;
    src?: string;
    path?: string;
    prompt?: string;
    type?: string;
    status?: "loading" | string;
    selected?: boolean;
  }>;
}
```

`src` treba biti data URL (`data:image/png;base64,...`) ili lokalno prikaziv URL koji renderer već zna prikazati. Najmanje rizično za paritet: generisati data URL u Python artifactu kao što `legacyMedia.cjs` radi preko `imageDataUrl()`.

`path` je potreban za `"Sačuvaj kao..."`.

## Sigurnosni zahtjevi

- Model nikad ne smije dati raw local path za referentnu sliku.
- Reference se dodaju samo preko native file pickera i postojećeg `/thumbnail-references` toka.
- Svaki resolve reference mora ponovo validirati allowed root, ekstenziju i postojanje fajla.
- `thumbnail_edit` ne smije raditi ako target thumbnail path nije app-internal generated thumbnail.
- Ne logovati base64, promptove, pune lokalne putanje, API key ili raw OpenAI response.
- OpenAI outbound pozivi idu samo iz Python backend-a.
- Tool registry mora označiti outbound toolove sa `outbound=True`.
- Greške moraju biti strukturisane i prikazane korisniku, ne silent fail.

## Testovi

Dodati ili proširiti:

- `python_backend/tests/test_thumbnail_references.py`
- novi `python_backend/tests/test_thumbnail_board.py`
- novi `python_backend/tests/test_thumbnail_tools.py`

Minimalni testovi:

1. Loading placeholder dobija permanentni broj i `status="loading"`.
2. Startup cleanup uklanja loading zapise.
3. Generate sa fake image clientom snima sliku, dodaje ready record i vraća `thumbnailBoard` artifact.
4. Generate failure uklanja loading zapis/run.
5. Edit bez targeta i bez selected thumbnaila vraća kontrolisanu grešku.
6. Edit sa targetom kreira novi thumbnail sa `parent_id`, ne mijenja original.
7. Select po broju postavlja `selected_id` i vraća selected artifact.
8. Grid paginacija vraća stabilne permanentne brojeve.
9. Reference response nikad ne vraća raw path.
10. Referenca obrisana nakon registracije se ne koristi.
11. Tool registry sadrži svih pet `thumbnail_*` alata.
12. `thumbnail_generate` i `thumbnail_edit` imaju `outbound=True`.

Ako se dira Electron delegacija, dodati Node test ili minimalni smoke koji potvrđuje da `thumbnail_*` ide kroz `executeTool()` prema Python-u, a ne kroz legacy grane.

## Verifikacija

Obavezno pokrenuti:

```powershell
cd python_backend
pytest
```

I iz root-a:

```powershell
npm run typecheck
npm run build
```

Ako OpenAI integration smoke nije moguć zbog API ključa ili troška, to jasno napisati u agent reportu. Unit testovi moraju koristiti fake image client, bez mreže.

## Acceptance kriterijumi

Zadatak je gotov kada:

- thumbnail board state je u SQLite/Python-u, ne u Electron JSON DB-u
- `thumbnail_generate` i `thumbnail_edit` ne pozivaju OpenAI iz Electron-a
- `thumbnail_*` toolovi su registrovani u Python registryju
- Realtime tool execution za thumbnail ide kroz Python `executeTool()`
- postojeći React `ArtifactPanel` i dalje može prikazati board artifact
- native add-reference flow i dalje ne izlaže raw path modelu
- "Sačuvaj kao..." radi za Python-generated thumbnail path
- testovi iz sekcije "Testovi" prolaze
- agent report je napisan po `CLAUDE.md`

## Potreban agent report

Na kraju obavezno napisati:

```text
agent_reports/YYYY-MM-DD_pi-qm6-thumbnail-python-domain.md
```

Sekcije po `CLAUDE.md`:

- Datum
- Scope
- GitNexus impact
- Šta je urađeno
- Zašto je urađeno
- Kako je urađeno
- Šta nije dirano
- Verifikacija
- Rizici/ograničenja
- Potreban follow-up
- Potrebna korisnička potvrda

Posebno u reportu naglasiti:

- da li je legacy Electron thumbnail fallback i dalje prisutan
- da li je rađen stvarni OpenAI smoke ili samo fake-client test
- da li Qt migracija sada može zvati Python thumbnail API bez Electron legacy sloja
