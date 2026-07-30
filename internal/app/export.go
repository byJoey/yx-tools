package app

import (
	"encoding/csv"
	"fmt"
	"os"
	"strconv"
)

var csvHeader = []string{"IP 地址", "已发送", "已接收", "丢包率", "平均延迟", "下载速度(MB/s)", "地区码", "端口"}

// WriteCSV 导出测速结果，列顺序与测速内核保持一致
func WriteCSV(path string, rs []Result) error {
	if path == "" {
		path = ResultFile
	}
	f, err := os.Create(path)
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
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	rows, err := r.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(rows) < 2 {
		return nil, fmt.Errorf("%s 没有数据", path)
	}
	idx := map[string]int{}
	for i, h := range rows[0] {
		idx[h] = i
	}
	pick := func(row []string, names ...string) string {
		for _, n := range names {
			if i, ok := idx[n]; ok && i < len(row) {
				return row[i]
			}
		}
		return ""
	}
	out := make([]Result, 0, len(rows)-1)
	for _, row := range rows[1:] {
		ip := pick(row, "IP 地址", "IP", "ip")
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

// WriteProxyList 生成 IP:端口 格式的反代列表
func WriteProxyList(path string, rs []Result, limit int) (int, error) {
	if path == "" {
		path = ProxyListFile
	}
	if limit > 0 && limit < len(rs) {
		rs = rs[:limit]
	}
	f, err := os.Create(path)
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
