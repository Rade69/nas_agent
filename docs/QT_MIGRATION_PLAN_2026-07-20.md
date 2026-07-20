# Qt Desktop Migration — plan realizacije

**Datum:** 2026-07-20
**Status:** prijedlog za usvajanje
**Scope:** potpuno uklanjanje Electron/Chromium sloja; React UI → PySide6; WebRTC glas → WebSocket iz Pythona; cilj: Windows + macOS + Linux
**Odnos prema drugim planovima:**
- **Zamjenjuje** `docs/ELECTRON_MIGRATION_PLAN_REVISED_2026-07-19.md` (EM-0…EM-9) — taj plan je pretpostavljao da Electron ostaje kao tanak shell; ovaj plan ga u potpunosti uklanja, pa je EM-plan bespredmetan (nema smisla stanjivati `main.cjs` koji se briše). EM-plan se označava kao `superseded`, ne briše se — istorijski je koristan (invarijante, contract-freeze ideja, test matrica su ponovo iskorišćene ovdje).
- **Ne mijenja** `docs/SECURITY_HARDENING_ROADMAP_REVISED_2026-07-19.md` (R0…R10) — taj plan je pretežno backend/Python fokusiran i nastavlja nezavisno. Tačke dodira eksplicitno navedene u §2.4.
- **Nadovezuje se na dva dokazana spike-a** iz ove sesije, koji nisu teorija nego pokrenut i verifikovan kod: `spikes/voice_websocket_spike.py` (glas + tool-calling + confirmation flow, sve dokazano preko WebSocket-a) i `spikes/pyside6_orb_spike.py` (companion orb u PySide6, strukturno potvrđen).

---

## 1. Odluka o grani — zaključena, ne otvorena

**Nova grana `qt-desktop-migration`, forkovana iz `hybrid-python-backend` (ne iz `master`).**

Razlog: `hybrid-python-backend` je 135 commita ispred `master`-a i tu živi sav `python_backend/` — agent runtime, permission engine, sav sigurnosni rad iz Gate 0, 236 testova. To je većina stvarnog inženjerskog uloga u projektu i **ne mijenja se ovom migracijom**. Novi repo bi značio ili ručno prenošenje te osnove, ili gubitak konteksta. Grana umjesto novog repo-a:

- `python_backend/` ostaje zajednički — periodičan `git merge hybrid-python-backend` u migracionu granu povlači backend izmjene bez ručnog rada, jer Qt grana ne dira `python_backend/`.
- Druga sesija nastavlja svakodnevni rad (browser bridge, Plans Panel, a11y) na `hybrid-python-backend` bez prekida.
- `CLAUDE.md`, `AGENTS.md`, GitNexus indeks, `agent_reports/` istorija — sve važi bez ponovnog postavljanja.
- Rollback je trivijalan: grana se briše ili napušta, `hybrid-python-backend` je netaknut.

**Merge nazad:** tek nakon QM-9 (kraj plana), eksplicitnom korisničkom odlukom, ne automatski.

---

## 2. Obavezne arhitektonske odluke

### 2.1 Jedan proces ili dva — ODLUKA: **dva procesa ostaju, za v1**

Dvije opcije su razmatrane:

- **Opcija A (usvojena za v1):** Qt shell pokreće `python_backend/` kao **poseban proces**, isto kao Electron danas (`pythonProcess.cjs` obrazac) — HTTP na `127.0.0.1`, session token preko env varijable, health check prije prikaza prozora. `python_backend/` se **ne mijenja ni jednom linijom** za ovu odluku.
- **Opcija B (odložena, moguća kasnija optimizacija):** FastAPI agent runtime učitan **u istom Python procesu** kao Qt UI — nestaje HTTP sloj, auth token, dva procesa. Veća dobit (manje pokretnih dijelova), ali veći rizik: asyncio (FastAPI) i Qt event loop moraju koegzistirati u istom procesu (npr. preko `qasync`), što je poznato osjetljivo područje, i zahtijeva rework `python_backend/` lifecycle-a koji je danas pisan kao samostalan servis.

**Zašto A za v1:** prati princip iz cijele ove sesije — dokaz prije gradnje, najmanja količina rizika koja bezbjedno radi posao. Opcija A znači da **236 postojećih backend testova ostaje validno bez izmjene**, i da je blast radius migracije strogo ograničen na `electron/` → Qt zamjenu. Opcija B ostaje zapisana kao mogući QM-10+ korak, tek ako se pokaže stvarna potreba (npr. mjerena latencija ili packaging veličina to zahtijeva) — ne prije.

### 2.2 UI framework unutar Qt

**PySide6** (već instaliran, verzija 6.11.1 potvrđena u ovoj sesiji). Widgets, ne QML — brži prijenos mentalnog modela iz React komponenti (deklarativno stablo widgeta je bliže JSX-u nego QML scene graph), i korisnik već poznaje Qt/PySide6 iz ASYCUDA_PRO.

### 2.3 Glas

