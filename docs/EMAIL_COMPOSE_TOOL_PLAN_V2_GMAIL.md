# EMAIL COMPOSE TOOL — Revidirani plan V2 (Gmail-fokusiran)

**Datum:** 2026-07-13
**Status:** Plan — implementacija nije započeta
**Zamjenjuje:** [`EMAIL_COMPOSE_TOOL_PLAN.md`](./EMAIL_COMPOSE_TOOL_PLAN.md) (V1, Outlook-fokusiran)
**Ugrađuje nalaze iz:** [`EMAIL_COMPOSE_TOOL_SECURITY_REVIEW_2026-07-13.md`](./EMAIL_COMPOSE_TOOL_SECURITY_REVIEW_2026-07-13.md)
**Povod revizije:** Korisnik je odlučio da je Gmail primarni cilj (Outlook koristi
mali dio korisničke baze), i zatražio novi plan koji rješava SVE nedostatke
identifikovane u sigurnosnom review-u V1 plana — ne samo zamjenu Outlook→Gmail.

---

## 0. Šta se mijenja u odnosu na V1 (executive summary)

| V1 (Outlook) | V2 (ovaj dokument, Gmail) | Razlog |
|---|---|---|
| Generic `computer_*` UIA alati (click/type/press_key) | Chrome DevTools Protocol (CDP), eksplicitan, uzak skup komandi | CDP daje deterministički pristup DOM-u/tabovima; UIA-kroz-Chrome zavisi od toga da li je Chrome-ova accessibility tree aktivirana, i ne rješava "koji je tab aktivan" problem |
| Automatizacija korisnikovog **regularnog** Chrome prozora | Namjenski, izolovan Chrome profil (poseban `--user-data-dir`) samo za ovaj zadatak | Strukturalno eliminiše "aktivni tab može biti banka/password manager" rizik iz V1 review-a (4.7) — u izolovanom prozoru NEMA drugih tabova |
| Tekstualna Send-blokada (lista naziva dugmadi) | Send je **strukturalno nedostižan** — adapter nikad ne šalje input event van poznatih DOM selektora za To/CC/BCC/Subject/Body | Allowlist-only sposobnost je jača garancija od blocklist-a (review 4.2) |
| Poseban `/email/compose` HTTP endpoint | Regularan tool `email_prepare_draft` kroz postojeći `ToolExecutor` | Review 3.1/4.1 — izbjegava zaobilaženje confirmation/cancellation/action-log/validacije |
| Plaintext email sadržaj u confirmation/action-log bazi | Kratkotrajan in-memory draft store sa TTL-om, hash-bazirana potvrda | Review 4.4 |
| ConfirmationDialog prikazuje "Pošalji email" | Eksplicitno "Pripremi draft" / "Ubaci u email", nikad "Pošalji" | Review 4.5 |
| `Tab` navigacija, `\n`→Enter u tekstu | CDP `Input.insertText`/DOM fokus po eksplicitnom selektoru, nema Tab-a niti fizičkih Enter događaja | Review 4.6 |
| Fiksni `sleep()`, "max 2 retry" | Polling na CDP evente + eksplicitan monotoni deadline po koraku | Review 3.8/3.9/4.12 |
| Outlook prvi, Gmail "kasnije, van obima" | **Gmail prvi (MVP), Outlook eventualno kasnije kao poseban adapter** | Korisnikova odluka — realna korisnička baza |

---

## 1. Koncept i cilj (nepromijenjeno iz V1)

```
KORISNIK: "Ricky, napiši email šefu"
RICKY:    otvara izolovan Chrome profil sa Gmail-om → popunjava To/Subject
KORISNIK: diktira tijelo emaila (Dictation Mode)
RICKY:    prebacuje tekst u email body → STOP
KORISNIK: pregleda i sam klikče "Send" u tom prozoru
```

Agentu je **strukturalno**, ne samo na nivou pravila, onemogućeno da klikne
Send — vidi poglavlje 4 za mehanizam.

---

## 2. Zašto Gmail, i zašto CDP a ne UIA-kroz-Chrome

### 2.1 Zašto Gmail (korisnikova odluka)

Vrlo mali dio korisnika koristi Outlook desktop klijent; Gmail (web) je
realan primarni cilj. Outlook ostaje mogući budući adapter (Faza F), ali
van MVP-a.

### 2.2 Zašto ne "UIA kroz Chrome" (V1/review-ov prvobitni pristup za Gmail)

