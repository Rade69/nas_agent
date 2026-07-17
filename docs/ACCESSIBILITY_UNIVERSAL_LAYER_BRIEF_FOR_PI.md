# Accessibility — Univerzalni (always-on) sloj — brief za pi agenta

**Datum:** 2026-07-14
**Namjena:** implementacioni brief za pi agenta
**Status ulaza:** Audit završen (`docs/ACCESSIBILITY_AUDIT_2026-07-14.md`,
commit `dc327d5`). Ovaj brief izdvaja SAMO "always-on" podskup — tri stvari
koje su neophodne slijepima I korisne svima, i koje se isporučuju UKLJUČENE
po defaultu (nisu iza prekidača).
**Recenzent:** Claude Code radi detaljan pregled svake faze. Optimizuj za
čitljiv, izolovan diff po fazi.

---

## 0. Kratki cilj

Aplikacija je voice-first, ali mnoge stvari radi/pada **tiho i samo vizuelno**.
Cilj: agent **nikad ne djeluje niti ne pada u tišini** — kaže šta je uradio,
u kom je stanju, i kad mu treba odluka, tako da to čuje i screen reader i
korisnik koji ne gleda u ekran.

Tri stvari, tri faze:

- **A1 — čitljivo, objavljeno stanje** (ARIA live region za status/greške).
- **A2 — potvrde koje se ne mogu propustiti** (focus + objava u ConfirmationDialog).
- **A3 — izgovoren ishod** (system prompt: kratka rečenica o ishodu vizuelne akcije).

Ovo NIJE puna pristupačnost. Verbozni opisi, high-contrast tema, skaliranje
teksta, gašenje animacija — sve to je BUDUĆI, ZASEBAN, OPT-IN "Accessibility
Mode" i **nije u obimu ovog briefa**.

---

## 1. Zašto "always-on", ne opt-in

Odluka projekta (vidi memoriju/audit): pristupačnost ima dvije klase.
1. **Nevidljiva higijena** — semantički HTML, ARIA labeli, focus management,
   live regions. **Ništa ne mijenja za korisnika koji vidi**, screen reader
   samo radi bolje. Uvijek uključeno, nikad iza prekidača. **Ovaj brief je
   tačno taj podskup.**
2. **Ponašajni/vizuelni sloj** — verbozni opisi, high-contrast, veći tekst.
   Mijenja iskustvo svima → opt-in, isključeno po defaultu. **Van ovog briefa.**

Granica za A3 (izgovoren ishod) je najosjetljivija: **jedna kratka rečenica o
ISHODU je always-on** (pomaže svima u voice-first aplikaciji); **verbozni opis
svakog vizuelnog detalja / čitanje cijelih tabela naglas NIJE** — to je opt-in,
buduće. Ne prelaziti tu granicu.

---

## 2. KRITIČNO: multi-agent kolizija

Ovaj rad dodiruje fajlove na kojima aktivno rade DVA druga toka:

- **pi (ti) sam** — voice reliability epic (R0-R3, `src/lib/realtime.ts`,
  `src/App.tsx`) i browser-tab kontrola. Status stringovi, connection state,
  error klasifikacija koje A1 treba **već postoje** iz tvog R1-R3 rada — A1
  ih samo **objavljuje screen readeru**, ne izmišlja nove.
- **Claude Code** — upravo commitovan email Faza B koji je dodao u
  `ConfirmationDialog.tsx`: `isEmailDraftConfirmation`, `confirmation.emailNeverSent`
  poruku, i `confirmation.prepareDraft` labelu. **NE SMIJEŠ revertovati ni
  izmijeniti tu logiku** — A2 dodaje focus/objavu OKO postojećeg, ne dira
  email granu.

Obavezno prije ijednog edita:
```powershell
git status --short
git log -5 --oneline
git diff -- src/lib/realtime.ts src/App.tsx src/components/ConfirmationDialog.tsx electron/ipc_handlers/realtime.cjs
```
Re-čitati SVJEŽE (ne keširano) prije izmjene: `src/App.tsx`,
`src/components/ConfirmationDialog.tsx`, `src/components/pixel/MiniComputerWindow.tsx`,
`electron/ipc_handlers/realtime.cjs`. Ako je working tree prljav sa tuđim
necommitovanim izmjenama u tim fajlovima — STANI i prijavi vlasništvo prije
rada. Ne brisati i ne prepisivati tuđe promjene. Zabranjeni su `git reset --hard`,
`git checkout --`.

