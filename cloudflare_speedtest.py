#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare SpeedTest 跨平台自动化脚本
支持 Windows、Linux、macOS (Darwin)
支持完整的 Cloudflare 数据中心机场码映射
"""

import os
import sys
import platform
import subprocess
import requests
import json
import csv
from pathlib import Path
from datetime import datetime


# 使用curl的备用HTTP请求函数（解决SSL模块不可用的问题）
def curl_request(url, method='GET', data=None, headers=None, timeout=30):
    """
    使用curl命令进行HTTP请求（当requests的SSL模块不可用时使用）
    
    Args:
        url: 请求的URL
        method: HTTP方法（GET, POST, DELETE等）
        data: 请求数据（将被转换为JSON）
        headers: 请求头字典
        timeout: 超时时间（秒）
    
    Returns:
        dict: 包含status_code、json、text等属性的响应对象模拟
    """
    cmd = ['curl', '-s', '-w', '\\n%{http_code}', '-X', method, '--connect-timeout', str(timeout)]
    
    # 添加请求头
    if headers:
        for key, value in headers.items():
            cmd.extend(['-H', f'{key}: {value}'])
    
    # 添加请求数据
    if data:
        json_data = json.dumps(data)
        cmd.extend(['-d', json_data])
    
    # 添加URL
    cmd.append(url)
    
    try:
        # 执行curl命令，指定编码为utf-8
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        output = result.stdout
        
        # 分离响应体和状态码
        lines = output.strip().split('\n')
        if len(lines) >= 1:
            status_code = int(lines[-1])
            response_text = '\n'.join(lines[:-1])
        else:
            status_code = 0
            response_text = output
        
        # 创建响应对象模拟
        class CurlResponse:
            def __init__(self, status_code, text):
                self.status_code = status_code
                self.text = text
                self._json = None
            
            def json(self):
                if self._json is None:
                    self._json = json.loads(self.text) if self.text else {}
                return self._json
        
        return CurlResponse(status_code, response_text)
    
    except subprocess.TimeoutExpired:
        raise Exception("请求超时，请检查网络连接")
    except subprocess.CalledProcessError as e:
        raise Exception(f"curl命令执行失败: {e}")
    except FileNotFoundError:
        raise Exception("curl命令未找到，请确保系统已安装curl")
    except Exception as e:
        raise Exception(f"curl请求失败: {e}")


# Cloudflare 数据中心完整机场码映射
# 数据来源：Cloudflare 官方数据中心列表
AIRPORT_CODES = {
    # 亚太地区 - 中国及周边
    "HKG": {"name": "香港", "region": "亚太", "country": "中国香港"},
    "TPE": {"name": "台北", "region": "亚太", "country": "中国台湾"},
    
    # 亚太地区 - 日本
    "NRT": {"name": "东京成田", "region": "亚太", "country": "日本"},
    "KIX": {"name": "大阪", "region": "亚太", "country": "日本"},
    "ITM": {"name": "大阪伊丹", "region": "亚太", "country": "日本"},
    "FUK": {"name": "福冈", "region": "亚太", "country": "日本"},
    
    # 亚太地区 - 韩国
    "ICN": {"name": "首尔仁川", "region": "亚太", "country": "韩国"},
    
    # 亚太地区 - 东南亚
    "SIN": {"name": "新加坡", "region": "亚太", "country": "新加坡"},
    "BKK": {"name": "曼谷", "region": "亚太", "country": "泰国"},
    "HAN": {"name": "河内", "region": "亚太", "country": "越南"},
    "SGN": {"name": "胡志明市", "region": "亚太", "country": "越南"},
    "MNL": {"name": "马尼拉", "region": "亚太", "country": "菲律宾"},
    "CGK": {"name": "雅加达", "region": "亚太", "country": "印度尼西亚"},
    "KUL": {"name": "吉隆坡", "region": "亚太", "country": "马来西亚"},
    "RGN": {"name": "仰光", "region": "亚太", "country": "缅甸"},
    "PNH": {"name": "金边", "region": "亚太", "country": "柬埔寨"},
    
    # 亚太地区 - 南亚
    "BOM": {"name": "孟买", "region": "亚太", "country": "印度"},
    "DEL": {"name": "新德里", "region": "亚太", "country": "印度"},
    "MAA": {"name": "金奈", "region": "亚太", "country": "印度"},
    "BLR": {"name": "班加罗尔", "region": "亚太", "country": "印度"},
    "HYD": {"name": "海得拉巴", "region": "亚太", "country": "印度"},
    "CCU": {"name": "加尔各答", "region": "亚太", "country": "印度"},
    
    # 亚太地区 - 澳洲
    "SYD": {"name": "悉尼", "region": "亚太", "country": "澳大利亚"},
    "MEL": {"name": "墨尔本", "region": "亚太", "country": "澳大利亚"},
    "BNE": {"name": "布里斯班", "region": "亚太", "country": "澳大利亚"},
    "PER": {"name": "珀斯", "region": "亚太", "country": "澳大利亚"},
    "AKL": {"name": "奥克兰", "region": "亚太", "country": "新西兰"},
    
    # 北美地区 - 美国西海岸
    "LAX": {"name": "洛杉矶", "region": "北美", "country": "美国"},
    "SJC": {"name": "圣何塞", "region": "北美", "country": "美国"},
    "SEA": {"name": "西雅图", "region": "北美", "country": "美国"},
    "SFO": {"name": "旧金山", "region": "北美", "country": "美国"},
    "PDX": {"name": "波特兰", "region": "北美", "country": "美国"},
    "SAN": {"name": "圣地亚哥", "region": "北美", "country": "美国"},
    "PHX": {"name": "凤凰城", "region": "北美", "country": "美国"},
    "LAS": {"name": "拉斯维加斯", "region": "北美", "country": "美国"},
    
    # 北美地区 - 美国东海岸
    "EWR": {"name": "纽瓦克", "region": "北美", "country": "美国"},
    "IAD": {"name": "华盛顿", "region": "北美", "country": "美国"},
    "BOS": {"name": "波士顿", "region": "北美", "country": "美国"},
    "PHL": {"name": "费城", "region": "北美", "country": "美国"},
    "ATL": {"name": "亚特兰大", "region": "北美", "country": "美国"},
    "MIA": {"name": "迈阿密", "region": "北美", "country": "美国"},
    "MCO": {"name": "奥兰多", "region": "北美", "country": "美国"},
    
    # 北美地区 - 美国中部
    "ORD": {"name": "芝加哥", "region": "北美", "country": "美国"},
    "DFW": {"name": "达拉斯", "region": "北美", "country": "美国"},
    "IAH": {"name": "休斯顿", "region": "北美", "country": "美国"},
    "DEN": {"name": "丹佛", "region": "北美", "country": "美国"},
    "MSP": {"name": "明尼阿波利斯", "region": "北美", "country": "美国"},
    "DTW": {"name": "底特律", "region": "北美", "country": "美国"},
    "STL": {"name": "圣路易斯", "region": "北美", "country": "美国"},
    "MCI": {"name": "堪萨斯城", "region": "北美", "country": "美国"},
    
    # 北美地区 - 加拿大
    "YYZ": {"name": "多伦多", "region": "北美", "country": "加拿大"},
    "YVR": {"name": "温哥华", "region": "北美", "country": "加拿大"},
    "YUL": {"name": "蒙特利尔", "region": "北美", "country": "加拿大"},
    
    # 欧洲地区 - 西欧
    "LHR": {"name": "伦敦", "region": "欧洲", "country": "英国"},
    "CDG": {"name": "巴黎", "region": "欧洲", "country": "法国"},
    "FRA": {"name": "法兰克福", "region": "欧洲", "country": "德国"},
    "AMS": {"name": "阿姆斯特丹", "region": "欧洲", "country": "荷兰"},
    "BRU": {"name": "布鲁塞尔", "region": "欧洲", "country": "比利时"},
    "ZRH": {"name": "苏黎世", "region": "欧洲", "country": "瑞士"},
    "VIE": {"name": "维也纳", "region": "欧洲", "country": "奥地利"},
    "MUC": {"name": "慕尼黑", "region": "欧洲", "country": "德国"},
    "DUS": {"name": "杜塞尔多夫", "region": "欧洲", "country": "德国"},
    "HAM": {"name": "汉堡", "region": "欧洲", "country": "德国"},
    
    # 欧洲地区 - 南欧
    "MAD": {"name": "马德里", "region": "欧洲", "country": "西班牙"},
    "BCN": {"name": "巴塞罗那", "region": "欧洲", "country": "西班牙"},
    "MXP": {"name": "米兰", "region": "欧洲", "country": "意大利"},
    "FCO": {"name": "罗马", "region": "欧洲", "country": "意大利"},
    "ATH": {"name": "雅典", "region": "欧洲", "country": "希腊"},
    "LIS": {"name": "里斯本", "region": "欧洲", "country": "葡萄牙"},
    
    # 欧洲地区 - 北欧
    "ARN": {"name": "斯德哥尔摩", "region": "欧洲", "country": "瑞典"},
    "CPH": {"name": "哥本哈根", "region": "欧洲", "country": "丹麦"},
    "OSL": {"name": "奥斯陆", "region": "欧洲", "country": "挪威"},
    "HEL": {"name": "赫尔辛基", "region": "欧洲", "country": "芬兰"},
    
    # 欧洲地区 - 东欧
    "WAW": {"name": "华沙", "region": "欧洲", "country": "波兰"},
    "PRG": {"name": "布拉格", "region": "欧洲", "country": "捷克"},
    "BUD": {"name": "布达佩斯", "region": "欧洲", "country": "匈牙利"},
    "OTP": {"name": "布加勒斯特", "region": "欧洲", "country": "罗马尼亚"},
    "SOF": {"name": "索非亚", "region": "欧洲", "country": "保加利亚"},
    
    # 中东地区
    "DXB": {"name": "迪拜", "region": "中东", "country": "阿联酋"},
    "TLV": {"name": "特拉维夫", "region": "中东", "country": "以色列"},
    "BAH": {"name": "巴林", "region": "中东", "country": "巴林"},
    "AMM": {"name": "安曼", "region": "中东", "country": "约旦"},
    "KWI": {"name": "科威特", "region": "中东", "country": "科威特"},
    "DOH": {"name": "多哈", "region": "中东", "country": "卡塔尔"},
    "MCT": {"name": "马斯喀特", "region": "中东", "country": "阿曼"},
    
    # 南美地区
    "GRU": {"name": "圣保罗", "region": "南美", "country": "巴西"},
    "GIG": {"name": "里约热内卢", "region": "南美", "country": "巴西"},
    "EZE": {"name": "布宜诺斯艾利斯", "region": "南美", "country": "阿根廷"},
    "BOG": {"name": "波哥大", "region": "南美", "country": "哥伦比亚"},
    "LIM": {"name": "利马", "region": "南美", "country": "秘鲁"},
    "SCL": {"name": "圣地亚哥", "region": "南美", "country": "智利"},
    
    # 非洲地区
    "JNB": {"name": "约翰内斯堡", "region": "非洲", "country": "南非"},
    "CPT": {"name": "开普敦", "region": "非洲", "country": "南非"},
    "CAI": {"name": "开罗", "region": "非洲", "country": "埃及"},
    "LOS": {"name": "拉各斯", "region": "非洲", "country": "尼日利亚"},
    "NBO": {"name": "内罗毕", "region": "非洲", "country": "肯尼亚"},
    "ACC": {"name": "阿克拉", "region": "非洲", "country": "加纳"},
}

# 在线机场码列表URL（GitHub社区维护）
AIRPORT_CODES_URL = "https://wget.la/https://raw.githubusercontent.com/cloudflare/cf-ui/master/packages/colo-config/src/data.json"
AIRPORT_CODES_FILE = "airport_codes.json"

# Cloudflare IP列表URL和文件
CLOUDFLARE_IP_URL = "https://www.cloudflare.com/ips-v4/"
CLOUDFLARE_IP_FILE = "Cloudflare.txt"
CLOUDFLARE_IPV6_URL = "https://www.cloudflare.com/ips-v6/"
CLOUDFLARE_IPV6_FILE = "Cloudflare_ipv6.txt"

# Cloudflare IPv6 地址段（内置）
# 数据来源：https://www.cloudflare.com/ips-v6/
CLOUDFLARE_IPV6_RANGES = [
    # 主要地址段
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32",
    
    # 详细子网段
    "2400:cb00:2049::/48",
    "2400:cb00:f00e::/48",
    "2606:4700:10::/48",
    "2606:4700:130::/48",
    "2606:4700:3000::/48",
    "2606:4700:3001::/48",
    "2606:4700:3002::/48",
    "2606:4700:3003::/48",
    "2606:4700:3004::/48",
    "2606:4700:3005::/48",
    "2606:4700:3006::/48",
    "2606:4700:3007::/48",
    "2606:4700:3008::/48",
    "2606:4700:3009::/48",
    "2606:4700:3010::/48",
    "2606:4700:3011::/48",
    "2606:4700:3012::/48",
    "2606:4700:3013::/48",
    "2606:4700:3014::/48",
    "2606:4700:3015::/48",
    "2606:4700:3016::/48",
    "2606:4700:3017::/48",
    "2606:4700:3018::/48",
    "2606:4700:3019::/48",
    "2606:4700:3020::/48",
    "2606:4700:3021::/48",
    "2606:4700:3022::/48",
    "2606:4700:3023::/48",
    "2606:4700:3024::/48",
    "2606:4700:3025::/48",
    "2606:4700:3026::/48",
    "2606:4700:3027::/48",
    "2606:4700:3028::/48",
    "2606:4700:3029::/48",
    "2606:4700:3030::/48",
    "2606:4700:3031::/48",
    "2606:4700:3032::/48",
    "2606:4700:3033::/48",
    "2606:4700:3034::/48",
    "2606:4700:3035::/48",
    "2606:4700:3036::/48",
    "2606:4700:3037::/48",
    "2606:4700:3038::/48",
    "2606:4700:3039::/48",
    "2606:4700:a0::/48",
    "2606:4700:a1::/48",
    "2606:4700:a8::/48",
    "2606:4700:a9::/48",
    "2606:4700:a::/48",
    "2606:4700:b::/48",
    "2606:4700:c::/48",
    "2606:4700:d0::/48",
    "2606:4700:d1::/48",
    "2606:4700:d::/48",
    "2606:4700:e0::/48",
    "2606:4700:e1::/48",
    "2606:4700:e2::/48",
    "2606:4700:e3::/48",
    "2606:4700:e4::/48",
    "2606:4700:e5::/48",
    "2606:4700:e6::/48",
    "2606:4700:e7::/48",
    "2606:4700:e::/48",
    "2606:4700:f1::/48",
    "2606:4700:f2::/48",
    "2606:4700:f3::/48",
    "2606:4700:f4::/48",
    "2606:4700:f5::/48",
    "2606:4700:f::/48",
    "2803:f800:50::/48",
    "2803:f800:51::/48",
    "2a06:98c1:3100::/48",
    "2a06:98c1:3101::/48",
    "2a06:98c1:3102::/48",
    "2a06:98c1:3103::/48",
    "2a06:98c1:3104::/48",
    "2a06:98c1:3105::/48",
    "2a06:98c1:3106::/48",
    "2a06:98c1:3107::/48",
    "2a06:98c1:3108::/48",
    "2a06:98c1:3109::/48",
    "2a06:98c1:310a::/48",
    "2a06:98c1:310b::/48",
    "2a06:98c1:310c::/48",
    "2a06:98c1:310d::/48",
    "2a06:98c1:310e::/48",
    "2a06:98c1:310f::/48",
    "2a06:98c1:3120::/48",
    "2a06:98c1:3121::/48",
    "2a06:98c1:3122::/48",
    "2a06:98c1:3123::/48",
    "2a06:98c1:3200::/48",
    "2a06:98c1:50::/48",
    "2a06:98c1:51::/48",
    "2a06:98c1:54::/48",
    "2a06:98c1:58::/48",
]

# GitHub Release版本 - 使用官方CloudflareSpeedTest
GITHUB_VERSION = "v2.3.4"
GITHUB_REPO = "XIU2/CloudflareSpeedTest"

# 配置文件路径
CONFIG_FILE = ".cloudflare_speedtest_config.json"


def generate_ipv6_file():
    """生成 IPv6 地址列表文件"""
    try:
        with open(CLOUDFLARE_IPV6_FILE, 'w', encoding='utf-8') as f:
            for ipv6_range in CLOUDFLARE_IPV6_RANGES:
                f.write(ipv6_range + '\n')
        print(f"✅ IPv6 地址列表已生成: {CLOUDFLARE_IPV6_FILE}")
        print(f"   共 {len(CLOUDFLARE_IPV6_RANGES)} 个 IPv6 地址段")
        return True
    except Exception as e:
        print(f"❌ 生成 IPv6 地址列表失败: {e}")
        return False


def get_system_info():
    """获取系统信息"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # 标准化系统名称
    if system == "darwin":
        os_type = "darwin"
    elif system == "linux":
        os_type = "linux"
    elif system == "windows":
        os_type = "win"
    else:
        print(f"不支持的操作系统: {system}")
        if sys.platform == "win32":
            input("按 Enter 键退出...")
        sys.exit(1)
    
    # 标准化架构名称
    if machine in ["x86_64", "amd64", "x64"]:
        arch_type = "amd64"
    elif machine in ["arm64", "aarch64"]:
        arch_type = "arm64"
    elif machine in ["armv7l", "armv6l"]:
        arch_type = "arm"
    else:
        print(f"不支持的架构: {machine}")
        if sys.platform == "win32":
            input("按 Enter 键退出...")
        sys.exit(1)
    
    return os_type, arch_type


