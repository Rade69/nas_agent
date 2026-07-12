# RileyJarvis Windows Hybrid ("Nas-agent") — pregled projekta

**Datum:** 2026-07-12
**Izradio:** Claude Code (Anthropic, model Sonnet 5) — direktnim čitanjem izvornog koda ovog repozitorija (`python_backend/`, `electron/`, `src/`, `docs/`), ne na osnovu sažetaka ili tuđih opisa. Gdje god je moguće, tvrdnje niže su potkrijepljene tačnim putanjama fajlova; nesigurne/neprovjerene stvari su eksplicitno tako označene.

> Ovaj dokument je pisan kao odgovor na potrebu za jasnim, provjerljivim pregledom projekta — ne kao marketinški materijal. Sadrži i ono što nije završeno.

---

## 1. Šta je ovo

RileyJarvis Windows Hybrid je desktop AI companion aplikacija za Windows — glasom vođen asistent koji radi kroz Electron prozor, sa Python backend-om koji nosi poslovnu logiku, i OpenAI Realtime API-jem kao primarnim glasovnim pipeline-om. Cilj migracije (u toku od 2026-07-04) je premjestiti sve što je originalno bilo u `electron/main.cjs` (PowerShell automatizacija, storage, AI integracije) u odvojeni Python backend, uz zadržavanje Electron/React sloja isključivo kao UI + IPC most.

Projekat prati fazni migracioni plan (`docs/MIGRATION_PLAN.md`, jedini izvor istine za status faza) — **sve numerisane faze 0-19 su završene**, ostatak rada je van numerisanog plana: Security Gate 1/2 (produkcijski hardening), GUI lokalizacija (u toku), i backlog stavke identifikovane kroz kontinuiran rad i preglede.

---

## 2. Arhitektura

```text
React UI  →  Electron (tanak shell/IPC)  →  Python backend (FastAPI)  →  SQLite
                    ↑
                    └── OpenAI Realtime API (WebRTC, direktno iz renderer-a)
```

### 2.1 Slojevi i njihove odgovornosti

| Sloj | Fajlovi | Odgovornost |
|---|---|---|
| **React renderer** | `src/` | Cijeli UI. Voice-first "pixel" dashboard dizajn — dashboard prikazuje sve sekcije odjednom (Spreman/Diktiranje, Potvrda, Aktivnost, Planovi), ne single-screen navigaciju. |
| **Electron main proces** | `electron/main.cjs`, `electron/core/*.cjs`, `electron/ipc_handlers/*.cjs` | **Isključivo** app shell, IPC allowlist, Python process manager. Arhitektonsko pravilo (`AGENTS.md`, `CLAUDE.md`): nova poslovna logika se **ne** dodaje ovdje — samo tanka IPC prosljeđivanja ka Python backend-u. |
| **Python backend** | `python_backend/app/` (FastAPI) | Agent runtime, tool registry, permission/risk engine, storage (SQLite), AI integracije (OpenAI Chat Completions, image gen, Exa web search), confirmations/plans state mašina. |
| **SQLite** | `data/ricky.sqlite` | `settings`, `confirmations`, `plans`, `plan_steps`, `tool_runs` (action log), `activity_events`, `agent_conversations`/`agent_messages`, `notes`, `records`, `artifacts`. |
| **OpenAI Realtime (WebRTC)** | `src/lib/realtime.ts` | Jedini audio pipeline (mikrofon, VAD, STT, TTS) — namjerno **direktno u rendereru**, ne kroz Python. Arhitektonska odluka dokumentovana u `docs/ARCHITECTURE_VOICE_FIRST_REVISED.md`: Python ne preuzima mikrofon jer bi to unijelo dodatnu latenciju u glasovni put bez jasne koristi. |

### 2.2 Zašto baš ovako (ključne odluke)

- **Voice pipeline ostaje u rendereru, ne u Python-u.** Ovo je eksplicitno "hard rule" u `MIGRATION_PLAN.md` — jedna od stvari koje se namjerno NE migriraju, jer bi Python audio pipeline (mikrofon/VAD/STT/TTS) uveo nepotrebnu latenciju i kompleksnost bez arhitektonske dobiti.
- **Electron je "glup" po dizajnu.** `electron/main.cjs` trenutno ima 772 linije — dio toga su i dalje legacy PowerShell tool handleri (fallback dok se ne dokaže da su Python ekvivalenti pouzdani), ne nova logika. Ovo je poznat, praćen tehnički dug (vidi sekciju 6).
- **Ephemeral credential minting ide kroz Python, ne Electron.** Standardni OpenAI API ključ postoji samo na Python backend strani (`python_backend/app/api/realtime.py`); Electron traži kratkoživući Realtime token od Python-a, nikad ne vidi trajni ključ.
- **Svaki tool poziv (i glasom i tekstom) prolazi kroz isti `ToolExecutor`.** Agent runtime (`app/agent/runtime.py`) nema paralelni put mimo permission/risk sloja — dokazano testovima, ne samo tvrdnja.

