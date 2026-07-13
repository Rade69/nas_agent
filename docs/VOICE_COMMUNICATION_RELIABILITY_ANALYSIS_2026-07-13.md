# Analiza pouzdanosti glasovne komunikacije

**Projekat:** RileyJarvis Windows Hybrid (Naš-agent)
**Datum:** 13. jul 2026.
**Status:** tehnička analiza i preporuka; kod nije mijenjan
**Obuhvat:** korisnik → mikrofon → OpenAI Realtime → agent → alati → glasovni odgovor

## 1. Izvršni sažetak

Postojeći izbor tehnologije je u osnovi dobar:

- Electron/React renderer koristi WebRTC za direktan, niskolatentni audio tok;
- Python backend čuva standardni OpenAI API ključ i izdaje kratkotrajni Realtime credential;
- Python ostaje vlasnik lokalnih alata, sigurnosnih pravila i poslovne logike;
- Electron povezuje UI, WebRTC i Python tool bridge.

Nestabilnost ne zahtijeva zamjenu WebRTC-a Python WebSocket audio cjevovodom. Glavni problem je što je sadašnji `RickyRealtimeClient` funkcionalan prototip, ali nema dovoljno robustan lifecycle za produkcijsku glasovnu sesiju.

Najvažniji potvrđeni nedostaci su:

1. prekid WebRTC/DataChannel veze nakon povezivanja se ne prati;
2. dva paralelna `connect()` poziva mogu otvoriti dvije sesije;
3. greška se odmah prepiše stanjem `idle`;
4. izuzetak tokom izvršavanja alata može ostaviti `toolRunning=true` i zaustaviti razgovor;
5. serverski događaji se obrađuju konkurentno bez reda;
6. važne DataChannel poruke mogu biti tiho odbačene;
7. SDP povezivanje nema timeout niti `AbortController`;
8. automatski reconnect ne postoji;
9. nema ozbiljne ulazne audio dijagnostike;
10. postojeći testovi ne pokrivaju stvarni WebRTC lifecycle.

Najbolje rješenje je **kontrolisan reliability refactor postojećeg klijenta**, a ne veliki rewrite i ne promjena cijele arhitekture.

## 2. Pregledana implementacija

Ključni moduli:

- [`src/lib/realtime.ts`](../src/lib/realtime.ts) — WebRTC sesija, mikrofon, DataChannel, događaji i tool loop;
- [`src/lib/realtimeEventRouter.ts`](../src/lib/realtimeEventRouter.ts) — mapiranje Realtime događaja na UI voice state;
- [`src/lib/realtimeEventHelpers.ts`](../src/lib/realtimeEventHelpers.ts) — parsiranje i sanitizacija događaja;
- [`src/lib/realtimeTypes.ts`](../src/lib/realtimeTypes.ts) — tipovi klijenta i događaja;
- [`src/App.tsx`](../src/App.tsx) — lifecycle klijenta, stanje UI-a, diktiranje i potvrde;
- [`electron/ipc_handlers/realtime.cjs`](../electron/ipc_handlers/realtime.cjs) — Realtime session konfiguracija i prompt;
- [`electron/services/pythonClient.cjs`](../electron/services/pythonClient.cjs) — poziv Python endpointa;
- [`python_backend/app/api/realtime.py`](../python_backend/app/api/realtime.py) — izdavanje Realtime credentiala;
- [`python_backend/app/schemas/realtime.py`](../python_backend/app/schemas/realtime.py) — API schema;
- [`python_backend/tests/test_realtime.py`](../python_backend/tests/test_realtime.py) — testovi token endpointa.

## 3. Trenutni tok