**WebSocket, ne WebRTC** — dokazano u `spikes/voice_websocket_spike.py`: 259-1637ms latencija (prosjek ~600-1000ms, "odlično" do "dobro" po sopstvenoj skali), nula eha na korisnikovom hardveru, tool-calling i confirmation-gated akcije rade preko glasa end-to-end. GA API oblik (ne beta) je dokumentovan u spike-u.

### 2.4 Dodirne tačke sa `SECURITY_HARDENING_ROADMAP_REVISED_2026-07-19.md`

| R-faza | Odnos prema Qt migraciji |
|---|---|
| R1 (filesystem_search) | nezavisno, backend-only, nastavlja bez izmjene |
| R2 (legacy PowerShell containment) | nezavisno — ali pojednostavljeno: Qt shell nikad neće ni imati legacy PowerShell fallback (to je bio Electron-specifičan mehanizam), pa R2/R8 postaju **lakši** ovom migracijom, ne teži |
| R3-R5 (secrets, SQLCipher, screenshot enkripcija) | nezavisno, backend-only |
| R6 (signing) | **dijeljeno** — nov Qt installer i dalje treba potpisivanje; isti zahtjev, nova mehanika (vidi QM-8) |
| R9 (Electron/Chromium CVE praćenje) | **nestaje u potpunosti** — nema više Chromium-a za praćenje, cijela faza otpada |

---

## 3. Verifikovani baseline (2026-07-20)

### 3.1 Šta se NE mijenja

```text
python_backend/           105 .py fajlova, agent runtime, permission engine,
                           236 testova — 0% izmjena za ovu migraciju
docs/SECURITY_*.md         svi sigurnosni planovi, nastavljaju nezavisno
agent_reports/, MIGRATION_PLAN.md   istorija i tracker, nastavljaju
```

### 3.2 Šta se briše (nakon uspješnog cutover-a, ne prije QM-9)

```text
electron/                  4 391 linija (main.cjs 949, legacyMedia.cjs 730, ...)
src/                        8 071 linija React/TS (40 fajlova)
electron-builder.yml, NSIS installer config
```

### 3.3 Već dokazano, spremno za ugradnju u pravu app strukturu

| Spike | Šta dokazuje | Fajl |
|---|---|---|
| Glas preko WebSocket-a | Transport, latencija, barge-in, eho (na ovom hardveru), tool-calling preko glasa, confirmation flow preko glasa | `spikes/voice_websocket_spike.py` |
| Companion orb u Qt | Frameless/transparent/always-on-top prozor, drag, tri prstena preko avatara (ispravan z-order, `CompositionMode_Screen`), minimize u tačku | `spikes/pyside6_orb_spike.py` |

Ovo nisu teorijski predlošci — oba su pokrenuta, pukla, popravljena i ponovo testirana u ovoj sesiji. QM-2 i QM-3 ih **portuju** u pravu app strukturu, ne pišu iznova.

### 3.4 Nepoznato / nedokazano

- **macOS, Linux** — nula testova **odavde** (ja nemam pristup), ali **ne nula pristupa uopšte**: korisnik ima dual-boot Fedora 44 (Linux) koji često koristi — brz, čest test ciklus — i pristup MacBook Air-u (macOS, preko domaćinstva) — sporiji, rjeđi test ciklus jer je posuđena mašina. Ovo mijenja QM-9b/c iz "nadaj se da radi" u stvarno testabilne faze, samo sa različitom učestalošću iteracije po platformi. Vidi QM-9 i §7 (rizici).
- **Eho na drugom hardveru** — nula eha izmjereno je na korisnikovom laptopu (Intel Smart Sound mikrofon sa hardverskim AEC-om); nepoznato na desktop mikrofonu/zvučnicima.
- **Providnost na multi-monitor Windows setupu sa različitim DPI** — korisnik je prijavio bug, odbrambena popravka je napisana u orb spike-u, **nije potvrđena** (nema drugog monitora odavde).
- **Mermaid renderovanje** — jedina teška web-zavisnost (interno koristi Chromium/Puppeteer); nema čist Qt ekvivalent. Rješenje odloženo do QM-6.

---

## 4. Invarijante — ne smiju se slomiti

1. Isti permission/confirmation tok mora raditi identično preko glasa i preko teksta (već dokazano za glas u spike-u; tekst već radi kroz `python_backend/`).
2. Nijedan high-risk alat ne smije proći bez `confirmation_id` — ovo je već garantovano u `permission_engine.py` i **ne zavisi od shell-a**, ali UI mora ispravno prikazati čekanje/odobrenje.
3. Kill-switch mora raditi čak i kad backend ne odgovara.
4. Qt UI nikad ne dobija API ključ direktno — isti obrazac kao danas (Electron nikad nije vidio trajni OpenAI ključ, samo ephemeral Realtime token).
5. Companion orb zadržava vizuelni karakter potvrđen u spike-u (avatar + tri prstena, ne generička animacija).
6. Permanentni thumbnail broj i parent/child veze (kad se thumbnail domen migrira) se ne mijenjaju.
7. Svaka faza ima zaseban commit, agent report, ažuriran tracker, i definisan rollback.
8. Nema brisanja `electron/`/`src/` prije nego što je Qt ekvivalent funkcionalno potvrđen (QM-9 preduslov, ne ranije).

