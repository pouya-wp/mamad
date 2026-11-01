$ErrorActionPreference = 'Stop'
[pscustomobject]@{
    ComputerName = $env:COMPUTERNAME
    CheckedAt = (Get-Date).ToString('o')
    SqlServices = @(Get-Service -Name 'MSSQL*' -ErrorAction SilentlyContinue | Select-Object Name, Status)
    SqlCmdAvailable = [bool](Get-Command sqlcmd -ErrorAction SilentlyContinue)
} | ConvertTo-Json -Depth 4 -Compress

# Read-only counts/IDs; short lock and query timeouts on the active till database.
& sqlcmd -S '.\SEPANDYAR2014' -E -d 'Sepand_One_1405' -l 5 -t 10 -b -W -s '|' -Q 'SET LOCK_TIMEOUT 3000; SET NOCOUNT ON; SELECT TOP 5 DateFactor, COUNT_BIG(*) AS InvoiceCount, MAX(FactorID) AS LastFactor FROM dbo.Day_Factor WHERE ISNULL(Cancel,0)=0 GROUP BY DateFactor ORDER BY DateFactor DESC; SELECT TOP 5 FactorID, DateFactor, Time FROM dbo.Day_Factor WHERE ISNULL(Cancel,0)=0 ORDER BY FactorID DESC;'
if ($LASTEXITCODE -ne 0) { throw "SQL read-only verification failed: $LASTEXITCODE" }
