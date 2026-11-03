# AI Company OS Ultimate Edition

A local Windows desktop application built with Electron, React/TypeScript, an interactive Three.js office and a FastAPI/SQLAlchemy backend. This repository contains functional application code, not a hosted dashboard.

**Release status:** development. A Windows installer is only verified when the **Windows installer** workflow completes, including its packaged backend, installation and window launch checks. Download `AI-Company-OS-Windows-x64` from the successful Actions run and extract `AI-Company-OS-Setup.exe`. Do not confuse a source checkout with a built installer.

## Development

Python 3.12, Node 22+, FFmpeg (or bundled imageio-ffmpeg).

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
pip install -r backend/requirements-video.txt pytest
npm ci
npm run build
# Run Electron from the activated Python environment:
npm run desktop
```

Set `AIOS_PYTHON` to a Python executable when using a virtual environment without activation. Browser-only Vite mode is for layout development; the desktop bridge is required for business operations.

## Windows build

Run `scripts/build-windows.ps1` in PowerShell on Windows 10/11 x64. PyInstaller bundles Python and the backend dependencies; electron-builder produces the NSIS installer. FFmpeg is bundled through imageio-ffmpeg. Whisper weights download on first transcription. End users need neither Python nor Node. The installer currently has no publisher certificate: Windows SmartScreen may show an unknown-publisher warning.

See [installation](docs/INSTALLATION.md), [security](docs/SECURITY.md), [acceptance status](docs/ACCEPTANCE.md), and [implementation plan](IMPLEMENTATION_PLAN.md).
