# Sigurnosna gap-analiza i plan implementacije

**Datum:** 2026-07-07
**Autor:** Claude Code (na osnovu Fable-5 + Codex konsultacije, unakrsno provjereno sa stvarnim kodom)
**Metod:** Pročitan stvarni sigurnosni kod (ne naslijepo). Fajlovi pregledani: `electron/core/secureWebPreferences.cjs`, `electron/core/securitySelfTest.cjs`, `electron/preload.cjs`, `python_backend/app/core/{auth,config,logging,path_sandbox,security_self_test}.py`, `python_backend/app/agent/{permission_engine,tool_executor,tool_registry,prompt_builder}.py`, `python_backend/app/main.py`, `index.html`, `pyproject.toml`, `package.json`.

> **Namjena:** Ovo je živi dokument. Svaka Fable/Codex preporuka je unakrsno provjerena sa stanjem u repou da NE bismo implementirali ono što već postoji. Radi se korak po korak, faza po faza, ne veliki rewrite.

---

## Executive summary

**Sigurnosna pozicija ovog projekta je već iznad prosjeka za ovu klasu aplikacija.** Fable je savjetovao naslijepo i pretpostavio da mnoge stvari nisu urađene — a jesu. Konkretno, već je čvrsto riješeno: IPC auth token, loopback binding, Electron sandbox/contextIsolation, allowlisted preload surface, whitelist tool katalog (nema generičkog `exec`), risk/confirmation gate sa payload-hash i tool-name vezivanjem, active-window provjera, fail-closed self-test, log redakcija tajni.

**Prave, potvrđene rupe** (redom po prioritetu, detalji u tabeli i planu ispod):

1. **Runtime schema validacija argumenata alata NE postoji** — schema se šalje modelu ali se ne enforce-uje na backendu.
2. **Prompt injection tretman minimalan** — sadržaj ekrana/tool rezultata ide modelu kao sirovi tekst, bez "ovo su podaci, ne komande" delimitera i bez auto risk-eskalacije.
3. **CSP nedostaje** (ni u `index.html` ni preko `onHeadersReceived`).
4. **Supply chain**: nema hash-pinning locka za Python (`pyproject.toml` bez `uv.lock`/hash), nema `npm ci` u build skriptama.
5. **API ključevi u plaintext** `.env.local` — nema OS keyring / `safeStorage`.
6. **Nema globalnog kill-switch hotkey-a** (postoji in-app Stop, ali ne globalni).
7. **TOCTOU za fajlove** — `path_sandbox` postoji ali se ne poziva; nijedan tool još ne prima korisničku/model putanju (nizak trenutni rizik, ali gap prije Document Engine faze).
8. **Baza nije enkriptovana** (SQLite plaintext); **clipboard/screenshot preview** tek djelimično.

---

## Gap-analiza: Fable/Codex stavka → stvarno stanje

Legenda statusa: ✅ URAĐENO · 🟡 DJELIMIČNO · ❌ RUPA

