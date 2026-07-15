# Sigurnosna i arhitektonska analiza plana za Email Compose Tool

**Datum:** 2026-07-13  
**Status:** Review plana — implementacija nije započeta  
**Predmet analize:** [EMAIL_COMPOSE_TOOL_PLAN.md](./EMAIL_COMPOSE_TOOL_PLAN.md)  
**Repo stanje korišteno za provjeru:** commit `0719a26`, uz postojeće nekomitovane izmjene koje nisu dirane

---

## 1. Izvršni rezime

Osnovna odluka iz plana je dobra: agent treba samo pripremiti email draft, dok korisnik mora lično pregledati poruku i ručno je poslati. Izbjegavanje SMTP-a, Gmail API-ja, Microsoft Grapha, OAuth tokena, čitanja inboxa i attachmenta značajno smanjuje početnu napadnu površinu.

Plan ipak nije siguran za implementaciju u sadašnjem obliku. Najvažnija tvrdnja — da agentu na nivou koda može biti nemoguće poslati email — nije ostvariva samo blokiranjem naziva dugmeta `Send` i nekoliko prečica. Postojeći generički alati za koordinatni klik, UIA klik, unos teksta i pritisak tipki pružaju alternativne puteve za aktiviranje kontrole u pogrešno fokusiranom prozoru.

Najveće potrebne promjene su:

1. `email_prepare_draft` mora prolaziti kroz postojeći `ToolExecutor`; ne praviti paralelni endpoint koji direktno poziva computer-use handlere.
2. Uvesti capability lock vezan za tačno identifikovan email compose prozor. Dok je lock aktivan, agentu blokirati generičke click/key/type alate u tom prozoru i dozvoliti samo namjensko postavljanje poznatih polja.
3. Za prvu verziju podržati samo jedan konkretan klijent — preporučeno Outlook desktop — preko zasebnog adaptera i UI Automation identifikatora.
4. Ne koristiti koordinatne klikove, `Tab` navigaciju ni simulirani `Enter` za popunjavanje polja.
5. Ne čuvati kompletan email body, primaoce i predmet u plaintext confirmation/audit bazi.
6. Confirmation UI mora govoriti „Pripremi draft" ili „Ubaci u email", nikada „Pošalji email".

Preporučeni MVP je manji od originalnog plana, ali je realniji za samostalnog developera i pruža znatno jaču, provjerljivu sigurnost.

---

## 2. Šta je u planu dobro postavljeno

- Slanje ostaje isključivo korisnička radnja.
- Nema SMTP/IMAP integracije niti čuvanja email lozinki.
- Nema OAuth tokena i refresh logike u prvoj verziji.
- Korisnik prije izvršenja vidi primaoca, predmet i tijelo emaila.
- `email_compose` je označen kao high-risk i zahtijeva Computer Mode i potvrdu.
- Attachmenti i čitanje inboxa su eksplicitno van obima.
- Postoji ideja defense-in-depth zaštite, iako predloženi konkretni slojevi nisu dovoljni.
- Plan uključuje negativne i red-team testove.
- Postojeći permission engine već podržava potvrdu vezanu za tačan naziv toola i hash payload-a, rok važenja i jednokratno korištenje.
- Postojeći action log već redigira vrijednosti ključeva poput `body`, `text`, `content`, `password` i `token`.

Ove odluke treba zadržati u revidiranom planu.

---

## 3. Potvrđeno trenutno stanje aplikacije

### 3.1 Jedinstveni put izvršenja toolova već postoji

`ToolExecutor` trenutno centralizuje:

- pronalazak i status toola;
- runtime JSON Schema validaciju;
- Computer Mode provjeru;
- confirmation provjeru;
- active-window provjeru;
- cancellation state;
- action log.

I REST `/tools/execute` i Python agent runtime koriste ovaj sloj. Novi workflow ne smije napraviti paralelni put mimo njega.

Relevantno:

- [`python_backend/app/agent/tool_executor.py`](../python_backend/app/agent/tool_executor.py)
- [`python_backend/app/agent/permission_engine.py`](../python_backend/app/agent/permission_engine.py)
- [`python_backend/app/agent/arg_validation.py`](../python_backend/app/agent/arg_validation.py)

### 3.2 Renderer već ima generički, allowlistovan tool IPC

