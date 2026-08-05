package task

import (
	"net"
	"testing"
)

func makeIPs(n int) []*net.IPAddr {
	out := make([]*net.IPAddr, 0, n)
	for i := 0; i < n; i++ {
		out = append(out, &net.IPAddr{IP: net.IPv4(10, byte(i>>16), byte(i>>8), byte(i))})
	}
	return out
}

func TestSampleIPs(t *testing.T) {
	InitRandSeed()
	defer func() { SampleSize = 0 }()

	t.Run("不限时原样返回", func(t *testing.T) {
		SampleSize = 0
		if got := len(sampleIPs(makeIPs(500))); got != 500 {
			t.Fatalf("want 500, got %d", got)
		}
	})

	t.Run("候选不足时不补也不裁", func(t *testing.T) {
		SampleSize = 800
		if got := len(sampleIPs(makeIPs(500))); got != 500 {
			t.Fatalf("want 500, got %d", got)
		}
	})

	t.Run("超出时裁到指定数量", func(t *testing.T) {
		SampleSize = 100
		if got := len(sampleIPs(makeIPs(4000))); got != 100 {
			t.Fatalf("want 100, got %d", got)
		}
	})

	t.Run("抽样结果不重复", func(t *testing.T) {
		SampleSize = 300
		got := sampleIPs(makeIPs(4000))
		seen := make(map[string]bool, len(got))
		for _, ip := range got {
			if seen[ip.String()] {
				t.Fatalf("重复 IP: %s", ip)
			}
			seen[ip.String()] = true
		}
	})

	// 顺序截取会让结果永远落在前几个段，这里确认确实是随机
	t.Run("抽样覆盖整个候选池", func(t *testing.T) {
		SampleSize = 200
		got := sampleIPs(makeIPs(4000))
		back := 0
		for _, ip := range got {
			// 索引大于 2000 的那一半
			if int(ip.IP.To4()[1])<<16|int(ip.IP.To4()[2])<<8|int(ip.IP.To4()[3]) >= 2000 {
				back++
			}
		}
		if back == 0 {
			t.Fatal("抽样全部来自前半段，不是随机")
		}
	})

	t.Run("两次抽样结果不同", func(t *testing.T) {
		SampleSize = 50
		a := sampleIPs(makeIPs(4000))
		b := sampleIPs(makeIPs(4000))
		same := 0
		for i := range a {
			if a[i].String() == b[i].String() {
				same++
			}
		}
		if same == len(a) {
			t.Fatal("两次抽样完全相同")
		}
	})
}
