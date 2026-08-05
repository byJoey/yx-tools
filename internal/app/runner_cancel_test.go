package app

import (
	"context"
	"testing"
	"time"

	"github.com/byJoey/yx-tools/internal/speedtest/task"
)

func newCancelableCtx() (context.Context, context.CancelFunc) {
	return context.WithCancel(context.Background())
}

// 点「停止」后，内核的派发循环必须立刻收手，
// 而不是把剩下几千个候选 IP 全部探测完。
// 这里直接验证取消信号本身，不打真实网络：
// 用真实测速会瞬间占掉上万个本地临时端口，拖垮同包其它用例。
func TestKernelStopsDispatchingOnCancel(t *testing.T) {
	defer task.SetContext(nil)

	ctx, cancel := newCancelableCtx()
	task.SetContext(ctx)
	if task.Canceled() {
		t.Fatal("刚设置就报已取消")
	}
	cancel()
	if !task.Canceled() {
		t.Fatal("取消后应立刻反映出来")
	}

	// 不设 context 时不能误判成已取消，否则测速根本跑不起来
	task.SetContext(nil)
	if task.Canceled() {
		t.Fatal("未设置 context 时不应报已取消")
	}
}

// 取消信号要能在派发循环里被及时看到
func TestCancelObservedQuickly(t *testing.T) {
	defer task.SetContext(nil)
	ctx, cancel := newCancelableCtx()
	task.SetContext(ctx)

	go func() {
		time.Sleep(50 * time.Millisecond)
		cancel()
	}()

	start := time.Now()
	for !task.Canceled() {
		if time.Since(start) > 5*time.Second {
			t.Fatal("5 秒内没观察到取消信号")
		}
		time.Sleep(5 * time.Millisecond)
	}
	if d := time.Since(start); d > time.Second {
		t.Fatalf("取消响应太慢: %v", d)
	}
}