Chrome izlaže svoj DOM kroz OS accessibility stablo (isti mehanizam koji
koriste screen reader-i), pa bi teorijski postojeći `computer_find_elements`/
`computer_click_element`/`computer_set_text_element` (FAZA 14, `uiautomation`
paket) mogli "vidjeti" Gmail-ove compose elemente. Problem: Chrome tu
accessibility tree **aktivira samo kad detektuje AT (assistive technology)
klijenta**, ponašanje nije uvijek trenutno/pouzdano, i dalje ne rješava dva
temeljna review nalaza (4.7):

- koji je od potencijalno više otvorenih tabova stvarno Gmail compose;
- da li je to ZAISTA `https://mail.google.com` a ne stranica koja liči na
  Gmail (phishing) ili je korisnik u međuvremenu promijenio tab.

### 2.3 Preporučeno: Chrome DevTools Protocol (CDP) + izolovan profil

CDP (isti mehanizam koji koriste Playwright/Puppeteer i legitimni browser-QA
alati) rješava oba problema direktno:

- Svaki CDP **target** (tab) ima eksplicitan `targetId` i `url` — identitet
  taba je *podatak koji CDP vraća*, ne nešto što treba inferisati iz HWND-a.
- `Accessibility.getFullAXTree`/`DOM.querySelector` daju direktan,
  deterministički pristup DOM-u konkretnog taba — bez zavisnosti od toga da
  li je OS accessibility tree "probuđena".
- **Ključna dodatna mjera (nije bila u V1 niti u review-u):** Chrome se
  pokreće u **potpuno izolovanom, namjenskom profilu**
  (`--user-data-dir=<posebna app-owned putanja>`), odvojenom od korisnikovog
  regularnog Chrome profila. U tom prozoru **nema drugih tabova** — otvara
  se isključivo radi ovog zadatka i zatvara nakon njega. Time se "aktivni
  tab može biti banka/password manager" rizik (review 4.7) **ne detektuje
  naknadno, nego strukturalno ne postoji** — nema drugog taba koji bi mogao
  biti nešto osjetljivo.
- Ovaj izolovani profil ima svoje kolačiće/sesiju — korisnik se u njega mora
  ulogovati JEDNOM (prvi put), poslije toga sesija ostaje (persistent
  profile, ne incognito). Vidi poglavlje 8.

### 2.4 CDP sigurnosne mjere (obavezne, ne opcione)

- Debug port **isključivo na `127.0.0.1`**, nikad `0.0.0.0` — CDP port bez
  ograničenja je poznat napadni vektor (lokalni proces bi mogao preuzeti
  potpunu kontrolu nad Chrome-om, čitati kolačiće, ubrizgati JS).
- Port se bira **nasumično** pri svakom pokretanju (ne fiksan/predvidiv broj).
- Chrome instancu pokreće **isključivo naš vlastiti proces** (Python backend,
  analogno kako se već pokreće Python backend iz `pythonProcess.cjs`) — nikad
  se ne pokušava "attach" na već pokrenut/tuđi Chrome proces, čime se
  izbjegava rizik povezivanja na Chrome koji je neko drugi unaprijed
  pripremio/kompromitovao.
- Chrome se pokreće sa `--user-data-dir` unutar aplikacijinog `data_dir`-a
  (isti korijen kao ostali app podaci), NIKAD sa korisnikovim default Chrome
  profilom.
- CDP WebSocket konekciju drži isključivo Python backend proces; ne izlaže
  se preko HTTP-a Electron-u niti bilo kome drugom.
- Chrome prozor se zatvara (proces se gasi) nakon završetka/otkazivanja
  workflow-a, ne ostaje trajno otvoren u pozadini.

---

## 3. Arhitektura end-to-end