GitNexus: prije izmjene svakog postojećeg simbola (`App.tsx:App`,
`ConfirmationDialog`, bilo šta u `realtime.ts`) pokreni
`gitnexus_impact(target, direction:"upstream")`. Za HIGH/CRITICAL — stani,
prijavi blast radius, čekaj. Prije commita `gitnexus_detect_changes`.

---

## 3. Šta pi NE smije raditi

- Ne implementirati opt-in stvari (verbozni opis, high-contrast, text scaling,
  reduced-motion) — to je van obima.
- Ne mijenjati email granu u `ConfirmationDialog.tsx` niti bilo šta u
  `email_*` alatima.
- Ne dirati browser-tab rad.
- Ne mijenjati voice state mašinu, reconnect, tool lifecycle iz R1-R3 osim
  da PROČITA postojeće stanje/status i objavi ga.
- Ne slabiti bezbjednosne osobine ConfirmationDialog-a (vidi sekciju 8).
- Ne mijenjati OpenAI session payload.
- Ne dodavati novu dependency (ovo je čist React/ARIA + prompt rad).
- Ne commitovati bez eksplicitne korisničke dozvole.
- Ne prelaziti iz jedne faze u sljedeću bez novog pregleda/odobrenja.

---

## 4. Faza A1 — čitljivo, objavljeno stanje (ARIA live region)

### Problem
Grep kroz cijelu aplikaciju: **samo 1 live region** (kill-switch, `App.tsx:649`).
Voice state, connection state, "alat traje", "čekam potvrdu", greške — sve je
vizuelni tekst BEZ `aria-live`. Screen reader ne čuje promjene stanja. (Ovo
je i frustracija koju je korisnik već imao: "backend error", zbunjenost oko
moda/mikrofona.)

### Zadatak
Jedna dijeljena, uvijek prisutna live-region komponenta u koju se preusmjerava
statusni tekst koji VEĆ postoji.

- Nova komponenta, npr. `src/components/StatusAnnouncer.tsx`:
  - `<div role="status" aria-live="polite" aria-atomic="true">` za normalna
    stanja (connecting, listening, thinking, tool running, reconnecting).
  - Odvojen `<div role="alert" aria-live="assertive">` za hitno:
    `waiting_confirmation`, `error`, reconnect-failed.
  - Vizuelno skriveno ali dostupno screen readeru (klasa tipa `.sr-only`:
    `position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0)`
    — NE `display:none` i NE `visibility:hidden`, jer to skriva i od AT).
- Montirati u `App.tsx` na top nivo, uvijek prisutno.
- Napajati ga iz POSTOJEĆIH izvora — `voiceStateLabel(voiceState)`,
  `onStatus` string, connection state, reconnect status iz R2. Ne izmišljati
  nove izvore istine; samo ih provući kroz announcer.
- Debounce/dedupe: ne objavljivati isti string dvaput zaredom (screen reader
  bi ponovio); objaviti samo na stvarnu promjenu.

### Acceptance
- Announcer element postoji u DOM-u uvijek (i kad je stanje "idle").
- Promjena voice/connection stanja upisuje novi tekst u `polite` region.
- `waiting_confirmation` i `error`/reconnect-failed idu u `assertive` region.
- Isti uzastopni tekst se ne upisuje dvaput.
- Vizuelno se NIŠTA ne mijenja za korisnika koji vidi (sr-only).

### Testovi
- Unit/component test: render sa datim voiceState/status → očekivani tekst u
  odgovarajućem regionu; ista vrijednost dvaput → jedan upis.
- Ručno (NVDA, sekcija 7): povezivanje, "alat traje", greška se ČUJU.

---

## 5. Faza A2 — potvrde koje se ne mogu propustiti

### Problem
`ConfirmationDialog.tsx` ima `role="dialog"`/`aria-modal`/`aria-label`, ali:
ne pomjera fokus na sebe pri otvaranju, nema focus trap, nema Escape, i ne
objavljuje se — screen reader korisnik možda NE SAZNA da se pojavio. Korisnik
je već pogodio srodni problem: potvrda nevidljiva u Computer Mode mini prozoru.

### Zadatak (bez diranja email/bezbjednosne logike)
- Pri otvaranju (pending), pomjeri fokus **u dijalog** — na sam kontejner
  (`tabIndex={-1}` + `ref.focus()`) ili na **dugme Odbij/Otkaži**, NIKAD na
  Odobri (vidi sekciju 8 — Odobri mora ostati namjeran).
- Focus trap: Tab/Shift+Tab kruži unutar dijaloga dok je otvoren; fokus ne
  bježi u pozadinu.
