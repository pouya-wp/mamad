# Read-only, top-level Downloads inventory for the current Windows account.
$ErrorActionPreference = 'Stop'
$offset = 0
$limit = 1000
$downloadsKey = '{374DE290-123F-4565-9164-39C4925E467B}'
$downloads = $null
try {
    $folders = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
    $downloads = [Environment]::ExpandEnvironmentVariables([string]$folders.$downloadsKey)
} catch { }
if ([string]::IsNullOrWhiteSpace($downloads)) {
    $downloads = Join-Path $env:USERPROFILE 'Downloads'
}
if (-not (Test-Path -LiteralPath $downloads -PathType Container)) {
    throw "Downloads directory does not exist: $downloads"
}
$entries = @(Get-ChildItem -LiteralPath $downloads -Force -ErrorAction Stop | Sort-Object Name)
$files = @($entries | Where-Object { -not $_.PSIsContainer })
$page = @($entries | Select-Object -Skip $offset -First $limit | ForEach-Object {
    [pscustomobject]@{
        name = $_.Name
        type = if ($_.PSIsContainer) { 'directory' } else { 'file' }
        bytes = if ($_.PSIsContainer) { $null } else { $_.Length }
    }
})
[pscustomobject]@{
    machine = $env:COMPUTERNAME
    account = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    downloads = $downloads
    totalEntries = $entries.Count
    totalFiles = $files.Count
    totalFileBytes = ($files | Measure-Object -Property Length -Sum).Sum
    offset = $offset
    returned = $page.Count
    hasMore = ($offset + $page.Count -lt $entries.Count)
    entries = $page
} | ConvertTo-Json -Depth 5 -Compress
