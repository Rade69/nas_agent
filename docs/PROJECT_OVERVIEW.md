# RileyJarvis Windows Hybrid ("Nas-agent") — pregled projekta

**Datum:** 2026-07-13 (ažurirano nakon provjere promjena zaključno sa commitom `13b2a8c`)
**Izradio:** Claude Code (Anthropic, model Sonnet 5); **reviziju 2026-07-13 uradio:** Codex — oba direktnim čitanjem izvornog koda ovog repozitorija (`python_backend/`, `electron/`, `src/`, `docs/`), ne na osnovu sažetaka ili tuđih opisa. Gdje god je moguće, tvrdnje niže su potkrijepljene tačnim putanjama fajlova; nesigurne/neprovjerene stvari su eksplicitno tako označene.

> Ovaj dokument je pisan kao odgovor na potrebu za jasnim, provjerljivim pregledom projekta — ne kao marketinški materijal. Sadrži i ono što nije završeno.

---

## 1. Šta je ovo

RileyJarvis Windows Hybrid je desktop AI companion aplikacija za Windows — glasom vođen asistent koji radi kroz Electron prozor, sa Python backend-om koji nosi poslovnu logiku, i OpenAI Realtime API-jem kao primarnim glasovnim pipeline-om. Cilj migracije (u toku od 2026-07-04) je premjestiti sve što je originalno bilo u `electron/main.cjs` (PowerShell automatizacija, storage, AI integracije) u odvojeni Python backend, uz zadržavanje Electron/React sloja isključivo kao UI + IPC most.

Projekat prati fazni migracioni plan (`docs/MIGRATION_PLAN.md`, jedini izvor istine za status faza) — **sve numerisane faze 0-19 su završene**, ostatak rada je van numerisanog plana: Security Gate 1/2 (produkcijski hardening) i backlog stavke identifikovane kroz kontinuiran rad i preglede. GUI lokalizacija (PR-1/2/3) je završena 2026-07-13 — vidi sekciju 6.

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
- **Glas dugme u TopBar-u je funkcionalno** — više nije vizuelno dugme bez akcije; koristi isti connect/disconnect/stop tok kao glavno mikrofonsko dugme (`src/components/pixel/TopBar.tsx`, `PixelMockupBoard.tsx`).
- **Početni hero prati stvarni VoiceState** — veliki naslov i pomoćni tekst više ne ostaju statično na "Ricky je spreman", nego lokalizovano prikazuju slušanje, obradu, razmišljanje, govor, čekanje potvrde, prekid, utišavanje i grešku (`src/components/pixel/IdleScreen.tsx`).

### 3.2 Diktiranje (Dictation Mode)
- Glasovni okidač ("dikt" supstring, jezički-svjestan od 2026-07-11) i eksplicitno dugme za ulazak.
- Live transkripcija u editor, sa Cyrillic→Latin transliteracijom (Whisper povremeno vraća ćirilicu usred sesije čak i za srpski-latinica projekat).
- **"Doradi" AI meni** — Formalizuj/Skrati/Provjeri pravopis/Prevedi na engleski, preko namjenskog `POST /text/rewrite` endpointa (plain text-in/text-out, ne prolazi kroz agent/tool-calling petlju).
- Undo, kopiraj, preuzmi kao `.txt`, obriši sve.
- Dugme **"Otkaži diktiranje"** sada ima jasno vidljiv danger/outline affordance umjesto da izgleda kao neaktivna sekundarna kontrola (`src/styles/11-pixel-shell.css`).

### 3.3 Planovi i potvrde (Plans & Confirmations)
- Rizik-svjestan permission model — svaka tool akcija ima `risk` (low/medium/high/critical); high/critical zahtijevaju eksplicitnu korisničku potvrdu prije izvršenja.
- Planovi (višekoračni zadaci) sa statusima (draft/proposed/approved/running/completed/rejected/cancelled), perzistentni u SQLite, ne fajlovi.
- **Confirmation Bridge** — kad glasom zatražen tool vrati `CONFIRMATION_REQUIRED`, aplikacija automatski predlaže potvrdu i, nakon odobrenja, automatski ponovo pokušava originalnu akciju.

### 3.4 Alati (tools)
Tool registry sa jedinstvenim contract-om (`docs/TOOL_CONTRACTS.md`) — bez obzira da li je tool implementiran u Python-u ili (legacy) PowerShell-u, ima isti schema: `risk`, `requires_confirmation`, `requires_computer_mode`, `requires_active_window_match`, `allowed_apps`/`blocked_apps`, `timeout_ms`. Kategorije: beleške/zapisi (notes/records), artifacts (prikaz sadržaja u UI panelu), web pretraga (Exa), generisanje slika (OpenAI Images), screenshot/UI inspect, i **computer-use** (klik/tip/scroll preko koordinata ili UI element targeting-a preko Windows UI Automation).

