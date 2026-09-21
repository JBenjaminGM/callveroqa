<#
  publish-clean.ps1 - Publica una copia LIMPIA del repo al repositorio publico `callqa`.

  Toma el estado COMMITEADO de `main` del repo completo (privado) y lo espeja al
  repo limpio, quitando toda la documentacion/meta (docs/, *.md de metodologia,
  AGENTS.md, CLAUDE.md, la carpeta ops/) y dejando solo el codigo funcional + un
  unico README curado. El repo limpio tiene su PROPIO historial (sin rastro de
  autoria). No toca el repo completo.

  Uso:
    # primera vez (crea el repo local + remoto):
    ./ops/publish-clean.ps1 -RemoteUrl "https://github.com/JBenjaminGM/callqa.git" -Message "CallVeroQA"
    # siguientes veces:
    ./ops/publish-clean.ps1 -Message "Mejoras en el dashboard"
#>
param(
  [string]$CleanDir  = "C:\Users\Benja\Documents\callqa",
  [string]$RemoteUrl = "",
  [string]$Message   = "Actualizar plataforma",
  [switch]$NoPush
)
$ErrorActionPreference = "Stop"

# Raiz del repo completo (privado) = carpeta padre de ops/.
$Full = Split-Path $PSScriptRoot -Parent
$readme = Join-Path $PSScriptRoot "clean-README.md"

Write-Host "Repo completo (origen): $Full"
Write-Host "Repo limpio (destino):  $CleanDir"

# 1) Asegurar que el repo limpio existe como repositorio git.
if (-not (Test-Path (Join-Path $CleanDir ".git"))) {
  New-Item -ItemType Directory -Force -Path $CleanDir | Out-Null
  git -C $CleanDir init -b main | Out-Null
  # Autor humano (no hereda ninguna identidad de IA).
  git -C $CleanDir config user.name  "JBenjaminGM"
  git -C $CleanDir config user.email "josbegm@gmail.com"
  Write-Host "Repo limpio inicializado."
}
if ($RemoteUrl) {
  if (git -C $CleanDir remote) { git -C $CleanDir remote set-url origin $RemoteUrl }
  else { git -C $CleanDir remote add origin $RemoteUrl }
  Write-Host "Remoto: $RemoteUrl"
}

# 2) Vaciar el arbol de trabajo (conservando .git) para reflejar bajas tambien.
Get-ChildItem -Force $CleanDir | Where-Object { $_.Name -ne ".git" } |
  Remove-Item -Recurse -Force

# 3) Exportar el estado commiteado de `main` del repo completo.
$tar = Join-Path $env:TEMP "callqa-clean.tar"
git -C $Full archive --format=tar main -o $tar
tar -xf $tar -C $CleanDir
Remove-Item $tar -Force

# 4) Quitar documentacion/meta (todo lo que cuenta de mas).
$strip = @("docs", "ops", "AGENTS.md", "CLAUDE.md", "README.md",
           "backend\README.md", "frontend\README.md")
foreach ($p in $strip) {
  $fp = Join-Path $CleanDir $p
  if (Test-Path $fp) { Remove-Item -Recurse -Force $fp }
}
# Red de seguridad: cualquier otro .md que no sea el README raiz.
Get-ChildItem -Path $CleanDir -Recurse -Filter *.md -File -Force |
  Where-Object { $_.FullName -ne (Join-Path $CleanDir "README.md") } |
  Remove-Item -Force

# 5) README curado (unico documento del repo limpio).
Copy-Item $readme (Join-Path $CleanDir "README.md") -Force

# 6) Commit + push (historial propio, sin rastro de autoria).
git -C $CleanDir add -A
$pending = git -C $CleanDir status --porcelain
if ($pending) {
  git -C $CleanDir commit -m $Message | Out-Null
  Write-Host "Commit: $Message"
} else {
  Write-Host "Sin cambios que publicar."
}
if (-not $NoPush) {
  git -C $CleanDir push -u origin main
  Write-Host "Push a origin/main hecho."
}
Write-Host "OK - repo limpio actualizado en $CleanDir"
