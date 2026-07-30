Write-Host "Scaffolding warehouse entities..." -ForegroundColor Green

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path (Join-Path -Path $scriptDir -ChildPath "backend")

# Activate virtual environment
if (Test-Path ".venv") {
    . .venv\Scripts\Activate.ps1
} elseif (Test-Path "venv") {
    . venv\Scripts\Activate.ps1
} else {
    Write-Host "Virtual environment not found. Please run install.sh or run.sh first." -ForegroundColor Red
    exit 1
}

# Scaffold Entities
python -m app.forge new-entity company --module warehouse --fields "name:string,contact_infos:string"
python -m app.forge new-entity crate_class --module warehouse --fields "name:string,min_weight:float,max_weight:float"
python -m app.forge new-entity order --module warehouse --fields "company:link,crate_class:link,total_amount:float,current_amount:float"
python -m app.forge new-entity crate --module warehouse --fields "code:string,order:link,crate_class:link,target:float,counted:float"
python -m app.forge new-entity reading --module warehouse --fields "crate:link,weight_kg:float,recorded_at:date,valid:boolean"

Write-Host "`nSyncing schema to the database..." -ForegroundColor Green
$env:PYTHONUTF8 = "1"
python -m app.forge sync

Write-Host "`nGenerating TypeScript types for frontend..." -ForegroundColor Green
python -m app.forge generate-types

Write-Host "`nScaffolding complete!" -ForegroundColor Green
