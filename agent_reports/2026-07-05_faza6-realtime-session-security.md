# Agent report — FAZA 6: Realtime session security (Python minta ephemeral credential)

**Datum:** 2026-07-05

## Scope

- Novi: `python_backend/app/schemas/realtime.py`, `python_backend/app/api/realtime.py`, `python_backend/tests/test_realtime.py`.
- Izmjena: `python_backend/app/core/config.py` (dodano `openai_api_key` polje + `.env.local` fallback loading; spojeno sa Codex-ovim paralelnim FAZA 7 dodatkom `data_dir`/`database_path` u istom fajlu).
- Izmjena: `python_backend/app/main.py` (registrovan `realtime_router`; spojeno sa Codex-ovim FAZA 7 storage/action-log wiring-om u istom fajlu).
- Izmjena: `electron/services/pythonClient.cjs` (dodana `createRealtimeSession`).
- Izmjena: `electron/main.cjs` (`handleRealtimeCreateToken` sad zove Python backend umjesto direktnog fetch-a ka OpenAI; uklonjen `process.env.OPENAI_API_KEY` check i `crypto.createHash` safety-identifier iz Electron-a).
- Izmjena: `docs/MIGRATION_PLAN.md` (FAZA 6 status ✅; Security Gate 0 red ažuriran — 3/5 stavki gotovo).

## GitNexus impact

`gitnexus_impact({target: "handleRealtimeCreateToken", direction: "upstream", repo: "nas_agent"})` → simbol nije pronađen (indeks zaostaje za preimenovanjima iz FAZE 3 IPC splita — poznato ograničenje, isto zabilježeno u prethodnim FAZA 3/5 izvještajima). Urađena ručna analiza čitanjem cijele funkcije i njenih pozivalaca prije izmjene.

`gitnexus_detect_changes({repo: "nas_agent", scope: "all"})` nakon izmjene → `risk_level: "low"`, `affected_count: 0`.

## Šta je urađeno

Prije izmjene pročitana su oba FAZA 4/5 izvještaja i trenutna Python backend struktura (`app/api/`, `app/core/`, `app/schemas/`) da se novi endpoint uklopi u postojeće konvencije (isti stil kao `app/api/tools.py`, isti `AppError`/`register_error_handlers` obrazac iz `app/core/errors.py`).

**Python backend:**

1. `app/core/config.py` — `Settings` dobija `openai_api_key: str | None`. `get_settings()` prvo pokušava `python-dotenv` da učita `.env.local` iz repo roota (`REPO_ROOT = Path(__file__).resolve().parents[3]`) sa `override=False` (ne prepisuje već postavljen env), zatim čita `os.environ.get("OPENAI_API_KEY")`. Ovo je fallback — u normalnom radu Electron već ubrizgava `OPENAI_API_KEY` u Python child process env (`pythonProcess.cjs` spawn nasljeđuje `process.env`), pa ovo pokriva i slučaj direktnog pokretanja backend-a (`uvicorn app.main:app`) van Electron-a, po uputama u `python_backend/README.md`.
2. `app/schemas/realtime.py` — `RealtimeSessionRequest` (`session: dict[str, Any]`, namjerno netipizovano — Python ne treba da poznaje puni OpenAI Realtime session schema, samo ga prosljeđuje) i `RealtimeSessionResponse` (`value`, `expiresAt`).
3. `app/api/realtime.py` — `POST /realtime/session`: čita `settings.openai_api_key`; ako nedostaje, vraća `AppError("MISSING_API_KEY", ..., 500)`; inače poziva `https://api.openai.com/v1/realtime/client_secrets` sa istim headerima kao prije (`Authorization`, `OpenAI-Safety-Identifier` — identičan sha256 hash `"riley-local-ricky"` kao u starom `main.cjs` kodu, samo sad računat u Pythonu preko `hashlib`), i mapira upstream grešku/nedostajuću vrijednost na `AppError` (502).
4. `app/main.py` — registrovan `realtime_router`.
5. `tests/test_realtime.py` — 3 nova testa: uspješan slučaj (mockovan `httpx.post`), nedostajući API ključ (500 `MISSING_API_KEY`), upstream 401 greška (502 `REALTIME_REQUEST_FAILED`). Ukupno `11 passed` u cijelom `python_backend` paketu nakon dodavanja (bio 4 prije FAZE 6/7, Codex je u međuvremenu dodao FAZA 7 testove).

