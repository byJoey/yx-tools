package app

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func makeResults(n int) []Result {
	out := make([]Result, 0, n)
	for i := 0; i < n; i++ {
		out = append(out, Result{IP: "1.1.1." + string(rune('0'+i%10)), Port: 443, Speed: 5, Colo: "HKG"})
	}
	return out
}

// 上报数量留空（0）时应全部上传，而不是悄悄截成 10 条
func TestUploadLimitZeroSendsAll(t *testing.T) {
	var got int
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			var items []apiItem
			_ = json.NewDecoder(r.Body).Decode(&items)
			got = len(items)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"success":true}`))
	}))
	defer srv.Close()

	target := APITarget{Domain: "http://" + srv.Listener.Addr().String(), UUID: "u"}
	cases := []struct {
		name  string
		limit int
		total int
		want  int
	}{
		{"留空传全部", 0, 25, 25},
		{"负数也当全部", -1, 25, 25},
		{"指定数量则截断", 10, 25, 10},
		{"指定数超过总数不补", 50, 25, 25},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got = 0
			n, err := UploadToAPI(context.Background(), target, makeResults(c.total), c.limit, false)
			if err != nil {
				t.Fatal(err)
			}
			if n != c.want || got != c.want {
				t.Fatalf("want %d, 返回 %d, 实际发出 %d", c.want, n, got)
			}
		})
	}
}

// 节点名沿用旧 Python 版格式：地区名-速度MB/s
func TestNodeName(t *testing.T) {
	cases := []struct {
		in   Result
		want string
	}{
		{Result{Colo: "HKG", Speed: 8.34}, "香港-8.34MB/s"},
		{Result{Colo: "", Speed: 0}, "未知地区-0.00MB/s"},
		{Result{Colo: "ZZZ", Speed: 1.5}, "ZZZ-1.50MB/s"},
	}
	for _, c := range cases {
		if got := nodeName(c.in); got != c.want {
			t.Fatalf("want %q, got %q", c.want, got)
		}
	}
}
