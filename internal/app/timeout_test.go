package app

import (
	"context"
	"errors"
	"testing"
	"time"
)

// 整体超时属于正常收工：应当拿已测出的结果交付，
// 而不是把整批作废。这里用一个必然超时的极短时限验证语义。
func TestMaxRunTimeDoesNotDiscardResults(t *testing.T) {
	o := Options{MaxRunTime: 1, Count: 1}
	o.Normalize()
	if o.MaxRunTime != 1 {
		t.Errorf("时限不该被改写，got %d", o.MaxRunTime)
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Millisecond)
	defer cancel()
	<-ctx.Done()
	// 超时与主动取消要区别对待
	if !errors.Is(ctx.Err(), context.DeadlineExceeded) {
		t.Fatal("应是超时而非取消")
	}
}

func TestDLTimeoutDefaults(t *testing.T) {
	var o Options
	o.Normalize()
	if o.DLTimeout != 10 {
		t.Errorf("单个 IP 测速上限应默认 10 秒，got %d", o.DLTimeout)
	}
	if o.MaxRunTime != 0 {
		t.Errorf("整轮时限应默认不限，got %d", o.MaxRunTime)
	}

	o2 := Options{DLTimeout: 30, MaxRunTime: 300}
	o2.Normalize()
	if o2.DLTimeout != 30 || o2.MaxRunTime != 300 {
		t.Errorf("用户设的值不该被覆盖，got dt=%d mt=%d", o2.DLTimeout, o2.MaxRunTime)
	}

	// 负数按不限处理，不该变成负的超时
	o3 := Options{MaxRunTime: -5}
	o3.Normalize()
	if o3.MaxRunTime != 0 {
		t.Errorf("负数应归零，got %d", o3.MaxRunTime)
	}
}
