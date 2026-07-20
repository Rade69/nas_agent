# FlowOS — revidirani plan realizacije

**Datum revizije:** 2026-07-17
**Status:** prijedlog, nije odobren za realizaciju
**Odnos prema originalu:** ovaj dokument **zamjenjuje** `FLOWOS_PLAN_REALIZACIJE.md` u dijelu vizije, opsega i redoslijeda. Original se zadržava kao trag ranijeg razmišljanja, ali **nije izvor istine** — ako se dva dokumenta razilaze, važi ovaj.
**Preduslov za bilo kakav rad:** Naš-agent (RileyJarvis Windows Hybrid) mora biti u stabilnoj fazi. Vidi §12.

---

## 0. Zašto revizija — šta je originalni plan promašio

Originalni plan je tehnički dobro napisan, ali je rješavao **pogrešno formulisan problem**.

Original polazi od pretpostavke: *korisniku treba sistem koji hvata misli i pretvara ih u organizovane zadatke* (Inbox → Razjasni → Planiraj → Danas → Review). To je klasičan GTD model.

Stvarnost, utvrđena u razgovoru 2026-07-17:

- Korisnik **ne koristi** ClickUp, Obsidian, Todoist niti bilo koji sličan alat — i **funkcioniše bez njih**.
- Prema tome, hvatanje misli i planiranje dana **nije njegova praznina**. Da jeste, već bi koristio neki od desetina zrelih alata koji to rade bolje nego što bi FlowOS ikad mogao.
- Njegova stvarna praznina je **vidljivost u faze sopstvenog rada** — rada koji već teče kroz agente (Claude Code + Codex/pi), kroz planove i kroz izvještaje, ali se nigdje ne vidi na jednom mjestu.

Formulacija koju je korisnik potvrdio kao tačnu:

> **Ogledalo rada kroz faze, a ne organizator obaveza.**

Zato je ~80% originalnog opsega (Inbox, AI klasifikacija unosa, Danas sa Sada/Sljedeće/Kasnije, fokus tajmer, planiranje dana, Review u GTD smislu) **izbačeno iz ovog plana**. To nije skraćivanje zbog vremena — to je uklanjanje pogrešnog proizvoda.

### 0.1 Dokaz da praznina postoji (nije hipoteza)

U sesiji 2026-07-17 desilo se sljedeće:

1. Claude Code (ja) je tvrdio da Python backend Naš-agenta *ne postoji* i da je rad "u FAZI 4+".
2. Stvarnost: sve faze 0–19 su završene, backend ima 105 `.py` fajlova, pun agent runtime, 236 testova.
3. Uzrok greške: citirana je zastarjela uvodna proza iz `CLAUDE.md` umjesto provjere trackera.
4. Ispravka je došla tek kad je **korisnik ručno poslao** `docs/PROJECT_OVERVIEW.md`.

To nije bila samo greška jednog agenta. To je **simptom**: aktuelno stanje rada nije lako dostupno *ni korisniku, ni Claude Code-u, ni Codexu*. Svi rekonstruišu stanje iz raštrkanih izvora, i svi povremeno promaše.

**To je problem koji FlowOS treba da riješi. Ništa drugo.**

---

## 1. Vizija (redefinisana)

FlowOS je **sloj vidljivosti nad radom koji već teče**. On ne prima obaveze od korisnika i ne organizuje ih — on čita tragove koje rad **već ostavlja za sobom** i pretvara ih u jasnu sliku faza.

> FlowOS ne pita korisnika šta radi. FlowOS mu pokazuje gdje je rad stigao.

Ključna arhitektonska razlika u odnosu na original:

| | Original (v1) | Revidirano (v2) |
|---|---|---|
| Ulaz | korisnik unosi misli/zadatke | **nema ručnog unosa** — čitaju se postojeći artefakti |
| Uloga AI-ja | klasifikuje svaki unos, predlaže rok/prioritet | marginalna; deterministički kod izvodi ~sve |
| Prvi ekran | Inbox (12 nerazjašnjenih) | **Pregled faza** (gdje je koji tok) |
| Izvor istine | FlowOS baza | **repozitorij** (git, tracker, reports) — FlowOS je samo čita |
| Smjer podataka | čovjek → sistem | rad → sistem → čovjek |
| Odnos sa Naš-agentom | FlowOS delegira zadatke agentu | FlowOS **posmatra** šta su agenti uradili |

