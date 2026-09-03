#Requires -Version 5.1
<#
.SYNOPSIS
  Gera SwiftSend.exe (PyInstaller) e o instalador Inno Setup.
.PARAMETER Version
  Versão exibida no setup (ex.: 1.2.3). Padrão: 0.0.0-dev.
.PARAMETER SkipBuild
  Não roda PyInstaller; usa python/dist/SwiftSend.exe existente.
.PARAMETER IsccPath
  Caminho explícito para ISCC.exe (opcional).
#>
param(
    [string]$Version = "0.0.0-dev",
    [switch]$SkipBuild,
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonDir = Join-Path $RepoRoot "python"
$ExePath = Join-Path $PythonDir "dist\SwiftSend.exe"
$IssPath = Join-Path $PSScriptRoot "SwiftSend.iss"
$OutputDir = Join-Path $PSScriptRoot "output"

function Get-VersionInfo([string]$ver) {
    # "v1.2.3-rc.1" / "1.2.3" -> "1.2.3.0"
    $clean = $ver.TrimStart("v", "V")
    if ($clean -match "^(\d+)(?:\.(\d+))?(?:\.(\d+))?") {
        $a = $Matches[1]
        $b = if ($Matches[2]) { $Matches[2] } else { "0" }
        $c = if ($Matches[3]) { $Matches[3] } else { "0" }
        return "$a.$b.$c.0"
    }
    return "0.0.0.0"
}

function Find-ISCC([string]$explicit) {
    if ($explicit -and (Test-Path -LiteralPath $explicit)) {
        return (Resolve-Path $explicit).Path
    }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path -LiteralPath $p)) {
            return $p
        }
    }
    return $null
}

Write-Host "=== SwiftSend installer ==="
Write-Host "Repo:    $RepoRoot"
Write-Host "Version: $Version"

if (-not $SkipBuild) {
    Write-Host "`n--- PyInstaller (python/build.py) ---"
    Push-Location $PythonDir
    try {
        & python build.py
        if ($LASTEXITCODE -ne 0) {
            throw "build.py falhou com código $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Executável não encontrado: $ExePath (rode sem -SkipBuild ou gere o PyInstaller antes)"
}

$iscc = Find-ISCC $IsccPath
if (-not $iscc) {
    throw @"
ISCC.exe (Inno Setup 6) não encontrado.
Instale: https://jrsoftware.org/isinfo.php
Ou passe -IsccPath 'C:\...\ISCC.exe'
"@
}

$versionInfo = Get-VersionInfo $Version
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Host "`n--- Inno Setup ---"
Write-Host "ISCC: $iscc"
Write-Host "VersionInfo: $versionInfo"

& $iscc `
    "/DMyAppVersion=$Version" `
    "/DMyAppVersionInfo=$versionInfo" `
    $IssPath

if ($LASTEXITCODE -ne 0) {
    throw "ISCC falhou com código $LASTEXITCODE"
}

$setup = Join-Path $OutputDir "SwiftSend-Setup-$Version.exe"
if (-not (Test-Path -LiteralPath $setup)) {
    throw "Setup não gerado: $setup"
}

Write-Host "`nSUCESSO: $setup"