`window.ricky.executeTool(toolCall)` već mapira na tačno određeni `tools:execute` IPC kanal. Zato novi `email:compose` IPC kanal i poseban Electron handler nisu nužni. Korištenje postojećeg puta smanjuje količinu koda i broj mjesta na kojima se sigurnost može razići.

Relevantno:

- [`electron/preload.cjs`](../electron/preload.cjs)
- [`electron/main.cjs`](../electron/main.cjs)
- [`electron/core/ipc.cjs`](../electron/core/ipc.cjs)

### 3.3 Outlook trenutno nije dozvoljen u `computer_open_app`

`computer_open_app` koristi fiksnu allowlistu. Trenutno su dozvoljeni Notepad, Calculator, Paint, WordPad, Explorer, Chrome i Edge. Outlook nije dozvoljen. Pored toga, argument se zove `appName`, a pseudokod plana koristi `app_name`.

Ovo je dobar postojeći sigurnosni obrazac: ne treba ga zamijeniti proizvoljnim pokretanjem putanje. Outlook treba dodati kroz namjenski adapter ili strogo kontrolisanu alias mapu, bez `shell=True` i bez modelom kontrolisane izvršne putanje.

Relevantno:

- [`python_backend/app/tools/system/computer.py`](../python_backend/app/tools/system/computer.py)
- [`python_backend/app/agent/tool_catalog/phase13.py`](../python_backend/app/agent/tool_catalog/phase13.py)

### 3.4 `computer_press_key` ne podržava kombinacije iz plana

Trenutna Python shema prihvata samo pojedinačne tipke: `enter`, `return`, `tab`, `escape`, `delete`, `space` i strelice. Ne podržava `Ctrl+N`, `Ctrl+Enter`, `Alt+S` ni `Ctrl+Return`.

Zbog toga pseudokod nije izvršiv kako je napisan. Ne preporučuje se proširivanje generičkog keyboard toola modifier kombinacijama samo radi emaila, jer bi se time povećala napadna površina cijele aplikacije.

### 3.5 Unos teksta nije neutralna operacija

Postojeći `computer_type_text` pretvara:

- `\n` u fizički pritisak `Enter`;
- `\t` u fizički pritisak `Tab`.

Zato slanje `to + "\t"` i `subject + "\t"` nije sigurno. Ako se fokus promijeni, `Tab`, `Enter` ili nastavak teksta mogu djelovati na pogrešnu kontrolu ili drugi prozor.

### 3.6 UIA podrška postoji, ali je preširoka za sigurnosnu garanciju

`computer_click_element` i `computer_set_text_element` mogu pronaći prvi element koji zadovoljava kriterije. Name matching je substring, a izbor prvog rezultata nije dovoljan kada postoji više compose prozora ili više sličnih kontrola.

`computer_set_text_element` koristi `ValuePattern.SetValue`, što je bolja osnova od keyboard simulacije, ali fallback na `SendKeys` ponovo uvodi fokus i keystroke rizik.

Relevantno:

- [`python_backend/app/tools/system/element_target.py`](../python_backend/app/tools/system/element_target.py)
- [`python_backend/app/agent/tool_catalog/phase14.py`](../python_backend/app/agent/tool_catalog/phase14.py)

### 3.7 Potvrda je jednokratna i troši se prije handlera

Permission engine atomarno troši odobrenje prije poziva handlera. To je ispravno fail-closed ponašanje i sprečava replay. Posljedica je da neuspjeli pokušaj otvaranja ili popunjavanja drafta zahtijeva novu potvrdu.

Ovo treba jasno prikazati korisniku. Aplikacija ne smije neprimjetno automatski pokušati ponovo sa istim odobrenjem niti tražiti široku potvrdu za više budućih pokušaja.

### 3.8 `timeout_ms` se trenutno ne sprovodi

`ToolDefinition.timeout_ms` postoji, ali trenutni `ToolExecutor` sinhrono poziva `tool.handler(request.arguments)` bez enforcementa timeouta. Zato postavljanje `timeout_ms=30000` ne znači da će workflow stvarno biti prekinut poslije 30 sekundi.