```text
Korisnik govori
      |
      v
navigator.mediaDevices.getUserMedia
      |
      v
RTCPeerConnection ──────────────── OpenAI Realtime
      |                                  |
      | remote audio                     | server events
      v                                  v
HTMLAudioElement                  RTCDataChannel
                                         |
                                         v
                               RickyRealtimeClient
                                  |            |
                                  |            v
                                  |     React stanje/transkript
                                  v
                         Electron executeTool IPC
                                  |
                                  v
                         Python tools i sigurnost
                                  |
                                  v
                     function_call_output + response.create
                                  |
                                  v
                         OpenAI glasovni odgovor
```

Audio ne prolazi kroz Python backend. To je dobro za latenciju i smanjuje količinu audio logike koju aplikacija mora sama održavati.

## 4. Metod i granice zaključaka

Nalazi su podijeljeni na:

- **potvrđeno u kodu** — ponašanje je direktno vidljivo u implementaciji;
- **vjerovatna posljedica** — tehnički slijedi iz implementacije, ali nije reproducirana sa stvarnim mikrofonom;
- **hipoteza za mjerenje** — mogući uzrok čija važnost zavisi od uređaja, mreže, jezika ili korisničkog okruženja.

U ovom pregledu nije izvršen pravi razgovor preko mikrofona. Zato se ne tvrdi da je svaki nedostatak već izazvao korisnikov konkretan simptom. Dovoljno je, međutim, potvrđenih lifecycle rupa da se nestabilnost ne može pripisati samo mreži ili OpenAI servisu.

## 5. Nalazi po prioritetu

### P0-1 — prekid veze nakon povezivanja nije detektovan

**Status:** potvrđeno u kodu
**Rizik:** visok

Klijent prati:

- DataChannel `open`;
- DataChannel `message`;
- WebRTC `ontrack`.

Ne prati:

- `RTCPeerConnection.connectionstatechange`;
- `RTCPeerConnection.iceconnectionstatechange`;
- DataChannel `close`;
- DataChannel `error`;
- `MediaStreamTrack.ended`;
- promjenu ili uklanjanje audio uređaja;
- browser/Electron `online` i `offline` događaje.

Ako se mreža prekine, ICE transport otkaže ili DataChannel zatvori, UI može ostati u stanju `connected`. Korisnik govori, ali nema odgovora ni jasne greške.

**Preporuka:** jedan transport handler treba mapirati sva stanja u kontrolisanu session state mašinu. `failed`, `closed` i dugotrajno `disconnected` stanje moraju pokrenuti cleanup, obavijest i po potrebi reconnect.

### P0-2 — moguća su paralelna povezivanja

**Status:** potvrđeno u kodu
**Rizik:** visok

`connect()` sprečava novi poziv samo kada `this.pc` već postoji. `this.pc` se postavlja tek nakon tokena, mikrofona, SDP POST-a i remote descriptiona.

Tok greške:

```text
connect A: this.pc == null → nastavlja
connect B: this.pc == null → nastavlja
connect A: otvara mikrofon i sesiju
connect B: otvara drugi mikrofon i sesiju
zadnji završeni poziv prepisuje this.pc / this.dc
druga sesija može ostati živa i bez vlasnika
```

Izvori paralelnog poziva mogu biti glavno dugme, top bar, companion orb ili dupli klik.

**Preporuka:** čuvati `connectPromise`, postaviti session generation ID prije prvog `await` i odbiti/vratiti postojeći Promise dok je stanje `connecting`.

### P0-3 — greška se odmah prepisuje stanjem `idle`

**Status:** potvrđeno u kodu
**Rizik:** srednje-visok

`catch` postavlja connection, mood i voice state na `error`, a zatim poziva `disconnect()`, koji ih odmah postavlja na `idle`.

To korisniku skriva uzrok problema i otežava podršku.

**Preporuka:** odvojiti:

- `cleanupResources()` — samo zatvara tehničke resurse;
- `disconnect(reason)` — određuje završno stanje;
- `fail(error)` — čuva `failed` stanje i tipizirani razlog dok korisnik ne pokuša ponovo.

### P0-4 — tool exception može zamrznuti razgovor

**Status:** potvrđeno u kodu
**Rizik:** kritičan

