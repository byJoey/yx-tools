package app

import (
	"context"
	"sync"
	"time"
)

// Event 是推送给界面的一条运行事件
type Event struct {
	Type     string   `json:"type"` // progress / log / done / error
	Stage    string   `json:"stage,omitempty"`
	Message  string   `json:"message,omitempty"`
	Current  int      `json:"current,omitempty"`
	Total    int      `json:"total,omitempty"`
	Results  []Result `json:"results,omitempty"`
	Result   *Result  `json:"result,omitempty"` // 下载测速逐条出结果时带上
	Finished bool     `json:"finished"`
	At       int64    `json:"at"`
}

// Runner 串行调度测速任务，并把过程广播给所有订阅者
type Runner struct {
	mu       sync.RWMutex
	running  bool
	cancel   context.CancelFunc
	history  []Event
	results  []Result
	subs     map[chan Event]struct{}
	lastOpts Options
}

// NewRunner 创建调度器
func NewRunner() *Runner {
	return &Runner{subs: make(map[chan Event]struct{})}
}

// Subscribe 订阅事件流，返回通道与退订函数；已有历史会先回放
func (r *Runner) Subscribe() (<-chan Event, func()) {
	ch := make(chan Event, 64)
	r.mu.Lock()
	for _, e := range r.history {
		select {
		case ch <- e:
		default:
		}
	}
	r.subs[ch] = struct{}{}
	r.mu.Unlock()
	return ch, func() {
		r.mu.Lock()
		if _, ok := r.subs[ch]; ok {
			delete(r.subs, ch)
			close(ch)
		}
		r.mu.Unlock()
	}
}

func (r *Runner) broadcast(e Event) {
	e.At = time.Now().UnixMilli()
	r.mu.Lock()
	r.history = append(r.history, e)
	if len(r.history) > 200 {
		r.history = r.history[len(r.history)-200:]
	}
	// 逐条结果同时累积到 results，这样中途刷新页面也能
	// 通过 /api/results 拿到已经测出来的部分
	if e.Type == "result" && e.Result != nil {
		r.results = append(r.results, *e.Result)
	}
	for ch := range r.subs {
		select {
		case ch <- e:
		default: // 订阅者太慢就丢事件，不阻塞测速
		}
	}
	r.mu.Unlock()
}

// Running 返回是否有任务在跑
func (r *Runner) Running() bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.running
}

// Results 返回最近一次测速结果
func (r *Runner) Results() []Result {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]Result, len(r.results))
	copy(out, r.results)
	return out
}

// LastStage 返回最近一次进度事件的阶段名
func (r *Runner) LastStage() string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	for i := len(r.history) - 1; i >= 0; i-- {
		if r.history[i].Stage != "" {
			return r.history[i].Stage
		}
	}
	return ""
}

// LastOptions 返回最近一次使用的参数
func (r *Runner) LastOptions() Options {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.lastOpts
}

// Start 启动一次测速；已有任务在跑时返回 false
func (r *Runner) Start(o Options) bool {
	r.mu.Lock()
	if r.running {
		r.mu.Unlock()
		return false
	}
	ctx, cancel := context.WithCancel(context.Background())
	r.running = true
	r.cancel = cancel
	r.history = nil
	r.results = nil // 上一轮的结果别串到这一轮
	r.lastOpts = o
	r.mu.Unlock()

	go func() {
		defer func() {
			r.mu.Lock()
			r.running = false
			r.cancel = nil
			r.mu.Unlock()
			cancel()
		}()
		rs, err := Run(ctx, o, func(p Progress) {
			if p.Result != nil {
				// 单条结果单独发一种事件，前端可以立刻插进表格
				r.broadcast(Event{Type: "result", Stage: p.Stage, Result: p.Result})
				return
			}
			r.broadcast(Event{Type: "progress", Stage: p.Stage, Message: p.Message, Current: p.Current, Total: p.Total})
		})
		if err != nil {
			if ctx.Err() != nil {
				r.broadcast(Event{Type: "error", Message: "已取消", Finished: true})
				return
			}
			r.broadcast(Event{Type: "error", Message: err.Error(), Finished: true})
			return
		}
		r.mu.Lock()
		r.results = rs
		r.mu.Unlock()
		if err := WriteCSV(ResultFile, rs); err != nil {
			r.broadcast(Event{Type: "log", Message: "结果写入失败: " + err.Error()})
		}
		r.broadcast(Event{Type: "done", Message: "测速完成", Results: rs, Total: len(rs), Current: len(rs), Finished: true})
	}()
	return true
}

// Cancel 取消当前任务
func (r *Runner) Cancel() {
	r.mu.RLock()
	c := r.cancel
	r.mu.RUnlock()
	if c != nil {
		c()
	}
}
