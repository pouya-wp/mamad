$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Audit'
$command = $connection.CreateCommand()
$command.CommandTimeout = 20
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT * FROM dbo.TblFactorAvamelNasiyeForush ORDER BY Id;
SELECT TABLE_NAME AS t,COLUMN_NAME AS c,DATA_TYPE AS d FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN('vmInvoice','PosTransaction','Master','TRDetail','TblTypePardakht') ORDER BY TABLE_NAME,ORDINAL_POSITION;
SELECT OBJECT_NAME(object_id) AS n,definition AS sql FROM sys.sql_modules WHERE object_id=OBJECT_ID('dbo.vmInvoice');
SELECT TOP 15 Factor,IdAmel,Bed,Bes,Description,Sharh FROM dbo.Day_TR WHERE ISNULL(IdKala,0)=0 AND IdAmel<>1 ORDER BY Factor DESC;
SELECT TOP 15 Factor,IdAmel,Bed,Bes,Description,Sharh,Srfsl,Moin,HSB FROM dbo.TR WHERE Factor BETWEEN 22750 AND 22815 AND ISNULL(IdKala,0)=0 ORDER BY Factor DESC;
SELECT TOP 10 o.ShFactor,o.FactorCust,f.FactorID,o.TypeTasviye,f.IsTasviye FROM dbo.TblFactorOnvan o LEFT JOIN dbo.Day_Factor_Log f ON o.FactorCust=CONVERT(varchar(20),f.FactorID) WHERE o.ShFactor>22700 ORDER BY o.ShFactor DESC;
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
