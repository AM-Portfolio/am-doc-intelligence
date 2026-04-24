param(
    [string]$RootToken = $env:VAULT_TOKEN,
    [string]$BackupPath = "f:\am-repos\am-repos\am-auth\vault\backups\vps_vault_full_backup_20260422_000034.json",
    [string]$KubeConfig = "f:\am-repos\am-repos\am-auth\kubeconfig.vps"
)

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
$CloudinaryData = [PSCustomObject]@{
    CLOUDINARY_CLOUD_NAME = "dr6crhham"
    CLOUDINARY_API_KEY = "712557573888213"
    CLOUDINARY_API_SECRET = "eKoN0tAMCCNMnXtxiFdOsHDP69Y"
}
Write-VaultData "secret/preprod/apps/docs/cloudinary" $CloudinaryData

# Google
$GoogleData = [PSCustomObject]@{
    GOOGLE_CLIENT_ID = "placeholder"
    GOOGLE_CLIENT_SECRET = "placeholder"
}
Write-VaultData "secret/preprod/apps/docs/google" $GoogleData

# JWT
if ($Secrets."secret/preprod/apps/auth/jwt") {
    $JwtData = $Secrets."secret/preprod/apps/auth/jwt"
    # Ensure key matches what app expects (JWT_SECRET)
    $NewJwtData = [PSCustomObject]@{
        JWT_SECRET = $JwtData.secret
    }
    Write-VaultData "secret/preprod/apps/auth/jwt" $NewJwtData
}

Write-Host "Vault Sync Complete!"