### 3.5 Postavke i lokalizacija
- Settings panel (`SettingsPanel.tsx`) — korisničko ime (koje agent koristi u razgovoru), jezik diktiranja/interfejsa i korisnički definisane brze komande. Brze komande se perzistiraju kroz postojeću SQLite key/value settings infrastrukturu; prazna lista znači da UI koristi ugrađene lokalizovane komande, a neprazna lista se prikazuje i šalje agentu doslovno kako ju je korisnik unio.
- **i18n infrastruktura** (i18next + react-i18next) — 5 jezika (sr-Latn/en/de/es/fr), pokriva približno **16 komponenti** sa user-facing tekstom, uključujući novije screenshot i quick-command ekrane (vidi sekciju 6 za preostale izuzetke).
- Jezik diktiranja pokreće i STT jezički hint (OpenAI Whisper `language` parametar) i agentov preferirani jezik odgovora u sistem promptu.
- Ranijih pet odvojenih jezičkih mapa je konsolidovano u **dva izvora istine**: renderer koristi `src/shared/languages.ts`, a Electron Realtime handler jednu `LANGUAGE_CONFIG` mapu u `electron/ipc_handlers/realtime.cjs`. Dva izvora ostaju namjerno odvojena zbog renderer ESM / Electron CJS granice.

