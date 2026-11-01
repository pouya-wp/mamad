$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Audit'
$command = $connection.CreateCommand()
$command.CommandTimeout = 20
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT COLUMN_NAME AS c,DATA_TYPE AS d FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='TblPerson' ORDER BY ORDINAL_POSITION;
SELECT Srfsl,Moin,HSB,SUM(Bed-Bes) AS balance,SUM(CASE WHEN Bes>0 THEN Bes ELSE 0 END) AS credits,MAX(Time) AS changed FROM dbo.TR WHERE Srfsl=110 AND Moin=1 GROUP BY Srfsl,Moin,HSB;
SELECT TOP 15 t.Sodor,t.Factor,t.Bed,t.Bes,t.Srfsl,t.Moin,t.HSB,t.Type,t.TRDureTasviye,d.Tag1,d.Tag2,d.RowFactor,d.RowFactor_Id,d.Id1,d.Id2,d.Id3,d.Id4 FROM dbo.TR t LEFT JOIN dbo.TRDetail d ON d.Sodor=t.Sodor WHERE t.Srfsl=110 AND t.Bes>0 ORDER BY t.Sodor DESC;
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
