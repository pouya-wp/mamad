$ErrorActionPreference = 'Stop'
$connection = New-Object System.Data.SqlClient.SqlConnection 'Data Source=.\SEPANDYAR2014;Initial Catalog=Sepand_One_1405;Integrated Security=True;Connect Timeout=5;Application Name=ONE CAFE ReadOnly Payment Sync'
$command = $connection.CreateCommand()
$command.CommandTimeout = 30
$command.CommandText = @'
SET LOCK_TIMEOUT 3000; SET NOCOUNT ON;
DECLARE @headers TABLE(f int PRIMARY KEY,closed bit,cancelled bit,customer int,active bit,accounting int);
INSERT INTO @headers
SELECT f.FactorID,f.IsTasviye,f.Cancel,f.CustomerId,1,NULL
FROM dbo.Day_Factor f WHERE f.Type=203 AND f.FactorID IN (__FACTOR_IDS__);
INSERT INTO @headers
SELECT f.FactorID,f.IsTasviye,f.Cancel,f.CustomerId,0,NULL
FROM dbo.Day_Factor_Log f WHERE f.Type=203 AND f.FactorID IN (__FACTOR_IDS__)
AND NOT EXISTS(SELECT 1 FROM @headers h WHERE h.f=f.FactorID);
UPDATE h SET accounting=o.ShFactor FROM @headers h
JOIN dbo.TblFactorOnvan o ON o.FactorCust=CONVERT(varchar(20),h.f) AND o.Type=203
WHERE NOT EXISTS(SELECT 1 FROM dbo.TblFactorOnvan other WHERE other.Type=203 AND other.FactorCust=o.FactorCust AND other.ShFactor<>o.ShFactor);
DECLARE @rows TABLE(f int,w int,tp int,method int,debit bigint,credit bigint,k int,q numeric(18,4));
INSERT INTO @rows SELECT h.f,t.IdAnbar,t.Tp1,t.IdAmel,t.Bed,t.Bes,t.IdKala,t.Ted FROM @headers h JOIN dbo.Day_TR t ON t.Factor=h.f WHERE h.active=1;
INSERT INTO @rows SELECT h.f,t.IdAnbr,t.Tp1,t.IdAmel,t.Bed,t.Bes,t.IdKala,t.TED FROM @headers h JOIN dbo.TR t ON t.Factor=h.accounting AND t.Type=203 WHERE h.active=0 AND h.accounting IS NOT NULL;
INSERT INTO @rows SELECT h.f,t.IdAnbar,t.Tp1,t.IdAmel,t.Bed,t.Bes,t.IdKala,t.Ted FROM @headers h JOIN dbo.Day_TR_Log t ON t.Factor=h.f WHERE h.active=0 AND h.accounting IS NULL;
-- Match the native SumMabKol definition. IdAmel=99 posts receivables;
-- unlike the native closed flag, it does not establish a cash receipt.
WITH balance AS (
 SELECT Srfsl,Moin,HSB,SUM(Bed-Bes) AS amount,
 SUM(CASE WHEN Factor=0 AND Bes>0 THEN Bes ELSE 0 END) AS unallocated
 FROM dbo.TR GROUP BY Srfsl,Moin,HSB
), unposted AS (
 SELECT f.CustomerId,SUM(t.Bed-t.Bes) AS amount
 FROM dbo.Day_Factor f JOIN dbo.Day_TR t ON t.Factor=f.FactorID
 WHERE ISNULL(f.Cancel,0)=0 AND f.Type=203 AND t.IdAmel=99 AND ISNULL(t.IdAnbar,0)=0 AND ISNULL(t.Tp1,0)=0
 AND NOT EXISTS(SELECT 1 FROM dbo.TblFactorOnvan o WHERE o.Type=203 AND o.FactorCust=CONVERT(varchar(20),f.FactorID))
 GROUP BY f.CustomerId
)
SELECT h.f,h.closed,h.cancelled,h.customer AS customer_id,
 NULLIF(LTRIM(RTRIM(ISNULL(p.Name,N'')+CASE WHEN LTRIM(RTRIM(ISNULL(p.Name,N'')))=LTRIM(RTRIM(ISNULL(p.Famil,N''))) THEN N'' ELSE N' '+ISNULL(p.Famil,N'') END)),N'') AS customer_name,
 CASE WHEN p.Sh_ozviat IS NOT NULL AND p.Srfsl IS NOT NULL AND p.Moin IS NOT NULL AND p.Hesab IS NOT NULL THEN CONCAT(p.Srfsl,':',p.Moin,':',p.Hesab) END AS account_key,
 ISNULL((SELECT SUM(credit-debit) FROM @rows r WHERE r.f=h.f AND (ISNULL(r.w,0)>0 OR ISNULL(r.tp,0)>0)),0) AS total,
 CAST(CASE WHEN p.Srfsl=110 AND p.Moin>0 AND NOT EXISTS(
 SELECT 1 FROM dbo.TblPerson other WHERE other.Sh_ozviat<>p.Sh_ozviat AND other.Srfsl=p.Srfsl AND other.Moin=p.Moin AND other.Hesab=p.Hesab
 ) AND NOT EXISTS(SELECT 1 FROM dbo.TR t WHERE t.Factor=h.accounting AND t.Type=203 AND t.IdAmel=99 AND (t.Srfsl<>p.Srfsl OR t.Moin<>p.Moin OR t.HSB<>p.Hesab))
 AND (b.amount IS NOT NULL OR u.amount IS NOT NULL) THEN 1 ELSE 0 END AS bit) AS account_verified,
 ISNULL(b.amount,0)+ISNULL(u.amount,0) AS account_balance,
 ISNULL(b.unallocated,0) AS unallocated_receipts
