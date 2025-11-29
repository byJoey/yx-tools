# Cloudflare SpeedTest 跨平台自动化工具

[![Version](https://img.shields.io/badge/Version-2.2.3-blue.svg)](https://github.com/byJoey/yx-tools)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个功能强大的跨平台Cloudflare测速工具，支持全球97个数据中心机场码映射，提供常规测速和优选反代功能。

**当前版本：v2.2.3**

## 主要功能

### 常规测速
- **全球97个数据中心** - 支持完整的Cloudflare机场码映射
- **智能测速** - 自动下载最新IP列表，支持自定义参数
- **结果分析** - 生成详细的CSV格式测速报告
- **IPv4/IPv6支持** - 支持IPv4和IPv6地址测速

### 小白快速测试
- **一键测速** - 简单输入3个参数即可开始测试
- **全自动模式** - 无需选择地区，自动测试所有IP
- **适合新手** - 专为新手设计，操作简单

### 优选反代
- **CSV文件处理** - 从测速结果中提取最优IP
- **反代列表生成** - 自动生成`ips_ports.txt`反代配置
- **多格式支持** - 兼容各种CSV文件格式

### 结果上报
- **Cloudflare Workers API** - 支持上报到Cloudflare Workers API
- **GitHub仓库上传** - 支持上传到GitHub公开仓库
- **批量上传** - 支持批量上传优选IP结果
- **自动格式化** - 自动格式化IP列表（包含注释）

### 命令行支持
- **命令行模式** - 支持命令行参数运行
- **自动化脚本** - 适合集成到自动化流程
- **参数配置** - 支持所有功能的命令行参数配置

### 定时任务设置（Linux/OpenWrt）
- **自动检测环境** - 自动检测Linux和OpenWrt系统
- **Cron任务设置** - 支持设置Cron定时任务
- **智能检测** - 自动检测是否已有类似任务
- **灵活管理** - 支持清理现有任务或继续添加
- **使用绝对路径** - 自动使用绝对路径，确保定时任务正确执行

### Docker容器化支持
- **Docker镜像** - 提供官方Docker镜像，开箱即用
- **Docker Compose** - 支持Docker Compose一键部署
- **数据持久化** - 支持挂载数据目录，保存测速结果
- **多架构支持** - 支持amd64和arm64架构
- **环境隔离** - 容器化运行，环境干净整洁

### 图形化界面
  <img width="2104" height="1798" alt="image" src="https://github.com/user-attachments/assets/f6438b5c-3108-434b-95b8-1a60166332aa" />
  <img width="2104" height="1798" alt="image" src="https://github.com/user-attachments/assets/47eaab5d-74c1-4e64-9d76-b63f9aafca8a" />
- **现代化图形界面** - 操作更加直观友好
- **主题切换** - 可根据个人喜好选择主题
- **多架构支持** - 支持amd64和arm64架构

## 支持平台

| 平台 | 架构 | 状态 |
|------|------|------|
| **Windows** | x64 | 完全支持 |
| **Windows** | ARM64 | 完全支持 |
| **macOS** | Intel | 完全支持 |
| **macOS** | Apple Silicon | 完全支持 |
| **Linux** | x64 | 完全支持 |
| **Linux** | ARM64 | 完全支持 |

## 快速开始

### 方法一：交互式模式（推荐新手）

```bash
# 克隆项目
git clone https://github.com/byJoey/yx-tools.git
cd yx-tools

# 安装依赖
pip install -r requirements.txt

# 运行程序（交互式模式）
python3 cloudflare_speedtest.py
```

### 方法二：命令行模式（推荐自动化）

```bash
# 克隆项目
git clone https://github.com/byJoey/yx-tools.git
cd yx-tools

# 安装依赖
pip install -r requirements.txt

# 运行程序（命令行模式）
python3 cloudflare_speedtest.py --mode beginner --count 10 --speed 1 --delay 1000

# 运行程序（图形模式）
python3 cloudflare_speedtest_gui.py

# 查看帮助
python3 cloudflare_speedtest.py --help
```

### 方法三：使用预编译版本

从 [Releases](https://github.com/byJoey/yx-tools/releases) 页面下载对应平台的可执行文件：

- `CloudflareSpeedTest-windows-amd64.exe` - Windows x64
- `CloudflareSpeedTest-macos-amd64` - macOS Intel
- `CloudflareSpeedTest-macos-arm64` - macOS Apple Silicon
- `CloudflareSpeedTest-linux-amd64` - Linux x64
- `CloudflareSpeedTest-linux-arm64` - Linux ARM64
- `yx-tools-gui-xxx.xxx` - 各平台的图形化版本


### 方法四：使用Docker（推荐容器化部署）

#### 直接拉取预构建镜像（最简单）

```bash
# 拉取最新镜像
docker pull ghcr.io/byjoey/yx-tools:latest

# 运行容器（交互模式 - 前台运行）
# 如果设置了定时任务，容器会自动保持运行
docker run -it --name cloudflare-speedtest \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  ghcr.io/byjoey/yx-tools:latest

# 运行容器（交互模式 - 后台运行，退出终端不中断）
# 推荐方式：先后台运行，再进入容器设置
docker run -d --name cloudflare-speedtest \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  ghcr.io/byjoey/yx-tools:latest

# 然后进入容器设置定时任务
docker exec -it cloudflare-speedtest python3 /app/cloudflare_speedtest.py

# 运行容器（命令行模式）
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  ghcr.io/byjoey/yx-tools:latest \
  --mode beginner --count 10 --speed 1 --delay 1000

# 拉取特定版本
docker pull ghcr.io/byjoey/yx-tools:v2.2.3

# 查看所有可用标签
# 访问: https://github.com/byJoey/yx-tools/pkgs/container/yx-tools
```

#### 使用Docker Compose（推荐）

```bash
# 克隆项目
git clone https://github.com/byJoey/yx-tools.git
cd yx-tools

# 创建数据目录
mkdir -p data config

# 使用Docker Compose运行（交互模式）
docker-compose run --rm cloudflare-speedtest

# 使用Docker Compose运行（命令行模式）
docker-compose run --rm cloudflare-speedtest --mode beginner --count 10 --speed 1 --delay 1000
```

#### 本地构建镜像

```bash
# 克隆项目
git clone https://github.com/byJoey/yx-tools.git
cd yx-tools

# 构建镜像
docker build -t cloudflare-speedtest:latest .

# 运行容器（交互模式）
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  cloudflare-speedtest:latest

# 运行容器（命令行模式）
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  cloudflare-speedtest:latest \
  --mode beginner --count 10 --speed 1 --delay 1000

# 后台运行并设置定时任务
docker run -d --name cloudflare-speedtest \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  cloudflare-speedtest:latest \
  --mode beginner --count 10 --speed 1 --delay 1000
```

#### Docker内定时任务设置

容器内已集成cron服务，支持在容器内设置定时任务，**定时任务会自动持久化到 `/app/config/crontab` 文件，容器重启后会自动恢复**。

**方法一：交互模式设置（推荐）**

**方式A：前台运行（使用 -it）**

```bash
# 1. 前台运行容器（交互模式）
docker run -it --name cloudflare-speedtest \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  ghcr.io/byjoey/yx-tools:latest

# 2. 在交互模式中选择设置定时任务
# 3. 设置完成后，定时任务会自动保存到 ./config/crontab
# 4. 容器会保持运行，定时任务会按计划执行
# 5. 使用 Ctrl+P, Ctrl+Q 分离容器（不停止容器）
# 6. 或者直接关闭终端，容器会继续运行（因为设置了 --restart unless-stopped）
# 7. 即使容器重启，定时任务也会自动恢复
```

**方式B：后台运行（使用 -d，推荐）**

```bash
# 1. 后台运行容器
docker run -d --name cloudflare-speedtest \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  ghcr.io/byjoey/yx-tools:latest

# 2. 进入容器设置定时任务（交互模式）
docker exec -it cloudflare-speedtest python3 /app/cloudflare_speedtest.py

# 3. 在交互模式中选择设置定时任务
# 4. 设置完成后，定时任务会自动保存到 ./config/crontab
# 5. 容器会保持运行，定时任务会按计划执行
# 6. 退出终端不影响容器运行
# 7. 即使容器重启，定时任务也会自动恢复
```

**方法二：使用环境变量自动设置**

在 `docker-compose.yml` 中配置：

```yaml
environment:
  - CRON_SCHEDULE=0 2 * * *  # 每天凌晨2点
  - CRON_COMMAND=python3 /app/cloudflare_speedtest.py --mode beginner --count 10 --speed 1 --delay 1000
```

或使用Docker命令：

```bash
docker run -d --name cloudflare-speedtest \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  -e CRON_SCHEDULE="0 2 * * *" \
  -e CRON_COMMAND="python3 /app/cloudflare_speedtest.py --mode beginner --count 10 --speed 1 --delay 1000" \
  --restart unless-stopped \
  ghcr.io/byjoey/yx-tools:latest
```

**方法三：手动编辑crontab**

```bash
# 进入容器
docker exec -it cloudflare-speedtest bash

# 编辑crontab
crontab -e

# 查看定时任务
crontab -l

# 退出容器后，定时任务会自动保存
```

**Cron时间格式示例：**
- `0 2 * * *` - 每天凌晨2点
- `0 */6 * * *` - 每6小时
- `*/30 * * * *` - 每30分钟
- `0 3 * * 1` - 每周一凌晨3点

**定时任务持久化说明：**
- ✅ 定时任务自动保存到 `./config/crontab` 文件
- ✅ 容器重启后自动恢复定时任务
- ✅ 每5分钟自动保存一次，确保不丢失
- ✅ 退出终端不影响容器运行（使用 `-d` 后台运行）

#### Docker使用说明

- **预构建镜像**：可直接从 [GitHub Container Registry](https://github.com/byJoey/yx-tools/pkgs/container/yx-tools) 拉取，无需本地构建
- **镜像地址**：`ghcr.io/byjoey/yx-tools:latest`
- **定时任务**：容器内已集成cron服务，支持在容器内设置定时任务（容器需24小时运行）
- **定时任务持久化**：定时任务自动保存到 `./config/crontab`，容器重启后自动恢复
- **后台运行**：使用 `-d` 参数后台运行，退出终端不影响容器运行
- **数据持久化**：结果文件会保存在 `./data` 目录中
- **配置文件**：配置文件会保存在 `./config` 目录中（包括crontab）
- **网络访问**：容器需要网络访问来下载IP列表和上传结果
- **时区设置**：默认使用 `Asia/Shanghai` 时区
- **架构支持**：镜像包含 amd64 和 arm64 版本的 CloudflareST 可执行文件，支持多架构自动选择

#### 容器管理命令

```bash
# 查看容器状态
docker ps -a | grep cloudflare-speedtest

# 查看容器日志
docker logs cloudflare-speedtest

# 查看定时任务
docker exec -it cloudflare-speedtest crontab -l

# 编辑定时任务
docker exec -it cloudflare-speedtest crontab -e

# 停止容器
docker stop cloudflare-speedtest

# 启动容器（定时任务会自动恢复）
docker start cloudflare-speedtest

# 重启容器（定时任务会自动恢复）
docker restart cloudflare-speedtest

# 删除容器（不会删除数据，数据在挂载的目录中）
docker rm cloudflare-speedtest
```

#### 独立网络配置（软路由环境）

在软路由环境中使用Docker时，建议为容器分配独立IP，并在软路由中将该IP设置为不走代理。

**方法一：使用 Docker Compose 配置独立网络**

```yaml
# docker-compose.yml
version: '3.8'

services:
  cloudflare-speedtest:
    build:
      context: .
      dockerfile: Dockerfile
    image: cloudflare-speedtest:latest
    container_name: cloudflare-speedtest
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    networks:
      isolated_network:
        ipv4_address: 172.20.0.10  # 指定独立IP
    environment:
      - TZ=Asia/Shanghai
      - PYTHONUNBUFFERED=1
    restart: unless-stopped

networks:
  isolated_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
```

**方法二：使用 Docker 命令配置独立网络**

```bash
# 1. 创建独立网络
docker network create \
  --driver bridge \
  --subnet=172.20.0.0/16 \
  --gateway=172.20.0.1 \
  isolated_network

# 2. 运行容器并指定独立IP
docker run -d --name cloudflare-speedtest \
  --network isolated_network \
  --ip 172.20.0.10 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  ghcr.io/byjoey/yx-tools:latest
```

**方法三：使用 Macvlan 网络（推荐软路由）**

Macvlan 网络允许容器直接使用物理网络接口，获得独立的 MAC 地址和 IP：

```bash
# 1. 创建 Macvlan 网络（需要根据实际网络接口调整）
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  macvlan_network

# 2. 运行容器并指定独立IP
docker run -d --name cloudflare-speedtest \
  --network macvlan_network \
  --ip 192.168.1.100 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  ghcr.io/byjoey/yx-tools:latest
```

**软路由代理设置**

配置独立IP后，需要在软路由中将该IP设置为不走代理：

1. **OpenWrt/Lede**：
   - 进入"网络" → "负载均衡" → "规则"
   - 添加规则：源地址为容器IP（如 `192.168.1.100`），动作选择"直连"或"不走代理"

2. **PassWall/Clash**：
   - 进入"访问控制" → "局域网设备"
   - 添加设备规则：IP地址为容器IP，策略选择"直连"或"DIRECT"

3. **V2Ray/Xray**：
   - 在路由规则中添加：
   ```json
   {
     "type": "field",
     "ip": ["192.168.1.100/32"],
     "outboundTag": "direct"
   }
   ```

**注意事项**：
- 确保容器IP与软路由在同一网段
- 确保容器IP未被其他设备占用
- 配置后测试容器网络连接是否正常
- Macvlan 网络需要根据实际网络接口名称调整 `parent` 参数（如 `eth0`、`br-lan` 等）

## 使用指南

### 方法一：交互式模式（推荐新手）

#### macOS/Linux 权限设置
```bash
chmod 755 可执行文件拽到终端回车
可执行文件拽到终端回车
如果还是不行 请执行sudo spctl --master-disable
依然不行 xattr -d com.apple.quarantine 可执行文件拽到终端回车
```

#### 运行程序
```bash
python3 cloudflare_speedtest.py
```

选择功能：
```
功能选择:
  1. 小白快速测试 - 简单输入，适合新手
  2. 常规测速 - 测试指定机场码的IP速度
  3. 优选反代 - 从CSV文件生成反代IP列表

请选择功能 [默认: 1]: 1
```

### 方法二：命令行模式（推荐自动化）

命令行模式适合自动化脚本、定时任务、CI/CD等场景，支持所有功能通过参数配置。

#### 基本用法

**小白快速测试模式**
```bash
# 使用默认参数（10个IP，速度1MB/s，延迟1000ms）
python3 cloudflare_speedtest.py --mode beginner

# 指定测试参数
python3 cloudflare_speedtest.py --mode beginner --count 20 --speed 2 --delay 500

# 使用IPv6测试
python3 cloudflare_speedtest.py --mode beginner --ipv6

# 高质量测试（50个IP，速度5MB/s，延迟200ms）
python3 cloudflare_speedtest.py --mode beginner --count 50 --speed 5 --delay 200

# 快速测试（5个IP，速度0.5MB/s，延迟2000ms）
python3 cloudflare_speedtest.py --mode beginner --count 5 --speed 0.5 --delay 2000
```

**常规测速模式**
```bash
# 测试指定地区（香港）
python3 cloudflare_speedtest.py --mode normal --region HKG --count 10

# 测试指定地区（新加坡），指定速度和延迟
python3 cloudflare_speedtest.py --mode normal --region SIN --count 20 --speed 5 --delay 300

# 测试指定地区（东京），使用IPv6
python3 cloudflare_speedtest.py --mode normal --region NRT --count 15 --ipv6

# 测试指定地区（洛杉矶），高质量测试
python3 cloudflare_speedtest.py --mode normal --region LAX --count 50 --speed 10 --delay 200
```

**优选反代模式**
```bash
# 从默认CSV文件生成反代列表
python3 cloudflare_speedtest.py --mode proxy

# 从指定CSV文件生成反代列表
python3 cloudflare_speedtest.py --mode proxy --csv result.csv

# 从自定义路径的CSV文件生成反代列表
python3 cloudflare_speedtest.py --mode proxy --csv /path/to/result.csv
```

#### 完整参数说明

| 参数 | 说明 | 默认值 | 必需 | 示例 |
|------|------|--------|------|------|
| `--mode` | 运行模式 | - | ✅ | `beginner`/`normal`/`proxy` |
| `--ipv6` | 使用IPv6（默认IPv4） | IPv4 | ❌ | `--ipv6` |
| `--count` | 测试IP数量 | 10 | ❌ | `--count 20` |
| `--speed` | 下载速度下限 (MB/s) | 1.0 | ❌ | `--speed 2` |
| `--delay` | 延迟上限 (ms) | 1000 | ❌ | `--delay 500` |
| `--region` | 地区码（常规测速模式需要） | - | ⚠️ | `--region HKG` |
| `--csv` | CSV文件路径（优选反代模式） | result.csv | ❌ | `--csv result.csv` |
| `--upload` | 上传方式 | none | ❌ | `api`/`github`/`none` |
| `--worker-domain` | Worker域名（API上传需要） | - | ⚠️ | `--worker-domain example.com` |
| `--uuid` | UUID或路径（API上传需要） | - | ⚠️ | `--uuid abc123` |
| `--repo` | GitHub仓库路径（GitHub上传需要） | - | ⚠️ | `--repo owner/repo` |
| `--token` | GitHub Token（GitHub上传需要） | - | ⚠️ | `--token ghp_xxx` |
| `--file-path` | GitHub文件路径 | cloudflare_ips.txt | ❌ | `--file-path ips.txt` |
| `--upload-count` | 上传IP数量 | 10 | ❌ | `--upload-count 20` |
| `--clear` | 上传前清空现有IP（避免IP累积，推荐使用） | false | ❌ | `--clear` |

**说明：**
- ✅ 必需参数：必须提供
- ⚠️ 条件必需：在特定模式下需要
- ❌ 可选参数：可以不提供，使用默认值

#### 使用场景示例

**场景1：定时自动测速并上报到API**
```bash
# 每天凌晨2点自动测速并上报（清空现有IP，推荐）
python3 cloudflare_speedtest.py --mode beginner \
  --count 20 --speed 2 --delay 500 \
  --upload api \
  --worker-domain example.com --uuid abc123 \
  --upload-count 20 --clear

# 每天凌晨2点自动测速并上报（IP会累积）
python3 cloudflare_speedtest.py --mode beginner \
  --count 20 --speed 2 --delay 500 \
  --upload api \
  --worker-domain example.com --uuid abc123 \
  --upload-count 20
```

**场景2：测试多个地区并上传到GitHub**
```bash
# 测试香港地区
python3 cloudflare_speedtest.py --mode normal \
  --region HKG --count 20 --speed 5 --delay 300 \
  --upload github \
  --repo username/cloudflare-ips --token ghp_xxx \
  --file-path hkg_ips.txt

# 测试新加坡地区
python3 cloudflare_speedtest.py --mode normal \
  --region SIN --count 20 --speed 5 --delay 300 \
  --upload github \
  --repo username/cloudflare-ips --token ghp_xxx \
  --file-path sin_ips.txt
```

**场景3：快速测试IPv6**
```bash
# 快速测试IPv6地址
python3 cloudflare_speedtest.py --mode beginner \
  --ipv6 --count 10 --speed 1 --delay 1000
```

**场景4：高质量测试（适合对速度要求高的场景）**
```bash
# 测试50个IP，速度要求5MB/s以上，延迟200ms以内
python3 cloudflare_speedtest.py --mode beginner \
  --count 50 --speed 5 --delay 200
```

**场景5：批量生成反代列表**
```bash
# 从多个CSV文件生成反代列表
python3 cloudflare_speedtest.py --mode proxy --csv result1.csv
python3 cloudflare_speedtest.py --mode proxy --csv result2.csv
python3 cloudflare_speedtest.py --mode proxy --csv result3.csv
```

#### 结果上报详细说明

**上报到 Cloudflare Workers API**

完整示例（清空现有IP，推荐）：
```bash
python3 cloudflare_speedtest.py --mode beginner \
  --count 20 --speed 2 --delay 500 \
  --upload api \
  --worker-domain example.com \
  --uuid abc123 \
  --upload-count 20 \
  --clear
```

完整示例（IP会累积）：
```bash
python3 cloudflare_speedtest.py --mode beginner \
  --count 20 --speed 2 --delay 500 \
  --upload api \
  --worker-domain example.com \
  --uuid abc123 \
  --upload-count 20
```

参数说明：
- `--upload api`：指定上传方式为API
- `--worker-domain`：您的Worker域名（例如：example.com）
- `--uuid`：UUID或路径（例如：abc123 或 351c9981-04b6-4103-aa4b-864aa9c91469）
- `--upload-count`：要上传的IP数量（默认10个）
- `--clear`：上传前清空现有IP，避免IP累积（推荐使用）

**上报到 GitHub 仓库**

完整示例：
```bash
python3 cloudflare_speedtest.py --mode beginner \
  --count 20 --speed 2 --delay 500 \
  --upload github \
  --repo username/repo-name \
  --token ghp_xxxxxxxxxxxxxxxxxxxx \
  --file-path cloudflare_ips.txt \
  --upload-count 20
```

参数说明：
- `--upload github`：指定上传方式为GitHub
- `--repo`：GitHub仓库路径，格式：`owner/repo`（例如：`username/repo-name`）
- `--token`：GitHub Personal Access Token（需要 `repo` 权限）
- `--file-path`：上传的文件路径（默认：`cloudflare_ips.txt`）
- `--upload-count`：要上传的IP数量（默认10个）

**获取GitHub Token：**
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选 `repo` 权限
4. 生成并复制Token

#### 常用参数组合

**快速测试组合**
```bash
python3 cloudflare_speedtest.py --mode beginner --count 5 --speed 0.5 --delay 2000
```

**标准测试组合**
```bash
python3 cloudflare_speedtest.py --mode beginner --count 20 --speed 2 --delay 500
```

**高质量测试组合**
```bash
python3 cloudflare_speedtest.py --mode beginner --count 50 --speed 5 --delay 200
```

**地区测试组合**
```bash
# 香港
python3 cloudflare_speedtest.py --mode normal --region HKG --count 20 --speed 5 --delay 300

# 新加坡
python3 cloudflare_speedtest.py --mode normal --region SIN --count 20 --speed 5 --delay 300

# 东京
python3 cloudflare_speedtest.py --mode normal --region NRT --count 20 --speed 5 --delay 300
```

#### 查看帮助信息

```bash
# 查看完整帮助信息
python3 cloudflare_speedtest.py --help

# 查看帮助信息（包含使用示例）
python3 cloudflare_speedtest.py -h
```

#### 错误处理

**常见错误及解决方法：**

1. **缺少必需参数**
```bash
# 错误：缺少 --mode 参数
python3 cloudflare_speedtest.py --count 20
# 解决：添加 --mode 参数
python3 cloudflare_speedtest.py --mode beginner --count 20
```

2. **常规测速模式缺少地区码**
```bash
# 错误：常规测速模式需要 --region 参数
python3 cloudflare_speedtest.py --mode normal --count 20
# 解决：添加 --region 参数
python3 cloudflare_speedtest.py --mode normal --region HKG --count 20
```

3. **上传模式缺少必需参数**
```bash
# 错误：API上传缺少 --worker-domain 或 --uuid
python3 cloudflare_speedtest.py --mode beginner --upload api
# 解决：添加必需参数
python3 cloudflare_speedtest.py --mode beginner --upload api \
  --worker-domain example.com --uuid abc123
```

#### 自动化脚本示例

**Linux/Mac 定时任务（crontab）**
```bash
# 编辑crontab
crontab -e

# 每天凌晨2点自动测速并上报到API（清空现有IP，推荐）
0 2 * * * cd /path/to/project && python3 cloudflare_speedtest.py --mode beginner --count 20 --speed 2 --delay 500 --upload api --worker-domain example.com --uuid abc123 --clear >> /var/log/cloudflare_speedtest.log 2>&1
```

**Windows 计划任务**
```batch
@echo off
cd /d C:\path\to\project
python cloudflare_speedtest.py --mode beginner --count 20 --speed 2 --delay 500 --upload api --worker-domain example.com --uuid abc123 --clear
```

**Shell脚本示例**
```bash
#!/bin/bash
# 自动测速脚本

# 测试香港地区
python3 cloudflare_speedtest.py --mode normal \
  --region HKG --count 20 --speed 5 --delay 300 \
  --upload github \
  --repo username/cloudflare-ips --token ghp_xxx \
  --file-path hkg_ips.txt

# 测试新加坡地区
python3 cloudflare_speedtest.py --mode normal \
  --region SIN --count 20 --speed 5 --delay 300 \
  --upload github \
  --repo username/cloudflare-ips --token ghp_xxx \
  --file-path sin_ips.txt
```

### 交互式模式详细说明

#### 1. 小白快速测试模式

专为新手设计，只需要输入3个简单的数字：
```
📊 第一步：设置测试IP数量
请输入要测试的IP数量 [默认: 10]: 20

⏱️  第二步：设置延迟上限
请输入延迟上限(ms) [默认: 1000]: 500

🚀 第三步：设置下载速度下限
请输入下载速度下限(MB/s) [默认: 1]: 2
```

#### 2. 常规测速模式

**机场码选择**
- 输入机场码：`HKG` (香港)
- 输入城市名：`香港` 或 `Hong Kong`
- 查看完整列表：输入 `LIST`

**自定义参数**
```
自定义配置:
请输入要测试的IP数量 [默认: 10]: 20
请输入下载速度下限 (MB/s) [默认: 1]: 5
请输入延迟上限 (ms) [默认: 1000]: 500
```

#### 3. 优选反代模式

```
优选反代模式
==================================================
此功能将从CSV文件中提取IP和端口信息，生成反代IP列表
CSV文件格式要求：
  - 包含 'IP 地址' 和 '端口' 列
  - 或包含 'ip' 和 'port' 列
  - 支持逗号分隔的CSV格式
==================================================

请输入CSV文件路径 [默认: result.csv]: 
```

#### 4. 结果上报功能

**Cloudflare Workers API 上报**
- 需要提供 Worker 域名和 UUID或者路径
- 支持批量上传
- 自动格式化IP列表（包含注释）

**GitHub 仓库上传**
- 需要提供 GitHub Personal Access Token
- 支持上传到公开仓库
- 文件格式：`IP:端口#地区名-速度MB/s`
- 使用换行符分隔，不使用逗号

## 输出文件

### 测速结果 (result.csv)
```csv
IP 地址,端口,延迟,下载速度 (MB/s),上传速度 (MB/s)
1.2.3.4,443,10.5,150.2,120.8
5.6.7.8,80,15.2,200.1,180.5
```

### 反代列表 (ips_ports.txt)
```
1.2.3.4:443
5.6.7.8:80
9.10.11.12:8080
```

### GitHub上传格式 (cloudflare_ips.txt)
```
1.2.3.4:443#香港-5.23MB/s
5.6.7.8:443#新加坡-8.45MB/s
9.10.11.12:443#东京-6.78MB/s
```
- 使用换行符分隔，每行一个IP
- 包含注释信息（#后面的内容）
- 格式：`IP:端口#地区名-速度MB/s`（井号前后无空格）

## 支持的机场码

### 亚太地区
- **HKG** - 香港
- **NRT** - 东京
- **SIN** - 新加坡
- **SYD** - 悉尼
- **ICN** - 首尔
- **TPE** - 台北

### 欧洲地区
- **LHR** - 伦敦
- **FRA** - 法兰克福
- **AMS** - 阿姆斯特丹
- **CDG** - 巴黎
- **MAD** - 马德里
- **FCO** - 罗马

### 美洲地区
- **LAX** - 洛杉矶
- **SFO** - 旧金山
- **DFW** - 达拉斯
- **ORD** - 芝加哥
- **JFK** - 纽约
- **YYZ** - 多伦多

> 完整列表包含97个全球数据中心，支持所有主要城市和地区。

## 高级配置

### 环境变量
```bash
# 设置默认机场码
export DEFAULT_AIRPORT=HKG

# 设置默认IP数量
export DEFAULT_IP_COUNT=20

# 设置默认速度阈值
export DEFAULT_SPEED_LIMIT=50
```

### 配置文件
创建 `config.json` 文件：
```json
{
  "default_airport": "HKG",
  "default_ip_count": 20,
  "default_speed_limit": 50,
  "default_delay_limit": 200,
  "default_time_limit": 10
}
```

## 开发说明

### 项目结构
```
cloudflare-speedtest/
├── cloudflare_speedtest.py    # 主程序
├── requirements.txt            # 依赖文件
├── .github/
│   └── workflows/
│       └── build-all-platforms.yml  # 自动构建
├── README.md                   # 说明文档
└── LICENSE                     # 许可证
```



## 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 报告问题
如果您发现任何问题，请：
1. 检查 [Issues](https://github.com/your-username/cloudflare-speedtest/issues) 是否已存在
2. 创建新的 Issue，详细描述问题
3. 提供系统信息和错误日志

## 更新日志

### v2.2.3 (最新)
- ✨ 新增Docker支持
  - 提供官方Docker镜像，开箱即用
  - 支持Docker Compose一键部署
  - 支持多架构（amd64/arm64）
  - 数据持久化支持
  - 环境隔离，运行更稳定
- ✨ 新增定时任务设置功能（Linux/OpenWrt）
  - 自动检测Linux和OpenWrt环境
  - 支持设置Cron定时任务
  - 智能检测现有任务，支持清理或继续添加
  - 自动使用绝对路径，确保定时任务正确执行
  - 支持交互模式和命令行模式
- 🔧 改进命令生成功能
  - 自动使用实际应用名（支持改名的.py文件和封装后的可执行文件）
  - 使用绝对路径生成命令，确保定时任务正确执行
- 🔧 改进GitHub上传功能
  - 添加配置保存功能，避免每次都要输入Token和仓库信息
  - 改进网络错误处理，自动使用curl备用方案
- 🐛 修复命令行模式下GitHub上传的网络错误问题

### v2.2.2
- ✨ 新增命令行参数支持
- ✨ 新增小白快速测试模式
- ✨ 新增结果上报功能（Cloudflare Workers API 和 GitHub）
- ✨ 新增IPv6支持
- ✨ 新增GitHub仓库上传功能
- 🐛 修复编码问题（GBK解码错误）
- 🐛 修复NoneType strip错误
- 🔧 改进错误处理和用户提示
- 📝 更新文档说明
- 🔧 优化UUID格式验证（支持任意格式）
- 🔧 改进GitHub上传功能（支持公开仓库，包含注释）

### v2.0.0
- 重构代码结构
- 优化用户体验
- 改进错误处理机制

### v1.0.0 
- 初始版本发布
- 支持97个全球数据中心
- 常规测速功能
- 优选反代功能
- 跨平台支持
- 预编译可执行文件

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 致谢

- [Cloudflare](https://www.cloudflare.com/) - 提供全球CDN服务
- [CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest) - 原始测速工具
- 所有贡献者和用户的支持


---

**如果这个项目对您有帮助，请给我们一个星标！**
