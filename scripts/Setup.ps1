# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskRuntime = Join-Path $taskRoot 'runtime'
New-Item -ItemType Directory -Force $taskRuntime | Out-Null
$existing = (Test-Path (Join-Path $taskRuntime 'data\data.db')) -and (Test-Path (Join-Path $taskRuntime 'webdav-account.json'))
$form = New-Object Windows.Forms.Form
$form.Text = '夸克网盘 - 安装自动启动服务'
$form.Size = New-Object Drawing.Size(640,370)
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
$drive.SelectedItem = 'Q'
$form.Controls.Add($drive)
$help = New-Object Windows.Forms.Label
$help.Location = New-Object Drawing.Point(20,60)
$help.Size = New-Object Drawing.Size(580,70)
$help.Text = if ($existing) { '已找到本机账户。点击安装，将当前配置注册为开机自动启动的服务。' } else {
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
$button = New-Object Windows.Forms.Button
$button.Text = '安装自动启动服务'
$button.Location = New-Object Drawing.Point(430,250)
$button.Size = New-Object Drawing.Size(170,35)
$button.Add_Click({
    if (-not $existing -and [string]::IsNullOrWhiteSpace($cookie.Text)) {
        [void][Windows.Forms.MessageBox]::Show('请先粘贴夸克 Cookie。'); return
    }
    $form.Tag = @{Drive=[string]$drive.SelectedItem; Cookie=$cookie.Text}
    $form.DialogResult = 'OK'; $form.Close()
})
$form.Controls.Add($button)
$notice = New-Object Windows.Forms.Label
$notice.Location = New-Object Drawing.Point(20,290)
$notice.Size = New-Object Drawing.Size(580,40)
$notice.Text = "WinFsp - Windows File System Proxy, Copyright (C) Bill Zissimopoulos.`r`nhttps://github.com/winfsp/winfsp"
$form.Controls.Add($notice)
if ($form.ShowDialog() -ne 'OK') { exit }
$cookiePath = Join-Path $taskRuntime 'setup-cookie.txt'
try {
    $installArgs = @{DriveLetter=$form.Tag.Drive}
    if (-not $existing) {
        [IO.File]::WriteAllText($cookiePath, $form.Tag.Cookie, (New-Object Text.UTF8Encoding($false)))
        $installArgs.CookieFile = $cookiePath
    }
    & (Join-Path $PSScriptRoot 'Install-Service.ps1') @installArgs
    [void][Windows.Forms.MessageBox]::Show('安装完成，盘符将随 Windows 自动启动。打开资源管理器“此电脑”即可使用。')
    Start-Process explorer.exe -ArgumentList 'shell:MyComputerFolder'
} catch {
    $result = Join-Path $taskRuntime 'install-result.json'
    $message = if (Test-Path $result) { (Get-Content $result -Raw | ConvertFrom-Json).error } else { $_.Exception.Message }
    [void][Windows.Forms.MessageBox]::Show($message, '安装失败')
} finally {
    Remove-Item -LiteralPath $cookiePath -ErrorAction SilentlyContinue
    $form.Dispose()
}
