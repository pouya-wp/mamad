param(
    [string]$Server = '.\SEPANDYAR2014',
    [string]$Database = 'Sepand_One_1405',
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
if (-not $OutputPath) {
    $filename = 'one-cafe-products-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'
    $OutputPath = Join-Path ([Environment]::GetFolderPath('Desktop')) $filename
}

Add-Type -AssemblyName System.Data
$builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
$builder['Data Source'] = $Server
$builder['Initial Catalog'] = $Database
$builder['Integrated Security'] = $true
$builder['Connect Timeout'] = 15
$builder['Application Name'] = 'ONE CAFE read-only product export'

$connection = New-Object System.Data.SqlClient.SqlConnection($builder.ConnectionString)
$items = New-Object 'System.Collections.Generic.List[object]'
try {
    $connection.Open()
    $command = $connection.CreateCommand()
    $command.CommandTimeout = 60
    $command.CommandText = @'
SELECT IDKala, CAST(MAX(Name) AS nvarchar(4000)) AS ProductName
FROM dbo.TblKala
WHERE IDKala > 0 AND NULLIF(LTRIM(RTRIM(Name)), '') IS NOT NULL
GROUP BY IDKala
ORDER BY IDKala;
'@
    $reader = $command.ExecuteReader()
    try {
        while ($reader.Read()) {
            $name = $reader.GetString(1).Trim()
            if ($name) {
                $items.Add([pscustomobject]@{
                    sourceItemId = [int]$reader.GetValue(0)
                    name = $name
                })
            }
        }
    } finally {
        $reader.Close()
        $command.Dispose()
    }
} finally {
    $connection.Close()
    $connection.Dispose()
}

$json = ConvertTo-Json -InputObject $items.ToArray() -Depth 3
[System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.UTF8Encoding]::new($false))
$persianCount = @($items | Where-Object { $_.name -match '[\u0600-\u06FF]' }).Count
$questionCount = @($items | Where-Object { $_.name.Contains('?') }).Count
Write-Host ('Saved: ' + $OutputPath)
Write-Host ('Products: ' + $items.Count)
Write-Host ('Names with Persian letters: ' + $persianCount)
Write-Host ('Names with question marks: ' + $questionCount)
if ($persianCount -eq 0) {
    Write-Warning 'No Persian names were found in this table. Keep the JSON for diagnosis; no source data was changed.'
}
