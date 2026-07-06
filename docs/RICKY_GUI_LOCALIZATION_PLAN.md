# Ricky Assistant — GUI Localization Plan

## Svrha

Ovaj dokument definiše prijedlog lokalizacije GUI-ja za Ricky Assistant.

Važno: ovo se odnosi samo na **tekstove u grafičkom interfejsu**.

Ne odnosi se na:

```txt
- OpenAI Realtime voice model,
- STT prepoznavanje jezika,
- TTS glas,
- automatsko prevođenje korisničkih dokumenata,
- jezik kojim agent odgovara u razgovoru.
```

Glasovni model može sam prepoznavati jezike. Ovaj plan služi da korisnik može izabrati jezik interfejsa, npr. njemački, španski, francuski ili srpski latinica, i da cijeli GUI prikaže tekstove na tom jeziku.

---

# Osnovna odluka

GUI lokalizacija treba biti uvedena odmah u ranoj UI implementaciji.

Razlog:

```txt
Ako se i18n uvede odmah:
- lako je dodavati nove jezike,
- komponente ostaju čiste,
- nema kasnijeg ručnog traženja hardkodiranih tekstova.

Ako se ostavi za kasnije:
- UI će imati mnogo hardkodiranih stringova,
- refaktor će biti spor,
- lako će ostati neprevedeni dijelovi,
- Activity/Plans/Settings tekstovi će postati neuredni.
```

Ovo nije veliki feature. Ovo je **UI engineering rule**.

---

# Podržani jezici za MVP

Početni jezici:

```txt
sr-Latn  Serbian Latin / Srpski latinica
en       English
de       Deutsch / Njemački
es       Español / Španski
fr       Français / Francuski
```

Iako korisnik posebno traži srpski latinica, njemački, španski i francuski, preporuka je da `en` ostane kao fallback/base jezik jer:

```txt
- trenutni UI tekstovi su vjerovatno već na engleskom,
- mnogi tool nazivi i developer termini su engleski,
- lakše je imati stabilan fallback ako prevod nedostaje.
```

Default može biti:

```txt
sr-Latn
```

ili:

```txt
en
```

Preporuka za tvoju upotrebu:

```txt
default interface_language = sr-Latn
fallback language = en
```

---

# Tehnički pristup

Preporučeni pristup za React/Electron UI:

```txt
react-i18next / i18next
```

Predložena struktura:

```txt
src/
  i18n/
    index.ts
    locales/
      sr-Latn.json
      en.json
      de.json
      es.json
      fr.json
```

Alternativno, ako se ne želi odmah uvoditi biblioteka, može se napraviti mali interni translation helper. Ipak, preporuka je koristiti standardni i18n alat jer će projekat rasti.

---

# Settings model

U settings dodati:

```json
{
  "interface_language": "sr-Latn"
}
```

Dozvoljene vrijednosti:

```txt
sr-Latn
en
de
es
fr
```

U UI dodati:

```txt
Settings → Language / Jezik
```

Prikaz opcija:

```txt
Srpski latinica
English
Deutsch
Español
Français
```

Kada korisnik promijeni jezik, GUI bi idealno trebalo da se promijeni odmah, bez restartovanja aplikacije.

Ako je to komplikovano u prvoj verziji, prihvatljivo je:

```txt
Promjena jezika će se primijeniti nakon restartovanja aplikacije.
```

Ali dugoročno je bolje da se primijeni odmah.

---

# interface_language kao STT jezički hint (Dictation Mode)

> Dodatak (2026-07-06). `interface_language` ne treba biti samo prevod GUI teksta — treba biti i signal lokalnom STT engine-u (vidi Dictation/Voice Draft Mode u `RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md` sekciji G) koji jezik/pismo da očekuje. Ovo NIJE prevođenje govora (transcript i dalje ostaje ono što je korisnik stvarno rekao, po pravilu iz sekcije "Transcript language rule" ispod) — samo jezička/pismovna pretpostavka za tačniju transkripciju.

## Zašto je ovo potrebno — stvaran nalaz, ne teorija