Email workflow mora imati sopstveni monotoni deadline i kontrolisane per-step timeout vrijednosti, ili se prije implementacije mora dodati opšti executor timeout na način koji ne ostavlja pozadinski OS thread da nastavi kucati nakon vraćene greške.

### 3.9 Pseudokod je `async`, a postojeći executor je sinhron

Plan predlaže `async def email_compose_handler`, dok postojeći `ToolExecutor` poziva handler sinhrono. Nekritičko registrovanje coroutine handlera moglo bi vratiti coroutine objekat umjesto rezultata ili proizvesti nekonzistentno ponašanje.

Za MVP koristiti sinhroni, eksplicitni workflow sa kratkim polling intervalima i cancellation provjerama, ili prethodno planski proširiti cijeli executor za sigurne async handlere. Ne uvoditi samo lokalni `asyncio.sleep` pseudokod.

---

## 4. Sigurnosni nalazi po prioritetu

### 4.1 KRITIČNO — direktni `/email/compose` handler zaobilazi centralni gate

Planirani endpoint direktno poziva interne computer-use handlere. Time se mogu zaobići ili razdvojiti:

- potvrda;
- active-window enforcement;
- cancellation;
- action receipt;
- argument validacija;
- jednoobrazno error mapiranje;
- legacy fail-closed pravila.

#### Preporuka

Registrovati jedan regularan tool, preporučeno `email_prepare_draft`, i izvršavati ga kroz postojeći `ToolExecutor`. Renderer treba koristiti postojeći `window.ricky.executeTool`.

Ako composite handler interno koristi niže primitive, one ne smiju biti obični javni handleri koje model može proizvoljno kombinovati. Treba ih izdvojiti u interni `OutlookDraftAdapter` sa vlastitim provjerama identiteta prozora i polja.

---

### 4.2 KRITIČNO — tekstualni Send block nije sigurnosna granica

Lista obrazaca `Send`, `Pošalji`, `Senden`, `Envoyer` i slično ne može pokriti:

- koordinatni klik;
- dugme bez očekivanog accessible name-a;
- drukčiji `AutomationId`;
- `Enter` ili `Space` nad fokusiranim dugmetom;
- InvokePattern nad kontrolom koju je model našao po drugom kriteriju;
- drugi jezik ili nestandardni mail klijent;
- promjenu fokusa između provjere i akcije;
- aktiviranje stavke iz menija ili accessibility actiona.

System prompt je koristan samo kao pomoćno ponašajno pravilo. Ne treba ga računati kao stvarnu tehničku sigurnosnu granicu.

#### Preporuka: email draft capability lock

Dok je agentov email workflow aktivan za određeni compose prozor:

- blokirati `computer_click` u tom prozoru;
- blokirati `computer_click_element` u tom prozoru;
- blokirati `computer_press_key` u tom prozoru, osim minimalnih eksplicitno dozvoljenih recovery tipki ako su zaista potrebne;
- blokirati obični `computer_type_text`;
- dozvoliti samo interno postavljanje polja `To`, `CC`, `BCC`, `Subject` i `Body` preko potvrđenih UIA elemenata;
- lock mora biti vezan za PID, HWND i identitet compose prozora;
- lock može ukloniti završetak/otkazivanje workflowa ili korisnik, ali ne model.

Korisnikov fizički miš i tastatura ostaju neblokirani, pa korisnik može ručno poslati email.

Bez ovakvog capability locka dokumentacija ne smije tvrditi da agent „ne može poslati email"; može samo tvrditi da namjenski draft tool ne sadrži Send korak.

---

### 4.3 KRITIČNO — TOCTOU i promjena fokusa tokom višekoračnog workflowa

Active-window provjera se trenutno radi jednom prije cijelog handlera. Email workflow traje dovoljno dugo da korisnik, notifikacija ili drugi proces preuzmu fokus između koraka.

#### Preporuka

Prije svakog write koraka provjeriti:

- da je originalni proces još živ;
- da je HWND isti;
- da prozor i dalje predstavlja compose draft;
- da je ciljano polje potomak tog prozora;
- da je control type očekivan;
- da postoji tačno jedan kandidat;
- da cancellation nije zatražen;
- da deadline nije istekao.

Ako bilo koja provjera ne uspije, workflow mora stati bez fallbacka na globalni keyboard input.

---

### 4.4 VISOKO — plaintext čuvanje email sadržaja u confirmation bazi

