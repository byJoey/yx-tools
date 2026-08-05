// yx 是 Cloudflare 优选 IP 测速工具，同时提供命令行与 Web 图形界面。
package main

import (
	"context"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"

	"github.com/byJoey/yx-tools/internal/app"
)

var version = "3.0.0"

const usage = `Cloudflare 优选 IP 测速工具 v%s

用法:
  yx                        启动图形界面（默认，自动打开浏览器）
  yx web [选项]             启动图形界面
  yx test [选项]            命令行测速
  yx proxy [选项]           从结果生成反代列表
  yx upload [选项]          上报已有结果
  yx cron [选项]            管理定时任务（Linux/macOS）

测速选项 (test):
  -colo   地区机场码，多个用逗号分隔，如 HKG,SIN；留空测全部
  -ipv6   使用 IPv6 段
  -n      测速数量（默认 10）
  -sl     下载速度下限 MB/s（默认 1）
  -tl     平均延迟上限 ms（默认 1000）
  -t      延迟测速线程数（默认 200，最大 1000）
  -port   测速端口（默认 443）
  -url    测速地址
  -f      自定义 IP 文件（支持 IP:端口 每行一条）；留空自动用 Cloudflare 官方 IP 段
  -c      参与延迟测速的候选 IP 数量，从官方段里随机抽（默认 0 不限，约 6000 个）
  -all    穷举每个网段的全部 IP（很慢，会忽略 -c）
  -http   用真实 HTTP 请求测延迟（含 TLS 握手与服务端响应），比 TCP 握手准
  -nodl   只测延迟，跳过下载测速
  -o      结果输出文件（默认 result.csv）

上报选项 (test 末尾追加，或单独用 upload):
  -upload api|github   上报方式
  -domain / -uuid      Worker 域名与 UUID
  -repo / -token       GitHub 仓库与 Token
  -path                GitHub 文件路径（默认 cloudflare_ips.txt）
  -limit               上报数量（默认 10）
  -clear               上报前清空 Worker 已有 IP

界面选项 (web):
  -listen  监听地址（默认 127.0.0.1:8080，远程访问用 0.0.0.0:8080）
  -no-open 不自动打开浏览器

定时任务 (cron):
  -list            列出已登记的任务
  -add "测速参数"   添加任务，配合 -at 指定时间
  -at "0 */6 * * *" cron 时间表达式（默认每 6 小时）
  -replace         添加前先清掉本程序已有的任务
  -remove          清除本程序登记的全部任务

示例:
  yx                                     打开图形界面
  yx web -listen 0.0.0.0:8080            在服务器上跑，浏览器远程访问
  yx test -colo HKG,SIN -n 20            测香港和新加坡，取 20 个
  yx test -n 10 -upload api -domain a.b -uuid xxx -clear
  yx proxy -limit 20                     生成 ips_ports.txt
  yx cron -add "test -n 10 -sl 2" -at "0 */6 * * *" -replace
`

func main() {
	if len(os.Args) < 2 {
		runWeb([]string{})
		return
	}
	switch os.Args[1] {
	case "web":
		runWeb(os.Args[2:])
	case "test":
		runTest(os.Args[2:])
	case "proxy":
		runProxy(os.Args[2:])
	case "upload":
		runUpload(os.Args[2:])
	case "cron":
		runCron(os.Args[2:])
	case "-v", "--version", "version":
		fmt.Printf("yx v%s\n", version)
	case "-h", "--help", "help":
		fmt.Printf(usage, version)
	default:
		// 兼容直接带测速参数的写法
		if strings.HasPrefix(os.Args[1], "-") {
			runTest(os.Args[1:])
			return
		}
		fmt.Printf("未知命令: %s\n\n", os.Args[1])
		fmt.Printf(usage, version)
		os.Exit(1)
	}
}

// ── 图形界面 ──────────────────────────────────────
func runWeb(args []string) {
	fs := flag.NewFlagSet("web", flag.ExitOnError)
	listen := fs.String("listen", "127.0.0.1:8080", "监听地址")
	noOpen := fs.Bool("no-open", false, "不自动打开浏览器")
	_ = fs.Parse(args)

	srv := app.NewServer()
	ln, err := net.Listen("tcp", *listen)
	if err != nil {
		fmt.Fprintf(os.Stderr, "监听失败: %v\n", err)
		os.Exit(1)
	}
	url := "http://" + displayAddr(ln.Addr().String())
	fmt.Printf("图形界面已启动: %s\n按 Ctrl+C 退出\n", url)
	if !*noOpen {
		go openBrowser(url)
	}

	httpSrv := &http.Server{Handler: srv, ReadHeaderTimeout: 10 * time.Second}
	go func() {
		sig := make(chan os.Signal, 1)
		signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
		<-sig
		fmt.Println("\n正在退出…")
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		_ = httpSrv.Shutdown(ctx)
	}()
	if err := httpSrv.Serve(ln); err != nil && err != http.ErrServerClosed {
		fmt.Fprintf(os.Stderr, "服务异常: %v\n", err)
		os.Exit(1)
	}
}

