# Sigurnosni i arhitektonski audit — 2026-07-13

## 1. Svrha i obim

Ovaj izvještaj je rezultat read-only pregleda trenutne implementacije RileyJarvis Windows Hybrid ("Naš-agent"). Cilj nije bio ponoviti postojeće planove, nego provjeriti stvarni kod i utvrditi:

- koje sigurnosne kontrole zaista rade;
- gdje implementacija odstupa od deklarisane arhitekture;
- koje greške nose najveći stvarni rizik;
- šta je realno popraviti kroz male PR-ove jednog developera;
- šta treba blokirati prije beta ili produkcijskog izdanja.

Pregledani su ključni tokovi u `electron/`, `src/`, `python_backend/`, packaging konfiguracija, sigurnosna dokumentacija i testovi. GitNexus indeks je osvježen prema tadašnjem HEAD-u, ali konceptualna FTS pretraga nije radila pouzdano; zato su nalazi potvrđeni direktnim čitanjem izvornog koda, pozivalaca, testova i git istorije.

Audit nije mijenjao runtime kod.

## 2. Verifikacija

Pokrenuto je:

- `npx gitnexus analyze --force` — indeks uspješno osvježen;
- `npm run typecheck` — prošao;
- `npm run build` — prošao, produkcijski CSP potvrđen u `dist/index.html`;
- `python -m pytest -q` — **251/251 testova prošlo**;
- `npm audit --omit=dev` — **0 poznatih produkcijskih ranjivosti**.

Važno ograničenje: frontend nema JS/TS test framework, pa su Realtime, Confirmation Bridge i kill-switch tokovi provjereni čitanjem, ne automatskim testovima.

## 3. Izvršni sažetak

Osnovna arhitektura je dobra: Electron renderer je izolovan, IPC je imenovan, backend je na loopback adresi i zaštićen session tokenom, trajni OpenAI ključ ne ulazi u renderer, a Python `ToolExecutor` centralizuje argument validation, permission checks, confirmations, cancellation state i action log.

Međutim, pronađena su tri P0 problema koja zajedno probijaju zamišljenu sigurnosnu granicu:

1. model može sam uključiti Computer Mode pozivom `set_mode`;
2. `computer_open_app` ima `subprocess.Popen(..., shell=True)` nad model-kontrolisanim stringom;
3. thumbnail reference tok prihvata proizvoljnu lokalnu putanju i kasnije šalje fajl OpenAI Images servisu bez file sandboxa i posebne privacy potvrde.

Zbog toga se trenutni build ne treba nuditi širim beta korisnicima sa uključenim computer-use/thumbnail funkcijama dok se P0 nalazi ne zatvore.

## 4. Prioritetna mapa

| ID | Nalaz | Rizik | Preporučeni prioritet | Procjena rada |
|---|---|---:|---:|---:|
| S-01 | Model može sam uključiti Computer Mode | CRITICAL | P0 | ✅ **Popravljeno 2026-07-13**, revidirano isti dan — vidi `agent_reports/2026-07-13_security-pr-a-set-mode-and-open-app.md` i `agent_reports/2026-07-13_computer-mode-voice-reentry.md` (glasovni `set_mode` vraćen, gated kroz S-2 escalation pravilo umjesto potpunog uklanjanja) |
| S-02 | `computer_open_app` omogućava shell execution | CRITICAL | P0 | ✅ **Popravljeno 2026-07-13** — vidi `agent_reports/2026-07-13_security-pr-a-set-mode-and-open-app.md` |
| S-03 | Proizvoljna lokalna slika može biti poslata u cloud kroz thumbnail reference | CRITICAL | P0 | srednja |
| S-04 | Odobrena confirmation se može ponovo koristiti | HIGH | P0 | ✅ **Popravljeno 2026-07-13** — vidi `agent_reports/2026-07-13_security-s04-one-time-confirmations.md` |
| S-05 | „Stop sve“ ne prekida handler nakon početka commit faze | HIGH | P1 | srednja |
| S-06 | UIA read alati mogu čitati osjetljive aplikacije | HIGH | P1 | srednja |
| S-07 | UIA active-window provjera nije vezana za stvarni target | HIGH | P1 | srednja |
| S-08 | Frontend sigurnosno-kritični tokovi nemaju testove | HIGH | P1 | srednja |
| S-09 | Packaged backend piše mutable podatke u resources folder | HIGH | P1 | mala |
| S-10 | Neočekivani handler exception može ostati bez action loga | MEDIUM | P2 | mala |
| S-11 | Linkovi iz artefakata mogu otvoriti nekontrolisan Electron prozor | MEDIUM | P2 | mala |
| S-12 | Action-log redakcija ne pokriva sve privatne vrijednosti | MEDIUM | P2 | mala |
| S-13 | Token/SQLite nemaju dodatni OS i at-rest hardening | MEDIUM | P3 | srednja |
| S-14 | Cancellation registry ne čisti završene zapise | LOW | P3 | mala |
| S-15 | Sigurnosni komentari i tracker sadrže zastarjele tvrdnje | LOW | P3 | mala |

