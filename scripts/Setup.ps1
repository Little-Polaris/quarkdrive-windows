# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
param([ValidatePattern('^[K-Z]$')][string]$DriveLetter = 'Q', [switch]$Portable)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskRuntime = Join-Path $taskRoot 'runtime'
New-Item -ItemType Directory -Force $taskRuntime | Out-Null
$existing = (Test-Path (Join-Path $taskRuntime 'data\data.db')) -and (Test-Path (Join-Path $taskRuntime 'webdav-account.json'))
$form = New-Object Windows.Forms.Form
$form.Text = '夸克网盘 - 一键部署'
$form.Size = New-Object Drawing.Size(640,410)
$form.StartPosition = 'CenterScreen'
$label = New-Object Windows.Forms.Label
$label.Text = '盘符（K-Z）：'
$label.Location = New-Object Drawing.Point(20,20)
$label.AutoSize = $true
$form.Controls.Add($label)
$drive = New-Object Windows.Forms.ComboBox
$drive.Location = New-Object Drawing.Point(170,16)
$drive.DropDownStyle = 'DropDownList'
[void]$drive.Items.AddRange([string[]](75..90 | ForEach-Object { [char]$_ }))
$drive.SelectedItem = $DriveLetter
$form.Controls.Add($drive)
$help = New-Object Windows.Forms.Label
$help.Location = New-Object Drawing.Point(20,60)
$help.Size = New-Object Drawing.Size(580,70)
$help.Text = if ($existing) { '已找到本机账户。选择运行方式后点击部署。切换到手动模式前，请先卸载现有服务。' } else {
    '先在 pan.quark.cn 登录。按 F12 打开“网络”，刷新页面，选择 drive.quark.cn 请求，复制请求标头中的 Cookie 完整值，粘贴到下方。'
}
$form.Controls.Add($help)
$cookie = New-Object Windows.Forms.TextBox
$cookie.Location = New-Object Drawing.Point(20,135)
$cookie.Size = New-Object Drawing.Size(580,85)
$cookie.Multiline = $false
$cookie.UseSystemPasswordChar = $true
$cookie.Enabled = -not $existing
$form.Controls.Add($cookie)
$register = New-Object Windows.Forms.CheckBox
$register.Text = '注册为 Windows 服务，开机自动启动'
$register.Checked = -not $Portable
$register.Location = New-Object Drawing.Point(20,225)
$register.Size = New-Object Drawing.Size(580,30)
$form.Controls.Add($register)
$button = New-Object Windows.Forms.Button
$button.Text = '部署并挂载'
$button.Location = New-Object Drawing.Point(430,280)
$button.Size = New-Object Drawing.Size(170,35)
$button.Add_Click({
    if (-not $existing -and [string]::IsNullOrWhiteSpace($cookie.Text)) {
        [void][Windows.Forms.MessageBox]::Show('请先粘贴夸克 Cookie。'); return
    }
    $form.Tag = @{Drive=[string]$drive.SelectedItem; Cookie=$cookie.Text; Service=$register.Checked}
    $form.DialogResult = 'OK'; $form.Close()
})
$form.Controls.Add($button)
$notice = New-Object Windows.Forms.Label
$notice.Location = New-Object Drawing.Point(20,330)
$notice.Size = New-Object Drawing.Size(580,40)
$notice.Text = "WinFsp - Windows File System Proxy, Copyright (C) Bill Zissimopoulos.`r`nhttps://github.com/winfsp/winfsp"
$form.Controls.Add($notice)
if ($form.ShowDialog() -ne 'OK') { exit }
$cookiePath = Join-Path $taskRuntime 'setup-cookie.txt'
try {
    $installArgs = @{DriveLetter=$form.Tag.Drive; Portable=(-not $form.Tag.Service)}
    if (-not $existing) {
        [IO.File]::WriteAllText($cookiePath, $form.Tag.Cookie, (New-Object Text.UTF8Encoding($false)))
        $installArgs.CookieFile = $cookiePath
    }
    & (Join-Path $PSScriptRoot 'Install-Service.ps1') @installArgs
    $successText = if ($form.Tag.Service) { '部署完成，盘符将随 Windows 自动启动。' } else {
        '部署完成，已挂载盘符。下次需要使用时运行 scripts/Start-Quark.ps1。'
    }
    [void][Windows.Forms.MessageBox]::Show($successText)
    Start-Process explorer.exe -ArgumentList 'shell:MyComputerFolder'
} catch {
    $result = Join-Path $taskRuntime 'install-result.json'
    $message = if (Test-Path $result) { (Get-Content $result -Raw | ConvertFrom-Json).error } else { $_.Exception.Message }
    [void][Windows.Forms.MessageBox]::Show($message, '安装失败')
} finally {
    Remove-Item -LiteralPath $cookiePath -ErrorAction SilentlyContinue
    $form.Dispose()
}
