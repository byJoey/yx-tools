package app

import (
	"os"
	"path/filepath"
	"testing"
)

// 老用户配置里存着已经失效的测速地址，升级后会被回填回来盖掉新默认值，
// 结果是版本换了速度依然是 0。读取时应当直接迁移掉。
func TestLoadConfigMigratesDeadTestURL(t *testing.T) {
	cases := []struct {
		name    string
		stored  string
		migrate bool
	}{
		{"上游默认地址已 403", "https://cf.xiu2.xyz/url", true},
		{"镜像站返回空 body", "https://cloudflaremirrors.com/archlinux/iso/latest/archlinux-x86_64.iso", true},
		{"误设成默认值的私人域名要清掉", "https://xy.kg/test", true},
		{"用户自己填的可用地址要保留", "https://speed.cloudflare.com/__down?bytes=50000000", false},
		{"自建地址要保留", "https://my-own-mirror.example/bigfile", false},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			dir := t.TempDir()
			path := filepath.Join(dir, configName)
			body := `{"test_url":"` + c.stored + `"}`
			if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
				t.Fatal(err)
			}

			// 真正走一遍加载逻辑，而不是只测判定函数
			cfgMu.Lock()
			cfg = nil // 清掉进程内缓存，强制从磁盘读
			cfgMu.Unlock()
			got := loadConfigFrom(path)

			if c.migrate && got.TestURL != DefaultTestURL {
				t.Errorf("失效地址应迁移成默认值，got %q", got.TestURL)
			}
			if !c.migrate && got.TestURL != c.stored {
				t.Errorf("可用地址不该被改动，got %q want %q", got.TestURL, c.stored)
			}
		})
	}
}

// 默认地址本身不该被判成失效，否则会陷入自我迁移
func TestDefaultTestURLIsNotDead(t *testing.T) {
	if isDeadTestURL(DefaultTestURL) {
		t.Errorf("默认地址 %q 不该被判成失效", DefaultTestURL)
	}
	if DefaultTestURL == "" {
		t.Error("默认地址不该为空")
	}
}
