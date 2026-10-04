"""打包配置数据模型。

本模块定义"把一个 Python 脚本打包成 exe"所需的全部配置项。
它是纯数据层：只依赖标准库，不依赖 UI、也不依赖 PyInstaller，
因此可以在无图形环境、甚至未安装 PyInstaller 时被独立测试。

字段设计依据（来自 GitHub 调研的通用实践）：
- script_path / name          —— 打包对象与产物名称
- onefile / console           —— PyInstaller 最核心的两个开关
- icon_path / add_data        —— 图标与附加资源
- hidden_imports / extra_args —— 高级能力兜底
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# 支持的脚本扩展名
SUPPORTED_SCRIPT_SUFFIXES = (".py", ".pyw")


@dataclass
class PackConfig:
    """一次打包任务的完整配置。"""

    # ---- 必填 ----
    script_path: str

    # ---- 产物 ----
    # 输出 exe 名称（不含扩展名）；为空则自动取脚本文件名
    name: str = ""

    # 是否打包为单文件（--onefile）；False 为单目录（--onedir）
    onefile: bool = True

    # 是否显示控制台窗口；False 等价于 --noconsole（-w）
    console: bool = True

    # 图标文件路径（可选，.ico / .png）；打包产物使用的图标
    icon_path: str = ""

    # 输出目录（dist 目录）；为空则用 PyInstaller 默认
    output_dir: str = ""

    # 打包前清理缓存（--clean）
    clean: bool = False

    # ---- 高级 ----
    # 附加数据，格式 ["源路径;目标路径", ...]，对应 --add-data
    add_data: List[str] = field(default_factory=list)

    # 隐藏导入的模块名列表，对应 --hidden-import
    hidden_imports: List[str] = field(default_factory=list)

    # 其他原始参数，原样追加到命令末尾
    extra_args: List[str] = field(default_factory=list)

    # ---- 派生属性 ----
    @property
    def resolved_name(self) -> str:
        """最终输出名称；未指定 name 时取脚本文件名（不含扩展名）。"""
        if self.name:
            return self.name
        return Path(self.script_path).stem

    # ---- 校验 ----
    def validate(self) -> List[str]:
        """校验配置，返回错误信息列表；空列表表示通过。

        这里只做"静态、可快速判断"的校验（文件是否存在、类型对不对），
        不涉及实际打包，保证调用方能拿到清晰的用户级报错。
        """
        errors: List[str] = []

        sp = Path(self.script_path)
        if not sp.exists():
            errors.append(f"脚本文件不存在：{self.script_path}")
        elif sp.suffix.lower() not in SUPPORTED_SCRIPT_SUFFIXES:
            errors.append(
                f"仅支持 {' / '.join(SUPPORTED_SCRIPT_SUFFIXES)} 脚本，"
                f"收到：{sp.suffix or '(无扩展名)'}"
            )

        if self.icon_path and not Path(self.icon_path).exists():
            errors.append(f"图标文件不存在：{self.icon_path}")

        return errors
