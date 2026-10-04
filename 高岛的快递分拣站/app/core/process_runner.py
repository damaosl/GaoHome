"""进程运行器：在后台执行命令，逐行流式回传 stdout/stderr。

关键设计：
- 用两个后台线程分别读 stdout 与 stderr，避免任一路管道缓冲区写满
  导致子进程阻塞（死锁），这是 PyInstaller 这类长时进程的常见坑；
- 按行回传（PyInstaller 的进度信息按行输出，如 "Building PKG..."）；
- 编码取系统 locale 首选编码（中文 Windows 为 GBK/cp936），保证中文
  文件名与报错不乱码，同时用 errors="replace" 兜底防崩溃；
- 提供 cancel() 供 GUI 的"取消打包"按钮调用。
"""
from __future__ import annotations

import locale
import subprocess
import threading
from typing import Callable, List, Optional

# 日志回调：接收一行已去换行符的文本
LogCallback = Callable[[str], None]


def _read_stream(stream, callback: Optional[LogCallback]) -> None:
    """持续读取一个流直到 EOF，逐行交给回调。"""
    for line in iter(stream.readline, ""):
        if callback:
            callback(line.rstrip("\n"))
    stream.close()


class ProcessRunner:
    """封装一次子进程执行：启动、流式回传、等待结束、取消。"""

    def __init__(
        self,
        command: List[str],
        on_stdout: Optional[LogCallback] = None,
        on_stderr: Optional[LogCallback] = None,
        cwd: Optional[str] = None,
    ) -> None:
        self.command = command
        self.on_stdout = on_stdout
        self.on_stderr = on_stderr
        self.cwd = cwd
        self._proc: Optional[subprocess.Popen] = None

    def run(self) -> int:
        """执行命令并等待结束，返回退出码（0 表示成功）。"""
        encoding = locale.getpreferredencoding(False) or "utf-8"

        self._proc = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=encoding,
            errors="replace",
            cwd=self.cwd,
        )

        # 两个守护线程分别排空 stdout/stderr，防止管道阻塞
        t_out = threading.Thread(
            target=_read_stream, args=(self._proc.stdout, self.on_stdout), daemon=True
        )
        t_err = threading.Thread(
            target=_read_stream, args=(self._proc.stderr, self.on_stderr), daemon=True
        )
        t_out.start()
        t_err.start()

        self._proc.wait()
        t_out.join(timeout=2)
        t_err.join(timeout=2)
        return self._proc.returncode

    def cancel(self) -> None:
        """终止正在运行的子进程（若尚未结束）。"""
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()

    @property
    def is_running(self) -> bool:
        """子进程是否仍在运行。"""
        return self._proc is not None and self._proc.poll() is None
