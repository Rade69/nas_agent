# Agent report — Screenshot privacy (retencija + brisanje + galerija)

**Datum:** 2026-07-12
**Povod:** FABLE-5 GUI pregled (2026-07-12), tačka #3 — "Snimci ekrana" kao
top-level navigacija implicira trajno skladište; treba retention politika,
"obriši sve", oznaka poslano-modelu-vs-lokalno.

**Scope:**
- Backend: `python_backend/app/storage/db.py` (nova `screenshots` tabela),
  `app/storage/repositories/screenshot_repo.py` (novo),
  `app/services/screenshot_service.py` (novo), `app/schemas/screenshot.py`
  (novo), `app/api/screenshots.py` (novo), `app/tools/system/screenshot.py`,
  `app/agent/tool_catalog/phase11.py`, `app/main.py`.
- Electron: `electron/ipc_handlers/screenshots.cjs` (novo),
  `electron/services/pythonClient.cjs`, `electron/main.cjs`, `electron/preload.cjs`.
- Frontend: `src/components/pixel/ScreenshotsGallery.tsx` (novo),
  `src/components/pixel/PixelMockupBoard.tsx`, `src/vite-env.d.ts`,
  `src/styles/11-pixel-shell.css`, `src/i18n/locales/*.json` (5 fajlova).

---

## Ključan nalaz prije implementacije (mijenja obim)

Provjereno grep-om kroz cijeli `python_backend/app/agent/` i
`app/tools/system/`: **nijedan screenshot se trenutno nikad ne šalje
nijednom modelu** — nema `image_url`/`base64`/vision poziva bilo gdje u
kodu. `screen_snapshot` je čisto lokalna akcija: PNG se snimi na disk,
prikaže se u lokalnom Artifact panelu (`file://` URL direktno u renderer-u),
kraj. Ovo znači da je `sentToModel` polje **danas uvijek `false`** — nije
previd, to je tačno stanje sistema. Kolona i dalje postoji (vidi ispod), ali
sam badge u galeriji će uvijek pisati "Lokalno" dok se ne doda neka vizuelna
(vision) sposobnost modelu — to je iskreno, ne obmanjujuće.

Drugi nalaz: `screen_snapshot`-ov povratni `artifact` objekat je **potpuno
efemeran** — koristi se samo za taj jedan odgovor u Artifact panelu, nikad
se ne upisuje u bazu (`tool_executor.py` ne perzistira inline `artifact`
polje). Prije ove izmjene, **nije postojao apsolutno nikakav trajan zapis**
o tome koji screenshotovi postoje — jedini trag je bio sam PNG fajl na
disku. "Snimci ekrana" tab je bio statičan placeholder ("Nema snimaka
ekrana.") koji se prikazivao bez obzira šta stvarno postoji na disku.

---

## Šta je urađeno

### Backend

- Nova `screenshots` SQLite tabela: `id, file_path, created_at, sent_to_model`.
- `ScreenshotRepository` — `record()`, `list()`, `list_older_than()`,
  `delete()`, `delete_all()`.
- `ScreenshotService` — `record()`, `list()` (pokreće `cleanup_expired()`
  kao side-effect prije vraćanja liste), `delete_all()` (briše redove I
  fajlove sa diska), `cleanup_expired()` (30 dana default retencija, fiksna
  vrijednost — ne Settings-konfigurabilna u ovom prolazu, vidi "Šta nije
  urađeno").
- `GET /screenshots`, `DELETE /screenshots` (`app/api/screenshots.py`).
- `screen_snapshot` tool handler sad poziva `screenshot_service.record()`
  odmah nakon snimanja PNG-a — dodatno uz postojeći efemeran `artifact`
  povratak, ne umjesto njega.
- Cleanup se pokreće i pri startup-u backend-a (`main.py`), ne samo lijeno
  pri `GET /screenshots` pozivu — fajlovi ne čekaju da neko otvori tab.
- 6 novih testova (`tests/test_screenshots.py`): prazna lista, lista sa
  zapisima (najnoviji prvi), delete-all briše redove i fajlove, delete-all
  preživljava već-obrisan fajl (bez pucanja), retencija stvarno briše
  zastarjele redove pri `list()`, i end-to-end test da `screen_snapshot`
  tool stvarno upisuje red (ne samo efemeran artifact).

### Electron

- Isti thin-passthrough obrazac kao `settings.cjs`/`text.cjs` —
  `screenshots:list`/`screenshots:delete-all` IPC kanali,
  `window.ricky.listScreenshots`/`deleteAllScreenshots`.

### Frontend

- `ScreenshotsGallery.tsx` zamjenjuje statičan placeholder — grid thumbnail
  prikaz (`file://` URL, isti mehanizam koji `ArtifactPanel.tsx` već koristi
  za lokalne slike, ništa novo za CSP/sigurnosnu konfiguraciju), "Obriši
  sve" dugme sa `window.confirm()` potvrdom, retention napomena tekst, badge
  po snimku (Lokalno/Poslano modelu — vidi napomenu o `sentToModel` iznad).
  Prazno stanje reuse-uje postojeći `dashboard.noScreenshots` key.
- Novi `screenshots.*` i18n namespace, 8 key-eva, svih 5 jezika (sr-Latn/en
  pouzdani, de/es/fr best-effort, isti disclaimer kao svugdje drugo u ovom
  projektu za ne-srpske/ne-engleske prevode).

---

## Šta NIJE urađeno (namjerno, obrazloženo)

- **Retention period nije Settings-konfigurabilan** — fiksnih 30 dana.
  Dodavanje novog Settings polja bi udvostručilo obim ovog zadatka bez
  jasne potrebe još; lako se doda kasnije ako korisnik stvarno zatraži.
- **`sent_to_model` nema poseban UI za "kad" se to desi** — jer se to nikad
  ne dešava danas (vidi "Ključan nalaz" iznad). Kolona i badge postoje kao
  pripremljena infrastruktura, ne aktivno korišćena logika.
- Nema paginacije u galeriji — `list(limit=200)` je dovoljno za realan obim
  prije nego retencija počne brisati stare. Ako se ovo pokaže nedovoljno,
  lako se doda kasnije.

---

## Verifikacija

- `cd python_backend && python -m pytest -q` — **242 passed** (236 + 6 nova).
- `npm run typecheck` — čisto.
- `npm run build` — čisto.
- `node --check` na sva 4 dirana/nova `.cjs` fajla — čisto.
- Runtime NIJE testiran — Electron desktop app, nema browser-automation
  alata u ovom okruženju. Potreban korisnički test: napraviti screenshot
  (Computer Mode → screen_snapshot), otvoriti "Snimci ekrana" tab, provjeriti
  da se snimak prikaže sa thumbnail-om i badge-om "Lokalno", probati
  "Obriši sve".

## Potreban follow-up

- Runtime test korisnika.
- Ako se ikad doda vision-capable poziv modelu (screenshot poslan OpenAI-ju),
  taj kod put mora eksplicitno postaviti `sent_to_model=True` — trenutno
  nema poziva koji bi to trebao da radi.

## Potrebna korisnička potvrda

Runtime test prije nego se smatra potpuno gotovim.
