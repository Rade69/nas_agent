# Faza A — GmailDraftAdapter (prvi pravi kod, i dalje bez tool registracije/glasa)

**Datum:** 2026-07-13
**Scope:** `python_backend/app/services/gmail_draft_adapter.py` (novo),
`python_backend/tests/test_gmail_draft_adapter.py` (novo),
`python_backend/pyproject.toml` (nova zavisnost `websockets`).
**Plan:** [`docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md`](../docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md)
poglavlje 11, Faza A ("osnovni GmailDraftAdapter, bez glasa... bez confirmation
UI-ja još — direktan poziv radi validacije targetiranja").

## GitNexus impact

Nova, prije-nezabilježena datoteka — `detect_changes` nije prikazao ništa iz
ovog rada dok index nije osvježen (`npx gitnexus analyze`, +11 novih
simbola). Nakon osvježavanja: modul nije registrovan ni u jednom postojećem
pozivnom putu (nema `ToolExecutor`/`tool_catalog` registracije još — namjerno,
to je Faza B), pa je blast radius potpuno izolovan na novi fajl. Ručno
potvrđen `git diff --stat`: jedina izmjena POSTOJEĆEG fajla je 6 dodatih
linija u `pyproject.toml` (nova zavisnost). Sve ostalo (`src/lib/realtime.ts`,
`docs/MIGRATION_PLAN.md`) u trenutnom radnom stablu pripada "pi" agentovom
paralelnom voice reliability radu (R3) — nedirano, potvrđeno da nije dio
ovog diff-a.

## Šta je urađeno

`GmailDraftAdapter` — uzak, allowlist-only skup operacija (poglavlje 4.2
plana), BEZ ijedne click/keypress metode u javnom API-ju:

- `launch_isolated_chrome(data_dir)` — pokreće Chrome sa `--user-data-dir`
  van korisnikovog regularnog profila, `--remote-debugging-port` nasumičan,
  `--remote-debugging-address=127.0.0.1` (loopback-only).
- `is_logged_in(session)` — provjerava da li je trenutni URL na
  `mail.google.com` origin-u (Google-ova sopstvena JS logika preusmjerava na
  `accounts.google.com` ako profil nije ulogovan).
- `open_compose(session)` — navigira na compose preko `Page.navigate` NAKON
  potvrđenog login-a (ne kao launch argument — vidi "Faza A0 korekcija"
  niže), fail-closed na 0 ili >1 pronađenih compose dialoga.
- `set_subject_field` / `set_body_field` / `set_recipient_field` — `DOM.focus`
  (direktan fokus na node, bez sintetizovanog klika) + `Input.insertText`
  (isti primitiv koji koristi pravo IME/paste, ne simulacija tipka-po-tipka).
- `verify_draft_values` — čita nazad upisane vrijednosti radi potvrde.
- `close_isolated_chrome` — gasi Chrome proces.

Sinhron dizajn (`websockets.sync.client`, ne `asyncio`), namjerno usklađen
sa `ToolExecutor.execute()`-ovim sinhronim ugovorom — sigurnosni review
(sekcija 3.9) je eksplicitno upozorio da bi async handler registrovan
"kako je napisan" bio nekompatibilan.

## Ručna end-to-end verifikacija protiv PRAVOG Gmail-a

Pošto ovo zahtijeva stvaran login (agent to ne može uraditi umjesto
korisnika), modul je testiran uživo uz korisnikovo učešće (isti izolovani
profil kreiran u Fazi A0 spike-u, samo sad kroz PRAVI adapter kod, ne
throwaway spike skriptu):

1. **Prvi pokušaj** — `is_logged_in` vratio `false` iako je korisnik bio
   ulogovan. Uzrok: provjera se dešavala prije nego se inicijalna
   navigacija stigla učitati (CDP target postoji čim se tab kreira, ne kad
   je sadržaj spreman). **Popravka:** `_wait_for_url_to_settle()` — čeka da
   se URL ne mijenja kroz dva uzastopna provjeravanja umjesto fiksnog sleep-a.
2. **Drugi pokušaj** — i dalje `false`. Uzrok: Gmail-ov login tok ima
   redirect lanac (mail.google.com → accounts.google.com cookie-rotation →
   nazad), pa URL prolazi kroz privremeno `about:blank`/prelazna stanja gdje
   `document.readyState` već javlja "complete" iako sadržaj još nije stvaran
   inbox. Popravka je bila dio iste `_wait_for_url_to_settle` izmjene.
3. **Treći pokušaj** — login potvrđen, ALI `open_compose` javlja
   `GMAIL_COMPOSE_NOT_FOUND`. Uzrok: URL se ažurira na `?compose=new`
   SINHRONO, ali Gmail-ov JS renderuje sam dialog tek koji trenutak kasnije
   — URL "settled" ne znači DOM spreman. **Popravka:** dodato kratko
   pollanje (do 5s) za pojavu `[role="dialog"]` nakon navigacije, umjesto
   provjere tačno jednom.
4. **Četvrti pokušaj** — dialog nađen, Subject polje uspješno popunjeno, ALI
   `set_body_field` baca `GMAIL_FIELD_NOT_FOUND` za selektor koji je
   dijagnostika potvrdila da POSTOJI u DOM-u. Uzrok izolovan na CDP DOM
   domena `DOM.querySelector(nodeId=..., selector=...)` — nepouzdano vraćao
   prazan rezultat za scoped upit unutar dialog subtree-a, dok je
   JS-bazirani `element.querySelector(...)` (preko `Runtime.callFunctionOn`
   na resolved node object) dosljedno radio. Tačan uzrok CDP DOM domena
   ponašanja nije do kraja izoliran (posumnjano na staleness DOM stabla
   nakon Gmail-ovih vlastitih re-renderovanja), ali je popravka empirijski
   potvrđena kao pouzdana: `_find_in_dialog` sad koristi
   `DOM.resolveNode` → `Runtime.callFunctionOn` (`this.querySelector(...)`)
   → `DOM.requestNode` umjesto direktnog `DOM.querySelector(nodeId, ...)`.
   Ovo je i dalje čisto READ-ONLY, usko skopiran upit (samo unutar dialog
   subtree-a preko objectId-a), ne proizvoljno izvršavanje skripte nad
   stranicom.
5. **Peti pokušaj — potpun uspjeh.** Svih 5 provjera prošlo:
   - `logged_in: true`
   - `dialog_id` pronađen (tačno jedan)
   - Subject upisan i pročitan nazad TAČNO: `"Test predmet iz adaptera"`
   - Body upisan i pročitan nazad TAČNO, uključujući multi-line prelom reda:
     `"Prva linija.\nDruga linija."`
   - To polje upisano i pročitano nazad TAČNO: `"test-recipient@example.com"`
   - `verify_draft_values()` vratio `True`

Test draft je nakon toga obrisan (prazan subject), Chrome proces zatvoren.
Nijedan stray Chrome proces nije ostao (provjereno `Get-Process`).

## Zašto ovako

- Sve četiri popravke slijede isti princip iz plana: **fail-closed umjesto
  nagađanja** — svaka funkcija radije baca jasnu grešku (`GMAIL_NOT_LOGGED_IN`,
  `GMAIL_COMPOSE_NOT_FOUND`, `GMAIL_MULTIPLE_COMPOSE_DIALOGS`,
  `GMAIL_FIELD_NOT_FOUND`) nego da pretpostavi stanje koje nije potvrđeno.
- `_find_in_dialog`-ova JS-scoped pretraga i dalje poštuje "nema generičkog
  klika" garanciju iz plana (poglavlje 4.4) — mijenjen je SAMO mehanizam
  pronalaska elementa (DOM domen → Runtime domen), ne proširena sposobnost
  adaptera. I dalje nema nijedne metode koja bi mogla kliknuti/pritisnuti
  taster na proizvoljan element.
- Cc/Bcc namjerno vraćaju `GMAIL_CC_BCC_NOT_SUPPORTED` umjesto tihog
  ignorisanja — spike/Faza A nisu testirali te selektore (Gmail zahtijeva
  klik na "Cc/Bcc" link da ih otkrije), eksplicitna greška je bezbjednija
  od nagađanja.

## Šta nije dirano

- Nema `ToolDefinition`/`tool_catalog` registracije — modul se NE MOŽE
  pozvati preko modela/glasa još (Faza B).
- Nema confirmation gate-a, draft store-a, TTL-a — nema šta da se
  eksploatiše jer alat nije izložen nikome van direktnih Python poziva.
- `python_backend/app/agent/tool_executor.py`, `permission_engine.py` —
  nula izmjena.
- `src/lib/realtime.ts`, `docs/MIGRATION_PLAN.md` — pi-jev paralelni rad,
  netaknuto.

## Verifikacija

- `python -m pytest tests/test_gmail_draft_adapter.py -v` — **11 passed**
  (mockovan CDP sloj preko `FakeSession` sa scriptovanim odgovorima; ne
  zahtijeva pravi Chrome/login u CI-ju).
- `python -m pytest -q` (cijeli suite) — **294 passed** (283 prije + 11 novih).
- Ručna end-to-end verifikacija protiv PRAVOG Gmail naloga — vidi sekciju
  gore, 5 iteracija dok svih 5 provjera nije prošlo.
- `mcp__gitnexus__detect_changes` — nula postojećih simbola izmijenjeno van
  `pyproject.toml` (6 dodatih linija), potvrđeno ručnim `git diff --stat`.
- **Otkriven i popravljen bug u samom test fajlu tokom pisanja**: fake
  `time.monotonic()` u jednom testu je vraćao FIKSNU veliku vrijednost
  nakon prvog poziva umjesto monotono rastuće — ovo je uzrokovalo
  BESKONAČNU petlju u `open_compose`-ovom dialog-polling kodu (deadline
  izračunat iz te iste fiksne vrijednosti nikad nije mogao biti pređen),
  potrošivši ~172s CPU vremena prije nego što je uočeno i ubijeno. Popravljen
  fake da monotono raste po pozivu — dokumentovano u samom testu kao
  upozorenje budućim izmjenama ovog obrasca.

## Rizici/ograničenja

- CDP DOM domen `DOM.querySelector` (scoped) ponašanje nije do kraja
  razumljeno — zaobiđeno, ne popravljeno na izvoru. Ako se u budućnosti
  doda još scoped upita, koristiti `_find_in_dialog`-ov JS-scoped obrazac,
  ne generički `DOM.querySelector(nodeId, ...)`.
- To polje cilja `input[role="combobox"]` — nakon upisa teksta, Gmail
  obično zahtijeva Tab/Enter da "pretvori" upisan tekst u recipient chip;
  plan eksplicitno zabranjuje Tab/Enter simulaciju (rizik od pogrešnog
  fokusa), pa adapter NAMJERNO ostavlja sirov tekst u polju bez chip
  konverzije — korisnik će ovo vidjeti kad pregleda draft prije slanja,
  prihvatljiv trade-off, ali vrijedi eksplicitno testirati da li Gmail
  svejedno ispravno šalje na taj tekst ako ga korisnik ne dotakne dodatno.
- Cc/Bcc nisu podržani (eksplicitna greška, ne tih fail).
- Ponašanje sa Chrome verzijama različitim od one korištene u testu (150)
  nije provjereno.
- Multi-dialog fail-closed put je testiran samo mock-om (jedinični test),
  ne uživo protiv stvarnog Gmail-a sa dva otvorena drafta.

## Potreban follow-up

Faza B iz plana: registracija kao `email_prepare_draft` tool kroz
`ToolExecutor`, hash-bazirana jednokratna potvrda, kratkotrajan draft store,
ispravljen `ConfirmationDialog` render. Prije toga vrijedi razmotriti: da li
CC/BCC treba riješiti odmah ili ostaje odloženo za kasniju fazu.

## Potrebna korisnička potvrda

Korisnik je već uživo učestvovao u verifikaciji (login + posmatranje
rezultata) — ovaj dio je već potvrđen kroz sam proces rada. Sljedeći
checkpoint za korisničku potvrdu je nakon Faze B (kad alat postane pozivljiv
kroz confirmation tok).
