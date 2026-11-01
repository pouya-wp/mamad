# Read-only network check for the PC where ONE CAFE cannot load or sign in.
# No password, database data, or local files are read or sent.
$ErrorActionPreference = 'Continue'
$hostName = 'onecafe.beyondex.one'
$originIp = '95.38.191.245'

Write-Output "ONE CAFE connection check - $(Get-Date -Format o)"
Write-Output "Computer: $env:COMPUTERNAME"

foreach ($dnsServer in @('system', '1.1.1.1', '8.8.8.8')) {
    try {
        $options = @{ Name = $hostName; Type = 'A'; ErrorAction = 'Stop' }
        if ($dnsServer -ne 'system') { $options.Server = $dnsServer }
        $addresses = @(Resolve-DnsName @options | Where-Object Type -eq 'A' | Select-Object -ExpandProperty IPAddress -Unique)
        Write-Output "DNS ${dnsServer}: $($addresses -join ', ')"
    } catch {
        Write-Output "DNS ${dnsServer}: FAILED - $($_.Exception.Message)"
    }
}

try {
    $tcp = Test-NetConnection -ComputerName $hostName -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    Write-Output "TCP 443: $tcp"
} catch {
    Write-Output "TCP 443: FAILED - $($_.Exception.Message)"
}

$format = 'HTTP %{http_code}; remote %{remote_ip}; DNS %{time_namelookup}s; TCP %{time_connect}s; TLS %{time_appconnect}s; first byte %{time_starttransfer}s; total %{time_total}s'
Write-Output 'HTTPS via current DNS:'
& curl.exe -4 -sS -L -o NUL -w "$format`n" --connect-timeout 8 --max-time 20 "https://$hostName/"
Write-Output "curl exit: $LASTEXITCODE"

Write-Output 'HTTPS with DNS bypassed, certificate still verified:'
& curl.exe -4 -sS -L -o NUL -w "$format`n" --resolve "${hostName}:443:${originIp}" --connect-timeout 8 --max-time 20 "https://$hostName/"
Write-Output "curl exit: $LASTEXITCODE"

Write-Output 'Guest API (HTTP 401 is expected):'
& curl.exe -4 -sS -o NUL -w "$format`n" --connect-timeout 8 --max-time 20 "https://$hostName/api/method/cafe_app.api.session.boot"
Write-Output "curl exit: $LASTEXITCODE"