`executeFunctionCalls()` postavlja `toolRunning=true`, ali cijela metoda nije zaštićena `try/catch/finally` blokom.

Promise može biti odbačen u:

- `window.ricky.executeTool()`;
- pripremi thumbnaila;
- `createConfirmation()`;
- slanju tool outputa;
- IPC ili Python grešci.

Posljedice:

- `toolRunning` ostaje `true`;
- model ne dobije `function_call_output`;
- UI može ostati u `thinking`/`working` stanju;
- naredni `response.done` više ne vraća stanje u idle;
- korisniku izgleda kao da je glasovna komunikacija stala.

**Preporuka:** svaki function call mora završiti jednim od dva ishoda:

```text
uspješan function_call_output
kontrolisan error function_call_output
```

Cleanup i `toolRunning=false` moraju biti u `finally`. Tool timeout treba postojati u backendu i na renderer/IPC granici.

### P0-5 — obrada događaja nije serijalizovana

**Status:** potvrđeno u kodu
**Rizik:** visok

DataChannel handler pokreće asinhroni `handleServerEvent()` bez čekanja. Više događaja može istovremeno mijenjati:

- `currentAssistantText`;
- `toolRunning`;
- voice state;
- response lifecycle;
- transkript;
- confirmation state.

Posebno su rizični paralelni `response.done`, više function callova i novi korisnički turn dok prethodni alat traje.

**Preporuka:** događaje staviti u jednostavan Promise queue. Audio vizuelne delta događaje je moguće tretirati odvojeno, ali state-changing događaji moraju imati determinističan red.

### P0-6 — stale događaji stare sesije nisu odbačeni

**Status:** potvrđeno kao nedostatak zaštite
**Rizik:** visok

Nema session generation ID-a. Nakon disconnect/reconnecta zakašnjeli callback stare sesije može ažurirati stanje nove sesije.

**Preporuka:** svaki connect dobija monoton `generation`. Svi event handleri prvo provjeravaju da li pripadaju aktivnoj generaciji. Cleanup uklanja handlere prije zatvaranja objekata.

### P0-7 — važne poruke mogu biti tiho izgubljene

**Status:** potvrđeno u kodu
**Rizik:** visok

`sendEvent()` šalje samo ako je DataChannel `open`. U suprotnom ne vraća grešku i ne obavještava pozivaoca.

Mogu biti izgubljeni:

- `session.update`;
- prelazak u/iz dictation modea;
- `response.create`;
- `function_call_output`;
- buduće cancel/clear poruke.

**Preporuka:** `sendEvent()` mora:

1. validirati aktivnu sesiju;
2. dodati `event_id` za važne događaje;
3. vratiti uspjeh ili baciti tipiziranu grešku;
4. po potrebi redati dozvoljene poruke dok se kanal otvara;
5. nikada automatski ponavljati ne-idempotentnu poruku bez provjere.

### P0-8 — SDP povezivanje nema timeout

**Status:** potvrđeno u kodu
**Rizik:** visok

Python token endpoint koristi `httpx` timeout od 15 sekundi. Rendererov SDP `fetch` nema `AbortController` niti ukupni connect deadline.

**Preporuka:** zajednički connect deadline od približno 15–20 sekundi treba obuhvatiti token, mikrofon i SDP razmjenu. Timeout mora zatvoriti lokalni `pc`, zaustaviti mic track i invalidirati generaciju.

### P0-9 — djelimično kreirani resursi nisu centralizovano očišćeni

**Status:** potvrđeno u kodu
**Rizik:** srednje-visok

`RTCPeerConnection` se prvo čuva u lokalnoj varijabli, a u `this.pc` tek na kraju. Ako povezivanje padne prije toga, standardni `disconnect()` nema referencu na lokalni peer radi zatvaranja.

Mic stream se ranije upisuje u polje i uglavnom može biti zaustavljen, ali cleanup zavisi od tačke pada.

