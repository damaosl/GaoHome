"""极简主题：统一的配色与 QSS 样式表。

设计原则（UI 与主题统一为「极简」）：
- 纯白背景、近黑文字、极浅灰分隔线；
- 强调方式 = 细黑边框 + 近黑文字，白底白净，不做多余装饰；
- 扁平化：细边框、轻圆角、无阴影、无渐变；
- 大留白、克制的字号层级。
"""
from __future__ import annotations

# ---- 极简配色 ----
COLOR_BG = "#FFFFFF"            # 主背景（纯白）
COLOR_TEXT = "#1A1A1A"          # 主文字（近黑）
COLOR_TEXT_SECONDARY = "#8A8A8A"  # 次级文字
COLOR_BORDER = "#E5E5E5"        # 边框 / 分隔线（极浅灰）
COLOR_ACCENT = "#1A1A1A"        # 强调色 = 主文字色（纯黑，最克制）
COLOR_ACCENT_TEXT = "#FFFFFF"   # 强调色上的文字（白）
COLOR_LOG_BG = "#FAFAFA"        # 日志区背景（极浅灰）
COLOR_DISABLED = "#B0B0B0"      # 禁用态文字

# ---- 统一字体 ----
FONT_UI = '"Microsoft YaHei UI", "Segoe UI", sans-serif'
FONT_MONO = '"Consolas", "Courier New", monospace'

QSS = f"""
/* ===== 全局 ===== */
QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    font-family: {FONT_UI};
    font-size: 13px;
}}

/* ===== 标题 ===== */
QLabel#title {{
    font-size: 22px;
    font-weight: 600;
}}
QLabel#subtitle {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
}}
QLabel#section {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
    letter-spacing: 1px;
}}

/* ===== 输入框 ===== */
QLineEdit {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 6px 10px;
    background: {COLOR_BG};
    selection-background-color: {COLOR_ACCENT};
    selection-color: {COLOR_ACCENT_TEXT};
}}
QLineEdit:focus {{
    border-color: {COLOR_TEXT};
}}
QLineEdit:disabled {{
    color: {COLOR_DISABLED};
    background: {COLOR_LOG_BG};
}}

/* ===== 按钮 ===== */
QPushButton {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 6px 16px;
    background: {COLOR_BG};
    color: {COLOR_TEXT};
}}
QPushButton:hover {{
    border-color: {COLOR_TEXT};
}}
QPushButton:pressed {{
    background: {COLOR_LOG_BG};
}}
QPushButton:disabled {{
    color: {COLOR_DISABLED};
    border-color: {COLOR_BORDER};
}}

/* 主按钮：白底黑字 + 细黑边框（极简、更白净） */
QPushButton#primary {{
    background: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_TEXT};
    font-weight: 600;
    padding: 10px 16px;
}}
QPushButton#primary:hover {{
    background: {COLOR_LOG_BG};
}}
QPushButton#primary:pressed {{
    background: {COLOR_BORDER};
}}
QPushButton#primary:disabled {{
    background: {COLOR_BG};
    color: {COLOR_DISABLED};
    border-color: {COLOR_BORDER};
}}

/* ===== 复选框 ===== */
QCheckBox {{
    spacing: 6px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    background: {COLOR_BG};
}}
QCheckBox::indicator:checked {{
    background: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT};
}}

/* ===== 日志区 ===== */
QPlainTextEdit#log {{
    background: {COLOR_LOG_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    font-family: {FONT_MONO};
    font-size: 12px;
    padding: 8px;
}}

/* ===== 分隔线 ===== */
QFrame#separator {{
    background: {COLOR_BORDER};
    max-height: 1px;
    border: none;
}}

/* ===== 滚动条（克制） ===== */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_TEXT_SECONDARY};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
