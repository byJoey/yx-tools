import sys

path = r'c:\Users\gaoliang\Desktop\yx-tools-2.2.7\cloudflare_speedtest.py'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Replace patterns that cause stalls
patterns = [
    ('if sys.platform == "win32":\n            input("按 Enter 键退出...")', 
     'if sys.platform == "win32" and sys.stdin.isatty():\n            input("按 Enter 键退出...")'),
    ('if sys.platform == "win32":\n                input("按 Enter 键退出...")',
     'if sys.platform == "win32" and sys.stdin.isatty():\n                input("按 Enter 键退出...")'),
    ('input("\\n放置完成后，按回车键继续...")',
     'if sys.stdin.isatty(): input("\\n放置完成后，按回车键继续...")'),
    ('choice = input("\\n是否需要重新扫描？[y/N]: ").strip().lower()',
     'choice = input("\\n是否需要重新扫描？[y/N]: ").strip().lower() if sys.stdin.isatty() else "n"'),
]

for old, new in patterns:
    content = content.replace(old, new)

# Also handle the KeyboardInterrupt one which might have double "避免窗口立即关闭"
content = content.replace(
    '# Windows 系统添加暂停，避免窗口立即关闭\n        if sys.platform == "win32":\n            print("\\n" + "=" * 60)\n            input("按 Enter 键退出...")',
    '# Windows 系统添加暂停，避免窗口立即关闭 (仅在交互模式下)\n        if sys.platform == "win32" and sys.stdin.isatty():\n            print("\\n" + "=" * 60)\n            input("按 Enter 键退出...")'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Replacement done.")