## 5. Detaljni nalazi

### S-01 — CRITICAL: model može sam uključiti Computer Mode ✅ Popravljeno 2026-07-13

**Revizija (isti dan):** korisnik je prijavio da je potpuno uklanjanje
glasovnog `set_mode`-a nepotrebno trenje za genuine zahtjeve. Umjesto
potpunog uklanjanja, `set_mode` je vraćen modelu ALI gated kroz Python
`permission_engine`-ov postojeći S-2 escalation mehanizam: genuine zahtjev
(bez prethodno pročitanog eksternog sadržaja ovu sesiju) izvršava se odmah;
ako je model već pročitao web/ekran sadržaj, zahtjev eskalira na
confirmation. UI toggle (direktan klik) ostaje uvijek bez trenja i nezavisan
od backend statusa. Vidi `agent_reports/2026-07-13_computer-mode-voice-reentry.md`
za pun dizajn i obrazloženje.

**Dokaz (originalni nalaz, prije revizije)**

- `electron/core/realtimeToolSpecs.cjs` izlaže modelu tool `set_mode` sa vrijednostima `display` i `computer`.
- `electron/main.cjs:344-346` prihvata taj poziv i direktno postavlja `currentMode = "computer"`.
- isti `currentMode` se zatim prosljeđuje Python backendu kao `computer_mode: true` (`electron/main.cjs:300`).
- sistemski meni čak preporučuje glasovnu komandu „Switch to computer use mode“.

**Zašto je kritično**

`SECURITY_HARDENING_PLAN.md` zahtijeva da korisnik eksplicitno uključi Computer Mode. Trenutno ga model može uključiti sam, pa Computer Mode nije nezavisna sigurnosna odluka korisnika. U kombinaciji sa S-02 model može sam otvoriti gate, a zatim aktivirati shell fallback.

**Preporuka**

- ukloniti `set_mode` iz model-facing tool specifikacija;
- razdvojiti UI IPC `computer-mode:request` od agent toolova;
- uključivanje dozvoliti samo trusted UI gestom ili eksplicitnom confirmation karticom;
- vezati Computer Mode za kratku sesiju, jasno prikazan target i timeout;
- automatski ga gasiti na Stop, restart, promjenu korisnika i nakon perioda neaktivnosti;
- backendu prosljeđivati mode iz Electron-owned state-a, nikada iz modelovog payload-a;
- dodati test da model tool call ne može uključiti Computer Mode.

### S-02 — CRITICAL: `computer_open_app` je shell execution put ✅ Popravljeno 2026-07-13

**Dokaz**

`python_backend/app/tools/system/computer.py:188-199` uzima `appName` iz tool argumenta. Ako `os.startfile()` padne, poziva:

```python
subprocess.Popen(app_name, shell=True)
```

Tool schema prihvata proizvoljan string. Tool je `medium`, zahtijeva Computer Mode, ali ne i confirmation. Test `test_phase13_computer_tools.py` eksplicitno potvrđuje `shell=True` poziv.

**Rizik**

Shell metaznakovi, `cmd /c`, PowerShell i druge naredbe mogu biti proslijeđene model-kontrolisanim stringom. Ovo direktno krši zabranu arbitrary shell toola iz `AGENTS.md` i sigurnosnog plana.

**Preporuka**

- odmah privremeno postaviti `computer_open_app.enabled=False`;
- ukloniti `shell=True` bez fallbacka;
- uvesti mapu dozvoljenih aliasa ka fiksnim executable listama;
- koristiti `subprocess.Popen([...], shell=False)`;
- odbiti putanje, argumente, navodnike i shell metaznakove;
- dodati red-team testove za `&`, `|`, `>`, `<`, `%COMSPEC%`, `cmd /c`, `powershell`, `.bat`, `.cmd` i `.ps1`.

### S-03 — CRITICAL: proizvoljna lokalna slika može završiti u cloudu

**Dokaz**

