param(
  [string]$EnvFile = ".env",
  [int]$KeepLast = 14
)

$ErrorActionPreference = "Stop"

function Read-EnvFile([string]$Path) {
  $values = @{}
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Environment file not found: $Path"
  }
  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $idx = $line.IndexOf("=")
    $key = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim().Trim('"')
    $values[$key] = $value
  }
  return $values
}

$envs = Read-EnvFile $EnvFile
$nasHost = $envs["NAS_HOST"]
$nasUser = $envs["NAS_USER"]
$nasBackupDir = $envs["NAS_DB_BACKUP_DIR"]
$postgresUser = $envs["POSTGRES_USER"]
$postgresDb = $envs["POSTGRES_DB"]

if (-not $nasHost -or -not $nasUser -or -not $nasBackupDir) {
  throw "NAS_HOST, NAS_USER, NAS_DB_BACKUP_DIR must be set in .env"
}
if (-not $postgresUser -or -not $postgresDb) {
  throw "POSTGRES_USER and POSTGRES_DB must be set in .env"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$localDir = Join-Path $PWD "storage\db-backups-tmp"
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
$dumpPath = Join-Path $localDir "lawcompass_$timestamp.dump"

docker compose exec -T postgres pg_dump -U $postgresUser -d $postgresDb -Fc > $dumpPath

$batchPath = Join-Path $localDir "sftp_backup_$timestamp.txt"
@"
cd $nasBackupDir
put $dumpPath
ls
bye
"@ | Set-Content -LiteralPath $batchPath -Encoding UTF8

try {
  sftp -b $batchPath "$nasUser@$nasHost"
} finally {
  Remove-Item -LiteralPath $batchPath -Force -ErrorAction SilentlyContinue
}

Get-ChildItem -LiteralPath $localDir -Filter "lawcompass_*.dump" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip $KeepLast |
  Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "PostgreSQL backup uploaded to NAS backup directory. Secrets and NAS absolute paths were not printed."

