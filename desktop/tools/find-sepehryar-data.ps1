param(
    [string]$OutputPath = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Sepehryar-path-report.txt'),
    [string]$AppFolder
)

# Read-only discovery for the actual POS computer. It lists paths and metadata,
# but never changes files, opens database files, or connects to a database.
$ErrorActionPreference = 'Continue'
$report = [System.Collections.Generic.List[string]]::new()
$namePattern = '(?i)sepehr|sepehryar|sepand|food.?yar|mysql|maria|mssql|sql.?server|سپهر|فودیار'
$servicePattern = '(?i)sepehr|sepehryar|sepand|food.?yar|mysql|maria|mssql|sql.?server|sqlagent|sqlbrowser'

function Add-Report([string]$text) {
    $script:report.Add($text)
}

function Add-Heading([string]$title) {
    Add-Report ''
    Add-Report ('=== ' + $title + ' ===')
}

function Add-Candidate([string]$candidate) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Container)) { return }
    try {
        $folder = Get-Item -LiteralPath $candidate -Force -ErrorAction Stop
        Add-Report ('Folder: ' + $folder.FullName)
        $children = @(Get-ChildItem -LiteralPath $folder.FullName -Force -ErrorAction SilentlyContinue | Select-Object -First 40)
        $directories = @($children | Where-Object { $_.PSIsContainer } | ForEach-Object Name)
        if ($directories.Count) { Add-Report ('  Subfolders: ' + ($directories -join ', ')) }
        $files = @($children | Where-Object { -not $_.PSIsContainer })
        $signals = @('my.ini', 'my.cnf', 'ibdata1', 'aria_log_control', 'mysqld-auto.cnf')
        $present = @($files | Where-Object { $_.Name -in $signals } | ForEach-Object Name)
        if ($present.Count) { Add-Report ('  Database markers: ' + ($present -join ', ')) }
        $extensions = @($files | Where-Object Extension | Group-Object Extension | Sort-Object Count -Descending | Select-Object -First 8 | ForEach-Object { "$($_.Name):$($_.Count)" })
        if ($extensions.Count) { Add-Report ('  File extensions: ' + ($extensions -join ', ')) }
    } catch {
        Add-Report ('Folder (access denied): ' + $candidate)
    }
}

Add-Report ('Sepehryar path discovery - ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Add-Report ('Computer: ' + $env:COMPUTERNAME)
Add-Report 'This report contains paths and metadata only. Review it before sharing.'

Add-Heading 'Running processes'
try {
    $processes = @(Get-Process -ErrorAction Stop | Where-Object { $_.ProcessName -match $namePattern })
    if (-not $processes.Count) { Add-Report 'No matching process is running.' }
    foreach ($process in $processes) {
        $processPath = try { $process.Path } catch { '[unavailable]' }
        Add-Report ("$($process.ProcessName) (PID $($process.Id)): $processPath")
    }
} catch { Add-Report ('Could not inspect processes: ' + $_.Exception.Message) }

Add-Heading 'Windows services'
try {
    $services = @(Get-CimInstance Win32_Service -ErrorAction Stop | Where-Object { $_.Name -match $servicePattern -or $_.DisplayName -match $servicePattern })
    if (-not $services.Count) { Add-Report 'No matching service found.' }
    foreach ($service in $services) {
        Add-Report ("$($service.Name) / $($service.DisplayName): $($service.State)")
        # Only report these location switches; do not print the full service
        # command line because it might contain credentials.
        foreach ($match in [regex]::Matches($service.PathName, '(?i)--(defaults-file|datadir)\s*(?:=\s*|\s+)(?:"([^"]+)"|([^\s"]+))')) {
            $value = if ($match.Groups[2].Success) { $match.Groups[2].Value } else { $match.Groups[3].Value }
            Add-Report ("  $($match.Groups[1].Value): $value")
        }
    }
} catch { Add-Report ('Service details unavailable: ' + $_.Exception.Message) }

Add-Heading 'Installed applications'
$uninstallRoots = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
foreach ($root in $uninstallRoots) {
    Get-ItemProperty -Path $root -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -match $namePattern } |
        ForEach-Object { Add-Report ("$($_.DisplayName): $($_.InstallLocation)") }
}

