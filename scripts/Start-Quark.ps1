# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
param(
    [ValidatePattern('^[K-Z]$')][string]$DriveLetter = 'Q',
    [switch]$ReadOnly
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
if (Get-Service QuarkMount -ErrorAction SilentlyContinue) {
    if ((Get-Service QuarkMount).Status -eq 'Running') { Write-Host 'Quark services are running.'; return }
    & (Join-Path $PSScriptRoot 'Manage-Services.ps1') -Action Start
    return
}
$taskRuntime = Join-Path $taskRoot 'runtime'
if (-not $PSBoundParameters.ContainsKey('DriveLetter') -and (Test-Path (Join-Path $taskRuntime 'settings.json'))) {
    $DriveLetter = (Get-Content (Join-Path $taskRuntime 'settings.json') -Raw -Encoding UTF8 | ConvertFrom-Json).drive_letter
}
. (Join-Path $PSScriptRoot 'Runtime.ps1')
$taskOpenList = Join-Path $taskRoot 'bin\openlist\openlist.exe'
$taskRclone = Join-Path $taskRoot 'bin\rclone\rclone.exe'
$taskPython = Get-QuarkPython $taskRoot

function Get-OwnedProcess([string]$PidName, [string]$ExePath) {
    $pidFile = Join-Path $taskRuntime $PidName
    if (Test-Path -LiteralPath $pidFile) {
        $savedId = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
        $candidate = Get-Process -Id $savedId -ErrorAction SilentlyContinue
        if ($candidate -and $candidate.Path -eq $ExePath) {
            if ($PidName -eq 'quota.pid') {
                $startFile = Join-Path $taskRuntime 'quota-start-time.txt'
                if (-not (Test-Path -LiteralPath $startFile)) { return $null }
                $startTicks = [long](Get-Content -LiteralPath $startFile -Raw).Trim()
                if ($candidate.StartTime.ToUniversalTime().Ticks -ne $startTicks) { return $null }
            }
            return $candidate
        }
    }
    return $null
}

if (-not (Get-OwnedProcess 'openlist.pid' $taskOpenList)) {
    if (Get-NetTCPConnection -LocalPort 5244 -State Listen -ErrorAction SilentlyContinue) {
        throw 'Port 5244 is in use by another process.'
    }
    $taskProcess = Start-Process -FilePath $taskOpenList -ArgumentList (
        'server --data "' + (Join-Path $taskRuntime 'data') + '"'
    ) -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru `
      -RedirectStandardOutput (Join-Path $taskRuntime 'logs\stdout.log') `
      -RedirectStandardError (Join-Path $taskRuntime 'logs\stderr.log')
    $taskProcess.Id | Set-Content (Join-Path $taskRuntime 'openlist.pid')
}
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        Invoke-RestMethod 'http://127.0.0.1:5244/api/public/settings' -TimeoutSec 2 | Out-Null
        break
    } catch {
        if ($attempt -eq 19) { throw 'OpenList did not become ready.' }
        Start-Sleep -Milliseconds 500
    }
}

if (-not (Get-OwnedProcess 'quota.pid' $taskPython)) {
    if (Get-NetTCPConnection -LocalPort 5245 -State Listen -ErrorAction SilentlyContinue) {
        throw 'Port 5245 is in use by another process.'
    }
    $taskQuota = Start-Process -FilePath $taskPython -ArgumentList (
        '"' + (Join-Path $PSScriptRoot 'Quota-WebDAV.py') + '"'
    ) -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru `
      -RedirectStandardOutput (Join-Path $taskRuntime 'logs\quota-stdout.log') `
      -RedirectStandardError (Join-Path $taskRuntime 'logs\quota-stderr.log')
    $taskQuota.Id | Set-Content (Join-Path $taskRuntime 'quota.pid')
    $taskQuota.StartTime.ToUniversalTime().Ticks | Set-Content (Join-Path $taskRuntime 'quota-start-time.txt')
}
for ($attempt = 0; $attempt -lt 5; $attempt++) {
    & $taskRclone about quark: --config (Join-Path $taskRuntime 'rclone.conf') --json | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    if ($attempt -eq 4) { throw 'Quark capacity service did not become ready.' }
    Start-Sleep -Milliseconds 500
}

if (Get-OwnedProcess 'rclone.pid' $taskRclone) {
    Write-Host 'Quark is already mounted.'
    return
}
$taskDrive = $DriveLetter + ':'
if (Test-Path ($taskDrive + '\')) { throw "Drive $taskDrive is already in use." }
$taskAccessFlag = if ($ReadOnly) { ' --read-only' } else { '' }
$taskArgs = 'mount quark: ' + $taskDrive + ' --config "' +
    (Join-Path $taskRuntime 'rclone.conf') + '" --network-mode --volname \\OpenList\Quark' +
    $taskAccessFlag + ' --vfs-cache-mode full --vfs-cache-max-size 2G --vfs-cache-max-age 1h' +
    ' --cache-dir "' + (Join-Path $taskRuntime 'cache') + '"' +
    ' --dir-cache-time 5m --poll-interval 0 --log-level NOTICE --log-file "' +
    (Join-Path $taskRuntime 'logs\rclone.log') + '"'
$taskProcess = Start-Process -FilePath $taskRclone -ArgumentList $taskArgs `
    -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $taskRuntime 'logs\rclone-stdout.log') `
    -RedirectStandardError (Join-Path $taskRuntime 'logs\rclone-stderr.log')
$taskProcess.Id | Set-Content (Join-Path $taskRuntime 'rclone.pid')
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    $taskProcess.Refresh()
    if ($taskProcess.HasExited) { throw 'Mount failed; see runtime/logs/rclone.log.' }
    if (Test-Path ($taskDrive + '\')) {
        $taskMode = if ($ReadOnly) { 'read-only' } else { 'read/write' }
        Write-Host "Quark mounted at $taskDrive ($taskMode)."
        return
    }
    Start-Sleep -Milliseconds 500
}
throw 'Mount is still starting; see runtime/logs/rclone.log.'
