param(
    [string]$EnvPath = ".env"
)

# Load .env file if it exists
if (Test-Path $EnvPath) {
    Write-Host "Loading environment from $EnvPath..."
    Get-Content $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $key, $value = $line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
        }
    }
}

$RootToken = $env:VAULT_ROOT_TOKEN
$BackupPath = $env:BACKUP_PATH
$KubeConfig = $env:KUBECONFIG_PATH

if (-not $RootToken) {
    Write-Error "VAULT_ROOT_TOKEN not found in environment or .env file"
    exit 1
}

if (-not (Test-Path $BackupPath)) {
    Write-Error "Backup file not found at $BackupPath"
    exit 1
}

$Backup = Get-Content $BackupPath | ConvertFrom-Json
$Secrets = $Backup.data

Write-Host "Starting Vault Sync to VPS..."

# Function to write to Vault
function Write-VaultData {
    param($Path, $Data)
    $Command = "VAULT_TOKEN=$RootToken vault kv put $Path"
    foreach ($Prop in $Data.PSObject.Properties) {
        $Key = $Prop.Name
        $Val = $Prop.Value
        if ($null -ne $Val) {
            # Escape single quotes for shell
            $ValStr = $Val.ToString().Replace("'", "''")
            $Command += " $Key='$ValStr'"
        }
    }
    
    Write-Host "Writing to $Path..."
    kubectl --kubeconfig $KubeConfig exec vault-0 -n vault -- /bin/sh -c "$Command"
}

# 1. Sync Infra Secrets
Write-Host "Syncing Infra Secrets..."
$InfraPaths = @(
    "apps/preprod/infra/mongodb",
    "apps/preprod/infra/kafka",
    "apps/preprod/infra/postgres",
    "apps/preprod/infra/redis"
)

foreach ($Path in $InfraPaths) {
    if ($Secrets.$Path) {
        Write-VaultData $Path $Secrets.$Path
        # Also mirror to 'secret/' path
        $SecretPath = $Path -replace "apps/", "secret/"
        Write-VaultData $SecretPath $Secrets.$Path
    }
}

# 2. Sync App Secrets
Write-Host "Syncing App Specific Secrets..."

# Cloudinary
if ($env:CLOUDINARY_CLOUD_NAME) {
    $CloudinaryData = [PSCustomObject]@{
        CLOUDINARY_CLOUD_NAME = $env:CLOUDINARY_CLOUD_NAME
        CLOUDINARY_API_KEY = $env:CLOUDINARY_API_KEY
        CLOUDINARY_API_SECRET = $env:CLOUDINARY_API_SECRET
    }
    Write-VaultData "secret/preprod/apps/docs/cloudinary" $CloudinaryData
    Write-VaultData "apps/preprod/services/am-cloudinary-manager" $CloudinaryData
    Write-VaultData "apps/prod/services/am-cloudinary-manager" $CloudinaryData
}



Write-Host "Vault Sync Complete!"
