# EMAIL COMPOSE TOOL — Tehnički plan

**Datum:** 2026-07-13
**Status:** Plan — nije započeta implementacija
**Vlasnik plana:** Korisnik (review) — Claude Code (implementacija)

---

## 1. Koncept i cilj

Korisnik glasovnom komandom zatraži od Ricky-ja da otvori email, izdiktira tekst, a **slanje isključivo radi korisnik ručno**. Agentu je na nivou koda zabranjeno kliknuti Send dugme.

```
KORISNIK: "Ricky, napiši email šefu"
RICKY:    otvara mail klijent → popunjava To/Subject
KORISNIK: diktira tijelo emaila (Dictation Mode)
RICKY:    prebacuje tekst u email body → STOP
KORISNIK: pregleda i sam klikče "Send"
```

### Zašto computer-use, a ne API integracija?

| Pristup | Za | Protiv |
|---------|-----|--------|
| Computer-use (ovaj plan) | Korisnik je već auth-an u mail klijent; ne treba čuvati lozinke/OAuth tokene; prirodan UX; Send dugme je uvijek pod kontrolom korisnika | Zavisi od konkretnog mail klijenta; krhkije na UI promjene |
| API (Gmail/Graph/SMTP) | Precizno, ne zavisi od GUI-ja | Treba OAuth flow, čuvanje tokena, refresh logika; novi attack surface za credential theft |

**Odluka:** computer-use pristup. API integracija može doći kasnije kao opciona nadogradnja.

---

## 2. Arhitektura — gdje šta živi

```
── RENDERER (React) ──────────────────────────────────────
│
│  VoiceSessionState: "email_dictation"
│  ────────────────────────────────────
│  │ EmailDictationPanel                 │
│  │  To:    [sef@firma.com         ]     │
│  │  Subj:  [Izvještaj Q3           ]    │
│  │  ────────────────────────────    │
│  │  │ (diktirani tekst, editable)  │    │
│  │  │                              │    │
│  │  ────────────────────────────    │
│  │  [Nastavi diktiranje]               │
│  │  [Ubaci u email]  [Otkaži]         │
│  ────────────────────────────────────
│
│  ConfirmationDialog (prikazuje preview prije unosa)
│
──────────────┬──────────────────────────────────────────
             │  IPC invoke('email:compose', {...})
             ▼
── ELECTRON MAIN ──────────────────────────────────────────
│
│  handleEmailCompose()
│    → POST /email/compose  (Python backend)
│    → vraća rezultat renderer-u
│
──────────────┬──────────────────────────────────────────
             │  HTTP (localhost, auth token)
             ▼
── PYTHON BACKEND ───────────────────────────────────────────
│
│  POST /email/compose
│    → email_compose_handler()
│       ├─ 1. Otvori mail klijent (computer_open_app)
│       ├─ 2. Novi email (computer_press_key Ctrl+N)
│       ├─ 3. Popuni To (computer_type_text)
│       ├─ 4. Popuni Subject (computer_type_text + Tab)
│       ├─ 5. Popuni Body (computer_type_text)
│       └─ 6. STOP — nikad ne diraj Send
│
│  permission_engine.py:
│    check_permission() → proširen za SEND_BLOCKED
│
│  computer.py (computer-use alati):
│    BLOCKED_UI_PATTERNS prošireno za Send varijante
│
─────────────────────────────────────────────────────────────
```

---

## 3. Backend dizajn

### 3.1 Novi API endpoint

```
POST /email/compose
Authorization: Bearer <token>
Content-Type: application/json

{
  "to": "sef@firma.com",
  "subject": "Izvještaj Q3",
  "body": "Poštovani,\n\nU prilogu dostavljam...\n\nPozdrav",
  "cc": null,
  "bcc": null,
  "mail_client": "outlook"       // opciono: "outlook" | "gmail_chrome" | "default"
}
```

Response:

```json
{
  "ok": true,
  "action": "email_draft_ready",
  "mail_client": "outlook",
  "details": {
    "to": "sef@firma.com",
    "subject": "Izvještaj Q3",
    "body_length": 142
  },
  "human_action_required": "Send email manually — agent cannot send.",
  "event_ids": ["evt_abc123"],
  "action_log_id": "log_def456"
}
```

