$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Audit'
$command = $connection.CreateCommand()
$command.CommandTimeout = 20
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT t.name AS t,SUM(p.rows) AS n FROM sys.tables t LEFT JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN(0,1) GROUP BY t.name HAVING SUM(p.rows)>0 ORDER BY t.name;
SELECT TABLE_NAME AS t,COLUMN_NAME AS c,DATA_TYPE AS d FROM INFORMATION_SCHEMA.COLUMNS WHERE COLUMN_NAME LIKE '%Tasv%' OR COLUMN_NAME LIKE '%Pay%' OR COLUMN_NAME LIKE '%Pard%' OR TABLE_NAME IN('Day_PrintFactor','Day_TR','TblFactorAvamelNasiyeForush','TblFactorAvamelNasiye_User') ORDER BY TABLE_NAME,ORDINAL_POSITION;
SELECT TOP 30 Factor,IdAmel,Sharh,Serial,Bed,Bes,Tp1,Deposit,Srfsl,Moin,HSB,ShiftId FROM dbo.Day_TR WHERE ISNULL(IdKala,0)=0 ORDER BY Factor DESC;
SELECT TOP 10 * FROM dbo.TblDefultHesab ORDER BY id;
SELECT TOP 5 ShFactor,FactorCust,TypeTasviye,TypePardakht,RefId,Id1,Id2,Id3,TasviyeSharh,Description FROM dbo.TblFactorOnvan ORDER BY ShFactor DESC;
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