```text
React Email Draft Panel
  - lokalni editable draft (To/Subject/Body)
  - eksplicitni preview/readback
  - korisnik bira "Pripremi draft"
              |
              v
ConfirmationService (postojeći, FAZA 9/S-04)
  - jednokratna potvrda vezana za email_prepare_draft + kanonski hash
  - kratak TTL
              |
              v
window.ricky.executeTool(...)  ← POSTOJEĆI generic IPC, bez novog kanala
              |
              v
electron/main.cjs handleToolsExecute → PHASE11_DELEGATED_TOOLS
  - bez email poslovne logike u Electron-u
              |
              v
Python ToolExecutor (postojeći)
  - schema validation, Computer Mode provjera, confirmation provjera,
    cancellation, action receipt — SVE postojeće garancije se primjenjuju
              |
              v
EmailDraftPolicy + GmailDraftAdapter (novo)
  - pokreće izolovan Chrome profil preko CDP-a
  - otvara Gmail compose (URL kao launch argument, NE kucanjem u adresnu traku)
  - identifikuje compose dialog preko DOM/AX stabla
  - verifikuje origin (https://mail.google.com) prije SVAKOG write koraka
  - postavlja SAMO poznata polja (To/CC/BCC/Subject/Body) preko CDP
    DOM/Input komandi ciljanih na eksplicitne selektore
  - nikad ne šalje klik/keypress event van tih poznatih elemenata
  - verifikuje upisane vrijednosti nakon upisa
  - zatvara/gasi izolovanu Chrome instancu na kraju
              |
              v
Draft ostaje otvoren u izolovanom Chrome prozoru
  - korisnik ga vidi, pregleda, i sam klikče Send
  - agent od ovog trenutka nema NIKAKVU dalju sposobnost da djeluje na taj prozor
    (CDP konekcija se zatvara nakon posljednjeg write koraka + verifikacije)
```

Ključna razlika od V1/review arhitekture: "capability lock" tamo je bio
**blokada** generičkih alata koji bi inače postojali. Ovdje je jednostavnije
i jače — `GmailDraftAdapter` **nikad nije imao** generičku "klikni bilo šta"
sposobnost. Ne treba ništa blokirati jer ta sposobnost nikad nije data.

---

## 4. Backend dizajn

### 4.1 Tool definicija

Naziv `email_prepare_draft` (ne `email_compose`) — ista logika kao review
5.1: naziv mora jasno govoriti da nema slanja.

```python
ToolDefinition(
    name="email_prepare_draft",
    description=(
        "Open a fresh, isolated Gmail compose window and fill in the "
        "recipient, subject, and body. This tool NEVER clicks Send — "
        "the user reviews and sends manually in the opened window."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "cc": {"type": "string"},
            "bcc": {"type": "string"},
        },
        "required": ["to", "subject", "body"],
        "additionalProperties": False,
    },
    risk="high",
    requires_confirmation=True,
    requires_computer_mode=True,
    requires_active_window_match=False,  # namjerno otvara nov, izolovan prozor
    allowed_apps=[],
    blocked_apps=[],
    logs_action_receipt=True,
    allowed_in_background=False,
    timeout_ms=45000,
    implemented_by="python",
    enabled=True,
)
```

Registruje se kroz `ToolExecutor` kao i svaki drugi alat — **nema paralelnog
`/email/compose` endpointa** (review 3.1/4.1 zatvoreno po dizajnu).

### 4.2 `GmailDraftAdapter` — uzak op-set

```text
python_backend/app/services/gmail_draft_adapter.py

launch_isolated_chrome() -> CdpConnection
open_compose(cdp) -> ComposeTarget           # nova Chrome instanca, novi tab
                                              # preko launch argument URL-a
verify_origin(compose_target) -> bool        # mail.google.com, tačan match
identify_compose_dialog(compose_target) -> ComposeDialogHandle
set_recipient_field(handle, to, cc, bcc)
set_subject_field(handle, subject)
set_body_field(handle, body)
verify_draft_values(handle, expected) -> bool
close_isolated_chrome(cdp)                   # NE zatvara korisnikov regularni Chrome
```

Adapter **ne nudi** `click(x, y)`, `press_key(key)`, generic `find_element`,
niti bilo šta što bi omogućilo klik na proizvoljan element. Ovo je ugovorna
(tip-nivo) garancija, ne samo runtime provjera — model/agent kod koji poziva
ovaj adapter fizički nema pristup širem API-ju.

### 4.3 Identitet i verifikacija prije svakog write koraka

Prije `set_recipient_field`/`set_subject_field`/`set_body_field`:

1. CDP target i dalje postoji (nije zatvoren/navigiran na drugu stranicu).
2. `target.url` i dalje počinje sa `https://mail.google.com/` (tačan match,
   ne substring — sprječava `mail.google.com.evil.example`).
3. Compose dialog DOM node i dalje postoji u stablu (nije zatvoren/minimiziran).
4. Postoji **tačno jedan** aktivni compose dialog kandidat — ako ih ima više
   (Gmail dozvoljava više minimiziranih draft-ova na dnu ekrana), fail-closed
   umjesto biranja prvog (isti princip kao review 4.11 za Outlook).
