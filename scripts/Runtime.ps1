# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
function Get-QuarkPython([string]$Root) {
    $bundled = Join-Path $Root 'bin\python\python.exe'
    if (Test-Path -LiteralPath $bundled) { return $bundled }
    return (Get-Command python -ErrorAction Stop).Source
}

function Install-QuarkWinFsp([string]$Root) {
    $driver = Join-Path ${env:ProgramFiles(x86)} 'WinFsp\bin\winfsp-x64.dll'
    if (Test-Path -LiteralPath $driver) { return }
    $installer = Join-Path $Root 'bin\installers\winfsp.msi'
    if (-not (Test-Path -LiteralPath $installer)) { throw 'The WinFsp installer is missing. Extract the complete Release ZIP.' }
    if ((Get-AuthenticodeSignature -LiteralPath $installer).Status -ne 'Valid') { throw 'The WinFsp installer signature is invalid.' }
    $log = Join-Path $Root 'runtime\logs\winfsp-install.log'
    $arguments = '/i "' + $installer + '" /qn /norestart /l*v "' + $log + '"'
    $process = Start-Process "$env:SystemRoot\System32\msiexec.exe" -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -eq 3010) { throw 'WinFsp requires a Windows restart. Restart, then run Deploy.ps1 again.' }
    if ($process.ExitCode -ne 0) { throw "WinFsp installation failed ($($process.ExitCode)); see runtime/logs/winfsp-install.log." }
    if (-not (Test-Path -LiteralPath $driver)) { throw 'WinFsp was installed but its driver is unavailable.' }
}
