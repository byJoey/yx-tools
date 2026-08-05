#!/bin/sh
# 以 root 起，把数据目录的属主修好再降权跑。
# 宿主机 bind mount 进来的目录默认属 root，容器里的普通用户写不了，
# 这一步能省掉用户自己 chown 的麻烦。
set -e

DATA_DIR="${YX_DATA_DIR:-/data}"

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_DIR"
  chown -R yx:yx "$DATA_DIR" 2>/dev/null || true
  exec su-exec yx yx "$@"
fi

exec yx "$@"
