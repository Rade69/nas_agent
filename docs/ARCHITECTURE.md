# Arhitektura — RileyJarvis Windows Hybrid

## Ciljna arhitektura

```text
React UI
  -> Electron preload / IPC
  -> Electron main process kao tanak shell/bridge
  -> Python backend kao mozak aplikacije
  -> Python tools: Windows automation, screenshot, UI inspect, storage, agent runtime, artifacts
  -> SQLite lokalna baza, logs, lokalni fajlovi
```

Cilj nije full rewrite. Cilj je postepeno izvlačenje logike iz `electron/main.cjs` u modularan Python backend, bez rušenja postojećeg UI-ja.

## Podjela odgovornosti

### React renderer = UI

- glavni prozor aplikacije, frameless UI,
- toolbar i mode switch,
- artifact panel,
- prikaz razgovora,
- IPC komunikacija sa main procesom.

### Electron main process = app shell + IPC bridge + Python process manager

- createWindow, app lifecycle,
- IPC setup,
- pokretanje/gašenje Python backend procesa,
- prosljeđivanje eventa iz Python backend-a prema React UI-ju.

`electron/main.cjs` **ne smije** ostati mozak aplikacije i ne smije dobijati novu poslovnu logiku, agent logiku, computer-use logiku, storage logiku ili AI-service logiku.

### Python backend = agent runtime + tools + storage + automation + AI integracije

- agent runtime, tool registry, tool execution,
- Windows automation (screenshot, ui inspect, tastatura, miš),
- memorija, action log, SQLite storage,
- AI model/API pozivi (OpenAI, Exa),
- permission/risk/confirmation sloj,
- artifact generation.

### SQLite = lokalno perzistentno skladište

Sve trajne podatke (tool_runs, artifacts, notes, records, settings, conversations) čuva Python backend u SQLite bazi.

### WebSocket/events = backend -> UI updates

Python backend šalje evente (tool progress, artifact created/updated, permission required) ka UI-ju preko WebSocket-a (ili polling fallback-a ako WebSocket nije stabilan).

### REST/HTTP = request/response tool execution

Electron poziva Python backend preko REST/HTTP endpointa (`/health`, `/tools`, `/tools/execute`, `/agent/message`) za sinhrone request/response operacije.

## Vidi i

- [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) — fazni plan implementacije.
- [TOOL_CONTRACTS.md](./TOOL_CONTRACTS.md) — standardni format tool definicija/poziva.
- [SECURITY_MODEL.md](./SECURITY_MODEL.md) — risk levels i permission pravila.
- [WINDOWS_AUTOMATION_NOTES.md](./WINDOWS_AUTOMATION_NOTES.md) — beleške o Windows automation slojevima (legacy PowerShell i planirani Python).
- [PACKAGING_PLAN.md](./PACKAGING_PLAN.md) — plan za instalabilni Windows build.
- [RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md](./RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md) — puni izvorni dokument sa svim fazama, iz kojeg su ovi fajlovi izvučeni.
