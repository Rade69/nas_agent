# Precizno otvaranje browsera

## Datum

2026-07-15

## Scope

Namjenski, sigurni Python alat za pouzdano otvaranje podrazumijevanog ili izabranog web browsera, opciono na tačnoj HTTP(S) adresi.

## GitNexus impact

- `register_phase13_tools`: LOW.
- Realtime `toolSpecs`: LOW.
- `ToolExecutor.execute`: LOW, jedan direktni API pozivalac.
- `handleToolsExecute`: LOW.
- Nema HIGH/CRITICAL rizika.

## Šta je urađeno

- Dodat `browser_open` sa izborom `default`, `brave`, `chrome`, `edge` ili `firefox`.
- Fonetski glasovni oblik `brejv` prihvata se u tool contractu i normalizuje na `brave`; modelov opis eksplicitno objašnjava mapiranje „Brejv“ → Brave.
- Brave se pronalazi preko PATH-a i standardnih `BraveSoftware/Brave-Browser/Application` lokacija u LocalAppData i Program Files direktorijima.
- URL je opcioni i mora biti apsolutni `http://` ili `https://`, bez ugrađenih kredencijala.
- Specifični browseri se pronalaze preko PATH-a i poznatih Windows install lokacija, zatim pokreću sa listom argumenata i `shell=False`.
- Dodati strukturirani rezultati (`browser`, `url`, `launch_accepted`, `process_started`, `process_id`) i greške `BROWSER_NOT_INSTALLED`, `BROWSER_OPEN_FAILED`, `BROWSER_UNAVAILABLE`.
- `ToolExecutor` sada pravilno pretvara `AppError` iz handlera u standardni tool error odgovor.
- Realtime tool opis nalaže modelu da browsere otvara kroz `browser_open`, a ne `computer_open_app`.
- Electron delegacija prosljeđuje novi alat Python backendu.

## Zašto je urađeno

Generički `computer_open_app` se oslanjao na kratke alias nazive i nije razlikovao otvaranje praznog browsera od navigacije na URL. Nije imao precizan kod za neinstaliran browser niti namjenski model contract.

## Kako je urađeno

Implementacija je izdvojena u `app/tools/system/browser.py`; model-controlled vrijednosti nikad ne postaju shell komanda. Browser je enum, a URL prolazi eksplicitnu provjeru scheme/netloc/credentials prije OS poziva.

## Šta nije dirano

- Postojeći legacy PowerShell alati.
- Permission/confirmation pravila; `browser_open` ostaje medium-risk i zahtijeva Computer Mode, a postojeća external-content eskalacija i dalje može tražiti potvrdu.
- Postojeće tuđe worktree izmjene.

## Verifikacija

- Novi backend testovi: 7/7 prošlo, uključujući izvršenje `brejv` aliasa kao Brave.
- FAZA 13 regresioni testovi: 60/60 prošlo.
- Realtime renderer testovi: 42/42 prošlo.
- `npm run check`, `npm run typecheck`, `npm run build`: prošlo.

## Rizici/ograničenja

`process_started=true` potvrđuje da je Windows prihvatio pokretanje konkretnog executable-a; browser može odmah proslijediti zahtjev već postojećem procesu i ugasiti pomoćni proces. Za default browser Windows/Python handler ne vraća PID, pa je `process_started=null`, a `launch_accepted=true`.

## Potreban follow-up

Ručni smoke test u aplikaciji: "otvori Brave pregledač", "otvori Brejv", "otvori default browser" i "otvori Edge na https://example.com".

## Potrebna korisnička potvrda

Potvrditi da se željeni browser i URL otvaraju na ciljnom Windows računaru.