| # | Fable/Codex stavka | Status | Dokaz / nalaz |
|---|--------------------|--------|---------------|
| S1 | Whitelist katalog akcija (nema generičkog exec) | ✅ | `tool_registry.py` — model bira iz fiksnog `ToolRegistry`; nema `exec` endpointa. |
| S2 | **Runtime validacija parametara (JSON schema)** | ✅ | **URAĐENO (FAZA S-1, 2026-07-07).** `tool_executor.execute()` sad zove `validate_tool_arguments(input_schema, arguments)` (`app/agent/arg_validation.py`) prije handlera; fail na `INVALID_ARGUMENTS`, handler se ne poziva. Fail-closed na neispravnu schemu. Testovi: `tests/test_arg_validation.py`. Vidi `agent_reports/2026-07-07_faza-s1-schema-validation.md`. |
| S3 | IPC auth token | ✅ | `auth.py` `require_local_token` kao global FastAPI dependency (`main.py:51`); token iz `RICKY_LOCAL_TOKEN`. |
| S4 | Bind samo na 127.0.0.1 | ✅ | `config.py:49` default `127.0.0.1`; self-test `backend_host_is_loopback`. |
| S5 | Odbij requeste bez tokena (uklj. health) | ✅ | Global dependency pokriva sve rute uključujući `/health`, `/security/self-test`. |
| S6 | Auth token van pojasa (env, ne u kodu) | ✅ | Prenosi se preko `RICKY_LOCAL_TOKEN` env-a kad Electron spawn-uje backend. |
| S7 | **Prompt injection: sadržaj kao podaci, ne komande** | ✅ | **URAĐENO (FAZA S-2, 2026-07-07).** SYSTEM_PROMPT sad ima eksplicitno pravilo; eksterni tool rezultati se umotavaju u `<untrusted_content>` delimitere (`prompt_builder.wrap_untrusted_content`, primijenjeno u `runtime.py`); breakout (ugniježđeni closing tag) se neutralizuje. |
| S8 | **Auto risk-eskalacija nakon čitanja eksternog sadržaja** | ✅ | **URAĐENO (FAZA S-2), oba puta pokrivena od 2026-07-10.** `reads_external_content` flag na alatkama; `permission_engine.check_permission` eskalira svaku akcijsku alatku (medium+/computer_mode) na obaveznu potvrdu nakon čitanja eksternog sadržaja. Autonomous `/agent/message` put (`runtime.py`) prati `external_content_seen` od početka. **Glasovni Realtime put ovo NIJE radio do 2026-07-10** — `handleToolsExecute` (main.cjs) nikad nije prosljeđivao flag, pa eskalacija nije mogla trigerovati za glasom pokrenute tool pozive (primarni interakcijski put aplikacije). Popravljeno: `realtime.ts` sad prati `externalContentSeen` po glasovnoj sesiji (konzervativniji reset od runtime.py-jevog per-poruka) i prosljeđuje ga kroz `main.cjs` do backend-a. Vidi `agent_reports/2026-07-10_s2-voice-path-fix.md`. |
| S9 | Human-in-the-loop između čitanja i akcije | ✅ | **URAĐENO (FAZA S-2).** Read→act lanac je sad prekinut auto-eskalacijom (S8). Autonomni runtime nema `confirmation_id` → akcija blokirana. Red-team test to dokazuje. |
| S10 | Confirmation vezan za tool + payload | ✅ | `permission_engine.py:162-176` — provjerava `tool_name` i `payload_hash` (anti-swap). Odličan. |
| S11 | Confirmation timeout | ✅ | `check_permission` → `is_expired`. |
| S12 | Nikad glasovna potvrda za high-risk | 🟡 | Treba potvrditi u realtime/voice sloju da "da/pokreni" ne može odobriti high-risk bez klika. Provjeriti `src/lib/realtime.ts`. |
| S13 | Electron contextIsolation/nodeIntegration/sandbox | ✅ | `secureWebPreferences.cjs` — sve tri + `webSecurity`, `allowRunningInsecureContent:false`; self-test enforce. |
| S14 | Allowlisted preload (nema generičkog invoke) | ✅ | `preload.cjs` — svaka funkcija = jedan imenovani kanal; self-test skenira protiv generic passthrough. |
| S15 | **CSP (blokira inline script/eval)** | ✅ | **URAĐENO (FAZA S-3, 2026-07-07).** Build-only Vite plugin (`vite.config.ts`) ubacuje strogi CSP `<meta>` u prod `dist/index.html` (`script-src 'self' 'wasm-unsafe-eval'`, bez unsafe-inline/eval; `connect-src` samo OpenAI; `object-src 'none'`). Meta jer prod ide preko `file://` (onHeadersReceived ne okida). Self-test `content_security_policy` gate-uje u packaged buildu. Dev nedirnut. |
| S16 | Main proces validira svaki IPC poziv | 🟡 | Kanali su imenovani; treba provjeriti da svaki handler u `main.cjs` validira payload (ne vjeruje rendereru). |
| S17 | **Supply chain: lockfile + hash pinning** | ❌/🟡 | `package-lock.json` postoji (✅), ali nema `npm ci` u skriptama; Python `pyproject.toml` bez hash-pinned locka (`uv.lock`/`requirements.txt --require-hashes`). |
| S18 | `--ignore-scripts` / npm audit | ❌ | Nije konfigurisano. |
| S19 | Network egress allowlist | ❌ | Nema eksplicitne liste dozvoljenih domena na nivou aplikacije. |
| S20 | Named pipe umjesto TCP | 🟡 | TCP 127.0.0.1 + token (prihvatljiv minimum). Named pipe je "nice-to-have", ne blokira. |
| S21 | **API ključevi u OS keyring, ne plaintext** | ❌ | `config.py` čita iz `.env.local` (plaintext na disku). Nema `safeStorage`/DPAPI. |
| S22 | Enkripcija baze (SQLCipher/file-level) | 🟡 | **DJELIMIČNO (B3/O3, 2026-07-08).** `action_log` sad **redaktuje** osjetljiv payload (text/body/content/transcript/token…→`[REDACTED]`) prije upisa u `tool_runs` — plaintext-content leak zatvoren cross-platform. DB fajl dobija `0600` (pun na POSIX; Windows treba ACL). Puna enkripcija (SQLCipher) + Windows ACL ostaju follow-up. Report: `agent_reports/2026-07-08_faza-b3-payload-redaction.md`. |
| S23 | Log hygiene (nema punog transkripta/base64 u logovima) | 🟡 | `logging.py` redaktuje TAJNE (ključeve, token), ali ne PII/transkript/screenshot. Treba audit `console.log`/`logger` poziva. |
| S24 | Screenshot preview prije slanja modelu | 🟡 | Postoji artifact panel; treba potvrditi da se capture PRIKAZUJE prije slanja i da se aktivni prozor šalje umjesto cijelog ekrana. |
| S25 | Privacy blacklist prozora (banking/pass mgr) | 🟡 | `DEFAULT_BLOCKED_APPS` blokira type/click u osjetljive procese, ALI screenshot/capture nema blacklist prozora; toast 2FA notifikacije nisu pokrivene. |
| S26 | Clipboard eksplicitni read, ne background polling | ❓ | Provjeriti postoji li clipboard tool i da nije pasivni polling. (Trenutno nema clipboard toola u registry — ako se doda, mora biti on-demand.) |
| S27 | Kucanje samo iz potvrđenog nacrta, ne direktno iz govora | 🟡 | `computer_type_text` traži confirmation; potvrditi da tekst ide iz nacrta, ne live transkripta. |
| S28 | **TOCTOU: fokus prozora + fajl putanja** | 🟡/❌ | Fokus: `check_active_window` provjerava proces prije izvršenja (dobro), ali postoji prozor između confirmation i exec-a. Fajl: `path_sandbox.resolve_within_roots` postoji ali se NE poziva (nijedan tool još ne prima putanju). |
| S29 | Fail-closed defaulti (Computer Mode OFF na startu, mic timeout) | ✅ | **URAĐENO (FAZA S-4, 2026-07-07).** Computer Mode: `currentMode="display"` na svakom startu, bez perzistencije na disk (potvrđeno). Mic idle timeout 5 min u `realtime.ts` (reset na svaki server event / text send, auto-disconnect na isteku). |
| S30 | Rate limit na confirm dugme (200-300ms) | ✅ | **URAĐENO (FAZA S-4).** `ConfirmationDialog` approve dugme neaktivno prvih 250ms nakon pojave dijaloga (`armed` state) — spriječava automatizovan/slučajan klik kroz potvrdu. |
| S31 | Potpisani auto-update | ❌/N/A | Nema auto-update mehanizma (FAZA 19 packaging). Ako se doda — potpisivanje obavezno. |
| S32 | **Red-team test set (prompt injection payloadi)** | 🟡 | **POČETO (FAZA S-9, 2026-07-07).** `tests/test_security_redteam.py` — 8 testova: delimiter breakout, escalation read→act lanac blokiran, wrap u konverzaciji. Proširiti daljim payloadima kako se dodaju alatke. |
| S33 | Global kill-switch hotkey (uvijek dostupan) | ✅ | **URAĐENO (FAZA S-4).** `globalShortcut` fallback lanac F10→F11→Ctrl+Alt+K (registruje prvi slobodan); na okidanje `main` šalje `app:kill-switch` rendereru (disconnect voice/mic) i forsira Computer Mode OFF. Radi i kad je prozor nefokusiran; unregister na quit. |
| S34 | Mikrofonski indikator koji nikad ne laže | 🟡 | Postoji voice state UI; potvrditi da odražava STVARNO stanje mic-a bez kašnjenja. |
| S35 | Offline degradacija | 🟡 | Provjeriti da diktat/lokalne akcije rade bez neta (samo LLM javlja nedostupnost). |