func displayAddr(addr string) string {
	host, port, err := net.SplitHostPort(addr)
	if err != nil {
		return addr
	}
	if host == "" || host == "0.0.0.0" || host == "::" {
		return "127.0.0.1:" + port
	}
	return addr
}

func openBrowser(url string) {
	time.Sleep(400 * time.Millisecond)
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		cmd = exec.Command("open", url)
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	_ = cmd.Start()
}

// ── 命令行测速 ────────────────────────────────────
type uploadFlags struct {
	mode   *string
	domain *string
	uuid   *string
	repo   *string
	token  *string
	path   *string
	limit  *int
	clear  *bool
}

func bindUploadFlags(fs *flag.FlagSet) uploadFlags {
	return uploadFlags{
		mode:   fs.String("upload", "", "上报方式: api / github"),
		domain: fs.String("domain", "", "Worker 域名"),
		uuid:   fs.String("uuid", "", "UUID 或自定义路径"),
		repo:   fs.String("repo", "", "GitHub 仓库 owner/repo"),
		token:  fs.String("token", "", "GitHub Token"),
		path:   fs.String("path", "", "GitHub 文件路径"),
		limit:  fs.Int("limit", 10, "上报数量"),
		clear:  fs.Bool("clear", false, "上报前清空 Worker 已有 IP"),
	}
}