Ručni test (`whisper-test/whisper_bcs_test.py`, faster-whisper `medium`, auto-detect jezika) je pokazao da isti engine, u istoj sesiji, može transkribovati srpski **naizmjenično na latinici i na ćirilici** — jedna rečenica latinicom, sljedeća ćirilicom, bez ikakve promjene na strani korisnika. Pošto je "srpski latinica" eksplicitan standard u ovom projektu (vidi UI stringove, `sr-Latn` kod), ovo je stvaran problem koji auto-detect ne rješava sam od sebe.

## Pravilo

```txt
interface_language se prosljeđuje STT engine-u kao language hint pri Dictation Mode pozivu,
ne samo i18n translation loader-u.
```

Predloženo mapiranje (faster-whisper jezički kodovi):

```txt
sr-Latn → "bs" (bosanski je u Whisper-u latinica-only, izbjegava se ćirilica/latinica kockanje
           za jugoslovenske jezike koji su međusobno visoko razumljivi)
en      → "en"
de      → "de"
es      → "es"
fr      → "fr"
```

Ako se ipak koristi `language="sr"` (npr. za bolju pokrivenost specifično srpskog rječnika) i engine svejedno vrati ćirilicu, dodati **transliteraciju ćirilica→latinica kao sigurnosnu mrežu** prije nego što tekst uđe u Voice Draft panel — ovo je deterministički, jednostavan mapping tabele karaktera, ne zahtijeva ML.

## Šta ostaje nepromijenjeno

```txt
- Transcript i dalje pokazuje ono što je korisnik rekao (nema silent prevoda sadržaja).
- interface_language i dalje odvojeno kontroliše GUI labele (postojeće pravilo iznad).
- Ako korisnik promijeni jezik u Settings, to mijenja i STT hint za SLJEDEĆU dictation sesiju,
  ne retroaktivno već sačuvane transkripte.
```

## Acceptance criteria

```txt
- Dictation Mode poziva STT sa language hint-om izvedenim iz interface_language, ne auto-detect.
- Srpski latinica ostaje latinica u transkriptu, konzistentno, ne naizmjenično sa ćirilicom.
- Promjena jezika u Settings mijenja STT hint bez potrebe za redizajnom cijelog voice pipeline-a.
```

---

# Ključno pravilo

Ne hardkodirati user-facing tekstove u komponentama.

Zabranjeno:

```tsx
<h1>No output yet</h1>
<button>Take screenshot</button>
<span>Computer Mode: OFF</span>
```

Dozvoljeno:

```tsx
<h1>{t("output.emptyTitle")}</h1>
<button>{t("actions.takeScreenshot")}</button>
<span>{t("computerMode.off")}</span>
```

Pravilo za agente:

```txt
No hardcoded user-facing strings.
All visible GUI text must use i18n translation keys.
```

---

# Šta se lokalizuje

Lokalizovati sve što korisnik vidi u GUI-ju:

```txt
- top bar,
- status badges,
- voice states,
- bottom voice bar,
- dugmad,
- tabovi,
- empty states,
- confirmation dialog,
- settings,
- tool descriptions,
- risk labels,
- error messages,
- Activity prikaz,
- Plans prikaz,
- Review Packet UI labels,
- Companion orb menu,
- tooltips.
```

Ne moraju se lokalizovati interni identifikatori:

```txt
screen_snapshot
computer_type_text
voice.state_changed
confirmation.required
tool.started
```

Interni nazivi ostaju stabilni i jezički nezavisni.

UI može prikazati prevedeni label, ali zadržati interni key.

Primjer:

```json
{
  "tool.screen_snapshot.label": "Snimanje ekrana",
  "tool.screen_snapshot.description": "Napravi screenshot trenutnog desktopa"
}
```

Interni naziv ostaje:

```txt
screen_snapshot
```

---

# VoiceState lokalizacija

Interni enum ostaje isti:

```ts
type VoiceState =
  | "idle"
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "waiting_confirmation"
  | "interrupted"
  | "muted"
  | "error";
```

UI prikaz se prevodi.

Primjer keys:

```json
{
  "voice.state.idle": "Ready",
  "voice.state.listening": "Listening...",
  "voice.state.transcribing": "Transcribing...",
  "voice.state.thinking": "Thinking...",
  "voice.state.speaking": "Speaking...",
  "voice.state.waiting_confirmation": "Waiting for confirmation",
  "voice.state.interrupted": "Interrupted",
  "voice.state.muted": "Muted",
  "voice.state.error": "Error"
}
```

---

# Activity log lokalizacija

Activity log ne smije čuvati samo prevedeni tekst.

Bolje:

```json
{
  "id": "evt_001",
  "type": "tool.started",
  "tool": "screen_snapshot",
  "timestamp": "2026-07-05T12:44:00Z",
  "status": "running"
}
```

UI onda prevodi prikaz.

Primjer:

```txt
en: Screenshot started
sr-Latn: Snimanje ekrana pokrenuto
de: Screenshot gestartet
es: Captura de pantalla iniciada
fr: Capture d’écran démarrée
```

Pravilo:

```txt
Baza čuva structured event.
UI prevodi event display.
```

To omogućava da korisnik promijeni jezik i stari activity log se prikaže na novom jeziku.

---

# Plans / Proposals lokalizacija

Planovi se takođe čuvaju kao struktura.

Primjer:

```json
{
  "id": "plan_001",
  "title_key": "plan.open_app_and_type.title",
  "status": "pending_approval",
  "steps": [
    {
      "type": "open_app",
      "app": "notepad.exe"
    },
    {
      "type": "type_text",
      "target": "active_window"
    }
  ]
}
```

UI prevodi generičke dijelove:

```txt
Ricky predlaže ove korake
Risk: HIGH
Target: notepad.exe
Cancel / Run
```

Ali korisnički sadržaj ostaje kakav jeste.

Primjer:

```txt
User text:
"Pošalji poruku Milanu"
```

Ne prevoditi automatski korisnikov originalni tekst bez eksplicitnog zahtjeva.

---

# Review Packet i dokumenti

Za Document/Paperwork Engine razlikovati:

```txt
interface_language
output_language
source_language
```

Primjer:

```json
{
  "interface_language": "sr-Latn",
  "output_language": "sr-Latn",
  "source_language": "de"
}
```

Pravila:

```txt
- GUI prati interface_language.
- Review Packet summary prati output_language.
- Izvorni citati ostaju na originalnom jeziku.
- Ako se citat prevodi, mora biti označeno da je prevod.
```

Primjer:

```txt
Original citation:
"Der Antrag muss innerhalb von 14 Tagen eingereicht werden."

Prevod:
"Zahtjev mora biti predat u roku od 14 dana."

UI mora jasno razlikovati original i prevod.
```

---

# Predloženi translation keys

## App / top bar

```json
{
  "app.title": "Ricky Assistant",
  "app.settings": "Settings",
  "app.companion": "Companion",
  "app.close": "Close",
  "app.minimize": "Minimize",
  "app.maximize": "Maximize"
}
```

## Backend

```json
{
  "backend.connected": "Python backend connected",
  "backend.disconnected": "Python backend disconnected",
  "backend.starting": "Python backend starting",
  "backend.error": "Python backend error"
}
```

## Computer mode

```json
{
  "computerMode.label": "Computer Mode",
  "computerMode.on": "ON",
  "computerMode.off": "OFF",
  "computerMode.enable": "Enable Computer Mode",
  "computerMode.disable": "Disable Computer Mode",
  "computerMode.warning": "Computer Mode allows Ricky to interact with your computer."
}
```

## Voice

```json
{
  "voice.center": "Voice Center",
  "voice.ready": "Ready",
  "voice.holdToTalk": "Hold to talk",
  "voice.releaseToSend": "Release to send",
  "voice.tapToSpeak": "Tap to speak",
  "voice.stop": "Stop",
  "voice.mute": "Mute",
  "voice.unmute": "Unmute",
  "voice.microphoneOn": "Microphone on",
  "voice.microphoneOff": "Microphone off",
  "voice.whatRickyHeard": "What Ricky heard",
  "voice.currentStep": "Current step",
  "voice.recentActivity": "Recent voice activity"
}
```

## Tabs

