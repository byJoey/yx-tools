package app

// Colo 是 Cloudflare 数据中心（机场码）条目
type Colo struct {
	Code    string `json:"code"`
	Name    string `json:"name"`
	Region  string `json:"region"`
	Country string `json:"country"`
}

// Colos 覆盖 Cloudflare 全球数据中心
var Colos = []Colo{
	{Code: "HKG", Name: "香港", Region: "亚太", Country: "中国香港"},
	{Code: "TPE", Name: "台北", Region: "亚太", Country: "中国台湾"},
	{Code: "NRT", Name: "东京成田", Region: "亚太", Country: "日本"},
	{Code: "KIX", Name: "大阪", Region: "亚太", Country: "日本"},
	{Code: "ITM", Name: "大阪伊丹", Region: "亚太", Country: "日本"},
	{Code: "FUK", Name: "福冈", Region: "亚太", Country: "日本"},
	{Code: "ICN", Name: "首尔仁川", Region: "亚太", Country: "韩国"},
	{Code: "SIN", Name: "新加坡", Region: "亚太", Country: "新加坡"},
	{Code: "BKK", Name: "曼谷", Region: "亚太", Country: "泰国"},
	{Code: "HAN", Name: "河内", Region: "亚太", Country: "越南"},
	{Code: "SGN", Name: "胡志明市", Region: "亚太", Country: "越南"},
	{Code: "MNL", Name: "马尼拉", Region: "亚太", Country: "菲律宾"},
	{Code: "CGK", Name: "雅加达", Region: "亚太", Country: "印度尼西亚"},
	{Code: "KUL", Name: "吉隆坡", Region: "亚太", Country: "马来西亚"},
	{Code: "RGN", Name: "仰光", Region: "亚太", Country: "缅甸"},
	{Code: "PNH", Name: "金边", Region: "亚太", Country: "柬埔寨"},
	{Code: "BOM", Name: "孟买", Region: "亚太", Country: "印度"},
	{Code: "DEL", Name: "新德里", Region: "亚太", Country: "印度"},
	{Code: "MAA", Name: "金奈", Region: "亚太", Country: "印度"},
	{Code: "BLR", Name: "班加罗尔", Region: "亚太", Country: "印度"},
	{Code: "HYD", Name: "海得拉巴", Region: "亚太", Country: "印度"},
	{Code: "CCU", Name: "加尔各答", Region: "亚太", Country: "印度"},
	{Code: "SYD", Name: "悉尼", Region: "亚太", Country: "澳大利亚"},
	{Code: "MEL", Name: "墨尔本", Region: "亚太", Country: "澳大利亚"},
	{Code: "BNE", Name: "布里斯班", Region: "亚太", Country: "澳大利亚"},
	{Code: "PER", Name: "珀斯", Region: "亚太", Country: "澳大利亚"},
	{Code: "AKL", Name: "奥克兰", Region: "亚太", Country: "新西兰"},
	{Code: "LAX", Name: "洛杉矶", Region: "北美", Country: "美国"},
	{Code: "SJC", Name: "圣何塞", Region: "北美", Country: "美国"},
	{Code: "SEA", Name: "西雅图", Region: "北美", Country: "美国"},
	{Code: "SFO", Name: "旧金山", Region: "北美", Country: "美国"},
	{Code: "PDX", Name: "波特兰", Region: "北美", Country: "美国"},
	{Code: "SAN", Name: "圣地亚哥", Region: "北美", Country: "美国"},
	{Code: "PHX", Name: "凤凰城", Region: "北美", Country: "美国"},
	{Code: "LAS", Name: "拉斯维加斯", Region: "北美", Country: "美国"},
	{Code: "EWR", Name: "纽瓦克", Region: "北美", Country: "美国"},
	{Code: "IAD", Name: "华盛顿", Region: "北美", Country: "美国"},
	{Code: "BOS", Name: "波士顿", Region: "北美", Country: "美国"},
	{Code: "PHL", Name: "费城", Region: "北美", Country: "美国"},
	{Code: "ATL", Name: "亚特兰大", Region: "北美", Country: "美国"},
	{Code: "MIA", Name: "迈阿密", Region: "北美", Country: "美国"},
	{Code: "MCO", Name: "奥兰多", Region: "北美", Country: "美国"},
	{Code: "ORD", Name: "芝加哥", Region: "北美", Country: "美国"},
	{Code: "DFW", Name: "达拉斯", Region: "北美", Country: "美国"},
	{Code: "IAH", Name: "休斯顿", Region: "北美", Country: "美国"},
	{Code: "DEN", Name: "丹佛", Region: "北美", Country: "美国"},
	{Code: "MSP", Name: "明尼阿波利斯", Region: "北美", Country: "美国"},
	{Code: "DTW", Name: "底特律", Region: "北美", Country: "美国"},
	{Code: "STL", Name: "圣路易斯", Region: "北美", Country: "美国"},
	{Code: "MCI", Name: "堪萨斯城", Region: "北美", Country: "美国"},
	{Code: "YYZ", Name: "多伦多", Region: "北美", Country: "加拿大"},
	{Code: "YVR", Name: "温哥华", Region: "北美", Country: "加拿大"},
	{Code: "YUL", Name: "蒙特利尔", Region: "北美", Country: "加拿大"},
	{Code: "LHR", Name: "伦敦", Region: "欧洲", Country: "英国"},
	{Code: "CDG", Name: "巴黎", Region: "欧洲", Country: "法国"},
	{Code: "FRA", Name: "法兰克福", Region: "欧洲", Country: "德国"},
	{Code: "AMS", Name: "阿姆斯特丹", Region: "欧洲", Country: "荷兰"},
	{Code: "BRU", Name: "布鲁塞尔", Region: "欧洲", Country: "比利时"},
	{Code: "ZRH", Name: "苏黎世", Region: "欧洲", Country: "瑞士"},
	{Code: "VIE", Name: "维也纳", Region: "欧洲", Country: "奥地利"},
	{Code: "MUC", Name: "慕尼黑", Region: "欧洲", Country: "德国"},
	{Code: "DUS", Name: "杜塞尔多夫", Region: "欧洲", Country: "德国"},
	{Code: "HAM", Name: "汉堡", Region: "欧洲", Country: "德国"},
	{Code: "MAD", Name: "马德里", Region: "欧洲", Country: "西班牙"},
	{Code: "BCN", Name: "巴塞罗那", Region: "欧洲", Country: "西班牙"},
	{Code: "MXP", Name: "米兰", Region: "欧洲", Country: "意大利"},
	{Code: "FCO", Name: "罗马", Region: "欧洲", Country: "意大利"},
	{Code: "ATH", Name: "雅典", Region: "欧洲", Country: "希腊"},
	{Code: "LIS", Name: "里斯本", Region: "欧洲", Country: "葡萄牙"},
	{Code: "ARN", Name: "斯德哥尔摩", Region: "欧洲", Country: "瑞典"},
	{Code: "CPH", Name: "哥本哈根", Region: "欧洲", Country: "丹麦"},
	{Code: "OSL", Name: "奥斯陆", Region: "欧洲", Country: "挪威"},
	{Code: "HEL", Name: "赫尔辛基", Region: "欧洲", Country: "芬兰"},
	{Code: "WAW", Name: "华沙", Region: "欧洲", Country: "波兰"},
	{Code: "PRG", Name: "布拉格", Region: "欧洲", Country: "捷克"},
	{Code: "BUD", Name: "布达佩斯", Region: "欧洲", Country: "匈牙利"},
	{Code: "OTP", Name: "布加勒斯特", Region: "欧洲", Country: "罗马尼亚"},
	{Code: "SOF", Name: "索非亚", Region: "欧洲", Country: "保加利亚"},
	{Code: "DXB", Name: "迪拜", Region: "中东", Country: "阿联酋"},
	{Code: "TLV", Name: "特拉维夫", Region: "中东", Country: "以色列"},
	{Code: "BAH", Name: "巴林", Region: "中东", Country: "巴林"},
	{Code: "AMM", Name: "安曼", Region: "中东", Country: "约旦"},
	{Code: "KWI", Name: "科威特", Region: "中东", Country: "科威特"},
	{Code: "DOH", Name: "多哈", Region: "中东", Country: "卡塔尔"},
	{Code: "MCT", Name: "马斯喀特", Region: "中东", Country: "阿曼"},
	{Code: "GRU", Name: "圣保罗", Region: "南美", Country: "巴西"},
	{Code: "GIG", Name: "里约热内卢", Region: "南美", Country: "巴西"},
	{Code: "EZE", Name: "布宜诺斯艾利斯", Region: "南美", Country: "阿根廷"},
	{Code: "BOG", Name: "波哥大", Region: "南美", Country: "哥伦比亚"},
	{Code: "LIM", Name: "利马", Region: "南美", Country: "秘鲁"},
	{Code: "SCL", Name: "圣地亚哥", Region: "南美", Country: "智利"},
	{Code: "JNB", Name: "约翰内斯堡", Region: "非洲", Country: "南非"},
	{Code: "CPT", Name: "开普敦", Region: "非洲", Country: "南非"},
	{Code: "CAI", Name: "开罗", Region: "非洲", Country: "埃及"},
	{Code: "LOS", Name: "拉各斯", Region: "非洲", Country: "尼日利亚"},
	{Code: "NBO", Name: "内罗毕", Region: "非洲", Country: "肯尼亚"},
	{Code: "ACC", Name: "阿克拉", Region: "非洲", Country: "加纳"},
}

// ColoMap 按机场码索引
var ColoMap = func() map[string]Colo {
	m := make(map[string]Colo, len(Colos))
	for _, c := range Colos {
		m[c.Code] = c
	}
	return m
}()

// ColoName 返回机场码对应的中文名，找不到时回退为机场码本身
func ColoName(code string) string {
	if c, ok := ColoMap[code]; ok {
		return c.Name
	}
	if code == "" {
		return "未知"
	}
	return code
}
