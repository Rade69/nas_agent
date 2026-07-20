# Security Hardening Roadmap — preostali rad

**Datum:** 2026-07-19
**Autor:** pi (security assessment nakon P2-K/P3-L/P3-M)
**Ulazni dokument:** `docs/SECURITY_FIX_PLAN_2026-07-19_FOR_PI.md` (zatvoren u potpunosti)
**Svrha:** plan realizacije preostalih bezbjednosnih stavki identifikovanih u procjeni
  zrelosti aplikacije. Ovo nije hitan posao — sve P1–P3 rupe su zatvorene.
  Ovaj dokument pokriva dubinsku odbranu i robusnost na nivou ispod "rupa" a
  iznad "utopije".

---

## 0. Stanje prije početka

**Završeno (3 commit-a):**
- `f9870ec` — P1-A, P1-B, P1-C, P2-D, P2-E, P2-F
- `ccd2f43` — P3-G, P3-H, P3-I, P3-J
- `8f2fb34` — P2-K, P3-L, P3-M

**Procjena zrelosti:** 7.5–8/10 za kategoriju (lokalni desktop AI agent sa
computer-use). Glavne prijetnje više nisu rupe u arhitekturi, već inherentni
rizici kategorije: nešifrovani podaci u mirovanju, legacy put, i sam
computer-use.

---

## 1. Prioriteti i zavisnosti

Stavke su poredane po **ROI** (uticaj na bezbjednost ÷ kompleksnost), ne
samo po težini. Faze se mogu raditi nezavisno osim gdje je eksplicitno
naznačena zavisnost.

| Faza | Stavka | Težina | ROI | Zavisnost |
|------|--------|--------|-----|-----------|
| H1 | SQLCipher — šifrovanje baze u mirovanju | Srednja | Visok | — |
| H2 | Šifrovanje screenshot fajlova u mirovanju | Srednja | Visok | H1 (djelimično) |
| H3 | FDE/BitLocker — dokumentacioni + detekcija | Niska | Srednji | — |
| H4 | Potpuno uklanjanje legacy PowerShell puta | Srednja-visoka | Srednji | Test pokrivenost computer_* |
| H5 | filesystem_search — ograničenje opsega + saglasnost | Srednja | Srednji | — |
| H6 | Formalni sigurnosni audit treće strane | Niska (koordinacija) | Visok | H1–H5 po mogućnosti |
| H7 | Electron/Chromium surface — mitigacija | Niska-kontinualna | Srednji | — |

---

## H1. SQLCipher — šifrovanje SQLite baze u mirovanju

### Problem
SQLite baza (`tool_runs`, `confirmations`, `plans`, `agent_conversations`,
`notes`, `records`, `browser_bridge_credentials`) stoji u čistom obliku na
disku. `os.chmod(0o600)` na Windows-u samo toggla read-only bit i **ne**
enforca owner-only ACL (`db.py:307` to već dokumentuje). Ko god ima pristup
fajl sistemu (ili malware sa pravima korisnika) može čitati cijelu istoriju
razgovora, planove, i credential-e.

### Pristup
SQLCipher je transparentni layer preko sqlite3 koji šifruje cijeli fajl
AES-256-CBC po strani. Python pristup:

1. **Dependency:** `pysqlcipher3` (ili `sqlcipher3-binary` na Windows-u).
   Provjeriti da li postoji wheel za Windows/Python 3.14 — ovo je najveći
   rizik ove faze (binary wheel dostupnost).
2. **Ključ:** izvesti iz postojećeg `settings.local_token` (već je
   `secrets.token_urlsafe(32)`) ili iz posebnog master key-a u
   `config.py`. Nikad ne hardkodovati.
3. **Migracija postojeće baze:** postoji jedan dev fajl. Napisati
   `_migrate_to_encrypted()` koja: otvori staru baze čisto, isprazni u
   memoriju, otvori novu šifrovanu, prebaci podatke, obriše staru.
   Jednokratno, pri pokretanju.
