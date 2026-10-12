# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
param(
    [ValidatePattern('^[K-Z]$')][string]$DriveLetter = 'Q',
    [string]$CookieFile,
    [switch]$Portable,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
. (Join-Path $taskRoot 'scripts\Runtime.ps1')
if (-not [Environment]::Is64BitOperatingSystem) { throw '64-bit Windows is required.' }
$python = Get-QuarkPython $taskRoot
& $python -c "import sys; sys.path.insert(0, sys.argv[1]); from Dependencies import applications; applications(); import ssl,sqlite3,http.server,ctypes; print('Bundled applications are ready.')" (Join-Path $taskRoot 'scripts')
if ($LASTEXITCODE -ne 0) { throw 'Package files are missing or cannot run. Extract the complete Release ZIP.' }
if ($CheckOnly) {
    $msi = Join-Path $taskRoot 'bin\installers\winfsp.msi'
    if (-not (Test-Path $msi) -or (Get-AuthenticodeSignature $msi).Status -ne 'Valid') { throw 'WinFsp installer is missing or invalid.' }
    Write-Host 'Deployment prerequisites verified. No installation or service changes were performed.'
    return
}
if ($CookieFile) {
    $runtime = Join-Path $taskRoot 'runtime'
    New-Item -ItemType Directory -Force $runtime | Out-Null
    $copy = Join-Path $runtime ('deployment-cookie-' + [Guid]::NewGuid().ToString('N') + '.txt')
    # Retain the caller's input file; only consume the internal copy.
    [IO.File]::WriteAllText($copy, (Get-Content -LiteralPath $CookieFile -Raw -Encoding UTF8), (New-Object Text.UTF8Encoding($false)))
    try {
        & (Join-Path $taskRoot 'scripts\Install-Service.ps1') -DriveLetter $DriveLetter -CookieFile $copy -Portable:$Portable
        Write-Host "Deployment completed. Open This PC to use ${DriveLetter}:."
    } finally { Remove-Item -LiteralPath $copy -ErrorAction SilentlyContinue }
} else {
    & (Join-Path $taskRoot 'scripts\Setup.ps1') -DriveLetter $DriveLetter -Portable:$Portable
}
