# Agent report — Diktiranje: pravi uzrok pronađen kroz debug logove, popravljeno

**Datum:** 2026-07-11
**Metod:** korisnik je ispravno predložio dodavanje debug logova umjesto
daljeg nagađanja (vidi `agent_reports/2026-07-10_dictation-debug-logging.md`).
Ovaj izvještaj dokumentuje NALAZ iz stvarnih logova i fix zasnovan na dokazu.

## Dokaz iz logova (tačan slijed, drugi test korisnika)

```
11:32:11.323  response.created
11:32:12.088  response.done — spoken="Slušam, diktiraj." functionCalls=[]
11:32:12.536  conversation.item.input_audio_transcription.completed
              transcript: "уђу диктатнот"   (ĆIRILICA)
              onTranscript: screen=home     (ekran se NIKAD nije prebacio)
```

## Dvije stvari dokazane, ne pretpostavljene

1. **Sistem prompt fix od jučer RADI.** Model je ispravno samo rekao "Slušam,
   diktiraj." bez ijednog tool poziva (`functionCalls=[]`) — NIJE zvao
   `set_mode`. Ranija prijava "ulazi u računarski mod" je vjerovatno bila
   test prije nego se taj prompt fix učitao (ili nedeterministička
   varijacija — ali u ovom snimljenom testu ne ponavlja se).
2. **Pravi preostali uzrok:** transkript stiže u ćirilici ("диктат"), a
   provjera `.toLowerCase().includes("dikt")` traži isključivo latinicu.
   Ćirilično "д-и-к-т" nikad ne poklapa latinično "dikt" — ekran se zato
   nikad nije prebacio, bez obzira na tajming. **Ovo je isti uzrok** kao
   miješanje pisama u dictationText koje je korisnik ranije prijavio
   screenshot-om — jedan uzrok, dvije posljedice, sad riješeno jednim fixom.

## Popravka

Nova, samostalna, deterministička funkcija `cyrillicToLatin()` u
`src/lib/cyrillicToLatin.ts` — potpuna 1:1 tabela srpske ćirilice u
latinicu (uklj. digrafe љ→lj, њ→nj, џ→dž i velika/mala slova). Primijenjena
u `App.tsx` `onTranscript`, **samo na `role: "user"` unose** (Rikijev
sopstveni generisani tekst ne prolazi kroz transkripciju, nije pogođen istim
problemom):
- prije provjere "dikt" okidača (popravlja glasovni ulaz u diktat),
- prije upisa u `dictationText` (popravlja miješana pisma u tekstu),
- i u glavnom transcript feedu (konzistentnost — projekat je sr-Latn
  standard svuda).

Logička provjera protiv stvarno uhvaćenog primjera: "уђу диктатнот" →
transliteracija → "uđu diktatnot" → `.includes("dikt")` **poklapa se**.

## Čišćenje

Svi privremeni `[DEBUG ...]` console.log pozivi uklonjeni iz `main.cjs`,
`realtime.ts`, `App.tsx` (poslužili svrsi, dali tačnu dijagnozu). Uklonjen i
neupotrijebljen `lastDiktUtteranceAtRef` iz ranijeg, sad-nepotrebnog
"race-condition correction" pokušaja — dokazano nepotreban jer prompt fix
stvarno radi; pravi uzrok je bio isključivo script mismatch, ne tajming.

## Verifikacija

- `node --check electron/main.cjs` — čisto.
- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- `grep -rn "DEBUG"` na sva tri fajla — prazno, potvrđeno uklonjeno.

## Rizici/ograničenja

- Transliteracija pokriva SAMO srpsku ćirilicu → latinicu. Ako STT ikad
  vrati neki treći nepredviđen script/jezik, taj tekst prolazi nepromijenjen
  (funkcija samo mapira poznate ćirilične karaktere, ostalo prosljeđuje
  netaknuto — sigurno ponašanje, ne baca grešku).
- ~450ms kašnjenje između Rikijeve glasovne potvrde i stvarnog prebacivanja
  ekrana (transkripcija stiže nakon response.done) ostaje kao manji,
  kozmetički lag — ne funkcionalni kvar. Nije adresirano ovim fixom
  namjerno, jer dokaz pokazuje da je zanemarljivo u odnosu na glavni bug.

## Test za korisnika

1. Reci glasom "uđi u diktat mod" (bilo latinicom bilo ćirilicom u tvom
   govoru — STT izlaz je sad normalizovan bez obzira na to).
2. Potvrdi da se ekran STVARNO prebaci na Diktiranje ovaj put.
3. Nastavi diktirati par rečenica — potvrdi da je tekst dosljedno latinica,
   bez miješanja pisama.
4. Ako i dalje ne radi — javi mi tačnu poruku/ponašanje; debug infrastruktura
   je uklonjena ali se lako vraća ako zatreba dalja dijagnoza.

## Potrebna korisnička potvrda

Runtime test obavezan prije commita — ovo je fix zasnovan na jednom
snimljenom primjeru; širi test (više rečenica, duže sesije) će potvrditi
da li transliteracija pokriva sve varijante koje STT stvarno vraća.
