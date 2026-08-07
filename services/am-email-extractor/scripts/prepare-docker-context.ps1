$ErrorActionPreference = "Stop"

$serviceRoot = Split-Path -Parent $PSScriptRoot
$platformSecurity = Join-Path $serviceRoot "../../../am-platform/libraries/am-platform-security"
$target = Join-Path $serviceRoot "third_party/am-platform-security"

if (-not (Test-Path $platformSecurity)) {
    throw "am-platform-security not found at $platformSecurity"
}

New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
if (Test-Path $target) {
    Remove-Item -Recurse -Force $target
}
Copy-Item -Recurse -Force $platformSecurity $target
Write-Host "Staged am-platform-security at $target"