### 3.2 `email_compose` tool definicija

Datoteka: `python_backend/app/tools/messaging/email.py` (novi modul)

```python
EMAIL_COMPOSE_TOOL = ToolDefinition(
    name="email_compose",
    description=(
        "Open the user's email client, create a new draft email, "
        "fill in recipient, subject, and body. "
        "CRITICAL: This tool MUST NOT click the Send button. "
        "The user manually sends the email after reviewing it."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body text (from dictation)"},
            "cc": {"type": "string"},
            "bcc": {"type": "string"},
            "mail_client": {
                "type": "string",
                "enum": ["outlook", "gmail_chrome", "default"],
                "default": "default"
            }
        },
        "required": ["to", "subject", "body"]
    },
    risk="high",
    requires_confirmation=True,
    requires_computer_mode=True,
    requires_active_window_match=False,  # namjerno otvara novi prozor
    allowed_apps=[],                      # ne ograničavamo — otvara mail klijent
    blocked_apps=[],
    logs_action_receipt=True,
    allowed_in_background=False,
    timeout_ms=30000,                     # 30s — treba vremena za otvaranje + kucanje
    implemented_by="python",
    enabled=True,
    # NOVO POLJE:
    forbidden_ui_actions=["click_send", "press_ctrl_enter"],
)
```

### 3.3 Handler — `email_compose_handler`

Datoteka: `python_backend/app/tools/messaging/email.py`

```python
# Pseudokod — NE implementirati, samo plan

async def email_compose_handler(args: dict, context: ToolContext) -> ToolResult:
    """Execute email compose workflow. NEVER clicks Send."""
    
    to = args["to"]
    subject = args["subject"]
    body = args["body"]
    client = args.get("mail_client", "default")
    
    # ===== KORAK 1: Otvori mail klijent =====
    if client == "outlook":
        open_result = await computer_open_app_handler(
            {"app_name": "outlook.exe", "wait_ms": 3000}
        )
    elif client == "gmail_chrome":
        # Otvori Chrome sa Gmail-om
        open_result = await computer_open_app_handler(
            {"app_name": "chrome.exe"}
        )
        # Navigiraj na Gmail
        await computer_type_text_handler(
            {"text": "https://mail.google.com/mail/u/0/#inbox?compose=new\n"}
        )
    else:
        # Default: probaj Outlook, fallback na default mail klijent
        open_result = await computer_open_app_handler(
            {"app_name": "outlook.exe", "wait_ms": 2000}
        )
    
    if not open_result.ok:
        return ToolResult(ok=False, error="EMAIL_CLIENT_NOT_FOUND")
    
    # ===== KORAK 2: Novi email (Ctrl+N u većini klijenata) =====
    await computer_press_key_handler({"key": "ctrl+n"})
    await asyncio.sleep(1.0)  # sačekaj da se compose prozor otvori
    
    # ===== KORAK 3: Popuni To polje =====
    await computer_type_text_handler({"text": to + "\t"})  # Tab za Subject
    await asyncio.sleep(0.3)
    
    # ===== KORAK 4: Popuni Subject =====
    await computer_type_text_handler({"text": subject + "\t"})  # Tab za Body
    await asyncio.sleep(0.3)
    
    # ===== KORAK 5: Popuni Body (diktirani tekst) =====
    await computer_type_text_handler({"text": body})
    
    # ===== KORAK 6: STOP — NE diraj Send =====
    # Tool se ovdje namjerno zaustavlja.
    # Send dugme ostaje za korisnika.
    
    return ToolResult(
        ok=True,
        action="email_draft_ready",
        details={
            "to": to,
            "subject": subject,
            "body_length": len(body),
            "mail_client": client
        },
        message="Email draft is ready in your mail client. Please review and send manually."
    )
```

### 3.4 Send dugme — hard-block na tri nivoa

Ovo je najvažniji sigurnosni zahtjev: **agentu mora biti nemoguće da klikne Send na nivou koda**, ne samo na nivou prompta.

