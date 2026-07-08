# Sigurnosni audit — D1 + D2 (read-only)

**Datum:** 2026-07-07
**Izvršio:** pi (read-only audit, po briefu `docs/PI_SECURITY_AUDIT_BRIEF.md`)
**Scope:** D1 (glasovna potvrda high-risk akcija) i D2 (IPC handleri validiraju payload)
**Izvor istine:** `docs/SECURITY_DELEGATION_PLAN.md`, `docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md`
**Napomena:** Nijedan fajl koda nije mijenjan. Ovaj fajl je jedini output.

---

## D1 — Može li glas odobriti high-risk akciju?

**Nalaz: NE.** High-risk akcija (`computer_type_text`, `computer_click`, `computer_click_element`, slanje emaila itd.) ne može biti odobrena glasom ("da"/"pokreni"). Odobrenje je moguće **isključivo klikom na dugme** u `ConfirmationDialog`, i to uz rate-limit.

### Lanac koji to dokazuje

**1) Glas ne ide direktno u confirmation flow.**
Glasovni unos ide kroz OpenAI Realtime sesiju (`src/lib/realtime.ts`). Transkript korisnika postaje `conversation.item` poruka modelu — ne okida nijedan `approveConfirmation`. Jedino mjesto u cijelom repo-u gdje se zove `approveConfirmation` iz renderera je `handleApproveConfirmation` (`src/App.tsx:286`), potvrđeno grep-om (`src/`, `electron/`, `python_backend/`):
- `src/App.tsx:286` — `window.ricky.approveConfirmation(confirmationId)`
- to je jedini renderer poziv; ostalo su testovi i Electron→Python proslijeđivanje.

**2) Approval je vezan isključivo na dugme.**
`handleApproveConfirmation` se proslijeđuje kao `onApprove` u `ConfirmationDialog` (`src/App.tsx:463`). U dijalogu (`src/components/ConfirmationDialog.tsx`) odobrenje se dešava samo preko:
```tsx
<button className="confirmation-button confirmation-approve"
  onClick={() => confirmation && onApprove(confirmation.id)}
  disabled={!isPending || busy || !armed} ...>
```
Nema `onKeyDown`, nema voice-listenera, nema kratice. Dodatno, `armed` rate-limit (`ConfirmationDialog.tsx`, ~red 38, `setTimeout(...,250)`) onemogućava dugme 250 ms nakon otvaranja — sprječava dvostruki/programatski klik.

**3) Model ne može sam odobriti niti forge-ati confirmation_id.**
Kada alat zahtijeva potvrdu, backend vrati `CONFIRMATION_REQUIRED` i `realtime.ts` samo *predlaže* potvrdu (`window.ricky.createConfirmation(...)`, `src/lib/realtime.ts:266`) i traži od modela da čeka. Status te potvrde je `pending`. Da bi se izvršila, model mora ponovo pozvati alat sa `confirmation_id` — a backend u `check_permission` (`python_backend/app/agent/permission_engine.py:117-160`) provjerava:
- `confirmation["status"] == "approved"` (red ~128) — pending se odbija,
- nije istekla,
- `tool_name` se poklapa (`CONFIRMATION_MISMATCH`),
- `payload_hash` se poklapa sa poslanim argumentima (`CONFIRMATION_MISMATCH`).

Dakle model ne može iskoristiti tuđi/pending confirmation_id. Odobrenje (`approved`) može postati **samo** klikom → `handleApproveConfirmation` → `confirmations:approve` → backend `approve()`.

**4) Backend ne razlikuje izvor potvrde — ali to nije rupu za glas.**
`ConfirmationService.approve()` (`python_backend/app/services/confirmation_service.py:80`) i API `/confirmations/{id}/approve` (`python_backend/app/api/confirmations.py:62`) samo prelaze status u `approved`; ne zapisuju `source` (voice/click). Pošto renderer nema nikakvu code-path koja zove `approve` iz glasa, ovo trenutno nije eksploatabilno — ali jeste **slabost u dubini obrane** (vidi Otvorena pitanja).

### D1 zaključak
 Glas **NE** može odobriti high-risk akciju. Jedini put je klik na odobravanje dugme, sa rate-limitom. Nema voice keyword handlinga ("da"/"pokreni") nigdje u kodu.

---

## D2 — IPC handleri validiraju payload?

**Nalaz: DJELIMIČNO.** Većina handlera je "thin pass-through" ka Python backendu, koji radi pravu validaciju (Pydantic schema, `Query(ge=, le=)`, `confirmation_id` match). Elektron-side handleri rade **minimalnu/tanku** validaciju (`asObject`, `=== true`, `String(...)`). Nekoliko handlera slijepo prosljeđuje renderer podatke dalje i zavise isključivo od backend validacije.

