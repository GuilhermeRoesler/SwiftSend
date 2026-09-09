#Requires -Version 5.1
<#
.SYNOPSIS
  Encerra o SwiftSend com segurança e só então inicia o instalador/atualização.
.PARAMETER TargetPid
  PID do processo SwiftSend a encerrar.
.PARAMETER Installer
  Caminho absoluto do instalador (Setup.exe / AppImage / DMG) já baixado.
.PARAMETER TimeoutSec
  Segundos aguardando encerramento gracioso antes de force kill. Padrão: 10.
#>
param(
    [Parameter(Mandatory = $true)]
    [int]$TargetPid,

    [Parameter(Mandatory = $true)]
    [string]$Installer,

    [int]$TimeoutSec = 10
)

$ErrorActionPreference = "Continue"

function Write-Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg
    try {
        Add-Content -LiteralPath (Join-Path $env:TEMP "swiftsend-update.log") -Value $line -Encoding UTF8
    } catch {}
}

Write-Log "apply_update start pid=$TargetPid installer=$Installer timeout=$TimeoutSec"

if (-not (Test-Path -LiteralPath $Installer)) {
    Write-Log "ERROR: installer not found"
    exit 2
}

$proc = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
if ($proc) {
    try {
        $null = $proc.CloseMainWindow()
        Write-Log "CloseMainWindow sent"
    } catch {
        Write-Log "CloseMainWindow failed: $_"
    }

    $deadline = (Get-Date).AddSeconds([Math]::Max(1, $TimeoutSec))
    while ((Get-Date) -lt $deadline) {
        $alive = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
        if (-not $alive) {
            Write-Log "process exited gracefully"
            break
        }
        Start-Sleep -Milliseconds 400
    }

    $still = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
    if ($still) {
        Write-Log "force kill after timeout"
        try {
            Stop-Process -Id $TargetPid -Force -ErrorAction Stop
        } catch {
            Write-Log "Stop-Process failed: $_"
            & taskkill.exe /F /PID $TargetPid 2>$null | Out-Null
        }
        Start-Sleep -Milliseconds 500
    }
} else {
    Write-Log "process already gone"
}

# Confirma que o PID não existe mais antes de abrir o instalador.
$final = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
if ($final) {
    Write-Log "ERROR: process still alive; abort installer"
    exit 3
}

Write-Log "starting installer"
try {
    Start-Process -FilePath $Installer -WorkingDirectory (Split-Path -Parent $Installer)
} catch {
    Write-Log "ERROR starting installer: $_"
    exit 4
}

Write-Log "done"
exit 0