---

## 5. Nadzorni model — Claude Code + pi

Korisnik izvodi posao kroz pi agenta zbog ograničenja tokena; ja (Claude Code) zadržavam arhitektonske odluke, sigurnosno-kritičan kod i verifikaciju. Ovo je isti obrazac koji `CLAUDE.md` već propisuje za multi-agent rad na ovom repo-u — ovdje samo eksplicitno primijenjen na migraciju.

### 5.1 Šta NIKAD ne ide pi-ju bez mog direktnog rada prije toga

- QM-1 (process bridge — auth token generisanje/prosljeđivanje) — sigurnosno osjetljivo, isti nivo pažnje kao FAZA 6 (ephemeral credential minting) u originalnoj migraciji.
- QM-3 (integracija glasovnog spike-a u pravu app strukturu) — ja sam spike izgradio i debug-ovao ove sesije; prenošenje u pravu strukturu bez gubitka konteksta ide meni prvo, pi nastavlja na već postavljenom obrascu.
- Bilo koja izmjena `permission_engine.py`, `confirmation_service`, ili auth toka.

### 5.2 Šta ide pi-ju, sa preciznim brief-om

- QM-5 (port pojedinačnih React komponenti u Qt widgete) — mehanički, ponovljiv obrazac, isti tip posla kao dosadašnji i18n brief-ovi koje je pi već uspješno radio.
- QM-6 podstavke (notes/records/artifacts UI, settings panel) — jasno ograničen opseg po komponenti.
- QM-8 mehanički dio (PyInstaller/Nuitka build skripta prema mom specu).

### 5.3 Format brief-a za pi (isti obrazac kao postojeći `docs/PI_TASK_*.md`)

```markdown
# PI Task: QM-5.<N> — <naziv komponente>

## Cilj
[jedna rečenica]

## Izvor (React)
src/components/<Fajl>.tsx — pročitati prije početka

## Cilj (Qt)
desktop/ui/<fajl>.py

## Kontrakt
- ulazi/izlazi identični postojećem backend API pozivu (ne mijenjati endpoint)
- [specifične vizuelne/funkcionalne tačke iz React verzije]

## Zabranjeno
- ne dirati python_backend/
- ne dirati desktop/core/process_bridge.py (moj fajl, QM-1)
- ne dirati desktop/ui/orb.py (portovan iz spike-a, QM-2)

## Test
[konkretna komanda/scenario za ručnu i/ili automatsku provjeru]

## Agent report
agent_reports/YYYY-MM-DD_qm5-<slug>.md
```

### 5.4 Verifikacija — ne mijenja se od postojeće discipline

Svaki pi-jev commit: ja čitam stvaran `git diff`, ne samo agent report. Ovo je već dokazano da hvata stvarne probleme na ovom projektu (vidi `docs/PROJECT_OVERVIEW.md` §5.1 primjere). Ništa se u toj disciplini ne mijenja za ovu migraciju — samo se dosljedno primjenjuje.

### 5.5 Collision fajlovi specifični za ovu migraciju

Pored postojeće liste (`python_backend/app/core/config.py`, `app/main.py`, `electron/main.cjs` — potonji nestaje pa prestaje biti relevantan za Qt granu):

```text
desktop/core/process_bridge.py     — moj fajl, pi ne dira (auth/lifecycle)
desktop/ui/orb.py                  — portovan iz spike-a, ja integrišem prvi put
desktop/ui/voice.py                — portovan iz spike-a, ja integrišem prvi put
desktop/main.py                    — composition root, isti status kao main.cjs danas
```

---

## 6. Faze realizacije

```text
QM-0 → QM-1 → QM-2 → QM-3 → QM-4 → QM-5 → QM-6 → QM-7 → QM-8 → QM-9
                                      (QM-5 i QM-6 dijele se u male pakete,
                                       mogu ići paralelno nakon QM-4)
QM-9a (Windows cutover) može ići prije QM-9b/c (macOS/Linux) — vidi §6.10
```

### QM-0 — Baseline i postavka grane

**Cilj:** zaključati polaznu tačku, spriječiti rad bez pouzdanog testnog signala.

**Koraci:**
1. Kreirati granu `qt-desktop-migration` iz `hybrid-python-backend`.
2. Kreirati `desktop/` folder (novi Qt shell), prazan skelet.
3. Snimiti baseline: `pytest` rezultat (236 testova), spisak spike fajlova kao polazna tačka.
4. Formalno zapisati odluku §2.1 (dva procesa za v1) u ovaj dokument (već urađeno gore) i u `docs/MIGRATION_PLAN.md` kao novu sekciju.
5. Instalirati `pyinstaller` ili `nuitka` u dev environment (izbor u QM-8, priprema sada).

