# 构建
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /yx ./cmd/yx

# 运行
FROM alpine:latest
RUN apk add --no-cache ca-certificates tzdata su-exec && \
    adduser -D -u 1000 yx
# 结果、配置、IP 段缓存都写这里；挂卷时宿主机目录要能被 uid 1000 写入
ENV YX_DATA_DIR=/data
WORKDIR /data
COPY --from=builder /yx /usr/local/bin/yx
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && chown yx:yx /data
EXPOSE 8080
# 默认起图形界面，监听所有网卡以便容器外访问
# 入口脚本以 root 修好挂载目录属主后降权到 yx 运行
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["web", "-listen", "0.0.0.0:8080", "-no-open"]
