# Agent report — privremeni debug logovi za dictation/set_mode bug

**Datum:** 2026-07-10
**Povod:** umjesto da dalje nagađam (race condition teorija, prompt-tuning
teorija) korisnik je ispravno predložio: dodati stvarno logovanje da se vidi
tačan redoslijed događaja, pa tek onda praviti fix zasnovan na dokazu.

## Šta je dodato (privremeno, uklanja se nakon dijagnoze)

| Fajl | Log | Šta pokazuje |
|---|---|---|
| `electron/main.cjs` `handleToolsExecute` | `[DEBUG tool-call]` | SVAKI tool koji model pozove, sa tačnim argumentima i timestampom — vidjećemo da li i kad model zove `set_mode` |
| `src/lib/realtime.ts` `handleServerEvent` | `[DEBUG event]` | Tip svakog eventa sa Realtime API-ja (osim `.delta` spam eventa) sa timestampom — redoslijed kojim eventi stvarno stižu |
| `src/lib/realtime.ts` (transcription completed) | `[DEBUG transcription]` | Tačan transkribovan tekst korisnikovog govora, sa timestampom |
| `src/lib/realtime.ts` (response.done) | `[DEBUG response.done]` | Šta je Riki izgovorio + lista tool poziva koje je odlučio da izvrši, sa timestampom |
| `src/App.tsx` `onTranscript` | `[DEBUG onTranscript]` | Da li/kad renderer primi user transkript, koji je `screen` u tom trenutku |
| `src/App.tsx` `onMode` | `[DEBUG onMode]` | Kad se mod stvarno promijeni, i koliko ms je prošlo od zadnjeg "dikt" izgovora |

## Zašto ovo, ne dalje nagađanje

Imao sam dvije neprovjerene teorije (race condition između transkripcije i
modelove reakcije na sirovi audio; slaba prompt-instrukcija). Umjesto da
implementiram korektivni mehanizam zasnovan na pretpostavci, ovi logovi
direktno pokazuju: (a) da li se `set_mode` uopšte poziva i sa kojim
argumentima, (b) tačan redoslijed transkripcije vs. modelove odluke, (c) da
li moj "dikt" detektor uopšte vidi transkript prije nego model reaguje.

## Kako korisnik čita logove

1. **Renderer logovi** (`[DEBUG onTranscript]`, `[DEBUG onMode]`,
   `[DEBUG event]`, `[DEBUG transcription]`, `[DEBUG response.done]`) —
   otvoriti DevTools u app prozoru (Ctrl+Shift+I ili F12), tab "Console".
2. **Main proces logovi** (`[DEBUG tool-call]`) — vidljivi u **terminalu** gdje
   je pokrenut `npm run dev`, NE u DevTools konzoli (glavni proces i renderer
   su odvojeni procesi).
3. Reprodukovati bug (reći "uđi u diktat mod" glasom), pa kopirati sve linije
   koje sadrže `[DEBUG` iz oba mjesta (poredane po vremenu ako je moguće) i
   podijeliti nazad.

## Napomena

`lastDiktUtteranceAtRef` (u `App.tsx`) je dodat ranije kao dio nedovršenog
"race condition correction" pokušaja — trenutno se SAMO postavlja (u
`onTranscript`), ali se NIGDJE ne koristi za stvarnu korekciju. Namjerno
zaustavljeno na pola dok ne dobijemo dokaz iz logova; nije bug, samo
nedovršen/dormantan kod koji čeka odluku.

## Sljedeći korak

Nakon što korisnik podijeli logove, napraviti tačan fix (ne nagađati) i
ODMAH nakon toga ukloniti sve `[DEBUG ...]` console.log linije iz ovog
izvještaja — ovo NIJE za produkciju.
