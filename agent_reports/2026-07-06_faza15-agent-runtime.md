# Agent report — FAZA 15: Agent runtime u Pythonu (LocalDesktopAssistant)

**Datum:** 2026-07-06

## Scope

Novi Python moduli i endpointi:
- `python_backend/app/agent/conversation_state.py` (novo)
- `python_backend/app/agent/model_client.py` (novo)
- `python_backend/app/agent/prompt_builder.py` (novo)
- `python_backend/app/agent/runtime.py` (novo)
- `python_backend/app/schemas/agent.py` (novo)
- `python_backend/app/storage/repositories/agent_repo.py` (novo)
- `python_backend/app/api/agent.py` (novo)
- `python_backend/app/storage/db.py` — dodane tabele `agent_conversations`, `agent_messages`
- `python_backend/app/agent/tool_executor.py` — dodat javni `.registry` property (aditivno)
- `python_backend/app/main.py` — wiring `agent_runtime`/`conversation_state_service`, `include_router(agent_router)` (spojeno sa GLM-ovim paralelnim FAZA 16 izmjenama u istom fajlu)
- `python_backend/tests/test_agent_runtime.py` (novo, 6 testova)

## GitNexus impact

Prije izmjene `ToolExecutor`: `gitnexus_impact({target: "ToolExecutor", direction: "upstream", repo: "nas_agent"})` → risk **LOW**, jedini direktni pozivalac `app/api/tools.py` (koji instancira `ToolExecutor` po requestu). Dodavanje `@property registry` je čisto aditivno — ne mijenja postojeći `__init__`/`execute` ugovor.

Nakon svih izmjena: `gitnexus_detect_changes({repo: "nas_agent"})` → risk **HIGH**, ali novi FAZA 15 fajlovi (agent.py, runtime.py, model_client.py, prompt_builder.py, conversation_state.py, agent_repo.py) se uopšte ne pojavljuju u listi (izgleda da `detect_changes` ne prijavljuje potpuno nove/untracked fajlove kao "added" simbole, samo diff postojećih). Sve prijavljene "touched" promjene dolaze iz: (a) mojih izmjena (`ToolExecutor`, `main.py`, `db.py` — sve aditivno), (b) GLM-ovih paralelnih necommitovanih FAZA 16 izmjena (`tool_registry.py`, `config.py`, dio `main.py`), (c) ranije session-ove `src/App.tsx` izmjene (polling konsolidacija). Širina preko `App` root simbola (7 "affected_processes" koji dijele samo `App` kao roditelja) je poznat artefakt grafa iz prethodnih izvještaja, ne stvarna regresija. Pokrenuto `npx gitnexus analyze` prije provjere jer je prvi `detect_changes` poziv izgledao zastario (indeks nije imao nove fajlove) — rebuild je prošao, ali rezultat je ostao isti jer alat evidentno ne prati potpuno nove fajlove kao promjenu.

## Šta je urađeno

Implementiran jedan-agent Python runtime ("LocalDesktopAssistant") po originalnoj specifikaciji iz `docs/RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md` ("Agent runtime u Pythonu", stara numeracija FAZA 14 — MIGRATION_PLAN.md je izvor istine za brojeve, tamo je ovo FAZA 15):

- **Conversation state**: `agent_conversations`/`agent_messages` SQLite tabele; `AgentConversationRepository` (CRUD) + `ConversationStateService` (ID generisanje, `get_or_create`, `append_message`, `history`, `raw_history_for_prompt` za prompt builder).
- **Model client**: `ModelClient` Protocol + `OpenAIModelClient` (httpx wrapper oko Chat Completions API, isti stil kao `ExaClient`/`OpenAIImageClient` iz FAZE 16 — bez SDK zavisnosti). Protocol omogućava `ScriptedModelClient` fake u testovima — **nijedan test ne zove pravi OpenAI API**.
- **Prompt builder**: čisto funkcionalan modul — `tools_to_openai_schema()` pretvara `ToolDefinition` listu (iz `ToolRegistry.list()`) u OpenAI function-calling format; `build_messages()` sastavlja messages niz iz istorije + sistemski prompt koji eksplicitno kaže modelu da ne tvrdi uspjeh dok tool rezultat to ne potvrdi.
- **Runtime**: `LocalDesktopAssistant.handle_message()` — petlja (max 4 iteracije): pozove model, ako vrati tool_calls izvrši ih **kroz isti `ToolExecutor.execute()` koji koristi i `POST /tools/execute`** (isti permission engine iz FAZE 10, ista cancellation state mašina), doda tool rezultate u istoriju, pozove model ponovo; ako model vrati čist tekst bez tool poziva, to je finalni odgovor.
- **API**: `POST /agent/message` (`{message, conversation_id?, computer_mode?}` → `{conversation_id, reply, tool_calls[], artifact_ids[], event_ids[]}`), `GET /agent/conversations/{id}` (puna istorija poruka).
- **Testovi** (6, svi sa `ScriptedModelClient` fake-om, bez mreže): plain reply bez tool poziva; perzistencija konverzacije + fetch; 404 na nepostojeću konverzaciju; low-risk tool (`echo`) izvršen kroz permission layer i rezultat vraćen modelu za finalni odgovor; **critical tool (`records_delete`) bez `confirmation_id` odbijen sa `CONFIRMATION_REQUIRED`** (agent runtime ga nikad ne dobija automatski — model ne može "izmisliti" odobrenje); **`screen_snapshot` bez `computer_mode` odbijen sa `COMPUTER_MODE_REQUIRED`**.