**Preporuka:** kreirane resurse odmah vezati za session scope i imati idempotentan cleanup koji radi u svakoj fazi povezivanja.

### P0-10 — nema kontrolisanog reconnecta

**Status:** potvrđeno u kodu
**Rizik:** visok

Privremeni mrežni prekid zahtijeva ručno gašenje i ponovno uključivanje glasa.

**Preporuka:** maksimalno tri automatska pokušaja sa jitterom, na primjer:

```text
0,5 s → 1,5 s → 4 s
```

Reconnect se ne pokreće nakon:

- korisničkog Stop-a;
- kill-switcha;
- idle timeouta;
- odbijene mic dozvole;
- fatalne autentikacijske ili konfiguracijske greške.

Svaki reconnect mora koristiti novi ephemeral credential.

## 6. Voice Activity Detection

Trenutna konfiguracija koristi:

```json
{
  "type": "semantic_vad",
  "eagerness": "medium",
  "create_response": true,
  "interrupt_response": true
}
```

Semantic VAD pokušava značenjski utvrditi kada je korisnik završio. `medium` je razuman početni kompromis, ali jedna vrijednost neće biti optimalna za:

- brz i spor govor;
- srpski i druge jezike;
- bučne i tihe prostorije;
- diktiranje i razgovor;
- ugrađeni laptop mikrofon i headset.

Mogući simptomi loše podešenog VAD-a:

- agent odgovara prije kraja rečenice;
- agent dugo ne reaguje;
- pozadinski govor prekida odgovor;
- kratke potvrde poput „da“ nisu prepoznate;
- diktat se dijeli u neprirodne segmente.

### Preporučeni profili

| Profil | Preporuka | Namjena |
|---|---|---|
| Prirodni razgovor | Semantic VAD `medium` | početni standard |
| Sporiji govor | Semantic VAD `low` | duže pauze i pristupačnost |
| Brze komande | Semantic VAD `high` | kratke, jasne naredbe |
| Bučno okruženje | testirati Server VAD | kontrola thresholda i tišine |
| Pouzdani fallback | push-to-talk | korisnik određuje granicu turna |

Push-to-talk nije korak unazad. Kao opcionalni fallback uklanja veliki dio VAD neizvjesnosti i posebno je koristan za dijagnostiku: ako push-to-talk radi stabilno, a hands-free ne radi, problem je vjerovatno u VAD-u ili akustici, ne u cijelom transportu.

## 7. Prekidi korisnika dok agent govori

WebRTC Realtime sa uključenim VAD-om podržava prekid odgovora. Server kod WebRTC-a upravlja output audio bufferom i automatski skraćuje neodsvirani dio.

Lokalna aplikacija ipak mora pravilno obraditi:

- `input_audio_buffer.speech_started`;
- `response.cancelled`;
- povratak iz `speaking` u `listening`;
- prekid lokalne animacije;
- razliku između glasovnog prekida i otkazivanja lokalnog alata.

Glasovni prekid ne smije automatski otkazati rizičan ili djelimično izvršen lokalni alat bez zasebne politike. Razgovor i tool execution imaju različite lifecycle granice.

## 8. Transkripcija i srpski jezik

Glavni razgovor koristi Realtime audio model, dok se korisnički transkript dodatno dobija preko `whisper-1` sa jezičkim hintom `sr`.

Poznati lokalni problemi već su zahtijevali:

- transliteraciju povremene ćirilice u latinicu;
- jezički hint radi smanjenja pogrešne detekcije;
- posebnu logiku za ulazak i izlazak iz diktiranja.

Aktuelna OpenAI dokumentacija predstavlja `gpt-realtime-whisper` kao model namijenjen najnižoj latenciji streaming transkripcije, dok `whisper-1` ostaje za postojeće integracije i nije nativno streaming rješenje na isti način.

To nije dovoljan razlog za direktnu zamjenu u produkciji. Potreban je spike koji testira:

- podršku unutar conversational Realtime sesije;
- kompatibilnost sa odabranim VAD režimom;
- srpsku latinicu i ćirilicu;
- bosanske/hrvatske varijante govora;
- engleske tehničke termine unutar srpske rečenice;
- imena, brojeve, e-mail adrese i putanje;
- prazne, zakašnjele i odrezane transkripte.

### Redoslijed transkripata

Završni transkripcijski događaji različitih turnova ne moraju stići redom. Aplikacija trenutno ne modeluje dovoljno `item_id` podatke da bi ih pouzdano povezala.

Potrebno je čuvati:

- `item_id`;
- `content_index`;
- vrijeme speech start/stop;
- status partial/final;
- session generation.

## 9. Audio ulaz i izlaz

### 9.1. Ulazni mikrofon

Trenutno se traže:

```json
{
  "echoCancellation": true,
  "noiseSuppression": true,
  "autoGainControl": true
}
```

To su razumne početne vrijednosti, ali različiti Windows drajveri i headset uređaji ih ne implementiraju jednako. Nema izbora uređaja niti provjere stvarno primijenjenih postavki.

Treba dodati:

- izbor aktivnog input uređaja;
- prikaz mic levela prije povezivanja i tokom sesije;
- detekciju dugotrajne potpune tišine;
- `track.muted`, `unmuted` i `ended` handlere;
- reakciju na `navigator.mediaDevices.devicechange`;
- prikaz dozvole i korisnički razumljive greške;
- test opciju za AEC/noise suppression/AGC, ne globalno isključivanje naslijepo.

### 9.2. Izlazni audio

Audio element se kreira programski i koristi `autoplay`. Potrebno je provjeriti:

- da li je `audio.play()` uspio kada Electron politika ili OS blokiraju autoplay;
- da li je element zadržan kao eksplicitno polje session managera;
- `playing`, `pause`, `ended`, `error` i `stalled` događaje;
- aktivni Windows output uređaj;
- da li je zvuk utišan ili je volumen nula;
- da li output track završava bez DataChannel zatvaranja.

Bez tih podataka slučaj „agent odgovara u transkriptu, ali se ništa ne čuje“ izgleda isto kao model koji nije odgovorio.

## 10. UI i state model

Trenutna connection stanja su:

```text
idle | connecting | connected | error
```

Za pouzdan lifecycle preporučuju se:

```text
idle
requesting_permission
minting_token
negotiating
connected
reconnecting
disconnecting
failed
```

Voice state i connection state moraju ostati odvojeni:

```text
connection: connected
voice: listening | transcribing | thinking | speaking | waiting_confirmation
```

UI treba moći reći:

- „Mikrofon nema dozvolu.“
- „Mikrofon je povezan, ali ne registrujem zvuk.“
- „Veza je prekinuta; pokušavam ponovo 2/3.“
- „Agent je čuo govor i obrađuje ga.“
- „Alat traje duže nego obično.“
- „Glasovni odgovor je stigao, ali reprodukcija nije počela.“

Generičko `idle` stanje nije dovoljno za podršku i samostalni oporavak korisnika.

## 11. Preporučena state mašina

```text
                 korisnik pokreće glas
                           |
                           v
                         idle
                           |
                           v
              requesting_permission
                           |
                           v
                    minting_token
                           |
                           v
                     negotiating
                    /          \
                   v            v
              connected       failed
              /   |   \           |
             /    |    \          | retry
            v     v     v         |
      listening thinking speaking  |
             \    |    /           |
              \   |   /            |
               connected <----------
                   |
          transport privremeno pada
                   |
                   v
              reconnecting
              /          \
             v            v
        connected        failed
```

Sve tranzicije treba centralizovati. Pojedinačni event handleri ne bi smjeli nezavisno postavljati proizvoljne kombinacije mooda, voice statea i connection statea.

## 12. Predloženi `RealtimeSessionManager`

Nije potreban framework niti veliki rewrite. Postojeći klijent se može postepeno preoblikovati tako da posjeduje:

