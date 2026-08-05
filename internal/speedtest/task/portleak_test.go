package task

import (
	"fmt"
	"net"
	"net/http"
	"net/http/httptest"
	"os/exec"
	"strings"
	"testing"
	"time"
)

// 统计本机 TIME_WAIT 连接数
func timeWaitCount(t *testing.T) int {
	out, err := exec.Command("netstat", "-an").Output()
	if err != nil {
		t.Skip("拿不到 netstat，跳过")
	}
	return strings.Count(string(out), "TIME_WAIT")
}

// tcping 每次探测都新建连接。若主动 close 而不设 SO_LINGER=0，
// 本地端口会进入 60 秒 TIME_WAIT，几千个候选就能占满整个临时端口池，
// 之后所有连接报 "can't assign requested address"——包括机器上的其它业务。
// 这里对本地监听端口做几百次探测，确认端口不会堆积。
func TestTCPingDoesNotLeakPorts(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	go func() {
		for {
			c, err := ln.Accept()
			if err != nil {
				return
			}
			_ = c.Close()
		}
	}()

	addr := ln.Addr().(*net.TCPAddr)
	before := timeWaitCount(t)

	p := &Ping{}
	const n = 400
	for i := 0; i < n; i++ {
		TCPPort = addr.Port
		if ok, _ := p.tcping(&net.IPAddr{IP: addr.IP}); !ok {
			t.Fatalf("第 %d 次探测失败", i)
		}
	}

	after := timeWaitCount(t)
	grew := after - before
	// 留一点余量给系统其它连接，但绝不能接近探测次数
	if grew > n/4 {
		t.Fatalf("%d 次探测后 TIME_WAIT 增长 %d，端口没有及时回收", n, grew)
	}
	t.Logf("%d 次探测，TIME_WAIT %d → %d（增长 %d）", n, before, after, grew)
}

// httping 每个 IP 新建 Transport，用完不回收同样会占住端口
func TestHTTPingDoesNotLeakPorts(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("CF-RAY", "abc-HKG")
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	host, port, _ := net.SplitHostPort(strings.TrimPrefix(srv.URL, "http://"))
	URL = srv.URL
	Httping = true
	HttpingStatusCode = 200
	HttpingCFColo = ""
	PingTimes = 2
	fmt.Sscanf(port, "%d", &TCPPort)
	defer func() { Httping = false; HttpingCFColo = "" }()

	before := timeWaitCount(t)
	p := &Ping{}
	const n = 150
	for i := 0; i < n; i++ {
		p.httping(&net.IPAddr{IP: net.ParseIP(host)})
	}
	time.Sleep(200 * time.Millisecond)

	after := timeWaitCount(t)
	grew := after - before
	// 修好前 150 次会留下 170+ 个；这里按 1/4 卡，留余量给系统其它连接
	if grew > n/4 {
		t.Fatalf("%d 次 httping 后 TIME_WAIT 增长 %d，连接没有回收", n, grew)
	}
	t.Logf("%d 次 httping，TIME_WAIT %d → %d（增长 %d）", n, before, after, grew)
}