```json
{
  "tabs.output": "Output",
  "tabs.activity": "Activity",
  "tabs.plans": "Plans",
  "tabs.memory": "Memory",
  "tabs.screens": "Screens"
}
```

## Output

```json
{
  "output.emptyTitle": "No output yet",
  "output.emptySubtitle": "Ask Ricky something by voice or use text as a fallback.",
  "output.askByVoice": "Ask Ricky by voice",
  "output.typeInstead": "Type instead..."
}
```

## Actions

```json
{
  "actions.screenshot": "Screenshot",
  "actions.inspectUi": "Inspect UI",
  "actions.openApp": "Open App",
  "actions.newNote": "New Note",
  "actions.more": "More",
  "actions.cancel": "Cancel",
  "actions.run": "Run",
  "actions.confirm": "Confirm",
  "actions.reject": "Reject",
  "actions.save": "Save",
  "actions.export": "Export"
}
```

## Risk

```json
{
  "risk.low": "Low",
  "risk.medium": "Medium",
  "risk.high": "High",
  "risk.critical": "Critical",
  "risk.confirmationRequired": "Confirmation required",
  "risk.blocked": "Blocked"
}
```

## Security / privacy

```json
{
  "security.localAndPrivate": "Local & Private",
  "security.noDataLeavesDevice": "No data leaves your device",
  "privacy.localOnly": "Local only",
  "privacy.redactedCloud": "Redacted cloud",
  "privacy.cloudAllowed": "Cloud allowed",
  "privacy.askEachTime": "Ask each time"
}
```

---

# Primjer sr-Latn prevoda

```json
{
  "app.title": "Ricky Assistant",
  "app.settings": "Podešavanja",
  "app.companion": "Companion",
  "app.close": "Zatvori",
  "app.minimize": "Minimizuj",
  "app.maximize": "Maksimizuj",

  "backend.connected": "Python backend povezan",
  "backend.disconnected": "Python backend nije povezan",
  "backend.starting": "Python backend se pokreće",
  "backend.error": "Greška u Python backendu",

  "computerMode.label": "Computer Mode",
  "computerMode.on": "UKLJUČEN",
  "computerMode.off": "ISKLJUČEN",
  "computerMode.enable": "Uključi Computer Mode",
  "computerMode.disable": "Isključi Computer Mode",
  "computerMode.warning": "Computer Mode dozvoljava Ricky-ju da upravlja računarom.",

  "voice.center": "Glasovni centar",
  "voice.ready": "Spreman",
  "voice.holdToTalk": "Drži za govor",
  "voice.releaseToSend": "Pusti za slanje",
  "voice.tapToSpeak": "Dodirni za govor",
  "voice.stop": "Zaustavi",
  "voice.mute": "Utišaj",
  "voice.unmute": "Uključi zvuk",
  "voice.microphoneOn": "Mikrofon uključen",
  "voice.microphoneOff": "Mikrofon isključen",
  "voice.whatRickyHeard": "Šta je Ricky čuo",
  "voice.currentStep": "Trenutni korak",
  "voice.recentActivity": "Nedavna glasovna aktivnost",

  "tabs.output": "Rezultat",
  "tabs.activity": "Aktivnost",
  "tabs.plans": "Planovi",
  "tabs.memory": "Memorija",
  "tabs.screens": "Ekrani",

  "output.emptyTitle": "Još nema rezultata",
  "output.emptySubtitle": "Pitaj Ricky-ja glasom ili koristi tekst kao rezervnu opciju.",
  "output.askByVoice": "Pitaj Ricky-ja glasom",
  "output.typeInstead": "Kucaj umjesto toga...",

  "actions.screenshot": "Screenshot",
  "actions.inspectUi": "Pregled UI-ja",
  "actions.openApp": "Otvori aplikaciju",
  "actions.newNote": "Nova bilješka",
  "actions.more": "Više",
  "actions.cancel": "Otkaži",
  "actions.run": "Pokreni",
  "actions.confirm": "Potvrdi",
  "actions.reject": "Odbij",
  "actions.save": "Sačuvaj",
  "actions.export": "Export",

  "risk.low": "Nizak",
  "risk.medium": "Srednji",
  "risk.high": "Visok",
  "risk.critical": "Kritičan",
  "risk.confirmationRequired": "Potvrda je potrebna",
  "risk.blocked": "Blokirano",

  "security.localAndPrivate": "Lokalno i privatno",
  "security.noDataLeavesDevice": "Podaci ne napuštaju uređaj",
  "privacy.localOnly": "Samo lokalno",
  "privacy.redactedCloud": "Redigovano u cloud",
  "privacy.cloudAllowed": "Cloud dozvoljen",
  "privacy.askEachTime": "Pitaj svaki put"
}
```

