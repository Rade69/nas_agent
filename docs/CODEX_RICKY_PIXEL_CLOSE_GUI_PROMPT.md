# CODEX PROMPT — Ricky GUI Pixel-Close Implementation from Approved Mockup

## Cilj

Implementiraj Ricky GUI tako da što preciznije prati odobreni mockup i njegove izdvojene cjeline:

```txt
Ricky-agent.png      -> kompletan odobreni mockup
GUI-SET-1.png        -> Idle / Spreman ekran
GUI-SET-2.png        -> Dictation Mode ekran
GUI-SET-3.png        -> Confirmation Modal
GUI-SET-4.png        -> Activity Drawer
GUI-SET-5.png        -> Plans Drawer
GUI-SET-6.png        -> donji principles/status/responsive footer blok
```

Ovo nije “inspiracija”.
Ovo nije samo promjena boja.
Ovo nije popravljanje starog ekrana.

Ovo je **precizan UI rebuild** prema mockupu.

---

# 1. Glavna naredba za Codex

```txt
Refaktoriši postojeći Ricky UI tako da strukturalno i vizuelno prati odobreni mockup.

Ne zadržavaj stari Home screen layout.
Ne zadržavaj stari plain R avatar.
Ne zadržavaj stari artifacts/debug panel u primarnom layoutu.
Ne prikazuj backend debug logove kao korisničku aktivnost.
Ne pravi generički chat UI.

Napravi state-based Ricky UI:
- Idle / Spreman
- Dictation Mode
- Confirmation Modal
- Activity Drawer
- Plans Drawer
```

---

# 2. Obavezno koristi branding assete

Asseti su pripremljeni u projektu na lokaciji:

```txt
assets/brending
```

Koristi ih direktno.

Najvažniji:

```txt
assets/brending/orb/ricky-orb-main.png
assets/brending/orb/ricky-orb-mini.png
assets/brending/orb/ricky-orb-idle.png
assets/brending/orb/ricky-orb-listening.png
assets/brending/orb/ricky-orb-speaking.png
assets/brending/orb/ricky-orb-thinking.png
assets/brending/orb/ricky-orb-warning.png
assets/brending/orb/ricky-orb-error.png

assets/brending/logo/ricky-logo-r.svg
assets/brending/logo/ricky-app-icon.png
assets/brending/logo/ricky-app-icon.ico
```

Ikonice koristi iz:

```txt
assets/brending/icons/navigation
assets/brending/icons/voice
assets/brending/icons/status
assets/brending/icons/safety
assets/brending/icons/actions
assets/brending/icons/window
assets/brending/icons/ui
assets/brending/icons/system
```

## Strogo zabranjeno

```txt
- ne koristiti emoji kao ikone
- ne koristiti random icon library ako asset postoji
- ne koristiti plain R u običnom krugu
- ne koristiti human avatar
- ne koristiti generički mikrofon kao Ricky identitet
```

Ricky identitet je:

```txt
stilizovano plavo R
+ glowing orb
+ voice-reactive ring
```

---

# 3. Vizuelni stil

Implementacija mora zadržati dark premium stil mockupa.

## Paleta

Koristi približne vrijednosti:

```css
--bg-main: #050A12;
--bg-shell: #07101B;
--bg-panel: #0B1422;
--bg-card: #0E1A2A;
--bg-card-soft: #101D2E;

--border-soft: rgba(80, 135, 190, 0.18);
--border-medium: rgba(94, 158, 220, 0.28);

--text-main: #F4F8FF;
--text-secondary: #A9B7C8;
--text-muted: #6F7F95;

--accent-blue: #168BFF;
--accent-cyan: #3AD7FF;
--accent-violet: #7C4DFF;

--success: #23D17D;
--warning: #F5A623;
--danger: #EF4444;
```

## Vizuelna pravila

```txt
- tamna pozadina
- suptilni gradienti
- rounded cards
- tanke linije
- plavi glow samo gdje treba
- ne pretjerivati sa neon efektima
- warning boja samo za rizik/potvrdu
- zeleni indikatori samo za uspjeh
```

---

# 4. Layout: globalni shell

Napravi glavni layout sa ovim zonama:

```txt
Top bar
Sidebar
Main content
```

## Preporučene mjere

