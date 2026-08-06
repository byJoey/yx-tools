# yx-tools

Cloudflare 优选 IP 测速工具。单个二进制，命令行和网页界面都能用。

[![Go](https://img.shields.io/badge/Go-1.22+-00ADD8.svg)](https://go.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)](https://github.com/byJoey/yx-tools/releases)

测速内核基于 [XIU2/CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest)，
补了反代场景需要的 `IP:端口` 支持。

## 能做什么

- 测 Cloudflare 各数据中心的延迟和下载速度，支持 IPv4 / IPv6
- 按机场码筛地区，全球 97 个数据中心
- 反代模式：输入 `IP:端口`，结果保留端口信息
- 一键上报到 [cfnew](https://github.com/byJoey/cfnew) 面板，或推到 GitHub 仓库
- 网页界面实时看进度，也能纯命令行跑，适合塞进定时任务

## 装

去 [Releases](https://github.com/byJoey/yx-tools/releases) 下对应平台的包，解压就能跑。不用装 Python，不用装依赖。

不知道下哪个？照这张表挑：

| 你的设备 | 下这个 |
| :--- | :--- |
| Windows 电脑（绝大多数） | `yx_windows_amd64.zip` |
| Windows，骁龙/ARM 本 | `yx_windows_arm64.zip` |
| Mac，M1 及以后（2020 年后买的） | `yx_darwin_arm64.tar.gz` |
| Mac，Intel 芯片（2020 年前） | `yx_darwin_amd64.tar.gz` |
| Linux 服务器 / VPS（绝大多数） | `yx_linux_amd64.tar.gz` |
| Linux ARM，甲骨文免费机、树莓派 | `yx_linux_arm64.tar.gz` |
| 老的 32 位 Linux | `yx_linux_386.tar.gz` |
| FreeBSD | `yx_freebsd_amd64.tar.gz` |

不确定 Mac 是哪种芯片：点左上角苹果图标 →「关于本机」，写着 M1/M2/M3/M4 就选 arm64。
不确定 Linux 是哪种：命令行敲 `uname -m`，`x86_64` 选 amd64，`aarch64` 选 arm64。

```bash
# Linux / macOS：解压后要先加执行权限
tar -xzf yx_linux_amd64.tar.gz
chmod +x yx_linux_amd64
./yx_linux_amd64
```

解压出来的文件名带平台后缀（如 `yx_linux_amd64`），不是 `yx`。嫌长可以自己改名：
`mv yx_linux_amd64 yx`。

Windows 解压后双击 `yx_windows_amd64.exe`，会自动开浏览器。
macOS 首次运行若提示「无法验证开发者」，去「系统设置 → 隐私与安全性」点「仍要打开」。

自己编译也行：

```bash
git clone https://github.com/byJoey/yx-tools.git
cd yx-tools
go build -o yx ./cmd/yx
```

## 用

### 网页界面

```bash
./yx
```

默认监听 `127.0.0.1:8080` 并自动开浏览器。放服务器上跑就换个监听地址：

```bash
./yx web -listen 0.0.0.0:8080
```

左边配参数，右边看结果。地区搜索框输中文或机场码都行，留空就是不限地区。

### 命令行

```bash
# 测 10 个，速度下限 1MB/s
./yx test -n 10 -sl 1

# 只测香港和新加坡
./yx test -colo HKG,SIN -n 20

# 测完直接上报到 cfnew
./yx test -n 10 -upload api -domain your.workers.dev -uuid 你的UUID -clear

# 从已有结果生成反代列表
./yx proxy -limit 20
```

`-h` 看完整参数。

### Docker

```bash
docker compose up -d
```

浏览器打开 `http://服务器IP:8080`。结果和配置存在 `./data`，容器会自己把这个目录的
权限修好，不用手动 chown。

不想用 compose 就直接跑：

```bash
docker run -d --name yx-tools -p 8080:8080 -v $PWD/data:/data ghcr.io/byjoey/yx-tools:latest
```

换存放位置改环境变量 `YX_DATA_DIR` 即可。
容器里没有可用的 cron，界面上的定时任务会自动隐藏 —— 定时跑请用宿主机的
crontab 调 `docker exec`。

## 参数

测速：

| 参数 | 说明 | 默认 |
| :--- | :--- | :--- |
| `-colo` | 机场码，逗号分隔，如 `HKG,SIN`；留空不限 | 空 |
| `-ipv6` | 测 IPv6 段 | 否 |
| `-n` | 测速数量 | 10 |
| `-sl` | 下载速度下限 MB/s | 1 |
| `-tl` | 平均延迟上限 ms | 1000 |
| `-t` | 延迟测速线程数，路由器上别开太高 | 200 |
| `-port` | 测速端口 | 443 |
| `-url` | 测速地址 | 内置 |
| `-f` | 自定义 IP 文件，每行一条，支持 `IP:端口` | 自动下载 |
| `-nodl` | 只测延迟，跳过下载测速 | 否 |
| `-dt` | 单个 IP 的下载测速时长上限，秒 | 10 |
| `-mt` | 整轮测速的时长上限，秒；0 不限，到点拿已测出的结果收工 | 0 |
| `-o` | 结果文件 | result.csv |

上报（跟在 `test` 后面，或单独用 `upload`）：

| 参数 | 说明 |
| :--- | :--- |
| `-upload` | `api` 上报 cfnew，`github` 推到仓库 |
| `-domain` `-uuid` | cfnew 的 Worker 域名和 UUID |
| `-repo` `-token` | GitHub 仓库 `owner/repo` 和 Token |
| `-path` | 仓库内文件路径，默认 `cloudflare_ips.txt` |
| `-limit` | 上报数量，默认 10 |
| `-clear` | 上报前清空已有 IP，建议带上，否则会越堆越多 |

界面：

| 参数 | 说明 | 默认 |
| :--- | :--- | :--- |
| `-listen` | 监听地址 | 127.0.0.1:8080 |
| `-no-open` | 不自动开浏览器 | 否 |

## 定时任务

Linux / macOS 直接用内置命令挂 cron，不用自己编辑 crontab：

```bash
# 每 6 小时测一次并上报
./yx cron -add "test -n 10 -sl 2 -upload api -clear" -at "0 */6 * * *"

# 看已登记的任务
./yx cron

# 清掉（只删本程序加的，不动你自己的任务）
./yx cron -remove
```

配置存在 `yx-config.json`（位置见下面「文件」一节），`-domain` `-uuid` 填过一次之后
命令里就能省掉。任务输出写到同目录的 `yx-cron.log`，添加时会打印完整路径。

Windows 用「任务计划程序」调用 `yx.exe test ...` 即可。

## 文件

跑完会生成这几个文件，默认落在当前目录；当前目录写不了（比如容器里、
装在只读位置）就自动退到程序目录、家目录 `~/.yx-tools`，最后是临时目录。
启动时会打印实际用的是哪个。想固定位置就设环境变量 `YX_DATA_DIR`。

- `result.csv` — 完整测速结果
- `ips_ports.txt` — 反代列表，`IP:端口` 一行一条
- `yx-config.json` — 配置，含 Token，注意别泄露
- `Cloudflare.txt` / `Cloudflare_ipv6.txt` — 缓存的官方 IP 段
- `yx-cron.log` — 定时任务的输出（设了定时任务才有）

## 相关

- [cfnew](https://github.com/byJoey/cfnew) — 配套的 Worker 面板
- [博客](https://joeyblog.net) ｜ [YouTube](https://youtube.com/@joeyblog) ｜ [TG 群](https://t.me/+ft-zI76oovgwNmRh)

## 致谢

测速内核来自 [XIU2/CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest)，MIT。

## 许可

MIT