---

## 3. Funkcionalnosti

### 3.1 Glasovna interakcija
- Realtime glasovni razgovor (WebRTC, OpenAI Realtime API), sa transkriptom, VoiceState mašinom (idle/listening/transcribing/thinking/speaking/waiting_confirmation/interrupted/muted/error).
- **Companion orb** — zaseban, uvijek-na-vrhu transparentan prozor (`electron/core/companionWindow.cjs`) koji prikazuje VoiceState i služi kao brz ulaz u glasovnu sesiju bez otvaranja glavnog prozora.
- **Kill-switch** — globalni prečac (Escape) i "Stop sve" dugme koji odmah prekidaju glas i sve tool izvršavanja (`POST /tools/executions/cancel-all`).

### 3.2 Diktiranje (Dictation Mode)
- Glasovni okidač ("dikt" supstring, jezički-svjestan od 2026-07-11) i eksplicitno dugme za ulazak.
- Live transkripcija u editor, sa Cyrillic→Latin transliteracijom (Whisper povremeno vraća ćirilicu usred sesije čak i za srpski-latinica projekat).
- **"Doradi" AI meni** — Formalizuj/Skrati/Provjeri pravopis/Prevedi na engleski, preko namjenskog `POST /text/rewrite` endpointa (plain text-in/text-out, ne prolazi kroz agent/tool-calling petlju).
- Undo, kopiraj, preuzmi kao `.txt`, obriši sve.

### 3.3 Planovi i potvrde (Plans & Confirmations)
- Rizik-svjestan permission model — svaka tool akcija ima `risk` (low/medium/high/critical); high/critical zahtijevaju eksplicitnu korisničku potvrdu prije izvršenja.
- Planovi (višekoračni zadaci) sa statusima (draft/proposed/approved/running/completed/rejected/cancelled), perzistentni u SQLite, ne fajlovi.
- **Confirmation Bridge** — kad glasom zatražen tool vrati `CONFIRMATION_REQUIRED`, aplikacija automatski predlaže potvrdu i, nakon odobrenja, automatski ponovo pokušava originalnu akciju.

### 3.4 Alati (tools)
Tool registry sa jedinstvenim contract-om (`docs/TOOL_CONTRACTS.md`) — bez obzira da li je tool implementiran u Python-u ili (legacy) PowerShell-u, ima isti schema: `risk`, `requires_confirmation`, `requires_computer_mode`, `requires_active_window_match`, `allowed_apps`/`blocked_apps`, `timeout_ms`. Kategorije: beleške/zapisi (notes/records), artifacts (prikaz sadržaja u UI panelu), web pretraga (Exa), generisanje slika (OpenAI Images), screenshot/UI inspect, i **computer-use** (klik/tip/scroll preko koordinata ili UI element targeting-a preko Windows UI Automation).

### 3.5 Postavke i lokalizacija
- Settings panel (`SettingsPanel.tsx`) — korisničko ime (koje agent koristi u razgovoru), jezik diktiranja/interfejsa.
- **i18n infrastruktura** (i18next + react-i18next) — 5 jezika (sr-Latn/en/de/es/fr), pokriva **12 od ~20 komponenti** koje imaju user-facing tekst (vidi sekciju 6 za tačan status).
- Jezik diktiranja pokreće i STT jezički hint (OpenAI Whisper `language` parametar) i agentov preferirani jezik odgovora u sistem promptu.

### 3.6 Ostalo
- Notepad-style beleške i "records" (strukturirani zapisi), artifact panel (prikaz markdown/koda/tabela/mermaid dijagrama/slika), thumbnail board (generisanje/editovanje slika preko OpenAI Images, i dalje na legacy JSON storage-u, ne SQLite — vidi sekciju 6).

---

## 4. Sigurnosni principi

