package utils

import (
	"fmt"
	"io"

	"github.com/cheggaaa/pb/v3"
)

// Quiet 为真时不输出进度条，供图形界面等场景静默运行
var Quiet bool

// OnProgress 在进度推进时被调用，供图形界面把进度转成事件推给前端。
// 内核所有进度都经由 Bar.Grow，挂在这里就能覆盖延迟与下载两个阶段。
var OnProgress func(current, total int)

type Bar struct {
	pb    *pb.ProgressBar
	total int
	cur   int
}

func NewBar(count int, MyStrStart, MyStrEnd string) *Bar {
	tmpl := fmt.Sprintf(`{{counters . }} {{ bar . "[" "-" (cycle . "↖" "↗" "↘" "↙" ) "_" "]"}} %s {{string . "MyStr" | green}} %s `, MyStrStart, MyStrEnd)
	bar := pb.ProgressBarTemplate(tmpl).New(count)
	if Quiet {
		bar.SetWriter(io.Discard)
	}
	bar.Start()
	return &Bar{pb: bar, total: count}
}

func (b *Bar) Grow(num int, MyStrVal string) {
	b.pb.Set("MyStr", MyStrVal).Add(num)
	b.cur += num
	if OnProgress != nil {
		OnProgress(b.cur, b.total)
	}
}

func (b *Bar) Done() {
	b.pb.Finish()
}
