# Pregled aplikacije — uočeni problemi i prijedlozi za unapređenje

**Datum:** 2026-07-12
**Agent:** pi
**Opseg:** Cjelokupna aplikacija — Python backend, Electron shell, React frontend

---

## 1. KRITIČNO: `electron/main.cjs` krši AGENTS.md pravilo

**AGENTS.md kaže:** *"Do not add new business logic to `electron/main.cjs`."*

**Stvarno stanje:** `electron/main.cjs` ima 772 linije, od čega je **~400 linija čiste poslovne logike** — `handleToolsExecute()` sadrži 24 inline `if (name === "...")` handlera koji su **DUPLIRANI**:
- Postoje u `PHASE11_DELEGATED_TOOLS` setu (šalju se u Python) ✅
- Postoje i kao legacy fallback handleri u `main.cjs` ⚠️

**Konkretan problem — dual data stores:**
- Kad Python radi: `note_add` ide u `data/ricky.sqlite` (SQLite)
- Kad Python padne: `note_add` ide u `data/ricky-db.json` (JSON)
- Ako korisnik doda belešku dok je backend down, ta beleška **nikad neće biti vidljiva** u SQLite-u kad se backend vrati — dva odvojena storage-a, podaci divergiraju. Isto važi za `records_create/search/update/delete`, `web_search`, `image_generate`.

**Prijedlog (visok prioritet):**
1. **Ukloniti sve legacy inline handler-e** za toolove koji već imaju Python ekvivalent (`note_*`, `records_*`, `artifact_*`, `web_search`, `image_generate`, `screen_snapshot`, `ui_inspect`)
2. Ako Python backend nije dostupan, vratiti **struktuiranu grešku** (`BACKEND_UNAVAILABLE`) umjesto da se fallback-uje na JSON DB — isto kao što `LEGACY_FAIL_CLOSED_TOOLS` već radi za high-risk toolove
3. `mermaid_render` i `thumbnail_*` nemaju Python ekvivalent — to su jedini toolovi koji opravdano ostaju u Electronu dok se ne migriraju

**Očekivani efekat:** `main.cjs` se smanjuje sa 772 na ~250 linija, uklanja se dual-store bug.

---

## 2. VISOK: Nula JS/TS testova

**Stanje:** 236 Python testova (`pytest`), **0 JavaScript/TypeScript testova**.

**Zašto je ovo problem:** Već su nađena **2 stvarna bug-a** u `App.tsx` i `realtime.ts` koja `npm run quality` nije uhvatio:
- `return` umjesto `continue` u confirmation bridge petlji (preskakalo ostatak batch-a)
- Retry rezultat posle odobrenja potvrde se nikad nije provjeravao (uvek "Retried")

**Pipeline `npm run quality` pokriva:** typecheck → build → node-check → pytest → smoke test. **Ne pokriva:** React logiku, realtime event handling, dictation state machine, confirmation/plan UI interakcije.

**Prijedlog (srednji prioritet):**
1. Dodati **Vitest** (već ima Vite — integracija je trivijalna)
2. Početi sa testovima za najkritičnije module:
   - `src/lib/realtime.ts` — `handleServerEvent`, `setDictationMode`, `cyrillicToLatin` util
   - `src/App.tsx` — dictation trigger/exit logika, confirmation bridge logika
   - `src/lib/realtimeEventRouter.ts` — routing različitih event tipova
3. Dodati `npm run test:frontend` u `quality` pipeline

---

## 3. VISOK: Nema React Error Boundary

**Stanje:** Ako bilo koja komponenta baci grešku prilikom renderovanja, cela aplikacija se ruši (white screen).

**Prijedlog (visok prioritet):** Dodati `ErrorBoundary` wrapper komponentu u `App.tsx`:

```tsx
class ErrorBoundary extends React.Component<{children: ReactNode}, {hasError: boolean}> {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error: Error) {
    // Prikaži fallback UI, loguj grešku
  }
  render() {
    if (this.state.hasError) return <FallbackScreen onRetry={...} />;
    return this.props.children;
  }
}
```

---

## 4. VISOK: Duplirane mape jezika na 4 lokacije

**Stanje:** Istih 5 jezika (`sr-Latn`, `en`, `de`, `es`, `fr`) je definisano na **4 različita mesta**:

