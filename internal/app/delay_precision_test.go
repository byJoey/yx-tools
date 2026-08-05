package app

import (
	"net"
	"testing"
	"time"

	"github.com/byJoey/yx-tools/internal/speedtest/utils"
)

func mustIP(s string) *net.IPAddr { return &net.IPAddr{IP: net.ParseIP(s)} }

// 亚毫秒握手曾被 Duration.Milliseconds() 整数截断成 0，
// 表现为「明明连得通、下载也有速度，延迟却是 0」。
func TestDelaySubMillisecondNotZero(t *testing.T) {
	cases := []struct {
		name string
		in   time.Duration
		min  float64
	}{
		{"亚毫秒不归零", 430 * time.Microsecond, 0.4},
		{"半毫秒", 500 * time.Microsecond, 0.49},
		{"正常毫秒级", 47 * time.Millisecond, 46.9},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			set := utils.DownloadSpeedSet{{
				PingData: &utils.PingData{
					IP: mustIP("1.1.1.1"), Sended: 4, Received: 4, Delay: c.in,
				},
			}}
			out := toResults(set)
			if len(out) != 1 {
				t.Fatalf("want 1 result, got %d", len(out))
			}
			if out[0].Delay < c.min {
				t.Fatalf("延迟被截断: want >= %v, got %v", c.min, out[0].Delay)
			}
		})
	}
}
