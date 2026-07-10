# E4 — Red-team test expansion (pi izvještaj)

**Datum:** 2026-07-10
**Izvršilac:** pi
**Brief:** `docs/briefs/2026-07-10_redteam-test-expansion.md`
**Referenca:** `docs/SECURITY_DELEGATION_PLAN.md` E4 [D+R]
**Status:** ✅ ZAVRŠEN — čeka Claude pregled

---

## Sažetak

Proširen `python_backend/tests/test_security_redteam.py` sa **8 novih red-team
testova** koji pokrivaju napadačke šablone koje nisu bile u postojećem setu od 8
testova. Nulti novi test ne duplira postojeće scenarije — svi testiraju
nepokrivene vektore ili proširuju pokrivenost postojećih mehanizama.

**Produkcijski kod nije diran** — `git diff --stat` pokazuje samo `test_security_redteam.py` (+261 ln).

---

## Novi testovi (8)

| # | Naziv | Domen | Šta provjerava |
|---|---|---|---|
| 1 | `test_fake_system_message_header_in_content` | S-2b wrap | Fake header `SYSTEM:` / `### Developer Message` ostaje unutar untrusted wrappera — wrapper ne interpretira unutrašnji framing |
| 2 | `test_confirmation_id_fabrication_in_content` | S-2c perm | Fabrikovan `confirmation_id` u tool argumentima NE zaobilazi permission engine — engine čita samo `request.context.confirmation_id` |
| 3 | `test_both_delimiters_stripped_from_payload` | S-2b wrap | Payload sa OBA delimitera (`UNTRUSTED_OPEN` + `UNTRUSTED_CLOSE`) — oba su stripped, rezultat ima tačno 1 open + 1 close (proširenje postojećeg breakout testa koji testira samo close) |
| 4 | `test_roleplay_override_framing_wrapped` | S-2b wrap | DAN (Do Anything Now) roleplay framing — nema posebnog tretmana, ostaje unutar delimitera |
| 5 | `test_escalation_persists_across_multiple_tool_calls_in_sequence` | S-2c perm | Eskalacija NIJE one-shot flag — svi uzastopni acting tool pozivi (ne samo prvi) su eskalirani kad je `external_content_seen=True` |
| 6 | `test_artifact_exfiltration_attempt_wrapped` | S-2b wrap | Save-then-read exfiltration framing — ostaje unutar untrusted wrappera |
| 7 | `test_multilingual_injection_payload_wrapped` | S-2b wrap | Injection payload na bosanskom/srpskom — wrap je jezički-agnostičan, identično ponašanje (relevantno: projekat je sr/bs-prvi) |
| 8 | `test_reader_tool_itself_cannot_bypass_via_own_result` | S-2c perm | Reader tool izuzeće NE curi na sljedeći acting tool — čak i kad reader arguments sadrže tvrdnje o auto-approved confirmation_id-u, permission engine ih ignoriše |

### Distribucija po mehanizmima

| Mehanizam | Postojeći testovi | Novi testovi | Ukupno |
|---|---|---|---|
| S-2a (system prompt rule) | 1 | 0 | 1 |
| S-2b (delimiter wrapping) | 2 | 4 | 6 |
| S-2c (permission escalation unit) | 3 | 3 | 6 |
| S-2c (E2E chain) | 2 | 0 | 2 |
| **Ukupno** | **8** | **8** | **16** |

Novi testovi su fokusirani na S-2b (wrap) i S-2c (permission escalation) — postojeći
su već dobro pokrivali S-2a i E2E lance.

---

## Pytest izlaz

```
Baseline (prije):  214 passed (8 red-team + 206 ostalih)
Poslije:           222 passed (16 red-team + 206 ostalih)
                   0 failed, 0 skipped
```

- `python -m pytest tests/test_security_redteam.py -v` → **16 passed** (8 starih + 8 novih)
- `python -m pytest -q` → **222 passed** (cijela suita)

---

## Produkcijski kod — potvrda nepromijenjen

```
$ git diff --stat
python_backend/tests/test_security_redteam.py | 261 ++++++++++++++++++++++++++
1 file changed, 261 insertions(+)
```

Nijedan od ovih fajlova nije diran:
- `app/agent/permission_engine.py` ✅
- `app/agent/prompt_builder.py` ✅
- `app/agent/runtime.py` ✅
- `app/main.py` ✅

---

## Konstante dodane u test fajl

| Konstanta | Opis |
|---|---|
| `FAKE_SYSTEM_HEADER_PAYLOAD` | Fake `SYSTEM:` / `### Developer Message` header |
| `CONFIRMATION_ID_PAYLOAD` | Fabrikovan `confirmation_id: confirm_bypass_2026` |
| `BOTH_DELIMITERS_PAYLOAD` | Sadrži i `UNTRUSTED_OPEN` i `UNTRUSTED_CLOSE` |
| `DAN_ROLEPLAY_PAYLOAD` | DAN (Do Anything Now) roleplay framing |
| `MULTIPLE_TOOL_ESCALATION_CONTEXT` | Pre-built `ToolExecutionContext` za testove perzistencije |
| `EXFIL_PAYLOAD` | Save-then-read data exfiltration pokušaj |
| `MULTILINGUAL_PAYLOAD` | Injection na bosanskom/srpskom |
| `READER_ESCAPE_CLAIM_ARGS` | Arguments koje tvrde da su acting tool sa auto-confirmationom |

---

## Found issues

Nema — svi novi testovi prolaze, nijedan nije otkrio neočekivani propust u
postojećim mehanizmima. S-2b (wrap_untrusted_content) i S-2c (check_permission)
rade kako je dokumentovano.

---

## Dira fajlovi

| Fajl | Akcija | Promjena |
|---|---|---|
| `python_backend/tests/test_security_redteam.py` | **izmijenjen** (dodano 8 testova + 8 konstanti) | +261 ln |

**NE commitovano** — čeka Claude pregled prema `docs/briefs/2026-07-10_redteam-test-expansion.md`.

---

## Claude pregled checklist

- [ ] `python -m pytest -q` → 222 passed
- [ ] `git diff --stat` → samo `test_security_redteam.py`
- [ ] Nema dupliranja sa postojećih 8 testova (pregledati nazive + assertion pattern-e)
- [ ] Svi payload-i su smisleni napadački šabloni (ne trivijalni)
- [ ] `check_permission` / `wrap_untrusted_content` nisu mijenjani
- [ ] Ako neki test pokazuje da mehanizam NE blokira napad → dokumentovati u "Found issues" ovog izvještaja (trenutno: nijedan takav slučaj)