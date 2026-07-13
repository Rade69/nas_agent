# Agent report — agent_name postavka (ime agenta se sada može promijeniti)

**Datum:** 2026-07-13
**Scope:** `python_backend/app/schemas/settings.py`, `python_backend/tests/test_settings.py`,
`electron/ipc_handlers/realtime.cjs`, `src/components/pixel/SettingsPanel.tsx`,
`src/i18n/locales/*.json` (5), `src/vite-env.d.ts`.

**Povod:** Korisnik je pitao da li je ime "Ricky" hardkodovano ili vezano za
OpenAI (nije — čist tekst u system promptu). Nakon objašnjenja, zatražio je
da se ime agenta može mijenjati, isto kao što se već može mijenjati ime
kojim agent oslovljava korisnika (`user_name`, postojeća postavka).

## GitNexus impact

`detect_changes` je vratio risk "critical", ali to je **lažno naduvano** —
skenira cijelo necommitovano radno stablo, koje trenutno dijeli drugi agent
("pi", `docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md`)
sa VELIKOM, nepovezanom, u-toku izmjenom `src/lib/realtime.ts`-a (DI test seam
za vitest harness). Ručno provjeren `git diff` na `electron/ipc_handlers/realtime.cjs`
(jedinom "srednje-centralnom" fajlu koji sam dirao) potvrđuje da je moja
izmjena čisto aditivna (novi `agentName` parametar + 3 mjesta interpolacije),
ništa drugo u toj funkciji nije mijenjano. **Nisam stage-ovao/commit-ovao
`src/lib/realtime.ts`, `docs/MIGRATION_PLAN.md`, `package.json`/`package-lock.json`
niti bilo šta iz pi-jevog necommitovanog rada** — ostavljeno netaknuto, po
multi-agent higijeni iz CLAUDE.md.

## Šta je urađeno

Novo `agent_name` polje, ožičeno identično postojećem `user_name` obrascu
(potvrđeno istraživanjem prije izmjene — Explore agent je mapirao cijeli
`user_name` pipeline):

- **Schema** (`settings.py`): `UserSettings.agent_name: str = "Ricky"` +
  `UserSettingsUpdateRequest.agent_name: str | None = None`. Storage/API
  (SQLite key/value tabela, generic `SettingsService`, `GET`/`PATCH /settings`)
  nisu dirani — potpuno generički, vođeni isključivo schema poljima.
- **System prompt** (`realtime.cjs`): `buildRickyInstructions(agentName, userName, languageName)`
  — dodat treći parametar, zamijenjena oba literal "Ricky" pojavljivanja u
  tekstu prompta (`"You are Ricky..."` → `"You are ${agentName}..."`, "what
  Ricky can do" → "what ${agentName} can do"). `handleRealtimeCreateToken()`
  čita `settings.agent_name` istim trim/fallback obrascem kao `user_name`
  (`DEFAULT_AGENT_NAME = "Ricky"` ako je prazno/nedostupno).
- **Settings UI** (`SettingsPanel.tsx`): novo polje "Ime agenta" u istoj
  "Lično" sekciji odmah ispod "Tvoje ime", isti save/status/dirty-check
  obrazac (`agentNameInput`/`agentNameStatus`/`handleSaveAgentName`).
- **i18n** (5 lokala): nove `settings.agentName`/`settings.agentNameHint`
  ključevi. Usput: postojeći `settings.nameHint` tekst ("Riki će te ovako
  oslovljavati...") je imao HARDKODOVANO "Riki"/"Ricky" u sve 4 ostale
  lokale — sad koristi `{{agentName}}` interpolaciju sa trenutnom vrijednosti
  iz `agentNameInput`, tako da hint ostaje tačan i nakon promjene imena.
- **Tipovi** (`vite-env.d.ts`): `UserSettings.agent_name: string` dodano;
  `updateSettings(payload: Partial<UserSettings>)` već pokriva novo polje
  bez izmjene.

## Zašto ovako

- Potpuno mirroring postojećeg `user_name` mehanizma (ista schema/storage/API/
  IPC/UI putanja) — namjerno, korisnik je eksplicitno tražio "kao i ime kojim
  agent oslovljava korisnika". Nema nove infrastrukture, samo novo polje kroz
  već postojeći generički pipeline.
- Scope namjerno OGRANIČEN na system prompt + Settings formu (isti opseg kao
  `user_name`, potvrđen istraživanjem — `user_name` se NE koristi nigdje
  drugo u UI-ju: nema header/greeting/i18n `{{userName}}` interpolacije van
  system prompta i same forme). Vizuelni "Ricky" brending na drugim mjestima
  (naslovi menija "Ricky Menu", `artifact.title: "Ricky Mode"`, ime avatar
  fajla) NIJE dirano — ostaje kao trajni vizuelni brend nezavisno od
  promptovog imena, isto kao što `user_name` ne mijenja bilo šta van prompta.

## Šta nije dirano

- `python_backend/app/services/settings_service.py`, `settings_repo.py`,
  `app/api/settings.py` — nula izmjena, potpuno generički (schema-driven).
- Vizuelni "Ricky" brending van system prompta (meni naslovi, artifact
  naslovi, avatar fajl) — namjerno van obima, vidi "Zašto ovako".
- `src/lib/realtime.ts`, `docs/MIGRATION_PLAN.md`, `package.json` — pi-jev
  necommitovan, nepovezan rad na voice reliability test harness-u; ostavljeno
  netaknuto.

## Verifikacija

- `python -m pytest -q` (cijeli suite) — **283 passed** (280 prije + novi
  `test_get_settings_default_agent_name`/`test_patch_settings_updates_agent_name`,
  plus popravljen postojeći `test_unknown_stored_keys_are_ignored` koji je
  hardkodovao tačan set polja).
- `npm run typecheck`, `npm run build`, `npm run check` (node --check) — čisto.
- `node --check electron/ipc_handlers/realtime.cjs` — čisto (nije u `npm run check` listi).
- `mcp__gitnexus__detect_changes` — risk "critical" prijavljen, ali ručno
  potvrđen kao inflacija od pi-jevog konkurentnog, necommitovanog rada na
  DRUGOM fajlu (`src/lib/realtime.ts`) — moja izmjena je čisto aditivna.
- Runtime NIJE testiran (agent nema Electron GUI pristup).

## Rizici/ograničenja

- Ako korisnik postavi prazno/whitespace-only ime, fallback je "Ricky" (isti
  obrazac kao `user_name` → "Riley") — nema posebne validacije van trim-a.
- Promjena imena zahtijeva NOVU Realtime sesiju da se primijeni (prompt se
  gradi samo pri `handleRealtimeCreateToken()`) — ako je glasovna sesija već
  aktivna, treba disconnect/reconnect da agent počne koristiti novo ime.
  Nije posebno signalizirano korisniku u UI-ju (isti nedostatak već postoji
  za `user_name`/`interface_language` promjene).

## Potreban follow-up

Korisnički test: promijeniti "Ime agenta" u Settings panelu, pokrenuti novu
glasovnu sesiju, i potvrditi da se agent predstavlja novim imenom.

## Potrebna korisnička potvrda

Runtime test (gore) prije nego se ovo smatra potpuno zatvorenim.