**Gate:** grana postoji, `python_backend/` testovi i dalje 100% zeleni (nedirnuti), `desktop/` skelet se pokreće (prazan Qt prozor).

**Veličina/izvođač:** S; **ja** (postavka grane i odluke, ne mehanički posao za pi).

---

### QM-1 — Process bridge (Qt ↔ Python backend)

**Cilj:** Qt shell pokreće, nadzire i bezbjedno komunicira sa `python_backend/` — isti posao koji danas radi `pythonProcess.cjs` + `preload.cjs` + auth token mehanika, samo u Pythonu.

**Koraci:**
1. `desktop/core/process_bridge.py`: spawn backend-a, izbor slobodnog porta, `secrets.token_bytes(32)` za session token (isti nivo entropije kao `crypto.randomBytes(32)` danas), prosljeđen kroz env varijablu — **ne** kroz komandnu liniju (vidljivo u process listi).
   - **Spawn mehanika mora od početka pretpostaviti frozen exe, ne dev environment** (FABLE-5 review, 2026-07-20): u paketovanoj verziji (QM-8) nema sistemskog Python interpretera na ciljnoj mašini, pa `subprocess.Popen(["python", ...])` puca na čistoj mašini. Ispravno od dana jedan: `subprocess.Popen([sys.executable, "--backend", ...])` — isti zapakovani exe se ponovo poziva sam sa flagom, a entry point grana na Qt UI vs FastAPI/uvicorn prema tom flagu. Popravljati ovo naknadno u QM-8 znači redizajn spawn logike koju QM-2/QM-3 već grade iznad nje.
2. Health check polling prije prikaza glavnog prozora (isti obrazac kao `securitySelfTest.cjs`).
3. HTTP klijent (`httpx`) sa Bearer tokenom za sve pozive ka backend-u.
4. **Gašenje backend procesa — Windows Job Object je primarni mehanizam, ne `atexit`** (FABLE-5 review, 2026-07-20): `atexit` se izvršava samo pri urednom gašenju interpretera — ne pri crash-u, `TerminateProcess`, ili prekidu strujе. Za garantovano gašenje djeteta kad roditelj nestane na *bilo koji* način, backend proces se dodjeljuje Windows Job Object-u sa `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` (preko `pywin32`/`win32job` ili direktno preko `ctypes`) — OS kernel garantuje ubijanje djeteta kad job handle nestane, bez ikakvog koda na backend strani. `atexit` + living-parent polling ostaju kao dodatni, ne primarni sloj (defense in depth, isti duh kao fail-closed dizajn u §4).
5. Fail-closed: ako backend ne odgovori na health check u N sekundi, Qt prikazuje grešku i ne otvara glavni prozor (isto ponašanje kao `production self-test`).

**Gate:**
- Qt app pokreće backend, backend prijavljuje healthy, Qt app se zatvara i backend proces nestaje (provjereno preko Task Manager / `psutil`, ne pretpostavka).
- **Backend proces nestaje i kad se Qt app ubije nasilno** (Task Manager "End task" ili ekvivalent) — test specifično za Job Object mehanizam, ne samo za graceful shutdown.
- **Spawn radi na mašini bez instaliranog Python interpretera** — test unaprijed, ne čekati QM-8 da se ovo otkrije.
- Token nikad nije vidljiv u command line argumentima procesa.
- Backend koji namjerno ne odgovara (test: pogrešan port) daje jasnu grešku, ne tihi pad.

**Rollback:** izolovan modul, brisanje `desktop/core/process_bridge.py` vraća na prazno stanje bez uticaja na `python_backend/`.

**Veličina/izvođač:** M; **ja** (sigurnosno osjetljivo — §5.1).

---

### QM-2 — Companion orb integracija

**Cilj:** prenijeti `spikes/pyside6_orb_spike.py` iz izolovanog spike-a u pravu app strukturu, ožičen na stvaran `VoiceState` iz backend-a umjesto lažnog auto-ciklusa.

**Koraci:**
1. `desktop/ui/orb.py` — portovan `RickyOrbWidget`, uklonjen auto-cycle/keyboard-test kod (bio je za spike, ne za produkciju).
2. Polling na `GET /voice/state` (ili ekvivalent) **1s maksimum**, ne 1-3s (FABLE-5 review, 2026-07-20: promjena glasovnog stanja je tačno ono što oko odmah uhvati — orb pozeleni dok agent već priča izgleda kao kvar, ne kao kašnjenje). Isti privremeni obrazac kao Electron `setInterval` polling danas. **Orb state je prvi kandidat za SSE** kad `GET /events/stream` dođe na red (`EventBus` na backendu već postoji, nije implementiran) — površina je sićušna (jedan endpoint) a dobit najvidljivija od svih mogućih SSE kandidata, vrijedi prioritizovati baš ovaj kad se ta faza otvori.
3. Minimize/restore preko desnog klika (kontekst meni), ne samo dupli klik iz spike-a — uskladiti sa `companionWindow.cjs` MENU_LABELS obrascem (već postoji lokalizovan tekst za 5 jezika, ponovo iskoristiti).
4. Multi-monitor fix iz spike-a (`screenChanged` handler) — **ovdje mora dobiti stvarnu potvrdu**, jer QM-0…QM-1 ne uvode drugi monitor u test.

