package app

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

var httpClient = &http.Client{Timeout: 30 * time.Second}

// APITarget 描述 cfnew 的优选 IP 接口位置
type APITarget struct {
	Domain string // Worker 域名，如 example.workers.dev
	UUID   string // UUID 或自定义路径
}

func (t APITarget) url() string {
	d := strings.TrimSpace(t.Domain)
	scheme := "https"
	// 允许显式指定 http，主要用于本地或内网自建
	if strings.HasPrefix(strings.ToLower(d), "http://") {
		scheme = "http"
		d = d[len("http://"):]
	} else if strings.HasPrefix(strings.ToLower(d), "https://") {
		d = d[len("https://"):]
	}
	d = strings.TrimSuffix(d, "/")
	// 去掉可能带上的路径部分
	if i := strings.Index(d, "/"); i >= 0 {
		d = d[:i]
	}
	u := strings.Trim(strings.TrimSpace(t.UUID), "/")
	return fmt.Sprintf("%s://%s/%s/api/preferred-ips", scheme, d, u)
}

type apiItem struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
	Name string `json:"name"`
}

// CountRemoteIPs 查询远端已有的优选 IP 数量
func CountRemoteIPs(ctx context.Context, t APITarget) (int, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, t.url(), nil)
	if err != nil {
		return 0, err
	}
	resp, err := httpClient.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("HTTP %d: %s", resp.StatusCode, truncate(string(body), 160))
	}
	var out struct {
		Count int `json:"count"`
	}
	_ = json.Unmarshal(body, &out)
	return out.Count, nil
}

// ClearRemoteIPs 清空远端优选 IP
func ClearRemoteIPs(ctx context.Context, t APITarget) error {
	payload, _ := json.Marshal(map[string]bool{"all": true})
	req, err := http.NewRequestWithContext(ctx, http.MethodDelete, t.url(), bytes.NewReader(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("清空失败 HTTP %d: %s", resp.StatusCode, truncate(string(body), 160))
	}
	return nil
}

// UploadToAPI 批量上报优选 IP 到 cfnew
func UploadToAPI(ctx context.Context, t APITarget, rs []Result, limit int, clear bool) (int, error) {
	if strings.TrimSpace(t.Domain) == "" || strings.TrimSpace(t.UUID) == "" {
		return 0, fmt.Errorf("请先填写 Worker 域名和 UUID")
	}
	if limit > 0 && limit < len(rs) {
		rs = rs[:limit]
	}
	if len(rs) == 0 {
		return 0, fmt.Errorf("没有可上传的结果")
	}
	if clear {
		if err := ClearRemoteIPs(ctx, t); err != nil {
			return 0, err
		}
	}
	items := make([]apiItem, 0, len(rs))
	for _, r := range rs {
		port := r.Port
		if port <= 0 {
			port = 443
		}
		items = append(items, apiItem{IP: r.IP, Port: port, Name: nodeName(r)})
	}
	payload, err := json.Marshal(items)
	if err != nil {
		return 0, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, t.url(), bytes.NewReader(payload))
	if err != nil {
		return 0, err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := httpClient.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return 0, fmt.Errorf("上传失败 HTTP %d: %s", resp.StatusCode, truncate(string(body), 200))
	}
	return len(items), nil
}

// nodeName 生成节点备注，如「香港-12ms」
func nodeName(r Result) string {
	name := ColoName(r.Colo)
	if r.Delay > 0 {
		return fmt.Sprintf("%s-%.0fms", name, r.Delay)
	}
	return name
}

// GitHubTarget 描述 GitHub 上传位置
type GitHubTarget struct {
	Repo  string // owner/repo
	Token string
	Path  string // 仓库内文件路径
}

// UploadToGitHub 把优选列表写入 GitHub 仓库，已存在则更新
func UploadToGitHub(ctx context.Context, t GitHubTarget, rs []Result, limit int) (int, error) {
	repo := strings.Trim(strings.TrimSpace(t.Repo), "/")
	if repo == "" || strings.TrimSpace(t.Token) == "" {
		return 0, fmt.Errorf("请先填写 GitHub 仓库和 Token")
	}
	if !strings.Contains(repo, "/") {
		return 0, fmt.Errorf("仓库格式应为 owner/repo")
	}
	path := strings.TrimSpace(t.Path)
	if path == "" {
		path = "cloudflare_ips.txt"
	}
	if limit > 0 && limit < len(rs) {
		rs = rs[:limit]
	}
	if len(rs) == 0 {
		return 0, fmt.Errorf("没有可上传的结果")
	}

	var sb strings.Builder
	for _, r := range rs {
		port := r.Port
		if port <= 0 {
			port = 443
		}
		fmt.Fprintf(&sb, "%s:%d#%s\n", r.IP, port, nodeName(r))
	}
	content := base64.StdEncoding.EncodeToString([]byte(sb.String()))
	api := fmt.Sprintf("https://api.github.com/repos/%s/contents/%s", repo, path)

	// 已存在则需要带上 sha 才能更新
	sha := ""
	{
		req, _ := http.NewRequestWithContext(ctx, http.MethodGet, api, nil)
		req.Header.Set("Authorization", "Bearer "+t.Token)
		req.Header.Set("Accept", "application/vnd.github+json")
		if resp, err := httpClient.Do(req); err == nil {
			defer resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				var meta struct {
					SHA string `json:"sha"`
				}
				b, _ := io.ReadAll(resp.Body)
				_ = json.Unmarshal(b, &meta)
				sha = meta.SHA
			}
		}
	}

	payload := map[string]string{
		"message": fmt.Sprintf("更新优选 IP (%d 个) %s", len(rs), time.Now().Format("2006-01-02 15:04")),
		"content": content,
	}
	if sha != "" {
		payload["sha"] = sha
	}
	body, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, http.MethodPut, api, bytes.NewReader(body))
	if err != nil {
		return 0, err
	}
	req.Header.Set("Authorization", "Bearer "+t.Token)
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("Content-Type", "application/json")
	resp, err := httpClient.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	rb, _ := io.ReadAll(resp.Body)
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return 0, fmt.Errorf("GitHub 上传失败 HTTP %d: %s", resp.StatusCode, truncate(string(rb), 200))
	}
	return len(rs), nil
}

func truncate(s string, n int) string {
	s = strings.TrimSpace(s)
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}