- `thumbnail_reference_add` je model-facing tool u `electron/core/realtimeToolSpecs.cjs`.
- `electron/tools_legacy/legacyMedia.cjs:thumbnailReferenceAdd()` radi `path.resolve(args.imagePath)` i samo provjerava da put postoji.
- nema file pickera, allowed roots provjere, ekstenzije, veličine, symlink zaštite ni posebne confirmation odluke.
- putanja se čuva u legacy JSON bazi.
- `thumbnailGenerate()` i `thumbnailEdit()` uzimaju reference putanje, a `editImageWithInputs()` radi `fs.readFile(inputPath)` i šalje sadržaj na `https://api.openai.com/v1/images/edits`.

**Rizik**

Model ili prompt injection može registrovati privatnu lokalnu sliku kao referencu, a naredni thumbnail poziv je poslati cloud servisu. To može uključiti screenshotove, skenove dokumenata, privatne fotografije ili druge slike do kojih proces ima pristup.

**Preporuka**

- ukloniti proizvoljni `imagePath` iz model-facing contracta;
- korisnik bira fajl kroz Electron native file picker;
- Electron vraća opaque `approved_file_id`, ne originalnu proizvoljnu putanju;
- Python/file service provjerava canonical path, approved root, symlink escape, MIME, ekstenziju i max veličinu;
- prije prvog cloud slanja prikazati: ime fajla, thumbnail preview, servis i svrhu;
- confirmation/payload hash vezati za konkretan file hash;
- dodati `privacy_mode` i action receipt `sent_to_cloud=true`;
- migrirati thumbnail logiku iz legacy Electron sloja u Python backend permission/file sandbox sloj.

### S-04 — HIGH: confirmation nije jednokratna ✅ Popravljeno 2026-07-13

**Dokaz**

`permission_engine.py:180-205` provjerava status `approved`, tool name i payload hash. Nakon uspješnog izvršenja confirmation ostaje `approved`; nema `consumed` statusa ni veze sa `execution_id`.

**Rizik**

Ista confirmation može autorizovati više identičnih izvršenja do isteka TTL-a. Dupli retry ili paralelni poziv može ponoviti klik, unos teksta ili kritičnu promjenu.

**Preporuka**

- state machine: `pending → approved → consuming → consumed`;
- atomski rezervisati confirmation prije commit faze;
- vezati za `execution_id`, tool, payload hash, resolved target, risk i expiry;
- svaka tool confirmation mora imati obavezan `tool_name`;
- potrošiti confirmation nakon prvog pokušaja, čak i kad commit završi greškom;
- dodati replay i concurrency testove.

### S-05 — HIGH: „Stop sve“ nije stvarni prekid započetog toola

**Dokaz**

`ToolExecutor` provjerava `cancel_requested` prije commit faze, zatim poziva handler sinhrono (`tool_executor.py:159`). Nijedan stvarni handler ne poziva `CancellationRegistry.is_cancel_requested()`; metoda se koristi samo u registru/testovima.

**Rizik**

Stop prekida Realtime glas i može blokirati tool prije commit-a, ali ne prekida web/image/UIA/OS operaciju koja je već počela. UI izraz „Stop sve“ zato može stvoriti lažan osjećaj sigurnosti.

**Preporuka**

- kratkoročno razlikovati poruke: `Voice stopped`, `Cancellation requested`, `Cancelled`, `Already committed`;
- handler contract proširiti sa `ExecutionContext(execution_id, is_cancelled)`;
- dodati checkpointe u UIA traversal, mrežne i segmentirane OS operacije;
- za neprekidive akcije prikazati realno `cannot_cancel_commit_started`;
- nakon kill-switcha blokirati nove tool callove dok se sesija eksplicitno ne obnovi.

### S-06 — HIGH: UIA read alati mogu čitati osjetljive aplikacije

`computer_find_elements` i `computer_get_element_text` imaju `reads_external_content=True`, ali nemaju app allowlist/blocked list ni per-window privacy consent. Computer Mode je široka dozvola, ne odobrenje za konkretan prozor.

**Preporuka**

- session-scoped allowlist aplikacija/prozora;
- first-read consent po target aplikaciji;
- blokirati Credential UI, password managere, bankarske/crypto aplikacije, remote desktop, terminale i admin prozore;
- jasno evidentirati koji je prozor pročitan i da li je sadržaj poslat modelu.

### S-07 — HIGH: active-window provjera nije vezana za UIA target

`check_active_window()` provjerava foreground process, ali UIA handler poslije toga nezavisno bira target iz `app`/`title_contains`. Ne provjerava se `foreground HWND/PID == resolved target HWND/PID`. Dodatno, polje `app` se opisuje kao process name, a implementacija ga poredi sa UIA `ClassName`.

**Preporuka**

