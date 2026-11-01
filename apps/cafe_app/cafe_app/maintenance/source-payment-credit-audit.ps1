$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Audit'
$command = $connection.CreateCommand()
$command.CommandTimeout = 20
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT IdAmel,COUNT_BIG(*) AS n,SUM(Bed-Bes) AS amount FROM dbo.Day_TR WHERE ISNULL(IdKala,0)=0 GROUP BY IdAmel;
SELECT TOP 15 f.FactorID,f.CustomerId,f.IsTasviye,f.DateFactor,t.IdAmel,t.Bed,t.Bes,t.Description FROM dbo.Day_Factor f JOIN dbo.Day_TR t ON f.FactorID=t.Factor WHERE t.IdAmel=99 AND ISNULL(t.IdKala,0)=0 ORDER BY f.FactorID DESC;
SELECT TOP 15 f.FactorID,f.CustomerId,f.IsTasviye,f.DateFactor,o.ShFactor,o.TypeTasviye,o.TypePardakht,t.IdAmel,t.Bed,t.Bes,t.Srfsl,t.Moin,t.HSB FROM dbo.Day_Factor_Log f JOIN dbo.Day_TR_Log d ON d.Factor=f.FactorID AND d.IdAmel=99 AND ISNULL(d.IdKala,0)=0 LEFT JOIN dbo.TblFactorOnvan o ON o.FactorCust=CONVERT(varchar(20),f.FactorID) AND o.Type=203 LEFT JOIN dbo.TR t ON t.Factor=o.ShFactor AND ISNULL(t.IdKala,0)=0 ORDER BY f.FactorID DESC;
SELECT TABLE_NAME AS t,COLUMN_NAME AS c,DATA_TYPE AS d FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN('TRDetail','TblTypePardakht','TblParam') ORDER BY TABLE_NAME,ORDINAL_POSITION;
SELECT TOP 8 t.* FROM dbo.TRDetail t WHERE t.Sodor IN(SELECT TOP 8 Sodor FROM dbo.TR WHERE IdAmel=99 ORDER BY Factor DESC);
SELECT name,type_desc,OBJECT_DEFINITION(object_id) AS definition FROM sys.objects WHERE name IN('vmInvoice','vwInvoiceDetails');
SELECT TABLE_SCHEMA AS s,TABLE_NAME AS t FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN('vmInvoice','vwInvoiceDetails');
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
    $json = ConvertTo-Json -InputObject @{machine=$env:COMPUTERNAME;database=$connection.Database;sets=@($sets.ToArray())} -Depth 12 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    $memory = New-Object System.IO.MemoryStream
    $gzip = [System.IO.Compression.GZipStream]::new($memory,[System.IO.Compression.CompressionLevel]::Optimal,$true)
    $gzip.Write($bytes,0,$bytes.Length); $gzip.Dispose()
    $encoded = [Convert]::ToBase64String($memory.ToArray()); $memory.Dispose()
    if ($encoded.Length -gt 55000) { throw 'Payment audit exceeds safe output size' }
    'GZIP:' + $encoded
} finally { $connection.Dispose() }
