package app

import (
	"testing"
	"time"
)

// 点「停止」后必须很快真正停下来，而不是等几千个 IP 全部探测完。
// 候选池越大这个差别越明显，所以直接用穷举模式压测。
func TestRunnerCancelStopsQuickly(t *testing.T) {
	if testing.Short() {
		t.Skip("需要联网")
	}
	r := NewRunner()
	if !r.Start(Options{
		SampleSize: 0,
		TestAll:    true,
		Count:      10,
		DelayLimit: 3000,
		Threads:    100,
	}) {
		t.Fatal("任务没能启动")
	}

	// 等它真正进入延迟测速阶段
	deadline := time.Now().Add(90 * time.Second)
	for time.Now().Before(deadline) {
		if !r.Running() {
			for _, e := range r.history {
				t.Logf("事件 %s: %s", e.Type, e.Message)
			}
			t.Fatal("任务提前结束")
		}
		if st := r.LastStage(); st == "ping" {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}
	time.Sleep(3 * time.Second)
	if !r.Running() {
		t.Fatal("任务还没跑起来就结束了")
	}

	start := time.Now()
	r.Cancel()
	for r.Running() {
		if time.Since(start) > 30*time.Second {
			t.Fatalf("取消后 %v 仍在运行", time.Since(start))
		}
		time.Sleep(100 * time.Millisecond)
	}
	t.Logf("取消耗时 %v", time.Since(start))
}
