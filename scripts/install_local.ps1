<#
PowerShell installer for local Windows deployment.

What this script does:
- Creates a virtual environment `.venv` in the project root
- Activates it and installs `requirements.txt`
- Copies `.env.example` -> `.env` if `.env` missing
- Creates `run_server.bat` and `run_bot.bat` launcher files
- Optionally creates Start Menu shortcuts (requires admin depending on target)

Usage (run as a regular user):
  powershell -ExecutionPolicy Bypass -File .\scripts\install_local.ps1

Note: Requires Python 3.10+ already installed and on PATH.
#>
Set-StrictMode -Version Latest

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $projectRoot

Write-Info "Project root: $projectRoot"

# Detect Python interpreter: prefer bundled portable Python in 'embedded_python' if present,
# otherwise use system 'python' from PATH.
$bundledPython = Join-Path $projectRoot 'embedded_python\python.exe'
if (Test-Path $bundledPython) {
    Write-Info "Bundled Python detected at $bundledPython. Will use bundled Python to create venv."
    $pythonCmd = $bundledPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Info "System Python found in PATH. Will use system Python."
    $pythonCmd = 'python'
} else {
    Write-Err "Python not found in PATH and no bundled Python in 'embedded_python'. Please install Python 3.10+ or include a portable Python in 'embedded_python'. Aborting."
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Info "Creating virtual environment .venv using $pythonCmd ..."
    & $pythonCmd -m venv .venv
} else {
    Write-Info "Virtual environment already exists (.venv)"
}

Write-Info "Activating virtual environment and installing requirements..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item .env.example .env
        Write-Info ".env created from .env.example — please edit and fill TELEGRAM_BOT_TOKEN and ALLOWED_HOSTS"
    } else {
        @"
TELEGRAM_MODE=polling
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_CHAT_IDS=
DJANGO_DEBUG=True
"@ | Out-File -Encoding utf8 .env
        Write-Info "Minimal .env created — please edit it and fill TELEGRAM_BOT_TOKEN"
    }
} else {
    Write-Info ".env already exists — leaving as is"
}

# Create run wrappers
$runServerBat = Join-Path $projectRoot 'run_server.bat'
$runBotBat = Join-Path $projectRoot 'run_bot.bat'

function Write-RunBat($path, $command) {
    $content = "@echo off`r`n" +
               "cd /d %~dp0`r`n" +
               "powershell -NoProfile -ExecutionPolicy Bypass -Command \"& { .\\.venv\\Scripts\\Activate.ps1; $command }\""
    $content | Out-File -FilePath $path -Encoding ASCII -Force
    Write-Info "Created $path"
}

Write-RunBat $runServerBat "python manage.py runserver 0.0.0.0:8000"
Write-RunBat $runBotBat "python -c \"from crm.telegram_bot import create_application; create_application().run_polling()\""

Write-Info "All done. Start the server with: .\\run_server.bat"
Write-Info "Start the bot with: .\\run_bot.bat"

# Optionally create shortcuts in Start Menu
function Create-Shortcut($targetPath, $shortcutName) {
    $WshShell = New-Object -ComObject WScript.Shell
    $startMenu = [Environment]::GetFolderPath('CommonPrograms')
    $lnk = $WshShell.CreateShortcut((Join-Path $startMenu "$shortcutName.lnk"))
    $lnk.TargetPath = $targetPath
    $lnk.WorkingDirectory = $projectRoot
    $lnk.Save()
    Write-Info "Shortcut '$shortcutName' created in Start Menu"
}

try {
    Create-Shortcut((Join-Path $projectRoot 'run_server.bat'), 'WaterDeliveryCRM - Run Server')
    Create-Shortcut((Join-Path $projectRoot 'run_bot.bat'), 'WaterDeliveryCRM - Run Bot')
} catch {
    Write-Info "Could not create Start Menu shortcuts (permission issue). You can run the generated .bat files manually."
}

Write-Info "Installer finished. Edit .env and then run .\\run_server.bat to start the app."
