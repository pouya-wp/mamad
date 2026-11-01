$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Catalog'
$command = $connection.CreateCommand()
$command.CommandTimeout = 15
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT IDAnbar AS w, IDKala AS id, Name AS n
FROM dbo.TblKala WHERE IDKala > 0 ORDER BY IDAnbar,IDKala;
SELECT TABLE_NAME AS t,COLUMN_NAME AS c,DATA_TYPE AS d
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME IN ('Day_Factor_Log','Day_TR_Log','TblFactorOnvan','TblLastMabFactor','TblAnbar')
ORDER BY TABLE_NAME,ORDINAL_POSITION;
SELECT TOP 12 DateFactor AS d,COUNT_BIG(*) AS n,MAX(FactorID) AS lastId
FROM dbo.Day_Factor_Log GROUP BY DateFactor ORDER BY DateFactor DESC;
SELECT IdAnbar AS w,COUNT_BIG(*) AS n FROM dbo.Day_TR
WHERE IdKala > 0 AND Bes > 0 GROUP BY IdAnbar ORDER BY IdAnbar;
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
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    if ($encoded.Length -gt 55000) { throw 'Export exceeds safe job output size; use pagination' }
    $encoded
} finally { $connection.Dispose() }
