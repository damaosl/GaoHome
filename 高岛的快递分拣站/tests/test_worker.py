"""worker 模块的单元测试。

说明：不触发真实打包（慢），用"脚本不存在"的配置走快速失败路径，
验证 log / pack_done 两个信号的发射是否正常。
"""
import unittest

from PySide6.QtCore import QCoreApplication

from app.core.config import PackConfig
from app.gui.worker import PackWorker


class TestPackWorker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # QThread/Signal 需要一个 QCoreApplication 实例
        cls._app = QCoreApplication.instance() or QCoreApplication([])

    def test_signals_on_fail_fast(self):
        logs: list[str] = []
        codes: list[int] = []
        outputs: list[str] = []

        worker = PackWorker(PackConfig(script_path="不存在.py"))
        worker.log.connect(logs.append)
        worker.pack_done.connect(codes.append)
        worker.output_dir.connect(outputs.append)

        # 直接调用 run()（同线程直连，信号同步触发），不走事件循环
        worker.run()

        self.assertEqual(codes, [1])
        self.assertTrue(any("文件不存在" in ln for ln in logs))
        self.assertEqual(outputs, [])  # 失败时不发射 output_dir


if __name__ == "__main__":
    unittest.main()
