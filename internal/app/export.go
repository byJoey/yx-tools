package app

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

var csvHeader = []string{"IP 地址", "已发送", "已接收", "丢包率", "平均延迟", "下载速度(MB/s)", "地区码", "端口"}

// WriteCSV 导出测速结果，列顺序与测速内核保持一致
func WriteCSV(path string, rs []Result) error {
	if path == "" {
		path = ResultFile
	}
	f, err := os.Create(DataPath(path))
	if err != nil {
		return err
	}
	defer f.Close()
	w := csv.NewWriter(f)
	defer w.Flush()
	if err := w.Write(csvHeader); err != nil {
		return err
	}
	for _, r := range rs {
		row := []string{
			r.IP,
			strconv.Itoa(r.Sent),
			strconv.Itoa(r.Received),
			strconv.FormatFloat(r.LossRate, 'f', 2, 64),
			strconv.FormatFloat(r.Delay, 'f', 2, 64),
			strconv.FormatFloat(r.Speed, 'f', 2, 64),
			orNA(r.Colo),
			strconv.Itoa(r.Port),
		}
		if err := w.Write(row); err != nil {
			return err
		}
	}
	return nil
}

func orNA(s string) string {
	if s == "" {
		return "N/A"
	}
	return s
}

// ReadCSV 读回测速结果，兼容旧版本导出的列名
func ReadCSV(path string) ([]Result, error) {
	f, err := os.Open(path)
	if err != nil && !filepath.IsAbs(path) {
		// 当前目录不可写时结果会落在数据目录，读取也要跟过去
		if alt, e := os.Open(DataPath(path)); e == nil {
			f, err = alt, nil
		}
	}
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return parseCSV(f, path)
}

// parseCSVText 解析一段 CSV 文本，供界面上粘贴的内容使用
func parseCSVText(text string) ([]Result, error) {
	return parseCSV(strings.NewReader(text), "输入内容")
}

// normalizeHeader 把列名压成可比对的形式：去 BOM、去空白、转小写。
// FOFA 那类资产导出的列名是全小写的 ip / port，本工具导出的是
// "IP 地址" / "端口"，归一化后用同一套名字匹配。
func normalizeHeader(h string) string {
	h = strings.TrimPrefix(h, "\ufeff")
	h = strings.ToLower(strings.TrimSpace(h))
	return strings.ReplaceAll(h, " ", "")
}

func parseCSV(src io.Reader, name string) ([]Result, error) {
	r := csv.NewReader(src)
	r.FieldsPerRecord = -1
	rows, err := r.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(rows) < 2 {
		return nil, fmt.Errorf("%s 没有数据", name)
	}
	idx := map[string]int{}
	for i, h := range rows[0] {
		idx[normalizeHeader(h)] = i
	}
	pick := func(row []string, names ...string) string {
		for _, n := range names {
			if i, ok := idx[normalizeHeader(n)]; ok && i < len(row) {
				return strings.TrimSpace(row[i])
			}
		}
		return ""
	}
	out := make([]Result, 0, len(rows)-1)
	for _, row := range rows[1:] {
		ip := pick(row, "IP 地址", "IP")
		if ip == "" {
			continue
		}
		port, _ := strconv.Atoi(pick(row, "端口", "port"))
		// 旧格式可能把端口写在 IP 里
		if h, p, ok := ParseProxyLine(ip); ok {
			ip = h
			if port <= 0 {
				port = p
			}
		}
		if port <= 0 {
			port = 443
		}
		speed, _ := strconv.ParseFloat(pick(row, "下载速度(MB/s)", "下载速度 (MB/s)", "下载速度"), 64)
		delay, _ := strconv.ParseFloat(pick(row, "平均延迟", "延迟", "latency"), 64)
		loss, _ := strconv.ParseFloat(pick(row, "丢包率"), 64)
		sent, _ := strconv.Atoi(pick(row, "已发送"))
		recv, _ := strconv.Atoi(pick(row, "已接收"))
		colo := pick(row, "地区码")
		if colo == "N/A" {
			colo = ""
		}
		out = append(out, Result{
			IP: ip, Port: port, Sent: sent, Received: recv,
			LossRate: loss, Delay: delay, Speed: speed,
			Colo: colo, ColoName: ColoName(colo),
		})
	}
	return out, nil
}

// hasIPColumn 判断首行是不是带 ip 列的表头。
// FOFA 这类资产导出的表头是全小写的 host,ip,port，
// 本工具导出的是 "IP 地址,...,端口"，都要认出来。
func hasIPColumn(header string) bool {
	if !strings.Contains(header, ",") {
		return false
	}
	for _, f := range strings.Split(header, ",") {
		switch normalizeHeader(f) {
		case "ip", "ip地址":
			return true
		}
	}
	return false
}

// ParseProxySource 解析用户贴进来的一段文本，可能是带表头的 CSV，
// 也可能是每行 IP:端口 的裸列表。两种都接受，省得用户自己分辨格式。
// CSV 只认 ip 与 port 两列，其余列（host、title、protocol 这些）一概不看。
func ParseProxySource(text string) ([]Result, error) {
	text = strings.TrimSpace(text)
	if text == "" {
		return nil, fmt.Errorf("内容是空的")
	}
	// 带表头的按 CSV 解析，能保住速度、地区这些列
	first := text
	if i := strings.IndexAny(first, "\r\n"); i >= 0 {
		first = first[:i]
	}
	if hasIPColumn(first) {
		if rs, err := parseCSVText(text); err == nil && len(rs) > 0 {
			return rs, nil
		}
	}
	var out []Result
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		// 允许 GitHub 那种 IP:端口#备注 的写法
		if i := strings.IndexByte(line, '#'); i >= 0 {
			line = strings.TrimSpace(line[:i])
		}
		ip, port, ok := ParseProxyLine(line)
		if !ok {
			continue
		}
		out = append(out, Result{IP: ip, Port: port})
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("没解析出可用的 IP，每行应是 IP 或 IP:端口")
	}
	return out, nil
}

// ProxyListFromCSV 从任意测速结果 CSV 生成反代列表。
// 沿用旧 Python 版的优选反代流程：外部拿到的 CSV（别人分享的结果、
// 上一轮测速的存档）先提取出 IP:端口，再拿这份列表当输入源重测一遍。
func ProxyListFromCSV(csvPath, outPath string, limit int) (int, error) {
	rs, err := ReadCSV(csvPath)
	if err != nil || len(rs) == 0 {
		// 来源也可能是每行 IP:端口 的纯列表（别人分享的多是这种），
		// 按 CSV 读不出来就退回文本解析，与界面的导入行为保持一致
		data, readErr := os.ReadFile(DataPath(csvPath))
		if readErr != nil {
			if err != nil {
				return 0, err
			}
			return 0, fmt.Errorf("%s 里没有可用的 IP", csvPath)
		}
		rs, err = ParseProxySource(string(data))
		if err != nil {
			return 0, err
		}
	}
	return WriteProxyList(outPath, rs, limit)
}

// WriteProxyList 生成 IP:端口 格式的反代列表
func WriteProxyList(path string, rs []Result, limit int) (int, error) {
	if path == "" {
		path = ProxyListFile
	}
	if limit > 0 && limit < len(rs) {
		rs = rs[:limit]
	}
	f, err := os.Create(DataPath(path))
	if err != nil {
		return 0, err
	}
	defer f.Close()
	for _, r := range rs {
		port := r.Port
		if port <= 0 {
			port = 443
		}
		if _, err := fmt.Fprintf(f, "%s:%d\n", r.IP, port); err != nil {
			return 0, err
		}
	}
	return len(rs), nil
}
