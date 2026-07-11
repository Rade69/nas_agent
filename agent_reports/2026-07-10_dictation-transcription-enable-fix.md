# Agent report — Diktiranje: uzrok zašto ništa nije radilo (transkripcija nikad uključena)

**Datum:** 2026-07-10
**Povod:** korisnička prijava — "Riki ga ne može otvoriti panel", i **čak ni
ručni klik pa govor ne upisuje ništa u textarea**.

## Ključna dijagnostička činjenica

Korisnik je potvrdio: klik na "Diktiranje" dugme **uspješno otvara panel**
(znači `screen`/dugme rade ispravno), ali tekst se **nikad ne upisuje** kad
govori. Ovo sužava problem isključivo na mehanizam hvatanja teksta, ne na
prebacivanje ekrana — što je isključilo nekoliko hipoteza (stale `screenRef`,
loše ožičeno dugme) i usmjerilo istragu na sam transkripcijski put.

## Vjerovatan korijenski uzrok

Provjerio sam punu `audio.input` konfiguraciju sesije poslatu OpenAI-ju pri
mintovanju tokena (`electron/ipc_handlers/realtime.cjs`) — sadržala je
**samo** `turn_detection`, **nikad** `transcription` polje. Bez eksplicitnog
`audio.input.transcription` u konfiguraciji, OpenAI Realtime API **ne mora**
(a po mom najboljem razumijevanju API-ja — vjerovatno neće) generisati
`conversation.item.input_audio_transcription.completed` evente za korisnikov
govor — jer transkripcija korisnikovog govora je opciona, odvojena mogućnost
od toga da model razumije/odgovori na audio (model radi direktno sa audio
signalom, transkript je samo za prikaz klijentu).

**Cijeli moj Faza 1 dizajn (i "dikt" glasovni triger, i hvatanje teksta u
dictationText) zavisi ISKLJUČIVO od tog jednog event tipa.** Ako se nikad
nije okidao, ništa od toga nikad nije moglo raditi — ni za diktat, ni
(vjerovatno) za prikaz korisnikovog govora u glavnom transcript/Aktivnost
panelu uopšte. Ovo je vjerovatno **pre-postojeći gap**, ne nešto što sam ja
pokvario danas — samo sam ga prvi put stvarno pogodio jer je moj rad
zavisio od njega.

## Popravka (dva mjesta, namjerno)

1. **`electron/ipc_handlers/realtime.cjs`** — dodano
   `audio.input.transcription: { model: "whisper-1" }` u početnu konfiguraciju
   sesije (pri mintovanju tokena).
2. **`src/lib/realtime.ts` `setDictationMode`** — **isto** polje dodano i u
   `session.update` koji se šalje pri ulasku/izlasku iz diktata. Razlog: ako
   OpenAI-jev `session.update` radi plitko spajanje (ne duboko) na nivou
   `audio.input` objekta, moj raniji update (koji je slao SAMO
   `turn_detection`) bi mogao **izbrisati** `transcription` polje čim se
   diktat uključi/isključi — čak i kad bi početna konfiguracija bila
   ispravna. Sad je oba mjesta eksplicitno konzistentno.

## ⚠️ Iskreno o neizvjesnosti — ovo NIJE 100% garantovano

Ne mogu uživo testirati OpenAI Realtime API, pa moram biti transparentan:
- **Naziv modela `"whisper-1"`** je klasična, dugo-stabilna vrijednost za
  OpenAI transkripciju — ali ne mogu potvrditi da je to tačno ono što ova
  konkretna nested `audio.input.transcription.model` shema (relativno nov
  API oblik, glavni model je `gpt-realtime-2`) očekuje. Moguće je da treba
  noviji identifikator (npr. `gpt-4o-transcribe`/`gpt-4o-mini-transcribe`).
- Ako ovaj fix NE riješi problem, **prva stvar za provjeru je tačno ovo ime
  modela** — ne treba dalje kopati po `screenRef`/React logici, jer je ta
  strana koda već provjerena i strukturno ispravna.

## Verifikacija

- `node --check electron/ipc_handlers/realtime.cjs` — čisto.
- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- Runtime NIJE testiran (ne mogu) — ovo je čisto API-contract fix, potpuna
  potvrda dolazi samo iz stvarnog testa.

## Test koraci za korisnika

1. Uđi u aktivnu glasovnu sesiju, klikni "Diktiranje" dugme.
2. Izgovori rečenicu — **treba da se pojavi u textarea-i.**
3. Ako se pojavi: probaj i glasovni triger ("uđi u diktat mod" bez klika).
4. Ako se I DALJE ništa ne pojavljuje u textarea-i nakon koraka 2 — javi mi,
   to znači da `"whisper-1"` nije ispravan naziv modela za ovu API shemu i
   treba probati alternativu.

## Potreban follow-up

Ako fix ne uspije zbog pogrešnog naziva modela — nemam siguran način da
uživo provjerim tačnu vrijednost bez pristupa OpenAI dokumentaciji uživo ili
bez korisnikove pomoći (probati par kandidata dok jedan ne proradi, ili
korisnik provjeri u OpenAI Realtime dokumentaciji/dashboard-u).