Ovo je sažetak stvarno implementiranih kontrola, ne plana. Izvor istine za produkcijski sigurnosni plan je `docs/SECURITY_HARDENING_PLAN.md`; ovaj pregled je destilacija onoga što je **stvarno u kodu**, provjereno čitanjem.

### 4.1 Permission / risk engine (`python_backend/app/agent/permission_engine.py`)
- Svaki tool ima deklarisan risk nivo (low/medium/high/critical). `critical` alati su onemogućeni po defaultu; `high` zahtijevaju computer mode + eksplicitnu potvrdu; `medium` zavisno od konteksta; `low` prolaze bez potvrde.
- **`confirmation_id` je vezan za `tool_name` + hash payload-a + expiraciju** — ne može se odobriti confirmation za jednu akciju pa "iskoristiti" za drugu.
- **Execution/cancellation state mašina** (`app/agent/cancellation.py`) — svaki tool poziv dobija `execution_id`, može se otkazati u letu preko `POST /tools/executions/{id}/cancel` ili globalno preko "Stop sve".
- **Active window enforcement za computer-use alate** — `DEFAULT_BLOCKED_APPS` (powershell.exe, cmd.exe, regedit.exe, taskmgr.exe, mmc.exe, pwsh.exe, powershell_ise.exe, credentialuibroker.exe, mstsc.exe) blokira klik/tip/scroll dok su ovi procesi aktivni, bez obzira šta model zatraži.

### 4.2 Prompt-injection zaštita (S-2)
- `external_content_seen` flag — kad tool pročita eksterni sadržaj (web stranica, email itd.), sesija se "escalira": naredni high-risk pozivi zahtijevaju potvrdu čak i ako inače ne bi. Flag se prenosi i kroz glasovni put (renderer → Electron → Python), popravljeno nakon što je originalno postojalo samo za tekstualni `/agent/message` put.

### 4.3 Autentifikacija i mrežna izolacija
- Python backend zahtijeva `Authorization: Bearer <token>` na svakom zahtjevu (`app/core/auth.py`). Electron generiše kratkoživući token po sesiji (`crypto.randomBytes(32)`), prosljeđuje ga preko env varijable, nikad ga ne loguje niti perzistira.
- **Poznato ograničenje:** ako backend nije pokrenut preko Electron-a (npr. direktno preko `uvicorn` u dev radu), auth provjera je fail-open. Stvaran, Electron-pokrenut put je jedini koji mora biti siguran, i taj put uvijek postavlja token.
- Nema generic `ipcRenderer.invoke` prolaza u `preload.cjs` — svaka IPC funkcija je eksplicitno imenovana i alistovana (`electron/core/ipc.cjs`).

### 4.4 Fail-closed dizajn
- **Legacy PowerShell fallback je onemogućen po defaultu** (`RICKY_USE_LEGACY_POWERSHELL_TOOLS=0`, provjereno u `electron/core/legacyTools.cjs:58-61`). Kad Python backend padne za tool koji ima Python ekvivalent, aplikacija vraća strukturiranu grešku umjesto tihog fallback-a na JSON storage.
- High-risk alati koji zahtijevaju potvrdu **nikad** ne prolaze kroz legacy fallback čak i kad je legacy eksplicitno uključen — `LEGACY_FAIL_CLOSED_TOOLS` blokira to eksplicitno, jer legacy put ne može verifikovati odobren `confirmation_id`.
- Global kill-switch (S-4) je fail-closed — prekida glas/mikrofon odmah, ne čeka potvrdu od backend-a.
- Security self-test (`GET /security/self-test` + `electron/core/securitySelfTest.cjs`) — u produkcijskom (packaged) buildu, ako self-test ne prođe, aplikacija se gasi **prije** nego što se ijedan prozor otvori (`dialog.showErrorBox` + `app.quit()`).

### 4.5 Log hygiene
- `SecretRedactionFilter` (`python_backend/app/core/logging.py`) — API ključevi i lokalni auth token se zamjenjuju placeholder-om u svakom log zapisu.
- Path sandbox primitivi postoje (`app/core/path_sandbox.py`), ali **nemaju još pozivaoca** — infrastruktura pripremljena za buduće file-tool proširenje, ne aktivno primijenjena.

