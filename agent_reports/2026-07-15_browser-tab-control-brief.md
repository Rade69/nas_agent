# Brif za upravljanje browser tabovima

## Datum

2026-07-15

## Scope

Detaljan tehnički i sigurnosni brif za delegiranje implementacije pouzdanog brojanja, listanja, aktiviranja i zatvaranja Brave/Chrome tabova pi agentu.

## GitNexus impact

- Repo kontekst: 6656 simbola i 172 execution flowa.
- Konceptualni query je prijavio degradiran FTS indeks; pi agent mora osvježiti indeks prije implementacije ako upozorenje ostane.
- Direktni konteksti za `register_phase13_tools`, `ToolExecutor.execute` i `handleToolsExecute` potvrđuju postojeći Python tool/permission i Electron delegation tok.
- Izmjena root sekcije `docs/MIGRATION_PLAN.md`: LOW, bez pozivalaca ili pogođenih procesa.

## Šta je urađeno

- Dodat `docs/PI_BROWSER_TAB_CONTROL_BRIEF.md` sa arhitekturom ekstenzije, autentifikovanim localhost transportom, snapshot modelom, tool contractom, permission pravilima, fazama, test planom i acceptance kriterijima.
- Tracker je označio funkcionalnost kao planiranu, ne implementiranu.

## Zašto je urađeno

Postojeći `browser_open` može pokrenuti browser ili URL, ali ne može znati koliko postojećih tabova ima niti pouzdano aktivirati „peti tab“. Tastaturne prečice ne daju pouzdan inventar ni stabilan identitet tabova.

## Kako je urađeno

Brif preporučuje Brave/Chrome MV3 ekstenziju za `chrome.tabs` API i Python broker kao vlasnika validacije, snapshotova, autorizacije i audit logike. Redni brojevi su vezani za kratkotrajni snapshot da promjena redoslijeda ne bi aktivirala ili zatvorila pogrešan tab.

## Šta nije dirano

- Nije implementirana ekstenzija, broker niti novi agent alat.
- Nisu mijenjani runtime kod, permission engine ni Electron main logika.
- Nisu dirane postojeće tuđe worktree izmjene.

## Verifikacija

- Brif je upoređen sa postojećim `browser_open`, tool catalogom, Realtime specifikacijom i ToolExecutor tokom.
- GitNexus direktni kontekst i impact provjera su izvršeni.
- Dokumenti su pregledani sa `git diff --check` nakon izmjene.

## Rizici/ograničenja

Produkcijska distribucija ekstenzije i sigurno uparivanje su zasebno složeni dijelovi. Brif zato zahtijeva male PR faze i zabranjuje nepouzdani keyboard/UI Automation pristup kao izvor broja tabova.

## Potreban follow-up

PR 1 i PR 2 su naknadno implementirani od pi agenta i potvrđeni sa 31/31 ciljanih testova. Sljedeći follow-up je PR 3: potvrđeno zatvaranje, hardening, multi-window/incognito pravila i produkcijski packaging.

## Potrebna korisnička potvrda

Prije produkcijskog pakovanja odlučiti da li je prihvatljiv početni razvojni „Load unpacked“ način instalacije ekstenzije ili je odmah potreban automatizovan installer tok.