Add-Heading 'Likely folders'
$roots = @(
    [Environment]::GetFolderPath('MyDocuments'),
    $env:ProgramData,
    $env:LOCALAPPDATA,
    $env:APPDATA,
    $env:ProgramFiles,
    [Environment]::GetEnvironmentVariable('ProgramFiles(x86)'),
    (Join-Path $env:USERPROFILE 'Desktop')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } | Select-Object -Unique

foreach ($root in $roots) {
    try {
        Get-ChildItem -LiteralPath $root -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match $namePattern } |
            ForEach-Object { Add-Candidate $_.FullName }
    } catch { }
}

if ($AppFolder) {
    Add-Heading 'Selected application folder'
    if (Test-Path -LiteralPath $AppFolder -PathType Container) {
        Add-Candidate $AppFolder
        Add-Report 'Configuration hints (passwords are redacted):'
        Get-ChildItem -LiteralPath $AppFolder -Filter '*.config' -File -Recurse -Depth 2 -ErrorAction SilentlyContinue |
            ForEach-Object {
                try {
                    $matches = @(Select-String -LiteralPath $_.FullName -Pattern 'connectionString|Data Source|Initial Catalog|Server=' -ErrorAction Stop)
                    if ($matches.Count) {
                        Add-Report ('  Config: ' + $_.FullName)
                        foreach ($match in $matches | Select-Object -First 10) {
                            $safeLine = $match.Line -replace '(?i)(password|pwd)\s*=\s*[^;\"'']+', '$1=[REDACTED]'
                            Add-Report ('    ' + $safeLine.Trim())
                        }
                    }
                } catch { Add-Report ('  Could not inspect config: ' + $_.FullName) }
            }
    } else {
        Add-Report ('Selected folder was not found: ' + $AppFolder)
    }
}

foreach ($drive in (Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue)) {
    if ($drive.Root -notmatch '^[A-Za-z]:\\$') { continue }
    try {
        Get-ChildItem -LiteralPath $drive.Root -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match $namePattern } |
            ForEach-Object { Add-Candidate $_.FullName }
    } catch { }
}

Add-Heading 'MySQL datadir in my.ini'
$configFiles = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($file in @('C:\my.ini', 'C:\Windows\my.ini')) {
    if (Test-Path -LiteralPath $file -PathType Leaf) { [void]$configFiles.Add($file) }
}

Add-Heading 'SQL Server data locations'
$sqlRoots = @(
    (Join-Path $env:ProgramFiles 'Microsoft SQL Server'),
    (Join-Path ([Environment]::GetEnvironmentVariable('ProgramFiles(x86)')) 'Microsoft SQL Server'),
    (Join-Path $env:ProgramData 'Microsoft\SQL Server')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } | Select-Object -Unique
foreach ($root in $sqlRoots) {
    Add-Report ('SQL Server root: ' + $root)
    Get-ChildItem -LiteralPath $root -Force -Directory -ErrorAction SilentlyContinue | Select-Object -First 20 |
        ForEach-Object { Add-Report ('  Folder: ' + $_.FullName) }
}
foreach ($root in @((Join-Path $env:ProgramData 'MySQL'), (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'MySQL'))) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
    Get-ChildItem -LiteralPath $root -Filter 'my.ini' -File -Recurse -Depth 3 -ErrorAction SilentlyContinue |
        ForEach-Object { [void]$configFiles.Add($_.FullName) }
}
foreach ($file in $configFiles) {
    Add-Report ('Config: ' + $file)
    try {
        Get-Content -LiteralPath $file -ErrorAction Stop |
            Where-Object { $_ -match '^\s*datadir\s*=' } |
            ForEach-Object { Add-Report ('  ' + $_.Trim()) }
    } catch { Add-Report '  Could not read datadir setting.' }
}

Add-Heading 'Next checks'
Add-Report 'In Sepehryar: note the exact product/version and the Backup or Sales Export path.'
Add-Report 'The Data.rar shown for this installation contains SQL Server database files; it is likely an old backup, not proof of the current live database location.'
Add-Report 'Do not copy a live .mdf/.ldf file while the accounting application or SQL Server is running.'

$report | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output ('Report saved to: ' + $OutputPath)