5. Cancellation nije zatražen (Stop dugme/kill-switch).
6. Monotoni deadline nije istekao.

Ako bilo koja provjera padne: workflow staje, ništa se dalje ne piše, i
korisniku se jasno kaže koja polja su (ako ijedna) potvrđeno upisana.

### 4.4 Send dugme — zašto je strukturalno nedostižno

Za razliku od V1/review-ovog "capability lock" (blokada generičkih alata),
ovdje Send jednostavno nikad nije u dosegu:

- Adapter piše samo preko `DOM.querySelector` na unaprijed poznate,
  Faza-A0-potvrđene selektore za To/CC/BCC/Subject/Body polja.
- Adapter nikad ne poziva CDP `Input.dispatchMouseEvent` niti bilo koji klik
  event — nema koda koji bi mogao "pogoditi" Send dugme, čak ni greškom.
- Jedini keyboard event koji se šalje je `Input.insertText` fokusiran na
  eksplicitno pronađen text-input element — nikad simulacija Enter/Ctrl+Enter.

Ovo je **allowlist arhitekture**, ne blocklist — jača garancija od bilo koje
liste zabranjenih naziva dugmadi (zatvara review 4.2 na korijenu, ne
zakrpom).

### 4.5 Multi-account handling

Gmail podržava više naloga (`/u/0/`, `/u/1/`...). MVP: koristi se **samo
default nalog** korisnika izolovanog profila (`/u/0/`). Ako korisnik ima
više naloga prijavljenih u tom profilu, prvi put se to mora eksplicitno
riješiti tokom onboardinga (poglavlje 8) — biranje TAČNO jednog naloga za
automatizaciju, ne runtime nagađanje.

### 4.6 Draft store, confirmation, i privatnost (review 4.4/6)

- Draft (`to`/`cc`/`bcc`/`subject`/`body`) živi **samo u memoriji** dok traje
  workflow — kratkotrajan Python-side store sa TTL-om 2–5 minuta, nasumičan
  `draft_id`.
- Confirmation se vezuje za **hash** kanonskog sadržaja drafta, ne za sam
  sadržaj — permission_engine (postojeći, FAZA 9/S-04) već podržava ovaj
  obrazac.
- Trajni action log/receipt sadrži SAMO: broj primalaca, dužinu subjecta/bodyja,
  hash prefiks, `mail_client: "gmail_isolated"`, `sent: false` — nikad
  stvarne adrese/subject/body (review "Minimalni action receipt", 6.3).
- Draft se briše iz memorije nakon uspjeha, greške, cancel-a, ili TTL-a.
- BCC se nikad ne prikazuje u Activity timeline-u.

### 4.7 Timeout i cancellation disciplina

`ToolDefinition.timeout_ms` **trenutno nije sprovođen** od strane
`ToolExecutor`-a (potvrđeno u kodu ovu sesiju — `execute()` je sinhrona
funkcija, nema timeout wrapper-a). `email_prepare_draft` workflow zato MORA
imati **sopstveni eksplicitni monotoni deadline** unutar `GmailDraftAdapter`-a
(isti princip kao `filesystem_search`-ov dijeljeni `deadline` iz ove
sesije), ne osloniti se na neiskorišten schema field. Svaki write korak
provjerava deadline i cancellation flag prije izvršenja; nema automatskog
retry-a write koraka (review 4.12) — ako se ne zna da li je prethodni upis
uspio, workflow staje i prijavljuje tačno stanje.

---

## 5. Frontend dizajn

Suštinski nepromijenjeno iz V1 (poglavlje 4), sa ispravkama iz review-a:

- `EmailDraftPanel` (ne `EmailDictationPanel` — imenovanje usklađeno sa
  "draft, ne compose/send" terminologijom kroz cijeli tok).
- IPC: **postojeći** `window.ricky.executeTool({name: "email_prepare_draft", ...})`
  — nema novog `email:compose` IPC kanala niti `emailAPI` preload expose-a
  (review 3.2 — smanjuje broj mjesta gdje se sigurnost može razići).
- `ConfirmationDialog`: novo eksplicitno renderovanje za
  `email_prepare_draft` (ne heuristika na substring "email"/"mail" u
  `action_name`, review 4.5) — naslov "Priprema email drafta", primarno
  dugme "Pripremi draft", trajna poruka "Ricky neće poslati email", nakon
  uspjeha "Draft je popunjen u posebnom Chrome prozoru. Pregledaj ga i
  pošalji ručno."
