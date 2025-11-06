import os
import sys
import csv
import shutil
import subprocess
import datetime
import requests
import zipfile
from typing import Tuple, Optional, List
import time
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv('/app/.env')

# ==================== 错误码定义 ====================
EXIT_SUCCESS = 0         # 正常退出（不重启）
EXIT_FATAL = 1           # 致命错误（需重启，最多3次）
EXIT_NON_FATAL = 2       # 非致命错误（无需重启，等待定时任务）


# ==================== 配置常量 ====================
TOOL_TYPE = "proxy"  # 可切换为 "official"
DEFAULT_PORT = "443"
OUTPUT_TXT = "cfst_ips.txt"
DEFAULT_RESULT_CSV = "cfst_result.csv"
DEFAULT_CLOUDFLARE_IP_FILE = "cloudflare_ips.txt"

ACCELERATOR_DOMAINS = [
    "https://gh-proxy.com/",
    "https://fastly.jsdelivr.net/",
    "https://testingcf.jsdelivr.net/",
    "https://cdn.jsdelivr.net/"
]

CUSTOM_PARAMS = {
    "f": "Cloudflare.txt",
    "dn": "10",
    "sl": "1",
    "tl": "1000",
    "o": DEFAULT_RESULT_CSV,
    "n": "50"
}

CUSTOM_FLAG_PARAMS = {
    "httping": False,
    "dd": False,
    "allip": False,
    "debug": False
}

TOOL_REPO = {
    "official": "https://github.com/XIU2/CloudflareSpeedTest/releases/latest/download/",
    "proxy": "https://github.com/byJoey/CloudflareSpeedTest/releases/download/v1.0/"
}


# ==================== 参数说明 ====================
DELAY_PARAMS = {
    "n": {"type": "值参数", "default": "200", "description": "延迟测速线程；越多延迟测速越快，性能弱的设备（如路由器）请勿太高，最大1000"},
    "t": {"type": "值参数", "default": "4", "description": "单个IP延迟测速次数；默认4次"},
    "tp": {"type": "值参数", "default": "443", "description": "指定测速端口；延迟测速/下载测速时使用的端口"},
    "httping-code": {"type": "值参数", "default": "200 301 302", "description": "有效状态代码；HTTPing延迟测速时网页返回的有效HTTP状态码，仅限一个"},
    "cfcolo": {"type": "值参数", "default": "空（所有地区）", "description": "匹配指定地区；IATA机场地区码或国家/城市码，英文逗号分隔，仅HTTPing模式可用。例如：Cloudflare使用HKG,LAX（机场码）；CDN77使用US,CN（国家码）"}
}

DELAY_FLAG_PARAMS = {
    "httping": {"type": "开关参数", "default": "禁用（默认TCPing）", "description": "切换测速模式；延迟测速模式改为HTTP协议，所用测试地址为[-url]参数。启用后会从响应头获取IP地区码（支持多种CDN）"}
}

DOWNLOAD_PARAMS = {
    "dn": {"type": "值参数", "default": "10", "description": "下载测速数量；延迟测速并排序后，从最低延迟起下载测速的数量"},
    "dt": {"type": "值参数", "default": "10", "description": "下载测速时间；单个IP下载测速最长时间，不能太短（默认10秒）"},
    "url": {"type": "值参数", "default": "https://cf.xiu2.xyz/url", "description": "指定测速地址；延迟测速(HTTPing)/下载测速时使用的地址，默认地址不保证可用性，建议自建。下载时会从响应头获取IP地区码（支持多种CDN）"}
}

FILTER_PARAMS = {
    "tl": {"type": "值参数", "default": "9999", "description": "平均延迟上限；只输出低于指定平均延迟的IP（单位：ms），各条件可搭配使用"},
    "tll": {"type": "值参数", "default": "0", "description": "平均延迟下限；只输出高于指定平均延迟的IP（单位：ms）"},
    "tlr": {"type": "值参数", "default": "1.00", "description": "丢包几率上限；只输出低于/等于指定丢包率的IP，范围0.00~1.00，0表示过滤掉任何丢包的IP"},
    "sl": {"type": "值参数", "default": "0.00", "description": "下载速度下限；只输出高于指定下载速度的IP（单位：MB/s），凑够[-dn]数量才会停止测速"}
}

