$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Exceptions'
$command = $connection.CreateCommand()
$command.CommandTimeout = 15
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT FactorID AS f,DateFactor AS d,Time AS t,Cancel AS c,'archive' AS s FROM dbo.Day_Factor_Log WHERE FactorID IN (19233,23050)
UNION ALL SELECT FactorID,DateFactor,Time,Cancel,'active' FROM dbo.Day_Factor WHERE FactorID IN (19233,23050);
SELECT t.Factor AS f,t.IdAnbar AS w,t.IdKala AS k,t.Ted AS q,t.Bes AS a,k.Name AS n
FROM dbo.Day_TR_Log t LEFT JOIN dbo.TblKala k ON k.IDKala=t.IdKala AND k.IDAnbar=t.IdAnbar
WHERE t.Factor IN (19233,23050) AND t.IdKala>0 AND t.Ted>0 AND t.Bes>0
UNION ALL
SELECT t.Factor,t.IdAnbar,t.IdKala,t.Ted,t.Bes,k.Name FROM dbo.Day_TR t
LEFT JOIN dbo.TblKala k ON k.IDKala=t.IdKala AND k.IDAnbar=t.IdAnbar
WHERE t.Factor IN (19233,23050) AND t.IdKala>0 AND t.Ted>0 AND t.Bes>0;
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
    $json = ConvertTo-Json -InputObject @{machine=$env:COMPUTERNAME;database=$connection.Database;sets=@($sets.ToArray())} -Depth 10 -Compress
    [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
} finally { $connection.Dispose() }