### 3.6 Ostalo
- Notepad-style beleške i "records" (strukturirani zapisi), artifact panel (prikaz markdown/koda/tabela/mermaid dijagrama/slika), thumbnail board (generisanje/editovanje slika preko OpenAI Images, i dalje na legacy JSON storage-u, ne SQLite — vidi sekciju 6).
- **Screenshot galerija i privatnost** — svaki novi screenshot dobija SQLite evidenciju (`screenshots` tabela) i prikazuje se u stvarnoj galeriji umjesto statičnog placeholdera. Galerija razlikuje lokalne snimke od onih poslatih modelu, nudi "Obriši sve", a backend briše i DB redove i PNG fajlove. Podrazumijevana retencija je 30 dana; cleanup se pokreće pri startu backend-a i pri listanju galerije (`ScreenshotService`, `ScreenshotsGallery.tsx`).

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
- **Ispravljeno 2026-07-12 (Security Gate 1 fix):** provjera je sad uvijek fail-closed. Ako backend nije pokrenut preko Electron-a (npr. direktno preko `uvicorn` u dev radu), `get_settings()` sam generiše token po procesu i upisuje ga u gitignored `python_backend/data/dev_local_token.txt` (`app/core/config.py:_resolve_local_token`), umjesto da propušta zahtjeve neautentifikovano. Ranije je taj put bio fail-open — bilo koji lokalni proces, uklj. fetch() sa zlonamjerne web stranice ka `127.0.0.1`, mogao je pozivati toolove bez autentifikacije. Vidi sekciju 7.
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
- ~~Dev-mode auth fail-open~~ **Popravljeno 2026-07-12.** Vidi sekciju 4.3 i sekciju 7.
- ~~S-2 eskalacija ima rupu za "odlazne" low-risk alate~~ **Popravljeno 2026-07-12.** Novo `outbound: bool` polje u `ToolDefinition` (`app/schemas/tool.py`) — `web_search` i `image_generate` su sad označeni `outbound=True`; `permission_engine.py`'s `check_permission()` eskalira svaki outbound tool poslije `external_content_seen`, nezavisno od risk nivoa i nezavisno od `reads_external_content` izuzeća (jedan tool može biti i reader i outbound istovremeno — `web_search` je oba). Vidi sekciju 7.
- **Legacy computer-use — manji rezidualni gap nego što je ranije ovdje pisalo.** `computer_click`/`computer_type_text` (najopasnija kategorija) idu kroz Python PRVO (`PHASE11_DELEGATED_TOOLS`, `electron/main.cjs:193-197`) sa `risk="high"`, `requires_confirmation=True`, `requires_active_window_match=True`, I nikad ne padaju na legacy fallback čak i kad je legacy uključen (`LEGACY_FAIL_CLOSED_TOOLS`, `main.cjs:212-217`) — ovo je najjače zaštićena kategorija u sistemu, ne najslabija. Stvaran, manji gap: `computer_open_app`/`computer_press_key`/`computer_scroll` (medium risk) NISU u `LEGACY_FAIL_CLOSED_TOOLS` — ako Python padne I `RICKY_USE_LEGACY_POWERSHELL_TOOLS=1` je eksplicitno postavljen (default je `0`), ova tri bi prošla kroz legacy PowerShell bez permission provjere.
- Nema JS/TS testova za confirmation flow (frontend, security-kritičan put) — vidi sekciju 6.
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
| GUI lokalizacija | ✅ PR-1 + PR-2 + PR-3 završeni (2026-07-13) | Svi ranije poznati preostali fajlovi (`ArtifactPanel`, `CompanionOrb` — uklj. native Electron tray/context meni u `electron/core/companionWindow.cjs`, `MiniComputerWindow`) sad prevedeni. Runtime nije testiran (agent nema browser-automation pristup) — vidi `agent_reports/2026-07-13_companion-orb-menu-localization.md`. Preostalo: dio error/tool labela van GUI-ja, `formatDate` u `ArtifactPanel.tsx` koristi browser default locale umjesto `interface_language`. |
| de/es/fr prevodi | Best-effort, **nisu native-speaker potvrđeni** | Eksplicitno označeno u kodu i agent reportovima svaki put — nije prikriveno. |
| JS/TS testovi | **Ne postoje** | `npm run test` pokreće samo `pytest`; `pytest --collect-only` je 2026-07-13 prikupio **251 backend test**. Nema Vitest-a ni bilo kakvog frontend test frameworka. Dva stvarna buga (confirmation bridge petlja, retry provjera) su ranije nađena ručnim pregledom, ne testovima — dokaz da nedostatak testova nije samo teoretski rizik. |
| `electron/main.cjs` veličina | 784 linije | Dio je legacy tool fallback (namjerno zadržan dok se ne dokaže Python zamjena), dio je IPC wiring. Čišćenje mrtvog/dupliranog koda je identifikovan, još ne urađen zadatak. |
| `App.tsx` veličina | 735 linija, i dalje sa mnogo handler funkcija | Kandidat za razdvajanje u custom hooks (`useVoiceSession`, `useDictation`, `useConfirmations` itd.) — nije urađeno, procijenjen kao srednji prioritet, ne hitno. |
| Jezička konfiguracija | ✅ Konsolidovana 2026-07-12 | Ranijih pet mapa svedeno je na dva namjerna izvora istine: `src/shared/languages.ts` za renderer i `LANGUAGE_CONFIG` u Electron Realtime handleru. Potpuno dijeljenje jednog fajla nije uvedeno jer bi CJS/ESM most zahtijevao dodatni build korak. |
| Cloud-only STT | Lokalni STT (faster-whisper) nije implementiran | Arhitektura isplanirana (`docs/LOCALIZATION_AND_STT_ENGINE_PLAN.md`), namjerno odloženo — dva paralelna STT koda znače duplo održavanje, ne raditi dok ne postoji jasan razlog (offline rad, trošak). |
| Dev-mode auth fail-open | ✅ Popravljeno 2026-07-12 | Vidi sekciju 4.3 — bio je "jeftin fix" po procjeni, ispalo je veći zahvat jer je skoro cijeli backend test suite (245 testova) implicitno zavisio od fail-open ponašanja; svih 12+ dotaknutih test fajlova prošlo je kroz eksplicitan auth-bypass override, ne kroz oslanjanje na staro ponašanje. |
| S-2 eskalacija: outbound low-risk alati (`image_generate`, `web_search`) | ✅ Popravljeno 2026-07-12 | Vidi sekciju 4.7 — pronađeno eksternim pregledom (FABLE-5, 2026-07-12), potvrđeno u kodu, i zatim popravljeno (`outbound: bool` polje + eskalacija u `permission_engine.py`). |
| Legacy computer-use — rezidualni gap (medium-risk alati) | Poznato, dokumentovano | Vidi sekciju 4.7 — manji obim nego što je ranija verzija ovog dokumenta tvrdila (ispravljeno 2026-07-12, vidi sekciju 7). |
| Polling umjesto push notifikacija | `setInterval` na 3s za events/confirmations | `EventBus` na backend-u već postoji; SSE (`GET /events/stream`) bi eliminisao polling, nije implementirano. |
| Rate limiting | Ne postoji na backend-u | Jedina zaštita je auth token, ne broj zahtjeva. Nisko-prioritetno za desktop app sa jednim korisnikom, ali odsutno. |
| Security Gate 1/2 | Nisu zatvoreni | Projekat nije spreman za javni/produkcijski release — vidi `docs/MIGRATION_PLAN.md` "Security Gates" tabelu. |

---

## 7. Eksterni pregled i ispravke (2026-07-12)

