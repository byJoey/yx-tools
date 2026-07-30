# 构建
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /yx ./cmd/yx

# 运行
FROM alpine:latest
RUN apk add --no-cache ca-certificates tzdata && \
    adduser -D -u 1000 yx
WORKDIR /data
COPY --from=builder /yx /usr/local/bin/yx
USER yx
EXPOSE 8080
# 默认起图形界面，监听所有网卡以便容器外访问
ENTRYPOINT ["yx"]
CMD ["web", "-listen", "0.0.0.0:8080", "-no-open"]
