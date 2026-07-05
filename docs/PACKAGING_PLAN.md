# Packaging plan — RileyJarvis Windows Hybrid

## Cilj

Napraviti instalabilnu Windows aplikaciju **tek kada** hibridna arhitektura radi stabilno i legacy PowerShell toolovi su isključeni po defaultu (nakon FAZE 16/17).

Ne startovati packaging prije toga — trenutna app je i dalje dev-mode pokretanje (`npm run dev`), ne pravi instalabilni `.exe`.

## Opcije za Python packaging

```text
PyInstaller
Nuitka
```

## Finalna struktura

```text
Ricky/
  Ricky.exe
  resources/
    app.asar
    python_backend/
      ricky_backend.exe
      data/
      logs/
```

Electron u produkciji startuje:

```text
resources/python_backend/ricky_backend.exe --host 127.0.0.1 --port 8765
```

## Acceptance criteria

- Korisnik ne mora instalirati Python.
- App se pokreće duplim klikom.
- Backend se pokreće i gasi zajedno sa app-om.
- `.env.local` i API ključevi nisu upakovani slučajno.

## Status

Nije započeto. Preduslov: FAZA 0–17 (vidi [MIGRATION_PLAN.md](./MIGRATION_PLAN.md)).
