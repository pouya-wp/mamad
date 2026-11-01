# ONE CAFE read-only workstation and SepandYar connectivity check.
# This script only reads status and SQL metadata. It never writes to SepandYar.
$ErrorActionPreference = 'Stop'
Write-Output ("Computer: " + $env:COMPUTERNAME)
Write-Output ("Windows user: " + [Security.Principal.WindowsIdentity]::GetCurrent().Name)
Write-Output ("Time: " + (Get-Date).ToString('o'))
$sqlcmd = Get-Command sqlcmd.exe -ErrorAction Stop
Write-Output ("sqlcmd: " + $sqlcmd.Source)
$query = @'
SET NOCOUNT ON;
SELECT DB_NAME() AS DatabaseName,
       (SELECT COUNT(*) FROM dbo.TblKala) AS ProductRows,
       (SELECT COUNT(*) FROM dbo.Day_Factor) AS FactorRows,
       (SELECT MAX(FactorID) FROM dbo.Day_Factor) AS LastFactorID,
       (SELECT COUNT(*) FROM dbo.Day_TR WHERE IdKala > 0) AS SaleLineRows;
'@
& $sqlcmd.Source -S '.\SEPANDYAR2014' -E -d 'Sepand_One_1405' -b -W -s '|' -f 65001 -Q $query
if ($LASTEXITCODE -ne 0) { throw "sqlcmd failed with exit code $LASTEXITCODE" }
