package task

import "fmt"

// FatalError 是内核在无法继续时抛出的错误。
// 内核原本直接 log.Fatal（os.Exit），跑在 Web 服务里会连带杀掉整个进程，
// 用户只是填错一个文件名就得重启服务。改成 panic 后由调用方 recover 成普通错误。
type FatalError struct {
	Msg string
}

func (e *FatalError) Error() string { return e.Msg }

func fatalf(format string, args ...any) {
	panic(&FatalError{Msg: fmt.Sprintf(format, args...)})
}