Ne moraju biti 1:1 pixel-perfect, ali moraju biti vizuelno blizu mockupu.

```txt
App min width: 1280px
App ideal width: 1440–1600px
Top bar height: 56–64px
Sidebar width: 144–160px
Main content padding: 16–20px
Cards radius: 12–16px
Input/button radius: 10–14px
```

---

# 5. Top bar

Top bar u mockupu je tanak, čist i premium.

## Lijevo

```txt
[Ricky mini orb/logo] Ricky [status]
```

Primjeri statusa:

```txt
Spreman
Diktiranje
Čekam potvrdu
Greška
```

Koristi mali orb/logo iz:

```txt
assets/brending/logo/ricky-logo-r.svg
```

ili mali app icon:

```txt
assets/brending/logo/ricky-app-icon.png
```

## Desno

```txt
Computer mode: ISKLJUČEN
voice / utility icon
calendar / plan icon
settings icon
minimize
maximize
close
```

Koristi pripremljene ikonice.

## Pravilo

Nemoj status `Spreman/Slušam/Diktiranje` ponavljati na 3 mjesta. Top bar je glavni globalni status.

---

# 6. Sidebar

Sidebar mora ličiti na mockup.

## Stavke

```txt
Početna
Aktivnost
Planovi
Memorija
Snimci ekrana
Postavke
```

Koristi:

```txt
assets/brending/icons/navigation/icon-home.svg
assets/brending/icons/navigation/icon-activity.svg
assets/brending/icons/navigation/icon-plans.svg
assets/brending/icons/navigation/icon-memory.svg
assets/brending/icons/navigation/icon-screenshots.svg
assets/brending/icons/navigation/icon-settings.svg
```

## Dno sidebara

Prikazati:

```txt
Ricky v0.4.0
Backend: OK
Lokalno
```

Ne prikazivati raw paths, debug artifacts ili backend spam u sidebaru.

## Obavezno ukloniti iz starog UI-ja

Ako postoji:

```txt
ARTIFACTS
Screen Snapshot
C:\Users\...
```

u glavnom sidebaru / primarnom layoutu — ukloni iz primarnog ekrana.

Screenshotovi idu u `Snimci ekrana` ili Activity, ne kao ružan debug blok.

---

# 7. Idle / Spreman ekran — prema GUI-SET-1

Ovo je najvažniji početni ekran.

## Struktura

```txt
Main content:
  left/center: veliki Ricky orb
  ispod njega: naslov i subtitle
  ispod: mikrofon CTA
  ispod: tekstualni fallback input

  desno: Zadnja aktivnost card
  desno ispod: Brze komande card
```

## Centralni dio

Mora sadržati:

```txt
Ricky orb:
assets/brending/orb/ricky-orb-main.png

Naslov:
Ricky je spreman

Subtitle:
Klikni mikrofon ili reci "Ricky"

Mikrofon button:
okruglo, plavo, premium glow

Input:
placeholder "Upiši umjesto govora..."
send button na desnoj strani inputa
```

## Desni card: Zadnja aktivnost

Naslov:

```txt
Zadnja aktivnost
```

Link desno:

```txt
Prikaži sve
```

Primjeri stavki:

```txt
Email poslan šefu        12:47
Nacrt izvještaja spreman 12:35
Otvoren dictation mode   12:31
Screenshot snimljen      12:22
```

Ne smije stajati:

```txt
Backend ready
Backend ready
Backend ready
```

kao glavna korisnička aktivnost.

## Desni card: Brze komande

Naslov:

```txt
Brze komande
```

Stavke:

```txt
Napiši email šefu
Napravi screenshot
Otvori Notepad
Planiraj sastanak sutra u 10h
```

---

# 8. Dictation Mode — prema GUI-SET-2

Dictation mora biti zasebno stanje, ne dodatak starom Home screenu.

## Aktivacija

Kada je aktivan dictation mode, glavni content prelazi u editor-first layout.

## Header unutar contenta

```txt
DICTATION MODE
auto-čuvanje uključeno
Otkaži diktiranje X
```

## Editor

Veliki editor mora dominirati ekranom.

Primjer sadržaja:

```txt
Poštovani,

Molim vas da mi dostavite izvještaj o prodaji za prošli mjesec,
uključujući ukupne rezultate, poređenje sa prethodnim mjesecom
i ključne zaključke.

Hvala unaprijed.
```

