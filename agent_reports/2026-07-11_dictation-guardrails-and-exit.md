# Agent report — diktat: sadržajno odbijanje, pogrešan jezik, glasovni izlazak

**Datum:** 2026-07-11
**Povod:** korisnik prijavio tri odvojena problema nakon uspješnog osnovnog
testa (glasovni ulazak, latinica, dosljedan tekst rade): (1) Riki odbija da
upiše "neprikladne" rečenice, (2) povremeno upisuje na pogrešnom jeziku (ne
samo pismo), (3) glasovna komanda za izlazak iz diktata se upisala KAO
diktat umjesto da izvrši izlazak.

## 1. Odbijanje "neprikladnog" sadržaja — DJELIMIČNO adresirano, iskreno

**Uzrok (najbolja procjena):** OpenAI model (gpt-realtime-2) ima ugrađenu
sigurnosnu obuku koja ga tjera da preuzme ulogu "autora"/procjenjivača
sadržaja umjesto čistog transkribera, čak i za bezazlen sadržaj (piće u
Sarajevu). Ovo NIJE nešto što Nas-agent kod direktno kontroliše — dolazi iz
OpenAI-jevog modela.

**Popravka:** dodana eksplicitna instrukcija u `RICKY_INSTRUCTIONS` —
"dok Riley diktira, ti si transkriber, ne autor; ne odbijaj/ublažavaj/
komentariši običan lični sadržaj; odbij SAMO jasno kršenje politike (npr.
detaljna uputstva za ozbiljnu štetu)".

**⚠️ Iskreno:** ovo je prompt-inženjering, ne garantovano rješenje. Model
može i dalje povremeno odbiti nešto što smatra spornim, jer je ta sigurnosna
obuka duboko ugrađena i prompt je ne može uvijek nadjačati. Ako se
ponavlja i poslije ovog fixa, to je stvarna granica trenutnog modela, ne
propust u kodu koji mogu dalje popraviti bez promjene modela/pristupa.

## 2. Povremeno pogrešan jezik (ne samo pismo)

**Uzrok:** transkripcija je imala `model: "whisper-1"` ali NE i `language`
hint — bez njega Whisper radi puni auto-detect PO SVAKOM izgovoru, što
povremeno pogodi pogrešan jezik u cjelini (ne samo ćirilicu/latinicu, kao
ranije popravljeni bug).

**Popravka:** dodano `language: "sr"` uz `model: "whisper-1"`, na oba mjesta
(početna konfiguracija sesije + `setDictationMode` session.update, isti
razlog kao ranije — da se ne izgubi na plitkom spajanju).

**⚠️ Iskreno:** ovo TREBA smanjiti učestalost, ali kao i ranije, ne mogu
uživo testirati OpenAI API pa ne garantujem 100% eliminaciju.

## 3. Nema glasovnog izlaska iz diktata — POPRAVLJENO, deterministički

**Uzrok:** kod je imao ulaznu detekciju ("dikt" fraza van diktata → uđi), ali
NIKAD izlaznu. Dok je `screen === "dictation"`, SVAKI izgovor se upisivao
kao sadržaj — uključujući i pokušaj da se izađe.

**Popravka:** nova provjera u `App.tsx` `onTranscript`, simetrična ulaznoj —
prije upisa u `dictationText`, provjerava listu izlaznih fraza
(`DICTATION_EXIT_PHRASES`): "vrati se u normalan", "izađi iz diktat",
"prekini diktat", "završi diktiranje" (+ varijante). Namjerno **višerečne,
specifične fraze**, ne pojedinačne riječi — jednu riječ poput "gotovo" bi
korisnik lako mogao izgovoriti kao dio stvarnog diktata ("Posao je gotovo"),
što bi ga neželjeno izbacilo iz moda. Ako fraza poklopi: `setDictationMode(false)`
+ `setScreen("home")`, TEKST SE NE UPISUJE (tretirano kao komanda, ne sadržaj)
— identična logika kao ulazna detekcija, samo obrnuto.

Dodana i prompt napomena da Riki kratko potvrdi izlazak (ne treba pozvati
nikakav tool — isti obrazac kao ulazak).

## Verifikacija

- `node --check electron/ipc_handlers/realtime.cjs` — čisto.
- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- Runtime NIJE testiran — potreban korisnički test za sva tri, pogotovo #1 i #2
  koji zavise od OpenAI ponašanja koje ne mogu uživo provjeriti.

## Test za korisnika

1. **Izlazak:** uđi u diktat, reci "vrati se u normalan mod" (ili "prekini
   diktiranje") — treba izaći BEZ da se ta rečenica upiše u tekst.
2. **Sadržaj:** probaj ponovo istu ili sličnu "neprikladnu" rečenicu — javi
   da li je i dalje odbija (ako da, to je granica modela, ne bug za dalje
   lovljenje u kodu).
3. **Jezik:** duži test (par minuta diktiranja) — provjeri da li se pogrešan
   jezik i dalje javlja, i koliko često u odnosu na prije.

## Rizici/ograničenja

- Lista izlaznih fraza je namjerno mala i specifična — ako korisnik koristi
  neku frazu koju nisam predvidio (npr. samo "izlaz" bez "diktat"), neće
  raditi. Lako se proširuje kad se sazna tačna fraza koju korisnik prirodno
  koristi.
- Stavke #1 i #2 zavise od OpenAI modela/API ponašanja koje se ne može
  potpuno kontrolisati sa naše strane — postavljene su najbolje moguće
  ograde (prompt + language hint), ne garancija.

## Potrebna korisnička potvrda

Runtime test obavezan, posebno za #1 i #2 gdje je ishod stvarno neizvjestan
dok se ne proba uživo.