OUTPUT_PARAMS = {
    "p": {"type": "值参数", "default": "10", "description": "显示结果数量；测速后直接显示指定数量的结果，为0时不显示结果直接退出"},
    "f": {"type": "值参数", "default": "ip.txt", "description": "IP段数据文件；如路径含有空格请加上引号，支持其他CDN IP段"},
    "ip": {"type": "值参数", "default": "空", "description": "指定IP段数据；直接通过参数指定要测速的IP段数据，英文逗号分隔（如1.1.1.1,2.2.2.2/24）"},
    "o": {"type": "值参数", "default": "result.csv", "description": "写入结果文件；如路径含有空格请加上引号，值为空时不写入文件（-o \"\"）"}
}

OTHER_PARAMS = {
    "dd": {"type": "开关参数", "default": "禁用", "description": "禁用下载测速；禁用后测速结果会按延迟排序（默认按下载速度排序）"},
    "allip": {"type": "开关参数", "default": "禁用", "description": "测速全部的IP；对IP段中的每个IP（仅支持IPv4）进行测速（默认每个/24段随机测速一个IP）"},
    "debug": {"type": "开关参数", "default": "禁用", "description": "调试输出模式；会在非预期情况下输出更多日志以便判断原因（如HTTPing失败原因）"}
}

VALUE_PARAMS = [
    "n", "t", "tp", "httping-code", "cfcolo",
    "dn", "dt", "url",
    "tl", "tll", "tlr", "sl",
    "p", "f", "ip", "o"
]
FLAG_PARAMS = [
    "httping", "dd", "allip", "debug"
]