- `Escape` = isto što i Odbij/Otkaži (sigurna, ne-destruktivna akcija).
- Objava sadržaja: dijalog treba `aria-labelledby`/`aria-describedby` koji
  pokrivaju action_name + risk + (za email) postojeću "neće poslati" poruku,
  tako da screen reader pročita ŠTA se potvrđuje čim se fokus pomjeri.
- Po zatvaranju, vrati fokus na element koji ga je imao prije (restore focus).
- Isti tretman za confirmation karticu u `MiniComputerWindow.tsx` (Claude je
  dodao karticu ranije; treba isti focus+objava obrazac, bez diranja njene
  postojeće logike).

### Acceptance
- Otvaranje pending potvrde pomjeri fokus u dijalog (NE na Odobri).
- Tab ne izlazi iz dijaloga dok je otvoren.
- Escape odbija/otkazuje (ne odobrava).
- Screen reader pročita action_name + risk (+ email napomenu) pri otvaranju.
- Zatvaranje vrati fokus na prethodni element.
- 250ms "armed" delay, single-use semantika, i email grana — **nepromijenjeni**.

### Testovi
- Component test: mount pending → `document.activeElement` je unutar dijaloga
  i NIJE Odobri dugme; Escape poziva onReject/onCancel; Tab ostaje unutra.
- Regresija: email `isEmailDraftConfirmation`/`emailNeverSent`/`prepareDraft`
  i dalje rade (postojeći/novi test).
- Ručno (NVDA): potvrda se ČUJE i pročita kad se pojavi.

---

## 6. Faza A3 — izgovoren ishod (system prompt)

### Problem
`electron/ipc_handlers/realtime.cjs` `buildRickyInstructions`:
- Linija ~58 doslovno: *"When a thumbnail finishes generating or editing, do
  not announce it verbally. The UI updates silently."* → za slijepe je to zid.
- Sekcija `# Artifacts` kaže da KORISTI artifacts, ali nikad da OPIŠE ishod.
- Linija ~62 već ima *"Explain what you are doing in one short sentence before
  longer tool work"* — dobra osnova, ali samo za NAJAVU, ne za ishod.

### Zadatak (prompt-only, minimalno, koordinisano)
- Zamijeniti "do not announce it verbally / UI updates silently" instrukciju
  tako da model **kratko izgovori ISHOD svake vizuelne akcije** (jedna
  rečenica): npr. "Gotovo — prikazao sam tabelu sa N unosa", "Thumbnail #20 je
  spreman", "Prikazao sam grafikon toka".
- Eksplicitno OGRANIČITI: **jedna kratka rečenica o ishodu**, NE verbozni opis,
  NE čitanje cijelog sadržaja tabele/teksta naglas. (Ta granica je ključna —
  puni opis je budući opt-in, ne ovo.)
- Ne dirati email instrukcije (Claude ih je upravo dodao) niti thumbnail
  numeraciju — samo "silent" → "kratko reci ishod" izmjena.
- Zadržati "Do not over-explain" duh — kratko, ne esej.

### Acceptance
- Prompt više ne kaže modelu da šuti nakon vizuelne akcije.
- Prompt eksplicitno traži jednu kratku rečenicu o ishodu, i eksplicitno
  zabranjuje verbozni/potpuni opis.
- Email i thumbnail instrukcije netaknute.
- `node --check electron/ipc_handlers/realtime.cjs` čisto.

### Testovi
- Prompt se ne unit-testira; verifikacija je `node --check` + ručni glasovni
  test (korisnik/recenzent): zatraži nešto vizuelno, potvrdi da Ricky KRATKO
  kaže ishod (ne ćuti, ne drži predavanje).

---

## 7. Ručni NVDA smoke matrix (obavezno prije "gotovo")

NVDA je besplatan (Windows). Recenzent/korisnik provjerava:
1. Pokretanje glasa — čuje se "povezujem se" / "spreman".
2. Alat koji traje — čuje se "alat traje" umjesto tišine.
3. Greška (npr. backend nedostupan) — čuje se greška, ne tišina.
4. Potvrda se pojavi — fokus uđe u dijalog, sadržaj se pročita.
5. Escape na potvrdi — odbija, ne odobrava.
6. Tab u potvrdi — ne izlazi iz dijaloga.
7. Zatvaranje potvrde — fokus se vrati.
8. Email potvrda — i dalje kaže "Pripremi draft" + "neće poslati" (regresija).
9. Vizuelna akcija (npr. prikaži tabelu/thumbnail) — Ricky KRATKO izgovori
   ishod.
