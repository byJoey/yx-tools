package app

import (
	"encoding/json"
	"os"
	"strings"
	"sync"
)

// Config 是持久化到磁盘的用户配置
type Config struct {
	WorkerDomain string `json:"worker_domain"`
	UUID         string `json:"uuid"`
	GitHubToken  string `json:"github_token"`
	GitHubRepo   string `json:"github_repo"`
	GitHubPath   string `json:"github_path"`

	// 上次使用的测速参数，供界面回填
	Colo       string  `json:"colo"`
	IPv6       bool    `json:"ipv6"`
	Count      int     `json:"count"`
	SpeedLimit float64 `json:"speed_limit"`
	DelayLimit int     `json:"delay_limit"`
	Threads    int     `json:"threads"`
	TestURL    string  `json:"test_url"`
	Port       int     `json:"port"`
	SampleSize int     `json:"sample_size"`
	HTTPing    bool    `json:"httping"`
	DisableDL  bool    `json:"disable_dl"`
	DLTimeout  int     `json:"dl_timeout"`
	MaxRunTime int     `json:"max_runtime"`
}

const configName = "yx-config.json"

var (
	cfgMu sync.RWMutex
	cfg   *Config
)

// DefaultConfig 返回一份带默认值的配置
func DefaultConfig() *Config {
	return &Config{
		GitHubPath: "cloudflare_ips.txt",
		Count:      10,
		SpeedLimit: 1,
		DelayLimit: 1000,
		Threads:    200,
		TestURL:    DefaultTestURL,
		Port:       443,
		SampleSize: 1000,
		DLTimeout:  10,
	}
}

// ConfigPath 返回配置文件路径，落在可写的数据目录里
func ConfigPath() string {
	return DataPath(configName)
}

// LoadConfig 读取磁盘配置，不存在时返回默认值
func LoadConfig() *Config {
	cfgMu.Lock()
	defer cfgMu.Unlock()
	if cfg != nil {
		c := *cfg
		return &c
	}
	cfg = loadConfigFrom(ConfigPath())
	c := *cfg
	return &c
}

// 历史上用过、现在已经测不出速度的下载地址。
// 这些地址存进了老用户的配置里，升级后会被回填回来盖掉新默认值，
// 结果就是版本换了速度依然是 0，所以读取时直接迁移掉。
var deadTestURLs = []string{
	"cf.xiu2.xyz",           // 返回 403
	"cloudflaremirrors.com", // 返回 200 但 body 是空的
}

func isDeadTestURL(u string) bool {
	for _, dead := range deadTestURLs {
		if strings.Contains(u, dead) {
			return true
		}
	}
	return false
}

// loadConfigFrom 从指定路径读配置并补齐缺省值。
// 独立出来是为了能直接测到失效地址的迁移。
func loadConfigFrom(path string) *Config {
	c := DefaultConfig()
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, c)
	}
	if c.TestURL == "" || isDeadTestURL(c.TestURL) {
		c.TestURL = DefaultTestURL
	}
	if c.Port <= 0 {
		c.Port = 443
	}
	if c.DLTimeout <= 0 {
		c.DLTimeout = 10
	}
	return c
}

// SaveConfig 覆盖写入配置
func SaveConfig(c *Config) error {
	cfgMu.Lock()
	defer cfgMu.Unlock()
	cfg = c
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(ConfigPath(), data, 0o600)
}

// ClearConfig 删除磁盘上的配置文件
func ClearConfig() error {
	cfgMu.Lock()
	defer cfgMu.Unlock()
	cfg = DefaultConfig()
	err := os.Remove(ConfigPath())
	if os.IsNotExist(err) {
		return nil
	}
	return err
}
