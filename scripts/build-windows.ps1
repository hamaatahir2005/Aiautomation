$ErrorActionPreference = 'Stop'
function Assert-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed with exit $LASTEXITCODE" } }
python -m pip install -r backend/requirements-video.txt pyinstaller==6.14.1 pytest
Assert-Exit
python -m pytest backend/tests -q
Assert-Exit
npm ci
Assert-Exit
python -m PyInstaller --noconfirm --onedir --name aios-backend --distpath build --workpath build/pyinstaller --paths backend --collect-all imageio_ffmpeg --collect-all faster_whisper --collect-all scenedetect --collect-all ctranslate2 --collect-submodules keyring.backends --hidden-import win32timezone backend/run.py
Assert-Exit
if (Test-Path build/backend) { Remove-Item build/backend -Recurse -Force }
Rename-Item build/aios-backend backend
npm run package:win
Assert-Exit
if (!(Test-Path release/AI-Company-OS-Setup.exe)) { throw 'Installer was not generated' }
Get-FileHash release/AI-Company-OS-Setup.exe -Algorithm SHA256 | Format-List
