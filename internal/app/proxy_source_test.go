package app

import (
	"fmt"
	"testing"
)

// 优选反代的输入源：CSV 只认 ip 与 port 两列，
// 其余列（host、title、protocol 这些）一概不看。
func TestParseProxySource(t *testing.T) {
	cases := []struct {
		name string
		text string
		want []string
	}{
		{
			// FOFA 资产导出：表头全小写，host 列带 https:// 前缀，只读 ip+port
			name: "FOFA三列导出",
			text: "host,ip,port\n" +
				"45.39.199.86:10443,45.39.199.86,10443\n" +
				"https://43.199.144.56:28017,43.199.144.56,28017\n" +
				"https://103.231.58.171:20000,103.231.58.171,20000\n",
			want: []string{"45.39.199.86:10443", "43.199.144.56:28017", "103.231.58.171:20000"},
		},
		{
			// FOFA 完整导出列更多，多出来的列必须被忽略
			name: "FOFA多列导出",
			text: "host,ip,port,protocol,title,country,server\n" +
				"https://1.1.1.1:2053,1.1.1.1,2053,https,Example,US,nginx\n" +
				"https://2.2.2.2:8443,2.2.2.2,8443,https,Test,HK,cloudflare\n",
			want: []string{"1.1.1.1:2053", "2.2.2.2:8443"},
		},
		{
			name: "本工具导出的结果CSV",
			text: "IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码,端口\n" +
				"104.16.1.1,4,4,0.00,12.30,25.60,HKG,443\n" +
				"104.16.1.2,4,4,0.00,18.10,11.20,NRT,2053\n",
			want: []string{"104.16.1.1:443", "104.16.1.2:2053"},
		},
		{
			name: "无表头的裸列表",
			text: "1.1.1.1:8443\n2.2.2.2\n[2606:4700::1111]:2087\n",
			want: []string{"1.1.1.1:8443", "2.2.2.2:443", "2606:4700::1111:2087"},
		},
		{
			name: "带备注和空行",
			text: "1.1.1.1:8443#香港\n\n2.2.2.2:2053 # 东京\n",
			want: []string{"1.1.1.1:8443", "2.2.2.2:2053"},
		},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rs, err := ParseProxySource(c.text)
			if err != nil {
				t.Fatalf("解析失败: %v", err)
			}
			var got []string
			for _, r := range rs {
				got = append(got, fmt.Sprintf("%s:%d", r.IP, r.Port))
			}
			if len(got) != len(c.want) {
				t.Fatalf("条数不对\n得到 %v\n期望 %v", got, c.want)
			}
			for i := range got {
				if got[i] != c.want[i] {
					t.Errorf("第 %d 条: 得到 %s, 期望 %s", i+1, got[i], c.want[i])
				}
			}
		})
	}
}

func TestParseProxySourceEmpty(t *testing.T) {
	if _, err := ParseProxySource("  \n\n "); err == nil {
		t.Fatal("空内容应当报错")
	}
}
