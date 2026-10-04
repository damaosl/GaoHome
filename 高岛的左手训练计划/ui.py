# -*- coding: utf-8 -*-
"""界面模块：极简暗色风格，tkinter 实现。"""

import os
import sys
import tkinter as tk

from pynput import mouse as pynput_mouse

from config import load_config, save_config
from engine import ClickerEngine
from hotkey import HotkeyManager
from keys import friendly_name

# ---- 配色（极简暗色）----
BG      = "#121212"   # 页面背景
CARD    = "#1c1c1e"   # 卡片 / 控件底色
FG      = "#ececec"   # 主文字
MUTED   = "#8e8e93"   # 次要文字
ACCENT  = "#34c759"   # 强调色（绿）
DANGER  = "#ff453a"   # 危险色（红）
BORDER  = "#2c2c2e"   # 边框
HOVER   = "#2a2a2c"   # 悬停

FONT       = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")

# 应用图标（源码运行在脚本同目录；打包后从 exe 内临时目录读取）
if getattr(sys, "frozen", False):
    _RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
else:
    _RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(_RESOURCE_DIR, "app.ico")


class Segmented(tk.Frame):
    """极简分段选择控件（按钮组）。"""

    def __init__(self, parent, options, command=None, initial=None):
        super().__init__(parent, bg=BG)
        self.options = options
        self.command = command
        self.value = initial if initial in options else options[0]
        self.buttons = {}
        for opt in options:
            b = tk.Button(
                self, text=opt, command=lambda o=opt: self.set(o),
                bg=CARD, fg=MUTED, activebackground=CARD, activeforeground=FG,
                relief="flat", bd=0, highlightthickness=0,
                cursor="hand2", font=FONT, padx=10, pady=3)
            b.pack(side="left", padx=1)
            self.buttons[opt] = b
        self._refresh()

    def set(self, value):
        if value not in self.options:
            return
        self.value = value
        self._refresh()
        if self.command:
            self.command(value)

    def get(self):
        return self.value

    def _refresh(self):
        for opt, b in self.buttons.items():
            if opt == self.value:
                b.configure(bg=ACCENT, fg="#0b0b0b")
            else:
                b.configure(bg=CARD, fg=MUTED)


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.engine = ClickerEngine()
        self.hotkeys = HotkeyManager(on_start=self._on_hotkey_start,
                                     on_stop=self._on_hotkey_stop)
        self._capture_target = None
        self._capture_gen = 0

        root.title("高岛的左手训练计划")
        root.configure(bg=BG)
        root.resizable(False, False)
        try:
            root.iconbitmap(ICON_PATH)
        except tk.TclError:
            pass

        self._build_ui()
        self._apply_input_type()
        self._apply_action()

        self.hotkeys.set_keys(self.cfg.start_key, self.cfg.stop_key)
        self.hotkeys.start()

        self._poll()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- 界面搭建 ----------------
    def _build_ui(self):
        # 顶栏
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=22, pady=(18, 6))
        tk.Label(header, text="高岛的左手训练计划", bg=BG, fg=FG, font=FONT_TITLE).pack(side="left")
        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        self.status_dot = tk.Label(right, text="●", bg=BG, fg=MUTED, font=("Segoe UI", 8))
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_var = tk.StringVar(value="空闲")
        tk.Label(right, textvariable=self.status_var, bg=BG, fg=MUTED, font=FONT).pack(side="left")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=2)

        # 输入类型
        row = self._row(body, "输入类型")
        self.input_seg = Segmented(
            row, ["鼠标", "键盘", "按键序列"], command=self._apply_input_type,
            initial={"mouse": "鼠标", "keyboard": "键盘", "sequence": "按键序列"}[self.cfg.input_type])
        self.input_seg.pack(side="left")

        # 触发方式
        row = self._row(body, "触发方式")
        self.action_seg = Segmented(row, ["连点", "长按"], command=self._apply_action,
                                    initial="连点" if self.cfg.action == "click" else "长按")
        self.action_seg.pack(side="left")

        # 动态区（随输入类型切换）
        self.dynamic = tk.Frame(body, bg=CARD, padx=12, pady=8, height=112)
        self.dynamic.pack(fill="x", pady=6)
        self.dynamic.pack_propagate(False)
        self._build_mouse_frame()
        self._build_keyboard_frame()
        self._build_sequence_frame()

        # 模式相关参数区（连点 / 长按二选一显示）
        self.mode_area = tk.Frame(body, bg=BG)
        self.mode_area.pack(fill="x")

        # 触发频率（连点）
        self.cps_row = self._row(self.mode_area, "触发频率")
        self.cps_var = tk.StringVar(value=str(self.cfg.cps))
        self._spin(self.cps_row, self.cps_var, 0.1, 1000, 0.5).pack(side="left")
        tk.Label(self.cps_row, text="次 / 秒", bg=BG, fg=MUTED, font=FONT).pack(side="left", padx=6)

        # 按住时长（长按）
        self.hold_row = self._row(self.mode_area, "按住时长")
        self.hold_var = tk.StringVar(value=str(self.cfg.hold_duration))
        self._spin(self.hold_row, self.hold_var, 0, 86400, 1).pack(side="left")
        tk.Label(self.hold_row, text="秒（0 = 一直按住）", bg=BG, fg=MUTED, font=FONT).pack(side="left", padx=6)

        # 持续时间（连点）
        self.dur_row = self._row(self.mode_area, "持续时间")
        self.dur_var = tk.StringVar(value=str(self.cfg.duration))
        self._spin(self.dur_row, self.dur_var, 0, 86400, 1).pack(side="left")
        tk.Label(self.dur_row, text="秒（0 = 不限）", bg=BG, fg=MUTED, font=FONT).pack(side="left", padx=6)

        # 开始快捷键
        row = self._row(body, "开始快捷键")
        self.start_key_btn = self._key_btn(row, self.cfg.start_key, lambda: self._capture("start"))
        self.start_key_btn.pack(side="left")

        # 结束快捷键
        row = self._row(body, "结束快捷键")
        self.stop_key_btn = self._key_btn(row, self.cfg.stop_key, lambda: self._capture("stop"))
        self.stop_key_btn.pack(side="left")

        # 开始 / 结束按钮
        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(14, 2))
        self.start_btn = self._btn(btns, "开始", self._start_clicking, bg=ACCENT, fg="#0b0b0b")
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.stop_btn = self._btn(btns, "结束", self._stop_clicking, bg=DANGER, fg="#0b0b0b")
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.stop_btn.configure(state="disabled")

        # 底部状态栏
        bar = tk.Frame(self.root, bg=CARD)
        bar.pack(fill="x", side="bottom")
        tk.Label(bar, text="快捷键全局生效", bg=CARD, fg=MUTED, font=FONT).pack(side="left", padx=22, pady=9)
        self.count_var = tk.StringVar(value="已触发 0 次")
        tk.Label(bar, textvariable=self.count_var, bg=CARD, fg=MUTED, font=FONT).pack(side="right", padx=22, pady=9)

    def _build_mouse_frame(self):
        f = tk.Frame(self.dynamic, bg=CARD)
        self.mouse_frame = f

        r1 = tk.Frame(f, bg=CARD)
        r1.pack(fill="x", pady=3)
        tk.Label(r1, text="按键", bg=CARD, fg=MUTED, font=FONT, width=6, anchor="w").pack(side="left")
        self.mouse_btn_seg = Segmented(
            r1, ["左键", "右键", "中键"],
            initial={"left": "左键", "right": "右键", "middle": "中键"}[self.cfg.mouse_button])
        self.mouse_btn_seg.pack(side="left")

        r2 = tk.Frame(f, bg=CARD)
        r2.pack(fill="x", pady=3)
        tk.Label(r2, text="位置", bg=CARD, fg=MUTED, font=FONT, width=6, anchor="w").pack(side="left")
        self.pos_seg = Segmented(
            r2, ["跟随光标", "固定坐标"], command=self._on_pos_change,
            initial="跟随光标" if self.cfg.follow_cursor else "固定坐标")
        self.pos_seg.pack(side="left")

        self.pos_row = tk.Frame(f, bg=CARD)
        self._record_btn = tk.Button(
            self.pos_row, text="记录坐标", command=self._record_pos,
            bg=HOVER, fg=FG, activebackground=HOVER, activeforeground=FG,
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            font=FONT, padx=8, pady=2)
        self._record_btn.pack(side="left")
        self.coord_var = tk.StringVar(value=self._coord_text())
        tk.Label(self.pos_row, textvariable=self.coord_var, bg=CARD, fg=MUTED, font=FONT).pack(side="left", padx=10)

    def _build_keyboard_frame(self):
        f = tk.Frame(self.dynamic, bg=CARD)
        self.keyboard_frame = f
        tk.Label(f, text="按键", bg=CARD, fg=MUTED, font=FONT, width=6, anchor="w").pack(side="left", pady=3)
        self.keyboard_key_btn = self._key_btn(f, self.cfg.keyboard_key, lambda: self._capture("keyboard"))
        self.keyboard_key_btn.pack(side="left", padx=(0, 10), pady=3)
        tk.Label(f, text="连按时重复触发该键", bg=CARD, fg=MUTED, font=FONT).pack(side="left", pady=3)

    def _build_sequence_frame(self):
        f = tk.Frame(self.dynamic, bg=CARD)
        self.sequence_frame = f

        r1 = tk.Frame(f, bg=CARD)
        r1.pack(fill="x", pady=2)
        tk.Label(r1, text="顺序", bg=CARD, fg=MUTED, font=FONT, width=6, anchor="w").pack(side="left")
        self.seq_var = tk.StringVar(value=self._seq_text())
        tk.Label(r1, textvariable=self.seq_var, bg=CARD, fg=FG, font=FONT).pack(side="left", padx=(0, 8))

        r2 = tk.Frame(f, bg=CARD)
        r2.pack(fill="x", pady=2)
        self.seq_add_btn = self._small_btn(r2, "添加按键", lambda: self._capture("sequence"))
        self.seq_add_btn.pack(side="left", padx=(0, 6))
        self.seq_del_btn = self._small_btn(r2, "删除末尾", self._seq_remove_last)
        self.seq_del_btn.pack(side="left", padx=(0, 6))
        self.seq_clear_btn = self._small_btn(r2, "清空", self._seq_clear)
        self.seq_clear_btn.pack(side="left")

        tk.Label(f, text="按顺序循环触发，例如 A → S → D", bg=CARD, fg=MUTED, font=FONT).pack(side="left", pady=2)

    # ---------------- 通用小部件 ----------------
    def _row(self, parent, label):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", pady=5)
        tk.Label(f, text=label, bg=BG, fg=MUTED, font=FONT, width=10, anchor="w").pack(side="left")
        return f

    def _btn(self, parent, text, command, bg=CARD, fg=FG):
        b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                      activebackground=HOVER, activeforeground=fg,
                      disabledforeground=MUTED,
                      relief="flat", bd=0, highlightthickness=0,
                      cursor="hand2", font=FONT_BOLD, padx=12, pady=7)
        return b

    def _spin(self, parent, var, from_, to, inc):
        return tk.Spinbox(parent, textvariable=var, from_=from_, to=to, increment=inc,
                          width=8, bg=CARD, fg=FG, insertbackground=FG, justify="center",
                          relief="flat", bd=0, highlightthickness=1,
                          highlightbackground=BORDER, highlightcolor=ACCENT,
                          buttonbackground=CARD, font=FONT)

    def _key_btn(self, parent, key_str, command):
        return tk.Button(parent, text=friendly_name(key_str), command=command,
                         bg=CARD, fg=FG, activebackground=HOVER, activeforeground=FG,
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT,
                         cursor="hand2", font=FONT, padx=12, pady=4)

    def _small_btn(self, parent, text, command):
        return tk.Button(parent, text=text, command=command,
                         bg=HOVER, fg=FG, activebackground=HOVER, activeforeground=FG,
                         relief="flat", bd=0, highlightthickness=0,
                         cursor="hand2", font=FONT, padx=8, pady=2)

    # ---------------- 视图切换 ----------------
    def _apply_input_type(self, value=None):
        self.mouse_frame.pack_forget()
        self.keyboard_frame.pack_forget()
        self.sequence_frame.pack_forget()
        t = self.input_seg.get()
        if t == "鼠标":
            self.mouse_frame.pack(fill="x", anchor="n")
            self._on_pos_change(self.pos_seg.get())
        elif t == "键盘":
            self.keyboard_frame.pack(fill="x", anchor="n")
        else:  # 按键序列
            self.sequence_frame.pack(fill="x", anchor="n")
        self._refresh_mode_rows()

    def _apply_action(self, value=None):
        self._refresh_mode_rows()

    def _refresh_mode_rows(self):
        self.cps_row.pack_forget()
        self.hold_row.pack_forget()
        self.dur_row.pack_forget()
        hold = self.action_seg.get() == "长按"
        seq = self.input_seg.get() == "按键序列"
        if hold:
            self.hold_row.pack(fill="x", pady=5)
            if seq:
                self.dur_row.pack(fill="x", pady=5)  # 序列长按：支持总时长
        else:
            self.cps_row.pack(fill="x", pady=5)
            self.dur_row.pack(fill="x", pady=5)

    def _on_pos_change(self, value):
        if value == "固定坐标":
            self.pos_row.pack(fill="x", pady=3)
        else:
            self.pos_row.pack_forget()

    def _record_pos(self):
        pos = pynput_mouse.Controller().position
        self.cfg.mouse_x, self.cfg.mouse_y = int(pos[0]), int(pos[1])
        self.coord_var.set(self._coord_text())

    def _coord_text(self):
        return f"({self.cfg.mouse_x}, {self.cfg.mouse_y})"

    # ---------------- 按键序列 ----------------
    def _seq_text(self):
        if not self.cfg.key_sequence:
            return "（空）"
        return " → ".join(friendly_name(k) for k in self.cfg.key_sequence)

    def _seq_refresh(self):
        self.seq_var.set(self._seq_text())

    def _seq_remove_last(self):
        if self.cfg.key_sequence:
            self.cfg.key_sequence.pop()
            self._seq_refresh()

    def _seq_clear(self):
        self.cfg.key_sequence.clear()
        self._seq_refresh()

    # ---------------- 快捷键录入 ----------------
    def _capture(self, target):
        self._capture_target = target
        self._capture_gen += 1
        gen = self._capture_gen
        self._target_btn(target).configure(text="请按键…", fg=ACCENT)
        self.hotkeys.capture_key(lambda s: self.root.after(0, self._on_captured, target, s, gen))
        self.root.after(6000, self._capture_timeout, target, gen)

    def _target_btn(self, target):
        return {"start": self.start_key_btn,
                "stop": self.stop_key_btn,
                "keyboard": self.keyboard_key_btn,
                "sequence": self.seq_add_btn}[target]

    def _on_captured(self, target, s, gen):
        if gen != self._capture_gen or self._capture_target != target:
            return
        self._capture_target = None
        if target == "start":
            self.cfg.start_key = s
            self.hotkeys.set_keys(self.cfg.start_key, self.cfg.stop_key)
            self._target_btn(target).configure(text=friendly_name(s), fg=FG)
        elif target == "stop":
            self.cfg.stop_key = s
            self.hotkeys.set_keys(self.cfg.start_key, self.cfg.stop_key)
            self._target_btn(target).configure(text=friendly_name(s), fg=FG)
        elif target == "keyboard":
            self.cfg.keyboard_key = s
            self._target_btn(target).configure(text=friendly_name(s), fg=FG)
        elif target == "sequence":
            self.cfg.key_sequence.append(s)
            self._seq_refresh()
            self._target_btn(target).configure(text="添加按键", fg=FG)

    def _capture_timeout(self, target, gen):
        if gen != self._capture_gen or self._capture_target != target:
            return
        self._capture_target = None
        self.hotkeys.cancel_capture()
        if target == "sequence":
            self._target_btn(target).configure(text="添加按键", fg=FG)
            return
        key_str = {"start": self.cfg.start_key,
                   "stop": self.cfg.stop_key,
                   "keyboard": self.cfg.keyboard_key}[target]
        self._target_btn(target).configure(text=friendly_name(key_str), fg=FG)

    # ---------------- 引擎控制 ----------------
    def _collect_config(self):
        c = self.cfg
        c.action = "click" if self.action_seg.get() == "连点" else "hold"
        try:
            c.cps = float(self.cps_var.get())
        except (ValueError, tk.TclError):
            c.cps = 10.0
        if c.cps <= 0:
            c.cps = 10.0
        try:
            c.hold_duration = float(self.hold_var.get())
        except (ValueError, tk.TclError):
            c.hold_duration = 1.0
        if c.hold_duration < 0:
            c.hold_duration = 0.0
        try:
            c.duration = float(self.dur_var.get())
        except (ValueError, tk.TclError):
            c.duration = 0.0
        if c.duration < 0:
            c.duration = 0.0
        c.input_type = {"鼠标": "mouse", "键盘": "keyboard", "按键序列": "sequence"}[self.input_seg.get()]
        c.mouse_button = {"左键": "left", "右键": "right", "中键": "middle"}[self.mouse_btn_seg.get()]
        c.follow_cursor = (self.pos_seg.get() == "跟随光标")
        return c

    def _start_clicking(self):
        if self.engine.running:
            return
        self._collect_config()
        if self.cfg.input_type == "sequence" and not self.cfg.key_sequence:
            return
        save_config(self.cfg)
        self.engine.start(self.cfg)

    def _stop_clicking(self):
        self.engine.stop()

    def _on_hotkey_start(self):
        self.root.after(0, self._start_clicking)

    def _on_hotkey_stop(self):
        self.root.after(0, self._stop_clicking)

    def _on_close(self):
        self._collect_config()
        save_config(self.cfg)
        self.engine.stop()
        self.hotkeys.stop()
        self.root.destroy()

    # ---------------- 状态轮询 ----------------
    def _poll(self):
        if self.engine.running:
            self.status_var.set("运行中")
            self.status_dot.configure(fg=ACCENT)
            self.start_btn.configure(state="disabled", bg="#2f5c3a")
            self.stop_btn.configure(state="normal", bg=DANGER)
        else:
            self.status_var.set("空闲")
            self.status_dot.configure(fg=MUTED)
            self.start_btn.configure(state="normal", bg=ACCENT)
            self.stop_btn.configure(state="disabled", bg="#5c2f2f")
        self.count_var.set(f"已触发 {self.engine.count} 次")
        self.root.after(100, self._poll)
