$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Audit'
$command = $connection.CreateCommand()
$command.CommandTimeout = 20
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT t.name AS t,SUM(p.rows) AS n FROM sys.tables t LEFT JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN(0,1)
WHERE t.name LIKE '%Tasv%' OR t.name LIKE '%Pay%' OR t.name LIKE '%Daryaft%' OR t.name LIKE '%Hesab%' OR t.name LIKE '%Moin%' OR t.name LIKE '%Srfsl%' OR t.name LIKE '%Sarf%' OR t.name LIKE '%Bank%' OR t.name LIKE '%FactorState%' OR t.name LIKE '%FactorStatus%' OR t.name LIKE '%FactorType%'
GROUP BY t.name ORDER BY t.name;
SELECT TABLE_NAME AS t,COLUMN_NAME AS c,DATA_TYPE AS d FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME LIKE '%Tasv%' OR TABLE_NAME LIKE '%Pay%' OR TABLE_NAME IN('TblHesab','TblMoin','TblSrfsl','TblBank','TblSarfasl') ORDER BY TABLE_NAME,ORDINAL_POSITION;
SELECT Type AS tp,IsTasviye AS settled,FactorStatus AS status,FactorState AS state,COUNT_BIG(*) AS n,MAX(FactorID) AS lastId FROM dbo.Day_Factor WHERE ISNULL(Cancel,0)=0 GROUP BY Type,IsTasviye,FactorStatus,FactorState;
SELECT TOP 100 Srfsl AS a,Moin AS m,Tp1 AS tp,[Index] AS i,COUNT_BIG(*) AS n,SUM(Bed) AS debit,SUM(Bes) AS credit,MAX(Factor) AS lastId FROM dbo.Day_TR WHERE ISNULL(IdKala,0)=0 GROUP BY Srfsl,Moin,Tp1,[Index] ORDER BY n DESC;
SELECT TOP 50 f.FactorID AS f,f.DateFactor AS d,f.Type AS tp,f.IsTasviye AS settled,f.FactorStatus AS status,f.FactorState AS state,t.Srfsl AS a,t.Moin AS m,t.HSB AS h,t.Bed AS debit,t.Bes AS credit,t.Tp1 AS tp1,t.[Index] AS i,t.Deposit AS deposit
FROM dbo.Day_Factor f LEFT JOIN dbo.Day_TR t ON t.Factor=f.FactorID AND ISNULL(t.IdKala,0)=0 WHERE ISNULL(f.Cancel,0)=0 ORDER BY f.FactorID DESC;
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
