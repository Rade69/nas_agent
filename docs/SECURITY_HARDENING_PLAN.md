# SECURITY_HARDENING_PLAN.md — RileyJarvis Windows Hybrid

## Status

Ovaj dokument je novi sigurnosni plan za RileyJarvis.

Cilj nije da se sigurnost doda na kraju. Cilj je da sigurnost bude ugrađena u samu izgradnju aplikacije.

Ovaj dokument treba čitati zajedno sa:

```txt
ARCHITECTURE_VOICE_FIRST_REVISED.md
SECURITY_MODEL.md
TOOL_CONTRACTS.md
MIGRATION_PLAN.md
AGENTS.md / CLAUDE.md
```

Ako postoji konflikt između ovog dokumenta i ranijeg blažeg security plana, ovaj dokument ima prioritet za produkcijski build.

---

# 0. Osnovni princip

Ne postoji softver bez mogućnosti greške.

Ali RileyJarvis mora biti građen po principu:

```txt
secure-by-design
secure-by-default
least privilege
fail closed
defense in depth
human gate for risky actions
```

To znači:

```txt
- sigurnost se ne dodaje na kraju,
- opasne akcije su blokirane po defaultu,
- model nikada nije sigurnosna granica,
- tool executor je sigurnosna granica,
- renderer nikada ne dobija punu moć nad OS-om,
- Python backend nikada ne sluša javno na mreži,
- standardni API key nikada nije u rendereru,
- dokumenti su nepouzdani podaci, ne instrukcije,
- osjetljivi dokumenti ne idu u cloud bez jasne korisničke dozvole,
- produkcijski build ne prolazi ako Security Self-Test ne prođe.
```

---

# 1. Trenutni kritični rizik

Postojeći `SECURITY_MODEL.md` već definiše risk levele i permission pravila, ali navodi da legacy PowerShell computer-use alati trenutno rade direktno iz `electron/main.cjs` bez punog permission sloja.

To je privremeno prihvatljivo samo u lokalnom development prototipu.

Za produkciju:

```txt
Legacy PowerShell computer-use path bez permission engine-a je BLOCKER.
```

Pravilo:

```txt
Nijedan produkcijski build ne smije izložiti click/type/keypress/scroll/open-app toolove
bez centralnog permission/risk/confirmation sloja.
```

---

# 2. Security Gates

Sigurnost nije jedna faza na kraju.

Uvesti obavezne security gate-ove.

## Security Gate 0 — prije širenja funkcija

Ovo mora postojati prije novih computer-use, document-engine ili tool funkcija.

Obavezno:

```txt
- Electron hardening
- IPC allowlist
- no generic IPC invoke
- Python backend localhost-only
- local auth token za backend
- OpenAI API key nikad u rendereru
- Realtime session endpoint preko backend-a
- no arbitrary shell
- tool manifest model
- risk levels
- confirmation_id model
- active window validation za computer-use
- log redaction
- path sandbox
- security self-test MVP
```

Ako Gate 0 nije urađen:

```txt
- ne dodavati nove opasne toolove,
- ne širiti PowerShell path,
- ne izlagati computer-use van lokalnog prototipa,
- ne praviti production installer.
```

## Security Gate 1 — prije beta/test korisnika

Obavezno:

```txt
- Document privacy modes
- prompt injection boundaries
- local_only mode
- redacted_cloud mode
- Action Receipt sa privacy statusom
- tool execution audit trail
- rate limits
- oversized input protection
- dependency scanning
- CI security checks
- production config validation
```

## Security Gate 2 — prije production release-a

Obavezno:

```txt
- code signing
- signed updates ako auto-update postoji
- encrypted secrets storage
- encrypted/safe local data storage za osjetljive podatke
- security self-test hard fail
- no devtools/debug in production
- no remote debugging
- no remote JS
- penetration test checklist
- incident/recovery plan
- local data delete/export controls
```

---

# 3. Threat model

## Assets koje štitimo

```txt
- OpenAI API key
- Realtime session credentials
- local auth token
- SQLite baza
- transcripts
- activity logs
- screenshots
- artifacts
- user documents
- review packets
- action receipts
- OS-level control preko computer-use toolova
- clipboard sadržaj
- active window context
```

