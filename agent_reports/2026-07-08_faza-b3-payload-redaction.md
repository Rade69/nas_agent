# Agent Report — B3/O3: Redakcija osjetljivog payloada u audit logu + DB permisije

**Datum:** 2026-07-08
**Agent:** Claude Code
**Scope:** Nalaz O3 iz pi B2 audita (`agent_reports/2026-07-08_pi-log-hygiene-audit.md`), verifikovan od Claude.

---

## Problem (verifikovan)
`ActionLogService.log_tool_response` (`action_log.py`) je upisivao **pun `input_payload` i `output_payload`** svakog tool poziva u plaintext SQLite (`tool_runs` tabela) — uključujući tačan tekst koji `computer_type_text` kuca (može biti lozinka ukucana u polje), email body, transkripte i sve credential-noseće argumente. Potvrđeno čitanjem `action_log.py:24-25` (prije izmjene).

## GitNexus impact
Jedini pozivalac `log_tool_response` je `ToolExecutor._log`. Izmjena je aditivna (redakcija prije upisa, isti interfejs). Blast radius: nizak. (GitNexus MCP je bio u reconnectu; blast radius utvrđen ručno — poznat jedini call site.)

## Šta je urađeno
1. **Redakcija payloada (`action_log.py`):** nova `redact_sensitive(value)` — rekurzivno prolazi dict/list i zamjenjuje **vrijednosti** ključeva iz `SENSITIVE_PAYLOAD_KEYS` (`text`, `body`, `content`, `transcript`, `password`, `secret`, `token`, `api_key`, `apikey`) sa `[REDACTED]`. Ključevi/struktura ostaju (audit i dalje pokazuje KOJI alat je pozvan sa KOJIM poljima i rezultat/status). Primijenjeno na `input_payload` i `output_payload` prije upisa. Ne mutira original.
2. **DB permisije (`db.py`):** `os.chmod(database_path, 0o600)` nakon inicijalizacije (best-effort, ne ruši startup). Iskreno dokumentovano: puno efektivno na POSIX-u; na Windowsu `os.chmod` samo toggluje read-only bit i NE enforce-uje owner-only ACL — pravi Windows at-rest (icacls ACL / SQLCipher) ostaje B3 follow-up.

## Zašto ovako (a ne enkripcija odmah)
- Redakcija je **cross-platform** i zatvara stvarni plaintext-content leak odmah, bez nove zavisnosti.
- Puna DB enkripcija (SQLCipher) traži novu zavisnost + upravljanje ključem (vezano za B1/keyring) — veći zahvat, odgođen kao B3 nastavak.
- Balans audit vs privatnost: čuva se forenzička vrijednost (koji alat, koja polja, status) bez čuvanja osjetljivog sadržaja.

## Šta NIJE dirano
- `electron/**` (uključujući Codex-ov nedovršeni jitter rad u `main.cjs`/`window.cjs`), GUI (`App.tsx`/`styles.css`).
- Artifact/notes/records tabele (pun sadržaj tamo je namjeran — korisnik ga traži; `tool_runs` je zaseban audit zapis).
- Permission engine, tool execution logika.

## Verifikacija
- `python -m pytest -q` → **199 passed** (197 prethodno + 2 nova: `test_redact_sensitive_masks_free_text_and_credentials`, `test_type_text_argument_is_redacted_in_audit_log`).
- Ažuriran postojeći `test_action_log.py` koji je očekivao nemaskiran `text` → sad očekuje `[REDACTED]`.
- Potvrđeno: osjetljiv string se NE pojavljuje u `input_json` u DB.

## Rizici / ograničenja
- Redakcija je key-based; ako se doda alat sa osjetljivim poljem pod drugim imenom (npr. `message` sa privatnim sadržajem), treba proširiti `SENSITIVE_PAYLOAD_KEYS`. Trenutni set pokriva poznata polja.
- DB nije enkriptovana; `0600` na Windowsu nije puna zaštita. Napadač sa pristupom disku i dalje čita ne-osjetljive metapodatke + strukturu. Puna zaštita = B3 (SQLCipher/ACL).

## Potreban follow-up (B3 nastavak)
- Windows ACL (icacls) na DB fajlu za stvarni owner-only.
- SQLCipher enkripcija DB (uz B1/keyring za ključ).
- Razmotriti redakciju/maskiranje i u `confirmations.payload_json` (isti razred sadržaja) ako se pokaže osjetljivim.

## Potrebna korisnička potvrda
- Nema blokera. Commit je Python-only, ne dira Codex GUI/jitter rad.
