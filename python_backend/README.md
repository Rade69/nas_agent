# RileyJarvis Python Backend

Minimal FastAPI backend skeleton for FAZA 4.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

## Tests

```powershell
pytest
```

## Endpoints

- `GET /health`
- `GET /tools`
- `POST /tools/execute`

FAZA 4 intentionally does not connect this backend to Electron.