```text
RealtimeSessionManager
  state
  generation
  connectPromise
  peerConnection
  dataChannel
  micStream
  audioElement
  connectAbortController
  reconnectPolicy
  eventQueue
  pendingEventsById
  activeResponseId
  activeToolCalls
  diagnosticsRingBuffer
```

Odgovornosti:

- tačno jedna aktivna ili povezujuća sesija;
- idempotentan cleanup;
- detekcija transportnog kvara;
- reconnect;
- odbacivanje stale događaja;
- serijalizacija state-changing događaja;
- garantovan završetak tool poziva;
- tipizirane greške;
- privatna dijagnostika bez sadržaja razgovora.

## 13. Reconnect politika

Reconnect treba biti ograničen i predvidiv.

### Pokušati reconnect

- ICE `failed`;
- DataChannel neočekivano `closed`;
- kratkotrajni gubitak mreže;
- remote transport prekinut bez korisničkog Stop-a.

### Ne pokušavati automatski

- `NotAllowedError` za mikrofon;
- neispravan ili nedostajući API ključ;
- konfiguracija/model nije podržan;
- korisnik je pritisnuo Stop;
- kill-switch;
- idle timeout;
- aplikacija se zatvara.

### Pravila

- novi ephemeral token po pokušaju;
- maksimalno tri pokušaja;
- exponential backoff sa jitterom;
- jasno vidljiv pokušaj u UI-u;
- bez automatskog ponavljanja posljednje rizične radnje;
- stari tool callovi se ne izvršavaju drugi put;
- korisnik može odustati tokom reconnecta.

## 14. Tool lifecycle

Glasovni razgovor je stabilan samo koliko i najsporiji tool bridge.

Za svaki `call_id` treba voditi stanje:

```text
received
validated
running
waiting_confirmation
completed
failed
cancelled
timed_out
```

Pravila:

- svaki call dobija tačno jedan završni `function_call_output`;
- više poziva iz istog `response.done` batcha se ne smiju izgubiti;
- `toolRunning` ne treba biti jedan globalni boolean ako više poziva može biti aktivno;
- timeout vraća kontrolisanu grešku modelu;
- exception se sanitizuje, ali se lokalno evidentira kod greške;
- voice interruption ne znači automatsko otkazivanje lokalnog alata;
- kill-switch mora otkazati i glas i backend izvršavanje;
- reconnect ne smije ponoviti alat bez idempotency odluke.

## 15. Privatna dijagnostika

Bez observabilityja nije moguće razlikovati mikrofon, VAD, mrežu, model, audio izlaz i tool problem.

Preporučuje se memorijski ring buffer, na primjer posljednjih 300 tehničkih događaja:

```text
timestamp
session generation
connection state
ICE state
DataChannel state
event type
event_id / response_id / item_id / call_id
trajanje faze
tipizirani error code
mic track state
input/output audio energy bucket
```

Ne bilježiti po početnim postavkama:

- audio;
- transkript;
- tool argumente;
- rezultat alata;
- API ključeve;
- osjetljive putanje ili sadržaj.

Korisnik može izvesti anonimizovani dijagnostički izvještaj. Debug log mora imati ograničenu veličinu i automatsko brisanje.

## 16. Metrike stabilnosti

Prije i poslije refactora treba mjeriti:

- uspješnost povezivanja;
- vrijeme od klika do `connected`;
- vrijeme od speech stop do prvog audio odgovora;
- procenat turnova bez odgovora;
- broj lažnih speech startova;
- broj prerano presječenih turnova;
- broj reconnecta po satu;
- uspješnost reconnecta;
- broj tool callova bez završnog outputa;
- broj DataChannel grešaka;
- broj praznih, zakašnjelih i odrezanih transkripata;
- broj output-audio odgovora koji nisu reprodukovani.

### Predloženi početni SLO za MVP

Vrijednosti treba potvrditi realnim testovima, ali početni cilj može biti:

