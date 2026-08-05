package app

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestWritableDir(t *testing.T) {
	ok := t.TempDir()
	if !writableDir(ok) {
		t.Error("临时目录应判定为可写")
	}

	// 不存在的子目录应被创建出来
	nested := filepath.Join(ok, "a", "b")
	if !writableDir(nested) {
		t.Error("应能创建多级目录")
	}

	if os.Geteuid() == 0 {
		t.Skip("root 无视权限位，跳过只读目录用例")
	}
	ro := filepath.Join(t.TempDir(), "ro")
	if err := os.Mkdir(ro, 0o555); err != nil {
		t.Fatal(err)
	}
	if writableDir(ro) {
		t.Error("只读目录不该判定为可写")
	}
}

func TestDataPathKeepsAbsolute(t *testing.T) {
	abs := filepath.Join(t.TempDir(), "x.csv")
	if got := DataPath(abs); got != abs {
		t.Errorf("绝对路径应原样返回，got %q", got)
	}
	if got := DataPath(""); got != "" {
		t.Errorf("空值应原样返回，got %q", got)
	}
	got := DataPath("result.csv")
	if !filepath.IsAbs(got) || filepath.Base(got) != "result.csv" {
		t.Errorf("相对名应解析到数据目录，got %q", got)
	}
}

// 内核遇到坏输入应返回错误而不是终止进程
func TestRunRecoversKernelFatal(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "not-exist.txt")
	_, err := Run(context.Background(), Options{IPFile: missing, Count: 1, DisableDL: true}, nil)
	if err == nil {
		t.Fatal("读不到 IP 文件应返回错误")
	}
}

// 来源文件是纯 IP:端口 列表时也该能生成，别人分享的多是这种格式
func TestProxyListFromPlainList(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "src.txt")
	body := "1.1.1.1:443\n1.0.0.1:2053\n# 注释\n8.8.8.8\n"
	if err := os.WriteFile(src, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(dir, "ips_ports.txt")
	n, err := ProxyListFromCSV(src, out, 0)
	if err != nil {
		t.Fatalf("纯列表应能解析: %v", err)
	}
	if n != 3 {
		t.Errorf("应解析出 3 条，got %d", n)
	}
	got, err := os.ReadFile(out)
	if err != nil {
		t.Fatal(err)
	}
	want := "1.1.1.1:443\n1.0.0.1:2053\n8.8.8.8:443\n"
	if string(got) != want {
		t.Errorf("内容不对\n got: %q\nwant: %q", got, want)
	}
}
