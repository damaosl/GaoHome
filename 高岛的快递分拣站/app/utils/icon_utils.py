"""图标工具：png → ico 转换（基于 Qt，零额外依赖）。

PyInstaller 在 Windows 上的 --icon 只接受 .ico；若用户选了 .png，
用 Qt 的 ICO 写入能力自动转换，避免引入 Pillow 这类重依赖。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage


def convert_to_ico(png_path: str, ico_path: str = "") -> str:
    """把 png 转为 ico，返回 ico 路径。

    参数：
        png_path : 源 png 文件路径
        ico_path : 目标 ico 路径；为空则生成在 png 同目录下的同名 .ico

    异常：
        ValueError  —— 图片无法读取
        RuntimeError —— 写出失败
    """
    img = QImage(png_path)
    if img.isNull():
        raise ValueError(f"无法读取图片：{png_path}")

    target = ico_path or str(Path(png_path).with_suffix(".ico"))
    if not img.save(target, "ico"):
        raise RuntimeError(f"图标转换失败：{png_path} -> {target}")
    return target
