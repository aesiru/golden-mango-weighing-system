$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $PSScriptRoot '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
  Write-Host 'Creating Python virtual environment...' -ForegroundColor Yellow
  if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $venv }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv $venv }
  else { Write-Error 'Python 3 not found. Install Python 3.11+.'; exit 1 }

  Write-Host 'Installing backend dependencies...' -ForegroundColor Yellow
  & $venvPython -m pip install --upgrade pip setuptools wheel
  & $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
}

# Run uvicorn in foreground
& $venvPython -m uvicorn app.main:app --reload --port 8000
