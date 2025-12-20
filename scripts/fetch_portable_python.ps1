<#
Download and install a per-user Python into the project `embedded_python` folder.

This script downloads the official Windows installer for the requested Python
version and runs it in quiet mode with `TargetDir` set to the project's
`embedded_python` folder. This produces a local, self-contained Python
installation that the installer scripts will use to create the virtualenv.

Notes:
- The script performs a per-user install (InstallAllUsers=0) to the target
  directory and should not require admin rights.
- The exact installer URL may change; update `$pythonInstallerUrl` if needed.
- Test the resulting `embedded_python\python.exe -m venv .venv_test` locally
  to confirm the portable install includes `venv` and `pip`.

Usage:
  powershell -ExecutionPolicy Bypass -File .\scripts\fetch_portable_python.ps1

Optional parameters:
  -Version <version>    e.g. 3.12.2
  -Arch <x86|amd64>     default amd64
#>
param(
    [string]$Version = '3.12.2',
    [ValidateSet('amd64','x86')][string]$Arch = 'amd64'
)

Set-StrictMode -Version Latest

function Write-Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Err($m) { Write-Host "[ERROR] $m" -ForegroundColor Red }

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition | Split-Path -Parent
Set-Location $root

$targetDir = Join-Path $root 'embedded_python'
if (Test-Path $targetDir) {
    Write-Info "embedded_python already exists at $targetDir"
    exit 0
}

# Build download URL for official python.org installer
$archSuffix = if ($Arch -eq 'amd64') { 'amd64' } else { 'win32' }
$installerName = "python-$Version-$archSuffix.exe"
$pythonInstallerUrl = "https://www.python.org/ftp/python/$Version/$installerName"

Write-Info "Downloading Python $Version ($Arch) from $pythonInstallerUrl"
$tmpInstaller = Join-Path $env:TEMP $installerName
try {
    Invoke-WebRequest -Uri $pythonInstallerUrl -OutFile $tmpInstaller -UseBasicParsing -ErrorAction Stop
} catch {
    Write-Err "Failed to download installer: $_"
    exit 1
}

Write-Info "Running installer into $targetDir (quiet mode)"
# Build argument list as an array to avoid quoting/parsing issues in PowerShell
$args = @(
  '/quiet',
  'InstallAllUsers=0',
  "TargetDir=$targetDir",
  'PrependPath=0',
  'Include_pip=1'
)

# Start-Process accepts an array for -ArgumentList which avoids unexpected token errors
$proc = Start-Process -FilePath $tmpInstaller -ArgumentList $args -Wait -PassThru -ErrorAction SilentlyContinue
if ($proc.ExitCode -ne 0) {
    Write-Err "Python installer exited with code $($proc.ExitCode). Check the installer log or run interactively."
    exit $proc.ExitCode
}

if (-not (Test-Path (Join-Path $targetDir 'python.exe'))) {
    Write-Err "Installation finished but python.exe not found in $targetDir"
    exit 2
}

Write-Info "Python installed into $targetDir"
Write-Info "You can now build the installer or run scripts/install_local.ps1 on the target machine to use the bundled Python."

Remove-Item $tmpInstaller -ErrorAction SilentlyContinue

exit 0