- Voice state `email_dictation` — nepromijenjeno iz V1.

---

## 6. Prvi-put postavka (onboarding za izolovani profil)

Pošto izolovani Chrome profil ima svoju, praznu sesiju:

1. Prvi put kad korisnik zatraži email draft, `GmailDraftAdapter` otvara
   izolovani profil i detektuje da nije ulogovan.
2. UI jasno kaže: "Prvi put: uloguj se na svoj Gmail nalog u ovom posebnom
   prozoru. Riki ne vidi niti čuva tvoju lozinku — samo koristi sesiju koja
   ostane nakon prijave."
3. Korisnik se loguje ručno (agent ne dira login formu — izvan dosega
   `email_prepare_draft` alata potpuno).
4. Sesija ostaje u perzistentnom `--user-data-dir` (nije incognito) — svaki
   sljedeći put je već ulogovan.
5. Settings panel dobija opciju "Zaboravi Gmail sesiju" (briše
   `--user-data-dir` sadržaj) — korisnička kontrola, isti princip kao
   postojeći "obriši lokalne podatke" pattern iz sigurnosnog backloga.

---

## 7. Edge case-ovi specifični za Gmail/CDP pristup

| Scenario | Ponašanje |
|---|---|
| Korisnik nije ulogovan u izolovani profil | Vidi poglavlje 6 — traži se ručna prijava, workflow ne nastavlja |
| Više Google naloga u izolovanom profilu | Koristi se samo unaprijed izabrani (poglavlje 4.5); ako nije izabran, traži se korisnička odluka prije prvog korištenja |
| Gmail promijeni DOM strukturu (redesign) | `identify_compose_dialog`/selektori padaju → `UNSUPPORTED_GMAIL_UI` greška, ne pokušaj slijepog fallbacka na klik/tab |
| Više minimiziranih draft-ova odjednom | Fail-closed (poglavlje 4.3, tačka 4) — ne bira se "prvi" |
| Chrome update mijenja CDP ponašanje | Faza A0 spike + periodičan smoke test protiv stvarnog Gmail-a prije release-a |
| Mrežni prekid tokom workflow-a | Deadline istekne → draft se prijavljuje kao djelimično/neuspješno popunjen, bez lažnog `ok=true` |
| Korisnik zatvori izolovani Chrome prozor ručno tokom diktata | Sljedeći write korak detektuje da CDP target ne postoji → workflow staje, traži novo pokretanje |
| Gmail "Confidential mode" ili druge compose varijante | Van obima MVP-a — adapter cilja samo standardni compose dialog; ako se detektuje nestandardna varijanta, `UNSUPPORTED_GMAIL_UI` |
| Non-default jezik Gmail interfejsa | Selektori targetirani preko DOM strukture/ARIA role gdje je moguće (ne lokalizovan tekst dugmadi) — provjeriti u Faza A0 spike-u da li Gmail-ovi ARIA labeli variraju po jeziku interfejsa |

---

## 8. Šta NE raditi (eksplicitno van obima, nepromijenjeno + prošireno)

- Ne implementirati SMTP/IMAP/Gmail API/OAuth — ostaje computer-use (CDP)
  pristup, ne API integracija.
- Ne čuvati Gmail lozinku — korisnik se loguje ručno, sesija živi u
  izolovanom profilu.
- Ne dodavati attachment-e.
- Ne slati automatski — Send je strukturalno nedostižan (poglavlje 4.4).
- Ne parsirati email adrese iz glasovnog unosa — korisnik ih potvrđuje ručno.
- Ne čitati postojeće emailove/inbox.
- Ne dijeliti izolovani Chrome profil sa korisnikovim regularnim Chrome
  profilom niti sa bilo kojim drugim tool-om.
- Ne izlagati CDP konekciju/port van Python backend procesa.
- Ne implementirati Outlook adapter u istoj fazi (Faza F, kasnije, van MVP-a).
- Ne implementirati bez prethodnog review-a OVOG plana od strane korisnika.

---

## 9. Zavisnosti