#### Nivo 1: Tool Execution Gate (`permission_engine.py`)

```python
# Dodati u permission_engine.py

FORBIDDEN_ACTIONS = [
    "click_send_button",       # Send dugme u email klijentu
    "press_ctrl_enter",        # Ctrl+Enter = Send u mnogim klijentima
    "press_alt_s",             # Alt+S = Send u Outlook-u
    "submit_form",             # generalno
    "confirm_payment",
    "sign_document",
]

def check_permission(tool_name: str, arguments: dict, context: ToolContext) -> PermissionResult:
    # ... postojeće provjere ...
    
    # NOVA PROVJERA: da li tool call cilja na Send
    if _targets_send_action(tool_name, arguments):
        return PermissionResult(
            allowed=False,
            reason="SEND_BLOCKED",
            message="Agent cannot send emails. This action is permanently blocked."
        )
    
    # ... ostatak postojećih provjera ...

def _targets_send_action(tool_name: str, arguments: dict) -> bool:
    """Detektuje pokušaj klika na Send dugme."""
    
    # computer_click_element sa Send labelom
    if tool_name == "computer_click_element":
        element_text = arguments.get("element_text", "").lower()
        element_name = arguments.get("element_name", "").lower()
        element_id = arguments.get("element_id", "").lower()
        
        send_patterns = ["send", "pošalji", "poslati", "senden", "envoyer", "invia"]
        combined = f"{element_text} {element_name} {element_id}"
        
        for pattern in send_patterns:
            if pattern in combined:
                return True
    
    # computer_press_key za Send prečice
    if tool_name == "computer_press_key":
        key = arguments.get("key", "").lower()
        if key in ("ctrl+enter", "alt+s", "ctrl+return"):
            return True
    
    # computer_type_text koji sadrži Enter nakon email tijela
    # (manje pouzdano, ali dodatna zaštita)
    
    return False
```

#### Nivo 2: UI Pattern Blokada (`computer.py`)

```python
# Dodati u computer.py — computer_click_element handler

# UIA element patterns koje agent NIKAD ne smije kliknuti
HARD_BLOCKED_UI_PATTERNS = [
    # Send dugmad (više jezika)
    {"name": "*Send*"},
    {"name": "*Pošalji*"},
    {"name": "*Senden*"},
    {"name": "*Envoyer*"},
    {"name": "*Invia*"},
    # Send shortcut dugmad
    {"automation_id": "*send*"},
    {"automation_id": "*Send*"},
    # Potvrda / Submit
    {"name": "*Submit*"},
    {"name": "*Confirm*"},
    {"name": "*Potvrdi*"},
]

async def computer_click_element_handler(args, context):
    element_name = args.get("element_name", "")
    element_text = args.get("element_text", "")
    automation_id = args.get("automation_id", "")
    
    # Provjera prije UIA pretrage
    for pattern in HARD_BLOCKED_UI_PATTERNS:
        for key, value in pattern.items():
            target = locals().get(key, "")
            if fnmatch.fnmatch(target.lower(), value.lower()):
                return ToolResult(
                    ok=False,
                    error="SEND_BLOCKED",
                    message="Cannot click Send/Submit buttons. User must do this manually."
                )
    
    # ... nastavi sa UIA pretragom i klikom ...
```

#### Nivo 3: System Prompt (posljednja linija odbrane)

```python
# Dodati u prompt_builder.py kao dio SYSTEM_PROMPT

EMAIL_SAFETY_RULES = """
## Email Safety (HARD RULE — VIOLATION IS A CRITICAL ERROR)

You are PERMANENTLY FORBIDDEN from clicking any Send, Submit, Pošalji, 
Senden, Envoyer, or Invia button in any email client, webmail, or form.

You are FORBIDDEN from pressing Ctrl+Enter, Alt+S, or any other
keyboard shortcut that sends an email.

When composing an email:
1. Open the mail client →
2. Fill To, Subject, Body →
3. STOP — tell the user: "Email is ready. Please review and send manually."
4. NEVER click Send →

The email_compose tool ends BEFORE the Send step.
After the tool completes, the email draft is visible to the user
in their mail client, and they send it themselves.
"""
```