### Tabela kanala

| Kanal | Handler (`main.cjs`) | Validira payload? | Napomena |
|---|---|---|---|
| `tools:execute` | `handleToolsExecute:775` | **DJELIMIČNO** | `asObject(toolCall?.arguments)` (slabo, red 777/446). `set_mode` koercira u `display` ako nije `"computer"` (red 819) — sigurno. `confirmation_id` se strpnguje i proslijeđuje Pythonu koji radi punu provjeru (`permission_engine`). Legacy fallback (vidi rizik R2) **ne** provjerava confirmation. |
| `tools:list` | `handleToolsList:585` | DA (nema payload) | Vraća statičke specove. |
| `realtime:create-token` | `handleRealtimeCreateToken:736` | DA (nema payload) | Sastavlja session config, ključ živi u Pythonu. |
| `app:quit/minimize/toggle-maximize` | 589/593/600 | DA (nema payload) | — |
| `confirmations:list` | `handleConfirmationsList:617` | **NE (client-side)** | Destructure `payload` bez provjere; `status`/`limit` idu u `URLSearchParams` (bez injekcije). Stvarna validacija `limit` (`ge=1,le=200`) u backendu (`api/confirmations.py:36`). Ako je `payload` `null` → default `{}`. |
| `confirmations:pending` | `handleConfirmationsPending:626` | DA (nema payload) | — |
| `confirmations:create` | `handleConfirmationCreate:630` | **NE** | `createConfirmation(payload || {})` — slijepo prosljeđuje renderer dict Pythonu. Pydantic `ConfirmationCreateRequest` validira. |
| `confirmations:approve` | `handleConfirmationApprove:634` | **NE** | `confirmationId` ide direktno u URL (`encodeURIComponent`, `pythonClient.cjs:104`) — nema path injekcije, ali nema ni tip-provjere (non-string se šalje kao `"undefined"`). Backend vraća 404 ako ne postoji. |
| `confirmations:reject` | `handleConfirmationReject:638` | **NE** | Isto kao approve. |
| `confirmations:cancel` | `handleConfirmationCancel:642` | **NE** | Isto; `DELETE` sa `encodeURIComponent`. |
| `plans:list` | `handlePlansList:646` | DA (nema payload) | — |
| `plans:create` | `handlePlanCreate:650` | **NE** | `createPlan(payload || {})` — slijepo proslijeđuje Pythonu. |
| `plans:get` | `handlePlanGet:654` | **NE** | `planId` direktno u URL (backend 404 ako nepostojeći). |
| `plans:update` | `handlePlanUpdate:658` | **NE** | Destructure `{ planId, payload }` — ako renderer pošalje ne-object, destructure baca/daje `undefined`; proslijeđuje Pythonu. |
| `plans:update-step` | `handlePlanStepUpdate:662` | **NE** | Isto, još `{ stepId }`. |
| `events:list` | `handleEventsList:667` | **DJELIMIČNO** | `typeof since === "string" ? since : undefined` — tip-provjera da, ali `since` ide u query bez formata-validacije. |
| `companion:show/hide/toggle` | 677/682/687 | DA (nema payload) | — |
| `companion:voice-state-update` | `handleCompanionVoiceStateUpdate:694` | **NE** | `forwardVoiceStateToCompanion(state)` (`companionWindow.cjs:119`) `webContents.send("companion:voice-state", state)` — prosljeđuje **proizvoljan** objekat u companion renderer bez ikakve provjere. Potencijalni drugi-renderer injection vektor ako companion renderer ikad renderuje `state` kao HTML (vidi R3). |
| `companion:click` | `handleCompanionClick:700` | DA (nema payload) | — |
| `companion:open-main` | `handleCompanionOpenMain:711` | DA (nema payload) | — |
| `companion:toggle-voice` | `handleCompanionToggleVoice:723` | DA (nema payload) | — |
| `companion:toggle-lock` | `handleCompanionToggleLock:731` | **DA** | `locked === true` stroga provjera; `setLockedPosition(Boolean(locked))` (`companionWindow.cjs:127`). |

### D2 zaključak
Handleri su dosljedno "thin" i delegiraju validaciju na Python backend — što je arhitektonski ispravno (pravilo: `main.cjs` samo shell/IPC). **Problem nije u pojedinom handleru, nego u odsustvu dosljednog tip/oblik-validacionog sloja na Electron strani** — cijela odbrana od kompromitovanog renderera (XSS) trenutno zavisi od toga da li backend za svaki kanal radi pravu validaciju. Za `confirmations:*` i `plans:*` to drži (Pydantic). Za `companion:voice-state-update` to **ne** drži (payload ide u drugi renderer, ne u backend).

