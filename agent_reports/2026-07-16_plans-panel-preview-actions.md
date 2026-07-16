# Agent Report — Plans panel preview actions

- Datum: 2026-07-16
- Agent: Codex
- Obim: Plans panel UI bugfix + product plan dokument

## Problem

Korisnik je prijavio da dugmad u vidljivom panelu "Planovi" ne rade.

Uzrok nije bio u glavnom `PlansPanel` drawer-u: on vec ima `onClick` handlere za tabove, kreiranje plana i status akcije. Problem je bio u donjem dashboard preview panelu (`PlansDrawerPreview`), koji je vizuelno prikazivao dugmad `Aktivni`, `Predlozeni`, `Zavrseni` i `Novi plan`, ali su to bila staticka dugmad bez akcije.

## Sta je promijenjeno

- `src/components/pixel/Previews.tsx`
  - `PlansDrawerPreview` sada ima lokalni tab state.
  - `Aktivni`, `Predlozeni` i `Zavrseni` filtriraju planove po statusu.
  - `Novi plan` poziva `onOpenPlans`.

- `src/components/pixel/PixelMockupBoard.tsx`
  - Proslijedjen je `onOpenPlans` u `PlansDrawerPreview`.

- `docs/PLANS_PANEL_PRODUCT_PLAN.md`
  - Arhiviran detaljan product/implementation plan za Plans panel.
  - P0 oznacen kao prijavljen zavrsen, uz napomenu da glasovno/agentsko upravljanje planovima pripada P1.

## Provjere

- `npm run typecheck` -> proslo
- `npm run check` -> proslo

## Napomena

Ova popravka ne dodaje agent-facing toolove za komande tipa "otvori novi plan". To je sljedeci P1 sloj: agent treba dobiti uske interne akcije za otvaranje Plans panela, kreiranje plana i kasnije upravljanje koracima.
