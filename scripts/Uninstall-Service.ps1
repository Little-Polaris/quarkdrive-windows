# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
if (-not (Get-Service QuarkMount,QuarkQuota,QuarkOpenList -ErrorAction SilentlyContinue)) {
    & (Join-Path $PSScriptRoot 'Stop-Quark.ps1') -ManualOnly
    Write-Host 'Manual mount stopped. Local configuration and cache have been retained.'
    return
}
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $process = Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Verb RunAs -WindowStyle Hidden `
        -ArgumentList ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"') -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Uninstallation failed; pending uploads or a different installation may exist.' }
    return
}
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskRuntime = Join-Path $taskRoot 'runtime'
Get-ChildItem (Join-Path $taskRuntime 'cache\vfsMeta') -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    if ((Get-Content $_.FullName -Raw | ConvertFrom-Json).Dirty) { throw 'Wait for pending uploads before uninstalling.' }
}
foreach ($name in @('QuarkMount','QuarkQuota','QuarkOpenList')) {
    $service = Get-CimInstance Win32_Service -Filter "Name='$name'"
    $wrapper = Join-Path $taskRuntime "services\$name.exe"
    if ($service) {
        if ($service.PathName.Trim('"') -ne $wrapper) { throw "Service $name belongs to a different installation." }
        Stop-Service $name
        & $wrapper uninstall
        if ($LASTEXITCODE -ne 0) { throw "Unable to unregister $name." }
    }
}
Write-Host 'Services removed. Local account data and cache have been retained.'
