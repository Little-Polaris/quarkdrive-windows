# 包内依赖

完整 Release 已附带下表组件，无需逐个下载、安装 Python 或修改 PATH。使用 Windows 10 / 11 自带的 PowerShell 和 .NET Framework 即可。

| 软件 | 固定版本 | 部署方式 |
| --- | --- | --- |
| OpenList，windows-amd64 | 4.2.6 | 使用包内 bin/openlist/openlist.exe |
| Rclone，windows-amd64 | 1.75.2 | 使用包内 bin/rclone/rclone.exe |
| WinSW，.NET 4.6.1 版 | 2.12.0 | 使用包内 bin/winsw/WinSW.exe，注册系统服务 |
| Python，64 位嵌入式环境 | 3.14.6 | 使用包内 bin/python/python.exe，不依赖系统 Python |
| WinFsp | 2.1.25156 | 已安装时复用；否则自动运行包内 MSI 安装器 |

完整解压后运行 Deploy.ps1 或双击 Install.cmd，按向导填写自己的 Cookie 并允许 Windows 管理员授权。

依赖安装使用包内文件，网盘功能仍需要网络连接。安装目录及其所在磁盘应在开机时可用；不要在安装后移动目录。

需要只检查程序能否运行时：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Deploy.ps1 -CheckOnly
```

固定版本的官方来源和 SHA-256 位于 bundle-components.json，组件许可和版权见根目录 THIRD_PARTY_NOTICES.md。

WinFsp - Windows File System Proxy, Copyright (C) Bill Zissimopoulos.
项目地址：<https://github.com/winfsp/winfsp>。
