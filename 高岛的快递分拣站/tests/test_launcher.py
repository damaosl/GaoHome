"""launcher 模块的单元测试。"""
import tempfile
import unittest
from pathlib import Path

from app.core.launcher import render_launcher, write_launcher


class TestLauncher(unittest.TestCase):
    def test_render_substitutes_payload_name(self):
        """载荷文件名被替换进模板，占位符消失。"""
        src = render_launcher("报告.txt")
        self.assertIn("'报告.txt'", src)
        self.assertNotIn("{payload_name}", src)

    def test_write_launcher_creates_file(self):
        """写出的启动器文件存在且包含载荷名。"""
        with tempfile.TemporaryDirectory() as d:
            path = write_launcher("a.txt", d)
            self.assertEqual(Path(path).name, "launcher.py")
            self.assertTrue(Path(path).exists())
            self.assertIn("a.txt", Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
