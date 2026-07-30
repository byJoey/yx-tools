package app

import (
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"io/fs"
	"net/http"
	"time"
)

//go:embed all:web
var webFS embed.FS

// Server 提供 Web 图形界面与 REST 接口
type Server struct {
	runner *Runner
	mux    *http.ServeMux
}

// NewServer 构造 Web 服务
func NewServer() *Server {
	s := &Server{runner: NewRunner(), mux: http.NewServeMux()}
	s.routes()
	return s
}

func (s *Server) routes() {
	sub, err := fs.Sub(webFS, "web")
	if err == nil {
		s.mux.Handle("/", http.FileServer(http.FS(sub)))
	}
	s.mux.HandleFunc("/api/colos", s.handleColos)
	s.mux.HandleFunc("/api/config", s.handleConfig)
	s.mux.HandleFunc("/api/status", s.handleStatus)
	s.mux.HandleFunc("/api/start", s.handleStart)
	s.mux.HandleFunc("/api/cancel", s.handleCancel)
	s.mux.HandleFunc("/api/events", s.handleEvents)
	s.mux.HandleFunc("/api/results", s.handleResults)
	s.mux.HandleFunc("/api/proxy-list", s.handleProxyList)
	s.mux.HandleFunc("/api/upload/api", s.handleUploadAPI)
	s.mux.HandleFunc("/api/upload/github", s.handleUploadGitHub)
}

// ServeHTTP 实现 http.Handler
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) { s.mux.ServeHTTP(w, r) }

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func (s *Server) handleColos(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, Colos)
}

func (s *Server) handleConfig(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		c := LoadConfig()
		// 凭据只回传是否已设置，不回显明文
		writeJSON(w, http.StatusOK, map[string]any{
			"worker_domain":    c.WorkerDomain,
			"uuid":             c.UUID,
			"github_repo":      c.GitHubRepo,
			"github_path":      c.GitHubPath,
			"has_github_token": c.GitHubToken != "",
			"colo":             c.Colo,
			"ipv6":             c.IPv6,
			"count":            c.Count,
			"speed_limit":      c.SpeedLimit,
			"delay_limit":      c.DelayLimit,
			"threads":          c.Threads,
			"test_url":         c.TestURL,
			"port":             c.Port,
		})
	case http.MethodPost:
		cur := LoadConfig()
		var in struct {
			WorkerDomain *string  `json:"worker_domain"`
			UUID         *string  `json:"uuid"`
			GitHubToken  *string  `json:"github_token"`
			GitHubRepo   *string  `json:"github_repo"`
			GitHubPath   *string  `json:"github_path"`
			Colo         *string  `json:"colo"`
			IPv6         *bool    `json:"ipv6"`
			Count        *int     `json:"count"`
			SpeedLimit   *float64 `json:"speed_limit"`
			DelayLimit   *int     `json:"delay_limit"`
			Threads      *int     `json:"threads"`
			TestURL      *string  `json:"test_url"`
			Port         *int     `json:"port"`
		}
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeErr(w, http.StatusBadRequest, "请求格式错误")
			return
		}
		if in.WorkerDomain != nil {
			cur.WorkerDomain = *in.WorkerDomain
		}
		if in.UUID != nil {
			cur.UUID = *in.UUID
		}
		if in.GitHubToken != nil && *in.GitHubToken != "" {
			cur.GitHubToken = *in.GitHubToken
		}
		if in.GitHubRepo != nil {
			cur.GitHubRepo = *in.GitHubRepo
		}
		if in.GitHubPath != nil {
			cur.GitHubPath = *in.GitHubPath
		}
		if in.Colo != nil {
			cur.Colo = *in.Colo
		}
		if in.IPv6 != nil {
			cur.IPv6 = *in.IPv6
		}
		if in.Count != nil {
			cur.Count = *in.Count
		}
		if in.SpeedLimit != nil {
			cur.SpeedLimit = *in.SpeedLimit
		}
		if in.DelayLimit != nil {
			cur.DelayLimit = *in.DelayLimit
		}
		if in.Threads != nil {
			cur.Threads = *in.Threads
		}
		if in.TestURL != nil {
			cur.TestURL = *in.TestURL
		}
		if in.Port != nil {
			cur.Port = *in.Port
		}
		if err := SaveConfig(cur); err != nil {
			writeErr(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
	case http.MethodDelete:
		if err := ClearConfig(); err != nil {
			writeErr(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
	default:
		writeErr(w, http.StatusMethodNotAllowed, "不支持的方法")
	}
}

func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"running": s.runner.Running(),
		"count":   len(s.runner.Results()),
	})
}

