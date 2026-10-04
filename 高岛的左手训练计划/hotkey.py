# -*- coding: utf-8 -*-
"""热键模块：全局监听开始 / 结束快捷键，并支持“按下即录入”。"""

from pynput import keyboard

from keys import key_to_str


class HotkeyManager:
    def __init__(self, on_start=None, on_stop=None):
        self.on_start = on_start
        self.on_stop = on_stop
        self.start_key = "<f6>"
        self.stop_key = "<f7>"
        self._capture_cb = None
        self._listener = None

    def set_keys(self, start_key, stop_key):
        self.start_key = start_key
        self.stop_key = stop_key

    def start(self):
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def capture_key(self, callback):
        """进入录制模式：下一次任意按键触发 callback(key_str)。"""
        self._capture_cb = callback

    def cancel_capture(self):
        self._capture_cb = None

    def _on_press(self, key):
        s = key_to_str(key)
        # 录制模式优先：捕获本次按键后立即退出录制
        if self._capture_cb is not None:
            cb = self._capture_cb
            self._capture_cb = None
            cb(s)
            return
        if s == self.start_key and self.on_start:
            self.on_start()
        elif s == self.stop_key and self.on_stop:
            self.on_stop()
