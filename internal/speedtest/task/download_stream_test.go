package task

import (
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strconv"
	"testing"
	"time"

	"github.com/byJoey/yx-tools/internal/speedtest/utils"
)

// 起一个本地测速靶子。全程不打公网。
func localTarget(t *testing.T) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("CF-RAY", "0000000000000000-TST")
		_, _ = w.Write(make([]byte, 64*1024))
	}))
	t.Cleanup(srv.Close)
	return srv
}

// 把内核指向本地靶子，并在用例结束后恢复原值
func pointKernelAt(t *testing.T, srv *httptest.Server) []*net.IPAddr {
	t.Helper()
	u, err := url.Parse(srv.URL)
	if err != nil {
		t.Fatal(err)
	}
	port, err := strconv.Atoi(u.Port())
	if err != nil {
		t.Fatal(err)
	}

	oldURL, oldPort, oldDisable := URL, TCPPort, Disable
	oldCount, oldMin, oldTimeout := TestCount, MinSpeed, Timeout
	t.Cleanup(func() {
		URL, TCPPort, Disable = oldURL, oldPort, oldDisable
		TestCount, MinSpeed, Timeout = oldCount, oldMin, oldTimeout
		OnSpeedResult, Deadline = nil, time.Time{}
		PortMapping = nil
	})

	URL, TCPPort, Disable = srv.URL, port, false
	MinSpeed, Timeout = 0, 2*time.Second
	PortMapping = make(map[string]int)

	ip := &net.IPAddr{IP: net.ParseIP("127.0.0.1")}
	return []*net.IPAddr{ip, ip, ip}
}

func pingSet(ips []*net.IPAddr) utils.PingDelaySet {
	var set utils.PingDelaySet
	for _, ip := range ips {
		set = append(set, utils.CloudflareIPData{
			PingData: &utils.PingData{IP: ip, Sended: 4, Received: 4},
		})
	}
	return set
}

// 下载测速本来就是一个个串行跑的，结果应当边测边回，
// 而不是攒到整批结束才一次性交出去。
func TestDownloadEmitsResultsOneByOne(t *testing.T) {
	srv := localTarget(t)
	ips := pointKernelAt(t, srv)
	TestCount = len(ips)

	var got int
	OnSpeedResult = func(utils.CloudflareIPData) { got++ }

	set := TestDownloadSpeed(pingSet(ips))
	if got != len(ips) {
		t.Errorf("应逐条回调 %d 次，实际 %d 次", len(ips), got)
	}
	if len(set) == 0 {
		t.Error("结果不该为空")
	}
}

// 候选很多时单个 IP 的 Timeout 兜不住总时长，Deadline 是总闸：
// 到点应立即收工。
func TestDownloadStopsAtDeadline(t *testing.T) {
	srv := localTarget(t)
	ips := pointKernelAt(t, srv)
	TestCount = len(ips)

	// 已经过期的截止时间：一条都不该测
	Deadline = time.Now().Add(-time.Second)
	var got int
	OnSpeedResult = func(utils.CloudflareIPData) { got++ }

	start := time.Now()
	TestDownloadSpeed(pingSet(ips))
	if got != 0 {
		t.Errorf("已过截止时间不该继续测，却测了 %d 条", got)
	}
	if elapsed := time.Since(start); elapsed > time.Second {
		t.Errorf("应立即返回，实际耗时 %v", elapsed)
	}
}

// 测速文件不够大或提前下完时，原本固定除以 Timeout 会严重低估速度：
// 几 MB 的文件在快节点上零点几秒就下完，摊到 10 秒后接近 0。
// 这里用本地靶子（速度极快、文件很小）验证结果不再是 0。
func TestDownloadSpeedNotZeroOnFastSmallFile(t *testing.T) {
	srv := localTarget(t) // 64KB，本地瞬间下完
	ips := pointKernelAt(t, srv)
	TestCount = 1

	var got float64
	OnSpeedResult = func(d utils.CloudflareIPData) { got = d.DownloadSpeed }

	TestDownloadSpeed(pingSet(ips[:1]))
	if got <= 0 {
		t.Errorf("小文件秒下完时速度不该归零，got %v", got)
	}
}