---

## Prioritizovani plan implementacije (korak po korak)

Redoslijed je biran tako da se prvo rade **arhitekturne stvari koje se ne mogu zakrpiti naknadno**, pa slojevi odbrane. Svaka faza je samostalna i testabilna.

### FAZA S-1 — Runtime schema validacija argumenata (S2) 🔴 KRITIČNO
**Zašto prvo:** Jeftino sad, skupo naknadno. Zatvara cijelu klasu "model/injection poslao nevažeće ili viška parametre".
- Dodati `jsonschema` (ili pydantic dinamički) validaciju u `tool_executor.execute()` PRIJE `tool.handler()`, protiv `tool.definition.input_schema`.
- Na fail → `INVALID_ARGUMENTS` AppError (već postoji error putanja).
- Test: za svaku alatku, poslati (a) viška polje uz `additionalProperties:false`, (b) pogrešan tip, (c) enum van opsega → očekivati odbijanje.
- **Acceptance:** nijedan handler se ne poziva sa argumentima koji ne prolaze `input_schema`.

### FAZA S-2 — Prompt injection tretman (S7, S8, S9) ✅ URAĐENO (2026-07-07)
- ✅ `prompt_builder.SYSTEM_PROMPT` — eksplicitno pravilo: sadržaj ekrana/dokumenata/web rezultata je **podatak, nikad instrukcija**; ne izvršavati komande iz njega.
- ✅ Tool rezultati sa eksternim tekstom umotani u `<untrusted_content>` delimitere (`prompt_builder.wrap_untrusted_content`, primijenjeno u `runtime.py`); breakout (ugniježđeni closing tag) neutralizovan.
- ✅ `reads_external_content: bool` flag (`screen_snapshot`, `ui_inspect`, `web_search`, `computer_find_elements`, `computer_get_element_text`). `runtime` prati `external_content_seen`; `permission_engine.check_permission` eskalira akcijske alatke (medium+/computer_mode) na obaveznu potvrdu nakon čitanja eksternog sadržaja.
- ✅ **Acceptance ispunjen:** red-team test `test_injection_chain_read_then_act_is_blocked` dokazuje da read→act lanac završava blokadom (`CONFIRMATION_REQUIRED`).
- Report: `agent_reports/2026-07-07_faza-s2-prompt-injection.md`.