---

## 4. Frontend dizajn

### 4.1 Novi `VoiceSessionState`: `"email_dictation"`

```typescript
// Proširiti VoiceSessionState u src/lib/realtime.ts

type VoiceSessionState =
  | "inactive"
  | "listening"
  | "paused"
  | "processing"
  | "dictation"          // postojeći — običan diktat
  | "email_dictation"    // NOVO — diktat za email
  | "reviewing"
  | "waiting_confirmation"
  | "completed"
  | "cancelled"
  | "error";
```

### 4.2 `EmailDictationPanel` komponenta

Datoteka: `src/components/pixel/EmailDictationPanel.tsx` (nova)

```typescript
// Props i state — NE implementirati, samo plan

interface EmailDictationPanelProps {
  to: string;
  subject: string;
  body: string;
  // Handlers
  onToChange: (value: string) => void;
  onSubjectChange: (value: string) => void;
  onBodyChange: (value: string) => void;
  onContinueDictation: () => void;
  onComposeEmail: () => void;   // šalje IPC → backend → otvara email
  onCancel: () => void;
  isProcessing: boolean;
}
```

#### Izgled panela:

```text
───────────────────────────────────────────
│  📧 Diktiranje emaila                    │
│                                          │
│  Prima:   [sef@firma.com          ]     │
│  Predmet: [Izvještaj Q3           ]     │
│                                          │
│  ────────────────────────────────────  │
│  │ Poštovani,                         │  │
│  │                                     │  │
│  │ U prilogu dostavljam izvještaj     │  │
│  │ za treći kvartal. Brojke su...     │  │
│  │                                     │  │
│  │ Pozdrav,                           │  │
│  │ Marko                               │  │
│  ────────────────────────────────────  │
│                                          │
│  [🎤 Nastavi diktiranje]                │
│  [📧 Ubaci u email]    [❌ Otkaži]      │
───────────────────────────────────────────
```

### 4.3 Flow kroz frontend

```
1. Korisnik kaže: "Ricky, napiši email šefu, predmet izvještaj"

2. Agent prepoznaje namjeru:
   - primaoca ("šefu" → rezolvira iz kontakata/adresara)
   - predmet ("izvještaj")

3. UI prelazi u VoiceSessionState = "email_dictation"
   ├─ primaoc i predmet su popunjeni
   └─ body polje prazno, čeka diktat

4. Korisnik diktira tijelo emaila
   ├─ tekst se pojavljuje u body textarea
   └─ korisnik može ručno ispraviti

5. Korisnik klikče "Ubaci u email" (ili glasovna komanda "Pošalji u email")

6. Prikazuje se ConfirmationDialog sa preview-om:
   ────────────────────────────────────
   │ ⚠ Ricky će otvoriti Outlook i    │
   │   unijeti ovaj email:            │
   │                                  │
   │   Prima: sef@firma.com           │
   │   Predmet: Izvještaj Q3          │
   │   Tijelo: 142 znaka              │
   │                                  │
   │   ⛔ Ricky NEĆE poslati email.   │
   │   Ti ćeš ga sam/a poslati.      │
   │                                  │
   │   [Ubaci u email]  [Otkaži]     │
   ────────────────────────────────────

7. Korisnik potvrđuje → IPC invoke('email:compose', {...})

8. Backend otvara mail klijent, popunjava polja, STOP

9. Activity timeline dobija stavku:
   "Email draft ready in Outlook — sef@firma.com"

10. Korisnik prelazi u Outlook i sam klikče Send
```

### 4.4 IPC kanal

```typescript
// electron/core/ipc.cjs — dodati handler

ipcMain.handle('email:compose', async (_event, payload: EmailComposePayload) => {
  const result = await fetch(`${BACKEND_URL}/email/compose`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getLocalToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  return result.json();
});
```

```typescript
// preload.cjs — dodati expose

contextBridge.exposeInMainWorld('emailAPI', {
  compose: (payload: EmailComposePayload) => 
    ipcRenderer.invoke('email:compose', payload),
});
```