Action log redigira `body`, ali confirmation sistem čuva puni `payload` u SQLite. Ako payload sadrži `to`, `cc`, `bcc`, `subject` i `body`, kompletan poslovni email ostaje trajno zapisan.

Primaoci i predmet trenutno nisu na listi osjetljivih action-log ključeva. Event timeline također može nenamjerno otkriti primaoca na ekranu ili u bazi.

#### Preporuka

Za MVP:

- držati puni draft u memoriji renderera ili kratkotrajnom backend draft storeu;
- koristiti nasumični `draft_id` sa TTL-om 2–5 minuta;
- vezati potvrdu za kanonski hash sadržaja;
- u trajni zapis upisati samo maskiranog primaoca, dužine, hash, mail klijent i status;
- redigovati ključeve `to`, `from`, `cc`, `bcc`, `recipient`, `email`, `subject` i njihove varijante;
- ne prikazivati BCC u activity timelineu;
- obrisati memorijski draft nakon uspjeha, greške, cancel-a ili TTL-a.

Ako je potreban recovery nakon restarta, koristiti enkripciju vezanu za Windows korisnika, npr. DPAPI, i definisati retention politiku. Plaintext SQLite nije dovoljan.

---

### 4.5 VISOKO — Confirmation UI trenutno koristi semantiku slanja

Postojeći `ConfirmationDialog` bira labelu `sendEmail` kada `action_name` sadrži `email` ili `mail`. Za draft-only funkciju to je opasno i zbunjujuće: korisnik može vjerovati da potvrđuje slanje ili, obrnuto, može nenamjerno odobriti nešto što misli da je samo preview.

#### Preporuka

Uvesti eksplicitni action kind ili specifično renderovanje za `email_prepare_draft`:

- naslov: „Priprema email drafta";
- primarno dugme: „Pripremi draft" ili „Ubaci u email";
- trajna poruka: „Ricky neće poslati email";
- poslije uspjeha: „Draft je popunjen. Pregledaj ga i pošalji ručno."

Ne koristiti heuristiku na osnovu substringa u `action_name` za sigurnosno važnu semantiku.

---

### 4.6 VISOKO — `Tab`/`Enter` navigacija i fallback `SendKeys`

Plan koristi `Tab` za prelazak između polja. Postojeći type handler novi red pretvara u Enter, a UIA set-text fallback koristi `SendKeys`.

#### Preporuka

- Svako polje pronaći i postaviti direktno preko `ValuePattern.SetValue()` ili drugog klijent-specifičnog sigurnog patterna.
- Ne koristiti Tab redoslijed kao ugovor UI-ja.
- Za body dozvoliti multiline vrijednost kao podatak, bez fizičkih Enter događaja.
- Ako UIA ValuePattern nije dostupan, vratiti `UNSUPPORTED_EMAIL_CLIENT_UI`; ne prelaziti automatski na globalni keyboard fallback.
- Ne koristiti clipboard za tijelo emaila; clipboard bi izložio osjetljivi sadržaj drugim aplikacijama i clipboard historyju.

---

### 4.7 VISOKO — Gmail/Chrome ne pripada prvom MVP-u

Predloženi Gmail tok otvara Chrome i odmah kuca URL, ali ne fokusira adresnu traku. Tekst može završiti na aktivnoj web stranici. Čak i uz `Ctrl+L`, provjera samo procesa `chrome.exe` nije dovoljna: aktivni tab može biti banka, password manager, admin konzola ili druga osjetljiva stranica.

#### Preporuka

Prva verzija treba podržati samo Outlook desktop. Gmail adapter treba biti zasebna kasnija faza koja pouzdano potvrđuje:

- browser profil/proces;
- aktivni origin `https://mail.google.com`;
- tačan compose dijalog;
- ciljane DOM/accessibility elemente;
- zabranu generic browser automationa dok je draft lock aktivan.

Otvaranje Gmail compose URL-a nije dovoljna sigurnosna provjera.

---

### 4.8 SREDNJE — pogrešno korištenje `external_content_seen`

Plan predlaže podizanje `external_content_seen` zato što email body može sadržati prompt injection. U trenutnoj arhitekturi taj flag znači da je agent pročitao nepouzdan eksterni sadržaj kroz reader tool i nakon toga želi djelovati.