| Zavisnost | Status | Napomena |
|---|---|---|
| Permission/confirmation engine (FAZA 10) | ✅ postoji | Ponovo koristi se bez izmjene |
| `ToolExecutor` (FAZA 15) | ✅ postoji | `email_prepare_draft` ide kroz njega, bez paralelnog puta |
| ConfirmationDialog (FAZA 9) | ✅ postoji | Treba prošireno renderovanje (poglavlje 5) |
| Confirmation jednokratnost (S-04) | ✅ postoji | Ponovo koristi se za hash-based potvrdu |
| Chrome instaliran na korisnikovom sistemu | Pretpostavka | Ako nije, `email_prepare_draft` vraća jasnu grešku |
| Python CDP klijent (npr. `websockets` paket) | **NOVA zavisnost** | Mala, jednonamjenska (WebSocket JSON-RPC ka CDP) — nema postojeće WebSocket biblioteke u `pyproject.toml`; potvrditi tačan izbor u Faza A0 spike-u |
| `uiautomation` (postojeći) | Nije potreban za ovaj tool | Gmail adapter NE koristi Phase 13/14 UIA alate — ostaju nedirani, van dosega ovog toka |

---

## 10. Sigurnosna analiza

### 10.1 Attack surface

| Površina | Rizik | Ublažavanje |
|---|---|---|
| `email_prepare_draft` tool poziv | Srednji | `risk=high`, `requires_confirmation=True`, `requires_computer_mode=True` — postojeći gate |
| CDP debug port | Visok ako pogrešno konfigurisan | Loopback-only, nasumičan port, proces-owned (poglavlje 2.4) |
| Izolovan Chrome profil | Nizak (izolovan od regularnog browsinga) | Poseban `--user-data-dir`, briše se na zahtjev korisnika |
| Body/To/Subject sadržaj | Nizak (podatak, ne instrukcija) | `CDP Input.insertText` samo u poznata polja; body se nikad ne vraća modelu kao izvršiv sadržaj |
| Prompt injection u diktiranom textu | Nizak | Tretira se kao neizvršiv podatak (review 4.8 princip) — ne interpretira se, ne mijenja workflow |
| Agent pokuša Send | **Strukturalno nemoguć put** | Adapter nema click/keypress sposobnost van poznatih text-input selektora (poglavlje 4.4) |
| Pogrešna adresa primaoca | Visok (ljudska greška, ne sigurnosni bug) | Korisnik vidi i potvrđuje To/Subject prije unosa (isto kao V1) |

### 10.2 Šta se dešava ako agent/model svejedno "pokuša" Send

```
Pokušaj 1: model zatraži email_prepare_draft sa drugim/izmijenjenim payload-om
         → confirmation je vezana za hash TAČNOG payload-a → CONFIRMATION_MISMATCH

Pokušaj 2: model bi (hipotetički) htio kliknuti nešto u compose prozoru
         → GmailDraftAdapter nema click() metodu u svom API-ju uopšte
         → nema koda koji bi to izvršio, bez obzira šta model "zatraži"

Pokušaj 3: model pokuša ponovo email_prepare_draft nakon uspjeha
         → prethodna confirmation je potrošena (single-use, S-04) → treba nova,
           svježa korisnička potvrda za bilo koji naredni pokušaj

Pokušaj 4: prompt injection unutar diktiranog body teksta ("pošalji ovo odmah")
         → body je podatak upisan u textarea, ne instrukcija → ne pokreće
           nikakav dodatni tool poziv niti mijenja workflow
```

---

## 11. Fazni redoslijed implementacije

### Faza A0 — tehnički spike, BEZ ijedne linije produkcijskog koda

- Potvrditi da CDP (`Accessibility.getFullAXTree` + `DOM.querySelector`)
  pouzdano vidi Gmail-ov compose dialog u izolovanom profilu.
- Identifikovati stabilne selektore/ARIA role za To/CC/BCC/Subject/Body
  polja i za sam compose dialog kontejner.
- Potvrditi da se compose može otvoriti preko launch-argument URL-a
  (`--app=https://mail.google.com/mail/u/0/#inbox?compose=new` ili
  ekvivalent) bez potrebe za kucanjem u adresnu traku.
- Izmjeriti pouzdanost detekcije "tačno jedan aktivan compose dialog" kad
  postoji više minimiziranih draft-ova.
- Izabrati konkretnu Python CDP biblioteku/pristup (poglavlje 9).
- Izlaz: bilješka sa nalazima, BEZ korisničkog obećanja, bez trajnog koda.

### Faza A — osnovni GmailDraftAdapter, bez glasa

- `GmailDraftAdapter` sa uzim op-setom (poglavlje 4.2).
- Ručni unos To/Subject/Body u panelu (bez diktata).
- Bez confirmation UI-ja još — direktan poziv radi validacije targetiranja.

### Faza B — `email_prepare_draft` kroz `ToolExecutor` + confirmation

