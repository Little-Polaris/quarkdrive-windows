# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
param([ValidateSet('Start','Stop','Restart')][string]$Action = 'Start')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskRuntime = Join-Path $taskRoot 'runtime'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $process = Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Verb RunAs -WindowStyle Hidden `
        -ArgumentList ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -Action ' + $Action) -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Service control failed; check pending uploads and service ownership.' }
    return
}
foreach ($name in @('QuarkOpenList','QuarkQuota','QuarkMount')) {
    $service = Get-CimInstance Win32_Service -Filter "Name='$name'"
    if (-not $service -or $service.PathName.Trim('"') -ne (Join-Path $taskRuntime "services\$name.exe")) {
        throw "Service $name is missing or belongs to another installation."
    }
}
if ($Action -in @('Stop','Restart')) {
    Get-ChildItem (Join-Path $taskRuntime 'cache\vfsMeta') -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        if ((Get-Content $_.FullName -Raw | ConvertFrom-Json).Dirty) { throw 'Wait for pending uploads before stopping services.' }
    }
    foreach ($name in @('QuarkMount','QuarkQuota','QuarkOpenList')) { Stop-Service $name }
}
if ($Action -in @('Start','Restart')) { Start-Service QuarkMount }
