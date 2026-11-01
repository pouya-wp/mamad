$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Week Export'
$command = $connection.CreateCommand()
$command.CommandTimeout = 20
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT f.FactorID AS f,f.DateFactor AS d,f.Time AS t,'archive' AS s
FROM dbo.Day_Factor_Log f
WHERE ISNULL(f.Cancel,0)=0 AND f.DateFactor >= '1405/06/28' AND f.DateFactor < '1405/07/06'
UNION ALL
SELECT f.FactorID,f.DateFactor,f.Time,'active'
FROM dbo.Day_Factor f
WHERE ISNULL(f.Cancel,0)=0 AND f.DateFactor >= '1405/06/28' AND f.DateFactor < '1405/07/06'
ORDER BY f;
SELECT f.FactorID AS f,'archive' AS s,t.IdAnbar AS w,t.IdKala AS k,t.Ted AS q,t.Bes AS a,t.Takh AS discount,k.Name AS n
FROM dbo.Day_Factor_Log f
INNER JOIN dbo.Day_TR_Log t ON t.Factor=f.FactorID AND t.IdKala>0 AND t.Ted>0 AND t.Bes>0
LEFT JOIN dbo.TblKala k ON k.IDKala=t.IdKala AND k.IDAnbar=t.IdAnbar
WHERE ISNULL(f.Cancel,0)=0 AND f.DateFactor >= '1405/06/28' AND f.DateFactor < '1405/07/06'
UNION ALL
SELECT f.FactorID,'active',t.IdAnbar,t.IdKala,t.Ted,t.Bes,t.Takh,k.Name
FROM dbo.Day_Factor f
INNER JOIN dbo.Day_TR t ON t.Factor=f.FactorID AND t.IdKala>0 AND t.Ted>0 AND t.Bes>0
LEFT JOIN dbo.TblKala k ON k.IDKala=t.IdKala AND k.IDAnbar=t.IdAnbar
WHERE ISNULL(f.Cancel,0)=0 AND f.DateFactor >= '1405/06/28' AND f.DateFactor < '1405/07/06'
ORDER BY f,s,w,k;
SELECT 'archive' AS s,f.FactorID AS f,
SUM(CASE WHEN t.IdKala>0 AND t.Ted>0 AND t.Bes>0 THEN t.Bes ELSE 0 END) AS products,
SUM(ISNULL(t.Bed,0)) AS debit,SUM(ISNULL(t.Bes,0)) AS credit,
SUM(CASE WHEN t.IdKala=0 THEN ISNULL(t.Bed,0) ELSE 0 END) AS nonItemDebit,
SUM(CASE WHEN t.IdKala=0 THEN ISNULL(t.Bes,0) ELSE 0 END) AS nonItemCredit
FROM dbo.Day_Factor_Log f LEFT JOIN dbo.Day_TR_Log t ON t.Factor=f.FactorID
WHERE ISNULL(f.Cancel,0)=0 AND f.DateFactor >= '1405/06/28' AND f.DateFactor < '1405/07/06'
GROUP BY f.FactorID
UNION ALL
SELECT 'active',f.FactorID,
SUM(CASE WHEN t.IdKala>0 AND t.Ted>0 AND t.Bes>0 THEN t.Bes ELSE 0 END),
SUM(ISNULL(t.Bed,0)),SUM(ISNULL(t.Bes,0)),
SUM(CASE WHEN t.IdKala=0 THEN ISNULL(t.Bed,0) ELSE 0 END),
SUM(CASE WHEN t.IdKala=0 THEN ISNULL(t.Bes,0) ELSE 0 END)
FROM dbo.Day_Factor f LEFT JOIN dbo.Day_TR t ON t.Factor=f.FactorID
WHERE ISNULL(f.Cancel,0)=0 AND f.DateFactor >= '1405/06/28' AND f.DateFactor < '1405/07/06'
GROUP BY f.FactorID;
SELECT IDAnbar AS w,IDKala AS k,Type AS p,Fi AS price FROM dbo.TblLastMabFactor ORDER BY IDAnbar,IDKala,Type;
SELECT ID AS w,Name AS n FROM dbo.TblAnbar ORDER BY ID;
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
    $json = ConvertTo-Json -InputObject @{machine=$env:COMPUTERNAME;database=$connection.Database;from='1405/06/28';toExclusive='1405/07/06';sets=@($sets.ToArray())} -Depth 12 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    $memory = New-Object System.IO.MemoryStream
    $gzip = [System.IO.Compression.GZipStream]::new($memory,[System.IO.Compression.CompressionLevel]::Optimal,$true)
    $gzip.Write($bytes,0,$bytes.Length)
    $gzip.Dispose()
    $encoded = [Convert]::ToBase64String($memory.ToArray())
    $memory.Dispose()
    if ($encoded.Length -gt 55000) { throw 'Compressed export exceeds safe output size; use smaller date batches' }
    'GZIP:' + $encoded
} finally { $connection.Dispose() }