---

# Primjer de prevoda

```json
{
  "voice.ready": "Bereit",
  "voice.holdToTalk": "Zum Sprechen halten",
  "voice.stop": "Stopp",
  "voice.mute": "Stummschalten",
  "tabs.output": "Ausgabe",
  "tabs.activity": "Aktivität",
  "tabs.plans": "Pläne",
  "tabs.memory": "Speicher",
  "tabs.screens": "Bildschirmfotos",
  "output.emptyTitle": "Noch keine Ausgabe",
  "output.emptySubtitle": "Frage Ricky per Sprache oder nutze Text als Alternative.",
  "actions.screenshot": "Screenshot",
  "actions.inspectUi": "UI prüfen",
  "actions.openApp": "App öffnen",
  "actions.newNote": "Neue Notiz",
  "actions.cancel": "Abbrechen",
  "actions.run": "Ausführen",
  "risk.confirmationRequired": "Bestätigung erforderlich"
}
```

---

# Primjer es prevoda

```json
{
  "voice.ready": "Listo",
  "voice.holdToTalk": "Mantén para hablar",
  "voice.stop": "Detener",
  "voice.mute": "Silenciar",
  "tabs.output": "Resultado",
  "tabs.activity": "Actividad",
  "tabs.plans": "Planes",
  "tabs.memory": "Memoria",
  "tabs.screens": "Pantallas",
  "output.emptyTitle": "Aún no hay resultados",
  "output.emptySubtitle": "Pregunta a Ricky por voz o usa texto como alternativa.",
  "actions.screenshot": "Captura de pantalla",
  "actions.inspectUi": "Inspeccionar UI",
  "actions.openApp": "Abrir aplicación",
  "actions.newNote": "Nueva nota",
  "actions.cancel": "Cancelar",
  "actions.run": "Ejecutar",
  "risk.confirmationRequired": "Confirmación requerida"
}
```

---

# Primjer fr prevoda

```json
{
  "voice.ready": "Prêt",
  "voice.holdToTalk": "Maintenir pour parler",
  "voice.stop": "Arrêter",
  "voice.mute": "Muet",
  "tabs.output": "Résultat",
  "tabs.activity": "Activité",
  "tabs.plans": "Plans",
  "tabs.memory": "Mémoire",
  "tabs.screens": "Écrans",
  "output.emptyTitle": "Aucun résultat pour le moment",
  "output.emptySubtitle": "Demandez à Ricky par la voix ou utilisez le texte comme alternative.",
  "actions.screenshot": "Capture d’écran",
  "actions.inspectUi": "Inspecter l’interface",
  "actions.openApp": "Ouvrir l’application",
  "actions.newNote": "Nouvelle note",
  "actions.cancel": "Annuler",
  "actions.run": "Exécuter",
  "risk.confirmationRequired": "Confirmation requise"
}
```

---

# Lokalizacija Companion menija

Companion menu takođe mora koristiti i18n.

Keys:

```json
{
  "companion.openRicky": "Open Ricky",
  "companion.holdToTalk": "Hold to talk",
  "companion.stop": "Stop",
  "companion.mute": "Mute",
  "companion.unmute": "Unmute",
  "companion.takeScreenshot": "Take screenshot",
  "companion.inspectUi": "Inspect UI",
  "companion.computerMode": "Computer Mode",
  "companion.settings": "Settings",
  "companion.quit": "Quit"
}
```

---

# Lokalizacija error poruka

Error poruke moraju biti lokalizovane.