FlowOS nije zamjena za Naš-agent i nije task manager. FlowOS je **ogledalo**.

---

## 2. Šta FlowOS NIJE (eksplicitno izbačeno)

Ovo je najvažnija sekcija plana. Sve navedeno je bilo u v1 i **namjerno je uklonjeno**:

- ❌ **Inbox / hvatanje misli** — korisnik to ne radi ni u jednom alatu; nema razloga vjerovati da bi počeo.
- ❌ **AI klasifikacija unosa** (prijedlog projekta/roka/prioriteta/tipa) — nema unosa koji treba klasifikovati.
- ❌ **Danas / Sada / Sljedeće / Kasnije danas** — planiranje dana nije problem.
- ❌ **Fokus sesija i tajmer** — mjerenje vremena nije problem.
- ❌ **AI plan za danas** — sistem ne treba da predlaže šta raditi; korisnik to zna.
- ❌ **Review u GTD smislu** (dnevni/sedmični pregled sa zaključcima) — ceremonija koju korisnik ne prakticira.
- ❌ **Prioriteti, energija, procjena trajanja, ponavljajući zadaci** — atributi task managera.
- ❌ **Semantička pretraga, vektorska baza** — nema mase teksta koja to opravdava.
- ❌ **Cloud sync, mobilni capture, timski workspace** — nema drugog korisnika ni drugog uređaja u problemu.
- ❌ **Delegiranje zadataka agentu iz FlowOS-a** (v1 §9.3, Faza 4) — vidi §9.3 niže; ovo je odloženo, ne odbačeno.

**Pravilo protiv povratka GTD-a:** ako se u bilo kojoj fazi pojavi zahtjev "dodaj samo još Inbox / samo još tajmer / samo još prioritete" — to je signal da se proizvod vraća u pogrešan oblik. Odgovor je ne, osim ako postoji zapisan dokaz da je korisnik tu funkciju **stvarno tražio nakon što je dvije sedmice koristio sistem bez nje**.

---

## 3. Principi (naslijeđeni iz razgovora 2026-07-17)

1. **Najmanja količina autonomije/kompleksnosti koja bezbjedno radi posao.** (`Use the least autonomous system that can safely do the job.`)
2. **Dokaz prije gradnje.** Ne gradi se alat za proces koji još nije dokazano ponovljiv. Svaka faza ima kill kriterij.
3. **Checkability je najvažniji kriterijum.** Svaka faza mora imati jeftin verifier — inače se ne radi.
4. **Deterministički kod je zadani put.** Model se koristi samo tamo gdje jezik stvarno treba obraditi, i to opciono.
5. **Ono što mora da se desi uvijek, ne smije zavisiti od toga hoće li model odlučiti da to uradi.** (push, ne pull)
6. **Git je jedini sloj kroz koji prolaze svi agenti.** Claude Code hookovi ne vide Codexov/pi-jev rad; git vidi sve.
7. **Ne duplirati ono što Naš-agent već ima** (permission engine, confirmations, cancellation, audit) — ni ne uvoziti tuđu infrastrukturu koja to duplira.
8. **Ne vjerovati izvještaju agenta na riječ** — izvor istine je stvaran diff/artefakt, ne tvrdnja.
9. **Read-only dok se ne dokaže potreba za pisanjem.**
10. **Nijedan token se ne troši bez jasne koristi.** Ako se ista informacija može izvesti kodom — izvodi se kodom.

---

## 4. Stvarni problem, precizno

Rad na projektima teče kroz više aktera (korisnik, Claude Code, Codex/pi) i ostavlja tragove na najmanje pet mjesta:

| Izvor | Šta nosi | Zašto nije dovoljan sam |
|---|---|---|
| `docs/MIGRATION_PLAN.md` tracker | status faza — **izvor istine** | tekst; ne pokazuje tok, ne veže se za stvarni kod |
| `agent_reports/*.md` | šta je rađeno, zašto, šta nije dirano | raspršeno po datumima; niko ne čita 50 fajlova |
| git istorija | ko je šta stvarno promijenio | tehnički; ne govori o fazama |
| `docs/PROJECT_OVERVIEW.md` | snapshot cjeline | **ručno pisan → odmah zastari** |
| razgovori sa agentima | najsvježiji kontekst | nestaje sa sesijom |