**Electron:**

6. `electron/services/pythonClient.cjs` — dodana `createRealtimeSession(session, options)` koja POST-uje na `/realtime/session` (isti `requestJson` helper kao `executeTool`/`listTools`).
7. `electron/main.cjs` `handleRealtimeCreateToken` — i dalje sastavlja `instructions` (RICKY_INSTRUCTIONS + `buildThumbnailBoardInstructions(db)`, jer to zavisi od Electron-side JSON DB stanja koje još nije migrirano — FAZA 7/11 posao) i `session` config objekat (model, tools, audio, tracing — nepromijenjeno), ali **ne dira više `process.env.OPENAI_API_KEY` niti radi direktan `fetch` ka OpenAI** — samo zove `createRealtimeSession(session)` i vraća rezultat. Dodat `Context:` komentar koji upućuje na ovaj report (netrivijalna arhitektonska odluka: zašto Electron i dalje sastavlja instructions/tools, a ne Python).

## Zašto je urađeno

FAZA 6 acceptance kriterijum (`docs/MIGRATION_PLAN.md`) i `SECURITY_HARDENING_PLAN.md` sekcija 7 traže da standardni OpenAI API ključ **ostaje isključivo na backend strani**, a renderer/Electron main proces koristi samo kratkoživući (ephemeral) credential. Prije ove izmjene, `electron/main.cjs` je direktno čitao `process.env.OPENAI_API_KEY` i zvao OpenAI — to je upravo obrnuto od cilja.

Obim je namjerno sužen da NE premjesti i sastavljanje `instructions`/`toolSpecs` u Python (to bi zahtijevalo da Python već ima pristup thumbnail board/DB stanju, što je FAZA 7/11 posao, još u toku kod Codex-a) — samo mjesto gdje se ključ koristi i credential minta.

## Kako je urađeno

Paralelno sa Codex-ovim FAZA 7 radom na istim Python fajlovima (`app/core/config.py`, `app/main.py`) — prije svake izmjene ponovo pročitan fajl (Write/Edit alat je i eksplicitno odbio pisanje jednom zbog konkurentne izmjene, vidi "Rizici" ispod) i moje dopune spojene sa Codex-ovim `data_dir`/`database_path`/storage wiring-om bez brisanja njegovih izmjena.

## Šta nije dirano

- `src/lib/realtime.ts` — netaknut (voice-first pravilo, Python ne preuzima audio pipeline).
- Renderer/React UI — netaknut, `window.ricky.createRealtimeToken()` preload API ostaje identičan, IPC kanal `realtime:create-token` ima isto ime i isti response oblik (`{value, expiresAt}`).
- `toolSpecs`, `RICKY_INSTRUCTIONS`, `buildThumbnailBoardInstructions` — netaknuti, i dalje u `main.cjs`.
- `generateImage`, `webSearch`, `createThumbnailImage` (koji i dalje direktno koriste `process.env.OPENAI_API_KEY`/`EXA_API_KEY` iz Electron-a) — namjerno netaknuti; ta migracija je FAZA 16 ("Prebaciti OpenAI/Exa/image pozive u Python"), van obima FAZE 6.
- Codex-ova FAZA 7 SQLite/storage logika — netaknuta, samo dopunjena (dodane linije, ništa obrisano).

## Verifikacija

