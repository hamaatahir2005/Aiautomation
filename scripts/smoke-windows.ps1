$ErrorActionPreference = 'Stop'
$env:AIOS_DATA = Join-Path $env:RUNNER_TEMP 'aios-smoke-data'
$env:AIOS_SESSION_TOKEN = [guid]::NewGuid().ToString()
$env:AIOS_PORT = '18765'
$proc = Start-Process build/backend/aios-backend.exe -PassThru
try {
  $ready = $false
  for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    try { $health = Invoke-RestMethod http://127.0.0.1:18765/health -Headers @{Authorization="Bearer $env:AIOS_SESSION_TOKEN"}; if ($health.status -eq 'ok') { $ready=$true; break } } catch {}
  }
  if (!$ready) { throw 'Packaged backend failed to launch' }
} finally { Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue }
$installer = Start-Process release/AI-Company-OS-Setup.exe -ArgumentList '/S' -PassThru -Wait
if ($installer.ExitCode -ne 0) { throw 'Silent installation failed' }
$exe = Join-Path $env:LOCALAPPDATA 'Programs/AI Company OS/AI Company OS.exe'
if (!(Test-Path $exe)) { throw "Installed application missing at $exe" }
node scripts/desktop-smoke.cjs
if ($LASTEXITCODE -ne 0) { throw 'Installed desktop UI acceptance failed' }
