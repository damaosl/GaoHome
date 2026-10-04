"""打包编排器：整合 配置校验 → 命令构建 → 进程执行，对外提供统一 API。

这是 core 层的"总装"模块，GUI 层只需与本模块交互即可完成一次打包。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from .command_builder import build_command
from .config import PackConfig
from .process_runner import LogCallback, ProcessRunner


def _pyinstaller_command() -> List[str]:
    """确定调用 PyInstaller 的方式。

    用 `python -m PyInstaller`（而非裸 `pyinstaller`），确保调用的是当前
    Python 解释器所安装的 PyInstaller，避免多环境下的版本错配。
    """
    return [sys.executable, "-m", "PyInstaller"]


class Packer:
    """一次打包任务的编排器。"""

    def __init__(self, config: PackConfig, on_log: Optional[LogCallback] = None) -> None:
        self.config = config
        self.on_log = on_log
        self._runner: Optional[ProcessRunner] = None

    def validate(self) -> List[str]:
        """前置校验，返回错误信息列表（空表示通过）。"""
        return self.config.validate()

    def pack(self) -> int:
        """执行打包，返回退出码（0 表示成功）。"""
        # 1. 前置校验，失败则不启动进程
        errors = self.config.validate()
        if errors:
            for e in errors:
                self._emit(f"[错误] {e}")
            return 1

        # 2. 构建完整命令
        command = _pyinstaller_command() + build_command(self.config)
        self._emit("执行命令： " + " ".join(command))

        # 3. 在脚本所在目录执行，保证相对路径（如 add-data）正确解析
        script_dir = str(Path(self.config.script_path).resolve().parent)

        # 4. 后台执行，stdout/stderr 统一汇入同一条日志流
        self._runner = ProcessRunner(
            command, on_stdout=self._emit, on_stderr=self._emit, cwd=script_dir
        )
        code = self._runner.run()
        self._emit(f"打包结束，退出码：{code}" + ("（成功）" if code == 0 else "（失败）"))
        return code

    def cancel(self) -> None:
        """取消正在进行的打包。"""
        if self._runner is not None:
            self._runner.cancel()

    @property
    def is_running(self) -> bool:
        """是否正在打包。"""
        return self._runner is not None and self._runner.is_running

    def _emit(self, line: str) -> None:
        if self.on_log:
            self.on_log(line)
