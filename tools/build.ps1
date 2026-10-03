# Builds a mod under mods/<Mod> with the VS 2022 MSVC toolchain and its bundled vcpkg.
# Output is staged to mods/<Mod>/dist/ by the mod's CMake post-build step; nothing is written to a game folder.
param(
    [string]$Mod = 'HelloSKSE',
    [string]$Preset = 'release',
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$modDir = Join-Path $repoRoot "mods\$Mod"
if (-not (Test-Path (Join-Path $modDir 'CMakePresets.json'))) {
    throw "No CMakePresets.json in $modDir"
}

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath = & $vswhere -version '[17.0,18.0)' -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) {
    throw 'Visual Studio 2022 with the MSVC x64 toolset was not found.'
}

Import-Module (Join-Path $vsPath 'Common7\Tools\Microsoft.VisualStudio.DevShell.dll')
Enter-VsDevShell -VsInstallPath $vsPath -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64' | Out-Null

if (-not $env:VCPKG_ROOT) {
    $env:VCPKG_ROOT = Join-Path $vsPath 'VC\vcpkg'
}
Write-Host "VS:    $vsPath"
Write-Host "vcpkg: $env:VCPKG_ROOT"

Push-Location $modDir
try {
    # CMake writes message() output to stderr; that must not abort the script.
    $ErrorActionPreference = 'Continue'
    if ($Clean -and (Test-Path "build\$Preset")) {
        Remove-Item -Recurse -Force "build\$Preset"
    }
    cmake --preset $Preset
    if ($LASTEXITCODE -ne 0) { throw "configure failed ($LASTEXITCODE)" }
    cmake --build --preset $Preset
    if ($LASTEXITCODE -ne 0) { throw "build failed ($LASTEXITCODE)" }
}
finally {
    Pop-Location
}

Write-Host "Staged: $(Join-Path $modDir 'dist')"