Korisnički diktat je ulazni podatak, ne tool output. Samo njegovo kucanje ne treba automatski označiti kao prethodno pročitan eksterni sadržaj.

#### Preporuka

- Body tretirati kao neizvršivi podatak.
- Ne spajati body u system prompt ili instrukcije.
- Ne interpretirati naredbe unutar bodyja.
- Ne vraćati puni body modelu kroz tool result.
- `external_content_seen` podići samo kada je runtime zaista pročitao screen/web/UI sadržaj.
- Ako se email tekst generiše iz nepouzdanog dokumenta ili web stranice, tada zadržati eskalaciju i posebno označiti izvor u previewu.

---

### 4.9 SREDNJE — globalni `Submit`/`Confirm` block bi kvario druge tokove

Globalno blokiranje svih elemenata nazvanih `Submit`, `Confirm` ili `Potvrdi` nije email-specifična zaštita. Onemogućilo bi legitimne potvrde u drugim aplikacijama, a substring `send` može pogoditi `Resend code` i druge nepovezane kontrole.

#### Preporuka

Blokade moraju biti kontekstualne: aktivni email draft lock + potvrđeni compose prozor + identitet kontrole. Opšti prompt može spominjati rizične radnje, ali backend policy ne treba koristiti globalne prevodilačke substring liste kao primarnu odluku.

---

### 4.10 SREDNJE — adresa primaoca zahtijeva poseban integritet

Glasovno prepoznata adresa može biti pogrešna, a Unicode znakovi i vizuelno slični domeni mogu zavarati korisnika. Outlook može tekst pretvoriti u contact chip koji prikazuje display name umjesto stvarne adrese.

#### Preporuka

- U MVP-u korisnik ručno unosi ili potvrđuje adresu u panelu.
- Ne rezolvirati „šefu", „Marku" ili sličan alias iz kontakata u prvoj verziji.
- Validirati dužinu i osnovnu strukturu adrese, ali ne tvrditi da regex potvrđuje postojanje mailboxa.
- Normalizovati i prikazati stvarni domain; upozoriti na non-ASCII/punycode domene.
- Nakon unosa preko UIA pročitati rezolviranu vrijednost/chip i uporediti je sa potvrđenim primaocem.
- Ako Outlook promijeni adresu ili je ne može rezolvirati, workflow stati i tražiti ručni pregled.
- Za pristupačnost omogućiti glasovno slovkanje adrese i readback prije odobrenja, ali potvrda mora ostati eksplicitna korisnička radnja.

---

### 4.11 SREDNJE — više prozora i više Outlook varijanti

Classic Outlook i New Outlook imaju različite procese, window class vrijednosti i accessibility strukturu. Izbor prvog UIA prozora koji odgovara djelimičnom nazivu nije siguran, posebno kada je otvoreno više draftova.

#### Preporuka

- Prije implementacije izabrati jednu podržanu varijantu i verziju.
- Napraviti adapter po klijentu/verziji.
- Kreirani compose prozor identifikovati novim HWND-om/PID-om nakon početne akcije.
- Ako postoji više kandidata, fail closed umjesto `windows[0]`.
- Ne koristiti lokalizovani naslov prozora kao jedini identitet.

---

### 4.12 SREDNJE — timeout, retry i cancellation moraju biti eksplicitni

Fiksni `sleep(1.0)` i „max 2 retry" nisu dovoljni. Sporo pokretanje i promjena fokusa mogu izazvati djelimično popunjen draft, a pozadinski handler ne smije nastaviti tipkati nakon što UI prijavi timeout.

#### Preporuka

- Koristiti polling za očekivani UIA uslov sa kratkim intervalom.
- Svaki korak ima deadline i cancellation check.
- Ne raditi automatski retry write koraka ako se ne zna da li je prethodni upis izvršen.
- Retry otvaranja klijenta može biti dozvoljen prije prvog write koraka.
- Nakon početka upisa, greška treba ostaviti draft vidljiv, prijaviti koja su polja potvrđeno popunjena i zahtijevati novu korisničku odluku.
- Stop/kill-switch mora prekinuti prije sljedećeg write koraka.

---

## 5. Preporučena ciljna arhitektura

