import platform
import sys

def get_system_info():
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        os_type = "darwin"
    elif system == "linux":
        os_type = "linux"
    elif system == "windows":
        os_type = "win"
    else:
        os_type = "unknown"
    
    if machine in ["x86_64", "amd64", "x64"]:
        arch_type = "amd64"
    elif machine in ["arm64", "aarch64"]:
        arch_type = "arm64"
    else:
        arch_type = "unknown"
    
    return os_type, arch_type

os_type, arch_type = get_system_info()
print(f"OS: {os_type}, Arch: {arch_type}")
