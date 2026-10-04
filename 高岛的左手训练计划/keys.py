# -*- coding: utf-8 -*-
"""键位工具：pynput 键对象 <-> 字符串，以及友好显示名转换。"""

from pynput.keyboard import Key, KeyCode

# 特殊键的友好显示名
_NAMES = {
    "space": "空格", "enter": "回车", "tab": "Tab", "esc": "Esc",
    "backspace": "退格", "delete": "Delete", "insert": "Insert",
    "up": "↑", "down": "↓", "left": "←", "right": "→",
    "shift": "Shift", "shift_l": "左Shift", "shift_r": "右Shift",
    "ctrl": "Ctrl", "ctrl_l": "左Ctrl", "ctrl_r": "右Ctrl",
    "alt": "Alt", "alt_l": "左Alt", "alt_r": "右Alt", "alt_gr": "AltGr",
    "cmd": "Win", "cmd_l": "左Win", "cmd_r": "右Win",
    "caps_lock": "CapsLock", "page_up": "PageUp", "page_down": "PageDown",
    "home": "Home", "end": "End", "num_lock": "NumLock",
    "print_screen": "PrintScreen", "scroll_lock": "ScrollLock",
    "pause": "Pause", "menu": "Menu",
}
for i in range(1, 13):
    _NAMES[f"f{i}"] = f"F{i}"


def key_to_str(key):
    """把 pynput 键对象转成可保存的字符串。

    Key.f6   -> '<f6>'
    KeyCode('a') -> 'a'
    无字符的 KeyCode -> '<vk:65>'
    """
    if isinstance(key, Key):
        return f"<{key.name}>"
    if isinstance(key, KeyCode):
        if key.char:
            return key.char
        if key.vk is not None:
            return f"<vk:{key.vk}>"
    return str(key)


def str_to_key(s):
    """把字符串还原为 pynput 键对象（用于模拟按键）。"""
    if not s:
        return None
    if s.startswith("<") and s.endswith(">"):
        inner = s[1:-1]
        if inner.startswith("vk:"):
            return KeyCode.from_vk(int(inner[3:]))
        try:
            return Key[inner]
        except KeyError:
            return KeyCode.from_char(inner)
    return KeyCode.from_char(s)


def friendly_name(s):
    """把键字符串转成适合显示在界面上的名称。"""
    if not s:
        return "未设置"
    if s.startswith("<") and s.endswith(">"):
        inner = s[1:-1]
        if inner.startswith("vk:"):
            return inner
        return _NAMES.get(inner, inner.upper())
    return s.upper()
