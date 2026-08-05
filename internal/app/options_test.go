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