# ==================== 日志工具函数 ====================
def get_timestamp():
    """获取当前时间戳（格式：YYYY-MM-DD HH:MM:SS）"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_info(module: str, message: str):
    """信息级日志（标准输出）"""
    print(f"[{get_timestamp()}] [INFO] [{module}] {message}")

def log_warn(module: str, message: str):
    """警告级日志（标准输出）"""
    print(f"[{get_timestamp()}] [WARN] [{module}] ⚠️ {message}")

def log_error(module: str, message: str):
    """错误级日志（标准错误输出）"""
    print(f"[{get_timestamp()}] [ERROR] [{module}] ❌ {message}", file=sys.stderr)

def log_download(message: str):
    """下载相关日志（复用统一格式）"""
    log_info("下载器", message)


# ==================== 工具函数 ====================
def get_system_info() -> Tuple[str, str]:
    """获取操作系统类型和架构信息"""
    os_type = sys.platform
    if os_type.startswith('linux'):
        os_type = 'linux'
    elif os_type.startswith('win'):
        os_type = 'win'
    elif os_type.startswith('darwin'):
        os_type = 'mac'
    else:
        raise ValueError(f"不支持的操作系统: {os_type}")

    # 修正架构识别逻辑
    arch_type = "amd64"  # 默认值
    if os_type == 'linux':
        try:
            # 调用uname -m获取真实架构（arm64设备输出aarch64，amd64输出x86_64）
            uname_output = subprocess.run(
                ["uname", "-m"], capture_output=True, text=True, check=True
            ).stdout.strip()
            if uname_output == "aarch64":
                arch_type = "arm64"
            elif uname_output == "x86_64":
                arch_type = "amd64"
            else:
                # 其他架构（如386、mips等，根据实际需求处理）
                arch_type = uname_output
        except subprocess.CalledProcessError:
            # 失败时 fallback 到原逻辑（仅区分32/64位）
            arch_type = "amd64" if sys.maxsize > 2**32 else "386"
    elif os_type == 'mac':
        try:
            uname_output = subprocess.run(
                ["uname", "-m"], capture_output=True, text=True, check=True
            ).stdout.strip()
            arch_type = "arm64" if uname_output == "arm64" else "amd64"
        except subprocess.CalledProcessError:
            arch_type = "amd64" if sys.maxsize > 2**32 else "386"
    else:
        # Windows默认逻辑（amd64/386）
        arch_type = "amd64" if sys.maxsize > 2**32 else "386"

    return os_type, arch_type


def get_accelerator_urls(original_url: str) -> List[str]:
    """生成所有可能的加速URL，包括原始URL（最后尝试）"""
    custom_proxy = os.environ.get("GITHUB_PROXY", "").strip()
    accelerators = []
    
    if custom_proxy:
        if not custom_proxy.endswith('/'):
            custom_proxy += '/'
        accelerators.append(custom_proxy)
    
    accelerators.extend(ACCELERATOR_DOMAINS)
    
    unique_accelerators = []
    seen = set()
    for acc in accelerators:
        if acc not in seen:
            seen.add(acc)
            unique_accelerators.append(acc)
    
    accelerated_urls = [f"{acc}{original_url}" for acc in unique_accelerators]
    accelerated_urls.append(original_url)
    
    return accelerated_urls


def _get_tool_filename() -> str:
    """根据当前系统/架构/TOOL_TYPE，返回压缩包文件名（不带路径）"""
    os_type, arch_type = get_system_info()
    base = 'cfst' if TOOL_TYPE == 'official' else 'CloudflareST_proxy'
    ext = 'zip' if os_type in ('win', 'mac') else 'tar.gz'
    return f"{base}_{os_type}_{arch_type}.{ext}"


def download_file(url: str, filename: str, timeout: int = 60, retries: int = 3) -> bool:
    """通用下载函数，支持多种方式与自动重试"""
    for attempt in range(1, retries + 1):
        log_download(f"尝试下载 ({attempt}/{retries}): {url}")

        # 方法1: requests
        try:
            with requests.get(url, stream=True, timeout=timeout) as resp:
                resp.raise_for_status()
                with open(filename, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                if os.path.getsize(filename) > 0:
                    log_download(f"下载成功: {filename}")
                    return True
                else:
                    log_warn("下载器", "下载文件为空")
                    os.remove(filename)
        except Exception as e:
            log_warn("下载器", f"requests 失败: {e}")

        # 方法2: curl
        try:
            result = subprocess.run(
                ["curl", "-L", "-o", filename, url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout
            )
            if result.returncode == 0 and os.path.getsize(filename) > 0:
                log_download(f"curl 下载成功: {filename}")
                return True
        except Exception as e:
            log_warn("下载器", f"curl 失败: {e}")

        # 方法3: wget
        try:
            result = subprocess.run(
                ["wget", "-O", filename, url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout
            )
            if result.returncode == 0 and os.path.getsize(filename) > 0:
                log_download(f"wget 下载成功: {filename}")
                return True
        except Exception as e:
            log_warn("下载器", f"wget 失败: {e}")

        # 方法4: PowerShell (Windows)
        if sys.platform == "win32":
            try:
                ps_cmd = f'Invoke-WebRequest -Uri "{url}" -OutFile "{filename}"'
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout
                )
                if result.returncode == 0 and os.path.getsize(filename) > 0:
                    log_download(f"PowerShell 下载成功: {filename}")
                    return True
            except Exception as e:
                log_warn("下载器", f"PowerShell 失败: {e}")

        # 方法5: urllib
        try:
            import urllib.request
            urllib.request.urlretrieve(url, filename)
            if os.path.getsize(filename) > 0:
                log_download(f"urllib 下载成功: {filename}")
                return True
        except Exception as e:
            log_warn("下载器", f"urllib 失败: {e}")

        # 方法6: HTTPS → HTTP fallback
        if url.startswith("https://"):
            http_url = url.replace("https://", "http://")
            log_download("尝试 HTTP 降级下载")
            try:
                with requests.get(http_url, stream=True, timeout=timeout) as resp:
                    resp.raise_for_status()
                    with open(filename, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    if os.path.getsize(filename) > 0:
                        log_download(f"HTTP 降级下载成功: {filename}")
                        return True
            except Exception as e:
                log_warn("下载器", f"HTTP 降级失败: {e}")

        if os.path.exists(filename):
            os.remove(filename)

        if attempt < retries:
            log_download("等待 2 秒后重试...")
            time.sleep(2)

    log_error("下载器", "所有下载方式均失败")
    return False


def extract_archive(archive_path: str) -> Optional[str]:
    """解压压缩包并返回可执行文件路径"""
    try:
        extract_dir = os.getcwd()
        
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                files = zip_ref.namelist()
                zip_ref.extractall(extract_dir)
        elif archive_path.endswith('.tar.gz'):
            subprocess.run(
                ["tar", "-zxf", archive_path, "-C", extract_dir],
                check=True,
                capture_output=True,
                text=True
            )
            files = subprocess.run(
                ["tar", "-ztf", archive_path],
                capture_output=True,
                text=True
            ).stdout.splitlines()
        else:
            log_error("解压工具", f"不支持的压缩格式: {archive_path}")
            return None

        os_type = get_system_info()[0]
        exec_ext = ".exe" if os_type == 'win' else ""
        exec_files = [f for f in files if f.endswith(exec_ext) and not f.startswith('__MACOSX')]

        if not exec_files:
            log_error("解压工具", f"未在压缩包中找到可执行文件: {files}")
            return None

        exec_name = exec_files[0].split('/')[-1]
        exec_path = os.path.join(extract_dir, exec_name)
        
        if os_type != 'win' and os.path.exists(exec_path):
            os.chmod(exec_path, 0o755)
        
        return exec_path

    except Exception as e:
        log_error("解压工具", f"解压失败: {str(e)}")
        return None


def ensure_speedtest_binary() -> Optional[str]:
    """确保测速工具可执行文件存在"""
    filename = _get_tool_filename()
    exec_name = filename.replace('.zip', '').replace('.tar.gz', '')
    if sys.platform == 'win32':
        exec_name += '.exe'
    exec_path = os.path.join(os.getcwd(), exec_name)

    if os.path.isfile(exec_path):
        log_info("测速工具", f"发现本地已有可执行文件 {exec_name}，跳过下载")
        return exec_path

    if not os.path.exists(filename):
        base_url = TOOL_REPO[TOOL_TYPE]
        original_url = f"{base_url}{filename}"
        attempt_urls = get_accelerator_urls(original_url)
        log_download(f"准备下载工具，将尝试以下加速地址: {[url.split('/')[2] for url in attempt_urls]}")

        download_success = False
        for url in attempt_urls:
            if download_file(url, filename):
                download_success = True
                break

        if not download_success:
            log_error("测速工具", "所有加速域名和原始地址均下载失败")
            return None
    else:
        log_info("测速工具", f"发现本地已有压缩包 {filename}，跳过下载")

    extracted_path = extract_archive(filename)
    if extracted_path and os.path.exists(extracted_path):
        return extracted_path

    return None


def download_cloudflare_ips(ip_version: str = "ipv4", ip_file: str = DEFAULT_CLOUDFLARE_IP_FILE) -> bool:
    """下载Cloudflare IP列表到指定文件"""
    urls = {
        "ipv4": "https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ip.txt",
        "ipv6": "https://raw.githubusercontent.com/XIU2/CloudflareSpeedTest/master/ipv6.txt"
    }
    original_url = urls.get(ip_version)
    if not original_url:
        log_error("IP列表", f"不支持的IP版本: {ip_version}")
        return False

    attempt_urls = get_accelerator_urls(original_url)
    log_download(f"准备下载IP列表，将尝试以下加速地址: {[url.split('/')[2] for url in attempt_urls]}")

    for url in attempt_urls:
        if download_file(url, ip_file):
            return True

    log_error("IP列表", "所有加速域名和原始地址均无法下载IP列表")
    return False


def generate_proxy_list(result_csv: str = DEFAULT_RESULT_CSV) -> bool:
    """从指定测速结果生成代理列表TXT"""
    if not os.path.exists(result_csv):
        log_warn("代理生成", f"未找到测速结果 {result_csv}（可能本次无有效数据）")
        return False

    try:
        with open(result_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            log_warn("代理生成", "测速结果为空（无符合条件的IP）")
            return False

        proxy_ips: List[str] = []
        for row in rows:
            ip = (row.get('IP 地址') or '').strip()
            port = (row.get('端口') or DEFAULT_PORT).strip()
            region = (row.get('地区') or row.get('地区码') or '未知').strip()

            if ip and ':' in ip:
                ip_part, *port_part = ip.split(':', 1)
                ip = ip_part
                port = port_part[0] if port_part and not port else port

            port = port if port.isdigit() else DEFAULT_PORT
            if ip:
                proxy_ips.append(f"{ip}:{port}#{region}")

        unique_proxies = list(dict.fromkeys(proxy_ips))
        with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
            f.write('\n'.join(unique_proxies))

        log_info("代理生成", f"生成代理列表: {len(unique_proxies)} 条记录 → {OUTPUT_TXT}")
        return True
    except Exception as e:
        log_warn("代理生成", f"生成代理列表失败 - {str(e)}")
        return False

def upload_to_github() -> None:
    """上传结果到GitHub仓库（修复加速代理带Token的URL格式）"""
    github_token = os.environ.get('GITHUB_TOKEN')
    github_repo = os.environ.get('GITHUB_REPO')
    if not github_token or not github_repo:
        print(f"[{get_timestamp()}] [WARN] [GitHub上传] ⚠️ 未配置GITHUB_TOKEN和GITHUB_REPO，跳过上传")
        return

    try:
        # 1. 生成加速的仓库URL（修复Token位置）
        original_repo_path = f"github.com/{github_repo}.git"  # 仅保留GitHub路径部分（不含协议）
        original_repo_url = f"https://{original_repo_path}"   # 原始URL（用于最后尝试）
        
        custom_proxy = os.environ.get("GITHUB_PROXY", "").strip()
        accelerators = []
        if custom_proxy:
            if not custom_proxy.endswith('/'):
                custom_proxy += '/'
            accelerators.append(custom_proxy)
        accelerators.extend(ACCELERATOR_DOMAINS)
        
        # 生成带加速的仓库URL列表（处理Token位置）
        accelerated_repo_urls = []
        for acc in accelerators:
            if not acc.endswith('/'):
                continue
            # 提取加速代理的域名部分（如"https://gh-proxy.com/" → "gh-proxy.com"）
            acc_domain = acc.replace("https://", "").replace("/", "")
            # 带Token的加速URL格式：https://{token}@{acc_domain}/{github_repo_path}
            if github_token:
                accelerated_url = f"https://{github_token}@{acc_domain}/{original_repo_path}"
            else:
                accelerated_url = f"{acc}{original_repo_path}"  # 不带Token的正常加速格式
            accelerated_repo_urls.append(accelerated_url)
        
        # 最后尝试原始URL（带Token）
        if github_token:
            original_url_with_token = f"https://{github_token}@github.com/{github_repo}.git"
            accelerated_repo_urls.append(original_url_with_token)
        else:
            accelerated_repo_urls.append(original_repo_url)

        # 2. 准备临时目录（不变）
        temp_dir = os.path.join(
            "/tmp" if sys.platform != "win32" else os.environ.get("TEMP", "."),
            f"github_upload_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        os.makedirs(temp_dir, exist_ok=True)
        repo_dir = os.path.join(temp_dir, "repo")

        # 3. 尝试用加速地址克隆仓库（逻辑不变，使用新的URL列表）
        clone_success = False
        for repo_url in accelerated_repo_urls:
            print(f"[{get_timestamp()}] [INFO] [GitHub上传] 尝试克隆仓库（地址：{repo_url.split('@')[-1]}）")  # 隐藏Token打印
            try:
                subprocess.run(
                    ["git", "clone", repo_url, repo_dir],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                clone_success = True
                break
            except Exception as e:
                print(f"[{get_timestamp()}] [WARN] [GitHub上传] 克隆失败（地址：{repo_url.split('@')[-1]}）：{str(e)}")
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir, ignore_errors=True)

        if not clone_success:
            print(f"[{get_timestamp()}] [ERROR] [GitHub上传] ❌ 所有加速地址均克隆失败")
            return

        # 4. 复制文件并提交（后续步骤不变）
        dest_path = os.path.join(repo_dir, OUTPUT_TXT)
        shutil.copy2(OUTPUT_TXT, dest_path)

        commit_msg = f"Auto-update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        git_cmds = [
            ["git", "-C", repo_dir, "config", "user.email", "bot@example.com"],
            ["git", "-C", repo_dir, "config", "user.name", "SpeedTest Bot"],
            ["git", "-C", repo_dir, "add", OUTPUT_TXT],
            ["git", "-C", repo_dir, "commit", "-m", commit_msg],
            ["git", "-C", repo_dir, "push"]
        ]

        for cmd in git_cmds:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise Exception(f"Git命令失败: {' '.join(cmd)}\n{result.stderr}")

        print(f"[{get_timestamp()}] [INFO] [GitHub上传] ✅ 成功上传到 {github_repo}")

    except Exception as e:
        print(f"[{get_timestamp()}] [WARN] [GitHub上传] ⚠️ GitHub上传失败 - {str(e)}")
    finally:
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            
def run_speed_test(exec_path: str, value_params: dict, flag_params: set) -> bool:
    """执行测速命令"""
    cmd = [exec_path]

    for param, value in value_params.items():
        cmd.extend([f"-{param}", value])

    for param in flag_params:
        cmd.append(f"-{param}")

    log_info("测速执行", f"执行测速: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=0
        )
        if result.returncode != 0:
            log_warn("测速执行", f"测速命令执行失败（返回码：{result.returncode}）")
            return False
        log_info("测速执行", "测速完成")
        return True
    except Exception as e:
        log_warn("测速执行", f"测速执行失败 - {str(e)}")
        return False


# ==================== 主流程函数 ====================
def auto_run_test() -> int:
    """完整自动化流程"""
    log_info("主流程", "开始 Cloudflare 测速流程")
    try:
        # 1. 下载 / 准备工具
        exec_path = ensure_speedtest_binary()
        if not exec_path:
            log_error("主流程", "无法获取测速工具，需重启容器")
            return EXIT_FATAL
        log_info("主流程", f"工具准备完成: {os.path.basename(exec_path)}")

        # 统一参数解析函数
        def build_params():
            uv, uf = {}, set()
            for p in VALUE_PARAMS:
                v = os.environ.get(p) or CUSTOM_PARAMS.get(p)
                if v is not None and str(v).strip() != "":
                    uv[p] = str(v).strip()
            for p in FLAG_PARAMS:
                ev = os.environ.get(p, "").strip().lower()
                if ev in {"true", "1", "yes"}:
                    uf.add(p)
                elif ev in {"false", "0"}:
                    continue
                elif CUSTOM_FLAG_PARAMS.get(p, False):
                    uf.add(p)
            return uv, uf

        used_value, used_flag = build_params()

        # ===== 判断是否两步法 =====
        cfcolo = used_value.get("cfcolo", "").strip()
        if cfcolo:
            log_info("主流程", f"检测到 cfcolo={cfcolo}，启用两步法测速")

            # 确保 IP 段文件存在
            ip_file = used_value.get("f", DEFAULT_CLOUDFLARE_IP_FILE)
            if not download_cloudflare_ips("ipv4", ip_file):
                log_warn("主流程", "IP列表下载失败，本次流程终止")
                return EXIT_NON_FATAL

            # ① 地区扫描
            scan_csv = "region_scan.csv"
            scan_value, scan_flag = {}, set()
            scan_value["f"]   = ip_file
            scan_value["tl"]  = "9999"
            scan_value["o"]   = scan_csv
            scan_value["url"] = "http://CloudflareIP/cdn-cgi/trace"
            scan_value["tp"] = "80"
            scan_flag.add("dd")
            scan_flag.add("httping")

            print("\n" + "="*50)
            log_info("主流程", ">>> 第一步：扫描地区 IP...")
            print("="*50 + "\n")
            
            if not run_speed_test(exec_path, scan_value, scan_flag):
                log_warn("主流程", "地区扫描失败，本次流程终止")
                return EXIT_NON_FATAL

            # 提取目标地区 IP
            region_file = f"region_{cfcolo.lower()}.txt"
            wanted_colos = {
                c.strip().upper()
                for c in cfcolo.translate(str.maketrans("，", ",")).split(",")
                if c.strip()
            }
            ips = []
            with open(scan_csv, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    colo = (row.get("地区码") or "").strip().upper()
                    if colo in wanted_colos:
                        ip = (row.get("IP 地址") or "").strip()
                        if ip:
                            ips.append(ip.split(":")[0])
            if not ips:
                log_warn("主流程", f"未找到 {cfcolo} 地区的 IP，本次流程终止")
                if os.path.exists(scan_csv):
                    os.remove(scan_csv)
                return EXIT_NON_FATAL

            with open(region_file, "w", encoding="utf-8") as f:
                f.write("\n".join(ips))
            log_info("主流程", f"已提取 {len(ips)} 个 IP → {region_file}")

            # ② 对该地区 IP 正式测速
            used_value, used_flag = build_params()
            used_value.pop("cfcolo", None)
            used_value["f"] = region_file
            
            print("\n" + "="*50)
            log_info("主流程", ">>> 第二步：对该地区 IP 进行 TCP 测速...")
            print("="*50 + "\n")
            
            if not run_speed_test(exec_path, used_value, used_flag):
                log_warn("主流程", "正式测速失败，清理临时文件后终止")
                os.remove(region_file)
                os.remove(scan_csv)
                return EXIT_NON_FATAL

            # 清理临时文件
            os.remove(region_file)
            os.remove(scan_csv)

            # 补充后续流程
            result_csv = used_value.get("o", DEFAULT_RESULT_CSV)
            generate_proxy_list(result_csv)

            upload_to_github()

            # 复制文件到数据目录
            try:
                os.makedirs("/app/data", exist_ok=True)
                for f in (DEFAULT_RESULT_CSV, OUTPUT_TXT):
                    if os.path.isfile(f):
                        shutil.copy2(f, f"/app/data/{f}")
            except Exception as e:
                log_warn("主流程", f"复制文件到 /app/data 失败（可忽略）: {e}")

            log_info("主流程", "所有流程完成")
            return EXIT_SUCCESS

        else:
            # ===== 一次性测速 =====
            ip_file = used_value.get("f", DEFAULT_CLOUDFLARE_IP_FILE)
            if not download_cloudflare_ips("ipv4", ip_file):
                log_warn("主流程", "IP列表下载失败，本次流程终止")
                return EXIT_NON_FATAL

            if not run_speed_test(exec_path, used_value, used_flag):
                log_warn("主流程", "测速失败，本次流程终止")
                return EXIT_NON_FATAL

        # 3. 生成代理列表
        result_csv = used_value.get("o", DEFAULT_RESULT_CSV)
        generate_proxy_list(result_csv)

        # 4. 上传 GitHub
        upload_to_github()

        # 5. 复制结果文件到宿主机
        try:
            os.makedirs("/app/data", exist_ok=True)
            for f in (DEFAULT_RESULT_CSV, OUTPUT_TXT):
                if os.path.isfile(f):
                    shutil.copy2(f, f"/app/data/{f}")
        except Exception as e:
            log_warn("主流程", f"复制文件到 /app/data 失败（可忽略）: {e}")

        log_info("主流程", "所有流程完成")
        return EXIT_SUCCESS

    except Exception as e:
        if isinstance(e, (requests.exceptions.RequestException, subprocess.TimeoutExpired, ConnectionError)):
            log_warn("主流程", f"非致命异常：{e}（下次定时任务可能恢复）")
            return EXIT_NON_FATAL
        else:
            log_error("主流程", f"致命异常：{e}（需重启容器）")
            return EXIT_FATAL


def main():
    """程序入口"""
    # 确保日志无缓冲
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    # Windows编码兼容
    if sys.platform == "win32":
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except Exception:
            pass

    print("=" * 60)
    print(" Cloudflare 自动测速与反代IP生成工具 ".center(60, "="))
    print("=" * 60)

    sys.exit(auto_run_test())


if __name__ == "__main__":
    main()