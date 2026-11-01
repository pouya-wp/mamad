$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Audit'
$command = $connection.CreateCommand()
$command.CommandTimeout = 20
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
SELECT SCHEMA_NAME(schema_id) AS s,name,OBJECT_DEFINITION(object_id) AS definition FROM sys.objects WHERE name LIKE 'Func_digimall_SumMab%';
SELECT TOP 15 o.FactorCust,v.invoice_id,v.payable_amount,v.payment_amount,v.payment_state FROM digimall.vmInvoice v JOIN dbo.TblFactorOnvan o ON o.ShFactor=v.invoice_id WHERE o.FactorCust IN('23206','23204','23190','23161','23089','23085','23031','23024','22992','22858','22814');
SELECT TOP 30 Factor,Sodor,Type,IdAmel,Bed,Bes,Srfsl,Moin,HSB,NumberFactor,TypeFactor FROM dbo.TR WHERE Srfsl=110 AND Moin=1 AND HSB IN(86,93,98,101,107,108) AND Bes>0 ORDER BY Sodor DESC;
SELECT TOP 12 f.FactorID,SUM(CASE WHEN t.IdKala>0 THEN t.Bes ELSE 0 END) AS total,SUM(CASE WHEN ISNULL(t.IdKala,0)=0 THEN t.Bed-t.Bes ELSE 0 END) AS allocations,SUM(CASE WHEN ISNULL(t.IdKala,0)=0 AND t.IdAmel=99 THEN t.Bed-t.Bes ELSE 0 END) AS credit FROM dbo.Day_Factor f JOIN dbo.Day_TR t ON t.Factor=f.FactorID WHERE ISNULL(f.Cancel,0)=0 GROUP BY f.FactorID ORDER BY f.FactorID DESC;
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
