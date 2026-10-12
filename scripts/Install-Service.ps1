# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
param([ValidatePattern('^[K-Z]$')][string]$DriveLetter = 'Q', [string]$CookieFile,
      [switch]$Portable, [switch]$DriverOnly)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskRuntime = Join-Path $taskRoot 'runtime'
. (Join-Path $PSScriptRoot 'Runtime.ps1')
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($Portable -and $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run manual mode from a normal PowerShell window; driver installation will request elevation when needed.'
}
if (-not $Portable -and -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -DriveLetter ' + $DriveLetter
    if ($CookieFile) { $arguments += ' -CookieFile "' + $CookieFile + '"' }
    if ($DriverOnly) { $arguments += ' -DriverOnly' }
    $elevated = Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
        -Verb RunAs -WindowStyle Hidden -ArgumentList $arguments -Wait -PassThru
    if ($elevated.ExitCode -ne 0) { throw 'Installation failed; see runtime/install-result.json.' }
    return
}
New-Item -ItemType Directory -Force (Join-Path $taskRuntime 'logs') | Out-Null
$resultFile = Join-Path $taskRuntime 'install-result.json'
$serviceNames = @('QuarkOpenList', 'QuarkQuota', 'QuarkMount')
try {
    if ($DriverOnly) {
        Install-QuarkWinFsp $taskRoot
        @{success=$true; driver_only=$true} | ConvertTo-Json | Set-Content $resultFile -Encoding UTF8
        return
    }
    $python = Get-QuarkPython $taskRoot
    & $python -c 'import sys; sys.path.insert(0, sys.argv[1]); from Dependencies import applications; applications()' $PSScriptRoot
    if ($LASTEXITCODE -ne 0) { throw 'Required files are missing from the deployment package.' }
    foreach ($name in $serviceNames) {
        $existing = Get-CimInstance Win32_Service -Filter "Name='$name'"
        $expected = Join-Path $taskRuntime "services\$name.exe"
        if ($existing -and $Portable) { throw 'Uninstall the existing Quark services before selecting manual mode.' }
        if ($existing -and $existing.PathName.Trim('"') -ne $expected) {
            throw "Service $name already belongs to a different folder; uninstall that installation first."
        }
    }
    if (-not [Environment]::Is64BitOperatingSystem) { throw '64-bit Windows is required.' }
    $driver = Join-Path ${env:ProgramFiles(x86)} 'WinFsp\bin\winfsp-x64.dll'
    if (-not (Test-Path $driver)) {
        if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Install-QuarkWinFsp $taskRoot }
        else {
            $driverArguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -DriverOnly'
            $elevated = Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
                -Verb RunAs -WindowStyle Hidden -ArgumentList $driverArguments -Wait -PassThru
            if ($elevated.ExitCode -ne 0) { throw 'WinFsp installation failed; see runtime/install-result.json.' }
        }
    }
    # Refuse to interrupt cached files that have not reached the cloud.
    Get-ChildItem (Join-Path $taskRuntime 'cache\vfsMeta') -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        if ((Get-Content $_.FullName -Raw | ConvertFrom-Json).Dirty) {
            throw 'Pending uploads exist. Close files and wait for upload completion before installing.'
        }
    }
    foreach ($name in @('QuarkMount', 'QuarkQuota', 'QuarkOpenList')) {
        if (Get-Service $name -ErrorAction SilentlyContinue) { Stop-Service $name; }
    }
    & (Join-Path $PSScriptRoot 'Stop-Quark.ps1') -ManualOnly
    if (Test-Path ($DriveLetter + ':\')) { throw "Drive $DriveLetter is already occupied." }
    foreach ($port in @(5244, 5245)) {
        if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is occupied." }
    }
    $initArgs = @((Join-Path $PSScriptRoot 'Initialize-Quark.py'), '--drive', $DriveLetter)
    if ($CookieFile) { $initArgs += @('--cookie-file', $CookieFile) }
    & $python @initArgs
    if ($LASTEXITCODE -ne 0) { throw 'Account configuration failed; check the Cookie and retry.' }
    if ($Portable) {
        & (Join-Path $PSScriptRoot 'Start-Quark.ps1') -DriveLetter $DriveLetter
    } else {
        & $python (Join-Path $PSScriptRoot 'Configure-Services.py')
        if ($LASTEXITCODE -ne 0) { throw 'Service configuration failed.' }
        foreach ($name in $serviceNames) {
            $wrapper = Join-Path $taskRuntime "services\$name.exe"
            if (Get-Service $name -ErrorAction SilentlyContinue) { & $wrapper refresh }
            else { & $wrapper install }
            if ($LASTEXITCODE -ne 0) { throw "Unable to register service $name." }
        }
        Start-Service QuarkMount
    }
    $ready = $false
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        if (Test-Path ($DriveLetter + ':\')) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'The drive is not ready; see runtime/logs.' }
    $installedServices = if ($Portable) { @() } else { $serviceNames }
    @{success=$true; drive=$DriveLetter; services=$installedServices; portable=[bool]$Portable; time=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content $resultFile -Encoding UTF8
} catch {
    @{success=$false; error=$_.Exception.Message; time=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content $resultFile -Encoding UTF8
    if ($Portable) { throw }
    exit 1
}
