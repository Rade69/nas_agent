# Agent report — Renderer XSS-sink audit (READ-ONLY)

**Datum:** 2026-07-09
**Tip:** READ-ONLY audit. Nijedan fajl koda nije mijenjan.

## Scope

Audit cijelog `src/**` na prisustvo HTML ponora (XSS sink-ova) — mjesta gdje
potencijalno nepovjerljiv sadržaj (tool rezultati, artifakti, transkript, web
rezultati, voice-state proslijeđen između prozora) može dospjeti u HTML bez
escapinga. Fokus na `ArtifactPanel.tsx` (mermaid/markdown/html/code render) i
`CompanionOrb.tsx` (voice-state R3 follow-up).

**Napomena o stanju repozitorija:** u `git status` postoje nekomitovane izmjene
(Codex) u `electron/core/window.cjs`, `electron/main.cjs`, `electron/preload.cjs`,
`src/App.tsx`, `src/vite-env.d.ts`. Ove fajlove sam čitao kakvi jesu na disku
(ne u `git HEAD`). Nijedan od njih ne izgleda "usred izmjene" (sintaksno
koherentni, nema polomljenih blokova). `src/App.tsx` ima izmjene oko artifact
fetch logike (l. 140–150) i retry rezultata (l. 316), ali logika potrošnje
artifakta je ista: `setArtifact(...)` → `ArtifactPanel`. `src/styles.css` je
u međuvremenu razdvojen u module (commit `a34baa8`) — nije relevantno za XSS.
`src/components/*` fajlovi koje sam čitao (`ArtifactPanel.tsx`, `CompanionOrb.tsx`,
`RickyOrb.tsx`) nemaju nekomitovanih izmjena u `git status`.

---

## Tabela nalaza

| # | Fajl:linija | Šta se renderuje | Odakle sadržaj | Nepovjerljiv? | Rizik | Prijedlog |
| --- | --- | --- | --- | --- | --- | --- |
| N1 | `src/components/ArtifactPanel.tsx:137` | Mermaid SVG via `dangerouslySetInnerHTML={{ __html: mermaidState.svg }}` | `artifact.content` (kind=`mermaid`) → `mermaid.render(id, source)` → `result.svg`. `artifact.content` dolazi iz tool rezultata / modela (App.tsx:145, 196, 316) | **Da** — sadržaj dolazi od alata/modela (potencijalno od weba / korisničkog unosa) | **Nizak** (mermaid `securityLevel:"strict"` sanitizuje SVG, vidi analizu) | Ostaviti + zadržati `strict`; opciono dodati DOMPurify kao odbranu-u-dubini |
| N2 | `src/components/ArtifactPanel.tsx:454` | `escapeHtml()` funkcija definirana ali **nigdje se ne poziva** (dead code) | — | — | Nema (mrtav kod) | Ili ukloniti, ili koristiti u mermaid SVG prije ubacivanja (višak uz strict) |

**Ostali artefact tipovi** (`markdown`, `code`, `notes`, `table`, `image`,
`imageLoading`, `thumbnailBoard`, `progress`, `text`): svi renderuju se kroz
React `{}` izraze (`<p>{content}</p>`, `<code>{artifact.content}</code>`,
`<img src={src} alt={title} />`, JSON-parsani podaci u `{cell}`) — React
podrazumijevano escape-uje. **Nema dodatnih HTML ponora.**

`renderInline` (l. 322–336) za markdown linkove koristi `href={match[2]}` i
`{match[1]}` kao tekst — React escape-uje; `target="_blank" rel="noreferrer"`.
Bez `javascript:` validacije, ali React ne dozvoljava `javascript:` URL-ove u
`href` na `<a>` (blokira ih). Rizik: nizak; opcionalno dodati `^https?` check.

---

## ArtifactPanel analiza

Jedini eksplicitni HTML ponor u cijelom `src/` je **N1** — mermaid SVG u
`ArtifactPanel.tsx:137`.

**Tok sadržaja:**
1. Tool/model vraća `RickyToolResult.artifact` sa `kind:"mermaid"` i `content`
   (mermaid source tekst). `App.tsx:145/196/316` → `setArtifact(...)`.
2. `realtime.ts:505 sanitizeToolResult()` ne mijenja `content` za mermaid kind
   (samo skraćuje > 1200 znakova, što ne sanitizuje).
3. `ArtifactPanel.tsx:57-90` `useEffect`: `normalizeMermaidSource(content)`
   → `mermaid.render(mermaidId, source)` → `result.svg` → `setMermaidState`.
4. `l.137`: `<div dangerouslySetInnerHTML={{ __html: mermaidState.svg }} />`.

**Zašto je rizik NIZAK:**
- `mermaid.initialize({ ..., securityLevel: "strict" })` (l. 50–55). Mermaid 11.16.0
  u `strict` modu: onemogućava `htmlLabels` (label-e se renderuju kao escaped tekst,
  ne kao HTML), onemogućava `click` event binding, i primjenjuje internu
  sanitizaciju SVG outputa (uklanja `<script>`, event handler atribute, itd.).
- `mermaidId` je sanitizovan: `rawId.replace(/[^a-zA-Z0-9_-]/g, "")` (l. 59) —
  ne napada DOM id-a.