**Gate:**
- Orb prati stvarne promjene stanja iz backend-a (test: ručno pokrenuti glasovnu sesiju, posmatrati promjenu boje/pulsa).
- Multi-monitor test **prođe uživo** (korisnički runtime test, ne moj).
- Drag, minimize, kontekst meni rade identično spike ponašanju.

**Rollback:** `desktop/ui/orb.py` je samostalan modul; uklanjanje ne utiče na QM-1.

**Veličina/izvođač:** M; **ja** prvi prolaz integracije (portovanje spike-a), pi može raditi kontekst meni/lokalizaciju pod mojim brief-om nakon toga.

---

### QM-3 — Glasovna integracija

**Cilj:** prenijeti `spikes/voice_websocket_spike.py` u pravu app strukturu — **dinamički** tool registry (ne 3 hardkodirana alata), realan confirmation UI (ne Enter-u-terminalu), realan audio device izbor.

**Arhitektonska odluka koja mora stati prije koda (FABLE-5 review, 2026-07-20):** spike je čist `asyncio` (WebSocket + `sounddevice` callback-ovi). Odlaganje opcije B (§2.1) ne uklanja problem — WebSocket klijent i dalje mora živjeti *unutar* Qt procesa već u v1, a Qt event loop i asyncio event loop ne koegzistiraju automatski u istoj niti. Dvije opcije, i razlog zašto se bira prva:

- **QThread sa sopstvenim asyncio loop-om (usvojeno).** Glasovni WebSocket + audio callback-ovi rade u pozadinskoj niti sa svojim `asyncio.run()`, komunikacija nazad ka UI niti ide preko Qt signala (thread-safe po dizajnu preko `QueuedConnection`). Pad WebSocket-a ili audio glitch ne dira UI loop.
- **`qasync` u glavnom loop-u (odbijeno).** Spaja asyncio i Qt loop u istu nit — tačno ono "poznato osjetljivo područje" zbog kojeg je opcija B (§2.1) svjesno odložena. Prihvatanje ovdje bi bilo nedosljedno sa tom odlukom.

**Koraci:**
1. `desktop/ui/voice.py` — portovan WebSocket klijent unutar `QThread` (vidi odluku gore), GA session.update oblik iz spike-a (već tačan, ne treba ponovo istraživati).
2. Alati se učitavaju dinamički sa `GET /tools` (isto što `toolSpecs` radi u `realtime.ts` danas), ne hardkodirana lista iz spike-a.
3. Tool execution ide kroz **stvaran** `POST /tools/execute` na backend — spike je alate izvršavao lokalno u Python funkciji; prava app mora pozvati pravi permission-engine-gated endpoint.
4. `CONFIRMATION_REQUIRED` odgovor otvara pravi Qt confirmation dijalog (ne terminal Enter) — vizuelni ekvivalent `ConfirmationDialog.tsx`, uključujući `armed` min-delay zaštitu (FAZA S-4/S30) koja već postoji u React verziji. **Ovaj dijalog pripada isključivo QM-3** (sigurnosno kritičan UI, radim ga ja) — vidi ispravku QM-5.3 niže, gdje je isti stavka ranije bila dupliran.
5. Idempotency: portovati `completedToolCallIds` logiku iz `realtime.ts` (red 742+) — spriječiti duplo izvršenje istog `call_id`.
6. Audio device: podrazumijevani sistemski, sa Settings opcijom izbora (paritet sa mogućim budućim potrebama, ne blokira v1).

**Gate:**
- Glasom pokrenut stvaran alat (ne test-alat iz spike-a) prolazi kroz pravi permission engine i vraća stvaran rezultat.
- High-risk alat preko glasa otvara pravi Qt confirmation dijalog; odobrenje preko UI-ja (ne terminal) automatski nastavlja radnju — isti Confirmation Bridge obrazac dokazan u spike-u, sada sa pravim dijalogom.
- Duplo pozivanje istog `call_id` ne izvršava alat dvaput.
- Voice/text paritet: isti upit tekstom i glasom daje istu sigurnosnu odluku (invarijanta §4.1).
- **Latencija se ponovo mjeri ovdje, ne pretpostavlja iz spike-a** (FABLE-5 review, 2026-07-20): spike-ovih 259-1637ms je izmjereno sa 3 lažna alata i na jednom hardveru sa hardverskim AEC-om (Intel Smart Sound). Gornja granica od ~1.6s je na ivici upotrebljivosti za razgovor — sa stvarnim brojem alata (veći tool-spec payload) i pravim permission-engine pozivom latencija može rasti. Ako se ponovljeno mjerenje pomjeri iznad ~2s prosjeka, to je stop-signal za dalji rad na QM-3, ne kozmetička napomena.

