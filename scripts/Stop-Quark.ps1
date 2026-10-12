# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
param([switch]$ManualOnly)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskRuntime = Join-Path $taskRoot 'runtime'
. (Join-Path $PSScriptRoot 'Runtime.ps1')
if (-not $ManualOnly -and (Get-Service QuarkMount -ErrorAction SilentlyContinue)) {
    & (Join-Path $PSScriptRoot 'Manage-Services.ps1') -Action Stop
    return
}
Get-ChildItem (Join-Path $taskRuntime 'cache\vfsMeta') -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    if ((Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json).Dirty) { throw 'Wait for pending uploads before stopping the mount.' }
}
foreach ($entry in @(
    @{ PidFile = 'rclone.pid'; Exe = (Join-Path $taskRoot 'bin\rclone\rclone.exe') },
    @{ PidFile = 'quota.pid'; Exe = (Get-QuarkPython $taskRoot) },
    @{ PidFile = 'openlist.pid'; Exe = (Join-Path $taskRoot 'bin\openlist\openlist.exe') }
)) {
    $taskPidFile = Join-Path $taskRuntime $entry.PidFile
    if (Test-Path -LiteralPath $taskPidFile) {
        $taskProcessId = [int](Get-Content -LiteralPath $taskPidFile -Raw).Trim()
        $taskProcess = Get-Process -Id $taskProcessId -ErrorAction SilentlyContinue
        if ($taskProcess -and $taskProcess.Path -eq $entry.Exe) {
            if ($entry.PidFile -eq 'quota.pid') {
                $startFile = Join-Path $taskRuntime 'quota-start-time.txt'
                if (-not (Test-Path -LiteralPath $startFile)) { continue }
                $startTicks = [long](Get-Content -LiteralPath $startFile -Raw).Trim()
                if ($taskProcess.StartTime.ToUniversalTime().Ticks -ne $startTicks) { continue }
            }
            Stop-Process -Id $taskProcessId -Force
        }
    }
}
Write-Host 'Quark mount and local OpenList stopped.'