---

## 5. Implementacioni koraci (redoslijed)

### Korak 1: Backend — `email_compose` tool + handler
**Fajlovi:**
- `python_backend/app/tools/messaging/__init__.py` (novi)
- `python_backend/app/tools/messaging/email.py` (novi)
- `python_backend/app/api/email.py` (novi endpoint)
- `python_backend/app/main.py` (registracija router-a)

**Output:** `POST /email/compose` radi; tool koristi postojeće `computer_*` handler-e interno.

### Korak 2: Backend — Send dugme hard-block
**Fajlovi:**
- `python_backend/app/agent/permission_engine.py` (dodati `_targets_send_action`)
- `python_backend/app/tools/system/computer.py` (dodati `HARD_BLOCKED_UI_PATTERNS`)
- `python_backend/app/agent/prompt_builder.py` (dodati `EMAIL_SAFETY_RULES`)

**Output:** Svaki pokušaj klika na Send vraća `SEND_BLOCKED` grešku.

### Korak 3: Frontend — `EmailDictationPanel` + voice flow
**Fajlovi:**
- `src/components/pixel/EmailDictationPanel.tsx` (novi)
- `src/App.tsx` (dodati `email_dictation` state rendering)
- `src/lib/realtime.ts` (dodati `email_dictation` u `VoiceSessionState`)

**Output:** Korisnik može diktirati email u namjenskom panelu.

### Korak 4: Electron — IPC bridge
**Fajlovi:**
- `electron/core/ipc.cjs` (dodati `email:compose` handler)
- `electron/preload.cjs` (dodati `emailAPI` expose)

**Output:** Renderer može poslati email compose zahtjev Python backend-u.

### Korak 5: Confirmation flow integracija
**Fajlovi:**
- `src/components/ConfirmationDialog.tsx` (dodati email-specific rendering)
- `python_backend/app/agent/permission_engine.py` (dodati `email_compose` u high-risk toolove)

**Output:** Prije unosa u email klijent, korisnik vidi preview i potvrđuje.

### Korak 6: Testovi
**Fajlovi:**
- `python_backend/tests/test_email_compose.py` (novi)
- `python_backend/tests/test_security_redteam.py` (dodati email-specific testove)

**Testovi koji moraju proći:**
```python
# 1. email_compose uspješno otvara mail klijent i popunjava polja
# 2. email_compose NIKAD ne klikče Send — tool se uvijek zaustavlja prije
# 3. computer_click_element sa "Send" labelom vraća SEND_BLOCKED
# 4. computer_press_key sa "ctrl+enter" vraća SEND_BLOCKED
# 5. check_permission blokira email_compose bez confirmation_id
# 6. email_compose bez computer_mode vraća COMPUTER_MODE_REQUIRED
# 7. prompt injection u email body-ju ne može zaobići Send blokadu
# 8. email_compose sa praznim 'to' poljem vraća VALIDATION_ERROR
```

---

## 6. Edge case-ovi i error handling

| Scenario | Ponašanje |
|----------|-----------|
| Outlook nije instaliran | `EMAIL_CLIENT_NOT_FOUND` → agent kaže "Nisam našao Outlook. Javi mi koji mail klijent koristiš." |
| Mail klijent se sporo otvara | Timeout 30s + retry logika (max 2 pokušaja) |
| Compose prozor se nije otvorio nakon Ctrl+N | Detektovati preko `ui_inspect` — ako nema compose prozora, vratiti grešku |
| Korisnik ne želi Outlook već Gmail | `mail_client` parametar: `"gmail_chrome"` → otvara Chrome pa navigira na Gmail compose URL |
| Diktirani tekst sadrži prompt injection | Body ide u `<untrusted_content>` delimitere → `external_content_seen` flag se diže → sve naredne akcije eskaliraju |
| Korisnik hoće da doda attachment | Agent ne dodaje attachment-e — kaže: "Dodaj attachment ručno u Outlook-u prije slanja." |
| Korisnik promijeni mišljenje tokom diktata | Cancel dugme — briše diktat — vraća se na idle |
| Više email naloga | Agent pita: "Koji nalog da koristim?" ili koristi default |

