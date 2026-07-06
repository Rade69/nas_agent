# Legacy tools — RileyJarvis Windows Hybrid

> **Context:** FAZA 17 / `agent_reports/2026-07-06_faza17-disable-legacy-powershell.md`
> **Related:** `docs/MIGRATION_PLAN.md`, `docs/ARCHITECTURE_VOICE_FIRST_REVISED.md`

Ovaj dokument objašnjava zašto neki legacy toolovi još postoje u `electron/` sloju i kako se kontrolišu preko feature flag-a.

---

## Zašto legacy toolovi postoje

Aplikacija je portirana sa macOS Electron prototipa na Windows u fazama. Svaka faza migracije prebacuje po jednu grupu toolova iz Electron/JSON-db/PowerShell u Python backend (SQLite). Neki toolovi još NISU migrirani — njihove legacy implementacije su jedini način da se ti toolovi koriste dok Python zamjene ne budu gotove.

---

## Feature flag: `RICKY_USE_LEGACY_POWERSHELL_TOOLS`

| Vrijednost | Ponašanje |
|-----------|-----------|
| `1` (default) ili nepostavljeno | Legacy toolovi su dostupni. Alati sa Python ekvivalentom **preferiraju Python**, ali padaju natrag na legacy ako backend ne radi. Alati **bez** Python ekvivalenta koriste legacy direktno. |
| `0` | Legacy toolovi su **potpuno blokirani**. Alati bez Python ekvivalenta vraćaju grešku `LEGACY_DISABLED`. Alati sa Python ekvivalentom ne padaju natrag na legacy — ako Python faila, vraća se `PYTHON_FAILED_LEGACY_DISABLED`. |

Postavlja se u `.env.local`:

```bash
# Disable all legacy PowerShell/JSON-db tools — rely on Python backend only.
RICKY_USE_LEGACY_POWERSHELL_TOOLS=0
```

---

## Toolovi sa Python ekvivalentom (odmah preferiraju Python)

Ovi alati su migrirani u FAZAMA 11 i 16. Aplikacija ih automatski delegira Python backend-u preko `POST /tools/execute`. Legacy implementacije postoje isključivo kao safety fallback i **ne pozivaju se** osim ako:

1. Python backend nije dostupan ILI
2. Feature flag `RICKY_USE_LEGACY_POWERSHELL_TOOLS=1` je postavljen

| Tool | Legacy lokacija | Python lokacija | Faza |
|------|----------------|----------------|------|
| `note_add`, `note_search`, `note_list` | `electron/main.cjs` (JSON db) | `app/tools/memory/notes.py` | FAZA 11 |
| `records_create`, `records_search`, `records_update`, `records_delete` | `electron/main.cjs` (JSON db) | `app/tools/memory/records.py` | FAZA 11 |
| `artifact_create`, `artifact_get`, `artifact_list`, `artifact_show` | `electron/main.cjs` (inline) | `app/tools/artifacts.py` | FAZA 11 |
| `screen_snapshot` | `electron/tools_legacy/powershell/screenSnapshot.cjs` | `app/tools/system/screenshot.py` | FAZA 11 |
| `ui_inspect` | `electron/tools_legacy/powershell/uiInspect.cjs` | `app/tools/system/ui_inspect.py` | FAZA 11 |
| `web_search` | `electron/main.cjs` (Exa, `webSearch()`) | `app/tools/web/search.py` | FAZA 16 |
| `image_generate` | `electron/main.cjs` (OpenAI, `generateImage()`) | `app/tools/images/generate.py` | FAZA 16 |

## Toolovi bez Python ekvivalenta (još uvijek legacy-only)

**Ovi alati će se migrirati u FAZI 13 (computer-use v1, koordinate) i FAZI 14 (computer-use v2, UI element targeting).** Do tada postoji **samo** legacy implementacija.

| Tool | Legacy lokacija | Faza |
|------|----------------|------|
| `computer_open_app` | `electron/tools_legacy/powershell/computerOpenApp.cjs` | Legacy (FAZA 13) |
| `computer_type_text` | `electron/tools_legacy/powershell/computerTypeText.cjs` | Legacy (FAZA 13) |
| `computer_press_key` | `electron/tools_legacy/powershell/computerPressKey.cjs` | Legacy (FAZA 13) |
| `computer_click` | `electron/tools_legacy/powershell/computerClick.cjs` | Legacy (FAZA 13) |
| `computer_scroll` | `electron/tools_legacy/powershell/computerScroll.cjs` | Legacy (FAZA 13) |

Ako je `RICKY_USE_LEGACY_POWERSHELL_TOOLS=0` postavljen, **ovi toolovi vraćaju grešku** dok se FAZA 13/14 ne implementiraju.

---

## Toolovi koji su **isključivo** Electron-side (ne migriraju se u Python)

Neki alati su dizajnirani da žive isključivo u Electron sloju (UI interakcija, thumbnail board). Oni nisu dio migracije i nisu kontrolisani legacy flag-om.

| Tool | Lokacija | Razlog |
|------|----------|--------|
| `set_mode` | `electron/main.cjs` | Direktno kontroliše Electron prozor — ne može biti u Pythonu |
| `artifact_show` | `electron/main.cjs` | Direktno kontroliše ArtifactPanel — UI-specifično |
| `show_menu` | `electron/main.cjs` | UI rendering |
| `mermaid_render` | `electron/main.cjs` | UI rendering |
| `thumbnail_*` | `electron/main.cjs` | Zavisi od JSON db `thumbnailBoard` state-a; migracija zahtijeva zasebnu fazu |

---

## Kada će se legacy potpuno ugasiti

1. **FAZA 13/14** — implementirati Python `computer_*` toolove
2. **Flip default-a**: kad FAZA 13/14 prođe end-to-end verifikaciju, default `RICKY_USE_LEGACY_POWERSHELL_TOOLS` se mijenja sa `1` na `0`
3. **FAZA 17 finalizacija**: legacy fajlovi se **ne brišu** — ostaju kao dev-only fallback iza flag-a. Potpuno uklanjanje je odluka za post-1.0 cleanup.

---

## Kratka istorija

- **FAZA 1-3**: baseline, arhitektura, split `electron/main.cjs` — svi toolovi u Electron/PowerShell
- **FAZA 4-5**: Python skeleton, Electron pokreće Python backend
- **FAZA 6**: Realtime session security (API ključ na backend)
- **FAZA 7**: SQLite storage + action log
- **FAZA 8**: Voice-first UI (TopBar/BottomVoiceBar/VoiceState)
- **FAZA 9**: Confirmations + Plans/Proposals
- **FAZA 10**: Permission/risk/cancellation engine
- **FAZA 11**: Tool registry + local toolovi (notes, records, artifacts, screenshot, ui_inspect) u Python → **prva grupa legacy→Python**
- **FAZA 12**: Companion orb
- **FAZA 15**: Agent runtime u Pythonu
- **FAZA 16**: OpenAI/Exa/image integracije u Python (web_search, image_generate) → **druga grupa legacy→Python**
- **FAZA 17** (ovaj): Legacy feature flag — **priprema za FAZA 13/14**