## Napadači / izvori rizika

```txt
- malicious document / PDF / email
- prompt injection u dokumentu ili web stranici
- XSS u Electron rendereru
- malicious dependency
- local malware koji pokušava koristiti localhost backend
- neovlašćen proces na računaru
- compromised update
- loše implementiran tool
- model output koji pokušava iznuditi akciju
- korisnik koji slučajno odobri pogrešnu stvar
```

## Najveći rizici

```txt
1. Electron XSS -> RCE
2. Preširok IPC
3. API key u rendereru
4. Backend sluša na 0.0.0.0 ili bez auth tokena
5. Prompt injection iz dokumenata
6. Agent sa previše tool ovlašćenja
7. Legacy PowerShell bez permission sloja
8. Osjetljivi dokumenti poslati cloud modelu bez dozvole
9. Tajne vrijednosti u logovima
10. File path traversal / symlink escape
11. Supply-chain napad kroz npm/pip dependency
12. Unsigned update / tampered installer
```

---

# 4. Electron hardening

Electron renderer ne smije imati Node.js moći.

## Production BrowserWindow pravila

Za svaki renderer prozor:

```ts
webPreferences: {
  nodeIntegration: false,
  contextIsolation: true,
  sandbox: true,
  webSecurity: true,
  allowRunningInsecureContent: false,
  enableRemoteModule: false,
  preload: path.join(__dirname, "preload.cjs")
}
```

Zabranjeno u produkciji:

```txt
nodeIntegration: true
contextIsolation: false
sandbox: false
webSecurity: false
allowRunningInsecureContent: true
enableRemoteModule: true
```

## Content Security Policy

U produkciji mora postojati CSP.

Minimalni smjer:

```txt
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:;
media-src 'self' blob:;
connect-src 'self' https://api.openai.com http://127.0.0.1:* ws://127.0.0.1:*;
object-src 'none';
base-uri 'none';
frame-ancestors 'none';
```

Ne koristiti remote CDN skripte u produkciji.

## DevTools / debug

Produkcija:

```txt
devTools disabled by default
remote debugging disabled
no --disable-web-security
no --no-sandbox
no verbose debug logs
```

Ako se uključi debug mode, mora biti:

```txt
- samo dev build,
- jasno označen,
- nikad u produkcijskom installeru.
```

---

# 5. Preload i IPC allowlist

Preload smije izložiti samo eksplicitne funkcije.

Dozvoljeno:

```ts
window.ricky = {
  app: {
    quit(),
    minimize(),
    maximize(),
    enterCompanionMode(),
    exitCompanionMode()
  },
  voice: {
    start(),
    stop(),
    interrupt(),
    mute(),
    unmute()
  },
  realtime: {
    getSession()
  },
  backend: {
    getStatus()
  },
  confirmation: {
    approve(id),
    reject(id)
  },
  companion: {
    restoreMainWindow(),
    savePosition(position),
    getPosition()
  }
}
```

Zabranjeno:

```txt
window.require
window.fs
window.child_process
window.powershell
window.ipcRenderer
ipcRenderer.invoke(anyChannel, anyPayload)
generic execute
generic shell
generic file read/write
```

## IPC handler pravila

Svaki IPC handler mora imati:

```txt
- allowlisted channel
- schema validation payload-a
- sender/window validation
- app state validation
- risk validation
- permission validation
- audit log
```

Ako bilo šta ne prođe:

```txt
BLOCKED
```

Ne tražiti od modela da odluči.

---

# 6. Python backend hardening

Python backend mora biti lokalni servis.

Obavezno:

```txt
host = 127.0.0.1
nikad 0.0.0.0
random port ili konfigurisan lokalni port
per-session local auth token
CORS samo za Electron app
Origin check za WebSocket
rate limit po endpointu
request size limit
structured input validation
```

## Local auth token

Na startu aplikacije:

```txt
Electron/Python generišu kratkoživući local_session_token.
Token se koristi za sve requestove prema backend-u.
Token se ne čuva trajno.
Token se ne loguje.
```

Svaki request mora imati:

```txt
Authorization: Bearer <local_session_token>
```

Ako token nedostaje ili je pogrešan:

```txt
401 BLOCKED
```

## Backend ne smije biti javni API