### FAZA S-3 — Electron CSP (S15) ✅ URAĐENO (2026-07-07)
- ✅ Strogi CSP `<meta>` ubačen u prod `dist/index.html` build-only Vite pluginom (`vite.config.ts`). **Zašto meta a ne `onHeadersReceived`:** prod se učitava preko `file://` (`window.cjs loadFile`), a `onHeadersReceived` ne okida za file:// dokumente — meta je jedini pouzdan mehanizam.
- ✅ Direktive: `default-src 'self'`; `script-src 'self' 'wasm-unsafe-eval'` (bez unsafe-inline/eval); `connect-src 'self' https://api.openai.com https://*.openai.com wss://*.openai.com`; `object-src 'none'`; `base-uri 'self'`; `frame-src 'none'`; `form-action 'none'`. `connect-src` je uzak jer je jedini eksterni egress renderera OpenAI Realtime SDP.
- ✅ Self-test provjera `content_security_policy` (`securitySelfTest.cjs`) — u packaged buildu čita `dist/index.html` i potvrđuje CSP meta + da `script-src` nema unsafe. Fail-closed u prod.
- ✅ Dev workflow netaknut (CSP samo u buildu).
- ⚠️ **Treba vizuelni smoke test u packaged buildu:** glasovni WebRTC poziv i mermaid/katex render dijagrama. Ako mermaid pukne uz `'wasm-unsafe-eval'`, dodati `'unsafe-eval'` (dokumentovani tradeoff) ili predkompajlirati dijagrame.
- Report: `agent_reports/2026-07-07_faza-s3-csp.md`.

