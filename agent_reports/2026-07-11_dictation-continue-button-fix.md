# Agent report — "Nastavi diktiranje" dugme (funkcija + vizuelni stil)

**Datum:** 2026-07-11
**Povod:** korisnik potvrdio da glavni dictation mehanizam sad radi (glasovni
triger, latinica, dosljedan tekst) — prijavio dva manja preostala problema:
"Nastavi diktiranje" dugme ne radi ništa, i dugmad (Nastavi diktiranje/
Doradi/...) vizuelno se ne razlikuju od običnog teksta.

## 1. Funkcionalni fix

**Uzrok:** `<button className="pixel-secondary"><IconMic /> Nastavi
diktiranje</button>` nikad nije imao `onClick` — čisto dekorativno dugme od
kad je UI redesign spec prvi put predvidio ovu akciju.

**Popravka:** novi `onContinue` prop kroz `DictationScreen` →
`PixelMockupBoard` → `App.tsx`. Pošto je hvatanje teksta već kontinuirano
dok je ekran na "dictation" (Faza 1), jedina realna praznina je: ako je
glas prekinut (mic idle timeout, ručni Stop), nema aktivne sesije koja bilo
šta hvata. Dugme sad: ako je povezano — ponovo potvrdi dictation mode
(`setDictationMode(true)`) + zapiše aktivnost ("Diktiranje nastavljeno") da
klik uvijek daje vidljivu potvrdu; ako NIJE povezano — ponovo se poveže pa
onda potvrdi dictation mode.

## 2. Vizuelni fix

**Uzrok:** `.pixel-secondary` (klasa koju dijele "Nastavi diktiranje",
"Doradi ▾", "..." — potvrđeno grep-om, koristi se ISKLJUČIVO u
`DictationScreen.tsx`) je imala providan border (`opacity 0.17`) i
pozadinu skoro identičnu okolnom panelu — vizuelno neразличива od teksta.

**Popravka:** jača, vidljivija border boja (`opacity 0.4`, `0.7` na hover),
svjetlija plavičasta pozadina, `cursor: pointer` + hover prelaz. Dirana
samo baza klase — nema uticaja van dictation ekrana (jedini korisnik klase).

## Namjerno van scope-a (ostaje)

"Doradi ▾" podmeni (Formalizuj/Skrati/Provjeri pravopis/Prevedi) i "..."
dugme i dalje nisu funkcionalno ožičeni — korisnik ih nije prijavio kao
testirane/pokvarene, samo je vizuelni fix zatražen za sve zajedno (sad
pokriveno, jer dijele istu CSS klasu). Ožičavanje njihove stvarne funkcije
(pošalji tekst modelu sa instrukcijom, zamijeni sadržaj) ostaje zaseban,
manji zadatak za kasnije — dobar kandidat za pi delegaciju.

## Verifikacija

- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- Runtime NIJE testiran (potreban korisnički test).

## Test za korisnika

1. Uđi u diktat, izdiktiraj nešto, zatim pritisni Stop/sačekaj da glas
   otpadne — klikni "Nastavi diktiranje" — treba da se ponovo poveže i
   nastaviš diktirati.
2. Dok je glas i dalje aktivan, klikni "Nastavi diktiranje" — treba se
   pojaviti kratka potvrda u Aktivnosti ("Diktiranje nastavljeno").
3. Provjeri vizuelno da "Nastavi diktiranje"/"Doradi"/"..." sad jasno
   izgledaju kao dugmad (border, pozadina, hover efekat).

## Potrebna korisnička potvrda

Runtime test obavezan prije commita.