Ovaj dokument je pregledao FABLE-5 (drugi AI model, eksterna recenzija). Sve tvrdnje iz tog pregleda su provjerene direktno u kodu od strane Claude Code (mene) prije nego što su prihvaćene — isti princip koji sekcija 5.1 opisuje za pi-jev rad, primijenjen ovdje na sopstveni dokument i na tuđu recenziju podjednako.

**Rezultat provjere:**

- **Original verzija sekcije 4.7 je sadržala grešku** — tvrdila je da `computer_click`/`computer_type_text` rade "bez permission sloja i bez auth tokena", prepisano iz zastarjelog pasusa u `docs/SECURITY_MODEL.md` koji nije ažuriran nakon FAZE 13/14. Stvarno stanje (provjereno u `electron/main.cjs` i `python_backend/app/agent/tool_catalog/phase13.py`): ova dva alata idu kroz Python prvo, zahtijevaju potvrdu, i fail-closed su čak i na legacy putu — **najjača** zaštita u sistemu, ne najslabija. Ispravljeno.
- **Dvije nove, stvarne praznine potvrđene i dodate** (nisu bile u originalnoj verziji ovog dokumenta): dev-mode auth fail-open (sekcija 4.7) i S-2 eskalacija koja ne pokriva "odlazne" low-risk alate poput `image_generate`/`web_search` (sekcija 4.7).
- **Jedan predlog je već bio implementiran** prije recenzije — min-delay na confirm dugme (`ConfirmationDialog.tsx`, `armed` state, FAZA S-4/S30) — provjereno, potvrđeno, nije ponovljen rad.
- **Jedan spot-check testa** (`test_agent_runtime.py:97-128`, `records_delete` bez potvrde) potvrdio da asertuje tačnu, jaku tvrdnju (`ok is False` + `CONFIRMATION_REQUIRED`), ne slabiju verziju — ne dokazuje da su svih 236 testova jednako strogi, samo da primjer istaknut u sekciji 5.1 drži vodu.

**Ažurirano 2026-07-12 (naknadno, isti dan):** dev auth fail-closed i outbound taint eskalacija su implementirani i testirani — vidi sekciju 4.3 i 4.7. Vitest za confirmation flow ostaje neimplementiran.

### 7.1 Naknadno potvrđene dorade (2026-07-13)

Nakon prvobitnog pregleda direktno su provjereni commitovi i trenutni kod za sljedeće promjene:

- screenshot evidencija, 30-dnevna retencija, brisanje svih snimaka i stvarna galerija (`59eaa1e`);
- povezivanje ranije neaktivnog TopBar "Glas" dugmeta na postojeći voice toggle/stop tok (`58d983f`);
- konsolidacija jezičkih mapa sa pet mjesta na dva namjerna izvora istine (`3533fb2`);
- state-aware hero naslov i pomoćni tekst na početnom ekranu (`948d785`);
- korisnički podesive, perzistentne brze komande u Settings panelu (`7b0f51f`);
- vidljiviji affordance za otkazivanje diktiranja (`e1d8c3f`).

Naknadni commitovi `8c021f6`, `c52eb6f` i `13b2a8c` dodaju i standardizuju obavezne file-header komentare kroz glavne `.py`, `.ts`, `.tsx`, `.cjs` i relevantne `.css` fajlove. To poboljšava održavanje i trag odluka, ali ne mijenja ponašanje aplikacije.

---

## 8. Zaključak

Projekat ima stvarnu arhitektonsku disciplinu koja se **provjerava, ne samo deklariše** — jasna podjela slojeva, permission/risk model koji je testovima dokazan da nema zaobilaznih puteva, fail-closed dizajn na više nivoa (legacy tools, kill-switch, security self-test). Multi-agent radni tok (Claude Code + pi) funkcioniše uz eksplicitnu, ponovljivu disciplinu provjere — dokazano više puta, uključujući i na sopstvenom dokumentu (sekcija 7), da se tvrdnje ne uzimaju zdravo za gotovo bez provjere u stvarnom kodu, bez obzira da li dolaze od pi-ja, od eksterne AI recenzije, ili od mene samog.

Istovremeno, projekat ima realne, imenovane praznine — GUI lokalizacija je znatno odmakla ali nije završena, frontend nema testove, i produkcijski gates (Security Gate 1/2) nisu zatvoreni. Dev-mode auth fail-open i S-2 outbound eskalacija su bili na ovoj listi do 2026-07-12, kad su oba popravljena (vidi sekciju 4.3, 4.7, 7). Nijedna od ovih stavki nije skrivena ili uljepšana u ovom dokumentu.