Ali detaljni tehnički error može ostati na engleskom u diagnostics/dev mode.

Primjer:

```json
{
  "error.backendDisconnected": "Python backend is disconnected.",
  "error.microphoneUnavailable": "Microphone is not available.",
  "error.permissionDenied": "Permission denied.",
  "error.actionBlocked": "This action was blocked for safety.",
  "error.confirmationExpired": "Confirmation expired."
}
```

UI prikazuje prevedeno.

Diagnostics može prikazati:

```txt
Raw error: ECONNREFUSED 127.0.0.1:48931
```

---

# Formatiranje datuma, vremena i brojeva

Ne prevoditi ručno datume i brojeve.

Koristiti `Intl`.

Primjeri:

```ts
new Intl.DateTimeFormat(language).format(date)
new Intl.NumberFormat(language).format(amount)
new Intl.NumberFormat(language, {
  style: "currency",
  currency: "EUR"
}).format(value)
```

Napomena:

```txt
Jezik interfejsa nije uvijek isto što i valuta.
```

Zato currency treba biti posebno podešavanje ili dolaziti iz podataka.

---

# Fallback pravilo

Ako prevod nedostaje:

```txt
1. koristi en
2. ako nema en, prikaži translation key u dev mode
3. u production prikaži razumljiv fallback
```

Primjer:

```txt
Missing key: voice.holdToTalk
```

U dev mode može biti korisno da se vidi key.

U production ne smije izgledati slomljeno.

---

# Testing checklist

Za svaki novi UI ekran provjeriti:

```txt
- nema hardkodiranih user-facing stringova,
- svi tekstovi se mijenjaju promjenom jezika,
- njemački duži tekst ne lomi layout,
- francuski akcenti se prikazuju ispravno,
- španski znakovi se prikazuju ispravno,
- srpska latinica sa čćžšđ radi ispravno,
- dugmad ne pucaju zbog dužine teksta,
- tooltipovi su prevedeni,
- confirmation dialog je preveden,
- error poruke su prevedene,
- Activity display koristi structured events,
- Companion menu je preveden.
```

Posebno testirati njemački jer često ima duže riječi.

---

# Agent implementation instruction

Dodati u UI/agent prompt:

```txt
Implement GUI localization foundation.

Supported interface languages:
- sr-Latn
- en
- de
- es
- fr

Rules:
1. No hardcoded user-facing strings.
2. Use i18n translation keys for all visible GUI text.
3. Store selected language in settings as interface_language.
4. English is fallback language.
5. Serbian Latin can be default for the user.
6. Activity events must be stored as structured events, not only translated strings.
7. Tool internal names stay stable; UI labels/descriptions are translated.
8. Review Packet source citations remain in original language.
9. Use Intl for dates, times, numbers and currencies.
10. Companion menu and confirmation dialogs must also be localized.

Do not modify OpenAI Realtime voice language handling in this task.
This task is only GUI localization.
```

---

# Suggested first implementation step

```txt
Localization PR-1:
- install/configure i18next/react-i18next or equivalent
- create src/i18n/index.ts
- create locale JSON files:
  sr-Latn.json
  en.json
  de.json
  es.json
  fr.json
- add interface_language setting
- localize TopBar, BottomVoiceBar and main workspace tabs
- add language selector in Settings
```

Second step:

```txt
Localization PR-2:
- localize Voice Center
- localize Output empty state
- localize Activity display
- localize Plans/Approval dialog
- localize Companion menu
```

Third step:

```txt
Localization PR-3:
- localize tool labels/descriptions
- localize risk labels
- localize error messages
- add missing translation checks
- add layout tests for German/French/Spanish/Srpski
```

---

# Zaključak

GUI lokalizacija nije kompleksna ako se uvede odmah.

Procjena:

```txt
Samo GUI localization foundation: 3/10
GUI + Activity structured events: 5/10
GUI + Plans/Review Packet localization: 6/10
```

Najvažnije pravilo:

```txt
Ne hardkodirati tekst u komponentama.
```

Ako se to ispoštuje od početka, dodavanje novih jezika kasnije postaje jednostavno.