| Lokacija | Mapa | Svrha |
|----------|------|-------|
| `electron/ipc_handlers/realtime.cjs:13` | `STT_LANGUAGE_HINTS` | `interface_language` → OpenAI `language` kod |
| `electron/ipc_handlers/realtime.cjs:18` | `LANGUAGE_NAMES` | `interface_language` → prompt ime jezika |
| `src/App.tsx:106` | `DICTATION_TRIGGER_WORDS` | Trigger substring po jeziku |
| `src/App.tsx:75` | `DICTATION_EXIT_PHRASES` | Exit fraze po jeziku |
| `src/components/pixel/SettingsPanel.tsx:15` | `LANGUAGE_OPTIONS` | UI dropdown opcije |
| `src/i18n/locales/*.json` | 5 fajlova | UI prevodi |

**Problem:** Dodavanje 6. jezika zahteva izmjenu na **minimalno 6 mesta** (5 mapa + JSON locale). Lako je zaboraviti jedno.

**Prijedlog (srednji prioritet):** Konsolidovati u **jedan shared config fajl**, npr. `src/shared/languages.ts`:
```ts
export const SUPPORTED_LANGUAGES = [
  { code: "sr-Latn", name: "Srpski (latinica)", sttHint: "sr", promptName: "Serbian (Latin script)", triggerWord: "dikt" },
  { code: "en", name: "English", sttHint: "en", promptName: "English", triggerWord: "dictat" },
  // ...
] as const;
```
Electron strana može da uvozi isti fajl (ili njegov CJS ekvivalent, generisan pri build-u).

---

## 5. SREDNJE: Nema reconnect/backoff logike za voice sesiju

**Stanje:** `realtime.ts connect()` pokušava **jednom**. Ako ne uspe — `disconnect()`, korisnik mora **ručno** da klikne "Poveži" ponovo.

**Prijedlog:**
- Dodati exponential backoff retry u `connect()` (1s, 2s, 4s, max 3 pokušaja)
- Prikazati "Pokušavam ponovo... (2/3)" u `onStatus`
- Ako sva 3 pokušaja padnu, prikazati "Nije moguće povezati se. Provjeri API ključ."

---

## 6. SREDNJE: Polling svake 3 sekunde — tri paralelna HTTP zahteva

**Stanje:** `App.tsx` ima `setInterval(pollAll, 3000)` koji šalje **tri odvojena HTTP zahteva**:
1. `listPendingConfirmations()` — potvrde
2. `listEvents(since)` — event bridge
3. `listEvents()` (kao health check) — provera backend-a

**Zašto je ovo loše:**
- 3 zahteva × 20 puta/minut = **60 HTTP zahteva/minut**
- Nema backoff-a — backend ne može da "kaže" frontendu da uspori
- UI polling se nastavlja čak i kad je backend down — nepotrebno opterećenje

**Prijedlog (srednji prioritet):**
1. **Smanjiti interval** sa 3s na 5s ili 10s za UI tok (eventi ne moraju stizati instant)
2. **Dodati exponential backoff** kad backend vrati `5xx` — ne ponavljati odmah
3. **Dugoročno (niži prioritet):** Zameniti polling sa **Server-Sent Events (SSE)** — `EventBus` već postoji na backendu, treba samo dodati `GET /events/stream` sa `StreamingResponse` i `text/event-stream`. Frontend dobija instant notifikacije bez polling-a.

---

## 7. SREDNJE: i18n pokriva samo 8 od 16 komponenti

**Stanje:** i18next je integrisan (`src/i18n/index.ts`) i `interface_language` ga pokreće (`i18n.changeLanguage()`). Ali **samo 8 fajlova** koristi `useTranslation()`:

✅ **Prevedeno:** Sidebar, TopBar, IdleScreen, PixelMockupBoard, Previews, SettingsPanel, Drawer, voiceStateLabel

❌ **Hardkodirano (srpski):**

