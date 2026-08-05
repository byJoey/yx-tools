package app

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/byJoey/yx-tools/internal/speedtest/task"
	"github.com/byJoey/yx-tools/internal/speedtest/utils"
)

// 默认参数
const (
	// 走 Cloudflare 的大文件，用于下载测速；原上游默认地址已失效
	DefaultTestURL  = "https://cloudflaremirrors.com/archlinux/iso/latest/archlinux-x86_64.iso"
	CloudflareIPv4  = "https://www.cloudflare.com/ips-v4/"
	CloudflareIPv6  = "https://www.cloudflare.com/ips-v6/"
	IPv4File        = "Cloudflare.txt"
	IPv6File        = "Cloudflare_ipv6.txt"
	ResultFile      = "result.csv"
	ProxyListFile   = "ips_ports.txt"
	defaultPingTime = 4
)

// Options 是一次测速任务的输入参数
type Options struct {
	Colo       string  `json:"colo"`        // 机场码筛选，多个用逗号分隔，空表示不限
	IPv6       bool    `json:"ipv6"`        // 使用 IPv6 段
	Count      int     `json:"count"`       // 下载测速数量
	SpeedLimit float64 `json:"speed_limit"` // 下载速度下限 MB/s
	DelayLimit int     `json:"delay_limit"` // 平均延迟上限 ms
	Threads    int     `json:"threads"`     // 延迟测速线程数
	Port       int     `json:"port"`        // 测速端口
	TestURL    string  `json:"test_url"`    // 下载测速地址
	IPFile     string  `json:"ip_file"`     // 自定义 IP 文件；为空则按 IPv6 选项自动下载
	IPText     string  `json:"ip_text"`     // 直接指定 IP 段，优先于 IPFile
	SampleSize int     `json:"sample_size"` // 参与延迟测速的候选 IP 数量，0 表示不限
	Proxy      bool    `json:"proxy"`       // 反代模式：直接测给定的 IP:端口 列表
	HTTPing    bool    `json:"httping"`     // 用真实 HTTP 请求测延迟（含 TLS 与服务端响应）
	DisableDL  bool    `json:"disable_dl"`  // 只测延迟，跳过下载测速
	TestAll    bool    `json:"test_all"`    // 测速全部 IP
	Verbose    bool    `json:"-"`           // 是否让测速内核输出自己的进度条
}

// Result 是单条测速结果
type Result struct {
	IP       string  `json:"ip"`
	Port     int     `json:"port"`
	Sent     int     `json:"sent"`
	Received int     `json:"received"`
	LossRate float64 `json:"loss_rate"`
	Delay    float64 `json:"delay"`
	Speed    float64 `json:"speed"`
	Colo     string  `json:"colo"`
	ColoName string  `json:"colo_name"`
}

// Progress 描述测速进度，供界面实时展示
type Progress struct {
	Stage   string `json:"stage"`   // prepare / ping / download / done
	Message string `json:"message"` // 面向用户的一句话
	Current int    `json:"current"`
	Total   int    `json:"total"`
}

// 测速内核使用大量包级变量，同一进程内必须串行执行
var runMu sync.Mutex

// Normalize 补齐缺省值并做边界约束
func (o *Options) Normalize() {
	if o.Count <= 0 {
		o.Count = 10
	}
	if o.Threads <= 0 {
		o.Threads = 200
	}
	if o.Threads > 1000 {
		o.Threads = 1000
	}
	if o.DelayLimit <= 0 {
		o.DelayLimit = 9999
	}
	if o.Port <= 0 {
		o.Port = 443
	}
	if o.TestURL == "" {
		o.TestURL = DefaultTestURL
	}
	// 反代模式测的是给定的 IP:端口 列表，列表是什么就测什么，不抽样也不穷举。
	// 地区筛选照常可用：反代最终回源到 Cloudflare，响应头里一样带得出机房代码。
	if o.Proxy {
		o.SampleSize = 0
		o.TestAll = false
		if o.IPFile == "" && o.IPText == "" {
			o.IPFile = ProxyListFile
		}
	}
	if strings.TrimSpace(o.Colo) != "" {
		o.HTTPing = true
	}
	if o.SampleSize < 0 {
		o.SampleSize = 0
	}
	// 勾了「测速全部 IP」就是要穷举，抽样会自相矛盾
	if o.TestAll {
		o.SampleSize = 0
	}
	// 候选数少于要出的结果数没有意义
	if o.SampleSize > 0 && o.SampleSize < o.Count {
		o.SampleSize = o.Count
	}
}