Nijedan pogled ne odgovara na pitanje koje korisnik stvarno ima:

> **Gdje smo? Šta je urađeno? Ko je to uradio? Šta čeka? Šta je blokirano? Šta je sljedeće?**

FlowOS v2 postoji **isključivo** da odgovori na to pitanje, izvedeno iz izvora koji **već postoje**, bez ručnog održavanja.

---

## 5. Izvori podataka (temelj arhitekture)

FlowOS **ne uvodi novi izvor istine**. On čita postojeće i izvodi pogled. Ovo je najvažnija tehnička odluka plana.

### 5.1 Primarni izvori (read-only)

```text
git (commits, autori, datumi, diff, Co-Authored-By)   → ko je šta radio, kada
docs/MIGRATION_PLAN.md (tracker tabela)               → definicija faza + status
agent_reports/*.md (frontmatter + sekcije)            → šta/zašto/rizici/follow-up
docs/PROJECT_OVERVIEW.md                              → poznati gapovi
```

### 5.2 Zašto git-first

Korisnik radi sa više agenata na istom stablu. Claude Code hookovi **ne vide** Codexov ni pi-jev rad. Ali svaki agent na kraju prolazi kroz git — commit je univerzalna tačka hvatanja. Zato:

- **git = temelj** (hvata sve aktere, uvijek)
- **hookovi = opcioni bonus** (preciznije, ali samo za Claude Code sesije) — **ne u v0.1**

### 5.3 Šta FlowOS NE radi sa izvorima

- ne mijenja ih
- ne traži od agenata da ih drugačije pišu (u v0.1)
- ne uvodi novi fajl koji neko mora ručno održavati (to je greška `PROJECT_OVERVIEW.md`-a i razlog zašto zastari)

**Ako FlowOS zahtijeva da neko nešto ručno održava da bi radio — dizajn je pogrešan.**

---

## 6. Funkcionalni opseg (faza-vidljivost, ne GTD)

### 6.1 Pregled faza (prvi i glavni ekran)

Za svaki aktivan tok rada (npr. "Naš-agent migracija", "Browser bridge", "GUI lokalizacija"):

- naziv toka i njegov cilj
- **faze sa statusom** (urađeno / u toku / čeka / blokirano)
- gdje je tok **sada**
- šta je **sljedeće**
- ko je posljednji radio na tome (Claude / Codex / korisnik) i kada
- šta ga **blokira**, ako išta

Izvedeno iz: tracker tabele + git istorije + agent_reports.

### 6.2 Tok — detalj

- kompletna istorija faza toka
- povezani commiti (stvarni, ne tvrdnja)
- povezani agent_reports
- otvoreni gapovi vezani za taj tok
- **razilaženja**: gdje tracker kaže jedno, a kod/git drugo ⚠️

### 6.3 Detekcija zastarjelosti (ključna funkcija)

Ovo je funkcija koja bi spriječila grešku iz §0.1:

- tracker kaže "u toku", a nema commita 3+ sedmice → **zastalo**
- tracker kaže "nije početo", a postoje commiti koji to diraju → **tracker zastario**
- dokument tvrdi stanje X, a git pokazuje Y → **razilaženje, prijavi**

Sve deterministički. Bez modela.

### 6.4 Ko-je-šta-radio (multi-agent pregled)

- pregled rada po akteru (Claude Code / Codex / pi / korisnik) iz `Co-Authored-By` i commit metapodataka
- šta je jedan agent ostavio nedovršeno
- gdje su dva agenta dirala isti fajl (collision vidljivost)

### 6.5 Šta je NOVO od zadnjeg puta

- šta se promijenilo otkad korisnik zadnji put gledao
- direktno rješava "nastavi gdje si stao" potrebu, bez ijednog ručnog zapisa

**To je cio MVP opseg. Nema šestog ekrana.**

---

