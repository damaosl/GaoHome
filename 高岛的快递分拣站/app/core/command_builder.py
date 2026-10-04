"""命令构建器：把 PackConfig 转成 PyInstaller 命令行参数列表。

设计要点：
- 纯函数，只依赖 config 层，不实际执行任何命令；
- 返回参数列表（不含可执行程序名），由 process_runner/packer 决定用
  `pyinstaller` 还是 `python -m PyInstaller` 来调用，保持解耦；
- 脚本路径永远放在最后，符合 PyInstaller 命令行习惯。
"""
from __future__ import annotations

from typing import List

from .config import PackConfig


def build_command(config: PackConfig) -> List[str]:
    """根据配置生成 PyInstaller 命令行参数列表。

    示例：
        build_command(PackConfig(script_path="main.py"))
        -> ["--onefile", "main.py"]
    """
    args: List[str] = []

    # 1. 打包模式：单文件 / 单目录
    args.append("--onefile" if config.onefile else "--onedir")

    # 2. 控制台窗口：默认显示；关闭时加 --noconsole（等价 -w）
    if not config.console:
        args.append("--noconsole")

    # 3. 产物名称（--name / -n）
    if config.name:
        args.extend(["--name", config.name])

    # 4. 图标（--icon / -i）
    if config.icon_path:
        args.extend(["--icon", config.icon_path])

    # 5. 输出目录（--distpath）
    if config.output_dir:
        args.extend(["--distpath", config.output_dir])

    # 6. 打包前清理缓存（--clean）
    if config.clean:
        args.append("--clean")

    # 7. 附加数据文件（--add-data，格式 "源;目标"，Windows 下用分号分隔）
    for data in config.add_data:
        args.extend(["--add-data", data])

    # 8. 隐藏导入模块（--hidden-import）
    for mod in config.hidden_imports:
        args.extend(["--hidden-import", mod])

    # 9. 用户自定义的额外原始参数，原样追加
    args.extend(config.extra_args)

    # 10. 脚本路径，永远放最后
    args.append(config.script_path)

    return args