func (s *Server) handleStart(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "请用 POST")
		return
	}
	var o Options
	if err := json.NewDecoder(r.Body).Decode(&o); err != nil {
		writeErr(w, http.StatusBadRequest, "请求格式错误")
		return
	}
	if !s.runner.Start(o) {
		writeErr(w, http.StatusConflict, "已有测速任务在运行")
		return
	}
	// 记住这次参数，下次打开界面自动回填
	c := LoadConfig()
	c.Colo, c.IPv6, c.Count = o.Colo, o.IPv6, o.Count
	c.SpeedLimit, c.DelayLimit, c.Threads = o.SpeedLimit, o.DelayLimit, o.Threads
	c.TestURL, c.Port = o.TestURL, o.Port
	_ = SaveConfig(c)
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (s *Server) handleCancel(w http.ResponseWriter, r *http.Request) {
	s.runner.Cancel()
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (s *Server) handleEvents(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		writeErr(w, http.StatusInternalServerError, "服务端不支持流式输出")
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.WriteHeader(http.StatusOK)
	flusher.Flush()

	ch, unsub := s.runner.Subscribe()
	defer unsub()
	ping := time.NewTicker(20 * time.Second)
	defer ping.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case <-ping.C:
			fmt.Fprint(w, ": ping\n\n")
			flusher.Flush()
		case e, ok := <-ch:
			if !ok {
				return
			}
			b, err := json.Marshal(e)
			if err != nil {
				continue
			}
			fmt.Fprintf(w, "data: %s\n\n", b)
			flusher.Flush()
		}
	}
}

func (s *Server) handleResults(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.runner.Results())
}

func (s *Server) handleProxyList(w http.ResponseWriter, r *http.Request) {
	var in struct {
		Limit int `json:"limit"`
	}
	_ = json.NewDecoder(r.Body).Decode(&in)
	rs := s.runner.Results()
	if len(rs) == 0 {
		var err error
		if rs, err = ReadCSV(ResultFile); err != nil {
			writeErr(w, http.StatusBadRequest, "没有可用的测速结果")
			return
		}
	}
	n, err := WriteProxyList(ProxyListFile, rs, in.Limit)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"count": n, "file": ProxyListFile})
}

func (s *Server) resultsOrCSV(w http.ResponseWriter) ([]Result, bool) {
	rs := s.runner.Results()
	if len(rs) > 0 {
		return rs, true
	}
	rs, err := ReadCSV(ResultFile)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "没有可用的测速结果")
		return nil, false
	}
	return rs, true
}

func (s *Server) handleUploadAPI(w http.ResponseWriter, r *http.Request) {
	var in struct {
		Domain string `json:"worker_domain"`
		UUID   string `json:"uuid"`
		Limit  int    `json:"limit"`
		Clear  bool   `json:"clear"`
	}
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		writeErr(w, http.StatusBadRequest, "请求格式错误")
		return
	}
	c := LoadConfig()
	if in.Domain == "" {
		in.Domain = c.WorkerDomain
	}
	if in.UUID == "" {
		in.UUID = c.UUID
	}
	rs, ok := s.resultsOrCSV(w)
	if !ok {
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 60*time.Second)
	defer cancel()
	n, err := UploadToAPI(ctx, APITarget{Domain: in.Domain, UUID: in.UUID}, rs, in.Limit, in.Clear)
	if err != nil {
		writeErr(w, http.StatusBadGateway, err.Error())
		return
	}
	c.WorkerDomain, c.UUID = in.Domain, in.UUID
	_ = SaveConfig(c)
	writeJSON(w, http.StatusOK, map[string]any{"count": n})
}

func (s *Server) handleUploadGitHub(w http.ResponseWriter, r *http.Request) {
	var in struct {
		Repo  string `json:"repo"`
		Token string `json:"token"`
		Path  string `json:"path"`
		Limit int    `json:"limit"`
	}
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		writeErr(w, http.StatusBadRequest, "请求格式错误")
		return
	}
	c := LoadConfig()
	if in.Repo == "" {
		in.Repo = c.GitHubRepo
	}
	if in.Token == "" {
		in.Token = c.GitHubToken
	}
	if in.Path == "" {
		in.Path = c.GitHubPath
	}
	rs, ok := s.resultsOrCSV(w)
	if !ok {
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 60*time.Second)
	defer cancel()
	n, err := UploadToGitHub(ctx, GitHubTarget{Repo: in.Repo, Token: in.Token, Path: in.Path}, rs, in.Limit)
	if err != nil {
		writeErr(w, http.StatusBadGateway, err.Error())
		return
	}
	c.GitHubRepo, c.GitHubToken, c.GitHubPath = in.Repo, in.Token, in.Path
	_ = SaveConfig(c)
	writeJSON(w, http.StatusOK, map[string]any{"count": n})
}
