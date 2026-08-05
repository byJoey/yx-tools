package app

import (
	"os"
	"path/filepath"
	"sync"
)

// 数据目录环境变量，Docker 镜像里指向挂载出来的卷
const dataDirEnv = "YX_DATA_DIR"

var (
	dataDirOnce sync.Once
	dataDir     string
)

// DataDir 返回存放结果、缓存与配置的目录。
// 按可写性依次挑选，避免在只读目录（如容器里的 /usr/local/bin）或
// 属主不对的挂载点上启动后才报 permission denied。
func DataDir() string {
	dataDirOnce.Do(func() {
		for _, dir := range candidateDataDirs() {
			if dir == "" {
				continue
			}
			if writableDir(dir) {
				dataDir = dir
				return
			}
		}
		dataDir = os.TempDir()
	})
	return dataDir
}

func candidateDataDirs() []string {
	var dirs []string
	if v := os.Getenv(dataDirEnv); v != "" {
		dirs = append(dirs, v)
	}
	if wd, err := os.Getwd(); err == nil {
		dirs = append(dirs, wd)
	}
	if exe, err := os.Executable(); err == nil {
		dirs = append(dirs, filepath.Dir(exe))
	}
	if home, err := os.UserHomeDir(); err == nil {
		dirs = append(dirs, filepath.Join(home, ".yx-tools"))
	}
	return dirs
}

// writableDir 判断目录能否落文件；不存在时尝试建出来
func writableDir(dir string) bool {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return false
	}
	f, err := os.CreateTemp(dir, ".yx-write-*")
	if err != nil {
		return false
	}
	name := f.Name()
	_ = f.Close()
	_ = os.Remove(name)
	return true
}

// DataPath 把相对文件名解析到数据目录；已是绝对路径的原样返回
func DataPath(name string) string {
	if name == "" {
		return ""
	}
	if filepath.IsAbs(name) {
		return name
	}
	return filepath.Join(DataDir(), name)
}
