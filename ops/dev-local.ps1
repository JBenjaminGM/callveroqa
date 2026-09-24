<#
.SYNOPSIS
  Levanta CallVeroQA en local SIN Docker.

.DESCRIPTION
  Pensado para una maquina sin WSL2 (o con Docker Desktop aun sin arrancar):
  PostgreSQL portatil (paquete pip `pgserver`, sin servicio de Windows) + API
  FastAPI en modo inline (sin Celery/Redis, igual que en Render) + frontend
  Next.js servido desde su build de produccion.

  Para el stack completo con Docker usa `docker compose up -d --build` en la
  raiz del repositorio: eso si levanta postgres, redis, api, worker y frontend.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File ops\dev-local.ps1
  powershell -ExecutionPolicy Bypass -File ops\dev-local.ps1 -Stop
#>
param(
    # Para la API, el frontend y PostgreSQL, y sale.
    [switch]$Stop,
    # Carpeta de trabajo para la base portatil y los audios (fuera del repo).
    [string]$DataRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
)

$ErrorActionPreference = 'Stop'

# PATH fresco: node/python recien instalados no estan en consolas antiguas.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')

$repo    = Split-Path $PSScriptRoot -Parent
$pgTools = Join-Path $DataRoot '.pgtools'
$pgData  = Join-Path $DataRoot '.pgdata'
$audios  = Join-Path $DataRoot '.audios'
$bin     = Join-Path $pgTools 'Lib\site-packages\pgserver\pginstall\bin'

function Stop-App {
    # Una instancia vieja ocupa el puerto y sirve un build que ya no existe
    # (sintoma: pagina en blanco con 404 de todos los chunks).
    Get-CimInstance Win32_Process |
        Where-Object {
            ($_.Name -eq 'node.exe' -and $_.CommandLine -match [regex]::Escape((Join-Path $repo 'frontend'))) -or
            ($_.CommandLine -match 'uvicorn app\.main')
        } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

if ($Stop) {
    Stop-App
    & "$bin\pg_ctl.exe" -D $pgData stop 2>$null
    Write-Host 'CallVeroQA detenido.'
    return
}

Stop-App

# --- PostgreSQL portatil ---
if (-not (Test-Path $bin)) {
    throw "Falta PostgreSQL portatil en $pgTools. Crealo con:`n" +
          "  py -3.11 -m venv `"$pgTools`"; & `"$pgTools\Scripts\python.exe`" -m pip install pgserver"
}
& "$bin\pg_ctl.exe" -D $pgData status *> $null
if ($LASTEXITCODE -ne 0) {
    & "$bin\pg_ctl.exe" -D $pgData -l (Join-Path $pgData 'server.log') `
        -o "-p 5432 -c listen_addresses=localhost" start
}

New-Item -ItemType Directory -Force $audios | Out-Null

# --- API (migraciones + servidor) ---
$apiCmd = @"
`$env:PYTHONIOENCODING='utf-8'
`$env:DATABASE_URL='postgresql://callveroqa:callveroqa@localhost:5432/callveroqa'
`$env:PROCESS_INLINE='true'
`$env:STORAGE_PATH='$audios'
Set-Location '$repo\backend'
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
"@
Start-Process powershell -ArgumentList '-NoExit', '-Command', $apiCmd

# --- Frontend (build de produccion; recuerda `npm run build` tras cambiar UI) ---
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$repo\frontend'; npm start"

Write-Host 'App: http://localhost:3000  ·  API: http://localhost:8000/docs'
