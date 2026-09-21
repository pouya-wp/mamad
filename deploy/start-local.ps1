# Starts the local ONE CAFE stack: ERPNext (Docker in WSL) + the panel dev server.
# Usage (PowerShell):  .\deploy\start-local.ps1
# Hiddify must be ON (Docker Hub / HTTPS inside WSL go through it).

$ErrorActionPreference = 'Stop'
$env:WSL_UTF8 = '1'
$root = Split-Path -Parent $PSScriptRoot
$compose = '-f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/frappe_docker/pwd.yml -f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/deploy/compose.cafe-dev.yaml'

Write-Host 'Starting ERPNext containers...'
wsl -d Ubuntu-24.04 -- bash -lc "docker compose $compose up -d"

Write-Host 'Waiting for the backend...'
for ($i = 0; $i -lt 60; $i++) {
  $ok = wsl -d Ubuntu-24.04 -- bash -lc "docker compose $compose exec -T backend curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/method/ping"
  if ($ok -eq '200') { break }
  Start-Sleep -Seconds 3
}

# nginx resolves "backend" once at startup; if it started before Docker DNS knew the name,
# Hiddify's fake-IP DNS answered and every API call returns 502. Restarting fixes the cache.
Write-Host 'Refreshing nginx upstreams...'
wsl -d Ubuntu-24.04 -- docker restart frappe_docker-frontend-1 | Out-Null
Start-Sleep -Seconds 4

try {
  $ping = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/api/method/ping' -TimeoutSec 30
  Write-Host "ERPNext is up ($($ping.StatusCode)) -> http://127.0.0.1:8080"
} catch {
  Write-Warning "ERPNext did not answer yet: $($_.Exception.Message)"
}

Write-Host 'Starting the panel -> http://127.0.0.1:5173'
Set-Location (Join-Path $root 'panel')
npm run dev