| Komponenta | Hardkodirane reči (primeri) |
|------------|------------------------------|
| `DictationScreen.tsx` | "DIKTIRANJE", "auto-čuvanje uključeno", "obrađujem...", "Diktirani tekst će se pojaviti ovdje...", "Nastavi diktiranje", "Doradi", "Skrati", "Provjeri pravopis", "Prevedi na engleski", "Više", "Kopiraj tekst", "Obriši sve", "Undo", "Preuzmi kao .txt", "Pošalji agentu", "Otkaži diktiranje" |
| `ConfirmationDialog.tsx` | Sav UI za potvrde |
| `PlansPanel.tsx` | Sav UI za planove |
| `ArtifactPanel.tsx` | "Artifact", toggle dugmad |
| `ActivityTimeline.tsx` | "Aktivnost", "Nema događaja" |
| `MiniComputerWindow.tsx` | Sav UI za mini prozor |
| `CompanionOrb.tsx` | Orb context meni stavke |
| `RickyOrb.tsx` | Orb vizuelni overlay |

**Prijedlog:** Nastaviti i18n rollout (PR-2/PR-3 iz `docs/RICKY_GUI_LOCALIZATION_PLAN.md`). DictationScreen je najvažniji jer je direktno vidljiv korisniku.

---

## 8. SREDNJE: Sync httpx u FastAPI rutama — blokira event loop

**Stanje:** Četiri Python endpointa koriste `httpx.post()` (sinhrono, blokirajuće):

| Fajl | Poziv |
|------|-------|
| `app/api/realtime.py:30` | `httpx.post(OPENAI_REALTIME_URL)` |
| `app/agent/model_client.py:75` | `httpx.post(OpenAI chat completions)` |
| `app/services/exa_client.py:46` | `httpx.post(Exa API)` |
| `app/services/openai_image_client.py:46` | `httpx.post(OpenAI images)` |

FastAPI izvršava sync rute u threadpool-u, pa ovo trenutno radi, ali:
- **Troši threadpool slotove** koji su ograničeni (40 po defaultu)
- **Ne može se koristiti `httpx.AsyncClient` connection pooling** — svaki poziv otvara novu TCP konekciju
- Kad 3 korisnika istovremeno zovu voice + image + chat — threadpool se brzo zasiti

**Prijedlog (srednji prioritet):** Konvertovati rute u `async def` i koristiti `httpx.AsyncClient` sa connection pool-om. Npr.:

```python
# app/core/http.py — shared AsyncClient kao dependency
async def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client

@router.post("/realtime/session")
async def create_realtime_session(body: ..., client: Annotated[httpx.AsyncClient, Depends(get_http_client)]):
    response = await client.post(OPENAI_REALTIME_URL, ...)
```

---

## 9. SREDNJE: `App.tsx` — 771 linija, previše odgovornosti

**Stanje:** `App.tsx` je "god komponenta" koja sadrži:
- Voice session management (+ connect, disconnect, kill-switch)
- Dictation state machine (+ text, rewrite, undo, copy, download, clear, send)
- Confirmation polling + approve/reject/cancel + auto-retry
- Plans state + update step status
- Activity events list + filtering
- Event bridge polling
- Health check polling
- Screen routing (home/dictation/activity/plans/memory/screens/settings)
- Companion orb toggle voice handler
- Keyboard kill-switch (Escape)
- 40+ handler funkcija

**Prijedlog (srednji prioritet):** Izdvojiti logiku u custom hookove:

```ts
// src/hooks/useVoiceSession.ts
export function useVoiceSession() { ... } // voiceState, connect, disconnect, clientRef

// src/hooks/useDictation.ts
export function useDictation() { ... } // dictationText, undo, rewrite, handlers

// src/hooks/useConfirmations.ts
export function useConfirmations() { ... } // pendingConfirmation, approve, reject, poll

// src/hooks/useEventPolling.ts
export function useEventPolling() { ... } // events, health, polling interval

// src/hooks/usePlans.ts
export function usePlans() { ... } // plans, updatePlan, updateStep
```

Svaki hook je izolovan, testabilan (`@testing-library/react-hooks` + Vitest), i `App.tsx` postaje tanki shell od ~100 linija koji samo komponuje hookove.

---

## 10. SREDNJE: Nema validacije API ključa pri startup-u

**Stanje:** Ako `OPENAI_API_KEY` nije podešen:
- Backend se pokreće normalno ✅
- Health check prolazi ✅
- Korisnik klikne "Poveži" → `POST /realtime/session` → **500 Internal Server Error**
- Korisnik vidi: *"Realtime WebRTC call failed: ..."* — nejasna poruka