4. **API kompatibilnost:** `pysqlcipher3` je drop-in za `sqlite3` —
   jedina izmjena je `conn.execute("PRAGMA key = '...'")` poslije `connect()`.

### Koraci
1. Provjeriti dostupnost `pysqlcipher3` / `sqlcipher3-binary` wheel-a za
   Windows + Python 3.14. Ako nema — istražiti `sqlcipher-wasm` ili
   alternativu. **Ovo je go/no-go tačka.**
2. Dodati `ENCRYPTION_KEY` u `config.py` (izvući iz `local_token` ili
   novog env var-a `RICKY_DB_KEY`).
3. Izmijeniti `db.connect()` da postavi `PRAGMA key` i provjeri da je
   šifrovanje aktivno (`PRAGMA cipher_version`).
4. Napisati migraciju u `initialize_database()` — detektuje nešifrovanu
   bazu, preseli podatke, obriše staru.
5. Testirati: baza se ne otvara bez ključa, stare baze se migriraju
   transparentno, svi postojeći testovi prolaze.

### Kriterij prihvatanja
- `sqlite3` klijent van aplikacije ne može pročitati bazu (greška ili
  smešten sadržaj).
- Postojeća dev baza se migrira bez gubitka podataka.
- Svi pytest testovi prolaze.
- `cipher_version` se loguje pri startup-u (potvrda da je aktivno).

### Kompleksnost
~2–3 dana, u zavisnosti od wheel dostupnosti. Glavni rizik: ako
`pysqlcipher3` nema Windows wheel, alternativa je SQLCipher C library +
`ctypes` binding (značajno više posla).

### Blast radius
`db.py:connect()` je pozvan iz **svih** repozitorijuma (`agent_repo`,
`notes_repo`, `confirmation_repo`, `event_repo`, `artifact_repo`,
`screenshot_repo`, `browser_bridge_credential_repo`). Mora se testirati
da svi i dalje rade.

---

## H2. Šifrovanje screenshot fajlova u mirovanju

### Problem
Screenshot-ovi u `data/screenshots/` stoje kao PNG fajlovi na disku. Mogu
sadržati tuđe osjetljive podatke (mejlovi, dokumenti, chat prozori).
P3-G je dodao retenciju (30 dana) i `DELETE_SCREENSHOTS_ON_EXIT`, ali
fajlovi u međuvremenu su čisti.

### Pristup
Šifrovati fajl po snimanju, dešifrovati samo in-memory pri serviranju.

1. **Ključ:** isti master key iz H1 (jedan ključ za bazu i fajlove).
2. **Format:** AES-256-GCM (autentifikovan) po fajlu. Nonce se generiše
   po snimanju i sprema u header fajla.
3. **Lokacija:** `screenshot_service.py:record()` šifruje fajl prije
   disk write-a. `screenshot_service` već ima `_delete_file()`.
4. **Serviranje:** endpoint koji vraća screenshot dešifruje u memoriji
   i šalje kao `image/png` (ne fajl sa diska).
5. **Migracija:** postojeći PNG-ovi se šifruju pri prvom startup-u nakon
   nadogradnje.

### Koraci
1. Dodati `crypto.py` modul u `app/core/` sa `encrypt_file()` /
   `decrypt_to_bytes()` (AES-GCM, `cryptography` biblioteka — vjerovatno
   već u deps preko OpenAI SDK).
2. Izmijeniti `ScreenshotService.record()` da šifruje prilikom snimanja.
3. Izmijeniti screenshot endpoint da dešifruje pri serviranju.
4. Napisati migraciju postojećih PNG-ova (šifruj sve u `data/screenshots/`).
5. Testirati: fajl na disku nije validan PNG, endpoint vraća validan image,
   `DELETE_SCREENSHOTS_ON_EXIT` i dalje radi.