Zabranjeno:

```txt
- slušanje na LAN adresi
- 0.0.0.0
- CORS *
- unauthenticated localhost endpoints
- open WebSocket bez origin/token provjere
```

---

# 7. Realtime / OpenAI key security

Standardni OpenAI API key nikada ne smije biti u rendereru.

Ispravan tok:

```txt
Renderer traži Realtime session
  -> Python backend koristi standardni OpenAI API key iz sigurnog storage-a
  -> Python backend kreira kratkoživući Realtime credential/session
  -> Renderer koristi samo kratkoživući credential za WebRTC
```

Zabranjeno:

```txt
- OPENAI_API_KEY u renderer env-u
- API key u localStorage/sessionStorage
- API key u preload-u
- API key u bundled JS-u
- API key u logovima
```

## Secrets storage

Za produkciju koristiti:

```txt
- Windows Credential Manager / DPAPI za API keys
- .env samo za development
- nikad commit .env.local
- nikad dijeliti .env korisnicima
```

---

# 8. Tool security model

Svaki tool mora imati manifest.

Primjer:

```json
{
  "name": "computer_type_text",
  "risk": "high",
  "enabled": true,
  "requires_computer_mode": true,
  "requires_confirmation": true,
  "requires_active_window_match": true,
  "allowed_apps": ["notepad.exe", "calc.exe"],
  "blocked_apps": ["powershell.exe", "cmd.exe", "regedit.exe"],
  "logs_action_receipt": true,
  "timeout_ms": 5000
}
```

## Tool executor provjere

Prije izvršenja toola:

```txt
1. Da li tool postoji u registry-ju?
2. Da li je enabled?
3. Da li payload prolazi schema validation?
4. Koji je risk level?
5. Da li risk level dozvoljava izvršenje?
6. Da li Computer Mode mora biti ON?
7. Da li je Computer Mode stvarno ON?
8. Da li postoji validan confirmation_id ako je potreban?
9. Da li confirmation_id odgovara baš toj akciji i payload-u?
10. Da li je active window dozvoljen?
11. Da li je path u allowed workspace-u?
12. Da li je network target dozvoljen?
13. Da li akcija može biti auditovana?
```

Ako bilo koji korak ne prođe:

```txt
BLOCKED
```

## Risk levels

```txt
low:
- health check
- list tools
- read local note metadata
- create local artifact
- screenshot bez OCR/upload-a

medium:
- open app
- inspect active window
- read file from allowed workspace
- search approved URL
- parse user-approved document locally

high:
- type text
- click
- press key
- paste clipboard
- edit file
- interact with browser
- upload selected document chunk to cloud model
- create export containing sensitive data

critical:
- delete files
- run shell command
- install package
- send email/message
- submit form
- pay
- sign
- execute arbitrary PowerShell/Python
- access secrets
- send sensitive documents to third party
```

## Default policy

```txt
low: allowed with logging
medium: maybe confirmation depending on context
high: Computer Mode + explicit confirmation required
critical: disabled by default / hard-block unless developer/admin allowlist
```

---

# 9. Computer-use security

Computer-use je najrizičniji dio aplikacije.

## Computer Mode

Computer-use toolovi ne rade ako:

```txt
Computer Mode = OFF
```

Za uključivanje Computer Mode-a:

```txt
- korisnik mora eksplicitno uključiti mode,
- UI mora jasno pokazati da je ON,
- companion orb mora pokazati da je ON,
- Computer Mode se automatski gasi nakon timeout-a ili restart-a.
```

## Active window validation

Za ove toolove:

```txt
computer_type_text
computer_click
computer_press_key
computer_scroll
paste_clipboard
```

obavezno:

```txt
- capture active window before
- validate process name
- validate window title if possible
- validate allowed_apps/blocked_apps
- capture active window after
- log result
```

Blocked apps po defaultu:

```txt
powershell.exe
cmd.exe
regedit.exe
taskmgr.exe
mmc.exe
credential manager
password managers
banking apps/sites
crypto wallets
remote desktop apps
system settings requiring admin
```

## Legacy PowerShell

Produkcija ne smije imati arbitrary PowerShell execution.

Dozvoljeno samo:

```txt
- strogo definisani wrapperi
- hardcoded safe commands
- no user/model generated shell
- no arbitrary -Command payload
```

Ako postoji shell tool:

```txt
risk = critical
enabled = false by default
developer_mode_required = true
```

---

# 10. File system sandbox

Ricky ne smije imati pristup cijelom disku.

Dozvoljeni prostori:

```txt
RickyData/
User-approved workspace folders
Temporary import folder
Explicitly selected files through file picker
```

Zabranjeni prostori:

```txt
C:\Windows
C:\Program Files
C:\Program Files (x86)
browser profile folders
password manager folders
SSH keys
.env files osim vlastitih dev fajlova
AppData secrets
Credential Manager exports
system registry hives
```

## Path validation

Za svaki path:

```txt
- canonicalize path
- resolve symlinks
- block ../ traversal
- block UNC/network paths unless explicitly allowed
- validate extension
- block executable/script extensions for execution
- enforce max file size
```

Zabraniti izvršavanje:

```txt
.exe
.bat
.cmd
.ps1
.vbs
.js
.msi
.scr
.reg
```

Osim ako postoji poseban admin/developer allowlist.

---

# 11. Network security

Aplikacija ne smije imati slobodan network egress za toolove.

Default allowlist:

```txt
https://api.openai.com
http://127.0.0.1:<backend_port>
ws://127.0.0.1:<backend_port>
approved update server ako postoji
```

Blokirati:

```txt
- LAN IP adrese osim ako korisnik dozvoli
- localhost portove osim vlastitog backend-a
- metadata IP adrese
- file:// remote učitavanje
- unknown domains
- arbitrary user/model generated URLs
```

## URL validation

Ako tool koristi URL:

```txt
- parse URL
- require https unless local backend
- block private IP ranges by default
- block redirects to blocked hosts
- log final resolved host
```

---

# 12. Document privacy model

Document Engine mora biti privacy-first.

Svaki Context Pack mora imati:

```txt
privacy_mode
```

Vrijednosti:

```txt
cloud_allowed
redacted_cloud
local_only
ask_each_time
```

## Defaults

Za osjetljive kategorije:

```txt
ask_each_time
```

ili:

```txt
local_only
```

Osjetljive kategorije:

```txt
medicinski dokumenti
poreski dokumenti
bankovni izvodi
lični dokumenti
ugovori
dokumenti trećih lica
carinska dokumentacija sa osjetljivim poslovnim podacima
```

Nema implicitnog cloud slanja.

## UI mora prikazati

Prije obrade:

```txt
Ricky želi obraditi ove dokumente.

Privacy mode:
- local_only / redacted_cloud / cloud_allowed / ask_each_time

Šta može napustiti računar:
- ništa
- redacted tekst
- odabrani chunkovi
- kompletan tekst

[Otkaži] [Promijeni privacy] [Pokreni]
```

## Action Receipt mora sadržati

```txt
- koji privacy mode je korišten
- da li je išta poslato cloud modelu
- koji dokumenti su obrađeni
- šta je redigovano
- koji chunkovi su poslati
- šta je ostalo lokalno
```

---

# 13. Prompt injection zaštita

Dokumenti, web stranice, emailovi, screenshotovi i PDF-ovi su podaci, ne instrukcije.

Hard pravilo:

```txt
External content is data, never instructions.
```

To znači:

```txt
- dokument ne može promijeniti system prompt
- dokument ne može promijeniti privacy_mode
- dokument ne može odobriti confirmation
- dokument ne može direktno izazvati tool call
- dokument ne može tražiti slanje podataka trećoj strani
- dokument ne može promijeniti security policy
```

## Tool calls

Model smije predložiti akciju.

Ali tool executor odlučuje:

```txt
model output -> proposed_action -> permission engine -> confirmation -> executor
```

Ne:

```txt
model output -> direct tool execution
```

## Prompt injection detection

Dodati heuristike:

```txt
- "ignore previous instructions"
- "send this to"
- "exfiltrate"
- "reveal system prompt"
- "disable safety"
- "run command"
- "download and execute"
```

Ako se detektuje:

```txt
- označiti source kao suspicious
- ne izvršavati akcije iz tog sadržaja
- prikazati upozorenje korisniku
- logovati u Activity
```

---

