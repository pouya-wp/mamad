$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Sync'
$command = $connection.CreateCommand()
$command.CommandTimeout = 30
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT p.Sh_ozviat,p.Name,p.Famil,p.Srfsl,p.Moin,p.Hesab,
 (SELECT COUNT(*) FROM dbo.TblPerson o WHERE o.Srfsl=p.Srfsl AND o.Moin=p.Moin AND o.Hesab=p.Hesab AND o.Sh_ozviat<>p.Sh_ozviat) AS shared_accounts,
 (SELECT COUNT(*) FROM dbo.TR t WHERE t.Srfsl=p.Srfsl AND t.Moin=p.Moin AND t.HSB=p.Hesab) AS ledger_rows,
 (SELECT SUM(t.Bed-t.Bes) FROM dbo.TR t WHERE t.Srfsl=p.Srfsl AND t.Moin=p.Moin AND t.HSB=p.Hesab) AS balance
 FROM dbo.TblPerson p WHERE p.Sh_ozviat IN (10,192);
SELECT f.FactorID,f.CustomerId,o.ShFactor,t.Srfsl,t.Moin,t.HSB,t.Bed,t.Bes FROM dbo.Day_Factor f LEFT JOIN dbo.TblFactorOnvan o ON o.Type=203 AND o.FactorCust=CONVERT(varchar(20),f.FactorID) LEFT JOIN dbo.TR t ON t.Factor=o.ShFactor AND t.Type=203 AND t.IdAmel=99 WHERE f.CustomerId IN (10,192) AND f.Type=203 AND EXISTS(SELECT 1 FROM dbo.Day_TR d WHERE d.Factor=f.FactorID AND d.IdAmel=99);
'@
try {
    $connection.Open()
    $reader = $command.ExecuteReader()
    $sets = New-Object System.Collections.Generic.List[object]
    do {
        $rows = New-Object System.Collections.Generic.List[object]
        while ($reader.Read()) {
            $row = [ordered]@{}
            for ($column = 0; $column -lt $reader.FieldCount; $column++) {
                $value = $reader.GetValue($column)
                $row[$reader.GetName($column)] = $(if ($value -is [DBNull]) { $null } else { $value })
            }
            $rows.Add($row)
        }
        $sets.Add(@($rows.ToArray()))
    } while ($reader.NextResult())
    $reader.Close()
    $json = ConvertTo-Json -InputObject @{version=2;machine=$env:COMPUTERNAME;database=$connection.Database;sets=@($sets.ToArray())} -Depth 12 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    $memory = New-Object System.IO.MemoryStream
    $gzip = [System.IO.Compression.GZipStream]::new($memory,[System.IO.Compression.CompressionLevel]::Optimal,$true)
    $gzip.Write($bytes,0,$bytes.Length); $gzip.Dispose()
    $encoded = [Convert]::ToBase64String($memory.ToArray()); $memory.Dispose()
    if ($encoded.Length -gt 55000) { throw 'Payment sync exceeds safe output size' }
    'GZIP:' + $encoded
} finally { $connection.Dispose() }
