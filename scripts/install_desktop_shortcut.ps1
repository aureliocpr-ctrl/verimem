# Create Desktop shortcuts for HippoAgent.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcut.ps1
#
# Idempotent: re-running just refreshes the targets to the current location
# of this repo (so it survives moving the project, mergeing a worktree, etc.).

$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$Desktop     = [Environment]::GetFolderPath("Desktop")

function New-Shortcut {
    param(
        [string]$LinkPath,
        [string]$Target,
        [string]$WorkingDir,
        [string]$Description,
        [string]$IconPath
    )
    $WS = New-Object -ComObject WScript.Shell
    $sc = $WS.CreateShortcut($LinkPath)
    $sc.TargetPath       = $Target
    $sc.WorkingDirectory = $WorkingDir
    $sc.Description      = $Description
    if ($IconPath) { $sc.IconLocation = $IconPath }
    $sc.Save()
    Write-Host "  [ok] $LinkPath" -ForegroundColor Green
    Write-Host "       -> $Target" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Installing HippoAgent Desktop shortcuts..." -ForegroundColor Cyan
Write-Host "  project: $ProjectRoot"
Write-Host "  desktop: $Desktop"
Write-Host ""

New-Shortcut `
    -LinkPath    (Join-Path $Desktop "HippoAgent Dashboard.lnk") `
    -Target      (Join-Path $ProjectRoot "scripts\launch_dashboard.bat") `
    -WorkingDir  $ProjectRoot `
    -Description "Launch the HippoAgent web dashboard (browser at :8765)" `
    -IconPath    "$env:SystemRoot\System32\shell32.dll,167"

New-Shortcut `
    -LinkPath    (Join-Path $Desktop "HippoAgent CLI.lnk") `
    -Target      (Join-Path $ProjectRoot "scripts\launch_cli.bat") `
    -WorkingDir  $ProjectRoot `
    -Description "Open a HippoAgent CLI shell (venv activated)" `
    -IconPath    "$env:SystemRoot\System32\shell32.dll,25"

New-Shortcut `
    -LinkPath    (Join-Path $Desktop "HippoAgent TUI.lnk") `
    -Target      (Join-Path $ProjectRoot "scripts\launch_tui.bat") `
    -WorkingDir  $ProjectRoot `
    -Description "Launch the HippoAgent terminal UI (chat, skills, episodes)" `
    -IconPath    "$env:SystemRoot\System32\shell32.dll,21"

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
Write-Host "Double-click any of the three icons on your Desktop to launch."
Write-Host ""