### 4.6 React nivo
- **Error Boundary** (dodato 2026-07-12, `src/components/ErrorBoundary.tsx`) — greška u bilo kojoj komponenti više ne ruši cijelu aplikaciju u prazan ekran; prikazuje fallback sa opcijom restarta.
- CSP i secure web preferences (`electron/core/secureWebPreferences.cjs`) — `sandbox`/`webSecurity`/`allowRunningInsecureContent` eksplicitno postavljeni, ne oslonjeni na Electron default.

### 4.7 Šta NIJE zatvoreno (transparentno)
- **Legacy PowerShell computer-use alati** (`computer_open_app`, `computer_type_text`, `computer_click`, `computer_scroll` — implementirani direktno u `electron/main.cjs`) rade **bez permission sloja i bez auth tokena**, dok se ne migriraju u Python. Ovo je poznat, dokumentovan rizik (`SECURITY_MODEL.md`), ne previd.
- Security Gate 1 (document privacy modes, CI security checks, rate limiting) i Gate 2 (code signing, produkcijski packaging) nisu zatvoreni — projekat nije spreman za javni/produkcijski release.
- Nema rate limiting-a na backend-u.

---

## 5. Radni tok — multi-agent saradnja

Ovaj repo dijele **dva agenta na istom filesystem-u**: Claude Code (ja) i korisnikov "pi" coding agent. Podjela rada:

- **Claude Code** — arhitektonske odluke, sigurnosno-kritičan kod, pregled i verifikacija pi-jevog rada prije commit-a, pisanje preciznih brief-ova za pi (`docs/PI_TASK_*.md`) kad se posao delegira.
- **pi** — mehanički, jasno ograničen rad po brief-u (npr. i18n key konverzija po utvrđenom obrascu, dodavanje polja po postojećem šablonu).

### 5.1 Disciplina koja se stvarno primjenjuje (ne samo deklariše)

1. **Nikad se ne vjeruje pi-jevom izvještaju na riječ.** Svaki put kad pi završi zadatak, ja čitam stvaran `git diff`, ne samo agent report — u ovoj sesiji je to više puta uhvatilo stvarne probleme (npr. varijabla koja zasjenjuje `t` iz `useTranslation()` hook-a u `PlansPanel.tsx`, obrisan bezbjednosno-relevantan komentar u `ConfirmationDialog.tsx`, duplirani niz umjesto jednog izvora istine).
2. **Isto važi obrnuto — kad pi napiše samostalan "review" izvještaj**, tvrdnje se provjeravaju u kodu prije nego što se prihvate kao tačne. Primjer iz 2026-07-12: pi-jev izvještaj je označio "main.cjs dual storage" kao KRITIČNO i "sync httpx blokira event loop" kao stvaran problem — provjerom koda je utvrđeno da je prvo tačno ali uslovno (samo ako je non-default env flag uključen), a drugo tehnički netačno (FastAPI sync rute se namjerno izvršavaju u threadpool-u, to nije bug).
3. **Verifikacija prije svakog commit-a:** `npm run typecheck`, `npm run build`, `pytest` (236 testova u trenutku pisanja), `node --check` na sve dirane `.cjs` fajlove, GitNexus `detect_changes` impact analiza. Ako GitNexus vrati HIGH/CRITICAL rizik, to se eksplicitno prijavljuje korisniku prije commit-a, uz ručno objašnjenje da li je rizik stvaran ili artefakt grafa (npr. centralni simboli koji dodiruju mnogo nepovezanih procesa).
4. **Agent report za svaki netrivijalan rad** (`agent_reports/YYYY-MM-DD_slug.md`) — šta je urađeno, zašto, kako, šta NIJE dirano, rizici, potreban follow-up. Ovo nije formalnost — koristi se kao stvarna referenca u narednim sesijama.
5. **Nikad se ne commituje bez eksplicitnog zahtjeva korisnika**, čak ni kad je sav posao završen i verifikovan.
6. **Runtime testovi kad je moguće** — ali iskreno priznato kad NIJE moguće (Electron desktop app, nema browser-automation alata u ovom okruženju) umjesto lažnog tvrđenja da je nešto testirano.

### 5.2 Primjer stvarne iteracije (ne teorijske)

Window drag bug (2026-07-12) je dobar primjer metodologije: 6 uzastopnih pokušaja, svaki testiran uživo od korisnika prije sljedeće izmjene, umjesto da se unaprijed "izračuna" ispravno rješenje. Konačan nalaz — Electron-ov `-webkit-app-region` drag/no-drag razrješavanje prati DOM render redoslijed, ne z-index/stacking context, suprotno standardnom CSS ponašanju — nije bio poznat unaprijed, otkriven je isključivo kroz "promijeni → testiraj → izvještaj → prilagodi" ciklus.

