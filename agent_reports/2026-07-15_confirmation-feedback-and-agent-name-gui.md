# Confirmation feedback i ime agenta u GUI-ju

## Datum

2026-07-15

## Scope

Popravka povratne informacije poslije odobrenog confirmation retryja i trenutno prikazivanje sačuvanog imena agenta iznad mikrofona.

## GitNexus impact

- `RickyRealtimeClient`: MEDIUM, 12 direktnih importera, jedan glavni `App` execution flow.
- `handleApproveConfirmation`, `PixelMockupBoard`, `IdleScreen`, `SettingsPanel`: LOW.
- Izmjena je ograničena na renderer confirmation/GUI tok; Electron main i Python permission engine nisu mijenjani.

## Šta je urađeno

- Dodat `RickyRealtimeClient.notifyConfirmationResult()` koji aktivnoj Realtime sesiji šalje strukturiran uspjeh/neuspjeh odobrenog retryja i traži novi odgovor modela.
- `App.tsx` poziva bridge i za uspješan rezultat i za izuzetak tokom retryja.
- `App.tsx` učitava `agent_name`, čuva ga u state-u i prosljeđuje idle ekranu.
- `SettingsPanel` nakon uspješnog čuvanja odmah javlja novo ime roditelju, bez restarta aplikacije.
- Lokalizovani `idle.ready` tekstovi koriste `{{agentName}}` interpolaciju.
- Dodat renderer test za post-approval Realtime obavijest.

## Zašto je urađeno

UI je izvršavao odobreni tool retry direktno, ali njegov rezultat nije vraćao modelu, pa je agent ostajao u uvjerenju da još čeka potvrdu. Ime agenta je bilo sačuvano u backendu i korišteno u promptu, ali centralni GUI naslov je ostao hardkodiran na Ricky.

## Kako je urađeno

Post-approval ishod se šalje kao interni, jasno označen conversation event sa minimalnim poljima (`tool_name`, `approved`, `execution_ok`, opcioni `error_code`), bez prosljeđivanja proizvoljnog tool sadržaja. GUI koristi postojeći React prop/state lanac.

## Šta nije dirano

- Permission i confirmation single-use pravila.
- Python backend i Electron IPC.
- Postojeće tuđe izmjene u `AGENTS.md`, `CLAUDE.md` i `src/styles/12-pixel-board.css`.

## Verifikacija

- `npm run typecheck` — prošlo.
- `npm run test:voice -- src/lib/__tests__/realtimeClient.test.ts` — 42/42 prošlo.
- `npm run build` — prošlo; samo postojeće upozorenje o velikim Vite chunkovima.

## Rizici/ograničenja

Realtime API nema poseban renderer-side system-event helper, pa se događaj šalje kao jasno označena interna tekstualna stavka korisničke uloge. Sadržaj je strogo strukturiran i ne uključuje proizvoljan rezultat alata.

## Potreban follow-up

Poželjna je ručna smoke provjera u pokrenutoj Electron aplikaciji: otvaranje browsera nakon potvrde i promjena imena kroz Settings.

## Dopuna: Computer Mode mini prozor

Naknadni live test je pokazao da prvi bridge nije pokrivao odobrenje kliknuto u zasebnom Computer Mode mini `BrowserWindow` rendereru: retry se izvršio tamo, ali je aktivni Realtime klijent ostao u skrivenom glavnom rendereru. Dodan je named IPC tok `confirmations:retry-result` (mini → Electron main → main renderer). Glavni renderer sada jedini šalje ishod aktivnoj Realtime sesiji, uz eksplicitnu instrukciju modelu da korisniku potvrdi da je klik na Odobri primljen i zatim kaže ishod akcije. `npm run check`, typecheck, 42 Realtime testa i build su prošli.

## Potrebna korisnička potvrda

Vizuelno potvrditi da se novo ime odmah vidi iznad mikrofona i da agent glasom potvrđuje rezultat odobrene akcije.
