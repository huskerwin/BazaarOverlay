$ErrorActionPreference = "Stop"

function New-BazaarShortcut {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetPath,
        [Parameter(Mandatory = $true)]
        [string]$ShortcutPath,
        [Parameter(Mandatory = $true)]
        [string]$Description,
        [Parameter(Mandatory = $true)]
        [string]$IconLocation,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [object]$Shell
    )

    if (-not (Test-Path $TargetPath)) {
        throw "Launcher script not found: $TargetPath"
    }

    $shortcut = $Shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.Description = $Description
    $shortcut.IconLocation = $IconLocation
    $shortcut.Save()

    Write-Output $ShortcutPath
}

$repo = Split-Path -Parent $PSScriptRoot
$overlayLauncher = Join-Path $repo "Run Bazaar Overlay.cmd"
$captureLauncher = Join-Path $repo "Run Capture Template.cmd"

$desktop = [Environment]::GetFolderPath("Desktop")

$overlayShortcutPath = Join-Path $desktop "Bazaar Overlay.lnk"
$captureShortcutPath = Join-Path $desktop "Bazaar Capture Template.lnk"

$shell = New-Object -ComObject WScript.Shell

New-BazaarShortcut -TargetPath $overlayLauncher -ShortcutPath $overlayShortcutPath -Description "Run Bazaar Overlay" -IconLocation "$env:SystemRoot\System32\shell32.dll,220" -WorkingDirectory $repo -Shell $shell

New-BazaarShortcut -TargetPath $captureLauncher -ShortcutPath $captureShortcutPath -Description "Run Bazaar Template Capture" -IconLocation "$env:SystemRoot\System32\shell32.dll,137" -WorkingDirectory $repo -Shell $shell