**Rollback:** izolovan modul; QM-1/QM-2 ostaju funkcionalni bez njega (orb i dalje prikazuje stanje, samo bez glasovnog unosa).

**Veličina/izvođač:** L, visok blast radius (dodiruje permission engine integraciju); **ja** vodim, obavezan GitNexus impact prije svake izmjene simbola u `python_backend/` ako se ijedan endpoint pokaže nedovoljnim.

---

### QM-4 — Glavni prozor, navigacija, skelet

**Cilj:** prazan Qt glavni prozor sa navigacijom (ekvivalent `App.tsx` strukture) — mjesto gdje QM-5 komponente dobijaju dom.

**Koraci:**
1. `desktop/main.py` — composition root, isti status kao `main.cjs` danas (§5.5 collision fajl).
2. Layout skelet koji prati postojeći "pixel dashboard" koncept (sve sekcije odjednom, ne single-screen navigacija — arhitektonska odluka već zabilježena u `PROJECT_OVERVIEW.md` §1).
3. Prazni placeholderi za sekcije koje QM-5 popunjava.

**Gate:** prozor se otvara, sve navigacione tačke postoje (prazne), orb (QM-2) i glas (QM-3) su vidljivi/dostupni iz glavnog prozora.

**Veličina/izvođač:** M; **ja**.

---

### QM-5 — Port UI komponenti (najveći paket, dijeli se po komponenti)

**Cilj:** 8.071 linija React-a → Qt widgeti, komponenta po komponenta, svaka svoj commit/report/gate.

**Redoslijed po prioritetu** (najviše korišćeno prvo, najmanje rizično prvo):

| Paket | React izvor | Kompleksnost | Izvođač |
|---|---|---|---|
| QM-5.1 | `DictationScreen.tsx` | M | pi (brief) |
| QM-5.2 | `ActivityTimeline.tsx` | M | pi (brief) |
| ~~QM-5.3~~ | ~~`ConfirmationDialog.tsx`~~ | — | **već izgrađeno u QM-3 korak 4** (FABLE-5 review, 2026-07-20: bila je duplirana kao poseban port paket ovdje, a QM-3 gate je već zahtijevao gotov dijalog — ista stvar se ne gradi dvaput). Red ostaje samo kao trag da stavka nije zaboravljena. |
| QM-5.4 | `PlansPanel` (P0-P5 funkcionalnost) | L | pi, po pod-fazama kao original |
| QM-5.5 | `SettingsPanel.tsx` | S | pi |
| QM-5.6 | `ArtifactPanel` (markdown/kod/tabele/mermaid) | **visoka — mermaid nema Qt ekvivalent** | ja odlučujem pristup, pi implementira |
| QM-5.7 | `MiniComputerWindow.tsx` | M | pi |
| QM-5.8 | Ostatak (manje komponente) | S svaka | pi |

**Gate po komponenti:** vizuelna provjera korisnika uživo (per `user_plans_visually` — korisnik mora vidjeti da bi ocijenio), funkcionalni test protiv stvarnog backend endpointa, agent report.

**Rollback po komponenti:** svaki port je zaseban commit; loš port se vraća bez uticaja na ostale.

**Veličina/izvođač:** XL ukupno, podijeljeno u S/M pakete — upravo tip posla za koji je pi najbolje pozicioniran, uz moj pregled svakog diff-a prije prihvatanja (§5.4).

---

### QM-6 — Feature parity (notes/records/thumbnails/artifacts)

**Cilj:** funkcionalnosti koje nisu čist UI port nego imaju svoj backend tok.

**Koraci:**
1. Notes/records CRUD — već postoji u `python_backend/`, samo UI (dio QM-5).
2. ~~Thumbnail domen — nasljeđuje nezavršen posao...~~ **URAĐENO (2026-07-20, pi, pod ovim planom).** Ono što je ovdje bilo opisano kao "najveći skriveni trošak" je izvršeno dok je ovaj dokument bio u reviziji — korisnik je uzeo ovu sekciju kao osnovu za `docs/PI_TASK_QM6_THUMBNAIL_PYTHON_DOMAIN.md`, pi je izvršio QM-6T1 do QM-6T6 (SQLite storage, `ThumbnailBoardService`, pravi OpenAI Image API poziv portovan iz `legacyMedia.cjs`, 5 model-facing Python tool-ova registrovanih u `phase11.py`, Electron legacy dispatch grane fizički uklonjene iz `handleToolsExecute`, REST API, instructions endpoint). **Verifikovano od mene** (ne samo report na riječ, §5.4): 25 novih testova prolazi, puni suite 409/412 (tri pada su pre-postojeća i dokumentovana u `ELECTRON_MIGRATION_PLAN_REVISED_2026-07-19.md` §2.4, nepovezana), `.cjs` fajlovi sintaksno validni, legacy `thumbnailGenerate()`/`thumbnailEdit()` pozivi potvrđeno više ne postoje u `main.cjs` (samo neiskorišćen `require()` import ostaje kao sitan cleanup, ne bug). Vidi `agent_reports/2026-07-20_pi-qm6-thumbnail-python-domain.md`. **Preostaje samo Qt UI za thumbnail board** (dio QM-5) — backend domen je zatvoren.
3. Mermaid — nema Chromium da ga renderuje. Odluka: renderovati kao formatiran kod blok (fallback) u v1, puna podrška odložena (zahtijeva ili embedded web view — što bi vratilo dio Chromiuma na mala vrata — ili čist Python/Qt mermaid renderer, koji ne postoji zreo).

