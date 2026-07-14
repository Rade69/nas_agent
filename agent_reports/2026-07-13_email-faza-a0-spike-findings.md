# Faza A0 spike nalazi — Gmail compose preko CDP (bez trajnog koda)

**Datum:** 2026-07-13
**Scope:** Throwaway skripte u scratchpad-u (van repo-a), NIJEDNA linija u
`python_backend/`/`electron/`/`src/`. Ovo je izvještaj o nalazima, ne kod.
**Plan:** [`docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md`](../docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md) poglavlje 11, Faza A0.

## Šta je urađeno

Uz uživo učešće korisnika (login u izolovan Chrome profil, nešto što agent
ne može uraditi umjesto korisnika):

1. Pokrenut izolovan Chrome profil (`--user-data-dir` van korisnikovog
   regularnog profila, `--remote-debugging-port=<nasumičan>`,
   `--remote-debugging-address=127.0.0.1`).
2. Potvrđeno da je CDP endpoint dostupan isključivo na loopback-u
   (`GET http://127.0.0.1:<port>/json/version` radi, ništa nije izloženo
   van 127.0.0.1).
3. Korisnik se ulogovao u svoj Gmail nalog u tom izolovanom prozoru.
4. Preko `Page.navigate` na `.../#inbox?compose=new` (POSLIJE login-a, ne kao
   inicijalni launch argument — vidi nalaz niže) otvoren compose dialog.
5. Preko `Runtime.evaluate` (read-only `querySelector` probe, ništa
   mijenjano) identifikovani stvarni, živi DOM selektori.
6. Testiran WRITE put: `DOM.getDocument` → `DOM.querySelector` → `DOM.focus`
   (fokus direktno na node, BEZ sintetizovanog klika) → `Input.insertText`.
   Upisan test string u Subject, pročitan nazad, **potvrđena tačna
   podudarnost**. Send NIJE dirnut.
7. Očišćen test tekst, izolovani Chrome proces zatvoren.

## Ključni nalazi

### 1. CDP pouzdano vidi i piše u Gmail compose — POTVRĐENO

`Runtime.evaluate`+`querySelector` i `DOM.focus`+`Input.insertText` rade
tačno kako je plan pretpostavio. Ovo je najvažnija otvorena pretpostavka iz
plana (poglavlje 15, pitanje 2-4) i sad je empirijski potvrđena, ne samo
teorijski.

### 2. Launch-argument URL gubi se u OAuth redirect lancu — ISPRAVKA PLANA

Plan (poglavlje 4.2, `open_compose()`) je pretpostavio da se compose otvara
preko URL-a kao launch argumenta. U praksi: kad Chrome profil NIJE još
ulogovan, Google-ov login/OAuth redirect lanac "pojede" `#compose=new` hash
fragment — nakon login-a stranica završi na običnom `#inbox`, bez compose-a.

**Ispravka:** `GmailDraftAdapter.open_compose()` mora:
1. Prvo navigirati na `https://mail.google.com/mail/u/0/#inbox` i provjeriti
   da li je korisnik ulogovan (detektovati login formu vs. inbox).
2. Ako nije ulogovan, vratiti jasnu grešku koja traži ručnu prijavu (isti
   onboarding tok kao plan poglavlje 6) — NE pokušavati compose dok login
   nije potvrđen.
3. Tek nakon potvrđenog login-a, `Page.navigate` na `#inbox?compose=new`.

### 3. Stabilni selektori (živi, potvrđeni podaci)

| Polje | Selektor | Napomena |
|---|---|---|
| Compose dialog | `[role="dialog"]` | Jedan nađen kad je jedan draft otvoren — treba potvrditi ponašanje sa 2 draft-a (nije testirano ovom sesijom) |
| Subject | `input[name="subjectbox"]` | **`name` atribut, jezik-nezavisan** — potvrđeno stabilno |
| Body | `[role="textbox"][contenteditable="true"]` unutar dialoga | `role` je jezik-nezavisan; `aria-label` ("Tijelo poruke"/"Message Body") NIJE, varira po jeziku naloga |
| To | `input[role="combobox"]` unutar dialoga | Tri kandidata nađena (span link za kontakte, wrapper div, stvarni input) — **treba dodatna verifikacija koji tačno prima `Input.insertText`**, span/div wrapper nisu text input |
| Send | `[role="button"]` sa aria-label koji sadrži lokalizovanu riječ "Send"/"Pošalji" | **Adapter ovo NIKAD ne treba tražiti** — allowlist dizajn iz plana znači da se Send selektor nikad ne koristi, ovo je samo potvrda da plan-ov "strukturalno nedostižan" argument stoji (ne postoji generic put koji bi slučajno pogodio ovaj element) |

### 4. Otvorena pitanja iz plana — status nakon spike-a

Iz `EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md` poglavlje 15:

1. ARIA labeli variraju po jeziku — **POTVRĐENO** (nalog je bio na
   srpsko/hrvatskom regionalnom variantu: "Predmet", "Tijelo poruke",
   "Prima", "Pošalji"). Selektori u tabeli gore su birani da budu
   jezik-nezavisni gdje god je moguće (name/role atributi, ne aria-label
   tekst).
2. CDP biblioteka — **RIJEŠENO**: čist `websockets` paket (već dostupan u
   okruženju, `pyproject.toml` treba `+ "websockets"`) + ručni JSON-RPC je
   dovoljan, nema potrebe za težom bibliotekom.
3. `--app=` launch mod — **NIJE TESTIRANO** ovom sesijom (koristio se
   regularan prozor sa punim Chrome UI-jem, ne `--app=` bez chrome-a).
   Ostaje otvoreno za Fazu A.
4. `Accessibility.getFullAXTree` pouzdanost — **ZAOBIĐENO**: `Runtime.evaluate`
   + `querySelector` se pokazalo dovoljno i jednostavnije za MVP; puna AX
   tree nije bila potrebna za pronalazak ovih 4 polja. Može se revizitovati
   kasnije ako se pokaže potreba za semantičkijim targetiranjem.
5. Chrome verzija/CDP domeni — Chrome 150 (aktuelan) je korišten, sve
   potrebne domene (`DOM`, `Runtime`, `Input`, `Page`) su dostupne i radile
   bez problema.

## Šta NIJE testirano (ostaje za Fazu A/B)

- Ponašanje sa VIŠE od jednog otvorenog/minimiziranog compose dialoga
  (plan zahtijeva fail-closed — nije empirijski provjereno).
- To polje — tačan node koji prihvata `Input.insertText` (tri kandidata,
  nije suženo na jedan).
- CC/BCC polja (nisu ni tražena ovom sesijom).
- Ponašanje kad se Chrome tab/prozor zatvori usred workflow-a (TOCTOU
  provjera iz plana poglavlje 4.3).
- Ponašanje pri promjeni Gmail DOM strukture (jednokratan test, ne
  ponovljeno mjerenje kroz vrijeme).

## Zaključak

Faza A0 je uspješno potvrdila glavnu arhitektonsku pretpostavku plana: CDP +
izolovan profil je izvodljiv, deterministički pristup Gmail compose-u, sa
jednom bitnom ispravkom (launch-URL vs. post-login navigate). Nema razloga
da se odustane od pristupa. Nastavlja se na Fazu A (pravi
`GmailDraftAdapter` modul u `python_backend/`, i dalje bez confirmation
UI-ja i bez voice toka).