## 7. GUI struktura (redefinisana)

### 7.1 Navigacija

```text
Pregled faza      ← prvi ekran, ne Inbox
Tokovi
Akteri            (ko je šta radio)
Razilaženja       (gdje se izvori ne slažu)
Postavke
```

Nema: Inbox, Danas, Review, Fokus, Pretraga (dok se ne pokaže da treba).

### 7.2 Prvi ekran — skica

```text
┌─────────────────────────────────────────────────────────┐
│ NAŠ-AGENT MIGRACIJA                    ▓▓▓▓▓▓▓▓▓░ 19/19 │
│ Faze 0-19: ✅ završeno                                   │
│ Sada: Security Gate 1 (djelimično)                       │
│ Blokira: document-privacy modes, CI security checks      │
│ Zadnji rad: Claude Code, prije 2 dana (746aa9d)          │
│ ⚠️ PROJECT_OVERVIEW.md nije ažuriran 5 dana              │
├─────────────────────────────────────────────────────────┤
│ BROWSER BRIDGE                         ▓▓▓▓▓▓▓░░░        │
│ Sada: čitanje stranice + manipulacija (druga sesija)     │
│ Zadnji rad: prije 1 dan (746aa9d fix pairing)            │
│ ⚠️ Dodiruje S-2 (poznat gap: outbound low-risk)          │
├─────────────────────────────────────────────────────────┤
│ GUI LOKALIZACIJA                       ▓▓▓▓▓▓░░░░ 12/20  │
│ Sada: PR-3 nije počet                                    │
│ Zadnji rad: prije 5 dana                                 │
│ ⏸️ zastalo                                               │
└─────────────────────────────────────────────────────────┘
```

Ovo je ekran koji bi spriječio grešku iz §0.1. Ovo je proizvod.

### 7.3 Vizuelni sistem

Zadržava se iz v1 (tamna tema, ljubičasta samo za primarne akcije, zelena/narandžasta/crvena za stanja, visok kontrast, keyboard). Codexov mockup je zanatski dobar — **ali njegov sadržaj (Inbox/Danas/tajmer) se ne koristi**, samo vizuelni jezik.

---

## 8. Tehnička arhitektura

### 8.1 Radikalno pojednostavljeno u odnosu na v1

v1 je predviđao Electron + React + FastAPI + SQLite + Alembic + TanStack + Zustand + background job runner + WebSocket. **Za read-only pogled nad git-om i par MD fajlova to je preveliko.**

**v0.1 — najmanje što radi posao:**

```text
Python skripta → čita git + tracker + agent_reports → generiše statični pregled
```

Bez baze. Bez servera. Bez Electrona. Bez migracija.

**Verifier:** pregled je tačan ili nije — provjerljivo poređenjem sa stvarnim stanjem repo-a.

### 8.2 Kada (i samo ako) v0.1 dokaže vrijednost

Nadograđuje se **redom, po dokazanoj potrebi**:

1. `+` osvježavanje na zahtjev (CLI komanda)
2. `+` više projekata odjednom
3. `+` GUI — tek ako tekstualni/HTML pregled nije dovoljan
4. `+` SQLite — **tek ako** se pokaže potreba za istorijom stanja kroz vrijeme
5. `+` Electron/FastAPI — **tek ako** GUI zaista treba biti aplikacija, a ne stranica

**Svaki korak zahtijeva zapisan razlog zašto prethodni nije bio dovoljan.** Bez toga se ne prelazi dalje.

### 8.3 Zaseban repo — ne modul Naš-agenta

Razlog: Naš-agent već ima dokumentovan collision problem (`config.py`, `app/main.py`, `electron/main.cjs`) sa dva agenta na istom stablu. Drugi proizvod u istom repo-u bi to pogoršao. FlowOS čita repozitorije **spolja** — nema razloga da živi unutar ijednog.

---

## 9. AI arhitektura

### 9.1 Nivo 0 — bez modela (pokriva ~sve)

- parsiranje git istorije, trackera, reporta
- računanje statusa faza, zastalosti, razilaženja
- detekcija ko je šta radio, collision
- generisanje pregleda

**Ovo je 95% proizvoda i ne košta ništa.**