**Gate:** svaka funkcija ima paritet test protiv stare Electron verzije (dok god obje postoje u granama).

**Veličina/izvođač:** ~~L (thumbnail dio)~~ **S** (samo Qt UI ostaje, backend gotov); pi po mom brief-u za UI dio, isti obrazac kao QM-5.

**Napomena o procesu (2026-07-20):** ovo je prvi stvaran primjer nadzornog modela iz §5 u radu — plan napisan, korisnik ga proslijedio pi-ju kao brief, pi izvršio, ja verifikovao diff/testove prije prihvatanja. Vrijedi zapamtiti obrazac: čim je faza dovoljno konkretno opisana u ovom dokumentu, spremna je da postane pi brief bez dodatnog prepisivanja.

---

### QM-7 — Kill-switch i sigurnosni self-test u novom shell-u

**Cilj:** funkcionalni paritet sa `securitySelfTest.cjs` i globalnim kill-switch-om, u Qt kontekstu.

**Koraci:**
1. Global hotkey (Escape) — Qt ekvivalent, testirati da radi i kad orb nije fokusiran.
2. "Stop sve" — poziva isti `POST /tools/executions/cancel-all` endpoint, nepromijenjen.
3. Self-test prije prikaza prozora proširuje QM-1 health check: provjerava i da backend permission engine odgovara očekivano (isti princip kao danas, portovan).

**Gate:** kill-switch radi sa fokusiranim i nefokusiranim prozorom (isti test iz originalnog EM-8 test matrice).

**Veličina/izvođač:** M; **ja**.

---

### QM-8 — Packaging (Windows prvo)

**Cilj:** jedan instalacioni paket bez Electron/Chromium tereta.

**Koraci:**
1. Izbor: PyInstaller vs Nuitka — odluka na osnovu veličine/brzine builda, testirati oba na malom primjeru prije commitmenta na jedan.
2. Uključiti `python_backend/` kao dio istog paketa (ne poseban sidecar proces koji se posebno pakuje — ovdje oba dijela su Python, pakovanje je jednostavnije nego Electron+Python sidecar kombinacija danas).
3. Code signing — **isti zahtjev kao R6** iz sigurnosnog roadmapa; sertifikat treba naručiti **odmah, paralelno**, ne čekati QM-8 (sedmice čekanja na EV sertifikat).
4. Instalacija/deinstalacija test na čistoj Windows mašini.

**Gate:** potpisan paket, instalacija/pokretanje/deinstalacija test prolazi, veličina paketa izmjerena i upoređena sa starim Electron installer-om (očekivana dobit — dokumentovati stvaran broj, ne pretpostavku).

**Veličina/izvođač:** L; ja specificiram, pi izvršava build skriptu po mom specu (§5.2).

---

### QM-9 — Cross-platform i cutover

**Ispravka (2026-07-20, nakon FABLE-5 review-a i korisnikove korekcije):** FABLE-5 je predložio potpuno brisanje QM-9b/c iz plana zbog "nula pristupa tim sistemima". To je bilo netačno — korisnik ima dual-boot Fedora 44 (Linux), koji često koristi, i pristup MacBook Air-u (macOS, preko domaćinstva). QM-9b/c ostaju formalne faze. Ono što ostaje tačno iz FABLE-ovog upozorenja: pristup je **asimetričan** — Linux test ciklus je brz i čest (korisnikova sopstvena mašina, dual-boot restart), macOS test ciklus je spor i rijedak (posuđena mašina). Redoslijed ispod prati tu realnost, ne pretpostavku.

#### QM-9a — Windows cutover (prvo — glavna, svakodnevna mašina)
- Pun paritet test prema staroj Electron verziji.
- Korisnička runtime potvrda na stvarnoj mašini.
- Merge odluka: **eksplicitna, korisnikova**, ne automatska.

#### QM-9b — Linux (drugo — brz test ciklus, dual-boot)
- Wayland vs X11 — transparentni always-on-top prozori su poznato nepouzdani na Wayland-u (isti rizik koji je ranije diskvalifikovao Tauri u ovoj sesiji — Qt na Linuxu nije imun na isti problem). Prvi test: da li orb (QM-2) uopšte zadržava providnost na korisnikovom stvarnom Wayland/X11 setupu.
- Distribucija — AppImage/Flatpak umjesto installer-a, nov teren.
- **Zašto prije macOS-a:** dual-boot restart je jeftin, korisnik može iterirati isti dan bez tuđe mašine — greške se brzo otkrivaju i brzo popravljaju.

