# Brief za pi — Renderer XSS-sink audit (SAMO izvještaj)

**Za:** pi · **Od:** Claude
**Tip:** READ-ONLY audit. **Ne mijenjaš nijedan fajl koda.** Output je jedan izvještaj.

---

## Zašto ovo
Renderer je glavna XSS meta (Fable). Imamo contextIsolation+sandbox+CSP kao odbranu, ali cilj je **nula XSS ponora (sink-ova)** — mjesta gdje potencijalno nepovjerljiv sadržaj (tool rezultati, artifakti, transkript, tekst sa ekrana/UI, web rezultati, voice-state proslijeđen između prozora) može dospjeti u HTML bez escapinga. React podrazumijevano escape-uje `{}` izraze — rizik su samo eksplicitni HTML ponori.

## Pravila (obavezno)
- **NE mijenjaš kod.** Nijedan `.ts`/`.tsx`/`.cjs`/`.py`. Samo čitaš.
- **NE diraš:** ništa (read-only). Ako Codex trenutno mijenja neki `src/` fajl, samo ga pročitaj kakav jeste i navedi `fajl:linija` — ne uređuj.
- Output je JEDAN fajl: `agent_reports/2026-07-08_pi-xss-sink-audit.md`.
- Srpski/bosanski, latinica. Svaki nalaz `fajl:linija`. Nejasno → "otvoreno pitanje".

## Šta tražiš (grep + čitanje, cijeli `src/**`)
1. **HTML ponori:** `dangerouslySetInnerHTML`, `.innerHTML`, `insertAdjacentHTML`, `document.write`, `outerHTML`, ručno pravljenje DOM-a iz stringa.
2. **Render bibliteke koje prave HTML/SVG iz teksta:** mermaid, markdown renderer, `katex`, bilo šta što uzima string i vraća HTML. Posebno pogledaj **`src/components/ArtifactPanel.tsx`** — kako renderuje artifakte tipa `markdown`, `mermaid`, `html`, `code`. Da li sadržaj artifakta (koji dolazi od alata / modela / weba) ide kroz `dangerouslySetInnerHTML` ili u mermaid/markdown bez sanitizacije?
3. **Proslijeđeni podaci između prozora:** kako `CompanionOrb.tsx` (`src/components/CompanionOrb.tsx` ili gdje već) konzumira `voice-state` koji main proces prosljeđuje — renderuje li ga kao **tekst/klasu** (bezbjedno) ili ga ubacuje u HTML? (Ovo je follow-up na već popravljen nalaz R3.)

## Za svaki nalaz u izvještaj
`fajl:linija` → šta se renderuje i odakle sadržaj dolazi (tool/artifact/transkript/voice-state/statično) → da li je nepovjerljiv → rizik (Visoko = nepovjerljiv sadržaj u HTML ponor; Nisko = statično/escape-ovano) → prijedlog (sanitizacija / textContent / DOMPurify / ostaviti).

Ako **nema** HTML ponora sa nepovjerljivim sadržajem — to je odličan rezultat; eksplicitno napiši "nema ponora" uz dokaz (grep rezultati prazni + kako ArtifactPanel renderuje).

## Format
`Datum`, `Scope`, `Tabela nalaza`, `ArtifactPanel analiza`, `CompanionOrb/voice-state (R3 follow-up)`, `Zaključak`, `Preporuka za Claude`. Bez izmjena koda.

Kad završiš, javi — Claude verifikuje `fajl:linija` i odlučuje o sanitizaciji.
