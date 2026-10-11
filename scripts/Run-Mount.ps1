# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskRuntime = Join-Path $taskRoot 'runtime'
$settings = Get-Content (Join-Path $taskRuntime 'settings.json') -Raw | ConvertFrom-Json
$drive = $settings.drive_letter + ':'
$rclone = $settings.applications.rclone
# Wait for the local services and the online account before publishing capacity.
while ($true) {
    $ErrorActionPreference = 'Continue'
    & $rclone about quark: --config (Join-Path $taskRuntime 'rclone.conf') --json 2>$null | Out-Null
    $ErrorActionPreference = 'Stop'
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 5
}
& $rclone mount quark: $drive --config (Join-Path $taskRuntime 'rclone.conf') `
    --network-mode --volname '\\OpenList\Quark' `
    -o 'FileSecurity=D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;AU)' `
    --vfs-cache-mode full --vfs-cache-max-size 2G --vfs-cache-max-age 1h `
    --cache-dir (Join-Path $taskRuntime 'cache') --dir-cache-time 5m --poll-interval 0 `
    --log-level NOTICE --log-file (Join-Path $taskRuntime 'logs\rclone.log')
exit $LASTEXITCODE
