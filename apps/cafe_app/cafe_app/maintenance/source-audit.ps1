$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Audit'
$command = $connection.CreateCommand()
$command.CommandTimeout = 15
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT name, state_desc FROM sys.databases WHERE database_id > 4 ORDER BY name;
SELECT s.name AS schemaName, t.name AS tableName, SUM(p.rows) AS [rows]
FROM sys.tables t INNER JOIN sys.schemas s ON s.schema_id=t.schema_id
LEFT JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1)
WHERE t.name LIKE '%Factor%' OR t.name LIKE '%Kala%' OR t.name IN ('TR','TRDetail')
GROUP BY s.name,t.name ORDER BY t.name;
SELECT TABLE_NAME AS tableName,COLUMN_NAME AS columnName,DATA_TYPE AS dataType
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME IN ('TblKala','TblFactor','TR','Day_Factor','Day_TR')
ORDER BY TABLE_NAME,ORDINAL_POSITION;
SELECT IDAnbar AS warehouseId,COUNT_BIG(*) AS [rows],COUNT(DISTINCT IDKala) AS ids
FROM dbo.TblKala GROUP BY IDAnbar ORDER BY IDAnbar;
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
    [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
} finally { $connection.Dispose() }