---

## 6. Poznata ograničenja i otvorene stavke

Namjerno uključeno, ne izostavljeno — dokument bi bio nepošten bez ovoga.

| Stavka | Status | Napomena |
|---|---|---|
| GUI lokalizacija | PR-1 + PR-2 završeni (12 komponenti), PR-3 nije počet | `DictationScreen`, `PlansPanel`, `ActivityTimeline`, `ConfirmationDialog` sad prevedeni; `MiniComputerWindow`, `CompanionOrb` context meni, `ArtifactPanel`, error/tool labele van onoga što je konvertovano — i dalje hardkodiran srpski. |
| de/es/fr prevodi | Best-effort, **nisu native-speaker potvrđeni** | Eksplicitno označeno u kodu i agent reportovima svaki put — nije prikriveno. |
| JS/TS testovi | **Ne postoje** | `npm run test` pokreće samo `pytest` (236 testova, samo backend). Nema Vitest-a ni bilo kakvog frontend test frameworka. Dva stvarna buga (confirmation bridge petlja, retry provjera) su ranije nađena ručnim pregledom, ne testovima — dokaz da nedostatak testova nije samo teoretski rizik. |
| `electron/main.cjs` veličina | 772 linije | Dio je legacy tool fallback (namjerno zadržan dok se ne dokaže Python zamjena), dio je IPC wiring. Čišćenje mrtvog/dupliranog koda je identifikovan, još ne urađen zadatak. |
| `App.tsx` veličina | 778 linija, ~40 handler funkcija | Kandidat za razdvajanje u custom hooks (`useVoiceSession`, `useDictation`, `useConfirmations` itd.) — nije urađeno, procijenjen kao srednji prioritet, ne hitno. |
| Duplirane jezičke mape | 5 mjesta u kodu | `STT_LANGUAGE_HINTS`, `LANGUAGE_NAMES`, `DICTATION_TRIGGER_WORDS`, `DICTATION_EXIT_PHRASES`, `LANGUAGE_OPTIONS` + 5 JSON locale fajlova — dodavanje 6. jezika trenutno zahtijeva izmjenu na 6 mjesta. Konsolidacija u jedan shared config nije urađena. |
| Cloud-only STT | Lokalni STT (faster-whisper) nije implementiran | Arhitektura isplanirana (`docs/LOCALIZATION_AND_STT_ENGINE_PLAN.md`), namjerno odloženo — dva paralelna STT koda znače duplo održavanje, ne raditi dok ne postoji jasan razlog (offline rad, trošak). |
| Legacy computer-use bez permission sloja | Poznato, dokumentovano | Vidi sekciju 4.7 — najveći preostali sigurnosni gap prije produkcijskog release-a. |
| Polling umjesto push notifikacija | `setInterval` na 3s za events/confirmations | `EventBus` na backend-u već postoji; SSE (`GET /events/stream`) bi eliminisao polling, nije implementirano. |
| Rate limiting | Ne postoji na backend-u | Jedina zaštita je auth token, ne broj zahtjeva. Nisko-prioritetno za desktop app sa jednim korisnikom, ali odsutno. |
| Security Gate 1/2 | Nisu zatvoreni | Projekat nije spreman za javni/produkcijski release — vidi `docs/MIGRATION_PLAN.md` "Security Gates" tabelu. |

---

## 7. Zaključak

Projekat ima stvarnu arhitektonsku disciplinu koja se **provjerava, ne samo deklariše** — jasna podjela slojeva, permission/risk model koji je testovima dokazan da nema zaobilaznih puteva, fail-closed dizajn na više nivoa (legacy tools, kill-switch, security self-test). Multi-agent radni tok (Claude Code + pi) funkcioniše uz eksplicitnu, ponovljivu disciplinu provjere — dokazano više puta u ovoj sesiji da nijedna strana (uključujući mene) ne uzima tvrdnje zdravo za gotovo bez provjere u stvarnom kodu.

Istovremeno, projekat ima realne, imenovane praznine — GUI lokalizacija je na pola puta, frontend nema testove, legacy computer-use put je poznat sigurnosni rizik, i produkcijski gates nisu zatvoreni. Nijedna od ovih stavki nije skrivena ili uljepšana u ovom dokumentu.