1. `python -m pytest` u `python_backend/` → `11 passed, 1 warning` (isti postojeći FastAPI/httpx deprecation warning kao u FAZA 4/5/7).
2. `node --check` na `electron/main.cjs` i `electron/services/pythonClient.cjs` → OK.
3. **End-to-end wiring test bez pravog OpenAI poziva** (da se ne troši pravi API ključ iz `.env.local`): pokrenut stvaran `uvicorn` proces sa namjerno praznim `OPENAI_API_KEY` env varom → `curl POST /realtime/session` vraća `500 MISSING_API_KEY` kako je i očekivano → zatim pozvano `electron/services/pythonClient.cjs`-ov `createRealtimeSession(...)` direktno iz Node-a protiv istog backend-a → greška se ispravno propagira kroz cijeli lanac: `"Python backend request failed: 500 OPENAI_API_KEY is not configured on the Python backend."` Ovo potvrđuje da Electron→Python HTTP wiring radi identično onome što bi `handleRealtimeCreateToken` uradio (isti `createRealtimeSession` poziv), bez potrebe da se pravi live poziv ka OpenAI Realtime API-ju napravi u ovoj sesiji.
4. `gitnexus_detect_changes` (scope "all") → risk LOW, 0 affected execution flows.

Test backend proces je zaustavljen nakon provjere (`taskkill` na port 8765).

## Rizici / ograničenja

- **Nije urađen live test sa pravim OpenAI Realtime API pozivom** (stvarno mintovanje ephemeral credential-a) — namjerno izbjegnuto da se ne troši/rizikuje pravi produkcijski API ključ korisnika bez eksplicitne dozvole. Preporučen ručni test: pokrenuti punu app (`npm run dev` preko `Ricky (Nas-agent).lnk`) i provjeriti da glasovna sesija i dalje uspješno startuje (isto ponašanje kao prije FAZE 6).
- Tokom rada, `Edit`/`Write` alat je jednom odbio izmjenu `python_backend/app/core/config.py` uz grešku "File has been modified since read" — uzrok: Codex je u tom trenutku paralelno radio na istom fajlu (FAZA 7). Fajl je ponovo pročitan i moje izmjene ručno spojene sa njegovim (`data_dir`/`database_path` zadržano, `openai_api_key` dodano pored). Isti obrazac ponovljen (preventivno) za `app/main.py`. Preporuka za buduće paralelne sesije: očekivati povremene collision-e na `app/core/config.py` i `app/main.py` jer su to prirodna mjesta gdje se sve nove faze "kače".
- Error poruka pri nedostajućem API ključu je sad drugačija ("Python backend request failed: 500 OPENAI_API_KEY is not configured on the Python backend." umjesto stare "OPENAI_API_KEY is missing in .env.local") — funkcionalno identično (i dalje baca Error koji IPC handler propagira do renderer-a), ali tekst poruke se promijenio. Nevažno za ponašanje UI-ja (poruka se ne parsira, samo prikazuje), ali vrijedi znati ako se ikad testira po tačnom tekstu greške.
- Security Gate 0 i dalje NIJE zatvoren — ova faza zatvara samo "Realtime session endpoint preko backend-a" stavku; backend lokalni auth token (Security PR-1) i permission/risk layer (FAZA 10/11) ostaju otvoreni.

## Potreban follow-up

- Ručni test stvarne voice sesije (`npm run dev`, pravi OpenAI poziv) na korisnikovom uređaju — agent to namjerno nije radio u ovoj sesiji.
- FAZA 10 (permission/risk layer) i backend local auth token (Security PR-1) ostaju sljedeći sigurnosni koraci prije nego se Security Gate 0 može zatvoriti.
- Kad FAZA 11 (tool registry) dođe na red, razmotriti da li `instructions`/`toolSpecs` sastavljanje treba seliti u Python zajedno sa migracijom DB-a — trenutno namjerno ostavljeno u Electron-u.

## Potrebna korisnička potvrda

Ručni test stvarne glasovne sesije nakon ove izmjene (`npm run dev` ili `Ricky (Nas-agent).lnk`) — agent nije napravio live poziv ka OpenAI Realtime API-ju da ne bi trošio/rizikovao pravi ključ iz `.env.local` bez eksplicitne dozvole.