### 9.2 Nivo 1 — jeftini model (opciono, OFF by default)

Samo za jedno: **sažimanje** (npr. 8 agent_reporta → 3 rečenice "šta se dešavalo na ovom toku").

Uslovi:
- isključivo na zahtjev korisnika, nikad automatski
- rezultat se **keširа** (isti ulaz = isti izlaz, bez novog poziva)
- ako model nije dostupan — sistem radi normalno, bez sažetka

### 9.3 Nivo 2 — Naš-agent: NE u ovom planu

v1 je predviđao delegiranje zadataka agentu iz FlowOS-a (Faza 4, 3–4 sedmice). **Izbačeno iz v2 opsega**, iz tri razloga:

1. Korisnik već delegira agentima direktno i to nije njegova praznina.
2. To bi napravilo FlowOS **izvršiocem**, a on je namjerno samo **ogledalo**. Ogledalo koje mijenja ono što posmatra prestaje biti ogledalo.
3. Naš-agent već ima permission/confirmation/cancellation sloj — FlowOS bi to ili duplirao ili zaobišao. Oboje je loše.

**Ako se ikad doda:** samo kroz postojeći Naš-agent API, uz njegov permission engine, nikad mimo. Ali ne prije nego što read-only ogledalo dokaže vrijednost kroz mjesece upotrebe.

---

## 10. Sigurnost i privatnost

Pojednostavljeno, jer je read-only:

- FlowOS **ne piše** u posmatrane repozitorije
- FlowOS **nema** shell tool
- FlowOS **ne šalje** ništa mreži u nivou 0 (default)
- ako se uključi nivo 1: šalje se **samo sažeti tekst reporta**, nikad diff, nikad kod, nikad tajne — uz redaction obrazac (`api[_-]?key`, `token`, `password`, `secret`)
- lokalno; bez cloud-a

---

## 11. Faze realizacije (dokaz prije gradnje)

Svaka faza ima **verifier** i **kill kriterij**. Ako faza padne — staje se, ne gura dalje.

### Faza −1 — Vizuelni mockup (0 koda aplikacije, 1 dan) 🔴 OBAVEZNO PRVO

