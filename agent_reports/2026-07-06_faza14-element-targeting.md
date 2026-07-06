# FAZA 14 — Computer-use Python v2 (UI element targeting)

## Datum

2026-07-06

## Scope

Implementirana je FAZA 14 iz `docs/MIGRATION_PLAN.md`: element-based UI automation preko Windows UI Automation (UIA). Dodaje 4 nova toola koja smanjuju oslanjanje na koordinate iz FAZA 13.

## Šta je urađeno

### `python_backend/app/tools/system/element_target.py` (novi)

4 handlera preko `uiautomation` biblioteke (pure-Python UIA wrapper, instaliran kao nova zavisnost):

- **`computer_find_elements`** — pretraga UI elemenata po app, title_contains, control_type, name, automation_id, class_name; vraća name/control_type/automation_id/class_name/bounding_rect/is_enabled za svaki element
- **`computer_click_element`** — klik na element (UIA `Click()` metod, sa `InvokePattern` fallback-om); zahtijeva `app` ili `title_contains` za lociranje prozora
- **`computer_set_text_element`** — postavlja tekst na element (`ValuePattern.SetValue`, sa `SendKeys` fallback-om)
- **`computer_get_element_text`** — čita tekst (`ValuePattern.Value`, fallback na `Name` properti)

Interni helperi:
- `_find_first_element(auto, criteria)` — nalazi prvi element koji match-uje kriterije (prvo traži prozor, onda pretražuje descendants)
- `_describe_element(el)` — bezbjedan dict summary UIA propertija

### `tool_registry.py` — `_register_phase14_tools()`

- 4 toola registrovana sa `requires_computer_mode=True`
- `computer_click_element` → `risk="high"`, `requires_confirmation=True`
- `computer_set_text_element` → `risk="high"`
- `computer_find_elements` i `computer_get_element_text` → `risk="medium"`, bez potvrde
- Svi `timeout_ms=15000` (UIA pozivi mogu biti sporiji)

### `electron/core/legacyTools.cjs`

- 4 FAZA 14 toola dodato u `TOOLS_WITH_PYTHON_EQUIVALENT`

### `electron/main.cjs`

- 4 FAZA 14 toola dodato u `PHASE11_DELEGATED_TOOLS`

### `RICKY_USE_LEGACY_POWERSHELL_TOOLS` default → 0

- Nakon FAZA 13 i 14, svi computer_* alati imaju Python ekvivalente
- Legacy PowerShell alati su sada **disabled by default**
- Može se re-enable sa `RICKY_USE_LEGACY_POWERSHELL_TOOLS=1`

### Testovi: `tests/test_phase14_element_targeting.py` (18 testova)

- 4 tool registration /tools listing
- 4 computer mode enforcement
- 4 `computer_find_elements` handler tests (no criteria, empty criteria, no windows found, finds by control type)
- 2 `computer_click_element` handler tests (no app/title raises, clicks element via Click())
- 3 `computer_set_text_element` handler tests (missing/empty text, no app/title raises)
- 3 `computer_get_element_text` handler tests (no app/title raises, ValuePattern read, fallback to Name)
- 1 regression: all 9 computer_* tools visible together
- Svi handler testovi koriste `patch.dict(sys.modules, {"uiautomation": MagicMock(...)})` za mock UIA sloja

## Nove zavisnosti

- `uiautomation==2.0.29` (pure-Python, nema C ekstenzija)
- `comtypes==1.4.16` (automatska zavisnost od `uiautomation`)

## Verifikacija

```text
pytest: 18/18 passed (novi testovi)
full suite: 172/172 passed (bez regresije)
typecheck: prošao
build: prošao
node --check: main.cjs + legacyTools.cjs clean
smoke: prošao
```

## Rizici/ograničenja

- **UIA je eksplorativno**: Windows UI Automation nije uvijek konzistentan među aplikacijama. Neki elementi mogu biti hidden/offscreen, neki pattern-i (ValuePattern, InvokePattern) možda nisu implementirani od strane aplikacije. Handleri imaju fallback mehanizme (`ValuePattern.SetValue` → `SendKeys`, `Click()` → `InvokePattern.Invoke()`), ali neke aplikacije mogu zahtijevati coordinate fallback (FAZA 13 `computer_click`).
- **Performanse**: UIA pretraga po `GetDescendants()` može biti spora za kompleksne prozore sa hiljadama elemenata. `max_results` limitira broj vraćenih elemenata, ali pretraga i dalje iterira kroz sve descendants. Buduća optimizacija: koristiti `FindAll` sa `PropertyCondition` umjesto Python list comprehension sa `GetDescendants()`.
- **`uiautomation` je nova zavisnost**: dodata je u Python environment; nije još deklarisana u `pyproject.toml` `dependencies` (treba dodati prije packaging-a).
- **Fallback na koordinate**: `computer_click` (FAZA 13) i dalje postoji kao fallback za slučajeve gdje UIA element targeting ne radi.