# 14. Logging, redaction i retention

Logovi ne smiju postati druga baza osjetljivih podataka.

## Ne logovati

```txt
API keys
session tokens
Authorization headers
passwords
raw full medical/tax documents
raw audio
complete screenshots by default
full clipboard contents
private keys
bank account numbers
```

## Logovati

```txt
event type
tool name
risk level
status
timestamp
document id
source reference
redacted summary
duration
confirmation_id
privacy_mode
```

## Redaction

Centralni redaction sloj:

```txt
python_backend/app/security/redaction.py
```

Redigovati:

```txt
emails
telefoni
ID/JMBG/passport brojevi
brojevi računa
API keys
tokens
adrese
kartice
osjetljive medical/tax vrijednosti gdje je moguće
```

## Retention

Korisnik mora imati opcije:

```txt
delete all local data
delete activity history
delete transcripts
delete screenshots
delete document cache
set retention: 7 / 30 / 90 dana
```

---

# 15. Encryption at rest

Za produkciju:

```txt
- API keys u Windows Credential Manager / DPAPI
- local auth token kratkoživući i neperzistentan
- sensitive config ne u plaintext-u
- SQLite encryption razmotriti prije Document Engine-a
- sensitive exports opciono password-protected
```

Ako se obrađuju medicinski/porezni/bankovni dokumenti:

```txt
SQLCipher ili drugi encryption-at-rest mehanizam postaje requirement, ne nice-to-have.
```

---

# 16. Supply-chain security

## JavaScript / Electron

```txt
- package-lock.json obavezan
- npm audit u CI
- dependency review
- no remote CDN scripts
- no untrusted postinstall scripts gdje je moguće
- pinovati kritične verzije
```

## Python

```txt
- requirements lock / uv lock / poetry lock
- pip-audit u CI
- pinovane verzije za kritične biblioteke
- virtualenv izolacija
```

## Build

```txt
- reproducible-ish build gdje je moguće
- clean build environment
- no secrets in build logs
- no .env in artifact
- SBOM kasnije ako projekat ide javno/komercijalno
```

---

# 17. Update i distribucija

Za produkcijski Windows build:

```txt
- code signing
- installer signing
- signed auto-update ako postoji
- HTTPS only update server
- update manifest signature validation
- no unsigned remote code
```

Ako update nije siguran:

```txt
auto-update = disabled
```

---

# 18. Production Security Self-Test

Aplikacija na startu production build-a mora pokrenuti security self-test.

Ako bilo šta od ovoga padne:

```txt
APP MUST FAIL CLOSED
```

Self-test provjere:

```txt
- nodeIntegration === false
- contextIsolation === true
- sandbox === true
- webSecurity === true
- allowRunningInsecureContent === false
- backend host === 127.0.0.1
- backend auth token exists
- backend does not accept unauthenticated requests
- CORS is not *
- standard OpenAI API key not present in renderer env
- no generic ipc invoke exposed
- no arbitrary shell tool enabled
- critical tools disabled by default
- log redaction enabled
- production devtools disabled
- remote debugging disabled
```

Ako self-test padne, UI prikazuje:

```txt
Security configuration failed.
Production mode blocked.
```

---

# 19. Security testing checklist

Prije release-a testirati:

```txt
Electron:
- XSS attempt
- CSP bypass
- preload exposure
- ipc channel abuse
- devtools/debug exposure

Backend:
- unauthenticated localhost request
- invalid token
- CORS abuse
- WebSocket origin abuse
- oversized payload
- malformed JSON
- rate limit

Tools:
- high tool without confirmation
- critical tool execution
- computer-use with Computer Mode OFF
- active window mismatch
- blocked app target
- path traversal
- symlink escape
- dangerous extension

LLM/document:
- prompt injection in PDF
- prompt injection in email/text
- document tries to change privacy_mode
- document tries to send data to third party
- cloud processing without user approval

Secrets:
- API key in renderer bundle
- token in logs
- .env in package
- sensitive document in activity log

Update/build:
- unsigned installer
- tampered update
- dependency vulnerability
```

---

# 20. Incident response

MVP mora imati barem osnovni recovery.

Dodati UI ili dokumentovanu opciju:

