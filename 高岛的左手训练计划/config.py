# -*- coding: utf-8 -*-
"""配置模块：负责连点器设置的加载与保存（config.json）。"""

import json
import os
from dataclasses import dataclass, asdict, field

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


@dataclass
class Config:
    input_type: str = "mouse"      # mouse | keyboard
    mouse_button: str = "left"     # left | right | middle
    follow_cursor: bool = True     # 鼠标点击是否跟随光标
    mouse_x: int = 0               # 固定坐标 X
    mouse_y: int = 0               # 固定坐标 Y
    keyboard_key: str = "a"        # 要连按的键盘键（单键）
    key_sequence: list = field(default_factory=list)  # 按键序列（按顺序连点）
    action: str = "click"          # 触发方式：click=连点 | hold=长按
    cps: float = 10.0              # 每秒触发次数（连点模式）
    hold_duration: float = 1.0     # 长按按住时长（秒），0 = 一直按住
    duration: float = 0.0          # 持续时间（秒），0 = 不限
    start_key: str = "<f6>"        # 开始快捷键
    stop_key: str = "<f7>"         # 结束快捷键

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        cfg = cls()
        for k, v in (d or {}).items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg


def load_config(path=CONFIG_PATH):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return Config.from_dict(json.load(f))
        except (OSError, ValueError):
            pass
    return Config()


def save_config(cfg, path=CONFIG_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg.to_dict(), f, ensure_ascii=False, indent=2)
    except OSError:
        pass
