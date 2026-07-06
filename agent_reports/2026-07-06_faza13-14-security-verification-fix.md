# Agent report — FAZA 13/14 verifikacija: active window enforcement nije bio ožičen

**Datum:** 2026-07-06

## Scope

Verifikacija pi-jevog FAZA 13 (`agent_reports/2026-07-06_faza13-computer-use-v1.md`) i FAZA 14
(`agent_reports/2026-07-06_faza14-element-targeting.md`) rada — na zahtjev korisnika ("pi je
kompletno završio fazu-19, provjeri"). Tokom verifikacije otkriveno da je pi u istoj sesiji, bez
najave, uradio i FAZU 13 i FAZU 14 (computer-use, najrizičnija kategorija alata u projektu), ne
samo FAZU 19. Korisnik je odlučio (upitan eksplicitno) da ja odmah popravim nađeni gap prije nego
išta od ovoga uđe u commit.

## GitNexus impact

`gitnexus_detect_changes` nakon popravke → risk **MEDIUM**, svi dirani simboli su tačno oni koje
sam i namjeravao dirati (`permission_engine.py`, `tool_registry.py`, `tool_executor.py` — sve dio
pi-jevog necommitovanog FAZA13/14 rada + moje dopune). Nema neočekivanih pogođenih simbola.

## Šta je nađeno (prije popravke)

Pi je ispravno implementirao `check_active_window()` u `permission_engine.py` — fail-closed,
case-insensitive, `blocked_apps` ima prioritet nad `allowed_apps`, ispravno ožičen u
`tool_executor.py` nakon `check_permission()`. 7 testova potvrđuje da ta funkcija radi ispravno
**izolovano** (ručno napravljen `ToolDefinition` objekat u svakom testu).

**Problem:** `tool_registry.py`-jev `_def()` helper za SVIH 9 novih computer-use toolova
(`computer_open_app/type_text/press_key/click/scroll` + `computer_find_elements/click_element/
set_text_element/get_element_text`) je hardkodirao:

```python
requires_active_window_match=False,
allowed_apps=[],
blocked_apps=[],
```

bez ijednog parametra da se to promijeni. Mehanizam je postojao i bio testiran, ali ga nijedan
stvarni registrovan tool nije koristio — potpuno neaktivan u praksi. Posljedica: Ricky je mogao
kucati tekst ili klikati bilo gdje na ekranu — uključujući otvoren PowerShell/cmd prozor, Registry
Editor, Task Manager, Credential Manager, password manager, bankarski sajt — potpuno neometano dok
god je Computer Mode uključen. Ovo je tačno scenario koji `SECURITY_HARDENING_PLAN.md` sekcija 9
eksplicitno navodi kao razlog za default blocklist (`powershell.exe, cmd.exe, regedit.exe,
taskmgr.exe, mmc.exe, credential manager, password managers, banking apps/sites, crypto wallets,
remote desktop apps`), ali ta lista nigdje nije bila primijenjena.

Dodatni nalaz: nekonzistentna potvrda. `computer_click_element` (FAZA 14) je ispravno imao
`requires_confirmation=True` (backend-enforced, preko `confirmation_id`). Ali `computer_click`/
`computer_type_text` (FAZA 13) i `computer_set_text_element` (FAZA 14) — svi risk="high" — nisu
imali `requires_confirmation=True`. Njihova `confirmed`/`risk` polja postoje u JSON schema-i, ali
handler kod (`computer.py`) ih nikad ne čita — čisto "molim model da pita korisnika" bez ikakve
backend garancije, za razliku od kritičnih toolova koji imaju stvaran `confirmation_id` gate.

Testovi (49+18) su prolazili jer su testirali `check_active_window()` u izolaciji i handler logiku
(mockovan Win32/UIA sloj) — nijedan test nije provjeravao da li stvarni registrovan tool ima
popunjen `blocked_apps`, tako da je gap prošao kroz "172/172 passed" bez upozorenja.

Ovo NIJE regresija u odnosu na legacy PowerShell (koji je koristio `SendKeys::SendWait` bez ikakve
active-window provjere) — ali cijela poenta zatvaranja Security Gate 0 prije FAZE 13/14 bila je da
se ova zaštita konačno doda prije nego što se computer-use alati prošire, ne da se legacy
nesigurnost samo prepiše u Python.

## Šta je urađeno (popravka)

1. **`permission_engine.py`** — dodat `DEFAULT_BLOCKED_APPS` (modul-level konstanta, jedan izvor
   istine): `powershell.exe, powershell_ise.exe, pwsh.exe, cmd.exe, regedit.exe, taskmgr.exe,
   mmc.exe, credentialuibroker.exe, mstsc.exe`. Kategorije iz spec-a koje nisu enumerabilne po
   imenu procesa (banking sites/password manageri unutar browsera) namjerno nisu pokušane —
   blokiranje `chrome.exe`/`msedge.exe` globalno bi pokvarilo svaku legitimnu web interakciju.
   Dokumentovano kao poznato ograničenje, ne prećutano.
2. **`tool_registry.py`** — `_def()` helperi za FAZA 13 i FAZA 14 sad primaju
   `requires_active_window_match`/`blocked_apps` parametre (ranije hardkodirano). Primijenjeno na:
   - `computer_type_text`, `computer_press_key`, `computer_click`, `computer_scroll` (FAZA 13)
   - `computer_click_element`, `computer_set_text_element` (FAZA 14)
   Namjerno preskočeno: `computer_open_app` (ne cilja postojeći prozor, spec ga ne pominje),
   `computer_find_elements`/`computer_get_element_text` (read-only; mogu čitati sadržaj bilo kojeg
   prozora što je poseban rizik, ali spec sekcija 9 eksplicitno pokriva samo write/interakciju
   toolove — ostavljeno kao follow-up, ne riješeno ovdje da se izbjegne prekomjeran obim popravke).
3. **`requires_confirmation=True`** dodano za `computer_click`, `computer_type_text`,
   `computer_set_text_element` — usklađeno sa `computer_click_element` koji je to već imao.
   **Poznata posljedica:** ovo dodaje friction čak i benignom kucanju (npr. diktiranje bilješke) —
   `computer_type_text`-ov opis je ranije eksplicitno govorio "Do not ask for extra confirmation
   just to type", ali ta namjera nikad nije imala tehnički mehanizam iza sebe osim modelovog
   dobrovoljnog izbora, što protivrječi principu "ne vjerovati modelu za sigurnosno-kritične
   odluke" (threat model eksplicitno navodi "model output koji pokušava iznuditi akciju"). Ovo je
   svjesna bezbjednosna odluka, ne previd — ali otvara produkt/UX pitanje (da li Dictation Mode
   kucanje treba biti poseban, manje rizičan tool od `computer_type_text`) koje ostavljam kao
   follow-up, ne rješavam ovdje jednostrano.
4. **Testovi** — 8 novih (`test_phase13_computer_tools.py` +4, `test_phase14_element_targeting.py`
   +4) koji provjeravaju STVARNE registrovane toolove preko `/tools/execute`, ne izolovane
   `ToolDefinition` objekte: blokiran aktivni prozor (`powershell.exe`/`regedit.exe`) odbija
   izvršenje čak i sa odobrenom potvrdom; potvrda se zahtijeva prije nego što se stigne do
   argument-validacije; end-to-end uspješan tok (propose → approve → execute sa
   `confirmation_id` + bezbjedan aktivni prozor) stvarno radi.
5. Ažurirane 4 postojeće `test_computer_tool_invalid_args` parametrizacije za `computer_type_text`/
   `computer_click` — sad prvo kreiraju i odobravaju potvrdu vezanu za tačan payload prije slanja,
   pošto permission-provjera sad ide prije argument-validacije za te dvije alatke.

## Verifikacija

1. `python -m pytest tests -q` — **180 passed** (172 pi-jeva + 8 novih), nema regresije.
2. `npm run check` — čisto (svi `.cjs` fajlovi).
3. `gitnexus_detect_changes` — risk MEDIUM, svi dirani simboli očekivani.
4. Ručno pregledan `computer.py`/`element_target.py` handler kod da potvrdim da `confirmed`/`risk`
   argumenti STVARNO nisu nigdje čitani (potvrđeno — čisto dokumentacioni schema polja).

## Šta nije dirano

- `computer.py`/`element_target.py` handler implementacije (Win32 SendInput, UIA pozivi) — pi-jev
  kod, funkcionalno solidan, nisam ga mijenjao.
- FAZA 19 finalizacija (`electron-builder.yml`, `pythonProcess.cjs` packaged-mode, `pyproject.toml`)
  — pregledano, ispravno, nedirano.
- `computer_find_elements`/`computer_get_element_text` (read-only element toolovi) — ostaju bez
  active window zaštite, namjerno, vidi follow-up.
- `computer_open_app` — ostaje bez active window zaštite, namjerno (ne cilja postojeći prozor).

## Rizici / ograničenja

- **Kategorije iz spec-a koje nisu pokrivene**: banking sites, password manageri, remote desktop
  apps koji rade UNUTAR browsera (chrome.exe/msedge.exe) ne mogu se blokirati po imenu procesa bez
  blokiranja svake legitimne web interakcije. Ovo ostaje stvaran, neriješen gap — rješenje bi
  zahtijevalo URL/tab-content svjesnost (van obima ove popravke).
- **UX friction za Dictation Mode**: `computer_type_text` sad uvijek zahtijeva potvrdu, što może
  značiti da svako diktiranje teksta u drugu aplikaciju treba UI tok za odobrenje koji trenutno ne
  postoji (Confirmation Review Mode je pomenut u UI redesign dokumentima ali nije implementiran).
  Ovo je poznata, namjerna bezbjednosna odluka — ali stvara stvaran produkt-nivo problem koji treba
  riješiti prije nego što Dictation Mode preko `computer_type_text` postane glavni tok.
- **`computer_find_elements`/`computer_get_element_text`** i dalje mogu čitati tekst sa ekrana bilo
  koje aplikacije (npr. maskiranu lozinku ako UIA expose-uje `Value` property) bez active window
  zaštite — nije "write" akcija pa je van scope-a ove popravke po spec-u, ali je realan
  information-disclosure rizik vrijedan budućeg razmatranja.

## Potreban follow-up

- Product odluka: kako Dictation Mode treba raditi sa novim `computer_type_text` confirmation
  gate-om — poseban, niže-rizičan "dictate_text" tool za samo-tekst bez ciljanja specifičnih akcija,
  ili implementirati Confirmation Review Mode UI tok prije nego korisnici koriste Computer Mode
  diktat u praksi.
- Razmotriti active-window zaštitu za `computer_find_elements`/`computer_get_element_text`
  (information disclosure, ne interakcija).
- Razmotriti eksplicitan `mstsc.exe`/`CredentialUIBroker.exe` listing nije dovoljan za sve
  "remote desktop apps"/"credential manager" scenarije (druge remote-desktop klijente treće strane
  nisu pokrivene) — treba periodično revidirati listu kako se nove kategorije rizika pojave.

## Potrebna korisnička potvrda

Preporučeno: donijeti odluku o Dictation Mode UX pitanju iz "Potreban follow-up" prije nego što se
Computer Mode diktat aktivno reklamira korisnicima aplikacije — trenutno bi svaki pokušaj kucanja
preko `computer_type_text` tražio potvrdu koja još nema UI tok.
