$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Categories'
$command = $connection.CreateCommand()
$command.CommandTimeout = 15
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT IDAnbar AS w,IDKala AS id,Name AS n,GroupCode AS g,KalaGroups AS gs,KalaType AS kt,KalaClass AS kc FROM dbo.TblKala WHERE IDAnbar=3 ORDER BY IDKala;
SELECT * FROM dbo.TblGroupKala;
SELECT TABLE_NAME AS t,COLUMN_NAME AS c,DATA_TYPE AS d FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME LIKE '%MenuTouch%' OR TABLE_NAME='TblGroupKala' ORDER BY TABLE_NAME,ORDINAL_POSITION;
SELECT TOP 100 * FROM dbo.TblGroupMenuTouchFactor;
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
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    if ($encoded.Length -gt 55000) { throw 'Category export exceeds output limit' }
    $encoded
} finally { $connection.Dispose() }