- `fallbackMermaidSource(title)` (l. 374) čisti `title`: `title.replace(/["<>]/g, "")`.
- `normalizeMermaidSource` (l. 369) ne pravi HTML — samo čisti ` ```mermaid` fence
  i normalizuje unicode quote znakove.

**Teorijski preostali rizik:** ako mermaid 11.16.0 `strict` mode ima bypass
(npr. kroz specifičan diagram tip), SVG bi mogao sadržavati payload. Ovo je
odbrana-u-dubini pitanje, ne stvarni ponor u našem kodu. DOMPurify preko SVG-a
prije `dangerouslySetInnerHTML` bi zatvorio i taj teorijski jaz.

**`escapeHtml` (N2):** funkcija definisana (l. 454–460) ali `grep` pokazuje da se
**ne poziva nigdje** u `src/`. Mrtav kod. Ako se ne planira koristiti (mermaid
strict već sanitizuje), može se ukloniti; ako se želi odbrana-u-dubini, treba
je primijeniti na `mermaidState.svg` prije ubacivanja — ali napomena: `escapeHtml`
bi slomio SVG strukturu (escape-ovao bi `<svg>`, `<path>` itd.), pa **nije
primjenjiva** na SVG; za tu svrhu treba DOMPurify (koji čuva SVG tagove a uklanja
opasne). Trenutno je `escapeHtml` bezbjedan mrtav kod.

---

## CompanionOrb / voice-state (R3 follow-up)

`src/components/CompanionOrb.tsx` konzumira voice-state **isključivo kao
tekst/atribut**, ne kao HTML:

| `fajl:linija` | Korištenje | Bezbjedno? |
| --- | --- | --- |
| `CompanionOrb.tsx:11` | `useState<VoiceState>(initialState)` | Da (state tip) |
| `CompanionOrb.tsx:17` | `window.ricky.onCompanionVoiceState?.((state: VoiceState) => setVoiceState(state))` | Da (tipovan callback) |
| `CompanionOrb.tsx:38` | `aria-label={\`Ricky companion — ${voiceStateLabel(voiceState)}\`}` | Da — React escape-uje atribut |
| `CompanionOrb.tsx:51` | `title={\`${voiceStateLabel(voiceState)} — ...\`}` | Da — React escape-uje atribut |
| `CompanionOrb.tsx:59` | `<span className="companion-state-pill">{voiceStateLabel(voiceState)}</span>` | Da — React escape-uje `{}` tekst |

**`voiceStateLabel()`** (`src/lib/voiceState.ts:36–55`) vraća statičke stringove
("Slušam", "Govorim", ...) iz `switch` po `VoiceState` enumu — ne prima
nepovjerljiv unos. Čak i da `state` vrijednost bude van-liste, default grana
vraća "Spreman". **Nema HTML ponora.**

IPC kanal `companion:voice-state` (`electron/preload.cjs:45–50`) proslijeđuje
`state` direktno u `setVoiceState` — ali `VoiceState` je TS tip, a potrošnja je
samo kroz `voiceStateLabel()` (switch) i `className`/`aria-label`/`title`/`{}` —
svi escape-ovani. Ako bi main proces proslijedio npr. `"<script>"` umjesto
validnog state-a, React bi ga renderovao kao tekstualni label "Spreman" (default
switch grana, jer `"<script>"` ne matchuje nijedan case). **R3 nalaz ostaje
popravljen — nema regresije.**

---

## Zaključak

- **Nema HTML ponora sa direktno nepovjerljivim, ne-sanitizovanim sadržajem.**
- Jedini `dangerouslySetInnerHTML` (N1, `ArtifactPanel.tsx:137`) renderuje SVG koji
  generiše `mermaid.render` pod `securityLevel:"strict"` — mermaid interni sanitizuje
  output. Rizik ocijenjen **Nizak**, ali ostaje teorijski jaz ako mermaid strict ima
  bypass.
- Svi ostali artifact tipovi (markdown/code/notes/table/image/...) koriste React
  `{}` izraze — escape-ovano.
- CompanionOrb/voice-state (R3) — bezbjedno, samo tekst/atribut, nema regresije.
- `escapeHtml` (N2) je mrtav kod, nije primjenjiv na SVG (slomio bi strukturu).

**Grep dokazi:**
- `dangerouslySetInnerHTML` → 1 hit (`ArtifactPanel.tsx:137`).
- `.innerHTML` / `insertAdjacentHTML` / `document.write` / `outerHTML` /
  `createContextualFragment` → 0 hitova u `src/`.
- Mermaid `securityLevel: "strict"` potvrđeno (l. 53). Verzija 11.16.0.

---

## Preporuka za Claude

1. **N1 (opciono, odbrana-u-dubini):** dodati `DOMPurify.sanitize(svg, {USE_PROFILES:{svg:true}})`
   na `mermaidState.svg` prije `dangerouslySetInnerHTML`. Zadržati
   `securityLevel:"strict"` (prva linija odbrane). Ne koristiti `escapeHtml` za
   SVG (slomio bi tagove). Ovo zatvara teorijski jaz u slučaju mermaid bypass.
2. **N2:** ukloniti mrtav `escapeHtml()` ili ga koristiti negdje smisleno (npr. u
   `fallbackMermaidSource` title, iako je tu već ručno očišćen). Najčistije:
   ukloniti.
3. **renderInline linkovi (l. 322):** opciono dodati `if (!/^https?:/.test(match[2]))`
   guard prije `<a href>`. React već blokira `javascript:`, ali eksplicitni guard
   je jasniji. Nije hitno.
4. **R3 CompanionOrb:** nema akcije — ostaje bezbjedno.

**Nema hitnih sanitizacija.** Trenutno stanje je prihvatljivo za MVP; N1/DOMPurify
je preporuka za očvrsnuće, ne blokada.