- najmanje 99% lokalno pokrenutih connect pokušaja pravilno završi u `connected` ili jasnom `failed` stanju;
- nijedan connect ne ostaje beskonačno u `connecting`;
- nijedan tool call ne ostaje bez završnog outputa;
- neočekivani prekid se otkrije u nekoliko sekundi;
- najviše tri automatska reconnect pokušaja;
- Stop i kill-switch zaustave mic track odmah;
- nema duplih sesija nakon brzog višestrukog klika.

## 17. Test strategija

### 17.1. Jedinični testovi

- state machine tranzicije;
- klasifikacija grešaka na retryable/fatal;
- reconnect backoff;
- stale generation odbacivanje;
- event queue redoslijed;
- `sendEvent` zatvoren kanal;
- tool `try/catch/finally`;
- tačno jedan output po `call_id`;
- voice state mapiranje;
- transcript slaganje po `item_id`.

### 17.2. Integracioni testovi sa mock WebRTC objektima

- dvostruki `connect`;
- token timeout;
- SDP timeout;
- DataChannel close/error;
- ICE disconnected → recovered;
- ICE failed → reconnect;
- mic permission denied;
- mic track ended;
- audio autoplay rejection;
- događaj stare sesije nakon reconnecta;
- tool rejection i timeout;
- više function callova u jednom odgovoru;
- kill-switch tokom povezivanja i tokom alata.

### 17.3. Ručni audio matrix

Testirati najmanje:

- ugrađeni laptop mikrofon;
- USB mikrofon;
- Bluetooth headset;
- promjenu uređaja usred sesije;
- tiho i bučno okruženje;
- brzi i sporiji govor;
- srpski, code-switching i tehničke izraze;
- govor dok Ricky govori;
- 15, 30 i 60 minuta trajanja;
- kratki prekid interneta;
- sleep/wake računara;
- glavni i companion prozor.

### 17.4. VAD evaluacija

Napraviti reprezentativan skup snimaka/turnova i porediti:

- Semantic VAD low/medium/high;
- Server VAD sa nekoliko pragova;
- push-to-talk baseline.

Ne birati postavku samo po subjektivnom utisku iz nekoliko čistih rečenica.

## 18. Faze realizacije

### Faza 0 — instrumentacija prije promjene ponašanja

- session generation i tehnički ID-evi;
- connection/ICE/DC event logging bez sadržaja;
- mjerenje connect i turn latencije;
- mic/output health signal;
- anonimizovan debug export.

**Cilj:** prikupiti dokaz gdje se sesija prekida.

### Faza 1 — kritični lifecycle popravci

- single-flight connect;
- centralizovan cleanup;
- timeout i abort;
- connection/ICE/DC/track handleri;
- trajno `failed` stanje;
- stale-event zaštita;
- `executeFunctionCalls` try/catch/finally;
- pouzdan `sendEvent`.

**Cilj:** ukloniti silent failure i deadlock scenarije.

### Faza 2 — kontrolisan reconnect

- retry klasifikacija;
- maksimalno tri pokušaja;
- novi token;
- UI reconnect stanje;
- zaštita od ponavljanja alata.

**Cilj:** oporavak od kratkog mrežnog prekida bez korisničke intervencije.

### Faza 3 — audio UX i VAD

- mic selector i meter;
- output playback health;
- VAD profili;
- push-to-talk fallback;
- pristupačne glasovne i vizuelne statusne poruke.

### Faza 4 — model i transkripcija eksperimenti

- A/B `gpt-realtime-2` i aktuelnog 2.1 modela;
- spike za `gpt-realtime-whisper`;
- srpski eval skup;
- pinovanje provjerene verzije/snapshota kada je dostupno i opravdano.

Model se mijenja tek nakon lifecycle stabilizacije kako se dvije vrste promjene ne bi pomiješale.

## 19. Šta ne preporučujem