- target riješiti prije confirmationa;
- confirmation vezati za PID, HWND, process path, title, automation ID i element identity;
- neposredno prije izvršenja ponovo validirati isti target;
- koristiti process resolver, ne `ClassName`, za `app` polje;
- dodati foreground/target mismatch i TOCTOU testove.

### S-08 — HIGH: nema frontend testova za sigurnosnu jezgru

Backend ima 251 testa, ali frontend nema Vitest ili ekvivalent. Netestirani su Realtime function-call batch, Confirmation Bridge, retry, `external_content_seen`, kill-switch i payload prikazan u confirmation dijalogu.

**Minimalni test paket**

1. `CONFIRMATION_REQUIRED` stvara tačno jednu confirmation.
2. Batch nastavlja nakon blokiranog toola.
3. Retry koristi isti tool/payload i ne laže o uspjehu.
4. Taint ostaje aktivan nakon external read toola.
5. Kill-switch ne dozvoljava novi response/tool.
6. Nepoznat tool se ne izvršava.
7. Confirmation UI prikazuje sve kritične argumente.
8. Model ne može uključiti Computer Mode.

### S-09 — HIGH: packaged mutable data folder je na pogrešnom mjestu

`electron/services/pythonProcess.cjs:181-205` postavlja `dataDir` na `process.resourcesPath/ricky_backend/data`. Kod standardne instalacije to je najčešće pod `Program Files`, gdje običan korisnik nema write dozvolu.

**Posljedice**

- SQLite/screenshot/image write može pasti;
- aplikacija može tražiti nepotrebna admin prava;
- reinstall/update može obrisati podatke.

**Preporuka**

Sidecar ostaje read-only u `resources`, a svi mutable podaci idu u `app.getPath("userData")`, npr. `%APPDATA%/Ricky/data`. Installer testirati kao standardni korisnik bez elevacije.

### S-10 — MEDIUM: neočekivani handler exception može zaobići uredan audit

`ToolExecutor` hvata samo `ValueError`. `RuntimeError`, `OSError`, `AppError`, COM, HTTP ili SQLite greška može izaći kao generičan 500, ostaviti execution state u `commit_started` i preskočiti action log.

**Preporuka**

- posebno hvatati `AppError`;
- catch-all pretvoriti u redigovani `TOOL_EXECUTION_FAILED`;
- u `finally` osigurati terminalni state i action log;
- stack trace ostaviti samo u lokalnom redigovanom dev logu.

### S-11 — MEDIUM: nekontrolisana navigacija iz artefakata

`ArtifactPanel.tsx` renderuje HTTPS linkove sa `target="_blank"`. Nisu pronađeni `setWindowOpenHandler` ni `will-navigate` guardovi. Mermaid je ispravno postavljen na `securityLevel: "strict"`, a CSP je potvrđen, ali navigacija ostaje posebna granica.

**Preporuka**

- deny-by-default `setWindowOpenHandler` na svakom BrowserWindowu;
- blokirati renderer navigation;
- dozvoljene `https:` linkove otvarati u sistemskom browseru nakon validacije i prikaza hostname-a;
- odbiti `file:`, `javascript:`, `data:` i custom protokole.

### S-12 — MEDIUM: action-log redakcija je nepotpuna

Rediguju se `text`, `body`, `content`, `password`, `secret`, `token` i slični ključevi. Ne rediguju se `query`, `prompt`, recipient/to, subject, putanje fajlova i naslovi prozora. Web query i image prompt zato mogu ostati u plaintext SQLite action logu.

**Preporuka**

Tool manifest treba imati audit policy: `full`, `metadata_only`, `redacted_fields`, `no_payload`. Outbound, file i computer-use alati podrazumijevano koriste `metadata_only`.

### S-13 — MEDIUM: at-rest i lokalni token hardening

- auth koristi običan `token != expected`, ne `secrets.compare_digest()`;
- dev token se zapisuje kao plaintext `dev_local_token.txt` bez eksplicitnog Windows ACL-a;
- SQLite, razgovori, notes, screenshots i legacy JSON nisu enkriptovani at rest.

**Preporuka**

- `compare_digest`;
- user-only ACL na data folderu;
- Windows DPAPI/Credential Manager za trajne tajne;
- prije osjetljivih dokumenata uvesti SQLCipher ili drugi at-rest model;
- centralni „Delete all local data“ i granularna retencija.

### S-14 — LOW: cancellation registry raste tokom cijele sesije

Završeni `ExecutionRecord` objekti se ne uklanjaju. Za desktop sesiju je rizik mali, ali dugotrajni rad nepotrebno povećava memoriju.