### FAZA S-4 — Fail-closed defaulti + kill switch (S29, S33, S30) ✅ URAĐENO (2026-07-07)
- ✅ Computer Mode uvijek OFF na startu (`currentMode="display"`, bez disk perzistencije).
- ✅ Mic idle timeout 5 min (`realtime.ts`, reset na aktivnost, auto-disconnect).
- ✅ `globalShortcut` kill-switch, fallback lanac F10→F11→Ctrl+Alt+K; gasi glas/mic (IPC `app:kill-switch` → renderer disconnect) + Computer Mode OFF; radi nefokusiran.
- ✅ Rate limit: confirm dugme neaktivno prvih 250ms (`armed` state).
- ⚠️ **Vizuelni smoke test:** pritisnuti hotkey tokom aktivne glasovne sesije i potvrditi da se mic ugasi (indikator + `getUserMedia` track stopped). Report: `agent_reports/2026-07-07_faza-s4-failclosed-killswitch.md`.

### FAZA S-5 — Supply chain (S17, S18) 🟠
- Python: preći na `uv.lock` ili `pip-compile --generate-hashes`; `pip install --require-hashes` u build/packaging.
- Node: `npm ci` u svim build skriptama (`package.json`, `ricky_backend.spec` pipeline); razmotriti `--ignore-scripts`.
- Dodati `npm audit` / `pip-audit` korak.

### FAZA S-6 — Skladištenje tajni i podataka (S21, S22, S23) 🟡
- API ključevi: Electron `safeStorage` (DPAPI na Windowsu) umjesto `.env.local` plaintext; backend ih dobija preko env-a pri spawn-u (već tako za token).
- Baza: SQLCipher ili barem file permisije 0600 + razmotriti enkripciju osjetljivih polja.
- Log audit: proći sve `logger`/`console.log` da ne ispisuju transkript/screenshot/email sadržaj.

### FAZA S-7 — TOCTOU i capture privatnost (S28, S24, S25) 🟡
- Kad se doda prvi tool koji prima putanju → obavezno `path_sandbox.resolve_within_roots` + re-verifikacija u trenutku exec-a.
- Screenshot: preview prije slanja + slanje aktivnog prozora umjesto cijelog ekrana + blacklist prozora za capture (banking/pass mgr) + provjera notifikacijskog sloja (2FA toast).

### FAZA S-8 — Egress allowlist + named pipe (S19, S20) 🟢 (niži prioritet)
- Aplikativni allowlist domena; opciono named pipe umjesto TCP.

### FAZA S-9 (paralelno sa S-1/S-2) — Red-team test set (S32) 🟡 POČETO (2026-07-07)
- ✅ `python_backend/tests/test_security_redteam.py` — 8 testova: SYSTEM_PROMPT pravilo, delimiter wrapping + breakout neutralizacija, permission eskalacija (unit), read→act lanac blokiran (integracija kroz agent runtime), wrap u perzistiranoj konverzaciji.
- Follow-up: proširivati novim payloadima kako se dodaju alatke (naročito prije Document Engine / novih akcijskih alatki).

---

## Šta NE raditi (Fable saglasan, potvrđeno)
- Proaktivne sugestije ("primijetio sam...") — creepy, troši API.
- Autonomno višekorak izvršavanje bez potvrde po koraku — v3, ne sad.
- Integracije sa 50 servisa — samo email/kalendar/fajlovi.

---

## Sljedeći korak
Predlažem da krenemo od **FAZE S-1 (runtime schema validacija)** jer je najjeftinija-sad-najskuplja-naknadno i čist, izolovan zadatak sa jasnim testom. Prije koda: `gitnexus_impact` na `tool_executor.execute` da se vidi blast radius. Čekam tvoju potvrdu koju fazu prvo.