#### QM-9c — macOS (treće — spor test ciklus, posuđena mašina)
- Audio device API razlike (`sounddevice`/PortAudio bi trebao raditi isto, ali netestirano).
- Tray/companion orb ekvivalent — macOS ima drugačija pravila za always-on-top/transparent prozore (može zahtijevati `NSPanel` nivo pristupa kroz PySide6, nepoznato bez testiranja).
- Code signing/notarizacija — potpuno drugačiji proces od Windows Authenticode.
- **Zašto poslije Linuxa:** svaki test ciklus zavisi od dostupnosti tuđe mašine. Praktična posljedica: pripremiti što više provjera unaprijed (checklist, ne istraživanje uživo) prije nego što se mašina fizički posudi, da se jedna sesija pristupa iskoristi maksimalno.

**Gate za QM-9b/c:** korisnički runtime test na stvarnoj mašini (ne pretpostavka), isti nivo dokaza kao QM-9a. Prva runda na svakoj platformi je i dalje djelimično istraživačka (nepoznati problemi kao NSPanel/Wayland specifike) — trajanje prve runde se ne procjenjuje unaprijed, ali sama faza **jeste** u planu, ne van njega.

**Veličina/izvođač:** nepoznato do prve runde na svakoj platformi; **ja** vodim prve prolaze (najviši rizik nepoznatih problema), pi nastavlja mehanički dio nakon što je obrazac utvrđen. Za macOS specifično: pripremiti brief unaprijed (checklist provjera) prije nego što je mašina fizički dostupna, da se ne troši rijetka prilika na istraživanje uživo koje je moglo biti pripremljeno ranije.

---

## 7. Rizici

| Rizik | Posljedica | Kontrola |
|---|---|---|
| ~~Thumbnail domen se otkrije kao veći posao usred QM-6~~ | — | **RIJEŠENO 2026-07-20** — backend domen izgrađen i verifikovan prije nego što je rizik uopšte stigao da se materijalizuje (vidi QM-6). Red ostaje kao trag da je rizik bio predviđen i zatvoren, ne previđen. |
| macOS/Linux otkriju blokirajuće probleme (orb transparentnost, audio) | QM-9b/c mogu trajati neodređeno | Windows cutover (QM-9a) je nezavisan i ne čeka ostale platforme — moguće isporučiti Windows prije nego što su druge platforme riješene |
| pi pogrešno interpretira brief i pravi izmjene van scope-a | gubitak vremena, mogući collision | strogo poštovanje §5.5 liste zabranjenih fajlova po zadatku; ja čitam diff prije prihvatanja (§5.4) |
| Backend endpoint nedovoljan za Qt potrebe (npr. nema SSE, samo polling) | UI osjeća kašnjenje | poznato unaprijed (§3.4 EventBus napomena), prihvaćeno kao v1 ograničenje, ne blocker |
| Mermaid fallback (kod blok umjesto renderovanog dijagrama) nezadovoljavajući korisniku | zahtijeva dodatni rad van plana | odluka o embedded web view vs čist Qt renderer ostaje otvorena, eksplicitno zapisana u QM-6 |
| Dvije grane (`hybrid-python-backend` i `qt-desktop-migration`) divergiraju u `python_backend/` | merge trenje | periodičan merge glavne grane u migracionu (ne obrnuto dok QM-9 ne potvrdi cutover) |
| Token/vrijeme budžet (razlog zašto pi uopšte radi ovaj posao) potroši se prije QM-9 | nedovršena migracija, Electron ostaje jedina radna verzija | fazna struktura sama po sebi je zaštita — svaka faza je samostalno korisna/rollback-able, nema "sve ili ništa" rizika |

---

## 8. Šta nije dio ovog plana

- Opcija B (jedan proces, §2.1) — ostaje zapisana mogućnost, ne aktivan rad.
- Lokalni STT/LLM hibrid (ranije diskutovan u ovoj sesiji) — poseban budući pravac, nezavisan od ovog plana.
- FlowOS — potpuno odvojena tema, eksplicitno van scope-a (korisnikova odluka od ranije u sesiji).
- Multi-user/RBAC — proizvod ostaje single-user desktop aplikacija.

---

## 9. Definicija završetka (po platformi)

```text
QM-9a (Windows) završeno kada:
  proces bridge radi + orb radi (uklj. multi-monitor potvrđen)
  + glas radi sa pravim alatima i confirmation flow-om
  + svi QM-5 paketi portovani i korisnički potvrđeni
  + thumbnail domen migriran u Python
  + potpisan packaged build prolazi instalacioni test
  + tracker/agent report/kod imaju isti status
  = Windows cutover odluka (korisnikova, eksplicitna)

QM-9b/c (macOS/Linux) završeno kada:
  isto gore, plus platform-specifični gate-ovi iz §6 QM-9b/c
  = Puna cross-platform definicija završetka
```

Windows završetak **ne čeka** macOS/Linux — mogu se isporučiti nezavisno, jednom po jednom.