```text
React Email Draft Panel
  - lokalni editable draft
  - eksplicitni preview/readback
  - korisnik bira „Pripremi draft"
              |
              v
ConfirmationService
  - jednokratna potvrda
  - vezana za email_prepare_draft + kanonski hash
  - kratki TTL
              |
              v
window.ricky.executeTool(...)
              |
              v
Electron tools:execute bridge
  - bez email poslovne logike
              |
              v
Python ToolExecutor
  - schema validation
  - Computer Mode
  - confirmation
  - cancellation
  - action receipt
              |
              v
EmailDraftPolicy + OutlookDraftAdapter
  - acquire draft lock
  - otvori podržani Outlook
  - identifikuje novi compose HWND/PID
  - setuje samo dozvoljena polja
  - provjerava identitet prije svakog write koraka
  - potvrđuje upisane vrijednosti
  - nikad ne pristupa Send kontroli
  - release/retain lock po jasno definisanom pravilu
              |
              v
Draft ostaje otvoren
  - agentove generičke akcije u tom prozoru blokirane
  - korisnik ručno pregleda i šalje
```

### 5.1 Predloženi naziv i ugovor toola

Koristiti naziv `email_prepare_draft`, ne `email_compose`, jer naziv jasnije pokazuje da nema slanja.

Primjer konceptualnog ugovora:

```python
ToolDefinition(
    name="email_prepare_draft",
    risk="high",
    requires_confirmation=True,
    requires_computer_mode=True,
    allowed_in_background=False,
    logs_action_receipt=True,
    implemented_by="python",
)
```

Ne preporučuje se samo dodavanje polja `forbidden_ui_actions` u `ToolDefinition`. Deklarativno polje nema sigurnosnu vrijednost dok ga centralni policy stvarno ne sprovodi nad svim relevantnim toolovima. Bolje je uvesti eksplicitnu `EmailDraftPolicy` komponentu sa testiranim pravilima.

### 5.2 Interni adapter umjesto pozivanja javnih handlera

`OutlookDraftAdapter` treba nuditi uske operacije:

```text
open_supported_client()
create_compose_window()
identify_compose_window()
set_recipient_field()
set_subject_field()
set_body_field()
verify_draft_values()
```

Adapter ne treba nuditi generički `click(x, y)`, `press_key(key)` ili `invoke(element)` API.

### 5.3 Model ne treba orkestrirati pojedinačne UI korake

Model treba odlučiti samo da zatraži `email_prepare_draft` sa već potvrđenim sadržajem. Deterministički backend workflow treba orkestrirati UIA korake. Time prompt injection ili modelova greška ne mogu promijeniti redoslijed i dodati Send akciju.

---

## 6. Privatnost i upravljanje podacima

### 6.1 Podaci koje treba smatrati osjetljivim

- `to`, `cc`, `bcc`;
- display name i stvarna adresa;
- subject;
- body;
- diktat/transkript;
- naziv firme ili kontakta izveden iz adrese;
- account/profile identitet;
- eventualni draft ID koji omogućava dohvat sadržaja.

### 6.2 Gdje sadržaj ne smije završiti

- plaintext action log;
- trajni confirmation payload bez enkripcije;
- activity timeline detalji;
- console/debug log;
- exception poruke;
- clipboard i clipboard history;
- telemetry;
- tool result vraćen modelu;
- screenshot galerija nastala automatski tokom compose toka.

### 6.3 Minimalni action receipt

Siguran receipt može sadržati:

```json
{
  "action": "email_draft_prepared",
  "mail_client": "outlook_classic",
  "recipient_count": 1,
  "subject_length": 12,
  "body_length": 142,
  "draft_hash_prefix": "8f42...",
  "sent": false
}
```

Ne treba sadržati puni body ni stvarne adrese.

---

## 7. Pristupačnost i voice-first sigurnost

Ova funkcija može biti naročito korisna slijepim i slabovidim osobama, ali vizuelni preview sam po sebi nije dovoljan.

Obavezno uključiti:

- screen-reader ispravan dijalog sa fokus trapom i jasnim naslovom;
- glasovni readback primaoca i predmeta;
- opciju slovkanja adrese znak po znak;
- upozorenje kada domen sadrži Unicode/punycode ili nije ranije korišten;
- jasnu razliku između „pripremi draft" i „pošalji";
- zvučnu potvrdu da je draft spreman, ali nije poslan;
- tipku/glasovnu naredbu za otkazivanje koja ne može biti zamijenjena potvrdom;
- zabranu da sama voice naredba „pošalji" aktivira Send ili automatski potvrdi draft;
- readback rezolvirane Outlook adrese nakon što klijent napravi contact chip;
- obavještenje ako su CC ili BCC popunjeni.

Za high-risk potvrdu korisnička namjera treba biti svježa i eksplicitna. Ranije izgovorena rečenica ne smije se tretirati kao trajno odobrenje.

---

## 8. Efikasan implementacioni redoslijed

### Faza A — tehnički spike, bez glasa

- Samo podržana varijanta Outlook desktopa.
- Ručni unos To/Subject/Body u aplikacijskom panelu.
- Ispitati stabilne UIA identifikatore.
- Napraviti `OutlookDraftAdapter`.
- Bez koordinatnih klikova, Tab navigacije i keyboard fallbacka.
- Ne spajati još kompletan confirmation i voice UX dok se ne dokaže pouzdano targetiranje.

### Faza B — capability lock i sigurnosna state machine

- Uvesti email draft session/lock vezan za PID + HWND.
- Blokirati generičke akcione toolove u zaključanom compose prozoru.
- Dodati per-step focus/identity/cancellation/deadline provjere.
- Definisati ponašanje kod djelimičnog uspjeha.
- Dodati kill-switch testove.

### Faza C — confirmation i privatnost

- Registrovati `email_prepare_draft` kroz `ToolExecutor`.
- Vezati jednokratnu potvrdu za tačan hash.
- Ispraviti ConfirmationDialog semantiku.
- Uvesti kratkotrajni draft store ili drugi način da osjetljiv payload ne ostane u plaintext bazi.
- Proširiti redaction i event privacy.

### Faza D — voice-first UI

- Dodati stanje/panel za email diktat tek nakon stabilnog backend workflowa.
- Glas popunjava lokalni panel, ne Outlook direktno.
- Adresa se eksplicitno potvrđuje.
- Dodati screen-reader i spoken readback tok.

### Faza E — drugi klijenti

- New Outlook kao poseban adapter ako je Classic Outlook bio MVP, ili obrnuto.
- Gmail/Chrome tek kao zaseban threat model i adapter.
- Ne uvoditi `default` klijent dok nema dokazano siguran adapter.

---

## 9. Obavezni testovi prije uključivanja funkcije

### 9.1 Permission i confirmation

1. Bez Computer Mode: `COMPUTER_MODE_REQUIRED`.
2. Bez potvrde: `CONFIRMATION_REQUIRED`.
3. Potvrda za drugi tool: `CONFIRMATION_MISMATCH`.
4. Promjena jednog znaka u primaocu, predmetu ili bodyju invalidira potvrdu.
5. Ista potvrda se ne može ponovo koristiti.
6. Neuspjeli handler ne vraća potrošenu potvrdu u approved stanje.
7. Istekli draft/confirmation se ne može izvršiti.

### 9.2 Window i UIA integritet

8. Promjena fokusa između bilo koja dva koraka prekida workflow.
9. Promjena HWND-a/PID-a prekida workflow.
10. Dva compose prozora izazivaju fail-closed, ne izbor prvog kandidata.
11. Polje koje nije potomak potvrđenog compose prozora ne može biti cilj.
12. Nepoznati Outlook UI layout vraća `UNSUPPORTED_EMAIL_CLIENT_UI`.
13. Nedostupan ValuePattern ne prelazi na globalni keyboard input.

### 9.3 Send zabrana

14. `computer_click` je blokiran u zaključanom compose prozoru.
15. `computer_click_element` je blokiran u zaključanom compose prozoru.
16. `Enter`, `Space` i svi modifier shortcuti su blokirani za agenta u tom prozoru.
17. Element bez imena, ali sa InvokePatternom, ne može biti aktiviran.
18. Send dugme na drugom jeziku ne zavisi od prevodilačke pattern liste.
19. Korisnikov fizički klik na Send ostaje moguć.
20. Model ne dobija javni tool kojim može ukloniti draft lock.

