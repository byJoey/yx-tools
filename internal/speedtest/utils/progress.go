package utils

import (
	"fmt"
	"io"

	"github.com/cheggaaa/pb/v3"
)

// Quiet 为真时不输出进度条，供图形界面等场景静默运行
var Quiet bool

type Bar struct {
	pb *pb.ProgressBar
}

func NewBar(count int, MyStrStart, MyStrEnd string) *Bar {
	tmpl := fmt.Sprintf(`{{counters . }} {{ bar . "[" "-" (cycle . "↖" "↗" "↘" "↙" ) "_" "]"}} %s {{string . "MyStr" | green}} %s `, MyStrStart, MyStrEnd)
	bar := pb.ProgressBarTemplate(tmpl).New(count)
	if Quiet {
		bar.SetWriter(io.Discard)
	}
	bar.Start()
	return &Bar{pb: bar}
}

func (b *Bar) Grow(num int, MyStrVal string) {
	b.pb.Set("MyStr", MyStrVal).Add(num)
}

func (b *Bar) Done() {
	b.pb.Finish()
}