**Prijedlog (srednji prioritet):**
1. Dodati `GET /health` prošireni odgovor sa `api_key_configured: true/false`
2. Frontend prikazuje **upozorenje** u TopBar-u: *"⚠️ OPENAI_API_KEY nije podešen. Ricky ne može da se poveže."*
3. `handleRealtimeCreateToken` u `realtime.cjs` loguje jasniju grešku kad `settings.openai_api_key` nedostaje

---

## 11. NIŽE: Nema rate limiting-a na backendu

**Stanje:** Backend nema nikakvu zaštitu od prekomernog broja zahteva. Jedina zaštita je `RICKY_LOCAL_TOKEN` (auth), ali autentifikovani frontend može da šalje neograničen broj zahteva.

**Prijedlog (niži prioritet — post-MVP):** Dodati `slowapi` (FastAPI rate limiting middleware):
- `/tools/execute`: 10 req/s (brzo, ali ne beskonačno)
- `/realtime/session`: 1 req/s (skup OpenAI poziv)
- `/health`, `/events`, `/settings`: 50 req/s

---

## 12. NIŽE: DB migracije — ručni `ALTER TABLE` bez framework-a

**Stanje:** `python_backend/app/storage/db.py` koristi `MIGRATIONS` listu sa `ALTER TABLE ADD COLUMN`. Radi za dodavanje kolona, ali ne može:
- Preimenovati kolonu
- Promeniti tip kolone
- Obrisati kolonu
- Kreirati indeks
- Rollback-ovati migraciju

**Prijedlog (niži prioritet — kad broj migracija pređe 10):** Uvesti **Alembic** (standardni SQLAlchemy migration tool). Ne zahteva SQLAlchemy ORM — može se koristiti samo za migracije nad raw SQL-om.

---

## 13. NIŽE: `cyrillicToLatin.ts` pokreće skupa regex pravila na SVAKOM transkriptu

**Stanje:** Svaki user transkript prolazi kroz `cyrillicToLatin()` — čak i kad je već latinica. To je O(n) operacija sa ~30 regex zamena po svakom karakteru.

**Prijedlog (niži prioritet — mikro-optimizacija):** Dodati brzu proveru pre transliteracije:
```ts
function needsTransliteration(text: string): boolean {
  return /[А-Яа-я]/.test(text); // ako nema ćiriličnih karaktera, preskoči
}
```

---

## 14. NIŽE: `data/ricky-db.json` i `data/ricky.sqlite` — zaostavština dual storage-a

**Stanje:** Postoje oba fajla:
- `ricky-db.json` (698 bajtova) — legacy JSON DB, koristi se za thumbnail board
- `ricky.sqlite` (282 KB) — Python SQLite DB, koristi se za sve ostalo

Thumbnail board **još uvek** koristi JSON fajl (`legacyMedia.cjs`), a ne SQLite. Kad se thumbnail migrira u Python, JSON fajl postaje suvišan.

**Prijedlog:** Dodati u backlog — migrirati `thumbnail_*` toolove u Python (poslednji preostali legacy handleri u `main.cjs`) i ukinuti `ricky-db.json`.

---

## 15. NIŽE: `en/de/es/fr` dictation fraze nisu potvrđene od izvornog govornika

**Stanje:** Sve ne-srpske trigger reči i exit fraze su best-effort — napisao ih je Claude Code, **nijedan izvorni govornik ih nije pregledao**. Komentar u kodu to dokumentuje (`agent_reports/2026-07-11_dictation-language-cascade.md`), ali rizik nije prijavljen korisniku.

**Prijedlog:** Pre nego što korisnik aktivno koristi ne-srpski jezik u Dictation Mode-u, native speaker treba da pregleda fraze i potvrdi:
- Da su **prirodne** (da korisnik zaista tako govori)
- Da **ne izazivaju lažne okidače** (da se ne pojavljuju u običnom diktiranom tekstu)

---

## 16. NIŽE: `language: "sr"` — hardcodirani model u `realtime.cjs`

**Stanje:** `model: "gpt-realtime-2"` je hardcodiran u `electron/ipc_handlers/realtime.cjs:95`. Nije konfigurabilan.