```txt
- revoke API key instructions
- clear local session
- delete all local data
- delete transcripts
- delete documents cache
- export audit log
- disable computer-use tools
- reset security settings to default
```

Ako se desi security incident:

```txt
1. disable affected tool
2. rotate API key
3. clear session credentials
4. inspect activity log
5. delete leaked local cache if needed
6. ship patched build
```

---

# 21. Development workflow rules

Svaki agent mora poštovati:

```txt
- ne uvoditi novi IPC kanal bez dokumentacije
- ne uvoditi novi tool bez manifest-a
- ne uvoditi novi endpoint bez auth/token provjere
- ne uvoditi document cloud processing bez privacy_mode
- ne uvoditi shell execution
- ne širiti electron/main.cjs business logikom
- ne commitovati .env
- ne dodavati dependency bez razloga
```

Ako repo koristi GitNexus/agent_reports:

```txt
- uraditi impact/context analizu prije rizičnih izmjena
- ostaviti report šta je promijenjeno
- navesti security impact
- navesti nove IPC/endpoints/tools
- navesti testove
```

---

# 22. Acceptance criteria za produkciju

Produkcijski build je dozvoljen samo ako:

```txt
- Security Gate 0 je kompletan
- Security Self-Test prolazi
- renderer nema standardni OpenAI API key
- backend sluša samo na 127.0.0.1
- backend ima local auth token
- IPC je allowlisted
- nema generic shell/powershell
- high/critical toolovi ne rade bez permission engine-a
- critical toolovi su disabled by default
- log redaction radi
- document privacy mode postoji prije Document Engine-a
- prompt injection boundary je dokumentovan i testiran
- production devtools/debug su disabled
- dependency scan nema kritične neriješene propuste
```

Ako nije ispunjeno:

```txt
NO PRODUCTION RELEASE
```

---

# 23. Instrukcija za Claude Code / Codex

Implementirati ovaj sigurnosni plan kao dokumentaciju i zatim kao gate-ove kroz postojeći `MIGRATION_PLAN.md`.

## Prvo uradi dokumentaciju

```txt
1. Dodaj SECURITY_HARDENING_PLAN.md.
2. Ažuriraj SECURITY_MODEL.md da referencira ovaj plan.
3. U MIGRATION_PLAN.md dodaj Security Gate 0 prije širenja computer-use toolova.
4. Ne renumerisati postojeće faze bez korisnikove odluke.
5. Ako postoji FAZA za permission layer kasno u planu, označiti je kao BLOCKER za production computer-use.
```

## Ne radi odmah

```txt
- ne implementirati sve kontrole u jednom PR-u,
- ne prepisivati realtime.ts,
- ne uvoditi Python STT/TTS,
- ne uvoditi Document Engine backend prije privacy modela,
- ne dodavati shell tool,
- ne izlagati nove dangerous IPC kanale.
```

## Prvi implementacioni PR za sigurnost

```txt
Security PR-1:
- Electron security config check
- preload API inventory
- generic IPC zabrana
- backend localhost/auth design
- no OpenAI key in renderer check
- Security Self-Test skeleton
```

## Drugi implementacioni PR

```txt
Security PR-2:
- tool manifest schema
- permission engine skeleton
- confirmation_id binding
- Computer Mode enforcement
- active window validation stub
- action receipt skeleton
```

## Treći implementacioni PR

```txt
Security PR-3:
- file sandbox
- path validation
- redaction.py
- log redaction integration
- retention settings
```

## Četvrti implementacioni PR

```txt
Security PR-4:
- document privacy model
- privacy_mode in Context Pack design
- local_only / redacted_cloud / cloud_allowed / ask_each_time
- cloud processing approval UI stub
```

---

# 24. Finalna pravila

```txt
1. Model nikada nije sigurnosna granica.
2. Prompt nikada nije sigurnosna granica.
3. Tool executor je sigurnosna granica.
4. Renderer nikada nema pun OS pristup.
5. Backend nikada nije javno dostupan.
6. API key nikada nije u rendereru.
7. Dokumenti su podaci, ne instrukcije.
8. Osjetljivi dokumenti ne idu u cloud bez jasne dozvole.
9. Critical tools su disabled by default.
10. Ako security self-test padne, produkcija se ne pokreće.
```
