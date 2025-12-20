param(
    [string]$InnoPath = $null
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($m) { Write-Host "[INFO]  $m" -ForegroundColor Cyan }
function Write-Err ($m) { Write-Host "[ERROR] $m" -ForegroundColor Red }

# Корень проекта
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition | Split-Path -Parent
Set-Location $root

# --- Поиск ISCC.exe ---
if (-not $InnoPath) {
    $candidates = @(
        "${Env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${Env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )

    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) {
            $InnoPath = $c
            break
        }
    }
}

if (-not $InnoPath -and $Env:INNO_PATH) {
    $InnoPath = $Env:INNO_PATH
}

if (-not $InnoPath) {
    Write-Err "Could not find ISCC.exe. Install Inno Setup or provide -InnoPath / set INNO_PATH."
    exit 2
}

if (-not (Test-Path $InnoPath)) {
    Write-Err "Provided Inno Path does not exist: $InnoPath"
    exit 3
}

Write-Info "Using ISCC.exe: $InnoPath"

# --- Проверка .iss ---
$iss = Join-Path $root 'installers\water_delivery_installer.iss'
if (-not (Test-Path $iss)) {
    Write-Err "Cannot find .iss file: $iss"
    exit 4
}

# --- embedded_python ---
$embeddedDir = Join-Path $root 'embedded_python'
if (-not (Test-Path $embeddedDir)) {
    $fetchScript = Join-Path $root 'scripts\fetch_portable_python.ps1'

    if (Test-Path $fetchScript) {
        Write-Info "embedded_python not found — running fetch_portable_python.ps1"
        try {
            & $fetchScript
        } catch {
            Write-Err "Fetching portable Python failed: $_"
        }
    } else {
        Write-Info "No fetch_portable_python.ps1 found — skipping embedded_python."
    }
}

# --- Сборка exe (опционально) ---
$buildExeScript = Join-Path $root 'scripts\build_exe.ps1'
if (Test-Path $buildExeScript) {
    Write-Info "Running build_exe.ps1"
    try {
        & $buildExeScript
    } catch {
        Write-Err "Exe build failed: $_"
    }
} else {
    Write-Info "No build_exe.ps1 found — skipping exe build."
}

# --- Запуск Inno Setup ---
Write-Info "Compiling installer: $iss"

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $InnoPath
$startInfo.Arguments = "`"$iss`""
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError  = $true
$startInfo.UseShellExecute = $false

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $startInfo
$null = $proc.Start()

while (-not $proc.HasExited) {
    $line = $proc.StandardOutput.ReadLine()
    if ($line) { Write-Host $line }
}

$out = $proc.StandardOutput.ReadToEnd()
if ($out) { Write-Host $out }

$err = $proc.StandardError.ReadToEnd()
if ($err) { Write-Err $err }

$exitCode = $proc.ExitCode

if ($exitCode -eq 0) {
    Write-Info "Inno Setup compiled successfully. See OutputDir in .iss."
    exit 0
} else {
    Write-Err "Inno Setup exited with code $exitCode"
    exit $exitCode
}
