# Log hygiene audit — B2 (read-only)

**Datum:** 2026-07-08
**Izvršio:** pi (read-only audit, po briefu `docs/PI_TASK_A1_B2_BRIEF.md`)
**Scope:** svi `console.*` / `print(` / `logging.*` / `logger.*` u `electron/**`, `python_backend/app/**`, `src/lib/**`. **Nije diran** `src/App.tsx`, `src/components/*`, `electron/main.cjs`, nijedan `.py`/`.cjs`/`.ts` — ovaj fajl je jedini output.
**Izvor istine:** `docs/SECURITY_DELEGATION_PLAN.md` (B2), `docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md`

---

## Scope i metod

Pregledano:
- `electron/**` — `console.*` u `main.cjs`, `core/window.cjs`, `services/pythonProcess.cjs`. `electron/tools_legacy/powershell/*` — **nema** nikakvih log poziva.
- `python_backend/app/**` — nema `print()`, nema `logger.*` info poziva sa sadržajem; jedino `ActionLogService.log_tool_response` (`app/services/action_log.py:16`) upisuje u **DB** (ne console).
- `src/lib/**` — **nema** `console.*` poziva.
- Backend `SecretRedactionFilter` (`app/core/logging.py`) pokriva samo API ključeve/token (OpenAI/Exa/local_token) — **ne** pokriva PII/transkript/sadržaj.

---

## Tabela nalaza

| fajl:linija | šta se ispisuje | rizik | prijedlog |
|---|---|---|---|
| `electron/core/window.cjs:34` | `[renderer] ${message} (${sourceId}:${line})` — proslijeđuje **bilo šta** što renderer ispiše u svoj console (uključujući transkript/email/screenshot putanju ako renderer ikad to loguje). Aktivno samo pod `RICKY_DEBUG_CONSOLE`. | **Srednje** (dev-only, ali propušta sav renderer output u Electron stdout) | Ostaviti, ali dokumentovati da `RICKY_DEBUG_CONSOLE` ne smije biti setovan u produkciji (vidi Otvorena pitanja O1). |
| `electron/core/window.cjs:37` | `[network-error] ${method} ${url} -> ${error}` — URL može sadržavati query parametre (npr. `?since=...`, confirmation id). Pod `RICKY_DEBUG_CONSOLE`. | **Nisko** | Ostaviti (id/status, ne tijelo). |
| `electron/main.cjs:836` | `console.warn("[faza11] Python backend failed for ${name}, falling back to legacy:", error.message)` — ime alata + poruka greške. | **Nisko** | Ostaviti (bez argumenata/payloada). |
| `electron/main.cjs:1798` | `"[kill-switch] TRIGGERED — stopping voice/mic..."` — statička poruka. | **Nisko** | Ostaviti. |
| `electron/main.cjs:1814/1817/1821/1823` | kill-switch registracija acceleraatora + greške. | **Nisko** | Ostaviti. |
| `electron/main.cjs:1843` | `console.error("[python-backend] Failed to start Python backend:", error)` — error objekat. Backend start error ne sadrži tajne (env se ne ispisuje). | **Nisko** | Ostaviti. |
| `electron/main.cjs:1861` | `console.warn("[security-self-test] FAILED:\n" + summary)` — `summary` = lista `check.name: check.detail`. Detalji su imena fajlova/CSP direktive, **ne** tajne (provjereno `securitySelfTest.cjs:28-132`). | **Nisko** | Ostaviti. |
| `electron/main.cjs:1864` | `console.error("[security-self-test] Could not run self-test:", error)` | **Nisko** | Ostaviti. |
| `electron/main.cjs:1883` | `console.warn("[companion] Could not create companion orb:", error)` | **Nisko** | Ostaviti. |
| `electron/services/pythonProcess.cjs:66/73/97/145/200/248` | `[python-backend] Starting: ${cmd} ${args}` / `Ready at ${baseUrl}` / error poruke. Komanda i args **ne** sadrže tajne (tajne idu preko `env`, ne args — `pythonProcess.cjs:103-109`). `baseUrl` je `127.0.0.1:port`. | **Nisko** | Ostaviti. |
| `electron/services/pythonProcess.cjs:112-118` | `child.stdout`/`child.stderr` se prosljeđuju u Electron `process.stdout`/`process.stderr` (prefix `[python-backend]`). Ovo proslijeđuje **sav** Python backend stdout/stderr — uključujući uvicorn access log i eventualne Python traceback-ove. | **Srednje** — vidi O2. | Ostaviti, ali provjeriti šta backend ispisuje (vidi O2). |
| `python_backend/app/services/action_log.py:23-25` | `ActionLogService.log_tool_response` upisuje `input_payload=request.model_dump()` i `output_payload=response.model_dump()` u SQLite (`tool_runs` tabelu). Ovo **nije console log**, ali jeste audit log sa **punim argumentima i rezultatom** alata (uklj. `computer_type_text` tekst, email body ako se doda, screenshot putanja). | **Visoko** (DB audit log sa punim payloadom) | Nije u B2 domeni (popravka) — vidi Preporuka. Relevantno za B3 (DB enkripcija). |
| `python_backend/app/tools/system/screenshot.py:58/65` | `content: str(screenshot_path)` — samo **putanja** do PNG-a, ne base64 sadržaj. | **Nisko** | Ostaviti (putanja, ne pikseli). |
| `python_backend/app/main.py:46` | `configure_logging(secrets=[openai_api_key, local_token, exa_api_key])` — tajne se **ne** ispisuju, već registruju za redakciju. | **Nisko** (pozitivno) | Ostaviti. |