### Kriterij prihvatanja
- `data/screenshots/*.png` se ne otvara u image viewer-u (šifrovano).
- HTTP endpoint i dalje vraća validan PNG.
- Retencija (P3-G) i `DELETE_SCREENSHOTS_ON_EXIT` i dalje rade.

### Kompleksnost
~1.5–2 dana. `cryptography` biblioteka je vjerovatno već dostupna.

### Zavisnost
H1 mora biti urađen prvo (master key mehanizam se dijeli).

---

## H3. FDE/BitLocker — dokumentacioni + detekcija

### Problem
Ni SQLCipher ni šifrovanje fajlova ne štite ako napadač ima pristup
dok je aplikacija pokrenuta (ključ je u memoriji) ili ako OS swap-uje
memoriju na disk. Prava zaštita u mirovanju je **Full Disk Encryption**
(BitLocker na Windows-u).

### Pristup
Ovo je prvenstveno **dokumentaciona i detekciona** stavka, ne kodna.

1. **Dokumentacija:** dodati sekciju u `README` / `docs/` koja
   preporučuje BitLocker i objašnjava zašto.
2. **Detekcija:** pri startup-u provjeriti da li je disk šifrovan
   (PowerShell `Get-BitLockerVolume` preko `subprocess`) i logovati
   upozorenje ako nije. Ne blokirati — samo informisati.
