# pi — sljedeći koraci (2026-07-06)

Redoslijed je bitan. Radi ovim tačnim redom, ne paralelno, ne obrnuto.

## Korak 3 — GUI rebuild sa pravim branding assetima (AKTUELNO)

Koraci 1 i 2 ispod su završeni i verifikovani. Sljedeći korak:
[PI_BRANDING_REBUILD_BRIEF.md](./PI_BRANDING_REBUILD_BRIEF.md) — koristi stvarne, gotove branding
assete (`assets/brending/`) da GUI stvarno liči na odobreni mockup, umjesto trenutnog stanja koje
korisnik je vizuelno potvrdio da je daleko od cilja (nema mikrofon dugmeta, prost R krug bez glow-a,
debug artifact panel vidljiv).

---

## Korak 1 — RICKY_CONFIRMATION_BRIDGE_BRIEF.md (završeno, referenca)

Pročitaj [RICKY_CONFIRMATION_BRIDGE_BRIEF.md](./RICKY_CONFIRMATION_BRIDGE_BRIEF.md) i implementiraj
tačno ono što piše — auto-propose confirmation kad tool vrati `CONFIRMATION_REQUIRED`, i auto-retry
originalnog tool poziva kad korisnik odobri. Ne diraj `permission_engine.py`/`tool_executor.py`/
`tool_registry.py` (backend strana je gotova i testirana). Ne pravi novi dialog — `ConfirmationDialog.tsx`
već postoji i radi.

Kad završiš: napiši agent_report, ažuriraj `docs/MIGRATION_PLAN.md` red za "Confirmation Bridge",
i javi da si gotov. Claude Code radi verifikaciju prije nego što se pređe na korak 2.

## Korak 2 — UI Redesign (završeno, referenca)

Kad Confirmation Bridge bude gotov, radi cijeli UI redesign iz **oba** dokumenta zajedno, ne samo
jednog:

- [RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md](./RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md) — arhitektura, layout, komponente, IPC/event boundaries, cancellation-aware Stop UI.
- [RICKY_FINAL_UI_IMPLEMENTATION_PROMPT.md](./RICKY_FINAL_UI_IMPLEMENTATION_PROMPT.md) — finalni vizuelni izgled (odobreni mockup, orb dizajn, konkretni Idle/Dictation/Confirmation ekrani, Stop kontrola, mapiranje na stvarne API-je).

Ova dva dokumenta su namjerno unakrsno povezana i nadopunjuju se — jedan bez drugog daje ili
ispravnu arhitekturu bez odobrenog izgleda, ili lijep izgled bez ispravnog ponašanja. Radi po oba
istovremeno, ne biraj jedan pa drugi kasnije.

## Zašto ovim redom

Confirmation Bridge dira `App.tsx` i `ConfirmationDialog` tok (auto-propose/auto-retry logika). UI
redesign redizajnira te iste komponente vizuelno. Ako se redesign radi prvi, gradi se UI oko
confirmation toka koji trenutno ne radi (vidi brief — `CONFIRMATION_REQUIRED` danas završava u
ćorsokaku za svaki tool koji traži potvrdu, uključujući `records_delete`). Bolje da redesign gradi
na već ispravnom, radnom toku nego da se bridge naknadno ubacuje u već izmijenjen redesign kod.