## Zašto je urađeno

Ovo je arhitektonski centralna faza migracije — "agent brain" se seli iz onoga što je do sada bio direktan `/tools/execute` poziv sa UI-ja u pravi Python-side orkestracioni sloj koji zna da poziva alate na osnovu modela. Ključni zahtjev iz `MIGRATION_PLAN.md`/originalne specifikacije: **"Python agent ne može zaobići permission layer"** — ovo je struktuno garantovano time što `runtime.py` nema svoj poseban put izvršavanja alata, već isključivo poziva isti `ToolExecutor` koga koristi i postojeći `/tools/execute` endpoint. Testovi za `records_delete`/`screen_snapshot` to i eksplicitno dokazuju, ne samo pretpostavljaju.

## Kako je urađeno

1. Pročitani postojeći moduli prije pisanja koda: `tool_executor.py`, `tool_registry.py`, `schemas/tool.py`, `permission_engine.py`, `confirmation_service.py`, `artifact_service.py`, `action_log.py`, `plans.py`/`schemas/plan.py` (za API/schema konvencije), `exa_client.py`/`openai_image_client.py` (za httpx client stil), `test_phase11_tools.py` (za test fixture stil).
2. `config.py`/`main.py` re-pročitani svježe preko `Bash cat` neposredno prije izmjene (poznat recurring-collision fajl — GLM paralelno radi FAZU 16 na istom fajlu); izmjene u `main.py` dodate kao novi blok koji ne dira GLM-ove FAZA 16 linije.
3. `gitnexus_impact` pokrenut na `ToolExecutor` prije dodavanja `.registry` property-a (LOW risk, potvrđeno prije izmjene).
4. Nakon implementacije: `python -m pytest tests/ -q` → **78 passed** (72 postojeća + 6 nova), nema regresija.
5. `npx gitnexus analyze` + `gitnexus_detect_changes` pokrenuti nakon izmjena (rezultat i objašnjenje iznad).

## Šta nije dirano

- Postojeći `/tools/execute`, `/tools` endpointi — nepromijenjeni (samo `ToolExecutor` dobio novi read-only property).
- `permission_engine.py`, `cancellation.py`, `confirmation_service.py` — nepromijenjeni; agent runtime ih koristi indirektno kroz `ToolExecutor`, bez ijedne izmjene njihove logike.
- GLM-ov FAZA 16 rad (`exa_client.py`, `openai_image_client.py`, `tools/web/search.py`, `tools/images/generate.py`, `EXA_API_KEY`/`exa_api_key` u `config.py`) — netaknuto, samo pročitano radi konvencije za `model_client.py`.
- Nema multi-agent orkestracije, nema streaming odgovora, nema UI integracije (frontend poziv `/agent/message` — ostaje budući follow-up, van FAZA 15 obima po specifikaciji).

## Verifikacija

1. `python -m pytest tests/ -q` — **78 passed**, 0 failed.
2. `gitnexus_impact` na `ToolExecutor` prije izmjene — LOW risk.
3. `npx gitnexus analyze` + `gitnexus_detect_changes` nakon izmjene — HIGH risk objašnjen iznad kao artefakt kumulativnih necommitovanih promjena više agenata preko `App` root simbola, ne regresija iz ove faze.
4. Ručno pregledan finalni `main.py` da potvrdim da GLM-ova FAZA 16 wiring (exa_client/openai_image_client/images_dir u `phase11_services`) nije slučajno prepisana.

