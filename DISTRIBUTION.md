# Studaxis Distribution Guide

This document explains how to build the Studaxis Windows installer: a single `.exe` that bundles the Python/FastAPI backend and React frontend, plus an Inno Setup installer for deployment.

## Prerequisites

- **Python 3.9+** with dependencies: `pip install -r requirements.txt`
- **Node.js** for the frontend build
- **PyInstaller**: `pip install pyinstaller`
- **Inno Setup 6** (for the installer): [https://jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)
- **Ollama** installed on target machines for AI features

## Build Steps

### 1. Build the React Frontend

The PyInstaller spec expects `frontend/dist` to exist:

```powershell
cd frontend
npm install
npm run build
cd ..
```

### 2. Run PyInstaller

Build the standalone executable:

```powershell
pyinstaller studaxis.spec
```

Output: `dist/Studaxis.exe`

#### What the spec does

- **Entry point**: `run.py` — starts FastAPI via uvicorn, runs hardware check, opens browser
- **Bundled data**:
  - `frontend/dist` → SPA served at `/`
  - `backend/data/sample_textbooks/*` → seed data copied to `%APPDATA%/Studaxis` on first run
- **Hidden imports**: psutil, uvicorn, chromadb, langchain, langchain-chroma, langchain-ollama, etc.
- **Console**: `--noconsole` — no CLI window; browser opens automatically

### 3. Build the Inno Setup Installer

Ensure `dist/Studaxis.exe` exists, then compile the installer:

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup_script.iss
```

Output: `dist/Studaxis-Setup-1.0.0.exe`

#### Installer behavior

- Installs `Studaxis.exe` under `%ProgramFiles%\Studaxis`
- Creates **Desktop shortcut** (optional, unchecked by default)
- **Post-install**: offers to run Studaxis once to pull the Ollama model based on detected RAM (4GB vs 8GB+)

## Asset Management

### User data location

When running from the `.exe`, data is stored in:

```
%APPDATA%\Studaxis\
├── data\
│   ├── profile.json
│   ├── sample_textbooks\
│   ├── chromadb\
│   ├── backups\
│   └── users\
```

### First-run bootstrap

On first launch, the executable:

1. Creates `%APPDATA%\Studaxis\data` and subdirectories
2. Copies bundled sample textbooks into `data/sample_textbooks` if empty
3. Triggers the hardware check (RAM detection)
4. Opens the browser; the app then prompts for Ollama model pull if needed

## Customization

### Icon

- **PyInstaller**: set `icon='studaxis.ico'` in `studaxis.spec` (place `studaxis.ico` in the project root)
- **Inno Setup**: uncomment `SetupIconFile=studaxis.ico` in `setup_script.iss` for a custom installer icon  
  You can convert `frontend/public/pwa-512x512.png` to `.ico` using an online tool or ImageMagick.

### Version

Update `#define MyAppVersion` in `setup_script.iss` for the installer.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `frontend/dist not found` | Run `cd frontend && npm run build` first |
| `ModuleNotFoundError` in exe | Add the module to `hiddenimports` in `studaxis.spec` |
| Ollama model not found | Run `ollama serve`, then `ollama pull llama3.2:3b-instruct-q2_K` (4GB) or `ollama pull llama3.2:3b-instruct-q4_K_M` (8GB+) |
| Port 6782 in use | Pass `--port 8001` when launching (requires source run; exe uses 6782) |

## Quick Reference

```powershell
# Full build
cd frontend && npm install && npm run build && cd ..
pyinstaller studaxis.spec
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup_script.iss
```