Desno gore u editoru:

```txt
41 riječi
```

## Akcije

Lijevo ispod editora:

```txt
Nastavi diktiranje
Doradi ▼
...
```

Doradi dropdown:

```txt
Formalizuj
Skrati
Provjeri pravopis
Prevedi na engleski
```

Desno:

```txt
Pošalji agentu
```

## Pravila

```txt
- editor je glavni fokus
- ne prikazivati desne idle cardove dok je editor u fokusu
- ne držati Activity/Plans stalno otvorene
- ne koristiti Notepad
```

---

# 9. Confirmation Modal — prema GUI-SET-3

Confirmation je najvažniji safety UI element.

## Mora biti modal

Ne smije biti:

```txt
mali banner
footer card
sporedni panel
```

Mora biti:

```txt
centralni modal
sa zatamnjenom/blurovanom pozadinom
vizuelno neizbježan
```

## Modal sadržaj

Naslov:

```txt
Ricky želi izvršiti ovu akciju
```

Subtitle:

```txt
Pažljivo provjeri detalje prije potvrde.
```

Tabela:

```txt
Akcija    Pošalji email
Prima     sef@firma.com
Predmet   Izvještaj o prodaji za prošli mjesec
Rizik     SREDNJI · ističe za 02:00
```

Link:

```txt
Prikaži cijeli sadržaj emaila ▼
```

Dugmad:

```txt
Izmijeni
Otkaži
Pošalji email
```

## Vizuelno

```txt
Warning ikona lijevo
Orange/yellow samo za rizik/potvrdu
Primary action može biti orange ili blue, ali rizik mora ostati jasan
```

---

# 10. Activity Drawer — prema GUI-SET-4

Activity može biti drawer ili panel.

## Sadržaj

Naslov:

```txt
Aktivnost
```

Zatvori dugme:

```txt
X
```

Stavke:

```txt
Email poslan šefu
sef@firma.com
12:47

Nacrt izvještaja spreman
41 riječi
12:35

Otvoren dictation mode
Auto-čuvanje uključeno
12:31

Screenshot snimljen
ekran_2025-07-06_12-22.png
12:22

Alat izvršen
Otvori aplikaciju: Notepad
12:20
```

Dugme:

```txt
Prikaži cijelu historiju
```

## Pravila

Activity mora prikazivati korisnički smislene događaje, ne backend debug logove.

---

# 11. Plans Drawer — prema GUI-SET-5

## Sadržaj

Naslov:

```txt
Planovi
```

Tabs:

```txt
Aktivni
Predloženi
Završeni
```

Plan cards:

```txt
Sedmični izvještaj prodaje
Svakog petka u 14:00
AKTIVAN

Podsjetnik: Sastanak tim
Sutra u 10:00
AKTIVAN

Analiza konkurencije
Rok: 10.07.2025
NA ČEKANJU
```

Dugme:

```txt
Novi plan
```

---

# 12. Footer / principles block — prema GUI-SET-6

Ovaj blok je dio mockupa kao dokumentacioni / demo blok, ali u produkcijskom UI-ju ne mora stalno biti prikazan.

Ako se implementira kao dev/demo screen, neka izgleda kao u mockupu.

Sekcije:

```txt
STATUS INDIKATORI
KLJUČNI PRINCIPI PRIMIJENJENI
RESPONSIVE PRAVILA
mini orb preview
```

## Važno

U production Home ekranu ovaj blok ne mora biti stalno vidljiv.

Ako ga implementiraš, stavi ga kao demo/dev section ili documentation panel, ne kao glavnu funkcionalnu zonu.

---

# 13. Ricky Orb animacija

Koristi plan iz:

```txt
RICKY_ORB_ANIMATION_PLAN.md
```

Osnovno:

```txt
idle       -> soft breathe
listening  -> aktivniji pulse
thinking   -> spor glow
speaking   -> voice ring pulse
warning    -> blagi warning ring
error      -> kratki red pulse
muted      -> smanjena opacity / bez animacije
```

Komponente:

```txt
RickyOrb.tsx
RickyOrb.css
CompanionOrb.tsx
mapVoiceStateToOrbState()
```

