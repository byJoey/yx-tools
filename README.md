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

```bash
# Linux / macOS
tar -xzf yx_linux_amd64.tar.gz
chmod +x yx_linux_amd64
./yx_linux_amd64
```

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

浏览器打开 `http://服务器IP:8080`。结果和配置存在 `./data`。

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

命令行模式适合塞进 cron：

```bash
# 每 6 小时测一次并上报
0 */6 * * * cd /opt/yx && ./yx test -n 10 -sl 2 -upload api -domain your.workers.dev -uuid 你的UUID -clear
```

配置会存在二进制同目录的 `yx-config.json`，填过一次之后命令里可以省掉 `-domain` `-uuid`。

## 文件

跑完会在当前目录生成：

- `result.csv` — 完整测速结果
- `ips_ports.txt` — 反代列表，`IP:端口` 一行一条
- `yx-config.json` — 配置，含 Token，注意别泄露
- `Cloudflare.txt` / `Cloudflare_ipv6.txt` — 缓存的官方 IP 段

## 相关

- [cfnew](https://github.com/byJoey/cfnew) — 配套的 Worker 面板
- [博客](https://joeyblog.net) ｜ [YouTube](https://youtube.com/@joeyblog) ｜ [TG 群](https://t.me/+ft-zI76oovgwNmRh)

## 致谢

测速内核来自 [XIU2/CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest)，MIT。

## 许可

MIT
