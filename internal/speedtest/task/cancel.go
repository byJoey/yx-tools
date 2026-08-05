package task

import "context"

// 测速内核以包级变量传参，取消信号沿用同一风格。
// 延迟与下载测速的派发循环会检查它，让用户点「停止」后能立即收手，
// 而不必等几千个 IP 全部探测完。
var runCtx context.Context

// SetContext 设置本次测速的取消信号，传 nil 表示不可取消
func SetContext(ctx context.Context) { runCtx = ctx }

// Canceled 报告本次测速是否已被取消
func Canceled() bool {
	if runCtx == nil {
		return false
	}
	return runCtx.Err() != nil
}

func canceled() bool { return Canceled() }