func runTest(args []string) {
	fs := flag.NewFlagSet("test", flag.ExitOnError)
	colo := fs.String("colo", "", "地区机场码，逗号分隔")
	ipv6 := fs.Bool("ipv6", false, "使用 IPv6")
	count := fs.Int("n", 10, "测速数量")
	speed := fs.Float64("sl", 1, "下载速度下限 MB/s")
	delay := fs.Int("tl", 1000, "平均延迟上限 ms")
	threads := fs.Int("t", 200, "延迟测速线程数")
	port := fs.Int("port", 443, "测速端口")
	url := fs.String("url", "", "测速地址")
	ipFile := fs.String("f", "", "自定义 IP 文件")
	sample := fs.Int("c", 0, "候选 IP 数量，0 表示不限")
	testAll := fs.Bool("all", false, "穷举全部 IP")
	httping := fs.Bool("http", false, "用真实 HTTP 请求测延迟")
	noDL := fs.Bool("nodl", false, "只测延迟")
	out := fs.String("o", app.ResultFile, "结果输出文件")
	uf := bindUploadFlags(fs)
	_ = fs.Parse(args)

	o := app.Options{
		Colo: *colo, IPv6: *ipv6, Count: *count,
		SpeedLimit: *speed, DelayLimit: *delay, Threads: *threads,
		Port: *port, TestURL: *url, IPFile: *ipFile, DisableDL: *noDL,
		SampleSize: *sample, TestAll: *testAll, HTTPing: *httping,
		Verbose: true,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	rs, err := app.Run(ctx, o, func(p app.Progress) {
		fmt.Println("· " + p.Message)
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "测速失败: %v\n", err)
		os.Exit(1)
	}
	printResults(rs)
	if err := app.WriteCSV(*out, rs); err != nil {
		fmt.Fprintf(os.Stderr, "写入 %s 失败: %v\n", *out, err)
	} else {
		fmt.Printf("\n结果已保存: %s\n", *out)
	}
	doUpload(ctx, uf, rs)
}

func printResults(rs []app.Result) {
	if len(rs) == 0 {
		fmt.Println("没有符合条件的结果")
		return
	}
	fmt.Printf("\n%-18s %-6s %-9s %-11s %-7s %s\n", "IP", "端口", "延迟(ms)", "速度(MB/s)", "丢包", "地区")
	fmt.Println(strings.Repeat("-", 68))
	for _, r := range rs {
		fmt.Printf("%-18s %-6d %-9.0f %-11.2f %-7.0f%% %s\n",
			r.IP, r.Port, r.Delay, r.Speed, r.LossRate*100, r.ColoName)
	}
}

func doUpload(ctx context.Context, uf uploadFlags, rs []app.Result) {
	mode := strings.ToLower(strings.TrimSpace(*uf.mode))
	if mode == "" || mode == "none" {
		return
	}
	cfg := app.LoadConfig()
	switch mode {
	case "api":
		d, u := *uf.domain, *uf.uuid
		if d == "" {
			d = cfg.WorkerDomain
		}
		if u == "" {
			u = cfg.UUID
		}
		n, err := app.UploadToAPI(ctx, app.APITarget{Domain: d, UUID: u}, rs, *uf.limit, *uf.clear)
		if err != nil {
			fmt.Fprintf(os.Stderr, "上报失败: %v\n", err)
			os.Exit(1)
		}
		cfg.WorkerDomain, cfg.UUID = d, u
		_ = app.SaveConfig(cfg)
		fmt.Printf("已上报 %d 个 IP 到 Worker\n", n)
	case "github":
		repo, token, path := *uf.repo, *uf.token, *uf.path
		if repo == "" {
			repo = cfg.GitHubRepo
		}
		if token == "" {
			token = cfg.GitHubToken
		}
		if path == "" {
			path = cfg.GitHubPath
		}
		n, err := app.UploadToGitHub(ctx, app.GitHubTarget{Repo: repo, Token: token, Path: path}, rs, *uf.limit)
		if err != nil {
			fmt.Fprintf(os.Stderr, "上传失败: %v\n", err)
			os.Exit(1)
		}
		cfg.GitHubRepo, cfg.GitHubToken, cfg.GitHubPath = repo, token, path
		_ = app.SaveConfig(cfg)
		fmt.Printf("已上传 %d 个 IP 到 GitHub\n", n)
	default:
		fmt.Fprintf(os.Stderr, "未知上报方式: %s\n", mode)
		os.Exit(1)
	}
}

// ── 生成反代列表 ──────────────────────────────────
func runProxy(args []string) {
	fs := flag.NewFlagSet("proxy", flag.ExitOnError)
	in := fs.String("i", app.ResultFile, "测速结果 CSV")
	out := fs.String("o", app.ProxyListFile, "输出文件")
	limit := fs.Int("limit", 0, "取前 N 条，0 表示全部")
	_ = fs.Parse(args)

	rs, err := app.ReadCSV(*in)
	if err != nil {
		fmt.Fprintf(os.Stderr, "读取失败: %v\n", err)
		os.Exit(1)
	}
	n, err := app.WriteProxyList(*out, rs, *limit)
	if err != nil {
		fmt.Fprintf(os.Stderr, "生成失败: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("已生成 %s，共 %d 条\n", *out, n)
}

// ── 上报已有结果 ──────────────────────────────────
func runUpload(args []string) {
	fs := flag.NewFlagSet("upload", flag.ExitOnError)
	in := fs.String("i", app.ResultFile, "测速结果 CSV")
	uf := bindUploadFlags(fs)
	_ = fs.Parse(args)

	if strings.TrimSpace(*uf.mode) == "" {
		fmt.Fprintln(os.Stderr, "请用 -upload api 或 -upload github 指定上报方式")
		os.Exit(1)
	}
	rs, err := app.ReadCSV(*in)
	if err != nil {
		fmt.Fprintf(os.Stderr, "读取失败: %v\n", err)
		os.Exit(1)
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	doUpload(ctx, uf, rs)
}

// ── 定时任务 ──────────────────────────────────────
func runCron(args []string) {
	fs := flag.NewFlagSet("cron", flag.ExitOnError)
	list := fs.Bool("list", false, "列出已登记的任务")
	add := fs.String("add", "", `添加任务，值为测速参数，如 "test -n 10 -sl 2"`)
	at := fs.String("at", "0 */6 * * *", "cron 时间表达式")
	replace := fs.Bool("replace", false, "添加前先清掉已有任务")
	remove := fs.Bool("remove", false, "清除本程序登记的全部任务")
	_ = fs.Parse(args)

	if !app.CronSupported() {
		fmt.Fprintln(os.Stderr, "当前系统不支持 crontab。Windows 请用「任务计划程序」调用本程序。")
		os.Exit(1)
	}

	switch {
	case *remove:
		n, err := app.RemoveCronJobs()
		if err != nil {
			fmt.Fprintf(os.Stderr, "清除失败: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("已清除 %d 条定时任务\n", n)

	case *add != "":
		// 用绝对路径，并切到程序所在目录，保证结果文件落在预期位置
		self := app.SelfPath()
		dir := filepath.Dir(self)
		cmd := fmt.Sprintf("cd %s && %s %s >> yx-cron.log 2>&1", quote(dir), quote(self), *add)
		if err := app.AddCronJob(*at, cmd, *replace); err != nil {
			fmt.Fprintf(os.Stderr, "添加失败: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("已添加定时任务\n  时间: %s\n  命令: %s\n", *at, cmd)
		fmt.Println("日志会写入程序目录下的 yx-cron.log")

	default:
		jobs, err := app.ListCronJobs()
		if err != nil {
			fmt.Fprintf(os.Stderr, "读取失败: %v\n", err)
			os.Exit(1)
		}
		if len(jobs) == 0 {
			fmt.Println("还没有登记定时任务")
			fmt.Println(`添加示例: yx cron -add "test -n 10 -sl 2" -at "0 */6 * * *"`)
			return
		}
		fmt.Printf("共 %d 条定时任务:\n", len(jobs))
		for i, j := range jobs {
			fmt.Printf("  %d. [%s] %s\n", i+1, j.Schedule, j.Command)
		}
		_ = list
	}
}

// quote 给路径加引号，避免空格截断
func quote(s string) string {
	if strings.ContainsAny(s, " \t") {
		return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
	}
	return s
}
