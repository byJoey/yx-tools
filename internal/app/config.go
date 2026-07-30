package app

import (
	"encoding/json"
	"os"
	"path/filepath"
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
	}
}

// ConfigPath 返回配置文件路径，与可执行文件同目录
func ConfigPath() string {
	exe, err := os.Executable()
	if err != nil {
		return configName
	}
	return filepath.Join(filepath.Dir(exe), configName)
}

// LoadConfig 读取磁盘配置，不存在时返回默认值
func LoadConfig() *Config {
	cfgMu.Lock()
	defer cfgMu.Unlock()
	if cfg != nil {
		c := *cfg
		return &c
	}
	cfg = DefaultConfig()
	data, err := os.ReadFile(ConfigPath())
	if err == nil {
		_ = json.Unmarshal(data, cfg)
	}
	if cfg.TestURL == "" {
		cfg.TestURL = DefaultTestURL
	}
	if cfg.Port <= 0 {
		cfg.Port = 443
	}
	c := *cfg
	return &c
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