### 9.4 Sadržaj i privatnost

21. Body sa `\n`, `\t`, `Ctrl+Enter`, „klikni Send" i prompt-injection tekstom ostaje samo podatak.
22. Tool result ne vraća body modelu.
23. Action log ne sadrži body, To, CC, BCC ni subject.
24. Confirmation DB ne čuva puni plaintext draft.
25. Activity timeline ne otkriva BCC ili kompletnu adresu.
26. Clipboard ostaje nepromijenjen.
27. Memorijski draft se briše nakon uspjeha, cancel-a, greške i TTL-a.

### 9.5 Cancellation i greške

28. Stop prije prvog write koraka ostavlja compose prozor netaknutim.
29. Stop između polja sprečava sljedeći write korak.
30. Timeout ne ostavlja pozadinski worker koji nastavlja kucati.
31. Backend nedostupan ne pokreće legacy fallback za draft workflow.
32. Djelimično popunjen draft se prijavljuje tačno, bez lažnog `ok=true`.
33. Automatski retry ne duplira primaoca, subject ili body.

### 9.6 Pristupačnost

34. Screen reader čita stvarnu akciju „Pripremi draft".
35. Fokus ne može pobjeći iz confirmation dijaloga.
36. Primaoci se mogu pročitati i slovkati prije potvrde.
37. Nakon izvršenja korisnik čuje da poruka nije poslana.
38. Glasovna riječ „pošalji" sama ne potvrđuje niti šalje email.

---

## 10. Acceptance kriteriji za sigurni MVP

Funkcija se može smatrati spremnom za ograničeni MVP tek kada važi sve sljedeće:

- podržan je tačno naveden Outlook klijent/verzija;
- workflow prolazi kroz `ToolExecutor`;
- nema posebnog paralelnog execution endpointa;
- nema koordinatnih klikova, Tab navigacije ni keyboard fallbacka;
- compose prozor je vezan za PID + HWND;
- identitet prozora i elementa provjerava se prije svakog write koraka;
- draft capability lock blokira sve agentove alternativne Send puteve u tom prozoru;
- confirmation je jednokratna i vezana za hash tačnog drafta;
- confirmation UI govori „Pripremi draft", ne „Pošalji";
- osjetljiv sadržaj nije trajno sačuvan u plaintext audit/confirmation/event podacima;
- cancellation i stvarni deadline rade između koraka;
- svi negativni testovi iz prethodne sekcije prolaze;
- korisnik je ručno testirao stvaran Outlook UI i pristupačnost;
- dokumentacija kaže tačno šta je tehnički garantovano, bez preširoke tvrdnje.

---

## 11. Šta ne treba raditi u prvoj verziji

- Ne podržavati „default mail client" bez poznatog adaptera.
- Ne podržavati Gmail/Chrome u istom adapteru kao Outlook.
- Ne proširivati generički `computer_press_key` opasnim modifier kombinacijama radi emaila.
- Ne dozvoliti modelu da orkestrira pojedinačne UI korake.
- Ne koristiti koordinatne klikove.
- Ne koristiti clipboard za body.
- Ne čuvati body/recipient/subject u plaintext SQLite payload-u.
- Ne uvoditi kontakt rezoluciju iz izraza poput „šefu".
- Ne dodavati attachmente.
- Ne čitati inbox ili sadržaj postojećih poruka.
- Ne nazivati korisničku potvrdu „Pošalji email".
- Ne smatrati system prompt ili listu lokalizovanih Send naziva tehničkom garancijom.

---

## 12. Konačna preporuka

Plan treba revidirati prije implementacije, ne odbaciti. Najsigurniji i najefikasniji prvi korak je mali Outlook-only spike koji dokazuje stabilno UIA targetiranje bez generičkih click/key primitive. Nakon toga treba implementirati capability lock i privatnost draft podataka, pa tek onda confirmation i voice UI.

Ključna sigurnosna odluka glasi:

> Agent ne treba dobiti generičke računarske sposobnosti unutar email compose prozora. Treba dobiti samo usku sposobnost da postavi unaprijed definisana draft polja, dok slanje ostaje izvan njegovog capability seta.

Tek takva arhitektura omogućava vjerodostojnu tvrdnju da namjenski agent workflow priprema draft, ali ne može poslati email.