- Registracija regularnog tool-a.
- Hash-based jednokratna potvrda.
- Ispravljen `ConfirmationDialog` (poglavlje 5).
- Kratkotrajan draft store + redigovan action receipt (poglavlje 4.6).

### Faza C — voice-first UI

- `EmailDraftPanel` + `email_dictation` voice state.
- Glasovni readback primaoca/predmeta prije potvrde.
- Pristupačnost (screen reader, slovkanje adrese) — vidi review poglavlje 7,
  primjenjuje se identično.

### Faza D — onboarding i profil management

- Prvi-put flow (poglavlje 6).
- "Zaboravi Gmail sesiju" u Settings.

### Faza E — red-team i edge-case testovi

- Puna lista iz poglavlja 12, prije uključivanja funkcije bilo kom korisniku.

### Faza F — Outlook adapter (opciono, kasnije, van MVP-a)

- Ako se pokaže stvarna potreba — poseban adapter, vjerovatno i dalje preko
  UIA (Outlook desktop nema CDP), sa istim principima izolacije koliko je
  izvodljivo (npr. provjera da je ciljani Outlook prozor upravo kreiran od
  strane ovog workflow-a, ne bilo koji postojeći Outlook prozor).

---

## 12. Obavezni testovi prije uključivanja funkcije

### 12.1 Permission i confirmation
1. Bez Computer Mode: `COMPUTER_MODE_REQUIRED`.
2. Bez potvrde: `CONFIRMATION_REQUIRED`.
3. Promjena bilo kog polja nakon potvrde invalidira confirmation (hash mismatch).
4. Potvrda je jednokratna — drugi pokušaj sa istim `confirmation_id` ne uspijeva.
5. Istekla potvrda se ne može izvršiti.

### 12.2 CDP/profil integritet
6. Debug port je isključivo na `127.0.0.1` — pokušaj konekcije sa druge mašine ne uspijeva (ili port uopšte nije dostupan van loopback-a).
7. Izolovani profil ne dijeli kolačiće sa korisnikovim regularnim Chrome profilom (provjeriti da login u jednom ne utiče na drugi).
8. Origin provjera odbija `mail.google.com.evil.example` i slične varijante.
9. Zatvaranje CDP targeta (korisnik zatvori prozor) tokom workflow-a zaustavlja sljedeći write korak.
10. Više aktivnih compose dialoga → fail-closed, ne izbor prvog.
11. Nepoznata Gmail DOM struktura → `UNSUPPORTED_GMAIL_UI`, bez fallbacka na klik/tab.

### 12.3 Send zabrana
12. `GmailDraftAdapter` nema click/keypress metodu dostupnu pozivaocu (statička/tip provjera, ne samo runtime test).
13. Nijedan CDP `Input.dispatchMouseEvent` poziv se ne emituje tokom cijelog workflow-a (provjeriti kroz CDP event log u testu).
14. Korisnikov fizički klik na Send u tom istom prozoru i dalje radi (agent ga ne blokira).

### 12.4 Sadržaj i privatnost
15. Body/To/CC/BCC se ne pojavljuju u action log-u.
16. Confirmation DB ne čuva plaintext draft — samo hash.
17. Activity timeline ne otkriva BCC niti punu adresu.
18. Memorijski draft se briše nakon uspjeha/greške/cancel-a/TTL-a.
19. Tool result vraćen modelu ne sadrži puni body.

### 12.5 Cancellation i greške
20. Stop prije prvog write koraka ostavlja compose prozor netaknutim.
21. Stop između polja sprječava sljedeći write korak.
22. Timeout ne ostavlja pozadinski proces koji nastavlja pisati.
23. Djelimično popunjen draft se prijavljuje tačno (ne lažni `ok=true`).

### 12.6 Pristupačnost
24. Screen reader čita "Pripremi draft", ne "Pošalji".
25. Primaoci se mogu pročitati/slovkati prije potvrde.
26. Glasovna riječ "pošalji" sama ne potvrđuje niti šalje email.

---

## 13. Acceptance kriteriji za bezbjedan MVP

- Faza A0 spike potvrdio je da CDP pouzdano targetira Gmail compose polja.
- `email_prepare_draft` prolazi isključivo kroz `ToolExecutor`.
- Chrome se pokreće u izolovanom, aplikacijom-kontrolisanom profilu — nikad
  korisnikov regularni profil.