// Run 执行一次完整测速。report 可为 nil。
func Run(ctx context.Context, o Options, report func(Progress)) ([]Result, error) {
	runMu.Lock()
	defer runMu.Unlock()

	o.Normalize()
	utils.SetQuiet(!o.Verbose)
	defer utils.SetQuiet(false)
	emit := func(p Progress) {
		if report != nil {
			report(p)
		}
	}

	ipFile := o.IPFile
	if o.IPText == "" && ipFile == "" {
		emit(Progress{Stage: "prepare", Message: "正在获取 Cloudflare IP 段"})
		var err error
		ipFile, err = ensureIPFile(ctx, o.IPv6)
		if err != nil {
			return nil, err
		}
	}

	// 内核以包级变量接收参数
	task.Routines = o.Threads
	task.PingTimes = defaultPingTime
	task.TestCount = o.Count
	task.TCPPort = o.Port
	task.URL = o.TestURL
	task.MinSpeed = o.SpeedLimit
	task.Disable = o.DisableDL
	task.TestAll = o.TestAll
	task.SampleSize = o.SampleSize
	task.IPFile = ipFile
	task.IPText = o.IPText
	task.PortMapping = make(map[string]int)

	colo := strings.TrimSpace(o.Colo)
	// 地区码只能从 HTTP 响应头里拿，选了地区就必须走 HTTPing
	task.Httping = o.HTTPing || colo != ""
	task.HttpingCFColo = colo
	utils.InputMaxDelay = time.Duration(o.DelayLimit) * time.Millisecond
	utils.InputMinDelay = 0
	utils.InputMaxLossRate = 1
	utils.PrintNum = 0 // 结果由本程序输出，禁用内核自身打印

	task.InitRandSeed()
	task.SetContext(ctx)
	defer task.SetContext(nil)

	// 把内核进度条的推进转成事件，让界面看得见进度而不是干等。
	// 几千个 IP 逐个上报会淹掉事件通道，所以按时间节流。
	stage := "ping"
	pingMsg := "正在测试延迟"
	if colo != "" {
		pingMsg += "并匹配地区 " + colo
	}
	var lastTick time.Time
	utils.OnProgress = func(cur, total int) {
		msg := pingMsg
		if stage == "download" {
			msg = "正在测试下载速度"
		}
		// 收尾那一下一定要发，否则进度条会停在 99%
		if cur < total && time.Since(lastTick) < 200*time.Millisecond {
			return
		}
		lastTick = time.Now()
		emit(Progress{Stage: stage, Message: msg, Current: cur, Total: total})
	}
	defer func() { utils.OnProgress = nil }()

	emit(Progress{Stage: "ping", Message: pingMsg})
	pingData := task.NewPing().Run().FilterDelay().FilterLossRate()
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if len(pingData) == 0 {
		return nil, errors.New("没有符合条件的 IP，可放宽延迟上限或更换地区")
	}

	var speedData utils.DownloadSpeedSet
	if o.DisableDL {
		speedData = utils.DownloadSpeedSet(pingData)
	} else {
		stage = "download"
		emit(Progress{Stage: "download", Message: "正在测试下载速度", Total: o.Count})
		speedData = task.TestDownloadSpeed(pingData)
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	results := toResults(speedData)
	// 未设速度下限时内核会返回全部 IP，这里统一收敛到用户要的数量
	if o.Count > 0 && len(results) > o.Count {
		results = results[:o.Count]
	}
	emit(Progress{Stage: "done", Message: fmt.Sprintf("完成，共 %d 个结果", len(results)), Current: len(results), Total: len(results)})
	return results, nil
}

func toResults(set utils.DownloadSpeedSet) []Result {
	out := make([]Result, 0, len(set))
	for _, d := range set {
		port := d.Port
		if port <= 0 {
			port = task.TCPPort
		}
		var loss float64
		if d.Sended > 0 {
			loss = float64(d.Sended-d.Received) / float64(d.Sended)
		}
		out = append(out, Result{
			IP:       d.IP.String(),
			Port:     port,
			Sent:     d.Sended,
			Received: d.Received,
			LossRate: loss,
			// 用 Seconds()*1000 而非 Milliseconds()：后者是整数截断，
			// 亚毫秒的握手（本机到近处节点常见）会被归零。
			Delay:    d.Delay.Seconds() * 1000,
			Speed:    d.DownloadSpeed / 1024 / 1024,
			Colo:     d.Colo,
			ColoName: ColoName(d.Colo),
		})
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Speed != out[j].Speed {
			return out[i].Speed > out[j].Speed
		}
		return out[i].Delay < out[j].Delay
	})
	return out
}

// ensureIPFile 下载并缓存 Cloudflare 官方 IP 段
func ensureIPFile(ctx context.Context, ipv6 bool) (string, error) {
	name, url := IPv4File, CloudflareIPv4
	if ipv6 {
		name, url = IPv6File, CloudflareIPv6
	}
	if st, err := os.Stat(name); err == nil && st.Size() > 0 {
		return name, nil
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return "", err
	}
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("下载 IP 段失败: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("下载 IP 段失败: HTTP %d", resp.StatusCode)
	}
	f, err := os.Create(name)
	if err != nil {
		return "", err
	}
	defer f.Close()
	sc := bufio.NewScanner(resp.Body)
	w := bufio.NewWriter(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		fmt.Fprintln(w, line)
	}
	if err := sc.Err(); err != nil {
		return "", err
	}
	return name, w.Flush()
}

// ParseProxyLine 解析 "IP:端口" 或裸 IP，端口缺省为 443
func ParseProxyLine(line string) (string, int, bool) {
	line = strings.TrimSpace(line)
	if line == "" || strings.HasPrefix(line, "#") {
		return "", 0, false
	}
	if strings.HasPrefix(line, "[") { // IPv6 字面量
		if h, p, err := net.SplitHostPort(line); err == nil {
			port, _ := strconv.Atoi(p)
			return h, port, net.ParseIP(h) != nil
		}
	}
	if strings.Count(line, ":") == 1 {
		h, p, err := net.SplitHostPort(line)
		if err == nil {
			port, _ := strconv.Atoi(p)
			if port > 0 && port < 65536 && net.ParseIP(h) != nil {
				return h, port, true
			}
		}
	}
	if net.ParseIP(line) != nil {
		return line, 443, true
	}
	return "", 0, false
}