## Napomena o paralelnom commit-u (cross-agent)

Dok je ovaj rad bio u toku, GLM je commitovao FAZA 16 (`499f450 feat(phase-16): move OpenAI/Exa/image integrations to Python backend`) i taj commit je — po njihovom vlastitom priznanju u commit poruci — pokupio i moje već-sačuvane (ali još ne moje-commitovane) FAZA 15 izmjene u `main.py`, `config.py` i `tool_registry.py`, jer smo dijelili isto working tree stanje na disku u trenutku njihovog commit-a. GLM je to eksplicitno primijetio i namjerno ostavio moje NOVE fajlove (`runtime.py`, `api/agent.py`, itd.) unstaged upravo da bih ih ja sam commitovao. Provjereno (`git diff HEAD -- main.py` prazan, `git show 499f450 -- main.py` sadrži i FAZA 15 wiring) — nema izgubljenog rada, samo su `main.py`/`config.py`/`tool_registry.py` sada već u historiji prije nego što sam ja stigao da ih commitujem. Preostaje da se commituju: `tool_executor.py`, `db.py` (obje čisto FAZA 15 izmjene, GLM ih nije dirao) i svi novi FAZA 15 fajlovi.

## Rizici / ograničenja

- `OpenAIModelClient` nije nikad pozvan sa pravim API ključem u ovoj sesiji (namjerno — established pravilo "nikad ne trošiti pravi API budžet u testovima"). Prva prava provjera end-to-end poziva modela ostaje korisniku kad pokrene aplikaciju uživo.
- Runtime nema mehanizam da agent sam ponudi/kreira `confirmation_id` za tool koji zahtijeva odobrenje (npr. da predloži plan i traži da korisnik odobri kroz `/confirmations` UI prije ponovnog poziva) — trenutno će critical/confirmation-required tool pozivi iz agent runtime-a UVIJEK biti odbijeni dok korisnik ručno ne kreira i odobri confirmation preko postojećeg `/confirmations` toka i ne pošalje `confirmation_id` kroz **budući** UI tok. Ovo je namjerno minimalan MVP obim (spec eksplicitno kaže "ne uvoditi više agenata/orkestraciju još"), ali znači da agent trenutno ne može sam "predložiti pa izvršiti" rizičnu akciju u jednom potezu — što je zapravo poželjno bezbjednosno ograničenje za sada.
- Nema frontend (React) integracije sa `/agent/message` — Electron/React strana i dalje zove `/tools/execute` direktno preko postojećeg toka; kad UI treba da razgovara sa agentom (a ne direktno da bira alate), treba dodati IPC/HTTP poziv ka novom endpointu (van obima ove faze).
- `MAX_TOOL_ITERATIONS = 4` je proizvoljna zaštita od beskonačne petlje poziva alata; nije testirano ponašanje kad se taj limit stvarno dostigne u realnom scenariju (samo je pokriveno da kod ne puca).

## Potreban follow-up

- Odlučiti kako će UI/voice tok pozivati `/agent/message` (zamjena za direktan `/tools/execute` poziv sa frontenda, ili paralelan tok) — ovo direktno utiče na FAZA 12 (Companion orb) i budući UI redesign.
- Razmisliti o mehanizmu kojim agent runtime može predložiti confirmation (npr. pozvati `POST /confirmations` sam kad tool zahtijeva odobrenje, umjesto da samo vrati grešku) — ali to je namjerna odluka da se odloži dok se ne odluči UX tok za to (Voice Input UX dodatak u UI redesign dokumentu already predviđa "Confirmation Review Mode").
- GLM-ova FAZA 16 (OpenAI/Exa/image u Python) je u toku paralelno — kad se commituje, provjeriti da `model_client.py` (FAZA 15) i `openai_image_client.py` (FAZA 16) ne bi trebalo da dijele zajednički HTTP helper (trenutno namjerno duplirano, isti stil, radi izolacije faza).

## Potrebna korisnička potvrda

Nema blokirajuće. Preporučeno: kad korisnik proba pravi `/agent/message` poziv uživo (sa pravim OpenAI ključem kroz Electron), potvrditi da odgovor modela izgleda razumno i da se tool pozivi (npr. `note_add`, `web_search` nakon FAZE 16) stvarno izvršavaju i vraćaju u odgovoru.