---

## Rizici / otvorena pitanja

**R1 (Srednje) — Backend ne bilježi izvor odobrenja.**
`ConfirmationService.approve()` i API ne zapisuju `source` (voice/click/auto). Danas nije eksploatabilno jer renderer nema voice→approve path, ali ako se ikad doda glasovna komanda ili auto-approve, neće se moći auditovati ko/šta je odobrio. *Preporuka:* dodati `source` polje u confirmation rezoluciju (samo Claude, dira backend schema).

**R2 (Visoko) — Legacy fallback je fail-OPEN na potvrdama.**
`handleToolsExecute` (`main.cjs:778-825`) za `PHASE11_DELEGATED_TOOLS` (uključujući `computer_type_text`, `computer_click`) delegira na Python. Ako Python padne i `isLegacyEnabled()` (LEGACY_FLAG≠0), pada na legacy if-chain koji **ne provjerava `confirmation_id`/odobrenje** (`main.cjs:989-1004`). `computer_type_text` samo pozove `computerTypeText(args.text)`; `computer_click` ima samo lokalnu `requiresConfirmation(args)` heuristiku, ne pravi confirmation gate. **Ovo znači:** kompromitovani renderer (ili sam model) može izvršiti high-risk computer akciju bez odobrenja kad god je backend nedostupan a legacy uključen. Ovo je direktno suprotno S-4 fail-closed cilju. *Otvoreno pitanje za Claude:* da li je legacy fallback namjerno fail-open radi kompatibilnosti, i da li treba biti fail-closed za high-risk alate bez obzira na LEGACY_FLAG.

**R3 (Nisko–Srednje) — `companion:voice-state-update` proslijeđuje proizvoljan objekat u companion renderer.**
`forwardVoiceStateToCompanion(state)` radi `webContents.send` bez provjere (`companionWindow.cjs:124`). Ako companion renderer (`CompanionOrb.tsx`) ikada renderuje polja iz `state` kao HTML/innerHTML umjesto kao tekst, kompromitovani glavni renderer može injektovati markup u drugi prozor. *Otvoreno pitanje:* provjeriti kako `CompanionOrb.tsx` konzumira `voice-state` (nije pregledano u ovom auditu — izvan D1/D2 briefa, ali logično povezano).

**R4 (Nisko) — `asObject` je prelab.**
`asObject` (`main.cjs:446`) prihvata bilo koji non-null non-array objekat, uključujući objekte sa prototipom/poljima koja backend ne očekuje. Pošto backend radi Pydantic validaciju, rizik je nizak, ali Electron-side ne sanitizuje tipove pojedinih argumenata (npr. `args.text` se strpnguje unutar `computerTypeText` — treba provjeriti da li `computerTypeText` radi `String(text)`). *Otvoreno pitanje:* provjeriti `computerTypeText`/`computerClick` (legacy, `electron/` ispod main.cjs) na tip validaciju.

**R5 (Info) — Nijedan Electron IPC handler ne koristi schema/Joi/zod validaciju.** Validacija je isključivo u Pythonu (Pydantic) ili uopšte ne postoji (companion). Za kanale koji idu u backend to je prihvatljivo; za `companion:voice-state-update` nije.

---

## Preporuka za Claude

1. **D1 — nema popravke potrebne.** Glas ne može odobriti high-risk. Potvrditi rate-limit `armed` logiku je već na mjestu (S-4).
2. **D2 — dodati Electron-side tip/oblik validaciju barem za `companion:voice-state-update`** (R3) — allowlista poznatih `VoiceState` stringova ili odbacivanje non-string `state`. Niski trud, zatvara realnu drugi-renderer površinu.
3. **R2 (legacy fail-open) je najozbiljniji nalaz** — predlažem zasebni zadatak (vjerojatno **[C]** = Claude) koji ili (a) čini legacy fallback fail-closed za high-risk `computer_*` alate bez obzira na LEGACY_FLAG, ili (b) eksplicitno dokumentuje zašto je fail-open prihvatljivo. Ovo dira `electron/main.cjs` i S-4 kill-switch/fail-closed dizajn → nedelegabilno.
4. **R1** se može kombinovati sa B1/keyring fazom kad se dira confirmation schema — niski prioritet sada.

Izvještaj gotov — čeka Claude verifikaciju i odluku o popravkama. Nijedan fajl koda nije diran.