10. Korisnik koji VIDI — ne primjećuje nikakvu vizuelnu promjenu (sr-only
    announcer, isti dijalog izgled).

---

## 8. Bezbjednosne napomene (ne narušiti)

- ConfirmationDialog "armed" 250ms delay (S-4/S-30) i single-use potvrde
  (S-04) ostaju NETAKNUTI. Focus management ne smije zaobići namjernost:
  **nikad ne auto-fokusirati Odobri dugme** i nikad ne dozvoliti da Enter na
  novootvorenom dijalogu odobri akciju. Fokus ide na kontejner ili na Odbij.
- Escape mapira na sigurnu akciju (odbij/otkaži), nikad na odobri.
- Live region ne smije objavljivati osjetljiv sadržaj (npr. puni email body,
  putanje, tokene) — samo stanje/status/naziv akcije. Isti redakcijski duh
  kao diagnostics iz voice reliability R0.
- A3 prompt izmjena ne smije natjerati model da naglas čita osjetljiv vizuelni
  sadržaj (npr. sadržaj screenshota) — "kratka rečenica o ishodu", ne sadržaj.

---

## 9. i18n

Sve nove korisniku-vidljive/objavljene stringove (announcer poruke, aria
labeli) dodati u svih 5 locale fajlova (`src/i18n/locales/{sr-Latn,en,de,es,fr}.json`).
Srpska latinica je autoritativna; ostali best-effort uz napomenu u reportu.
Announcer treba koristiti postojeće `voiceStateLabel`/status stringove gdje
već postoje, ne duplirati.

## 10. Verifikacija (po fazi)

```powershell
npm.cmd run test:voice   # ako dodaješ component testove ovdje
npm.cmd run typecheck
npm.cmd run build
node --check electron/ipc_handlers/realtime.cjs   # za A3
```
Prije commita: `git diff --check`, `git status --short`, `git diff --stat`,
pa `gitnexus_detect_changes`. U reportu odvojiti SVOJ diff od tuđeg prljavog
tree-a.

## 11. Report + stop

Za svaku fazu: `agent_reports/YYYY-MM-DD_a11y-universal-aN-slug.md` po
CLAUDE.md obrascu (Datum, Scope, GitNexus impact, Šta/Zašto/Kako, Šta nije
dirano, Verifikacija, Rizici, Follow-up, Korisnička potvrda).

Nakon svake faze: prikaži diff/stat, rezultate testova, GitNexus nalaz,
razdvajanje tuđih izmjena — pa **STANI i čekaj pregled (Claude Code) + novu
dozvolu**. Ne prelaziti na sljedeću fazu automatski. Ne commitovati bez
eksplicitne korisničke dozvole.

## 12. Preporučeni redoslijed

A1 (najizolovaniji, additivan, flagship) → pregled → A2 (jedna komponenta,
bezbjednosno osjetljivo) → pregled → A3 (prompt, najmanji ali kolizija sa
email/thumbnail promptom) → pregled. Ne spajati faze u jedan commit.

---

## 13. Ready-to-paste početni prompt za pi

```text
Radiš na RileyJarvis Windows Hybrid repo-u. Realizuješ
docs/ACCESSIBILITY_UNIVERSAL_LAYER_BRIEF_FOR_PI.md — ISKLJUČIVO Fazu A1 za sada.

Prvo pročitaj: AGENTS.md, CLAUDE.md, taj brief, i
docs/ACCESSIBILITY_AUDIT_2026-07-14.md.

Prije ijednog edita: git status --short, git log -5 --oneline, i git diff nad
src/lib/realtime.ts, src/App.tsx, src/components/ConfirmationDialog.tsx. Shared
tree koriste drugi agenti (Claude Code je upravo commitovao email rad u
ConfirmationDialog; ne diraj email granu). Ne briši i ne prepisuj tuđe promjene.

Ovo je "always-on" pristupačnost — NE opt-in. Ne implementiraj verbozne opise,
high-contrast, text scaling — to je van obima.

Radi SAMO A1: dijeljena ARIA live-region komponenta (sr-only) koja objavljuje
POSTOJEĆE voice/connection/status stringove screen readeru. Ne izmišljaj nove
izvore stanja. Vizuelno se ništa ne smije promijeniti.

Prije izmjene App.tsx pokreni GitNexus upstream impact. Dodaj component testove,
i18n u 5 locale-a, agent report. Na kraju prikaži diff/testove/impact i STANI —
Claude Code pregleda prije A2. Ne commituj bez dozvole.
```
