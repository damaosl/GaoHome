"""打包配置数据模型。

本模块定义"把一个文件打包成 exe"所需的全部配置项。
它是纯数据层：只依赖标准库，不依赖 UI、也不依赖 PyInstaller，
因此可以在无图形环境、甚至未安装 PyInstaller 时被独立测试。

字段设计依据（来自 GitHub 调研的通用实践）：
- script_path / name          —— 打包对象与产物名称
- onefile / console           —— PyInstaller 最核心的两个开关
- icon_path / add_data        —— 图标与附加资源
- hidden_imports / extra_args —— 高级能力兜底

打包对象既可以是 Python 脚本（.py/.pyw，直接编译），也可以是任意其他
类型的文件（由内置启动器解包后打开），从而实现"全文件类型通用"。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# 可直接交给 PyInstaller 编译的脚本扩展名
PYTHON_SUFFIXES = (".py", ".pyw")


@dataclass
class PackConfig:
    """一次打包任务的完整配置。"""

    # ---- 必填 ----
    # 打包对象：Python 脚本（.py/.pyw）或任意其他类型的文件
    script_path: str

    # 非 Python 脚本时使用：解包启动器 .py 的路径（由 packer 在打包前写入）
    launcher_script: str = ""

    # ---- 产物 ----
    # 输出 exe 名称（不含扩展名）；为空则自动取打包对象文件名
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
        """最终输出名称；未指定 name 时取打包对象文件名（不含扩展名）。"""
        if self.name:
            return self.name
        return Path(self.script_path).stem

    @property
    def is_python_script(self) -> bool:
        """打包对象是否为可直接编译的 Python 脚本。"""
        return Path(self.script_path).suffix.lower() in PYTHON_SUFFIXES

    @property
    def resolved_output_dir(self) -> Path:
        """打包产物的输出目录（存储位置）。

        与 command_builder/packer 的实际行为保持一致：
        - 未指定 output_dir 时，PyInstaller 默认在"打包时的工作目录"下生成
          dist；packer 以脚本所在目录为工作目录，因此默认产物在脚本旁；
        - 指定 output_dir（--distpath）时以它为准，相对路径同样基于脚本所在
          目录解析。
        """
        script_dir = Path(self.script_path).resolve().parent
        if self.output_dir:
            out = Path(self.output_dir)
            return out.resolve() if out.is_absolute() else (script_dir / out).resolve()
        return script_dir / "dist"

    # ---- 校验 ----
    def validate(self) -> List[str]:
        """校验配置，返回错误信息列表；空列表表示通过。

        这里只做"静态、可快速判断"的校验（文件是否存在、是否确为文件），
        不涉及实际打包，保证调用方能拿到清晰的用户级报错。
        """
        errors: List[str] = []

        sp = Path(self.script_path)
        if not sp.exists():
            errors.append(f"文件不存在：{self.script_path}")
        elif not sp.is_file():
            errors.append(f"不是文件：{self.script_path}")

        if self.icon_path and not Path(self.icon_path).exists():
            errors.append(f"图标文件不存在：{self.icon_path}")

        return errors
