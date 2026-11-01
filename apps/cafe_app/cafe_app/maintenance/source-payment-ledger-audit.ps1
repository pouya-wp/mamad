$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Audit'
$command = $connection.CreateCommand()
$command.CommandTimeout = 20
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT TABLE_NAME AS t,COLUMN_NAME AS c,DATA_TYPE AS d FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN('Day_TajzieTasvie','TblTypeTasviyeFactor','TblFactorOnvan','TblTTR','TblOnvan','Sodor','Onvan','TblSodor','TblGroupHesab','TblDefultHesab','TblTypeSanadBank') ORDER BY TABLE_NAME,ORDINAL_POSITION;
SELECT * FROM dbo.TblTypeTasviyeFactor ORDER BY Id;
SELECT TOP 40 Id,Sodor,Factor,Ted,CreateTime FROM dbo.Day_TajzieTasvie ORDER BY Id DESC;
SELECT TOP 50 Sodor,Factor,Idkala,Srfsl,Moin,HSB,Type,Tp1,Bed,Bes,Date,Time FROM dbo.TR WHERE ISNULL(Idkala,0)=0 AND Factor>23500 ORDER BY Factor DESC,Sodor DESC;
SELECT t.name AS t,SUM(p.rows) AS n FROM sys.tables t LEFT JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN(0,1) WHERE t.name LIKE '%Sodor%' OR t.name LIKE '%Onvan%' OR t.name LIKE '%Tasvi%' GROUP BY t.name ORDER BY t.name;
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