- Ne prebacivati audio kroz Python WebSocket samo zato što je postojeći klijent nestabilan.
- Ne uvoditi veliki voice framework prije popravke osnovnog lifecyclea.
- Ne pretpostaviti da će noviji model riješiti transport i state race probleme.
- Ne uvoditi beskonačni reconnect.
- Ne automatski ponavljati tool pozive nakon prekida.
- Ne logovati audio i transkript radi dijagnostike po početnim postavkama.
- Ne koristiti jedan globalni `toolRunning` boolean kao trajno rješenje za više poziva.
- Ne tretirati voice interruption kao isto što i kill-switch.
- Ne podešavati VAD samo prema jednom mikrofonu i jednoj osobi.
- Ne proglasiti problem riješen samo zato što typecheck i token endpoint testovi prolaze.

## 20. Procjena alternative: OpenAI Agents SDK voice sloj

Vrijedi napraviti mali odvojeni spike sa aktuelnim OpenAI Agents SDK voice/realtime slojem samo ako on u stvarnom Electron okruženju preuzima dovoljno lifecycle odgovornosti i ostavlja kontrolu nad postojećim lokalnim tool i confirmation bridgeom.

Potencijalna korist:

- manje ručno održavane Realtime event logike;
- standardizovan lifecycle;
- lakše praćenje session i tool događaja.

Rizici:

- migracija postojećeg confirmation i security konteksta;
- nepredviđene promjene tool semantike;
- dodatna zavisnost i release cadence;
- mogući konflikt sa Electron renderer okruženjem;
- veći blast radius nego ciljani reliability refactor.

Zato Agents SDK nije početna preporuka. Prvo treba procijeniti mali proof of concept, bez uklanjanja postojećeg klijenta. Ako ne uklanja većinu ručno održavanih lifecycle problema, migracija se ne isplati.

## 21. Verifikacija izvršena tokom analize

- `npm run typecheck` — prošao;
- `python -m pytest -q tests/test_realtime.py` — 3 testa prošla;
- Python testovi potvrđuju izdavanje tokena i obradu upstream grešaka;
- ne postoje ekvivalentni automatizovani testovi stvarnog TypeScript/WebRTC lifecyclea;
- runtime razgovor sa stvarnim mikrofonom nije izvršen u ovom pregledu.

Ovi rezultati potvrđuju da trenutni kod prolazi statičku provjeru i osnovni backend ugovor. Ne potvrđuju stabilnost glasovne komunikacije.

## 22. Konačna preporuka

Zadržati:

- WebRTC za direktan audio;
- ephemeral credential preko Python backenda;
- Python kao vlasnika alata, dozvola i poslovne logike;
- Electron/React kao UI i media-session sloj.

Promijeniti:

- `RickyRealtimeClient` u robustan session manager;
- connection i voice state u eksplicitnu state mašinu;
- tool loop tako da uvijek završava kontrolisanim outputom;
- DataChannel slanje tako da greške nisu tihe;
- događaje tako da se obrađuju deterministički i po session generaciji;
- UI tako da razlikuje mikrofon, mrežu, VAD, model, alat i audio-output problem;
- testove tako da simuliraju stvarne lifecycle kvarove.

Najveći povrat na uloženo vrijeme daju Faza 0 i Faza 1. Tek poslije njih ima smisla procjenjivati da li su preostali problemi dominantno VAD, transkripcija ili model.

## 23. Službene reference

- OpenAI, Realtime API with WebRTC: <https://developers.openai.com/api/docs/guides/realtime-webrtc>
- OpenAI, Voice activity detection: <https://developers.openai.com/api/docs/guides/realtime-vad>
- OpenAI, Realtime conversations: <https://developers.openai.com/api/docs/guides/realtime-conversations>
- OpenAI, Realtime transcription: <https://developers.openai.com/api/docs/guides/realtime-transcription>
- OpenAI, Realtime and audio overview: <https://developers.openai.com/api/docs/guides/realtime>
- OpenAI, model catalog: <https://developers.openai.com/api/docs/models>