### Šta NIJE nađeno (potvrda)
- **Nema** ispisivanja cijelog `transcript` ni u `electron/**` ni u `python_backend/app/**` ni u `src/lib/**`.
- **Nema** ispisivanja `arguments`/`args`/`payload`/`content` u console nigdje (legacy `computerTypeText`/`computerClick` itd. u `tools_legacy/powershell/*` nemaju nikakvih logova).
- **Nema** base64 screenshot sadržaja u logovima (screenshot vraća samo putanju, `screenshot.py:58`).
- **Nema** `print()` poziva u `python_backend/app/**`.
- `src/lib/realtime.ts` ima `sanitizeToolResult` (`realtime.ts:~445`) koji skraćuje `artifact.content` >1200 znakova prije slanja modelu — ali to ide u **model**, ne u log; pozitivno sporedno.

---

## Zaključak

Console logovi u `electron/**` su **uglavnom čisti** — ispisuju statične poruke, imena alata, putanje, id-eve i error.message. **Nijedan console log ne ispisuje pun transkript, screenshot base64, email body ili tajne.** Tajne (API ključevi/token) dodatno štiti `SecretRedactionFilter` u Python logovanju.

Dvije stvarne površine rizika:
1. **`RICKY_DEBUG_CONSOLE`** (`window.cjs:33`) uključuje proslijeđivanje **svog** renderer console outputa i network-error URL-ova u Electron stdout. Ako renderer ikad loguje osjetljiv sadržaj (što treba zasebno auditirati u `src/App.tsx`/`components` — Codex domen), onda i Electron logovi. Dev-only, ali ne smije biti setovan u produkciji.
2. **`pythonProcess.cjs:112-118`** prosljeđuje sav Python backend stdout/stderr u Electron log. Backend sam po sebi ne ispisuje PII (samo uvicorn access log = method+path+status, ne body), ali ako se ikad doda `print()`/`logger.info(payload)` u backend, automatski završi u Electron logu bez redakcije.

Najozbiljniji nalaz je **van console logova**: `ActionLogService` (`action_log.py:23-25`) upisuje **puni `input_payload` i `output_payload`** svakog alata u SQLite DB. Ovo uključuje tekst koji se kuca (`computer_type_text`), argumente klikova, i buduće email payloade. DB nije "log" u klasičnom smislu, ali jeste perzistentni audit zapis sa korisničkim sadržajem — direktno relevantno za **B3 (DB enkripcija / 0600 permisije)**, ne B2 popravku.

---

## Otvorena pitanja

**O1 — `RICKY_DEBUG_CONSOLE` u produkciji.** Da li packaging/startup garantuje da `RICKY_DEBUG_CONSOLE` nije setovan u produkciji? Nije provjereno u ovom auditu (izvan domene — diralo bi `main.cjs`/`env.cjs`). *Preporuka:* Claude provjeri `electron/core/env.cjs` i packaging config da env varijabla ne curi u produkciju.

**O2 — Backend stdout proslijeđivanje.** `pythonProcess.cjs:112-118` prosljeđuje sav backend stdout/stderr. Danas backend ne ispisuje PII, ali ne postoji filter na Electron strani. Ako Claude/privremeni debug `print()` uđe u backend, završi u logu. *Otvoreno pitanje:* da li dodati crnu listu paterna na proslijeđeni output? Niski prioritet.

**O3 — `ActionLogService` payload u DB.** Ovo je najveća perzistentna površina korisničkog sadržaja. Nije B2 (console log), ali je logično povezano sa B3. Treba odlučiti: (a) maskirati osjetljiva polja u `input_payload`/`output_payload` prije upisa u DB, ili (b) osloniti se na DB enkripciju (B3) i 0600 permisije. *Preporuka za Claude:* kombinacija — maskirati očigledno osjetljiva polja (text/body/transcript) u audit logu **i** enkriptovati DB (B3).

---

## Preporuka za Claude

1. **B2 (console logovi) — nema hitnih popravki.** Svi console logovi su čisti (statične poruke/id/status/error.message). Nema ispisivanja transkripta/screenshot/email/tajni u console.
2. **O1:** provjeriti da `RICKY_DEBUG_CONSOLE` ne curi u produkciju (`env.cjs`/packaging) — mali zadatak, u Claude domenu (`electron/core/*`).
3. **O3 (`ActionLogService`):** najvažniji nalaz — puni payload u DB. Obraditi unutar **B3** (DB enkripcija) ili zasebnog maskiranja u `action_log.py`. To dira `python_backend/app/services/action_log.py` i `app/schemas/tool.py` → **Claude** domen (nedelegabilno, dira storage sloj).
4. **O2:** niski prioritet — eventualno dodati redakciju na proslijeđeni backend stdout u `pythonProcess.cjs` (Claude domen, ali ne hitno).

Izvještaj gotov — čeka Claude verifikaciju. Nijedan fajl koda nije diran (osim `package.json` za A1, vidi zasebno).
