# Clash Verge CLI 🖥️

[![CI](https://github.com/Kerry1020/clash-verge-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Kerry1020/clash-verge-cli/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)

[English](README.md) | 简体中文

Clash Verge（Rev）/ mihomo 客户端的命令行工具，支持 macOS、Linux 和 Windows：在终端里管理代理、订阅、系统代理 / TUN、端口、备份和日志。

所有平台共用一套代码，操作系统和 Clash Verge 配置目录都会自动识别。

## 功能特性

### 📋 订阅管理
- 列出、添加、删除、激活订阅
- 支持通过 URL 导入订阅
- 按名称或 UID 切换订阅

### 🌐 代理管理
- 列出所有代理与代理组（可按组筛选）
- 通过正在运行的 Clash 内核测试某个组内节点的延迟
- 为任意代理组选择节点（立即生效，并记录到 `profiles.yaml`）

### 🔌 系统代理
- 开启 / 关闭 / 切换系统代理
- 开启 / 关闭 / 切换 TUN 模式
- 查看代理守卫（Proxy Guard）状态

### 📊 流量
- 当前订阅的上传 / 下载 / 总用量，以 GB 显示

### 🛡️ 守护模式
- 调用外部脚本 `minimax_guardian.py`，监控 API 连通性并在超时时自动切换节点
- 可配置检测间隔和延迟阈值

### 💾 备份与恢复
- 一条命令备份配置文件，可自定义备份名
- 列出并恢复历史备份

### 📝 日志与诊断
- 查看最新日志、按关键字搜索日志
- 快速健康检查（Clash 控制器 + 经本地代理发起一次 HTTPS 请求）

### ⚙️ 高级配置
- 端口配置（HTTP / SOCKS / Mixed / Redir）
- 查看 DNS 配置与分流规则
- 直接修改 `verge.yaml` 中的配置项（实验性）

## 快速开始

环境要求：Python 3.8+（依赖 `click>=8`、`pyyaml>=6`、`requests>=2.28`，安装时自动拉取）。

### 作为命令行工具安装（推荐，全平台）

```bash
git clone https://github.com/Kerry1020/clash-verge-cli.git
cd clash-verge-cli
pip install .            # 或：pipx install .

clash-verge --help
python -m clash_verge_cli --help   # 等价写法
```

`pip install .` 会安装 `clash-verge` 命令（入口为 `clash_verge_cli.commands:main`）。

### 免安装直接运行

旧的两个脚本仍然保留，作为同一个包（`src/clash_verge_cli`）的轻量启动器，原有命令和软链接都能继续使用：

```bash
pip install -r requirements.txt

# macOS / Linux
./clash_verge_cli.py --help

# Windows（两个启动器完全相同，平台会自动识别）
python clash_verge_cli_windows.py --help
python clash_verge_cli.py --help
```

软链接同样可用：

```bash
sudo ln -s $(pwd)/clash_verge_cli.py /usr/local/bin/clash-verge
```

### 上手示例

```bash
# 查看状态
clash-verge status

# 列出订阅
clash-verge profiles

# 激活订阅
clash-verge activate "my-profile"

# 测试代理延迟（名称含空格 / emoji / 中文都没问题）
clash-verge test "🚀 节点选择"
```

## 使用

### 全局选项

全局选项要写在子命令**之前**，例如 `clash-verge --timeout 10 test GLOBAL`。

| 选项 | 环境变量 | 说明 |
|------|----------|------|
| `--config-dir PATH` | `CLASH_VERGE_DIR` | Clash Verge 配置目录（默认自动识别） |
| `--controller ADDR` | `CLASH_API_URL` | 外部控制器地址，如 `127.0.0.1:9097`（默认读取 `clash-verge.yaml` 中的 `external-controller`） |
| `--secret TEXT` | `CLASH_API_SECRET` | 控制器密钥（默认读取 `clash-verge.yaml` 中的 `secret`） |
| `--timeout SEC` | | 网络超时（秒），默认 `5`，最小 `0.1` |
| `-V, --version` | | 显示版本 |
| `-h, --help` | | 显示帮助 |

### 命令一览

| 命令 | 选项 | 说明 |
|------|------|------|
| `status` | `--json` | 综合状态 |
| `profiles` | `--json` | 列出所有订阅 |
| `activate <name>` | | 切换订阅（名称或 UID） |
| `add <url>` | `--name TEXT` | 通过 URL 添加订阅 |
| `delete <name>` | | 删除订阅 |
| `proxies` | `--json`、`--group TEXT` | 列出所有代理 |
| `test <group>` | `--limit N`（5）、`--url URL`、`--json` | 测试代理组延迟 |
| `select <group> <proxy>` | | 选择节点 |
| `sysproxy` | `--json` | 查看系统代理状态 |
| `sysproxy-set on/off/toggle` | | 控制系统代理（也可写作 `sysproxy_set`） |
| `tun on/off/toggle` | | 控制 TUN 模式 |
| `ports` | `--json` | 查看端口配置 |
| `port-set <http/socks/mixed/redir> <port>` | `--enable/--disable` | 设置端口（也可写作 `port_set`） |
| `dns` | `--json` | 查看 DNS 配置 |
| `rules` | `--json`、`--type TEXT`、`--limit N`（20） | 查看分流规则 |
| `traffic` | `--json` | 查看流量统计 |
| `backup [name]` | | 创建备份 |
| `backups` | `--json` | 列出备份 |
| `restore <name>` | | 恢复备份 |
| `logs` | `--lines N`（50）、`--json` | 查看日志 |
| `loggrep <keyword>` | `--lines N`（100） | 搜索日志 |
| `guardian` | `--once`、`--interval SEC`（120）、`--max-latency MS`（3000） | 自动修复模式 |
| `health` | | 快速健康检查 |
| `restart` | | 重启 Clash Verge |
| `open-dir` / `open-logs` | | 打开配置 / 日志目录（也可写作 `open_dir` / `open_logs`） |
| `config` | `--json` | 查看 Clash 配置 |
| `vergecfg` | `--json` | 查看 Verge 配置 |
| `webui` | `--json` | 查看 Web UI 列表 |
| `core` | | 查看 Clash 内核 |
| `path` | | 显示识别到的配置目录 |
| `set <key> <value>` | | 设置 `verge.yaml` 配置项（实验性） |
| `refresh` | | touch `profiles.yaml` 以触发重新加载 |

> `test`、`select` 和 `health` 通过外部控制器（REST API）与正在运行的 Clash 内核通信，因此 Clash Verge 必须处于运行状态。密钥从 `clash-verge.yaml` 读取，并以 `Authorization: Bearer <secret>` 发送。`test` 默认使用 `verge.yaml` 中的 `default_latency_test` 作为测速地址，未配置时使用 `https://www.gstatic.com/generate_204`。
>
> `sysproxy-set`、`tun`、`port-set`、`activate` 和 `set` 会直接修改 Clash Verge 的配置文件，Clash Verge 重新加载后生效（必要时执行 `restart`）。
>
> `health` 先检查控制器，再经本地 mixed 端口（默认 `7897`）向 `https://api.minimax.io/anthropic` 发起一次 HTTPS 请求，任意一项失败都会以 `1` 退出。

### 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 成功 |
| `1` | 出错（未找到、控制器无法连接、健康检查失败等），错误信息输出到 stderr |
| `2` | 用法或参数错误 |

### JSON 输出

上表中带 `--json` 的命令都可以输出便于程序处理的 JSON：

```bash
clash-verge status --json
clash-verge proxies --json
clash-verge traffic --json
```

### 守护模式

API 异常时自动监控并修复。需要外部脚本 `minimax_guardian.py`（本仓库不包含），放在 CLI 同目录、当前目录，或通过 `CLASH_VERGE_GUARDIAN` 指定路径：

```bash
# 只运行一次
clash-verge guardian --once

# 持续运行（默认间隔 120 秒）
clash-verge guardian

# 自定义间隔和延迟阈值
clash-verge guardian --interval 60 --max-latency 2000
```

## 配置

### 环境变量

| 名称 | 必填 | Secret | 默认值 | 说明 |
|---|---|---|---|---|
| `CLASH_VERGE_DIR` | 否 | 否 | 自动识别 | 配置目录（同 `--config-dir`） |
| `CLASH_API_URL` | 否 | 否 | `clash-verge.yaml` 中的 `external-controller`，否则 `127.0.0.1:9097` | 控制器地址（同 `--controller`） |
| `CLASH_API_SECRET` | 否 | 是 | `clash-verge.yaml` 中的 `secret` | 控制器密钥（同 `--secret`） |
| `CLASH_VERGE_GUARDIAN` | 否 | 否 | — | `guardian` 使用的 `minimax_guardian.py` 路径 |

### 配置目录

查找顺序：`--config-dir` > `CLASH_VERGE_DIR` > 第一个已存在的已知目录 > 平台默认目录。

```
macOS:   ~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/
Linux:   ~/.local/share/io.github.clash-verge-rev.clash-verge-rev/   ($XDG_DATA_HOME)
         ~/.config/io.github.clash-verge-rev.clash-verge-rev/        ($XDG_CONFIG_HOME)
         ~/.config/clash-verge/
Windows: %APPDATA%\io.github.clash-verge-rev.clash-verge-rev\
         %APPDATA%\clash-verge-rev\
         %LOCALAPPDATA%\io.github.clash-verge-rev.clash-verge-rev\
         %LOCALAPPDATA%\clash-verge-rev\
         C:\Program Files\Clash Verge\
         C:\Program Files (x86)\Clash Verge\
```

**Windows 首次运行：** 如果没有找到安装目录且当前是交互式终端，CLI 会提示手动输入配置路径。也可以传入 `--config-dir` 或设置 `CLASH_VERGE_DIR`。

主要文件：
- `profiles.yaml` - 订阅管理
- `verge.yaml` - Verge 设置
- `clash-verge.yaml` - Clash 内核配置（控制器地址与密钥）

备份保存在配置目录下的 `clash-verge-rev-backup/` 中。

## 示例

### 日常使用

```bash
# 早上做一次健康检查
clash-verge health

# 切换到最快的节点
clash-verge test GLOBAL --limit 10
clash-verge select GLOBAL "德国hy2-5-三网优化"

# 查看流量
clash-verge traffic

# 改配置前先备份
clash-verge backup
```

### 自动化

```bash
# 用 cron 定时做健康检查
*/5 * * * * /usr/local/bin/clash-verge health >> /var/log/clash.log 2>&1

# 失败时自动切换（通过守护模式）
clash-verge guardian --interval 300
```

## 开发

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest          # 运行测试（HTTP 已 mock，不会动到你真实的配置）
ruff check .    # 代码检查
```

另见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [CHANGELOG.md](CHANGELOG.md)。

项目结构：

```
src/clash_verge_cli/
  commands.py   # click commands + entry point
  api.py        # mihomo external-controller client
  store.py      # profiles.yaml / verge.yaml / backups / logs
  platforms.py  # macOS / Linux / Windows paths and helpers
  output.py     # JSON / text output helpers
clash_verge_cli.py, clash_verge_cli_windows.py   # legacy launchers
tests/
```

## 许可证

GPL-3.0，详见 [LICENSE](LICENSE)。
