# Agent report — opcioni Smart Home/IoT/Camera dodatak

## Datum

2026-07-13

## Scope

Detaljno istraživanje mogućnosti proširenja RileyJarvis/Naš-agent sistema opcionalnim dodatkom za Home Assistant, IoT uređaje i nadzorne kamere, izrada faznog plana koji ostaje izvan osnovnog paketa te naknadna dopuna iskrenom poslovnom `NO-GO` procjenom za trenutni trenutak.

## GitNexus impact

GitNexus indeks je prije analize prijavio da je jedan commit iza HEAD-a. Pokrenut je `npx.cmd gitnexus analyze`; osvježavanje je završeno sa 5.733 čvora, 8.725 veza, 136 clustera i 152 flowa. Nisu mijenjani kodni simboli ni execution flowovi — dodani su samo dokumentacioni fajlovi, pa symbol impact analiza nije primjenjiva.

## Šta je urađeno

- Provjerena je trenutna Electron → Python → tool registry/permission/event arhitektura.
- Provjereni su packaging, settings, action-log i event-bus obrasci.
- Istraženi su zvanični Home Assistant REST, WebSocket, auth, permissions, camera, Matter, MQTT i ONVIF izvori.
- Istraženi su OASIS MQTT 5 sigurnosni zahtjevi, ONVIF profili/deprecation, Windows Credential Locker/DPAPI i NIST IoT baseline.
- Definisan je opcioni sidecar model koji nije uključen u osnovni installer.
- Definisani su capability katalog, risk matrica, dvostruki policy gate, camera privacy model, voice/accessibility pravila, threat model, faze, procjene, testovi i acceptance kriteriji.
- Plan je dopunjen poslovnom odlukom „ne implementirati sada“, razlozima, `GO` kriterijima, ograničenim proof-of-concept scopeom i pravilom prioriteta osnovnog proizvoda.
- Kreiran je `docs/OPTIONAL_SMART_HOME_IOT_CAMERA_ADDON_PLAN.md`.

## Zašto je urađeno

Direktna integracija svakog Matter, MQTT i ONVIF uređaja bila bi prevelika i sigurnosno skupa za osnovni paket. Home Assistant kao lokalni gateway smanjuje broj protokola i kredencijala koje Ricky mora posjedovati, dok zaseban sidecar odvaja tajne, mrežne zavisnosti i release ciklus od osnovne aplikacije. Naknadna poslovna procjena dodana je da tehnički detaljan plan ne bi bio pogrešno protumačen kao preporuka da se razvoj započne prije stabilizacije osnovnog proizvoda i validacije potražnje.

## Kako je urađeno

Zaključci su zasnovani na svježem source pregledu i zvaničnim izvorima. Plan koristi postojeći `ToolExecutor` kao prvi gate, ali predlaže nezavisni sidecar policy kao drugi gate. Model dobija samo opaque reference i uske toolove, nikada generic Home Assistant service/MQTT/ONVIF pristup.

## Šta nije dirano

- Nije mijenjan Python, Electron, React ili CSS kod.
- Nije mijenjan `docs/MIGRATION_PLAN.md` jer opcioni dodatak nije dio aktivnog osnovnog trackera i nije implementiran.
- Nisu mijenjani postojeći planovi i izvještaji.
- Nisu dirane nekomitovane izmjene drugih agenata.
- Nije napravljen commit.

## Verifikacija

- Novi dokumenti su potvrđeni na očekivanim putanjama.
- Provjerena je Markdown hijerarhija: 22 glavne sekcije i SH-0 do SH-10 faze.
- Dokument sadrži 18 jedinstvenih linkova ka zvaničnim Home Assistant, OASIS, CSA, ONVIF, Microsoft i NIST izvorima.
- Provjereno je postojanje svih relevantnih lokalnih arhitektonskih fajlova.
- `git diff --check` nije prijavio grešku u novim dokumentima; prikazao je samo postojeća CRLF/LF upozorenja za tuđe izmjene `AGENTS.md` i `CLAUDE.md`.
- Završni `git status` potvrđuje da implementacioni fajlovi nisu mijenjani i da GitNexus refresh nije dodao repo fajlove.
- Kodni testovi nisu potrebni jer implementacija nije mijenjana.

## Rizici/ograničenja

- Procjene su radni raspon za solo developera, ne kalendarsko obećanje.
- Stvarni Home Assistant i hardware-in-the-loop testovi nisu izvedeni u ovom dokumentacionom zadatku.
- Home Assistant integracije i pojedini uređaji imaju različite capabilityje; adapter mora raditi fail-closed.
- OAuth desktop onboarding zahtijeva poseban spike; long-lived token je prihvatljiv samo za ograničeni prototip.

## Potreban follow-up

- Ne započinjati implementaciju u trenutnom osnovnom-product ciklusu.
- Završiti i stabilizovati osnovni Ricky, zatim prikupiti stvarne zahtjeve i spremnost korisnika/partnera da plate ili finansiraju dodatak.
- Ponovo otvoriti plan tek kada se ispuni najmanje jedan snažan `GO` signal, idealno dva ili više.
- Ako je potreban demo za grant/partnera, ograničiti ga na vremenski definisan Home Assistant read-only proof-of-concept.
- Tek nakon `GO` odluke potvrditi Home Assistant-only MVP, sidecar packaging, SH-0 scope i podržanu HA verziju.
- Prije budućih kodnih izmjena uraditi GitNexus impact analizu svakog mijenjanog simbola.

## Potrebna korisnička potvrda

Trenutna preporuka je dokumentovana kao `NO-GO`: sačuvati dodatak kao budući epic, ne implementirati ga sada i vratiti mu se samo uz potvrđenu potražnju, finansiranje ili partnerstvo.
