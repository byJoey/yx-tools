package app

import "testing"

func TestNormalizeSampleSize(t *testing.T) {
	cases := []struct {
		name string
		in   Options
		want int
	}{
		{"负数归零", Options{SampleSize: -5}, 0},
		{"零表示不限", Options{SampleSize: 0}, 0},
		{"正常值保留", Options{SampleSize: 1000}, 1000},
		{"测速全部时忽略抽样", Options{SampleSize: 1000, TestAll: true}, 0},
		{"候选少于结果数时抬到结果数", Options{SampleSize: 3, Count: 20}, 20},
		{"候选等于结果数不变", Options{SampleSize: 20, Count: 20}, 20},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			o := c.in
			o.Normalize()
			if o.SampleSize != c.want {
				t.Fatalf("want %d, got %d", c.want, o.SampleSize)
			}
		})
	}
}

func TestNormalizeHTTPing(t *testing.T) {
	cases := []struct {
		name string
		in   Options
		want bool
	}{
		{"默认走 TCP", Options{}, false},
		{"显式开启", Options{HTTPing: true}, true},
		{"选了地区强制开启", Options{Colo: "HKG"}, true},
		{"地区带空格也算", Options{Colo: "  SIN  "}, true},
		{"空地区不影响", Options{Colo: "   "}, false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			o := c.in
			o.Normalize()
			if o.HTTPing != c.want {
				t.Fatalf("want %v, got %v", c.want, o.HTTPing)
			}
		})
	}
}

func TestNormalizeProxyMode(t *testing.T) {
	// 反代模式测的是给定的列表，不抽样也不穷举；
	// 但地区筛选照常可用——反代最终回源到 Cloudflare，
	// 响应头里一样带得出机房代码。
	o := Options{
		Proxy: true, Colo: "HKG",
		SampleSize: 500, TestAll: true,
	}
	o.Normalize()
	if o.Colo != "HKG" {
		t.Errorf("地区筛选不该被清掉，got %q", o.Colo)
	}
	if !o.HTTPing {
		t.Error("选了地区就该走 HTTPing")
	}
	if o.SampleSize != 0 || o.TestAll {
		t.Errorf("反代模式不应抽样或穷举，got sample=%d all=%v", o.SampleSize, o.TestAll)
	}
	if o.IPFile != DataPath(ProxyListFile) {
		t.Errorf("应默认读数据目录下的 %s，got %q", ProxyListFile, o.IPFile)
	}

	// 已指定输入源时不覆盖
	o2 := Options{Proxy: true, IPFile: "mine.txt"}
	o2.Normalize()
	if o2.IPFile != "mine.txt" {
		t.Errorf("不该覆盖用户指定的文件，got %q", o2.IPFile)
	}
}