Ako ne možeš odmah potpuno animirati, prvo ispravno postavi asset `ricky-orb-main.png`, pa dodaj CSS ring animaciju.

---

# 14. Component proposal

Možeš napraviti strukturu ovako:

```txt
src/
  components/
    layout/
      AppShell.tsx
      TopBar.tsx
      Sidebar.tsx

    ricky/
      RickyOrb.tsx
      RickyOrb.css
      VoiceInputBar.tsx
      IdleScreen.tsx
      DictationScreen.tsx
      ConfirmationModal.tsx
      ActivityDrawer.tsx
      PlansDrawer.tsx

    ui/
      Button.tsx
      Card.tsx
      Badge.tsx
      Icon.tsx
```

Ako postoje postojeće komponente, refaktoriši ih ali ne zadržavaj stari layout ako se kosi sa mockupom.

---

# 15. State model

Minimalni UI state:

```ts
type RickyScreenState =
  | "idle"
  | "dictation"
  | "confirmation";

type DrawerState =
  | null
  | "activity"
  | "plans"
  | "settings"
  | "memory"
  | "screens";

type VoiceState =
  | "idle"
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "waiting_confirmation"
  | "muted"
  | "error";
```

Render pravilo:

```txt
screenState === "idle"         -> IdleScreen
screenState === "dictation"    -> DictationScreen
screenState === "confirmation" -> prethodni screen u backgroundu + ConfirmationModal
drawer === "activity"          -> ActivityDrawer
drawer === "plans"             -> PlansDrawer
```

---

# 16. Najvažnije zabrane

Codex NE SMIJE:

```txt
1. Samo prebojiti stari UI.
2. Ostaviti plain R avatar.
3. Ostaviti artifacts/debug panel na početnom ekranu.
4. Prikazivati Backend ready spam kao korisničku aktivnost.
5. Koristiti Notepad kao UI za draft/transkript.
6. Koristiti generičke ikonice ako postoje assets/brending ikonice.
7. Pretvoriti UI u obični chat.
8. Sakriti orb ili ga svesti na malu dekoraciju.
9. Ostaviti veliki prazan prostor bez hijerarhije.
10. Napraviti confirmation kao mali banner.
```

---

# 17. Acceptance criteria

## Idle screen

Prihvatljivo samo ako:

```txt
- vizuelno liči na GUI-SET-1
- veliki Ricky orb je centralni fokus
- sidebar je čist
- desni cardovi su prisutni
- text input je ispod glavnog voice CTA
- nema starog artifacts/debug panela
```

## Dictation mode

Prihvatljivo samo ako:

```txt
- vizuelno liči na GUI-SET-2
- editor je dominantan
- postoji DICTATION MODE badge
- postoji auto-save status
- postoji Pošalji agentu dugme
- Doradi dropdown ima opcije
```

## Confirmation modal

Prihvatljivo samo ako:

```txt
- vizuelno liči na GUI-SET-3
- modal je centralan i dominantan
- background je zatamnjen/blurovan
- detalji akcije su jasni
- postoje Izmijeni / Otkaži / Pošalji email
```

## Activity drawer

Prihvatljivo samo ako:

```txt
- vizuelno liči na GUI-SET-4
- prikazuje smislene korisničke događaje
- ne prikazuje backend debug spam
```

## Plans drawer

Prihvatljivo samo ako:

```txt
- vizuelno liči na GUI-SET-5
- ima tabs Aktivni / Predloženi / Završeni
- plan cards su uredni
```

## Branding

Prihvatljivo samo ako:

```txt
- koristi ricky-orb-main.png
- koristi ricky-logo-r.svg ili app icon u headeru
- ne koristi plain R circle
- koristi assets/brending ikonice
```

---

# 18. Finalni zadatak

Implementiraj UI tako da kada se uporedi sa mockup segmentima:

```txt
GUI-SET-1
GUI-SET-2
GUI-SET-3
GUI-SET-4
GUI-SET-5
GUI-SET-6
```

bude jasno da je prava aplikacija nastala direktno iz tog mockupa.

Ako nakon izmjena aplikacija i dalje izgleda kao stari layout sa malo promijenjenom temom, task nije završen.

Cilj je:

```txt
maksimalno identičan GUI agent prema odobrenom mockupu
uz korištenje pripremljenih brending asseta
i state-based UX strukture
```
