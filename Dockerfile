FROM docker.cnb.cool/xzydm/mirrors/python:3.9-slim
# 设置工作目录
WORKDIR /app
ENV TZ=Asia/Shanghai
# 配置时区（保持不变）
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 更换 APT 源（保持不变）
RUN set -eux; \
    . /etc/os-release; \
    MIRROR_PREFIX="http://mirrors.cloud.tencent.com"; \
    case "$ID" in \
        debian) \
            case "$VERSION_ID" in \
                11) \
                    sed -i "s@http://deb.debian.org/debian@${MIRROR_PREFIX}/debian@g" /etc/apt/sources.list; \
                    sed -i "s@http://security.debian.org/debian-security@${MIRROR_PREFIX}/debian-security@g" /etc/apt/sources.list; \
                    ;; \
                12|13) \
                    sed -i "s@URIs: http://deb.debian.org/debian@URIs: ${MIRROR_PREFIX}/debian@g" /etc/apt/sources.list.d/debian.sources; \
                    sed -i "s@URIs: http://security.debian.org/debian-security@URIs: ${MIRROR_PREFIX}/debian-security@g" /etc/apt/sources.list.d/debian.sources; \
                    ;; \
                *) \
                    echo "Warning: Unsupported Debian version $VERSION_ID"; \
                    ;; \
            esac; \
            ;; \
        ubuntu) \
            sed -i "s@http://archive.ubuntu.com/ubuntu@${MIRROR_PREFIX}/ubuntu@g" /etc/apt/sources.list; \
            sed -i "s@http://security.ubuntu.com/ubuntu@${MIRROR_PREFIX}/ubuntu-security@g" /etc/apt/sources.list; \
            ;; \
        *) \
            echo "Warning: Unsupported distribution $ID"; \
            ;; \
    esac

# 安装系统依赖（保持不变，已包含必要工具）
# 安装系统依赖（保持不变，已包含必要工具）
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    curl \
    wget \
    cron \
    git \
    libgomp1 \
    ca-certificates \
    tzdata \
    tar \
    && \
    # 合并清理命令，减少层大小
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 复制优化后的Python脚本（文件名从auto_speedtest.py改为main.py）
COPY auto_speedtest.py .

# 安装Python依赖（保持不变，已包含必要依赖）
RUN pip install --no-cache-dir requests python-dotenv -i https://mirrors.cloud.tencent.com/pypi/simple/


# 定时任务：日志输出到/data目录（已挂载，持久化）
# 定时任务：显式设置PATH，确保python3可被找到
RUN echo "0 8 * * * root export PATH=/usr/local/bin:/usr/bin:/bin; . /app/.env; python3 /app/auto_speedtest.py >> /app/data/speedtest.log 2>&1" > /etc/cron.d/speedtest-cron && \
    echo "0 0 * * 0 root > /app/data/speedtest.log 2>&1" >> /etc/cron.d/speedtest-cron && \
    chmod 0644 /etc/cron.d/speedtest-cron

# 启动命令：保持脚本名不变
# 启动cron后，直接用tail跟踪日志（不依赖脚本执行结果）
# 启动命令：先创建日志文件，再启动服务
CMD ["sh", "-c", "mkdir -p /app/data && \
                  echo '启动初始化...' >> /app/data/speedtest.log 2>&1 && \
                  cron && \
                  stdbuf -oL -eL python3 /app/auto_speedtest.py >> /app/data/speedtest.log 2>&1 & \
                  tail -f /app/data/speedtest.log"]