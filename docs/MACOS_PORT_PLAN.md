# macOS podrška — analiza kompleksnosti (za kasnije)

## Kontekst

RileyJarvis je originalno bio macOS-only Electron app. Windows port (vidi `WINDOWS-PORT-NOTES.md` u root-u repo-a) je zamijenio sve macOS-specifične "computer-use" shell pozive (`osascript`, `screencapture`, `open -a`) sa PowerShell ekvivalentima. Ovaj dokument procjenjuje koliko bi bilo komplikovano vratiti/dodati macOS podršku, u kontekstu trenutne hibridne migracije (`docs/MIGRATION_PLAN.md`).

Nije aktivan zadatak — arhivirano za kasnije, ako/kad macOS podrška postane prioritet.

## Procjena po slojevima

### Već besplatno / bez izmjena

- **Electron shell** — cross-platform po defaultu. U kodu već postoji neobrisan ostatak macOS logike iz originalnog projekta: `app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); })`.
- **Voice/AI jezgro** (`src/lib/realtime.ts`) — WebRTC + browser API pozivi direktno ka OpenAI Realtime API. Potpuno OS-agnostično, nula izmjena potrebno.
- **IPC/tool contract, React UI, artifact panel** — OS-agnostično.

### Srednja komplikacija — computer-use alati u trenutnoj (Electron/PowerShell) arhitekturi

`electron/tools_legacy/powershell/*.cjs` (izdvojeno u FAZI 3) je 100% Windows-specifično (`SendKeys`, `user32.dll` P/Invoke). Za macOS bi trebalo napraviti paralelan set preko AppleScript-a (`osascript`) — isto što je originalni app radio prije Windows porta (vidi tabelu u `WINDOWS-PORT-NOTES.md`: `open -a`, AppleScript `keystroke`, AppleScript click, `screencapture`, AppleScript + Accessibility).

Posao: 7 tool fajlova × drugi dijalekt (AppleScript umjesto PowerShell), plus `process.platform` grananje pri učitavanju odgovarajućeg seta, plus testiranje na stvarnom Mac uređaju.

### Preporuka — ne raditi ovo u trenutnoj Electron/PowerShell arhitekturi

Bolje sačekati Python tool sloj (FAZA 10-12 iz `docs/MIGRATION_PLAN.md`):

- `pyautogui`/`pynput` (tastatura, miš) i `mss` (screenshot) su već cross-platform — ista Python implementacija bi radila na Windows i macOS gotovo bez izmjena.
- Jedini dio koji ostaje suštinski različit po OS-u je **UI element targeting** (FAZA 13) — `pywinauto`/UIA je Windows-only; macOS ekvivalent je `pyobjc` + Accessibility API, potpuno druga biblioteka i drugačiji API oblik.

Zaključak: ako je macOS podrška realan cilj, najjeftiniji put je odraditi Python computer-use sloj sa cross-platform bibliotekama od početka, umjesto da se sada duplira PowerShell sloj u AppleScript verziju koja bi ionako kasnije bila zamijenjena Python alatima.

### Packaging

`electron-builder` i `PyInstaller`/`Nuitka` podržavaju macOS build (`.dmg`/`.app`), ali praktična prepreka je što treba **stvaran Mac** (ili macOS CI runner) da se build-uje, testira i — za širu distribuciju — notarizuje/potpiše. Ovo se ne može uraditi sa Windows mašine.

## Kad ovo razmotriti

- Nakon FAZE 12 (Python computer-use v1), kad postoji Python implementacija tastature/miša/screenshot-a — provjeriti koliko je zaista "besplatno" prenosiva na macOS.
- Prije bilo kakvog packaging rada za macOS (FAZA 18 ekvivalent) — potreban je pristup Mac hardveru/CI-ju.

## Vidi i

- `WINDOWS-PORT-NOTES.md` (root repo-a) — originalna macOS→Windows tabela zamjena.
- [WINDOWS_AUTOMATION_NOTES.md](./WINDOWS_AUTOMATION_NOTES.md) — trenutni i planirani Windows automation sloj.
- [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) — FAZA 10-13 (Python screenshot/computer-use/UI targeting).
