# QuarkDrive — Windows 网盘挂载服务

将 OpenList 中的夸克网盘挂载为 Windows 网络驱动器，支持读写、真实容量显示，以及随 Windows 自动启动。

```text
夸克网盘 → OpenList → 本地 WebDAV 容量适配 → Rclone / WinFsp → Q:
```

## 功能

- 在资源管理器“此电脑”中显示网络盘符，默认 `Q:`，安装时可选择其他空闲盘符。
- 支持上传、读取、新建目录、编辑、重命名、移动和删除。
- 显示账户真实总容量及剩余容量；容量接口结果缓存约 60 秒。
- 注册三个 Windows 服务，按依赖顺序启动，意外退出后自动恢复。
- 文件使用本机缓存写回，服务重启后保留原缓存。
- 提供图形安装向导、服务控制脚本和卸载入口。

## 安装

适用 64 位 Windows 10 / 11。使用 Windows 自带 PowerShell 5.1；不需要额外 pip 包。

1. 从仓库的 **Releases** 下载 `QuarkDrive-Windows-x64.zip`，完整解压到本机固定目录。
2. 双击 `Install.cmd`，或运行下面的 PowerShell 命令。
3. 选择盘符，按向导填写自己的夸克 Cookie。
4. 批准 Windows 管理员授权提示。安装完成后打开资源管理器“此电脑”。

```powershell
powershell -NoProfile -STA -ExecutionPolicy Bypass -File .\Deploy.ps1
```

Release 包已包含 OpenList、Rclone、WinSW、Python 运行环境和 WinFsp 安装器，不需要逐个下载或配置 PATH。
部署脚本自动安装缺少的 WinFsp、初始化账户和注册服务。账户在本机单独配置。
向导中的“注册为 Windows 服务，开机自动启动”可以自行勾选；不勾选则以普通后台进程运行，之后用启动、停止脚本控制。
命令行添加 `-Portable` 可预选手动模式。手动模式从普通权限的 PowerShell 启动，安装驱动时会单独请求管理员授权。
Windows 若提示驱动安装需要重启，重启后再运行同一部署脚本即可继续。
详细步骤见 [迁移安装](docs/迁移安装.md)。

## 使用

选择服务模式时，开机后由 Windows 自动启动服务；联网和账户验证完成后盘符可用。

| 服务 | 用途 |
| --- | --- |
| `QuarkOpenList` | 连接网盘并提供读写接口 |
| `QuarkQuota` | 本地 WebDAV 转发及容量适配 |
| `QuarkMount` | 挂载 Windows 网络驱动器 |

OpenList 管理地址为 <http://127.0.0.1:5244>，用户名为 `admin`，密码保存在本机 `runtime/admin-password.txt`。
Cookie 更新位置为 OpenList 的“存储 → /Quark”。

手动控制可运行 `scripts/Start-Quark.ps1`、`scripts/Stop-Quark.ps1`，或使用 Windows 服务管理器。
双击 `Uninstall.cmd` 移除服务，本地配置与缓存会保留。

文件关闭后从缓存上传；停止服务或关机前等待上传完成。缓存目标上限为 2 GB，打开的大文件可能超过该值。
Windows 服务以 LocalSystem 运行，盘符对本机登录用户开放读写，适合自己的 Windows 设备。
手动模式的盘符由当前用户进程挂载；退出 Windows 后，下次使用时运行 `scripts/Start-Quark.ps1`。从服务模式切换到手动模式时，先运行 `Uninstall.cmd` 移除服务，再重新运行部署向导并取消服务选项。

## 目录

```text
Install.cmd          安装入口
Uninstall.cmd        卸载入口
scripts/             安装、挂载、容量适配与验证
docs/                依赖清单、使用说明和验证记录
bin/                 随 Release 附带的程序、运行环境、许可和源码，排除在 Git 之外
runtime/             本机配置、账户、数据库、日志和缓存，排除在 Git 和发布包之外
dist/                本地生成的发布包，排除在 Git 之外
```

## 构建发布包

维护者从源码打包时需要 Python 和 Go 1.27，用于准备程序及对应的依赖源码，然后执行：

```powershell
python scripts/Prepare-Bundle.py
python scripts/Build-Package.py
```

生成 ZIP 和 SHA-256 校验文件。打包使用明确的文件范围，逐文件核对校验值，不读取运行目录。
组件下载固定版本并检查 SHA-256；准备时可使用 `--proxy http://127.0.0.1:7890`。
源代码可从仓库及 GitHub 自动生成的源码归档取得。

实测覆盖读写、云端内容核对、服务重启、故障恢复及空白数据库初始化，见 [验证记录](docs/验证记录.md)。

## 许可证与依赖

本项目的脚本和说明采用 **GNU AGPL-3.0-only**，完整文本见 [LICENSE](LICENSE)。
各独立程序保留原项目的许可证，见 [第三方组件说明](THIRD_PARTY_NOTICES.md)。

WinFsp - Windows File System Proxy, Copyright (C) Bill Zissimopoulos.
项目地址：<https://github.com/winfsp/winfsp>。

这是使用 OpenList、Rclone 等开源项目组成的本地集成工具。使用云盘时应遵守平台服务协议和自己的账户权益范围：
[夸克网盘服务协议](https://terms.alicdn.com/legal-agreement/terms/b_end_product_protocol/20230516173016165/20230516173016165.html)。

## 问题反馈

提交问题时，请说明 Windows 版本、依赖版本、安装阶段和已脱敏的错误信息。
Cookie、密码、`runtime/`、网盘文件列表和完整数据库应保留在本机。
