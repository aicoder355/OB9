param(
    [string]$VenvPath = '.\.venv',
    [switch]$Clean
)

function Write-Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Err($m) { Write-Host "[ERROR] $m" -ForegroundColor Red }

Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition | Split-Path -Parent
Set-Location $root

$venvPython = Join-Path $root $VenvPath
if (-not (Test-Path $venvPython)) {
    Write-Err "Virtualenv not found at $VenvPath. Activate your venv or create one before running this script."
    exit 2
}

$pythonExe = Join-Path $venvPython 'Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
    Write-Err "python.exe not found in $pythonExe"
    exit 3
}

Write-Info "Installing PyInstaller into venv..."
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install pyinstaller > .\pyinstaller_install.log 2>&1
Write-Info "PyInstaller install log: .\pyinstaller_install.log"

if ($Clean) {
    Write-Info "Cleaning previous builds..."
    Remove-Item -Recurse -Force .\build,.\dist -ErrorAction SilentlyContinue
}

# Build server exe
$serverEntry = Join-Path $root 'scripts\pyinstaller\server_run.py'
Write-Info "Building server executable..."
& $pythonExe -m PyInstaller --noconfirm --onefile --name water_delivery_server `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --add-data ".env;." `
    --add-data "media;media" `
    $serverEntry 2>&1 | Tee-Object -FilePath .\pyinstaller_server.log

Write-Info "Server build log: .\pyinstaller_server.log"

# Build bot exe
$botEntry = Join-Path $root 'scripts\pyinstaller\bot_run.py'
Write-Info "Building bot executable..."
& $pythonExe -m PyInstaller --noconfirm --onefile --name water_delivery_bot `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --add-data ".env;." `
    --add-data "media;media" `
    $botEntry 2>&1 | Tee-Object -FilePath .\pyinstaller_bot.log

Write-Info "Bot build log: .\pyinstaller_bot.log"

Write-Info "Move built exes to installers\dist"
$outDir = Join-Path $root 'installers\dist'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
if (Test-Path .\dist\water_delivery_server.exe) { Move-Item .\dist\water_delivery_server.exe $outDir -Force }
if (Test-Path .\dist\water_delivery_bot.exe) { Move-Item .\dist\water_delivery_bot.exe $outDir -Force }

Write-Info "Executables available in installers\dist"
exit 0
