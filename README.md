# RileyJarvis (Windows port)

This is a Windows port of [RileyJarvis](https://github.com/rileybrown/rileyjarvis) — a local Electron desktop AI companion with realtime voice, a visual artifact panel, image generation, web search, notes, and opt-in Windows computer control.

It is built with Electron, React, Vite, TypeScript, and the OpenAI Realtime API.

The original project only supported macOS because its computer-use tools were implemented with AppleScript (`osascript`), `screencapture`, and `open -a`. In this port, `electron/main.cjs` implements those same tools using Windows APIs invoked through PowerShell (`SendKeys` for typing/keys, `user32.dll` P/Invoke for mouse click/scroll, `System.Drawing` for screenshots, `GetForegroundWindow`/`GetWindowText` for UI inspection). No native npm modules or extra installs are required — only the `powershell.exe` that ships with Windows.

## Features

- Realtime speech-to-speech conversation with OpenAI Realtime.
- Animated companion face with listening, thinking, speaking, and working states.
- Artifact panel for markdown, menus, notes, Mermaid diagrams, generated images, records, and progress.
- YouTube thumbnail board with persistent numbered generations and image edits.
- Optional Exa-powered web search.
- Local notes and records stored at runtime under `data/`.
- Optional computer-use mode for opening apps, clicking, typing, scrolling, screenshots, and UI inspection on Windows.

## Requirements

- Windows 10/11
- Node.js 20+
- npm
- An OpenAI API key with Realtime and image generation access
- Optional: an Exa API key for web search

## Quick Start

```bash
git clone https://github.com/rileybrown/rileyjarvis.git
cd rileyjarvis
npm install
cp .env.example .env.local
npm run dev
```

Edit `.env.local` before starting voice features:

```bash
OPENAI_API_KEY=your_openai_api_key_here
EXA_API_KEY=your_exa_api_key_here
```

`OPENAI_API_KEY` is required. `EXA_API_KEY` is optional; web search will show a setup message when it is missing.

## Windows Permissions and Notes

RileyJarvis runs locally. Depending on the features you use, Windows may ask for:

- Microphone permission for voice conversation (Settings > Privacy & security > Microphone, and the in-app prompt on first use).
- A firewall prompt the first time the app makes a network request (Realtime API, image generation, web search).

Computer-control tools are blocked until the app is in computer-use mode. They run short PowerShell scripts via `powershell.exe -ExecutionPolicy Bypass -Command ...` scoped to that single process call — this does not change your system-wide PowerShell execution policy. If antivirus software flags these calls, allow them for this app or review `electron/main.cjs`.

`computer_open_app` uses `Start-Process <name>`, which works for apps that are on `PATH` or have a registered App Execution Alias (e.g. `notepad`, `calc`, `mspaint`, `chrome`, `code`). Store-only apps without an alias may not open by name.

## Desktop shortcut

After `npm install`, double-click `Napravi-Precicu-Desktop.bat` once — it
creates a `Ricky` shortcut on your Desktop pointing at `Pokreni-Ricky.bat`
in this exact folder, with the Electron icon. Safe to re-run any time
(e.g. after moving the folder) to refresh the shortcut's target path.

## Development

```bash
npm run dev
```

This starts Vite on `127.0.0.1:5173` and launches Electron. Double-click
`Pokreni-Ricky.bat` (or the Desktop shortcut) to run the same thing without
opening a terminal manually.

Other useful commands:

```bash
npm run typecheck
npm run build
npm start
```

## Runtime Data

The app creates a local `data/` directory for notes, records, generated images, and thumbnail-board state. That directory is intentionally ignored by Git.

Do not commit:

- `.env.local`
- Anything under `data/`
- `dist/`
- `node_modules/`

## Security Notes

- API keys are loaded only from local environment files.
- `.env.local` and all `.env.*` files are ignored except `.env.example`.
- Generated images and local database files are ignored.
- Risky computer-control actions should require explicit confirmation.
- Typing and pressing Enter in computer-use mode are intentionally allowed without extra confirmation because they are core voice-control actions.

Before publishing a fork, run:

```bash
npm run typecheck
npm run build
git status --short
```

Then verify that no local secrets or runtime data are staged.

## License

MIT
