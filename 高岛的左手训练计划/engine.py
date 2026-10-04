# -*- coding: utf-8 -*-
"""引擎模块：后台线程按设定方式（连点 / 长按）触发鼠标 / 键盘动作。"""

import threading
import time

from pynput import keyboard as kb
from pynput import mouse as ms

from keys import str_to_key

_BUTTONS = {
    "left": ms.Button.left,
    "right": ms.Button.right,
    "middle": ms.Button.middle,
}


class ClickerEngine:
    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self._running = False
        self._count = 0
        self._seq_index = 0
        self._mouse = ms.Controller()
        self._keyboard = kb.Controller()

    @property
    def running(self):
        return self._running

    @property
    def count(self):
        return self._count

    def start(self, cfg):
        if self._running:
            return
        self._running = True
        self._count = 0
        self._seq_index = 0
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, args=(cfg,), daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._stop_event.set()
        self._running = False

    def _run(self, cfg):
        if cfg.action == "hold":
            self._run_hold(cfg)
        else:
            self._run_click(cfg)
        self._running = False

    def _run_click(self, cfg):
        if cfg.input_type == "sequence" and not cfg.key_sequence:
            return
        interval = 1.0 / max(float(cfg.cps), 0.01)
        started = time.time()
        while not self._stop_event.is_set():
            self._act(cfg)
            self._count += 1

            # 到达设定时长则自动结束
            if cfg.duration > 0 and (time.time() - started) >= cfg.duration:
                break

            # 等待到下一个触发点（可被 stop_event 立即打断）
            if self._stop_event.wait(interval):
                break

    def _run_hold(self, cfg):
        # 长按：按下 -> 按住设定时长 -> 松开（0 = 一直按住直到结束）
        # 序列模式：按顺序逐个长按，循环直到结束
        if cfg.input_type == "sequence" and not cfg.key_sequence:
            return
        started = time.time()
        while not self._stop_event.is_set():
            self._hold_act(cfg)
            self._count += 1
            # 单键长按：一次即结束；序列长按：循环到时长 / 停止
            if cfg.input_type != "sequence":
                break
            if cfg.duration > 0 and (time.time() - started) >= cfg.duration:
                break
            if self._stop_event.wait(0.05):
                break

    def _current_key(self, cfg):
        """返回本次要触发的键（单键模式或序列模式中的下一个键）。"""
        if cfg.input_type == "keyboard":
            return str_to_key(cfg.keyboard_key)
        if cfg.input_type == "sequence":
            seq = cfg.key_sequence or []
            if not seq:
                return None
            key = str_to_key(seq[self._seq_index % len(seq)])
            self._seq_index += 1
            return key
        return None

    def _wait_hold(self, hold):
        if hold > 0:
            self._stop_event.wait(hold)
        else:
            self._stop_event.wait()

    def _hold_act(self, cfg):
        hold = max(float(cfg.hold_duration), 0.0)

        if cfg.input_type in ("keyboard", "sequence"):
            key = self._current_key(cfg)
            if key is None:
                return
            self._keyboard.press(key)
            self._wait_hold(hold)
            self._keyboard.release(key)
            return

        button = _BUTTONS.get(cfg.mouse_button, ms.Button.left)
        if cfg.follow_cursor:
            self._mouse.press(button)
            self._wait_hold(hold)
            self._mouse.release(button)
        else:
            # 固定坐标：移动到目标点按住，松开后还原光标位置
            origin = self._mouse.position
            self._mouse.position = (int(cfg.mouse_x), int(cfg.mouse_y))
            self._mouse.press(button)
            self._wait_hold(hold)
            self._mouse.release(button)
            self._mouse.position = origin

    def _act(self, cfg):
        if cfg.input_type in ("keyboard", "sequence"):
            key = self._current_key(cfg)
            if key is not None:
                self._keyboard.tap(key)
            return

        button = _BUTTONS.get(cfg.mouse_button, ms.Button.left)
        if cfg.follow_cursor:
            self._mouse.click(button)
        else:
            # 固定坐标：移动到目标点点击后，还原光标位置
            origin = self._mouse.position
            self._mouse.position = (int(cfg.mouse_x), int(cfg.mouse_y))
            self._mouse.click(button)
            self._mouse.position = origin
