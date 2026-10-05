"""后台打包线程：把耗时的打包过程移出主线程，保持界面流畅。

Qt 信号从后台线程发射时会自动以队列方式投递到主线程，因此
GUI 只需 connect 这些信号即可安全更新界面，无需手动加锁。
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.core.config import PackConfig
from app.core.packer import Packer


class PackWorker(QThread):
    """在后台线程执行一次打包。

    信号：
        log        : str —— 一行打包日志（stdout/stderr 合并流）
        pack_done  : int —— 打包完成，参数为退出码（0 成功）
        output_dir : str —— 打包成功后的产物存储目录
    """

    # 注意：不能覆盖 QThread 自带的 finished（无参）信号，故取名 pack_done
    log = Signal(str)
    pack_done = Signal(int)
    output_dir = Signal(str)  # 打包成功后的产物存储目录

    def __init__(self, config: PackConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._packer = Packer(config, on_log=self.log.emit)

    def run(self) -> None:  # noqa: D102 - QThread 入口
        code = self._packer.pack()
        self.pack_done.emit(code)
        if code == 0:
            self.output_dir.emit(self._packer.output_dir)

    def cancel(self) -> None:
        """取消打包（可从主线程调用，terminate 是线程安全的）。"""
        self._packer.cancel()
