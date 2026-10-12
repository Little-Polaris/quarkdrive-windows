# 第三方组件与许可

Git 仓库保存本项目脚本、安装入口和文档。完整 Release 包附带下列固定版本的官方程序、许可证和源码归档，本项目通过独立进程或本地 HTTP / WebDAV 与其通信。
程序二进制保持官方原样；Python 的 `python314._pth` 配置增加本项目脚本目录以加载本地模块。

本项目自身采用 GNU AGPL-3.0-only。该许可不替换第三方组件的许可，也不授予云盘平台的商标、服务或账户权利。

| 组件 | 已验证版本 | 上游许可 | 许可原文 |
| --- | --- | --- | --- |
| OpenList | 4.2.6 | GNU AGPL v3 | [LICENSE](https://github.com/OpenListTeam/OpenList/blob/v4.2.6/LICENSE) |
| OpenList 前端，由官方 OpenList 程序提供 | 4.2.6 | MIT | [LICENSE](https://github.com/OpenListTeam/OpenList-Frontend/blob/v4.2.6/LICENSE) |
| Rclone | 1.75.2 | MIT | [COPYING](https://github.com/rclone/rclone/blob/v1.75.2/COPYING) |
| WinSW | 2.12.0 | MIT | [LICENSE.txt](https://github.com/winsw/winsw/blob/v2.12.0/LICENSE.txt) |
| WinFsp | 2.1.25156 | GPL v3，另有 FLOSS 特别例外 | [License.txt](https://github.com/winfsp/winfsp/blob/v2.1/License.txt) |
| Python | 3.14.6 | PSF 许可协议及所含组件许可 | [Python license](https://docs.python.org/3.14/license.html) |

WinFsp - Windows File System Proxy, Copyright (C) Bill Zissimopoulos.
项目地址：<https://github.com/winfsp/winfsp>。

许可全文位于 `bin/licenses/`，Python 及其内置组件许可位于 `bin/python/LICENSE.txt`。
OpenList 及其前端的对应版本源码、构建脚本和依赖锁定文件位于 `bin/sources/` 的上游源码归档中；构建说明见 `docs/源码与构建.md`。
组件原始地址及校验值在 `docs/bundle-components.json`，发布包内各文件校验值在 `docs/package-sha256.json`。
若自行修改或重新分发第三方程序，请遵循对应上游的许可、版权声明及源码提供要求。Windows、PowerShell 和 .NET Framework 由 Windows 安装环境提供，不包含在发布包中。

依赖的开源许可与云盘平台的服务协议各有适用范围。使用夸克网盘应遵守其[服务协议](https://terms.alicdn.com/legal-agreement/terms/b_end_product_protocol/20230516173016165/20230516173016165.html)及账户权益。