**Prijedlog:** Dodati `RICKY_REALTIME_MODEL` env var u `config.py` (kao što već postoji za `OPENAI_API_KEY`) sa defaultom `"gpt-realtime-2"`.

---

## 17. NIŽE: Nedostaje strukturirano logovanje na frontendu

**Stanje:** `console.log`/`console.warn` se koristi u 19 mesta u Electron kodu (uklj. produkcijski `main.cjs`). Nema:
- Log levela (info, warn, error, debug)
- Strukturiranog formata (JSON, vremenske oznake)
- Remote logovanja (nije potrebno za desktop app, ali barem log-to-file)

**Prijedlog:** Dodati jednostavan logger wrapper u `electron/core/logging.cjs` koji u dev modu ispisuje na konzolu, a u produkciji zapisuje u `data/ricky.log`.

---

## 18. NIŽE: `<select>` u SettingsPanel-u nema CSS styling

**Stanje:** Prijavljeno u `agent_reports/2026-07-11_interface-language-stt-hint.md`. `<select>` element ne nasleđuje stilove od `.pixel-settings-field input`.

**Prijedlog:** Dodati jedno CSS pravilo u `11-pixel-shell.css`:
```css
.pixel-settings-field select {
  border: 1px solid rgba(80, 135, 190, 0.24);
  border-radius: 8px;
  outline: 0;
  color: #f6f9ff;
  background: rgba(8, 17, 31, 0.76);
  padding: 10px 12px;
  font-family: inherit;
  font-size: 14px;
  appearance: none;
}
```

---

## Sažetak — prioriteti

| # | Problem | Prioritet | Trud |
|---|---------|-----------|------|
| 1 | `main.cjs` duplirani tool handleri + dual storage bug | 🔴 KRITIČAN | 2-3h |
| 2 | React Error Boundary (white-screen na grešci) | 🔴 VISOK | 30min |
| 3 | Duplirane mape jezika na 4 lokacije | 🟡 VISOK | 1-2h |
| 4 | Nula JS/TS testova | 🟡 VISOK | kontinuirano |
| 5 | Nema reconnect/backoff logike | 🟡 SREDNJE | 1-2h |
| 6 | Polling 3×/s bez backoff-a | 🟡 SREDNJE | 1h |
| 7 | i18n samo 8/16 komponenti | 🟡 SREDNJE | kontinuirano |
| 8 | Sync httpx blokira FastAPI threadpool | 🟡 SREDNJE | 2h |
| 9 | `App.tsx` 771 linija — prevelika komponenta | 🟡 SREDNJE | 3-4h |
| 10 | Nema provere OPENAI_API_KEY pri startup-u | 🟡 SREDNJE | 30min |
| 11 | Nema rate limiting-a | 🔵 NIŽE | 1h |
| 12 | Ručne DB migracije bez Alembic-a | 🔵 NIŽE | 2h |
| 13 | `cyrillicToLatin` na svakom transkriptu | 🔵 NIŽE | 5min |
| 14 | `ricky-db.json` zaostavština | 🔵 NIŽE | kontinuirano |
| 15 | en/de/es/fr fraze nisu native-speaker verified | 🔵 NIŽE | eksterni review |
| 16 | Hardcodiran model `gpt-realtime-2` | 🔵 NIŽE | 15min |
| 17 | Nema strukturiranog logovanja (frontend) | 🔵 NIŽE | 1h |
| 18 | `<select>` CSS nedostaje | 🔵 NIŽE | 5min |

---

## Preporučeni redosled rada (sledeća 2-3 sesije)

1. **Sesija 1 (najveći ROI):** Error Boundary (#2) + OPENAI_API_KEY provera (#10) + model env var (#16) + `<select>` CSS (#18) — ~1.5h, sve su brze pobede
2. **Sesija 2 (tehnički dug):** Uklanjanje legacy handlera iz `main.cjs` (#1) — ~2-3h, rešava AGENTS.md kršenje i dual-store bug
3. **Sesija 3 (kvalitet):** Konsolidacija mapa jezika (#3) + reconnect/backoff (#5) + polling optimizacija (#6) — ~3-4h
4. **Kontinuirano:** JS/TS testovi (#4) + i18n rollout (#7) + `App.tsx` refaktor u hookove (#9)