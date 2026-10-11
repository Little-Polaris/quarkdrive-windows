# 需要自行安装的软件

安装包仅包含脚本和说明，没有第三方程序、Python 运行环境或本机账户信息。
适用 64 位 Windows 10 / 11；Windows 自带的 PowerShell 5.1 即可，不需要 PowerShell 7。

| 软件 | 已验证版本 | 安装方法 |
| --- | --- | --- |
| Python，64 位 | 3.14.6 | 从官方下载安装器，安装时勾选 Add Python to PATH。使用系统解释器，不需要 pip 包。 |
| WinFsp | 2.1.25156 | 从官方发布页下载 MSI 并安装，提供挂载驱动。 |
| OpenList，windows-amd64 | 4.2.6 | 解压官方 ZIP，将 `openlist.exe` 放到本包的 `bin/openlist/`。 |
| Rclone，windows-amd64 | 1.75.2 | 解压官方 ZIP，将 `rclone.exe` 放到本包的 `bin/rclone/`。 |
| WinSW，.NET 4.6.1 版 | 2.12.0 | 下载 `WinSW.NET461.exe`，重命名为 `WinSW.exe`，放到本包的 `bin/winsw/`。使用 Windows 10 / 11 自带 .NET Framework。 |

官方地址：

- Python：<https://www.python.org/downloads/windows/>
- WinFsp：<https://github.com/winfsp/winfsp/releases/tag/v2.1>
- OpenList：<https://github.com/OpenListTeam/OpenList/releases/tag/v4.2.6>
- Rclone：<https://rclone.org/downloads/>，已验证版本归档 <https://downloads.rclone.org/v1.75.2/>
- WinSW：<https://github.com/winsw/winsw/releases/tag/v2.12.0>

程序也可安装到其他固定位置，并把 `openlist.exe`、`rclone.exe` 和 `WinSW.exe` 所在目录加入 PATH。脚本优先使用上表约定的 `bin/` 位置。
服务登记时保存程序的完整路径；安装后不要移动 Python 或这些程序。新安装 Python 后，关闭旧终端并重新启动安装向导，以刷新 PATH。

准备完成的目录示例：

```
QuarkDrive/
  Install.cmd
  Uninstall.cmd
  bin/
    openlist/openlist.exe
    rclone/rclone.exe
    winsw/WinSW.exe
  scripts/
  docs/
```

软件准备好后，按 `迁移安装.md` 操作。
