"""命令构建器：把 PackConfig 转成 PyInstaller 命令行参数列表。

设计要点：
- 纯函数，只依赖 config 层，不实际执行任何命令；
- 返回参数列表（不含可执行程序名），由 process_runner/packer 决定用
  `pyinstaller` 还是 `python -m PyInstaller` 来调用，保持解耦；
- 编译入口永远放在最后，符合 PyInstaller 命令行习惯。
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from .config import PackConfig


def build_command(config: PackConfig) -> List[str]:
    """根据配置生成 PyInstaller 命令行参数列表。

    示例：
        build_command(PackConfig(script_path="main.py"))
        -> ["--onefile", "main.py"]

    当 script_path 不是 Python 脚本时，改用 config.launcher_script 作为
    编译入口，并把用户选择的文件作为 --add-data 打包进去。
    """
    args: List[str] = []

    # 1. 打包模式：单文件 / 单目录
    args.append("--onefile" if config.onefile else "--onedir")

    # 2. 控制台窗口：默认显示；关闭时加 --noconsole（等价 -w）
    if not config.console:
        args.append("--noconsole")

    # 3. 产物名称（--name / -n）
    name = config.name
    if not name and not config.is_python_script:
        # 非 Python 脚本：默认用载荷文件名的 stem 作为产物名，避免被命名为 launcher
        name = Path(config.script_path).stem
    if name:
        args.extend(["--name", name])

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
    data_entries = list(config.add_data)
    if not config.is_python_script:
        # 非 Python 脚本：把用户选择的文件作为载荷，由启动器解包后打开
        payload_name = Path(config.script_path).name
        data_entries.insert(0, f"{config.script_path};{payload_name}")
    for data in data_entries:
        args.extend(["--add-data", data])

    # 8. 隐藏导入模块（--hidden-import）
    for mod in config.hidden_imports:
        args.extend(["--hidden-import", mod])

    # 9. 用户自定义的额外原始参数，原样追加
    args.extend(config.extra_args)

    # 10. 编译入口：Python 脚本直接编译，否则编译解包启动器
    entry = config.script_path if config.is_python_script else config.launcher_script
    args.append(entry)

    return args