3. **Settings panel:** opciono dodati indikator u UI ("Disk encryption:
   active / not detected").

### Koraci
1. Dodati `check_disk_encryption()` u `app/core/security_status.py`
   (novi modul) — `subprocess.run(["powershell", "-Command",
   "Get-BitLockerVolume"])` sa timeout-om, parsira `ProtectionStatus`.
2. Logovati `WARNING` ako nije `On`.
3. Dodati dokumentaciju.

### Kriterij prihvatanja
- Startup log pokazuje status disk šifrovanja.
- Dokumentacija postoji i objašnjava BitLocker preporuku.

### Kompleksnost
~0.5 dana.

---

## H4. Potpuno uklanjanje legacy PowerShell puta

### Problem
`electron/tools_legacy/powershell/*` (6 fajlova) i `electron/core/legacyTools.cjs`
su drugi put do OS automatizacije koji **ne prolazi** kroz Python permission
engine (blocked_apps, active-window, prompt-injection eskalacija). Trenutno
je feature-flagovan OFF (`RICKY_USE_LEGACY_POWERSHELL_TOOLS=0` po defaultu,
P3-H), ali kod postoji i može se uključiti.

### Pristup
Uklanjanje se radi **tek kad Python computer_* alati budu testirani za sve
slučajeve**. Ne uklanjati dok god postoji jedan scenario koji legacy put
radi a Python ne.

1. **Inventar:** šta legacy put radi? `computerClick`, `computerOpenApp`,
   `computerPressKey`, `computerScroll`, `computerTypeText`, `runPowerShell`.
   Uporediti sa Python ekvivalentima u `python_backend/app/tools/system/`.
2. **Gap analiza:** za svaki legacy alat, provjeriti da li Python
   ekvivalent pokriva istu funkcionalnost (koordinate, modifier keys,
   scroll delta, app allowlist). Dokumentovati razlike.
3. **Test pokrivenost:** dodati testove za Python computer_* alate koji
   pokrivaju sve scenarije koje legacy radi.
4. **Brisanje:** obrisati `electron/tools_legacy/` i `legacyTools.cjs`,
   ukloniti `LEGACY_FLAG` logiku iz `main.cjs`.
5. **Ažuriranje docs:** `docs/LEGACY_TOOLS.md` se briše ili mijenja u
   "Legacy put je uklonjen (datum)".

### Koraci
1. Napraviti inventar tabelu (legacy alat → Python ekvivalent → status).
2. Pokrenuti sve computer_* alate kroz ručno testiranje (klik, kucanje,
   scroll, app open).
3. Dodati regression testove za Python alate.
4. Obrisati legacy fajlove i flag.
5. Ažurirati `docs/MIGRATION_PLAN.md` i `docs/LEGACY_TOOLS.md`.

### Kriterij prihvatanja
- `electron/tools_legacy/` ne postoji.
- `RICKY_USE_LEGACY_POWERSHELL_TOOLS` env var se više ne čita.
- Svi computer_* alati rade kroz Python put.
- Regression testovi pokrivaju klik/kucanje/scroll/open.

### Kompleksnost
~3–4 dana (najviše vremena ide u test pokrivenost i gap analizu, ne samo
brisanje).

### Napomena
`AGENTS.md` kaže: "Ne brisati legacy PowerShell computer-use toolove dok
Python zamjena nije testirana." Ova faza je upravo to — testiranje pa
brisanje.

---

## H5. filesystem_search — ograničenje opsega + saglasnost

### Problem
`filesystem_search` pretražuje **sve diskove + home** i vraća pune putanje
modelu (i ka OpenAI). P2-F je dodao `SENSITIVE_DIR_NAMES` filter, ali opseg
i dalje obuhvata cijeli fajl sistem. Nema saglasnosti korisnika za pretragu
izvan `data_dir`/home.

### Pristup (izabrana opcija iz P2-F dokumentacije)
Kombinacija (a) + (c) iz originalnog P2-F nalaza:

1. **Default opseg:** pretraga po defaultu ograničena na `data_dir` +
   korisnički home (`Path.home()`).
2. **Proširena pretraga (drugi diskovi):** zahtijeva confirmation (medium
   risk) — korisnik eksplicitno odobrava pretragu cijelog sistema.
3. **Klasifikacija:** alat ostaje `reads_external_content=True` (već jeste)
   tako da ulazi u prompt-injection eskalaciju (P2-K sada per-conversation).

### Koraci
1. Dodati argument `scope` u `filesystem_search` tool definition:
   `"home"` (default) ili `"all_drives"`.
2. U `filesystem_search.py`, ako je `scope="all_drives"`, postaviti risk
   na `medium` + `requires_confirmation=True` (preko tool definition-a).
3. Default `scope="home"` ostaje `low` risk.
4. Testirati: default pretraga ne ide van home, proširena traži potvrdu.
5. Ažurirati `reads_external_content` klasifikaciju (već tačna).

### Kriterij prihvatanja
- Default pretraga ne dira diskove van home.
- `scope="all_drives"` traži confirmation.
- Alat ulazi u prompt-injection eskalaciju (P2-K).

### Kompleksnost
~1 dan.

---

## H6. Formalni sigurnosni audit treće strane

### Problem
Sve dosadašnje procjene su interni pregledi (Claude/pi). Iako temeljne,
nema nezavisne validacije. Kontrole izgledaju ispravno, ali "izgleda
ispravno" ≠ "dokazano ispravno".

### Pristup
Ovo je **koordinaciona** stavka, ne kodna.

1. **Scope:** definisati šta se auditira (backend, Electron, computer-use
   tok, browser bridge, auth, storage). Ovaj dokument + svi agent_reports
   + `SECURITY_FIX_PLAN_2026-07-19_FOR_PI.md` su ulazni materijal.
2. **Tip audit-a:** pentest (crveni tim pokušava eksploataciju) +
   code review (bijeli tim čita kod). Za single-user alat, code review
   je verovatno dovoljan za prvi krug.
3. **Izvođač:** eksterna firma ili samostalni bezbjednosni inženjer sa
   iskustvom u Electron + Python stack-u.
4. **Izlaz:** izvještaj sa nalazima, po istom formatu kao
   `SECURITY_FIX_PLAN_2026-07-19_FOR_PI.md` (težina, lokacija, ispravka,
   kriterij).
5. **Pratnja:** nalazi se implementiraju kroz nove faze u ovom roadmap-u.

### Koraci
1. Sastaviti audit brief (scope, ulazni materijali, očekivani izlaz).
2. Identifikovati izvođača.
3. Sprovesti audit.
4. Prioritizirati nalaze i dodati kao faze u ovaj dokument.

### Kriterij prihvatanja
- Izvještaj treće strane postoji u `docs/`.
- Nalazi su prioritetizirani i dodati u roadmap.

### Kompleksnost
Niska za kod (samo koordinacija), ali zahtijeva budžet/vrijeme.

### Preporuka
Raditi nakon H1–H5, da auditor vidi zrelo stanje, ne polovično.

---

## H7. Electron/Chromium surface — mitigacija (kontinualno)

### Problem
Electron nosi Chromium engine sa svim njegovim CVE-ovima. Ovo je
inherentna cijena stack-a, ne greška. Detaljna analiza zamjene je u
odvojenom odgovoru (sažeto: ne zamjenjuju sada, mitigacija je jeftinija).

### Pristup (mitigacija, ne eliminacija)
Ovo je **kontinualni ritual**, ne jednokratna faza.

1. **Electron verzija:** pin-ovati i redovno dizati. Pratiti
   `electron/releases` i Electron security blog. Cilj: biti unutar 1 minor
   verzije od najnovijeg stable.
2. **npm audit:** već u `npm run quality` (P3-J). Dodati da fail-a build
   na `high` ili `critical` (ako već ne fail-a).
3. **CSP:** provjeriti da je Content-Security-Policy strog u
   `window.cjs`. Ako nema CSP header-a, dodati.
4. **Dependency最小изация:** redovno prolaziti kroz `package.json` i
   uklanjati neiskorištene zavisnosti (manje zavisnosti = manje attack
   surface-a).
5. **Electron security checklist:** redovno prolaziti kroz zvanični
   Electron security checklist i provjeravati svaku stavku.

### Koraci
1. Provjeriti trenutnu Electron verziju (`^42.5.1`) i uporediti sa
   najnovijom. Ažurirati ako zaostaje.
2. Dodati CSP header u `window.cjs` ako ne postoji.
3. Dodati `npm audit --audit-level=high` gate u `npm run quality`.
4. Mjesečni ritual: provjeriti Electron + npm zavisnosti.

### Kriterij prihvatanja
- `npm audit` ne prijavljuje high/critical.
- CSP header postoji i strog je.
- Electron verzija je ažurna (unutar 1 minor-a).

### Kompleksnost
Niska po rundi, kontinualno.

---

## 2. Preporučeni redoslijed

```
H3 (FDE detekcija) ──────────────────────► (nezavisno, brzo)
H5 (filesystem_search scope) ────────────► (nezavisno, brzo)
H1 (SQLCipher) ─────► H2 (screenshot šifrovanje)
H4 (legacy uklanjanje) ──────────────────► (nezavisno, ali testiranje)
H7 (Electron mitigacija) ────────────────► (kontinualno)
H6 (audit treće strane) ─────────────────► (nakon H1–H5)
```

**Prvi kvartal:** H3 + H5 (brzi win-ovi, niska kompleksnost).
**Drugi kvartal:** H1 → H2 (šifrovanje u mirovanju, najveći ROI).
**Treći kvartal:** H4 (legacy uklanjanje, zahtijeva test pokrivenost).
**Kontinualno:** H7.
**Kada budžet dozvoli:** H6.

---

## 3. Šta NIJE u ovom planu (i zašto)

- **Electron zamjena (Tauri/Qt):** posebna analiza, ne u ovom roadmap-u.
  ROI nije dovoljno jak dok je Python backend migracija u toku. Vidi
  odgovor u chatu za detalje.
- **Computer-use eliminacija:** fundamentalni rizik kategorije, ne može
  se ukloniti bez promjene domene aplikacije.
- **Multi-user / RBAC:** aplikacija je single-user po dizajnu; RBAC bi
  bio over-engineering.
- **Network-level hardening (TLS za lokalne konekcije):** localhost
  loopback ne koristi TLS, što je prihvatljivo za single-user. Ako se
  ikad izloži mreži, ovo postaje hitno.