**Status: URAĐENO 2026-07-17** → [artifact mockup](https://claude.ai/code/artifact/47be578e-4944-4e30-9850-a17382a73509)

Napraviti **vizuelni mockup** ekrana Pregled faza za **stvarne tokove** iz repo-a — sa stvarnim podacima (git, tracker, agent_reports), ne izmišljenim primjerima.

> **Korekcija (2026-07-17):** ranija verzija ovog plana tražila je *papirni/pisani* opis. To je pogrešan medij za ovog korisnika — on eksplicitno radi tako da mu **treba da vidi GUI da bi mogao razmišljati o funkcionalnostima i međuzavisnostima**. Instinkt (validiraj prije koda) je bio tačan; oblik nije. Mockup nije gradnja — nula koda aplikacije, nula prekršenih preduslova iz §12.

**Zašto stvarni podaci, ne primjeri:** mockup sa izmišljenim podacima ne može odgovoriti na pitanje "govori li mi ovo nešto što mi danas fali". Mockup sa stvarnim podacima odgovara odmah — i sam čin izrade je test: ako se stvarno stanje ne može izvesti iz postojećih izvora, dizajn ne radi, i to se sazna prije koda.

**Šta je izrada mockupa već dokazala (2026-07-17):**

- Iz `git log` je izvučeno **5 aktivnih tokova** (Plans panel P0–P5, Browser bridge C4, A11y A1–A3, Pixel board, GUI lokalizacija) — agent koji radi na projektu nije znao da postoje dok nije pogledao.
- Detektovana su **3 stvarna razilaženja**, uključujući ono koje je istog dana izazvalo netačnu tvrdnju o statusu (`CLAUDE.md` tvrdi da backend ne postoji vs. 105 `.py` fajlova u git-u).
- Zaključak: **izvori su dovoljno strukturirani** da se pogled izvede deterministički. Otvorena bojazan iz §15.4 je time smanjena, ali ne i zatvorena (agent_reports su i dalje slobodan tekst).

**Verifier:** korisnik pogleda i kaže jedno od:
- "da, ovo je ono što mi fali" → ide se dalje na Fazu 0
- "ne, ovo mi ne govori ništa" → **projekat staje ovdje, cijena: jedan dan**

**Kill kriterij:** ako mockup ne izazove reakciju "ovo bih gledao svaki dan" — ne gradi se ništa.

### Faza 0 — Ručni skript (2–3 dana)

Jedna Python skripta koja generiše taj isti pregled automatski, iz stvarnih izvora.

**Verifier:** pokrenuti na Naš-agentu; pregled mora biti **tačan** (poređenje sa stvarnim stanjem) i **koristan** (korisnik ga otvara bar 3 puta u sedmici, neprisiljeno).

**Kill kriterij:** ako korisnik ne otvori pregled 7 dana zaredom bez podsjećanja — kraj. Alat koji se mora podsjećati da se koristi nije riješio problem.

### Faza 1 — Detekcija zastarjelosti/razilaženja (3–4 dana)

Dodati §6.3: tracker vs git, zastali tokovi, razilaženja.

**Verifier:** sistem mora uhvatiti **bar jedno stvarno razilaženje** koje čovjek nije primijetio. Test slučaj postoji: greška iz §0.1 (`CLAUDE.md` tvrdi "backend ne postoji", git pokazuje 105 fajlova) — ako sistem to ne bi uhvatio, ne radi svoj posao.

**Kill kriterij:** nula uhvaćenih razilaženja za mjesec dana → funkcija nema svrhu.

### Faza 2 — Više tokova + multi-agent pregled (1 sedmica)

§6.4 i §6.5: ko je šta radio, šta je novo od zadnjeg puta, više projekata.

**Verifier:** korisnik može odgovoriti na "gdje smo, ko je šta radio, šta visi" **za sve aktivne projekte**, bez otvaranja ijednog drugog alata.

### Faza 3 — Vidljiv oblik (1–2 sedmice, samo ako je traženo)

HTML/GUI — **tek ako** tekstualni izlaz iz Faze 0–2 nije dovoljan, sa zapisanim razlogom zašto.

**Kill kriterij:** ako je tekst dovoljan — GUI se ne pravi. Nema estetske gradnje.

### Faza 4+ — sve ostalo

Trajno stanje, istorija kroz vrijeme, sažeci, Electron — **samo uz zapisan dokaz potrebe iz stvarne upotrebe.**

### Ukupna procjena

```text
Faza −1:  1 dan
Faza 0:   2-3 dana
Faza 1:   3-4 dana
Faza 2:   1 sedmica
─────────────────────
Upotrebljiva verzija: ~2-3 sedmice
```

Original: 12–17 sedmica. Razlika nije u brzini rada — nego u tome što se **ne gradi pogrešan proizvod**.

---

## 12. Preduslovi (tvrdi)

Ništa iz ovog plana ne počinje dok:

1. **Naš-agent nije u stabilnoj fazi** — sve komponente rade bez problema (korisnikovo eksplicitno pravilo, 2026-07-17). Trenutno otvoreno: Security Gate 1/2, dev-mode auth fail-open, S-2 outbound gap, nema frontend testova, GUI lokalizacija 12/20.
2. **Ne postoji drugi otvoren veliki front.** Dva paralelna sistema od jednog čovjeka je glavni rizik ovog plana.
3. **Faza −1 (papirni test) nije prošla.**

**Redoslijed nije pregovorljiv.** Ovo je plan koji čeka, ne plan koji se izvršava.

---

## 13. Rizici

| Rizik | Zašto je stvaran | Ublažavanje |
|---|---|---|
| **Vraćanje u GTD** | Codexov mockup je već skliznuo u Inbox/Danas/tajmer jer je pratio v1 | §2 lista zabrana; svaki novi ekran mora odgovoriti "koje faza-pitanje ovo rješava?" |
| **Paralelni front** | Naš-agent nije gotov; jedan čovjek | §12 preduslov |
| **Alat koji se ne koristi** | Najčešći ishod ličnih alata | Kill kriterij Faze 0 (7 dana bez otvaranja = kraj) |
| **Pregled postane šum** | 15 tokova, svaki žut | Max 5–7 tokova; prikazati samo ono što traži pažnju |
| **Izvori nisu dovoljno strukturirani** | agent_reports su slobodan tekst | Faza −1 to otkriva na papiru, prije koda |
| **Scope creep ka izvršavanju** | "kad već vidim, da mogu i kliknuti" | §9.3 — ogledalo koje mijenja stvarnost nije ogledalo |
| **Duplira Naš-agent** | permission/audit već postoje | Read-only; nema pisanja |

---

## 14. Metrike (male, provjerljive)

Nema produktnih metrika tipa "80% Inbox stavki razjašnjeno" — nema Inboxa.

```text
Otvoren neprisiljeno              → ≥3× sedmično (inače: kill)
Uhvaćeno stvarnih razilaženja     → ≥1 mjesečno (inače: funkcija bez svrhe)
Ručnih pitanja "gdje smo?"        → treba pasti ka nuli
Tačnost pregleda                  → 100% (netačan pregled je gori od nikakvog)
AI trošak                         → 0 u default modu
Vrijeme do odgovora "gdje smo"    → <10 sekundi
```

---

## 15. Otvorene odluke

1. **Jedan projekat ili svi?** (Naš-agent prvo, ili odmah ASYCUDA_PRO/Deklarant Pro/FieldFix?) — preporuka: **jedan**, Naš-agent, jer je najbolje poznat.
2. **Naziv.** "FlowOS" nosi teret v1 značenja (operativni sistem za upravljanje radom). Ovo više nije to. Kandidati: *Ogledalo*, *Pregled*, *Stanje*. Korisnikova odluka.
3. **Da li tokovi postoje kao entitet ili se izvode?** — preporuka: izvode se iz trackera, bez novog ručnog fajla.
4. **Šta ako izvori nisu dovoljno strukturirani?** — otkriva Faza −1. Ako agent_reports moraju dobiti frontmatter da bi ovo radilo, to je mala izmjena postojećeg obrasca, ne novi sistem.
5. **Codexov mockup** — koristiti vizuelni jezik, odbaciti sadržaj. Ili početi ispočetka?

---

## 16. Konačna preporuka

Original je predlagao 12–17 sedmica za proizvod koji korisnik ne bi koristio, jer bi rješavao problem koji nema.

Ovaj plan predlaže: **jedan dan papirnog testa** koji odgovara na pitanje da li proizvod uopšte treba postojati — i, ako prođe, ~2–3 sedmice za nešto što stvarno gleda svaki dan.

Suština:

> **FlowOS ne treba da organizuje rad. Rad je već organizovan — kroz faze, planove i agente.**
> **FlowOS treba samo da ga učini vidljivim.**

I dalje važi pravilo koje je nadživjelo sve ostalo iz razgovora 2026-07-17:

```text
Use the least autonomous system that can safely do the job.
```

Ovdje to znači: **read-only skripta koja čita git i tracker** je vjerovatno cio proizvod. Sve preko toga mora zaraditi svoje mjesto.

---

## Dodatak A — Šta je zadržano iz originala

Da ne bi izgledalo da je original bezvrijedan — ovo je preživjelo:

- ✅ **Vizuelni sistem** (§7.4 v1) — tamna tema, jedno primarno dugme, boje stanja
- ✅ **Nivo 0/1/2 filozofija** (§9 v1) — deterministički kod prvo, model tek gdje treba
- ✅ **Kontrola troška** (§9.5, §17 v1) — bez vektorske baze, bez skupog modela za rutinu, budžet vidljiv
- ✅ **Sigurnosni principi** (§12 v1) — lokalno, bez shell-a, najmanji mogući kontekst modelu
- ✅ **Faza 0 instinkt** (§13 v1) — "validiraj workflow prije koda" — ovdje pooštreno u Fazu −1 sa kill kriterijem
- ✅ **§21 redoslijed odluka** (v1) — "validiraj bez kompleksnog koda, izmjeri gdje AI stvarno štedi" — to je i ovdje kičma

Original nije bio loše napisan. Bio je napisan za pogrešnog korisnika — generičkog čovjeka koji traži task manager, a ne za čovjeka koji vodi rad kroz agente i treba da ga vidi.