---

## 7. Šta NE raditi (eksplicitno van obima)

- **NE implementirati SMTP/IMAP** — nema slanja preko SMTP servera
- **NE implementirati OAuth** — nema Gmail API-ja, nema Microsoft Graph-a
- **NE čuvati email lozinke/tokene** — korisnik je već auth-an u svom klijentu
- **NE dodavati attachment-e** — previše rizično (exfiltration vektor)
- **NE slati automatski** — Send je hard-blokiran na 3 nivoa koda
- **NE parsirati email adrese iz glasovnog unosa** — korisnik ih unosi/potvrđuje ručno u panelu
- **NE čitati postojeće emailove** — ovo je samo za compose, ne za inbox
- **NE implementirati bez prethodnog review-a ovog plana od strane korisnika**

---

## 8. Zavisnosti (mora postojati prije implementacije)

Iz `MIGRATION_PLAN.md`, već postojeći i stabilni:

| Zavisnost | FAZA | Status |
|-----------|------|--------|
| Permission/confirmation engine | FAZA 10 | ✅ |
| `computer_open_app` | FAZA 13 | ✅ |
| `computer_type_text` | FAZA 13 | ✅ |
| `computer_press_key` | FAZA 13 | ✅ |
| `computer_click_element` | FAZA 14 | ✅ |
| Voice-first UI + Dictation Mode | FAZA 8 | ✅ |
| ConfirmationDialog | FAZA 9 | ✅ |
| Activity timeline | FAZA 8 | ✅ |
| `external_content_seen` eskalacija | S-2 | ✅ |

---

## 9. Sigurnosna analiza

### Attack surface koji se dodaje

| Površina | Rizik | Ublažavanje |
|----------|-------|-----------|
| `POST /email/compose` endpoint | Srednji | Auth token obavezan; `email_compose` je `risk=high` → confirmation obavezan |
| `computer_type_text` u email body | Srednji | Body ide kroz `wrap_untrusted_content`; `external_content_seen` se diže |
| Agent pokuša da klikne Send | **Kritično** | Hard-block na 3 nivoa: `_targets_send_action` + `HARD_BLOCKED_UI_PATTERNS` + system prompt |
| Agent otkuca pogrešnu adresu | Visok | Korisnik vidi To/Subject u panelu prije nego potvrdi; može ispraviti |
| Prompt injection u To/Subject polju | Nizak | Ne izvršava se — samo se kuca u UI; korisnik vidi prije potvrde |

### Šta se dešava ako agent svejedno pokuša Send?

```
Pokušaj 1: model zatraži computer_click_element("Send")
         → permission_engine._targets_send_action() vrati True
         → check_permission() vrati SEND_BLOCKED
         → tool se ne izvrši

Pokušaj 2: model zatraži computer_press_key("ctrl+enter")
         → ista provjera → SEND_BLOCKED

Pokušaj 3: model zatraži computer_type_text("\n") nad Send dugmetom
         → ovo je najteže blokirati, ali computer_type_text kuca tekst
           u fokusirano polje, ne aktivira dugmad
         → u najgorem slučaju doda novi red u body

Pokušaj 4: model pokuša email_compose pa odmah computer_click_element
         → external_content_seen je već podignut (body je untrusted)
         → svaki acting tool nakon čitanja eksternog sadržaja 
           zahtijeva confirmation → korisnik vidi ConfirmationDialog
```

---

## 10. Rezime odluka

| Odluka | Izbor | Razlog |
|--------|-------|--------|
| Pristup | Computer-use (ne API) | Sigurnost: nema čuvanja lozinki/tokena |
| Send blokada | 3 nivoa (permission + UI patterns + prompt) | Defense in depth |
| Diktat | Dictation Mode → panel → potvrda → unos | Korisnik kontroliše finalni tekst |
| Mail klijent | Outlook default, Gmail/other opciono | Outlook je najčešći na Windowsu |
| Attachmenti | Van obima | Previše rizično za prvu verziju |
| Čitanje inbox-a | Van obima | Samo compose, ne read |
