"""主窗口的 GUI 构建测试（offscreen 平台，无需真实显示器）。"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow


class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_window_builds(self):
        """窗口能正常构建，标题正确。"""
        w = MainWindow()
        self.assertEqual(w.windowTitle(), "高岛的快递分拣站")
        self.assertFalse(w.pack_btn.isEnabled())  # 脚本为空 → 主按钮禁用
        w.close()

    def test_pack_btn_enabled_when_script_set(self):
        """填入脚本后主按钮启用。"""
        w = MainWindow()
        w.script_edit.setText("test.py")
        self.assertTrue(w.pack_btn.isEnabled())
        w.close()

    def test_log_append(self):
        """日志追加正常。"""
        w = MainWindow()
        w._append_log("hello")
        self.assertIn("hello", w.log_view.toPlainText())
        w.close()


if __name__ == "__main__":
    unittest.main()