- CDP port je loopback-only, nasumičan, proces-owned.
- `GmailDraftAdapter` nema click/keypress sposobnost u svom javnom API-ju.
- Origin i compose-dialog identitet se provjeravaju prije SVAKOG write koraka.
- Confirmation je jednokratna, vezana za hash tačnog drafta.
- Confirmation UI govori "Pripremi draft", nikad "Pošalji".
- Osjetljiv sadržaj (To/CC/BCC/Subject/Body) nije trajno sačuvan u plaintext
  audit/confirmation/event podacima.
- Cancellation i eksplicitan deadline rade između svakog koraka.
- Svi testovi iz poglavlja 12 prolaze.
- Korisnik je ručno testirao stvaran Gmail UI i pristupačnost.
- Dokumentacija kaže tačno šta je tehnički garantovano, bez preširoke tvrdnje.

---

## 14. Mapiranje nalaza iz sigurnosnog review-a (V1) na ovaj plan

| Review nalaz | Status u V2 |
|---|---|
| 4.1 Paralelni endpoint zaobilazi ToolExecutor | Zatvoreno — `email_prepare_draft` ide isključivo kroz `ToolExecutor` (pogl. 4.1) |
| 4.2 Tekstualna Send-blokada nije granica | Zatvoreno na korijenu — allowlist arhitektura, adapter nema click sposobnost (pogl. 4.4) |
| 4.3 TOCTOU tokom višekoraknog workflow-a | Zatvoreno — eksplicitna provjera prije svakog write koraka (pogl. 4.3) |
| 4.4 Plaintext čuvanje sadržaja | Zatvoreno — kratkotrajan memory store + hash-based confirmation (pogl. 4.6) |
| 4.5 ConfirmationDialog "Pošalji" semantika | Zatvoreno — eksplicitno "Pripremi draft" renderovanje (pogl. 5) |
| 4.6 Tab/Enter navigacija, SendKeys fallback | Zatvoreno — CDP `Input.insertText` po eksplicitnom selektoru, bez Tab-a (pogl. 4.4) |
| 4.7 Gmail/Chrome nije bezbjedan za V1 | Adresirano direktno — izolovan profil + CDP eliminiše "koji tab" problem iz korijena (pogl. 2.3) |
| 4.8 `external_content_seen` pogrešno korištenje | Zatvoreno — body tretiran kao podatak, ne diže flag (pogl. 10.1) |
| 4.9 Globalni Submit/Confirm block bi kvario druge tokove | Ne primjenjivo — nema globalne blokade, allowlist je scoped na ovaj adapter (pogl. 4.4) |
| 4.10 Integritet adrese primaoca | Nepromijenjeno iz V1 — korisnik ručno unosi/potvrđuje, bez alias rezolucije (pogl. 8, V1) |
| 4.11 Više prozora/varijanti klijenta | Zatvoreno za Gmail — fail-closed na više compose dialoga (pogl. 4.3) |
| 4.12 Timeout/retry/cancellation eksplicitnost | Zatvoreno — sopstveni monotoni deadline, bez auto-retry write koraka (pogl. 4.7) |
| 3.8 `timeout_ms` se ne sprovodi u executor-u | Priznato i zaobiđeno (ne popravljeno na executor nivou — to je poseban, širi zadatak) — adapter ima svoj deadline (pogl. 4.7) |
| 3.9 Async pseudokod vs. sinhron executor | Zatvoreno — plan eksplicitno traži sinhron `GmailDraftAdapter` sa polling-om, ne `asyncio.sleep` pseudokod |

---

## 15. Otvorena pitanja za Faza A0 spike (ne pretpostavljati odgovor unaprijed)

1. Da li Gmail-ovi ARIA labeli za To/Subject/Body variraju po jeziku
   interfejsa naloga (utiče na to da li su selektori jezik-nezavisni)?
2. Koja tačno Python CDP biblioteka (`websockets` + ručni JSON-RPC, ili
   gotova biblioteka) daje najmanju površinu/najmanje dependency-ja?
3. Da li `--app=` launch mod (bez browser chrome-a oko prozora) mijenja
   dostupnost DOM/AX stabla u odnosu na regularan prozor?
4. Koliko pouzdano CDP `Accessibility.getFullAXTree` prati DOM promjene kad
   korisnik (ili Gmail auto-save) mijenja sadržaj tokom workflow-a?
5. Da li je potrebna eksplicitna provjera da Chrome verzija korisnika uopšte
   podržava potrebne CDP domene (starije verzije mogu nedostajati).