**Preporuka:** bounded retention ili uklanjanje terminalnih zapisa nakon kratkog debug perioda.

### S-15 — LOW: dokumentacioni drift

Neki komentari i tracker pasusi još opisuju stare fail-open ili legacy uslove koji više nisu tačni. Runtime može biti ispravan, ali pogrešan komentar povećava vjerovatnoću buduće regresije.

**Preporuka:** mali docs-only sync nakon sigurnosnih PR-ova, uz tracker kao izvor istine.

## 6. Potvrđene jake strane

- named preload IPC bez generic channel passthrougha;
- `contextIsolation=true`, `nodeIntegration=false`, `sandbox=true`, `webSecurity=true`;
- produkcijski CSP stvarno generisan, bez inline/eval skripti;
- backend sluša na loopback adresi;
- Bearer token dependency na svim FastAPI rutama;
- trajni OpenAI ključ ostaje u Python backendu;
- Realtime renderer dobija ephemeral credential;
- backend runtime argument validation;
- jedan Python `ToolExecutor` za REST i agent runtime;
- payload hash/tool binding kada confirmation ima `tool_name`;
- external-content taint i outbound escalation;
- legacy fallback isključen po defaultu;
- high-risk write alati fail-closed na legacy putu;
- log filter rediguje API ključeve i session token;
- screenshot retencija i delete-all;
- Mermaid strict režim;
- backend test suite prolazi;
- nema poznatih npm production ranjivosti u trenutnom auditu.

## 7. Preporučeni redoslijed malih PR-ova

### Security PR A — zatvoriti P0 computer gate

- ukloniti model-facing `set_mode`;
- privremeno deaktivirati `computer_open_app`;
- ukloniti `shell=True`;
- uvesti fiksni app alias allowlist;
- red-team testovi.

### Security PR B — file/privacy boundary za thumbnails

- native file picker;
- approved opaque file IDs;
- path sandbox + MIME/size/symlink provjera;
- cloud-send confirmation i action receipt;
- migracija legacy thumbnail file logike u Python.

### Security PR C — jednokratne confirmations

- `consuming/consumed` statusi;
- `execution_id` binding;
- atomic DB transition;
- replay/concurrency testovi.

### Security PR D — honest cancellation

- precizne UI poruke;
- `ExecutionContext`;
- handler checkpointi;
- registry cleanup.

### Security PR E — UIA privacy i target binding

- session target allowlist;
- sensitive-app denylist;
- PID/HWND binding;
- first-read consent;
- TOCTOU testovi.

### Security PR F — frontend safety tests

- Vitest samo za Realtime/confirmation/kill-switch jezgru;
- bez pokušaja da se odmah testira cijeli UI.

### Production PR G — packaging/data

- `app.getPath("userData")`;
- standard-user installer test;
- ACL/retention/migration provjera.

### Hardening PR H

- ToolExecutor catch-all audit;
- external navigation policy;
- audit metadata policy;
- `compare_digest`;
- rate/concurrency limit;
- Python dependency scan u CI.

## 8. Release preporuka

### Trenutno

- lokalni razvoj: dozvoljen uz svijest o rizicima;
- privatni test jednog developera: dozvoljen ako su P0 toolovi deaktivirani;
- širi beta test sa computer-use/thumbnail funkcijama: **ne preporučuje se**;
- javni produkcijski release: **nije dozvoljen** dok Security Gate 1/2 i P0/P1 nalazi nisu zatvoreni.

### Minimalni uslov za ograničenu betu

Obavezno zatvoriti S-01, S-02, S-03 i S-04. Za S-05 UI mora makar iskreno prikazivati da je cancellation samo zatražen. UIA read alati trebaju biti ograničeni ili privremeno deaktivirani dok S-06/S-07 nisu riješeni.

## 9. Konačni zaključak

Naš-agent ima dobru sigurnosnu arhitekturu na nivou slojeva, ali tri konkretna legacy/voice integraciona puta trenutno zaobilaze tu arhitekturu: model-kontrolisan Computer Mode, shell fallback i proizvoljna lokalna thumbnail referenca. To nisu razlozi za rewrite. Naprotiv, problemi su jasno locirani i mogu se zatvoriti kroz nekoliko malih PR-ova.

Najbolji naredni potez je Security PR A: ukloniti modelu pravo da uključuje Computer Mode i ukloniti `shell=True`. Nakon toga treba zatvoriti lokalni file/cloud privacy put i jednokratnost confirmations. Tek zatim ima smisla ulagati u šire UIA mogućnosti, accessibility proširenja ili javno pakovanje aplikacije.