FROM @headers h LEFT JOIN dbo.TblPerson p ON p.Sh_ozviat=h.customer
LEFT JOIN balance b ON b.Srfsl=p.Srfsl AND b.Moin=p.Moin AND b.HSB=p.Hesab
LEFT JOIN unposted u ON u.CustomerId=h.customer ORDER BY h.f;
SELECT f,ISNULL(method,0) AS method,SUM(debit-credit) AS amount FROM @rows
WHERE ISNULL(w,0)=0 AND ISNULL(tp,0)=0 GROUP BY f,method ORDER BY f,method;
SELECT a.Id AS id,a.Name AS name,CASE WHEN account.n=1 THEN account.name END AS account_name
FROM dbo.TblFactorAvamelNasiyeForush a OUTER APPLY (
 SELECT COUNT(*) AS n,MAX(NULLIF(LTRIM(RTRIM(ISNULL(p.Name,N'')+N' '+ISNULL(p.Famil,N''))),N'')) AS name
 FROM dbo.TblPerson p WHERE p.Srfsl=a.Sarfasl AND p.Moin=a.Moin AND p.Hesab=a.Hesab
) account ORDER BY a.Id;
SELECT r.f,r.w,r.k,k.Name AS name,SUM(r.q) AS qty,SUM(r.credit-r.debit) AS amount
FROM @rows r LEFT JOIN dbo.TblKala k ON k.IDAnbar=r.w AND k.IDKala=r.k
WHERE r.w>0 AND r.k>0 AND r.q>0 AND r.credit>0
GROUP BY r.f,r.w,r.k,k.Name ORDER BY r.f,r.w,r.k;
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
    $json = ConvertTo-Json -InputObject @{version=3;machine=$env:COMPUTERNAME;database=$connection.Database;sets=@($sets.ToArray())} -Depth 12 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    $memory = New-Object System.IO.MemoryStream
    $gzip = [System.IO.Compression.GZipStream]::new($memory,[System.IO.Compression.CompressionLevel]::Optimal,$true)
    $gzip.Write($bytes,0,$bytes.Length); $gzip.Dispose()
    $encoded = [Convert]::ToBase64String($memory.ToArray()); $memory.Dispose()
    if ($encoded.Length -gt 55000) { throw 'Payment sync exceeds safe output size' }
    'GZIP:' + $encoded
} finally { $connection.Dispose() }
