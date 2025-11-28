#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yx-tools-gui - 基于 Flet 的跨平台图形界面
"""

import flet as ft
import subprocess
import threading
import os
import sys
import json
import csv
from datetime import datetime

# 导入核心功能模块
try:
    from cloudflare_speedtest import (
        CLOUDFLARE_HTTPS_PORTS,
        DEFAULT_SPEEDTEST_URL,
        CLOUDFLARE_IP_FILE,
        CLOUDFLARE_IPV6_FILE,
        CONFIG_FILE,
        AIRPORT_CODES,
        get_system_info,
        download_cloudflare_speedtest,
        download_cloudflare_ips,
        generate_ip_with_ports,
        load_config,
        save_config,
        generate_ipv6_file,
    )
except ImportError:
    print("错误: 请确保 cloudflare_speedtest.py 在同一目录下")
    sys.exit(1)


# 主题颜色
PRIMARY_COLOR = "#FF6B35"  # 橙色
SECONDARY_COLOR = "#004E89"  # 深蓝色
SUCCESS_COLOR = "#28A745"
WARNING_COLOR = "#FFC107"
ERROR_COLOR = "#DC3545"

# 浅色主题
LIGHT_BG_COLOR = "#F0F2F5"
LIGHT_CARD_COLOR = "#FFFFFF"
LIGHT_TEXT_COLOR = "#1A1A1A"

# 深色主题
DARK_BG_COLOR = "#1A1A2E"
DARK_CARD_COLOR = "#2D2D44"
DARK_TEXT_COLOR = "#E8E8E8"


class CloudflareSpeedTestGUI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_page()
        self.create_ui()
        
    def setup_page(self):
        """设置页面属性"""
        self.page.title = "yx-tools-gui - 优选 IP 测速工具"
        self.page.window.width = 1000
        self.page.window.height = 800
        self.page.window.min_width = 900
        self.page.window.min_height = 700
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = LIGHT_BG_COLOR
        self.page.padding = 0
    
    def create_section_title(self, icon, title, subtitle=None):
        """创建区域标题"""
        items = [
            ft.Icon(icon, size=20, color=PRIMARY_COLOR),
            ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
        ]
        if subtitle:
            items.append(ft.Text(subtitle, size=12, color=ft.Colors.GREY_500))
        return ft.Row(items, spacing=8)
    
    def create_ui(self):
        """创建用户界面"""
        # 加载配置
        config = load_config() or {}
        saved_url = config.get("speedtest_url", "")
        
        # 统一卡片样式
        CARD_PADDING = 12
        CARD_RADIUS = 8
        CARD_COLOR = LIGHT_CARD_COLOR
        CARD_SHADOW = ft.BoxShadow(
            spread_radius=0,
            blur_radius=4,
            color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
            offset=ft.Offset(0, 1),
        )
        
        # ===== 顶部标题栏 =====
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Row([
                        ft.Image(
                            src=os.path.join(os.path.dirname(__file__), "icon", "icon.png"),
                            width=32,
                            height=32,
                            fit=ft.ImageFit.CONTAIN,
                        ) if os.path.exists(os.path.join(os.path.dirname(__file__), "icon", "icon.png")) 
                        else ft.Icon(ft.Icons.SPEED, size=32, color=PRIMARY_COLOR),
                        ft.Text("yx-tools-gui", size=18, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                    ], spacing=10),
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.BRIGHTNESS_6, tooltip="切换主题",
                                     on_click=self.toggle_theme, icon_size=18),
                        ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip="帮助",
                                     on_click=self.show_help, icon_size=18),
                    ], spacing=0),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            bgcolor=CARD_COLOR,
            shadow=CARD_SHADOW,
        )
        
        # ==================== 左侧：设置区域 ====================
        
        # ===== IP 版本选择 =====
        self.ip_version = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="ipv4", label="IPv4", active_color=PRIMARY_COLOR),
                ft.Radio(value="ipv6", label="IPv6", active_color=PRIMARY_COLOR),
            ], spacing=20),
            value="ipv4",
        )
        
        ip_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LANGUAGE, size=14, color=PRIMARY_COLOR),
                    ft.Text("IP 版本", size=12, weight=ft.FontWeight.BOLD),
                ], spacing=5),
                self.ip_version,
            ], spacing=8),
            padding=CARD_PADDING,
            bgcolor=CARD_COLOR,
            border_radius=CARD_RADIUS,
            shadow=CARD_SHADOW,
        )
        
        # ===== 端口选择 =====
        self.port_checkboxes = {}
        port_chips = []
        for port in CLOUDFLARE_HTTPS_PORTS:
            chip = ft.Chip(
                label=ft.Text(str(port), size=11, width=30, text_align=ft.TextAlign.CENTER),
                selected=(port == 443),
                on_select=lambda e, p=port: self.on_port_select(e, p),
                selected_color=PRIMARY_COLOR,
                show_checkmark=False,
            )
            self.port_checkboxes[port] = chip
            port_chips.append(chip)
        
        port_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.ROUTER, size=14, color=PRIMARY_COLOR),
                        ft.Text("测试端口", size=12, weight=ft.FontWeight.BOLD),
                    ], spacing=5),
                    ft.Row([
                        ft.TextButton("全选", on_click=self.select_all_ports,
                                     style=ft.ButtonStyle(color=PRIMARY_COLOR, padding=3)),
                        ft.TextButton("仅443", on_click=self.deselect_all_ports,
                                     style=ft.ButtonStyle(color=ft.Colors.GREY_600, padding=3)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row(port_chips, wrap=True, spacing=5, run_spacing=5),
                ft.Text("💡 多端口会增加测试时间", size=10, color=ft.Colors.GREY_500),
            ], spacing=6),
            padding=CARD_PADDING,
            bgcolor=CARD_COLOR,
            border_radius=CARD_RADIUS,
            shadow=CARD_SHADOW,
        )
        
        # ===== 测速 URL =====
        self.url_type = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="default", label="默认", active_color=PRIMARY_COLOR),
                ft.Radio(value="custom", label="自定义", active_color=PRIMARY_COLOR),
            ], spacing=15),
            value="custom" if saved_url else "default",
            on_change=self.on_url_type_change,
        )
        
        self.custom_url_field = ft.TextField(
            value=saved_url,
            visible=bool(saved_url),
            hint_text="https://your-speedtest-url.com",
            border_radius=5,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=6),
            text_size=11,
            dense=True,
        )
        
        url_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=14, color=PRIMARY_COLOR),
                    ft.Text("测速 URL", size=12, weight=ft.FontWeight.BOLD),
                ], spacing=5),
                self.url_type,
                self.custom_url_field,
                ft.Text("⚠️ 默认URL可能不支持非443端口", size=10, color=ft.Colors.ORANGE_700),
            ], spacing=5),
            padding=CARD_PADDING,
            bgcolor=CARD_COLOR,
            border_radius=CARD_RADIUS,
            shadow=CARD_SHADOW,
        )
        
        # ===== 测速参数 =====
        self.dn_count = ft.TextField(
            value="10",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=5,
            text_size=12,
            height=36,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            expand=True,
        )
        self.speed_limit = ft.TextField(
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=5,
            text_size=12,
            height=36,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            expand=True,
        )
        self.time_limit = ft.TextField(
            value="500",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=5,
            text_size=12,
            height=36,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            expand=True,
        )
        self.thread_count = ft.TextField(
            value="200",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=5,
            text_size=12,
            height=36,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            expand=True,
        )
        
        # 参数项：标签 + 输入框
        def param_item(label, field):
            return ft.Column([
                ft.Text(label, size=11, color=ft.Colors.GREY_600),
                field,
            ], spacing=3, expand=True)
        
        params_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.TUNE, size=14, color=PRIMARY_COLOR),
                    ft.Text("测速参数", size=12, weight=ft.FontWeight.BOLD),
                ], spacing=5),
                ft.Row([
                    param_item("IP 数量", self.dn_count),
                    param_item("速度下限 (MB/s)", self.speed_limit),
                ], spacing=12),
                ft.Row([
                    param_item("延迟上限 (ms)", self.time_limit),
                    param_item("线程数", self.thread_count),
                ], spacing=12),
            ], spacing=8),
            padding=CARD_PADDING,
            bgcolor=CARD_COLOR,
            border_radius=CARD_RADIUS,
            shadow=CARD_SHADOW,
        )
        
        # ===== 控制按钮 =====
        self.start_btn = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.WHITE, size=16),
                ft.Text("开始测速", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
            on_click=self.start_speedtest,
            style=ft.ButtonStyle(bgcolor=PRIMARY_COLOR, shape=ft.RoundedRectangleBorder(radius=6)),
            height=36, expand=True,
        )
        
        self.stop_btn = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.STOP, color=ft.Colors.WHITE, size=16),
                ft.Text("停止", size=13, color=ft.Colors.WHITE),
            ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
            on_click=self.stop_speedtest,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ERROR_COLOR, shape=ft.RoundedRectangleBorder(radius=6)),
            height=36, expand=True,
        )
        
        self.progress_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, color=PRIMARY_COLOR, visible=False)
        self.progress_bar = ft.ProgressBar(color=PRIMARY_COLOR, bgcolor=ft.Colors.GREY_200, visible=False, expand=True)
        self.status_text = ft.Text("就绪", size=11, color=ft.Colors.GREY_600)
        
        control_section = ft.Container(
            content=ft.Column([
                ft.Row([self.start_btn, self.stop_btn], spacing=10),
                ft.Row([self.progress_ring, self.status_text, self.progress_bar], spacing=6),
            ], spacing=8),
            padding=CARD_PADDING,
            bgcolor=CARD_COLOR,
            border_radius=CARD_RADIUS,
            shadow=CARD_SHADOW,
        )
        
        # ===== 左侧面板 =====
        left_panel = ft.Container(
            content=ft.Column(
                [
                    ip_section,
                    port_section,
                    url_section,
                    params_section,
                    ft.Container(expand=True),  # 弹性空间
                    control_section,
                ],
                spacing=8,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=420,
            expand=True,
        )
        
        # ==================== 右侧：日志和结果区域 ====================
        
        # ===== 日志输出 =====
        self.log_output = ft.TextField(
            multiline=True,
            read_only=True,
            text_size=10,
            value="🚀 准备就绪，点击「开始测速」按钮开始...\n",
            border_radius=5,
            border_color=ft.Colors.GREY_300,
            content_padding=ft.padding.all(8),
            expand=True,
        )
        
        log_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.TERMINAL, size=14, color=PRIMARY_COLOR),
                        ft.Text("运行日志", size=12, weight=ft.FontWeight.BOLD),
                    ], spacing=5),
                    ft.IconButton(icon=ft.Icons.CLEAR_ALL, tooltip="清空",
                                 on_click=self.clear_log, icon_color=ft.Colors.GREY_500, icon_size=16),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.log_output,
            ], spacing=5, expand=True),
            padding=CARD_PADDING,
            bgcolor=CARD_COLOR,
            border_radius=CARD_RADIUS,
            shadow=CARD_SHADOW,
            expand=1,
        )
        
        # ===== 结果表格 =====
        self.result_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("IP 地址", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("端口", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("延迟", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("速度", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("地区", size=11, weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border_radius=5,
            heading_row_color=ft.Colors.GREY_100,
            heading_row_height=32,
            data_row_max_height=28,
            data_row_min_height=24,
            column_spacing=30,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
            expand=True,
        )
        
        result_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.ANALYTICS, size=14, color=PRIMARY_COLOR),
                        ft.Text("测速结果", size=12, weight=ft.FontWeight.BOLD),
                    ], spacing=5),
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.CLOUD_UPLOAD, tooltip="上传优选IP",
                                     on_click=self.show_upload_dialog, icon_color=SUCCESS_COLOR, icon_size=16),
                        ft.IconButton(icon=ft.Icons.REFRESH, tooltip="刷新",
                                     on_click=self.load_results, icon_color=PRIMARY_COLOR, icon_size=16),
                        ft.IconButton(icon=ft.Icons.FOLDER_OPEN, tooltip="打开文件夹",
                                     on_click=self.export_results, icon_color=ft.Colors.GREY_600, icon_size=16),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    content=ft.ListView(
                        controls=[self.result_table],
                        expand=True,
                    ),
                    border=ft.border.all(1, ft.Colors.GREY_200),
                    border_radius=5,
                    expand=True,
                    padding=0,
                ),
            ], spacing=5, expand=True),
            padding=CARD_PADDING,
            bgcolor=CARD_COLOR,
            border_radius=CARD_RADIUS,
            shadow=CARD_SHADOW,
            expand=2,
        )
        
        # ===== 右侧面板 =====
        right_panel = ft.Container(
            content=ft.Column(
                [
                    log_section,
                    result_section,
                ],
                spacing=10,
                expand=True,
            ),
            expand=True,
        )
        
        # ===== 底部信息 =====
        footer = ft.Container(
            content=ft.Row(
                [
                    ft.TextButton("GitHub", url="https://github.com/byJoey/yx-tools",
                                 style=ft.ButtonStyle(padding=3)),
                    ft.Text("•", size=9, color=ft.Colors.GREY_400),
                    ft.TextButton("YouTube", url="https://www.youtube.com/@Joeyblog",
                                 style=ft.ButtonStyle(padding=3)),
                    ft.Text("•", size=9, color=ft.Colors.GREY_400),
                    ft.TextButton("Telegram", url="https://t.me/+ft-zI76oovgwNmRh",
                                 style=ft.ButtonStyle(padding=3)),
                    ft.Text("•", size=9, color=ft.Colors.GREY_400),
                    ft.Text("Made with ❤️ by Joey & Zag", size=10, color=ft.Colors.GREY_500),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
            ),
            padding=ft.padding.symmetric(vertical=8),
            bgcolor=CARD_COLOR,
        )
        
        # ===== 主内容区域：左右两栏 =====
        main_content = ft.Row(
            [
                ft.Container(content=left_panel, expand=2, padding=ft.padding.only(left=15, top=10, bottom=10, right=5)),
                ft.Container(content=right_panel, expand=3, padding=ft.padding.only(left=5, top=10, bottom=10, right=15)),
            ],
            spacing=0,
            expand=True,
        )
        
        # ===== 组装页面 =====
        self.page.add(
            ft.Column(
                [
                    header,
                    main_content,
                    footer,
                ],
                spacing=0,
                expand=True,
            )
        )
        
        # 进程引用
        self.process = None
        self.running = False
    
    def toggle_theme(self, e):
        """切换主题"""
        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = DARK_BG_COLOR
            # 更新所有颜色
            self.update_theme_colors(DARK_CARD_COLOR, DARK_TEXT_COLOR, is_dark=True)
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = LIGHT_BG_COLOR
            self.update_theme_colors(LIGHT_CARD_COLOR, LIGHT_TEXT_COLOR, is_dark=False)
        self.page.update()
    
    def update_theme_colors(self, card_color, text_color, is_dark=False):
        """更新主题颜色"""
        # 更新表格表头颜色
        if hasattr(self, 'result_table'):
            self.result_table.heading_row_color = "#3D3D5C" if is_dark else ft.Colors.GREY_100
        
        # 遍历页面控件更新颜色
        def update_control(control):
            if isinstance(control, ft.Container):
                if control.bgcolor in [LIGHT_CARD_COLOR, DARK_CARD_COLOR, "#FFFFFF", "#2D2D44"]:
                    control.bgcolor = card_color
            if isinstance(control, ft.DataTable):
                control.heading_row_color = "#3D3D5C" if is_dark else ft.Colors.GREY_100
            if hasattr(control, 'controls'):
                for c in control.controls:
                    update_control(c)
            if hasattr(control, 'content') and control.content:
                update_control(control.content)
        
        for control in self.page.controls:
            update_control(control)
    
    def show_help(self, e):
        """显示帮助"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("使用帮助"),
            content=ft.Column([
                ft.Text("1. 选择 IP 版本（IPv4 或 IPv6）", size=14),
                ft.Text("2. 选择要测试的端口（可多选）", size=14),
                ft.Text("3. 配置测速 URL（非 443 端口建议使用自定义 URL）", size=14),
                ft.Text("4. 调整测速参数", size=14),
                ft.Text("5. 点击「开始测速」按钮", size=14),
                ft.Container(height=10),
                ft.Text("💡 提示：", weight=ft.FontWeight.BOLD),
                ft.Text("• 多端口测试会依次测试每个端口", size=12),
                ft.Text("• 默认 URL 可能不支持非 443 端口", size=12),
                ft.Text("• 自定义 URL 会自动保存", size=12),
            ], tight=True, spacing=8),
            actions=[
                ft.TextButton("关闭", on_click=close_dialog),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def on_port_select(self, e, port):
        """端口选择变化"""
        self.port_checkboxes[port].selected = e.control.selected
        self.page.update()
    
    def select_all_ports(self, e):
        """全选端口"""
        for chip in self.port_checkboxes.values():
            chip.selected = True
        self.page.update()
    
    def deselect_all_ports(self, e):
        """仅选择 443"""
        for port, chip in self.port_checkboxes.items():
            chip.selected = (port == 443)
        self.page.update()
    
    def on_url_type_change(self, e):
        """URL 类型变化"""
        self.custom_url_field.visible = (e.control.value == "custom")
        self.page.update()
    
    def on_url_change(self, e):
        """URL 下拉框变化"""
        self.custom_url_field.visible = (e.control.value == "custom")
        self.page.update()
    
    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.value += f"[{timestamp}] {message}\n"
        # 滚动到底部
        self.log_output.value = self.log_output.value[-10000:]  # 限制长度
        self.page.update()
    
    def clear_log(self, e):
        """清空日志"""
        self.log_output.value = ""
        self.page.update()
    
    def get_selected_ports(self):
        """获取选中的端口"""
        ports = []
        for port, chip in self.port_checkboxes.items():
            if chip.selected:
                ports.append(port)
        return ports if ports else [443]
    
    def get_speedtest_url(self):
        """获取测速 URL"""
        if self.url_type.value == "custom" and self.custom_url_field.value:
            url = self.custom_url_field.value.strip()
            if not url.startswith("http"):
                url = "https://" + url
            # 保存到配置
            save_config(speedtest_url=url)
            return url
        return DEFAULT_SPEEDTEST_URL
    
    def export_results(self, e):
        """用系统文件浏览器打开结果文件"""
        result_file = "result.csv"
        if not os.path.exists(result_file):
            self.log("⚠️ 未找到结果文件")
            return
        
        abs_path = os.path.abspath(result_file)
        self.log(f"📁 打开文件: {abs_path}")
        
        # 用系统默认程序打开文件
        try:
            import subprocess
            if sys.platform == "win32":
                os.startfile(abs_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", abs_path])
            else:
                # Linux - 尝试用文件管理器打开并选中文件
                subprocess.run(["xdg-open", os.path.dirname(abs_path)])
        except Exception as ex:
            self.log(f"⚠️ 无法打开文件: {ex}")
    
    def show_upload_dialog(self, e):
        """显示上传对话框"""
        result_file = "result.csv"
        if not os.path.exists(result_file):
            self.log("⚠️ 未找到结果文件，请先完成测速")
            return
        
        # 加载保存的配置
        config = load_config() or {}
        saved_domain = config.get('worker_domain', '')
        saved_uuid = config.get('uuid', '')
        saved_github_token = config.get('github_token', '')
        saved_repo = config.get('repo_info', '')
        saved_file_path = config.get('file_path', 'cloudflare_ips.txt')
        
        # 获取当前主题的背景色
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        dialog_bgcolor = DARK_CARD_COLOR if is_dark else LIGHT_CARD_COLOR
        
        # ===== Cloudflare Workers API 字段 =====
        self.upload_url_field = ft.TextField(
            hint_text="https://你的域名/你的UUID或路径",
            value=f"https://{saved_domain}/{saved_uuid}" if saved_domain and saved_uuid else "",
            text_size=12,
            dense=True,
            height=38,
        )
        self.clear_existing_checkbox = ft.Checkbox(
            label="清空现有IP后再上传",
            value=True,
        )
        
        # ===== GitHub 字段 =====
        self.github_token_field = ft.TextField(
            hint_text="ghp_xxxxxxxxxxxx",
            value=saved_github_token,
            text_size=12,
            dense=True,
            password=True,
            can_reveal_password=True,
            height=38,
        )
        self.github_repo_field = ft.TextField(
            hint_text="owner/repo",
            value=saved_repo,
            text_size=12,
            dense=True,
            height=38,
        )
        self.github_file_path_field = ft.TextField(
            hint_text="cloudflare_ips.txt",
            value=saved_file_path,
            text_size=12,
            dense=True,
            height=38,
        )
        
        # ===== 通用字段 =====
        # 读取结果文件获取最大数量
        import csv
        max_count = 0
        try:
            with open("result.csv", 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                max_count = sum(1 for row in reader if row.get('IP 地址'))
        except:
            max_count = 100
        
        self.upload_max_count = max(1, max_count)
        self.upload_count_value = min(10, self.upload_max_count)
        
        self.upload_count_field = ft.TextField(
            value=str(self.upload_count_value),
            keyboard_type=ft.KeyboardType.NUMBER,
            text_size=12,
            width=60,
            dense=True,
            text_align=ft.TextAlign.CENTER,
            height=32,
            on_change=self.on_upload_count_change,
        )
        
        def decrease_count(e):
            current = int(self.upload_count_field.value or "1")
            if current > 1:
                self.upload_count_field.value = str(current - 1)
                self.page.update()
        
        def increase_count(e):
            current = int(self.upload_count_field.value or "1")
            if current < self.upload_max_count:
                self.upload_count_field.value = str(current + 1)
                self.page.update()
        
        upload_count_row = ft.Row([
            ft.Text("上传数量", size=11, color=ft.Colors.GREY_500),
            ft.IconButton(icon=ft.Icons.REMOVE, icon_size=16, on_click=decrease_count,
                         style=ft.ButtonStyle(padding=0)),
            self.upload_count_field,
            ft.IconButton(icon=ft.Icons.ADD, icon_size=16, on_click=increase_count,
                         style=ft.ButtonStyle(padding=0)),
            ft.Text(f"/ {self.upload_max_count}", size=11, color=ft.Colors.GREY_500),
        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        # API 上传内容
        api_content = ft.Column([
            ft.Text("管理页面 URL", size=11, color=ft.Colors.GREY_500),
            self.upload_url_field,
            self.clear_existing_checkbox,
        ], spacing=6, tight=True)
        
        # GitHub 上传内容
        github_content = ft.Column([
            ft.Text("GitHub Token", size=11, color=ft.Colors.GREY_500),
            self.github_token_field,
            ft.Text("仓库 (owner/repo)", size=11, color=ft.Colors.GREY_500),
            self.github_repo_field,
            ft.Text("文件路径", size=11, color=ft.Colors.GREY_500),
            self.github_file_path_field,
        ], spacing=6, tight=True)
        
        # 标签页
        self.upload_tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Cloudflare API", content=ft.Container(content=api_content, padding=10)),
                ft.Tab(text="GitHub", content=ft.Container(content=github_content, padding=10)),
            ],
            height=180,
        )
        
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        def do_upload(e):
            dialog.open = False
            self.page.update()
            # 根据选中的标签页执行不同的上传
            if self.upload_tabs.selected_index == 0:
                thread = threading.Thread(target=self.upload_to_api_thread)
            else:
                thread = threading.Thread(target=self.upload_to_github_thread)
            thread.daemon = True
            thread.start()
        
        dialog = ft.AlertDialog(
            title=ft.Text("上传优选IP", size=14, weight=ft.FontWeight.BOLD),
            bgcolor=dialog_bgcolor,
            content=ft.Container(
                content=ft.Column([
                    self.upload_tabs,
                    ft.Divider(height=1),
                    upload_count_row,
                ], spacing=6, tight=True),
                width=400,
            ),
            actions=[
                ft.TextButton("取消", on_click=close_dialog),
                ft.ElevatedButton("上传", on_click=do_upload, 
                                 style=ft.ButtonStyle(bgcolor=SUCCESS_COLOR, color=ft.Colors.WHITE)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def on_upload_count_change(self, e):
        """验证上传数量输入"""
        try:
            value = int(e.control.value or "1")
            if value < 1:
                e.control.value = "1"
            elif value > self.upload_max_count:
                e.control.value = str(self.upload_max_count)
            self.page.update()
        except ValueError:
            e.control.value = "10"
            self.page.update()
    
    def read_result_ips(self, upload_count):
        """读取测速结果IP列表"""
        import csv
        best_ips = []
        with open("result.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = (row.get('IP 地址') or '').strip()
                port = (row.get('端口') or '443').strip()
                
                # 获取速度
                speed = ''
                for key in ['下载速度(MB/s)', '下载速度 (MB/s)', '下载速度']:
                    if key in row and row[key]:
                        speed = str(row[key]).strip()
                        break
                
                # 获取地区
                region = (row.get('地区码') or 'N/A').strip()
                
                if ip:
                    try:
                        speed_val = float(speed) if speed else 0
                        best_ips.append({
                            'ip': ip,
                            'port': int(port) if port else 443,
                            'speed': speed_val,
                            'region': region
                        })
                    except ValueError:
                        continue
        return best_ips[:upload_count]
    
    def upload_to_api_thread(self):
        """上传到 Cloudflare Workers API"""
        try:
            url = self.upload_url_field.value.strip()
            if not url:
                self.log("❌ 请输入管理页面 URL")
                return
            
            # 解析 URL
            from urllib.parse import urlparse
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            worker_domain = parsed.netloc
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            
            if not worker_domain or not path_parts:
                self.log("❌ URL 格式错误，请检查")
                return
            
            uuid = path_parts[-1]
            
            # 保存配置
            save_config(worker_domain=worker_domain, uuid=uuid)
            
            # 读取结果
            upload_count = int(self.upload_count_field.value or "10")
            clear_existing = self.clear_existing_checkbox.value
            
            self.log(f"📤 开始上传优选IP到 {worker_domain}...")
            
            best_ips = self.read_result_ips(upload_count)
            if not best_ips:
                self.log("❌ 未找到有效的测速结果")
                return
            
            # 构建 API URL
            api_url = f"https://{worker_domain}/{uuid}/api/preferred-ips"
            
            # 如果需要清空
            if clear_existing:
                self.log("🗑️ 清空现有数据...")
                try:
                    import requests
                    resp = requests.delete(api_url, json={"all": True}, timeout=10)
                    if resp.status_code == 200:
                        self.log("✅ 现有数据已清空")
                    else:
                        self.log(f"⚠️ 清空失败: HTTP {resp.status_code}")
                except Exception as ex:
                    self.log(f"⚠️ 清空失败: {ex}")
            
            # 批量上传
            batch_data = []
            for ip_info in best_ips:
                name = f"{ip_info['region']}-{ip_info['speed']:.2f}MB/s"
                batch_data.append({
                    "ip": ip_info['ip'],
                    "port": ip_info['port'],
                    "name": name
                })
            
            self.log(f"🚀 上传 {len(batch_data)} 个优选IP...")
            
            try:
                import requests
                resp = requests.post(
                    api_url,
                    json={"ips": batch_data},
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    added = result.get('added', len(batch_data))
                    self.log(f"✅ 上传成功！已添加 {added} 个优选IP")
                else:
                    self.log(f"❌ 上传失败: HTTP {resp.status_code}")
                    try:
                        error_msg = resp.json().get('error', resp.text)
                        self.log(f"   错误信息: {error_msg}")
                    except:
                        pass
            except Exception as ex:
                self.log(f"❌ 上传失败: {ex}")
                
        except Exception as ex:
            self.log(f"❌ 上传出错: {ex}")
    
    def upload_to_github_thread(self):
        """上传到 GitHub 仓库"""
        try:
            github_token = self.github_token_field.value.strip()
            repo_info = self.github_repo_field.value.strip()
            file_path = self.github_file_path_field.value.strip() or "cloudflare_ips.txt"
            
            if not github_token:
                self.log("❌ 请输入 GitHub Token")
                return
            if not repo_info or '/' not in repo_info:
                self.log("❌ 仓库格式错误，应为 owner/repo")
                return
            
            # 保存配置
            save_config(github_token=github_token, repo_info=repo_info, file_path=file_path)
            
            upload_count = int(self.upload_count_field.value or "10")
            best_ips = self.read_result_ips(upload_count)
            
            if not best_ips:
                self.log("❌ 未找到有效的测速结果")
                return
            
            self.log(f"📤 开始上传优选IP到 GitHub: {repo_info}...")
            
            # 构建文件内容
            content_lines = []
            for ip_info in best_ips:
                # 格式: IP:端口#地区-速度
                line = f"{ip_info['ip']}:{ip_info['port']}#{ip_info['region']}-{ip_info['speed']:.2f}MB/s"
                content_lines.append(line)
            
            file_content = '\n'.join(content_lines)
            
            # GitHub API
            import requests
            import base64
            
            api_url = f"https://api.github.com/repos/{repo_info}/contents/{file_path}"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            
            # 检查文件是否存在（获取 SHA）
            sha = None
            try:
                resp = requests.get(api_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    sha = resp.json().get('sha')
                    self.log("📝 文件已存在，将更新内容")
            except:
                pass
            
            # 上传/更新文件
            data = {
                "message": f"Update Cloudflare preferred IPs ({len(best_ips)} IPs)",
                "content": base64.b64encode(file_content.encode()).decode(),
            }
            if sha:
                data["sha"] = sha
            
            self.log(f"🚀 上传 {len(best_ips)} 个优选IP...")
            
            resp = requests.put(api_url, headers=headers, json=data, timeout=30)
            
            if resp.status_code in [200, 201]:
                self.log(f"✅ 上传成功！文件: {file_path}")
                self.log(f"   仓库: https://github.com/{repo_info}")
            else:
                self.log(f"❌ 上传失败: HTTP {resp.status_code}")
                try:
                    error_msg = resp.json().get('message', resp.text)
                    self.log(f"   错误信息: {error_msg}")
                except:
                    pass
                    
        except Exception as ex:
            self.log(f"❌ 上传出错: {ex}")
    
    def start_speedtest(self, e):
        """开始测速"""
        self.running = True
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.progress_bar.visible = True
        self.progress_ring.visible = True
        self.status_text.value = "正在初始化..."
        self.page.update()
        
        # 在新线程中运行测速
        thread = threading.Thread(target=self.run_speedtest_thread)
        thread.daemon = True
        thread.start()
    
    def stop_speedtest(self, e):
        """停止测速"""
        self.running = False
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
        self.log("⏹️ 测速已停止")
        self.reset_ui()
    
    def reset_ui(self):
        """重置 UI 状态"""
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.progress_bar.visible = False
        self.progress_ring.visible = False
        self.status_text.value = "就绪"
        self.page.update()
    
    def run_speedtest_thread(self):
        """测速线程"""
        try:
            # 获取参数
            ip_version = self.ip_version.value
            ip_file = CLOUDFLARE_IP_FILE if ip_version == "ipv4" else CLOUDFLARE_IPV6_FILE
            selected_ports = self.get_selected_ports()
            speedtest_url = self.get_speedtest_url()
            
            self.log(f"📋 IP 版本: {ip_version}")
            self.log(f"📋 测试端口: {', '.join(map(str, selected_ports))}")
            self.log(f"📋 测速 URL: {speedtest_url}")
            
            # 准备 IP 文件
            self.status_text.value = "准备 IP 列表..."
            self.page.update()
            
            if ip_version == "ipv6":
                generate_ipv6_file()
            
            if not download_cloudflare_ips(ip_version, ip_file):
                self.log("❌ 准备 IP 列表失败")
                self.reset_ui()
                return
            
            self.log(f"✅ IP 列表已准备: {ip_file}")
            
            # 下载测速工具
            self.status_text.value = "下载测速工具..."
            self.page.update()
            
            os_type, arch_type = get_system_info()
            exec_name = download_cloudflare_speedtest(os_type, arch_type)
            self.log(f"✅ 测速工具已准备: {exec_name}")
            
            # 生成带端口的 IP 文件
            actual_ip_file = ip_file
            tp_ports = None
            
            if len(selected_ports) > 1 or selected_ports[0] != 443:
                self.status_text.value = "生成带端口的 IP 文件..."
                self.page.update()
                
                generated_file, tp_ports = generate_ip_with_ports(
                    ip_file, selected_ports, "ip_with_ports.txt"
                )
                if generated_file:
                    actual_ip_file = generated_file
                    self.log(f"✅ 带端口 IP 文件已生成")
            
            # 运行测速
            self.status_text.value = "正在测速..."
            self.page.update()
            
            # 构建命令
            if sys.platform == "win32":
                cmd = [exec_name]
            else:
                cmd = [f"./{exec_name}"]
            
            cmd.extend([
                "-f", actual_ip_file,
                "-n", self.thread_count.value,
                "-dn", self.dn_count.value,
                "-sl", self.speed_limit.value,
                "-tl", self.time_limit.value,
                "-o", "result.csv",
            ])
            
            # 如果是 CIDR 格式需要 -tp 参数
            if tp_ports and len(tp_ports) == 1:
                cmd.extend(["-tp", str(tp_ports[0])])
                if tp_ports[0] != 443:
                    cmd.extend(["-url", speedtest_url])
            elif not tp_ports and len(selected_ports) == 1 and selected_ports[0] != 443:
                cmd.extend(["-url", speedtest_url])
            
            self.log(f"🚀 运行命令: {' '.join(cmd)}")
            
            # 执行测速
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
            )
            
            # 读取输出
            for line in self.process.stdout:
                if not self.running:
                    break
                line = line.strip()
                if line:
                    self.log(line)
            
            self.process.wait()
            
            if self.running:
                if self.process.returncode == 0:
                    self.log("✅ 测速完成！")
                    self.status_text.value = "测速完成"
                    # 加载结果
                    self.load_results(None)
                else:
                    self.log(f"❌ 测速失败，返回码: {self.process.returncode}")
                    self.status_text.value = "测速失败"
            
        except Exception as e:
            self.log(f"❌ 错误: {str(e)}")
            self.status_text.value = "发生错误"
        finally:
            self.reset_ui()
    
    def load_results(self, e):
        """加载测速结果"""
        result_file = "result.csv"
        if not os.path.exists(result_file):
            self.log("⚠️ 未找到结果文件")
            return
        
        try:
            self.result_table.rows.clear()
            
            with open(result_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    if count >= 20:  # 只显示前 20 条
                        break
                    
                    ip = row.get('IP 地址', row.get('ip', ''))
                    port = row.get('端口', row.get('port', '443'))
                    latency = row.get('平均延迟', row.get('latency', ''))
                    speed = row.get('下载速度 (MB/s)', row.get('speed', ''))
                    region = row.get('地区码', row.get('colo', ''))
                    
                    # 从 IP 中提取端口
                    if ':' in ip and not port:
                        parts = ip.rsplit(':', 1)
                        if len(parts) == 2 and parts[1].isdigit():
                            ip = parts[0]
                            port = parts[1]
                    
                    self.result_table.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(ip)),
                                ft.DataCell(ft.Text(port)),
                                ft.DataCell(ft.Text(latency)),
                                ft.DataCell(ft.Text(speed)),
                                ft.DataCell(ft.Text(region)),
                            ]
                        )
                    )
                    count += 1
            
            self.log(f"📊 已加载 {count} 条结果")
            self.page.update()
            
        except Exception as e:
            self.log(f"❌ 加载结果失败: {str(e)}")


def main(page: ft.Page):
    CloudflareSpeedTestGUI(page)


if __name__ == "__main__":
    # 设置环境变量以确保任务栏图标正确显示
    os.environ["SDL_VIDEO_X11_WMCLASS"] = "yx-tools-gui"
    ft.app(target=main)