def get_executable_name(os_type, arch_type):
    """获取可执行文件名 - 使用官方命名规则"""
    if os_type == "win":
        return f"CloudflareST_windows_{arch_type}.exe"
    elif os_type == "darwin":
        return f"CloudflareST_darwin_{arch_type}"
    else:  # linux
        return f"CloudflareST_linux_{arch_type}"


def download_file(url, filename):
    """下载文件 - 支持多种下载方法"""
    print(f"正在下载: {url}")
    
    # 方法1: 尝试使用 requests（SSL不可用时静默切换到curl）
    try:
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ 下载完成: {filename}")
            return True
        except ImportError as e:
            # SSL模块不可用，静默切换到curl下载
            if "SSL module is not available" in str(e):
                result = subprocess.run([
                    "curl", "-L", "-o", filename, url
                ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
                
                if result.returncode == 0 and os.path.exists(filename):
                    print(f"✅ 下载完成: {filename}")
                    return True
            else:
                raise
    except Exception:
        # 静默失败，继续尝试其他方法
        pass
    
    # 方法2: 尝试使用 wget
    try:
        result = subprocess.run([
            "wget", "-O", filename, url
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        
        if result.returncode == 0 and os.path.exists(filename):
            print(f"✅ 下载完成: {filename}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # wget 不可用，静默继续
        pass
    except Exception:
        # wget 执行失败，静默继续
        pass
    
    # 方法3: 尝试使用 curl
    try:
        result = subprocess.run([
            "curl", "-L", "-o", filename, url
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        
        if result.returncode == 0 and os.path.exists(filename):
            print(f"✅ 下载完成: {filename}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # curl 不可用，静默继续
        pass
    except Exception:
        # curl 执行失败，静默继续
        pass
    
    # 方法3.5: Windows PowerShell 下载
    if sys.platform == "win32":
        try:
            ps_cmd = f'Invoke-WebRequest -Uri "{url}" -OutFile "{filename}"'
            result = subprocess.run([
                "powershell", "-Command", ps_cmd
            ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
            
            if result.returncode == 0 and os.path.exists(filename):
                print(f"✅ 下载完成: {filename}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # PowerShell 不可用，静默继续
            pass
        except Exception:
            # PowerShell 执行失败，静默继续
            pass
    
    # 方法4: 尝试使用 urllib
    try:
        import urllib.request
        urllib.request.urlretrieve(url, filename)
        print(f"✅ 下载完成: {filename}")
        return True
    except Exception:
        # urllib 下载失败，静默继续
        pass
    
    # 方法5: 尝试 HTTP 版本
    if url.startswith("https://"):
        http_url = url.replace("https://", "http://")
        try:
            try:
                response = requests.get(http_url, stream=True, timeout=60)
                response.raise_for_status()
                
                with open(filename, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"✅ 下载完成: {filename}")
                return True
            except ImportError as e:
                # SSL模块不可用，静默切换到curl下载
                if "SSL module is not available" in str(e):
                    result = subprocess.run([
                        "curl", "-L", "-o", filename, http_url
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and os.path.exists(filename):
                        print(f"✅ 下载完成: {filename}")
                        return True
                else:
                    raise
        except Exception:
            # HTTP 下载失败，静默继续
            pass
    
    # 所有方法都失败
    print("❌ 下载失败")
    return False


def download_cloudflare_speedtest(os_type, arch_type):
    """下载 CloudflareSpeedTest 可执行文件（优先使用反代版本）"""
    # 优先检查反代版本
    if os_type == "win":
        proxy_exec_name = f"CloudflareST_proxy_{os_type}_{arch_type}.exe"
    else:
        proxy_exec_name = f"CloudflareST_proxy_{os_type}_{arch_type}"
    
    if os.path.exists(proxy_exec_name):
        print(f"✓ 使用反代版本: {proxy_exec_name}")
        return proxy_exec_name
    
    # 检查是否已下载反代版本
    print("反代版本不存在，开始下载反代版本...")
    
    # 构建下载URL - 使用您的GitHub仓库
    if os_type == "win":
        if arch_type == "amd64":
            archive_name = "CloudflareST_proxy_windows_amd64.zip"
        else:
            archive_name = "CloudflareST_proxy_windows_386.zip"
    elif os_type == "darwin":
        if arch_type == "amd64":
            archive_name = "CloudflareST_proxy_darwin_amd64.zip"
        else:
            archive_name = "CloudflareST_proxy_darwin_arm64.zip"
    else:  # linux
        if arch_type == "amd64":
            archive_name = "CloudflareST_proxy_linux_amd64.tar.gz"
        elif arch_type == "386":
            archive_name = "CloudflareST_proxy_linux_386.tar.gz"
        else:  # arm64
            archive_name = "CloudflareST_proxy_linux_arm64.tar.gz"
    
    download_url = f"https://wget.la/https://github.com/byJoey/CloudflareSpeedTest/releases/download/v1.0/{archive_name}"
    
    if not download_file(download_url, archive_name):
        # 备用方案: 尝试 HTTP 下载
        http_url = download_url.replace("https://", "http://")
        if not download_file(http_url, archive_name):
            # 所有自动下载都失败，提供手动下载说明
            print("\n" + "="*60)
            print("自动下载失败，请手动下载反代版本:")
            print(f"下载地址: {download_url}")
            print(f"解压后文件名应为: CloudflareST_proxy_{os_type}_{arch_type}{'.exe' if os_type == 'win' else ''}")
            print("="*60)
            
            # 检查是否有手动下载的反代版本文件
            if os_type == "win":
                proxy_exec_name = f"CloudflareST_proxy_{os_type}_{arch_type}.exe"
            else:
                proxy_exec_name = f"CloudflareST_proxy_{os_type}_{arch_type}"
            
            if os.path.exists(proxy_exec_name):
                print(f"找到手动下载的反代版本: {proxy_exec_name}")
                # 手动下载的文件也需要赋予执行权限
                if os_type != "win":
                    os.chmod(proxy_exec_name, 0o755)
                    print(f"已赋予执行权限: {proxy_exec_name}")
                return proxy_exec_name
            else:
                print("未找到反代版本文件，程序无法继续")
                if sys.platform == "win32":
                    input("按 Enter 键退出...")
                sys.exit(1)
    else:
        # 解压文件
        print(f"正在解压: {archive_name}")
        try:
            if archive_name.endswith('.zip'):
                import zipfile
                with zipfile.ZipFile(archive_name, 'r') as zip_ref:
                    zip_ref.extractall('.')
            elif archive_name.endswith('.tar.gz'):
                import tarfile
                with tarfile.open(archive_name, 'r:gz') as tar_ref:
                    tar_ref.extractall('.')
            
            # 查找反代版本可执行文件
            found_executable = None
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file.startswith('CloudflareST_proxy_') and not file.endswith(('.zip', '.tar.gz')):
                        found_executable = os.path.join(root, file)
                        break
                if found_executable:
                    break
            
            if found_executable:
                # 获取最终文件名 - 使用标准格式
                if os_type == "win":
                    final_name = f"CloudflareST_proxy_{os_type}_{arch_type}.exe"
                else:
                    final_name = f"CloudflareST_proxy_{os_type}_{arch_type}"
                
                # 如果文件不在当前目录或文件名不匹配，移动到当前目录并重命名
                if os.path.abspath(found_executable) != os.path.abspath(final_name):
                    if os.path.exists(final_name):
                        os.remove(final_name)
                    # 确保源文件存在
                    if os.path.exists(found_executable):
                        os.rename(found_executable, final_name)
                    else:
                        print(f"❌ 源文件不存在: {found_executable}")
                        if sys.platform == "win32":
                            input("按 Enter 键退出...")
                        sys.exit(1)
                
                # 设置执行权限
                if os_type != "win":
                    os.chmod(final_name, 0o755)
                
                print(f"✓ 反代版本设置完成: {final_name}")
                return final_name
            else:
                print("解压后未找到反代版本可执行文件")
                # 列出解压后的所有文件用于调试
                print("解压后的文件:")
                for root, dirs, files in os.walk('.'):
                    for file in files:
                        if not file.endswith(('.zip', '.tar.gz', '.txt', '.md')):
                            print(f"  - {os.path.join(root, file)}")
                if sys.platform == "win32":
                    input("按 Enter 键退出...")
                sys.exit(1)
            
            # 清理压缩包
            os.remove(archive_name)
            
        except Exception as e:
            print(f"解压失败: {e}")
            if sys.platform == "win32":
                input("按 Enter 键退出...")
            sys.exit(1)
    
    # 在Unix系统上赋予执行权限
    if os_type != "win":
        os.chmod(proxy_exec_name, 0o755)
        print(f"已赋予执行权限: {proxy_exec_name}")
    
    return proxy_exec_name


def select_ip_version():
    """选择IP版本（IPv4或IPv6）"""
    print("\n" + "=" * 60)
    print(" IP 版本选择")
    print("=" * 60)
    print("  1. IPv4 - 测试 IPv4 地址（推荐，兼容性最好）")
    print("  2. IPv6 - 测试 IPv6 地址（需要本地网络支持IPv6）")
    print("=" * 60)
    
    while True:
        choice = input("\n请选择 IP 版本 [1/2，默认：1]: ").strip()
        if not choice or choice == "1":
            print("✓ 已选择: IPv4")
            return "ipv4", CLOUDFLARE_IP_FILE
        elif choice == "2":
            print("✓ 已选择: IPv6")
            return "ipv6", CLOUDFLARE_IPV6_FILE
        else:
            print("✗ 请输入 1 或 2")


def download_cloudflare_ips(ip_version="ipv4", ip_file=CLOUDFLARE_IP_FILE):
    """下载或生成 Cloudflare IP 列表
    
    Args:
        ip_version: IP版本 ("ipv4" 或 "ipv6")
        ip_file: IP文件路径
    """
    # 检查文件是否已存在
    if os.path.exists(ip_file):
        print(f"✅ 使用已有IP文件: {ip_file}")
        return True
    
    if ip_version == "ipv6":
        # IPv6 使用内置地址段生成
        print("正在生成 Cloudflare IPv6 地址列表...")
        return generate_ipv6_file()
    else:
        # IPv4 从网络下载
        print("正在下载 Cloudflare IPv4 列表...")
        
        if not download_file(CLOUDFLARE_IP_URL, CLOUDFLARE_IP_FILE):
            print("下载 Cloudflare IP 列表失败")
            return False
        
        # 检查文件是否为空
        if os.path.getsize(CLOUDFLARE_IP_FILE) == 0:
            print("Cloudflare IP 列表文件为空")
            return False
        
        print(f"Cloudflare IP 列表已保存到: {CLOUDFLARE_IP_FILE}")
        return True


def load_local_airport_codes():
    """从本地文件加载机场码（如果存在）"""
    if os.path.exists(AIRPORT_CODES_FILE):
        try:
            with open(AIRPORT_CODES_FILE, 'r', encoding='utf-8') as f:
                custom_codes = json.load(f)
                AIRPORT_CODES.update(custom_codes)
                print(f"✓ 已加载本地机场码配置（{len(custom_codes)} 个）")
        except Exception as e:
            print(f"加载本地机场码失败: {e}")


def save_airport_codes():
    """保存机场码到本地文件"""
    try:
        with open(AIRPORT_CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(AIRPORT_CODES, f, ensure_ascii=False, indent=2)
        print(f"✓ 机场码已保存到: {AIRPORT_CODES_FILE}")
    except Exception as e:
        print(f"保存机场码失败: {e}")


def display_airport_codes(region_filter=None):
    """显示所有支持的机场码，可按地区筛选"""
    # 按地区分组
    regions = {}
    for code, info in AIRPORT_CODES.items():
        region = info.get('region', '其他')
        if region not in regions:
            regions[region] = []
        regions[region].append((code, info))
    
    # 显示统计信息
    print(f"\n支持的机场码列表（共 {len(AIRPORT_CODES)} 个数据中心）")
    print("=" * 70)
    
    # 如果指定了地区筛选
    if region_filter:
        region_filter = region_filter.strip()
        if region_filter in regions:
            print(f"\n【{region_filter}地区】")
            print("-" * 70)
            for code, info in sorted(regions[region_filter], key=lambda x: x[0]):
                country = info.get('country', '')
                print(f"  {code:5s} - {info['name']:20s} ({country})")
        else:
            print(f"未找到地区: {region_filter}")
            print(f"可用地区: {', '.join(sorted(regions.keys()))}")
        return
    
    # 显示所有地区
    region_order = ["亚太", "北美", "欧洲", "中东", "南美", "非洲", "其他"]
    for region in region_order:
        if region in regions:
            print(f"\n【{region}地区】（{len(regions[region])} 个）")
            print("-" * 70)
            for code, info in sorted(regions[region], key=lambda x: x[0]):
                country = info.get('country', '')
                print(f"  {code:5s} - {info['name']:20s} ({country})")
    
    print("=" * 70)


def display_popular_codes():
    """显示热门机场码"""
    popular = {
        "HKG": "香港", "SIN": "新加坡", "NRT": "东京成田", "ICN": "首尔", 
        "LAX": "洛杉矶", "SJC": "圣何塞", "LHR": "伦敦", "FRA": "法兰克福"
    }
    
    print("\n热门机场码:")
    print("-" * 50)
    for code, name in popular.items():
        if code in AIRPORT_CODES:
            info = AIRPORT_CODES[code]
            region = info.get('region', '')
            print(f"  {code:5s} - {name:15s} [{region}]")
    print("-" * 50)


def find_airport_by_name(query):
    """根据城市名称查找机场码（支持模糊匹配）"""
    query = query.strip()
    if not query:
        return None
    
    # 先尝试精确匹配机场码
    query_upper = query.upper()
    if query_upper in AIRPORT_CODES:
        return query_upper
    
    # 构建城市名称到机场码的映射
    results = []
    
    for code, info in AIRPORT_CODES.items():
        name = info.get('name', '').lower()
        country = info.get('country', '').lower()
        query_lower = query.lower()
        
        # 精确匹配城市名称
        if name == query_lower:
            return code
        
        # 模糊匹配（包含关系）
        if query_lower in name or name in query_lower:
            results.append((code, info, 1))  # 优先级1
        elif query_lower in country:
            results.append((code, info, 2))  # 优先级2
    
    # 如果有匹配结果
    if results:
        # 按优先级排序
        results.sort(key=lambda x: x[2])
        
        # 如果只有一个结果，直接返回
        if len(results) == 1:
            return results[0][0]
        
        # 如果有多个结果，显示让用户选择
        print(f"\n找到 {len(results)} 个匹配的城市:")
        print("-" * 60)
        for idx, (code, info, _) in enumerate(results[:10], 1):  # 最多显示10个
            region = info.get('region', '')
            country = info.get('country', '')
            print(f"  {idx}. {code:5s} - {info['name']:20s} ({country}) [{region}]")
        print("-" * 60)
        
        try:
            choice = input(f"\n请选择 [1-{min(len(results), 10)}] 或按回车取消: ").strip()
            if choice:
                idx = int(choice) - 1
                if 0 <= idx < min(len(results), 10):
                    return results[idx][0]
        except (ValueError, IndexError):
            pass
    
    return None


def display_preset_configs():
    """显示预设配置"""
    print("\n" + "=" * 60)
    print(" 预设配置选项")
    print("=" * 60)
    print("  1. 快速测试 (10个IP, 1MB/s, 1000ms)")
    print("  2. 标准测试 (20个IP, 2MB/s, 500ms)")
    print("  3. 高质量测试 (50个IP, 5MB/s, 200ms)")
    print("  4. 自定义配置")
    print("=" * 60)


def get_user_input(ip_file=CLOUDFLARE_IP_FILE):
    """获取用户输入参数
    
    Args:
        ip_file: 要使用的IP文件路径
    """
    # 询问功能选择
    print("\n" + "=" * 60)
    print(" 功能选择")
    print("=" * 60)
    print("  1. 小白快速测试 - 简单输入，适合新手")
    print("  2. 常规测速 - 测试指定机场码的IP速度")
    print("  3. 优选反代 - 从CSV文件生成反代IP列表")
    print("=" * 60)
    
    choice = input("\n请选择功能 [默认: 1]: ").strip()
    if not choice:
        choice = "1"
    
    if choice == "1":
        # 小白快速测试模式
        return handle_beginner_mode(ip_file)
    elif choice == "3":
        # 优选反代模式
        return handle_proxy_mode()
    else:
        # 常规测速模式
        return handle_normal_mode(ip_file)


def select_csv_file():
    """选择CSV文件"""
    while True:
        csv_file = input("\n请输入CSV文件路径 [默认: result.csv]: ").strip()
        if not csv_file:
            csv_file = "result.csv"
        
        if os.path.exists(csv_file):
            print(f"找到文件: {csv_file}")
            return csv_file
        else:
            print(f"文件不存在: {csv_file}")
            print("请确保文件路径正确，或先运行常规测速生成result.csv")
            retry = input("是否重新输入？[Y/n]: ").strip().lower()
            if retry in ['n', 'no']:
                return None






def handle_proxy_mode():
    """处理优选反代模式"""
    print("\n" + "=" * 70)
    print(" 优选反代模式")
    print("=" * 70)
    print(" 此功能将从CSV文件中提取IP和端口信息，生成反代IP列表")
    print(" CSV文件格式要求：")
    print("   - 包含 'IP 地址' 和 '端口' 列")
    print("   - 或包含 'ip' 和 'port' 列")
    print("   - 支持逗号分隔的CSV格式")
    print("=" * 70)
    
    # 选择CSV文件
    csv_file = select_csv_file()
    
    if not csv_file:
        print("未选择有效文件，退出优选反代模式")
        return None, None, None, None
    
    # 生成反代IP列表
    print(f"\n正在处理CSV文件: {csv_file}")
    success = generate_proxy_list(csv_file, "ips_ports.txt")
    
    if success:
        print("\n" + "=" * 60)
        print(" 优选反代功能完成！")
        print("=" * 60)
        print(" 生成的文件:")
        print("   - ips_ports.txt (反代IP列表)")
        print("   - 格式: IP:端口 (每行一个)")
        print("\n 使用说明:")
        print("   - 可直接用于反代配置")
        print("   - 支持各种代理软件")
        print("   - 建议定期更新IP列表")
        print("=" * 60)
        
        # 询问是否进行测速
        print("\n" + "=" * 50)
        test_choice = input("是否对反代IP列表进行测速？[Y/n]: ").strip().lower()
        
        if test_choice in ['n', 'no']:
            print("跳过测速，优选反代功能完成")
            return None, None, None, None

        print("开始对反代IP列表进行测速...")
        print("注意: 反代模式直接对IP列表测速，不需要选择机场码")
        
        # 显示预设配置选项
        display_preset_configs()
        
        # 获取配置选择
        while True:
            config_choice = input("\n请选择配置 [默认: 1]: ").strip()
            if not config_choice:
                config_choice = "1"
            
            if config_choice == "1":
                # 快速测试
                dn_count = "10"
                speed_limit = "1"
                time_limit = "1000"
                print("✓ 已选择: 快速测试 (10个IP, 1MB/s, 1000ms)")
                break
            elif config_choice == "2":
                # 标准测试
                dn_count = "20"
                speed_limit = "2"
                time_limit = "500"
                print("✓ 已选择: 标准测试 (20个IP, 2MB/s, 500ms)")
                break
            elif config_choice == "3":
                # 高质量测试
                dn_count = "50"
                speed_limit = "5"
                time_limit = "200"
                print("✓ 已选择: 高质量测试 (50个IP, 5MB/s, 200ms)")
                break
            elif config_choice == "4":
                # 自定义配置
                print("\n自定义配置:")
                
                # 获取测试IP数量
                while True:
                    dn_count = input("请输入要测试的 IP 数量 [默认: 10]: ").strip()
                    if not dn_count:
                        dn_count = "10"
                    
                    try:
                        dn_count_int = int(dn_count)
                        if dn_count_int <= 0:
                            print("✗ 请输入大于0的数字")
                            continue
                        if dn_count_int > 200:
                            confirm = input(f"  警告: 测试 {dn_count_int} 个IP可能需要较长时间，是否继续？[y/N]: ").strip().lower()
                            if confirm != 'y':
                                continue
                        dn_count = str(dn_count_int)
                        break
                    except ValueError:
                        print("✗ 请输入有效的数字")
                
                # 获取下载速度下限
                while True:
                    speed_limit = input("请输入下载速度下限 (MB/s) [默认: 1]: ").strip()
                    if not speed_limit:
                        speed_limit = "1"
                    
                    try:
                        speed_limit_float = float(speed_limit)
                        if speed_limit_float < 0:
                            print("✗ 请输入大于等于0的数字")
                            continue
                        if speed_limit_float > 100:
                            print("警告: 速度阈值过高，可能找不到符合条件的IP")
                            confirm = input("  是否继续？[y/N]: ").strip().lower()
                            if confirm != 'y':
                                continue
                        speed_limit = str(speed_limit_float)
                        break
                    except ValueError:
                        print("✗ 请输入有效的数字")
                
                # 获取延迟阈值
                while True:
                    time_limit = input("请输入延迟阈值 (ms) [默认: 1000]: ").strip()
                    if not time_limit:
                        time_limit = "1000"
                    
                    try:
                        time_limit_int = int(time_limit)
                        if time_limit_int <= 0:
                            print("✗ 请输入大于0的数字")
                            continue
                        if time_limit_int > 5000:
                            print("警告: 延迟阈值过高，可能影响使用体验")
                            confirm = input("  是否继续？[y/N]: ").strip().lower()
                            if confirm != 'y':
                                continue
                        time_limit = str(time_limit_int)
                        break
                    except ValueError:
                        print("✗ 请输入有效的数字")
                
                print(f"✓ 自定义配置: {dn_count}个IP, {speed_limit}MB/s, {time_limit}ms")
                break
            else:
                print("✗ 无效选择，请输入 1-4")
        
        print(f"\n测速参数: 测试{dn_count}个IP, 速度下限{speed_limit}MB/s, 延迟上限{time_limit}ms")
        print("模式: 反代IP列表测速")
        
        # 运行测速
        result_code = run_speedtest_with_file("ips_ports.txt", dn_count, speed_limit, time_limit)
        
        # 如果测速成功，询问是否上报结果
        if result_code == 0 and os.path.exists("result.csv"):
            upload_results_to_api("result.csv")
        
        return None, None, None, None
    else:
        print("\n优选反代功能失败")
        return None, None, None, None


def handle_beginner_mode(ip_file=CLOUDFLARE_IP_FILE):
    """处理小白快速测试模式
    
    Args:
        ip_file: 要使用的IP文件路径
    """
    print("\n" + "=" * 70)
    print(" 小白快速测试模式")
    print("=" * 70)
    print(" 此功能专为新手设计，只需要输入3个简单的数字即可开始测试")
    print(" 无需了解复杂的参数设置，程序会引导您完成所有配置")
    print("=" * 70)
    
    # 获取测试IP数量
    print("\n📊 第一步：设置测试IP数量")
    print("说明：测试的IP数量越多，结果越准确，但耗时越长")
    while True:
        dn_count = input("请输入要测试的IP数量 [默认: 10]: ").strip()
        if not dn_count:
            dn_count = "10"
        try:
            dn_count_int = int(dn_count)
            if dn_count_int <= 0:
                print("✗ 请输入大于0的数字")
                continue
            if dn_count_int > 100:
                print("⚠️  测试数量较多，可能需要较长时间")
                confirm = input("  是否继续？[y/N]: ").strip().lower()
                if confirm != 'y':
                    continue
            dn_count = str(dn_count_int)
            break
        except ValueError:
            print("✗ 请输入有效的数字")
    
    # 获取延迟阈值
    print(f"\n⏱️  第二步：设置延迟上限")
    print("说明：延迟越低，网络响应越快。一般建议100-1000ms")
    while True:
        time_limit = input("请输入延迟上限(ms) [默认: 1000]: ").strip()
        if not time_limit:
            time_limit = "1000"
        try:
            time_limit_int = int(time_limit)
            if time_limit_int <= 0:
                print("✗ 请输入大于0的数字")
                continue
            if time_limit_int > 5000:
                print("⚠️  延迟阈值过高，可能影响使用体验")
                confirm = input("  是否继续？[y/N]: ").strip().lower()
                if confirm != 'y':
                    continue
            time_limit = str(time_limit_int)
            break
        except ValueError:
            print("✗ 请输入有效的数字")
    
    # 获取下载速度下限
    print(f"\n🚀 第三步：设置下载速度下限")
    print("说明：速度越高，网络越快。一般建议1-10MB/s")
    while True:
        speed_limit = input("请输入下载速度下限(MB/s) [默认: 1]: ").strip()
        if not speed_limit:
            speed_limit = "1"
        try:
            speed_limit_float = float(speed_limit)
            if speed_limit_float < 0:
                print("✗ 请输入大于等于0的数字")
                continue
            if speed_limit_float > 50:
                print("⚠️  速度阈值过高，可能找不到符合条件的IP")
                confirm = input("  是否继续？[y/N]: ").strip().lower()
                if confirm != 'y':
                    continue
            speed_limit = str(speed_limit_float)
            break
        except ValueError:
            print("✗ 请输入有效的数字")
    
    print(f"\n✅ 配置完成！")
    print(f"📋 测试参数:")
    print(f"   - 测试IP数量: {dn_count} 个")
    print(f"   - 延迟上限: {time_limit} ms")
    print(f"   - 速度下限: {speed_limit} MB/s")
    print("=" * 50)
    
    print(f"\n🎯 开始测速...")
    print(f"参数: 测试{dn_count}个IP, 速度下限{speed_limit}MB/s, 延迟上限{time_limit}ms")
    print("模式: 小白快速测试（全自动，无需选择地区）")
    
    # 直接使用 Cloudflare IP 列表进行测速
    print(f"\n正在使用 Cloudflare IP 列表进行测速...")
    
    # 获取系统信息和可执行文件
    os_type, arch_type = get_system_info()
    exec_name = download_cloudflare_speedtest(os_type, arch_type)
    
    # 构建测速命令
    if sys.platform == "win32":
        cmd = [exec_name]
    else:
        cmd = [f"./{exec_name}"]
    
    cmd.extend([
        "-f", ip_file,
        "-dn", dn_count,
        "-sl", speed_limit,
        "-tl", time_limit,
        "-o", "result.csv"
    ])
    
    print(f"\n运行命令: {' '.join(cmd)}")
    print("=" * 50)
    
    # 运行测速
    result = subprocess.run(cmd, encoding='utf-8', errors='replace')
    
    if result.returncode == 0:
        print("\n✅ 测速完成！结果已保存到 result.csv")
        print("📊 您可以查看 result.csv 文件来了解详细的测试结果")
        print("💡 提示：结果文件中的IP按速度从快到慢排序")
        
        # 询问是否上报结果
        upload_results_to_api("result.csv")
    else:
        print("\n❌ 测速失败")
    
    return "ALL", dn_count, speed_limit, time_limit


def handle_normal_mode(ip_file=CLOUDFLARE_IP_FILE):
    """处理常规测速模式
    
    Args:
        ip_file: 要使用的IP文件路径
    """
    print("\n开始检测可用地区...")
    print("正在使用HTTPing模式检测各地区可用性...")
    
    # 先运行一次HTTPing检测，获取可用地区
    available_regions = detect_available_regions()
    
    if not available_regions:
        print("❌ 未检测到可用地区，请检查网络连接")
        return None
    
    print(f"\n检测到 {len(available_regions)} 个可用地区:")
    for i, (region_code, region_name, count) in enumerate(available_regions, 1):
        print(f"  {i}. {region_code} - {region_name} (可用{count}个IP)")
    
    # 让用户选择地区
    while True:
        try:
            choice = int(input(f"\n请选择地区 [1-{len(available_regions)}]: ").strip())
            if 1 <= choice <= len(available_regions):
                selected_region = available_regions[choice - 1]
                cfcolo = selected_region[0]
                region_name = selected_region[1]
                count = selected_region[2]
                print(f"✓ 已选择: {region_name} ({cfcolo}) - 可用{count}个IP")
                break
            else:
                print(f"✗ 请输入 1-{len(available_regions)} 之间的数字")
        except ValueError:
            print("✗ 请输入有效的数字")
    
    # 显示预设配置选项
    display_preset_configs()
    
    # 获取配置选择
    while True:
        config_choice = input("\n请选择配置 [1-4]: ").strip()
        if config_choice == "1":
            dn_count = "10"
            speed_limit = "1"
            time_limit = "1000"
            print("✓ 快速测试: 10个IP, 1MB/s, 1000ms")
            break
        elif config_choice == "2":
            dn_count = "20"
            speed_limit = "5"
            time_limit = "500"
            print("✓ 标准测试: 20个IP, 5MB/s, 500ms")
            break
        elif config_choice == "3":
            dn_count = "50"
            speed_limit = "10"
            time_limit = "200"
            print("✓ 高质量测试: 50个IP, 10MB/s, 200ms")
            break
        elif config_choice == "4":
            # 自定义配置
            while True:
                try:
                    dn_count = input("请输入测试IP数量 [默认: 10]: ").strip()
                    if not dn_count:
                        dn_count = "10"
                    dn_count_int = int(dn_count)
                    if dn_count_int <= 0:
                        print("✗ 请输入大于0的数字")
                        continue
                    if dn_count_int > 1000:
                        print("警告: 测试数量过多，可能需要很长时间")
                        confirm = input("  是否继续？[y/N]: ").strip().lower()
                        if confirm != 'y':
                            continue
                    break
                except ValueError:
                    print("✗ 请输入有效的数字")
            
            # 获取下载速度下限
            while True:
                speed_limit = input("请输入下载速度下限 (MB/s) [默认: 1]: ").strip()
                if not speed_limit:
                    speed_limit = "1"
                
                try:
                    speed_limit_float = float(speed_limit)
                    if speed_limit_float < 0:
                        print("✗ 请输入大于等于0的数字")
                        continue
                    if speed_limit_float > 100:
                        print("警告: 速度阈值过高，可能找不到符合条件的IP")
                        confirm = input("  是否继续？[y/N]: ").strip().lower()
                        if confirm != 'y':
                            continue
                    break
                except ValueError:
                    print("✗ 请输入有效的数字")
            
            # 获取延迟阈值
            while True:
                time_limit = input("请输入延迟阈值 (ms) [默认: 1000]: ").strip()
                if not time_limit:
                    time_limit = "1000"
                
                try:
                    time_limit_int = int(time_limit)
                    if time_limit_int <= 0:
                        print("✗ 请输入大于0的数字")
                        continue
                    if time_limit_int > 5000:
                        print("警告: 延迟阈值过高，可能影响使用体验")
                        confirm = input("  是否继续？[y/N]: ").strip().lower()
                        if confirm != 'y':
                            continue
                    break
                except ValueError:
                    print("✗ 请输入有效的数字")
            
            print(f"✓ 自定义配置: {dn_count}个IP, {speed_limit}MB/s, {time_limit}ms")
            break
        else:
            print("✗ 无效选择，请输入 1-4")
    
    print(f"\n测速参数: 地区={cfcolo}, 测试{dn_count}个IP, 速度下限{speed_limit}MB/s, 延迟上限{time_limit}ms")
    print("模式: 常规测速（指定地区）")
    
    # 从地区扫描结果中提取该地区的IP进行测速
    if os.path.exists("region_scan.csv"):
        print(f"\n正在从扫描结果中提取 {cfcolo} 地区的IP...")
        
        # 读取该地区的IP
        region_ips = []
        with open("region_scan.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                colo = (row.get('地区码') or '').strip()
                if colo == cfcolo:
                    ip = (row.get('IP 地址') or '').strip()
                    if ip:
                        region_ips.append(ip)
        
        if region_ips:
            # 创建该地区的IP文件
            region_ip_file = f"{cfcolo.lower()}_ips.txt"
            with open(region_ip_file, 'w', encoding='utf-8') as f:
                for ip in region_ips:
                    f.write(f"{ip}\n")
            
            print(f"找到 {len(region_ips)} 个 {cfcolo} 地区的IP，开始测速...")
            
            # 使用该地区的IP文件进行测速
            os_type, arch_type = get_system_info()
            exec_name = download_cloudflare_speedtest(os_type, arch_type)
            
            # 构建测速命令
            if sys.platform == "win32":
                cmd = [exec_name]
            else:
                cmd = [f"./{exec_name}"]
            
            cmd.extend([
                "-f", region_ip_file,
                "-dn", dn_count,
                "-sl", speed_limit,
                "-tl", time_limit,
                "-o", "result.csv"
            ])
            
            print(f"\n运行命令: {' '.join(cmd)}")
            print("=" * 50)
            
            # 运行测速
            result = subprocess.run(cmd, encoding='utf-8', errors='replace')
            
            # 清理临时文件
            if os.path.exists(region_ip_file):
                os.remove(region_ip_file)
            
            if result.returncode == 0:
                print("\n✅ 测速完成！结果已保存到 result.csv")
                
                # 询问是否上报结果
                upload_results_to_api("result.csv")
            else:
                print("\n❌ 测速失败")
        else:
            print(f"❌ 未找到 {cfcolo} 地区的IP")
    else:
        print("❌ 未找到地区扫描结果文件")
    
    return cfcolo, dn_count, speed_limit, time_limit


def generate_proxy_list(result_file="result.csv", output_file="ips_ports.txt"):
    """从测速结果生成反代IP列表"""
    if not os.path.exists(result_file):
        print(f"未找到测速结果文件: {result_file}")
        return False
    
    try:
        import csv
        
        print(f"\n正在生成反代IP列表...")
        
        # 读取CSV文件
        with open(result_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            print("测速结果文件为空")
            return False
        
        # 生成反代IP列表
        proxy_ips = []
        for row in rows:
            # 查找IP和端口列
            ip = None
            port = None
            
            # 查找IP列
            for key in row.keys():
                if 'ip' in key.lower() and '地址' in key and row[key] is not None:
                    ip = str(row[key]).strip()
                    break
                elif key.lower() == 'ip' and row[key] is not None:
                    ip = str(row[key]).strip()
                    break
            
            # 查找端口列
            for key in row.keys():
                if '端口' in key and row[key] is not None:
                    port = str(row[key]).strip()
                    break
                elif key.lower() == 'port' and row[key] is not None:
                    port = str(row[key]).strip()
                    break
            
            # 如果IP地址中包含端口信息（如 1.2.3.4:443），提取端口
            if ip and ':' in ip:
                ip_parts = ip.split(':')
                if len(ip_parts) == 2:
                    ip = ip_parts[0]  # 提取纯IP地址
                    if not port:  # 如果还没有找到端口，使用IP中的端口
                        port = ip_parts[1]
            
            # 如果没有找到端口，使用默认值
            if not port:
                port = '443'
            
            if ip and port:
                proxy_ips.append(f"{ip}:{port}")
        
        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            for proxy in proxy_ips:
                f.write(proxy + '\n')
        
        print(f"反代IP列表已生成: {output_file}")
        print(f"共生成 {len(proxy_ips)} 个反代IP")
        print(f"📝 格式: IP:端口 (如: 1.2.3.4:443)")
        
        # 显示前10个IP作为示例
        if proxy_ips:
            print(f"\n前10个反代IP示例:")
            for i, proxy in enumerate(proxy_ips[:10], 1):
                print(f"  {i:2d}. {proxy}")
            if len(proxy_ips) > 10:
                print(f"  ... 还有 {len(proxy_ips) - 10} 个IP")
        
        return True
        
    except Exception as e:
        print(f"生成反代IP列表失败: {e}")
        return False


def run_speedtest_with_file(ip_file, dn_count, speed_limit, time_limit):
    """使用指定IP文件运行测速（反代模式，不需要机场码）"""
    try:
        # 获取系统信息
        os_type, arch_type = get_system_info()
        exec_name = download_cloudflare_speedtest(os_type, arch_type)
        
        # 构建命令（反代模式使用TCPing，专注于端口信息）
        cmd = [
            f"./{exec_name}",
            "-f", ip_file,
            "-dn", dn_count,
            "-sl", speed_limit,
            "-tl", time_limit,
            "-p", "20"  # 显示前20个结果
        ]
        
        print(f"\n运行命令: {' '.join(cmd)}")
        print("=" * 50)
        
        # 运行测速 - 实时显示输出
        print("正在运行测速，请稍候...")
        result = subprocess.run(cmd, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            print("\n测速完成！")
            print("结果已保存到 result.csv")
        else:
            print(f"\n测速失败，返回码: {result.returncode}")
        
        # 等待用户按键，不自动关闭窗口
        input("\n按回车键退出...")
        return 0
        
    except Exception as e:
        print(f"运行测速失败: {e}")
        return 1


def run_speedtest(exec_name, cfcolo, dn_count, speed_limit, time_limit):
    """运行 CloudflareSpeedTest"""
    print(f"\n开始运行 CloudflareSpeedTest...")
    print(f"测试参数:")
    print(f"  - 机场码: {cfcolo} ({AIRPORT_CODES.get(cfcolo, {}).get('name', '未知')})")
    print(f"  - 测试 IP 数量: {dn_count}")
    print(f"  - 下载速度阈值: {speed_limit} MB/s")
    print(f"  - 延迟阈值: {time_limit} ms")
    print("-" * 50)
    
    # 构建命令
    if sys.platform == "win32":
        cmd = [exec_name]
    else:
        cmd = [f"./{exec_name}"]
    
    cmd.extend([
        "-dn", dn_count,
        "-sl", speed_limit,
        "-tl", time_limit,
        "-f", CLOUDFLARE_IP_FILE
    ])
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\nCloudflareSpeedTest 任务完成！")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n运行失败: {e}")
        return e.returncode
    except FileNotFoundError:
        print(f"\n找不到可执行文件: {exec_name}")
        return 1


def main():
    """主函数"""
    # 设置控制台编码（Windows 兼容）
    if sys.platform == "win32":
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except:
            pass
    
    print("=" * 80)
    print(" Cloudflare SpeedTest 跨平台自动化脚本")
    print("=" * 80)
    print(" 支持 Windows / Linux / macOS (Darwin)")
    print(f" 内置 {len(AIRPORT_CODES)} 个全球数据中心机场码")
    print(" 支持单个/多机场码/地区优选测速")
    print(" 支持优选反代IP列表生成")
    print("=" * 80)
    
    # 获取系统信息
    os_type, arch_type = get_system_info()
    print(f"\n[系统信息]")
    print(f"  操作系统: {os_type}")
    print(f"  架构类型: {arch_type}")
    print(f"  Python版本: {sys.version.split()[0]}")
    
    # 加载本地机场码配置（如果存在）
    print(f"\n[配置加载]")
    load_local_airport_codes()
    
    # 下载 CloudflareSpeedTest
    print(f"\n[程序准备]")
    exec_name = download_cloudflare_speedtest(os_type, arch_type)
    
    # 选择 IP 版本
    ip_version, ip_file = select_ip_version()
    
    # 下载或生成 Cloudflare IP 列表
    if not download_cloudflare_ips(ip_version, ip_file):
        print("❌ 准备IP列表失败")
        return 1
    
    # 获取用户输入
    print(f"\n[参数配置]")
    print("=" * 60)
    print(" GitHub https://github.com/byJoey/yx-tools")
    print(" YouTube https://www.youtube.com/@Joeyblog")
    print(" 博客 https://joeyblog.net")
    print(" Telegram交流群: https://t.me/+ft-zI76oovgwNmRh")
    print("=" * 60)
    result = get_user_input(ip_file)
    
    # 检查是否是优选反代模式
    if result == (None, None, None, None):
        print("\n优选反代功能已完成，程序退出")
        # Windows 系统添加暂停，避免窗口立即关闭
        if sys.platform == "win32":
            print("\n" + "=" * 60)
            input("按 Enter 键退出...")
        return 0
    
    cfcolo, dn_count, speed_limit, time_limit = result
    
    # 常规测速模式已经在handle_normal_mode中完成测速
    print(f"\n常规测速已完成")
    
    # Windows 系统添加暂停，避免窗口立即关闭
    if sys.platform == "win32":
        print("\n" + "=" * 60)
        input("按 Enter 键退出...")
    
    return 0


def load_config():
    """从配置文件加载上次保存的配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"⚠️  读取配置文件失败: {e}")
            return None
    return None


def save_config(worker_domain, uuid):
    """保存配置到文件"""
    try:
        config = {
            "worker_domain": worker_domain,
            "uuid": uuid,
            "last_used": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️  保存配置失败: {e}")
        return False


def clear_config():
    """清除保存的配置"""
    try:
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            print("✅ 已清除保存的配置")
            return True
    except Exception as e:
        print(f"⚠️  清除配置失败: {e}")
        return False


def upload_results_to_api(result_file="result.csv"):
    """上报优选结果到 Cloudflare Workers API"""
    print("\n" + "=" * 70)
    print(" 优选结果上报功能")
    print("=" * 70)
    print(" 此功能可以将测速结果上报到您的 Cloudflare Workers API")
    print(" 需要提供您的 Worker 域名和 UUID或者路径")
    print("=" * 70)
    
    # 询问是否上报
    choice = input("\n是否要上报优选结果？[y/N]: ").strip().lower()
    if choice not in ['y', 'yes']:
        print("跳过上报")
        return
    
    # 检查结果文件是否存在
    if not os.path.exists(result_file):
        print(f"❌ 未找到测速结果文件: {result_file}")
        print("请先完成测速后再上报结果")
        return
    
    # 尝试加载保存的配置
    saved_config = load_config()
    worker_domain = None
    uuid = None
    
    if saved_config:
        saved_domain = saved_config.get('worker_domain', '')
        saved_uuid = saved_config.get('uuid', '')
        last_used = saved_config.get('last_used', '未知')
        
        print(f"\n💾 检测到上次使用的配置:")
        print(f"   Worker 域名: {saved_domain}")
        print(f"   UUID或者路径: {saved_uuid}")
        print(f"   上次使用: {last_used}")
        print("\n是否使用上次的配置？")
        print("  1. 是 - 使用上次配置")
        print("  2. 否 - 输入新的URL")
        print("  3. 清除配置 - 删除保存的配置")
        
        while True:
            config_choice = input("\n请选择 [1/2/3]: ").strip()
            if config_choice == "1":
                worker_domain = saved_domain
                uuid = saved_uuid
                print(f"\n✅ 使用保存的配置")
                print(f"   Worker 域名: {worker_domain}")
                print(f"   UUID或者路径: {uuid}")
                # 更新最后使用时间
                save_config(worker_domain, uuid)
                break
            elif config_choice == "2":
                print("\n请输入新的配置...")
                break
            elif config_choice == "3":
                clear_config()
                print("请重新输入配置...")
                break
            else:
                print("✗ 请输入 1、2 或 3")
    
    # 如果没有使用保存的配置，则获取新的URL
    if not worker_domain or not uuid:
        # 获取管理页面 URL
        print("\n📝 请输入您的 Worker 管理页面 URL")
        print("示例: https://你的域名/你的UUID或者路径")
        print("提示: 直接复制浏览器地址栏的完整URL即可")
        
        management_url = input("\n管理页面 URL: ").strip()
        if not management_url:
            print("❌ URL 不能为空")
            return
    
        # 解析 URL，提取域名和 UUID
        try:
            from urllib.parse import urlparse
            
            # 移除可能的协议前缀和尾部斜杠
            management_url = management_url.strip().rstrip('/')
            
            # 如果没有协议前缀，添加 https://
            if not management_url.startswith(('http://', 'https://')):
                management_url = 'https://' + management_url
            
            # 解析 URL
            parsed = urlparse(management_url)
            worker_domain = parsed.netloc
            
            # 从路径中提取 UUID（不再验证格式）
            if not worker_domain:
                print("❌ 无法解析域名，请检查 URL 格式")
                return
            
            # 从路径中提取最后一个非空部分作为UUID
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            if not path_parts:
                print("❌ 无法从 URL 中提取 UUID或者路径")
                print("   请确保 URL 包含 UUID或者路径")
                print("   格式示例: https://域名/UUID或者路径")
                return
            
            uuid = path_parts[-1]
            
            # 显示解析结果
            print(f"\n✅ 成功解析配置:")
            print(f"   Worker 域名: {worker_domain}")
            print(f"   UUID或者路径: {uuid}")
            
            # 询问是否保存配置
            save_choice = input("\n是否保存此配置供下次使用？[Y/n]: ").strip().lower()
            if save_choice not in ['n', 'no']:
                if save_config(worker_domain, uuid):
                    print("✅ 配置已保存")
                else:
                    print("⚠️  配置保存失败，但不影响本次上报")
            
        except Exception as e:
            print(f"❌ URL 解析失败: {e}")
            print("   请检查 URL 格式是否正确")
            return
    
    # 构建 API URL
    api_url = f"https://{worker_domain}/{uuid}/api/preferred-ips"
    
    # 检查是否已有数据
    print("\n🔍 正在检查现有优选IP...")
    try:
        try:
            response = requests.get(api_url, timeout=10)
        except ImportError as e:
            # SSL模块不可用，静默切换到curl
            if "SSL module is not available" in str(e):
                response = curl_request(api_url, method='GET', timeout=10)
            else:
                raise
        
        if response.status_code == 200:
            result = response.json()
            existing_count = result.get('count', 0)
            if existing_count > 0:
                print(f"⚠️  发现已存在 {existing_count} 个优选IP")
                print("\n是否要清空现有数据后再添加新的？")
                print("  1. 是 - 清空后添加（推荐，避免重复）")
                print("  2. 否 - 直接添加（可能有重复提示）")
                
                while True:
                    clear_choice = input("\n请选择 [1/2]: ").strip()
                    if clear_choice == "1":
                        print("准备清空现有数据...")
                        should_clear = True
                        break
                    elif clear_choice == "2":
                        print("将直接添加，跳过清空")
                        should_clear = False
                        break
                    else:
                        print("✗ 请输入 1 或 2")
            else:
                should_clear = False
                print("✅ 当前无数据，将直接添加")
        else:
            should_clear = False
            print("⚠️  无法获取现有数据状态，将直接尝试添加")
    except Exception as e:
        should_clear = False
        print(f"⚠️  检查现有数据失败: {e}")
        print("将继续尝试添加...")
    
    # 读取测速结果
    print("\n📊 正在读取测速结果...")
    try:
        best_ips = []
        with open(result_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 安全获取数据，避免NoneType错误
                ip = (row.get('IP 地址') or '').strip()
                port = (row.get('端口') or '').strip()
                
                # 尝试多种可能的列名来获取速度
                speed = ''
                for speed_key in ['下载速度(MB/s)', '下载速度 (MB/s)', '下载速度']:
                    if speed_key in row and row[speed_key] is not None:
                        speed = str(row[speed_key]).strip()
                        break
                
                # 尝试多种可能的列名来获取延迟
                latency = ''
                for latency_key in ['平均延迟', '延迟', 'latency']:
                    if latency_key in row and row[latency_key] is not None:
                        latency = str(row[latency_key]).strip()
                        break
                
                # 获取地区码
                region_code = (row.get('地区码') or '').strip()
                
                # 如果IP地址中包含端口信息
                if ip and ':' in ip:
                    ip_parts = ip.split(':')
                    if len(ip_parts) == 2:
                        ip = ip_parts[0]
                        if not port:
                            port = ip_parts[1]
                
                # 设置默认端口
                if not port:
                    port = '443'
                
                if ip:
                    try:
                        speed_val = float(speed) if speed else 0
                        latency_val = latency if latency else 'N/A'
                        
                        # 获取地区中文名称
                        region_name = '未知地区'
                        if region_code and region_code in AIRPORT_CODES:
                            region_name = AIRPORT_CODES[region_code].get('name', region_code)
                        elif region_code:
                            region_name = region_code
                        
                        best_ips.append({
                            'ip': ip,
                            'port': int(port),
                            'speed': speed_val,
                            'latency': latency_val,
                            'region_code': region_code,
                            'region_name': region_name
                        })
                    except ValueError:
                        continue
        
        if not best_ips:
            print("❌ 未找到有效的测速结果")
            return
        
        print(f"✅ 找到 {len(best_ips)} 个测速结果")
        
        # 询问要上报多少个结果
        while True:
            count_input = input(f"\n请输入要上报的IP数量 [默认: 10, 最多: {len(best_ips)}]: ").strip()
            if not count_input:
                upload_count = min(10, len(best_ips))
                break
            try:
                upload_count = int(count_input)
                if upload_count <= 0:
                    print("✗ 请输入大于0的数字")
                    continue
                if upload_count > len(best_ips):
                    print(f"⚠️  最多只能上报 {len(best_ips)} 个结果")
                    upload_count = len(best_ips)
                break
            except ValueError:
                print("✗ 请输入有效的数字")
        
        # 显示将要上报的IP
        print(f"\n将上报以下 {upload_count} 个优选IP:")
        print("-" * 70)
        for i, ip_info in enumerate(best_ips[:upload_count], 1):
            region_display = f"{ip_info['region_name']}" if ip_info.get('region_name') else '未知地区'
            print(f"  {i:2d}. {ip_info['ip']:15s}:{ip_info['port']:<5d} - {ip_info['speed']:.2f} MB/s - {region_display} - 延迟: {ip_info['latency']}")
        print("-" * 70)
        
        # 确认上报
        confirm = input("\n确认上报以上IP？[Y/n]: ").strip().lower()
        if confirm in ['n', 'no']:
            print("取消上报")
            return
        
        # 如果需要清空，先执行清空操作
        if should_clear:
            print("\n🗑️  正在清空现有数据...")
            try:
                try:
                    delete_response = requests.delete(
                        api_url,
                        json={"all": True},
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                except ImportError as e:
                    # SSL模块不可用，静默切换到curl
                    if "SSL module is not available" in str(e):
                        delete_response = curl_request(
                            api_url,
                            method='DELETE',
                            data={"all": True},
                            headers={"Content-Type": "application/json"},
                            timeout=10
                        )
                    else:
                        raise
                
                if delete_response.status_code == 200:
                    print("✅ 现有数据已清空")
                else:
                    print(f"⚠️  清空失败 (HTTP {delete_response.status_code})，继续尝试添加...")
            except Exception as e:
                print(f"⚠️  清空操作失败: {e}，继续尝试添加...")
        
        # 构建批量上报数据
        print("\n🚀 开始批量上报优选IP...")
        batch_data = []
        for ip_info in best_ips[:upload_count]:
            # 构建节点名称：地区名-速度MB/s
            region_name = ip_info.get('region_name', '未知地区')
            speed = ip_info['speed']
            name = f"{region_name}-{speed:.2f}MB/s"
            
            batch_data.append({
                "ip": ip_info['ip'],
                "port": ip_info['port'],
                "name": name
            })
        
        # 发送批量POST请求
        use_curl_fallback = False
        response = None
        success_count = 0
        fail_count = 0
        skipped_count = 0
        
        try:
            try:
                response = requests.post(
                    api_url,
                    json=batch_data,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
            except ImportError as e:
                # SSL模块不可用，静默切换到curl备用方案
                if "SSL module is not available" in str(e):
                    use_curl_fallback = True
                    response = curl_request(
                        api_url,
                        method='POST',
                        data=batch_data,
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                else:
                    raise
            
            # 处理响应
            if response and response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    success_count = result.get('added', 0)
                    fail_count = result.get('failed', 0)
                    skipped_count = result.get('skipped', 0)
                    
                    print("✅ 批量上报完成！")
                    print(f"   成功添加: {success_count} 个")
                    if skipped_count > 0:
                        print(f"   跳过重复: {skipped_count} 个")
                    if fail_count > 0:
                        print(f"   失败: {fail_count} 个")
                else:
                    print(f"❌ 批量上报失败: {result.get('error', '未知错误')}")
                    fail_count = upload_count
            elif response and response.status_code == 403:
                print(f"❌ 认证失败！请检查：")
                print(f"   1. UUID或者路径是否正确")
                print(f"   2. 是否在配置页面开启了 'API管理' 功能")
                fail_count = upload_count
            elif response:
                print(f"❌ 批量上报失败 (HTTP {response.status_code})")
                try:
                    error_detail = response.json()
                    print(f"   错误详情: {error_detail.get('error', '无详情')}")
                except:
                    pass
                fail_count = upload_count
                
        except requests.exceptions.Timeout:
            print(f"❌ 请求超时，请检查网络连接")
            print(f"   建议：检查网络连接或稍后重试")
            fail_count = upload_count
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络错误: {e}")
            print(f"   建议：检查网络连接或API地址是否正确")
            fail_count = upload_count
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            print(f"   建议：检查配置是否正确，或联系技术支持")
            fail_count = upload_count
        
        # 显示统计信息
        print("\n" + "=" * 70)
        print(" 批量上报完成！")
        print("=" * 70)
        print(f"  ✅ 成功添加: {success_count} 个")
        if 'skipped_count' in locals() and skipped_count > 0:
            print(f"  ⚠️  跳过重复: {skipped_count} 个")
        if fail_count > 0:
            print(f"  ❌ 失败: {fail_count} 个")
        print(f"  📊 总计: {upload_count} 个")
        print("=" * 70)
        
        if success_count > 0:
            print(f"\n💡 提示:")
            print(f"   - 您可以访问 https://{worker_domain}/{uuid} 查看管理页面")
            print(f"   - 优选IP已添加，订阅生成时会自动使用")
            print(f"   - 批量上报速度更快，避免了逐个请求的超时问题")
        
    except Exception as e:
        print(f"❌ 读取测速结果失败: {e}")
        import traceback
        traceback.print_exc()


def detect_available_regions():
    """检测可用地区"""
    # 检查是否已有检测结果文件
    if os.path.exists("region_scan.csv"):
        print("发现已有的地区扫描结果文件")
        choice = input("是否需要重新扫描？[y/N]: ").strip().lower()
        if choice != 'y':
            print("使用已有检测结果...")
            # 直接读取已有文件
            available_regions = []
            region_counts = {}
            
            with open("region_scan.csv", 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    colo = (row.get('地区码') or '').strip()
                    if colo and colo != 'N/A':
                        region_counts[colo] = region_counts.get(colo, 0) + 1
            
            # 构建地区列表（按IP数量排序）
            for colo, count in sorted(region_counts.items(), key=lambda x: x[1], reverse=True):
                region_name = "未知地区"
                for code, info in AIRPORT_CODES.items():
                    if code == colo:
                        region_name = f"{info.get('name', '')} ({info.get('country', '')})"
                        break
                available_regions.append((colo, region_name, count))
            
            return available_regions
    
    print("正在检测各地区可用性...")
    
    # 获取系统信息
    os_type, arch_type = get_system_info()
    exec_name = download_cloudflare_speedtest(os_type, arch_type)
    
    # 构建检测命令 - 使用HTTPing模式快速检测
    if sys.platform == "win32":
        cmd = [exec_name]
    else:
        cmd = [f"./{exec_name}"]
    
    cmd.extend([
        "-dd",  # 禁用下载测速，只做延迟测试
        "-tl", "9999",  # 高延迟阈值
        "-f", CLOUDFLARE_IP_FILE,
        "-httping",  # 使用HTTPing模式获取地区码
        "-url", "https://jhb.ovh",
        "-o", "region_scan.csv"  # 输出到地区扫描文件
    ])
    
    try:
        print("运行地区检测...")
        print("正在扫描所有地区，请稍候（约需1-2分钟）...")
        print("=" * 50)
        
        # 直接运行命令，显示完整输出
        result = subprocess.run(cmd, timeout=120, encoding='utf-8', errors='replace')
        
        if result.returncode == 0 and os.path.exists("region_scan.csv"):
            # 读取检测结果
            available_regions = []
            region_counts = {}  # 统计每个地区的IP数量
            
            with open("region_scan.csv", 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    colo = (row.get('地区码') or '').strip()
                    if colo and colo != 'N/A':
                        # 统计IP数量
                        if colo not in region_counts:
                            region_counts[colo] = 0
                        region_counts[colo] += 1
            
            # 构建地区列表（按IP数量排序）
            for colo, count in sorted(region_counts.items(), key=lambda x: x[1], reverse=True):
                # 查找地区名称
                region_name = "未知地区"
                for code, info in AIRPORT_CODES.items():
                    if code == colo:
                        region_name = f"{info.get('name', '')} ({info.get('country', '')})"
                        break
                available_regions.append((colo, region_name, count))
            
            # 保留地区扫描结果文件，不删除
            print("地区扫描结果已保存到 region_scan.csv")
            
            return available_regions
        else:
            print("地区检测失败，使用默认地区列表")
            # 返回默认的主要地区
            default_regions = [
                ('HKG', '香港 (中国)', 0),
                ('SIN', '新加坡 (新加坡)', 0),
                ('NRT', '东京 (日本)', 0),
                ('ICN', '首尔 (韩国)', 0),
                ('LAX', '洛杉矶 (美国)', 0),
                ('FRA', '法兰克福 (德国)', 0),
                ('LHR', '伦敦 (英国)', 0)
            ]
            return default_regions
            
    except Exception as e:
        print(f"地区检测出错: {e}")
        # 返回默认地区
        default_regions = [
            ('HKG', '香港 (中国)', 0),
            ('SIN', '新加坡 (新加坡)', 0),
            ('NRT', '东京 (日本)', 0),
            ('ICN', '首尔 (韩国)', 0),
            ('LAX', '洛杉矶 (美国)', 0),
            ('FRA', '法兰克福 (德国)', 0),
            ('LHR', '伦敦 (英国)', 0)
        ]
        return default_regions

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        # Windows 系统添加暂停，避免窗口立即关闭
        if sys.platform == "win32":
            print("\n" + "=" * 60)
            input("按 Enter 键退出...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        print(f"   建议：")
        print(f"   1. 检查网络连接")
        print(f"   2. 确保有足够的磁盘空间")
        print(f"   3. 检查Python环境是否正常")
        print(f"   4. 如果问题持续，请联系技术支持")
        # Windows 系统添加暂停，避免窗口立即关闭
        if sys.platform == "win32":
            print("\n" + "=" * 60)
            input("按 Enter 键退出...")
        sys.exit(1)

