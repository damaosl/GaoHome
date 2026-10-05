"""config 模块的单元测试（纯数据层，无 UI 依赖）。"""
import tempfile
import unittest
from pathlib import Path

from app.core.config import PackConfig


class TestResolvedOutputDir(unittest.TestCase):
    def test_default_dist_next_to_script(self):
        """未指定 output_dir 时，产物默认在脚本所在目录的 dist 下。"""
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / "main.py"
            script.write_text("", encoding="utf-8")
            cfg = PackConfig(script_path=str(script))
            self.assertEqual(cfg.resolved_output_dir, Path(d) / "dist")

    def test_explicit_absolute_output_dir(self):
        """指定绝对 output_dir 时，直接使用该目录。"""
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as out:
            script = Path(d) / "main.py"
            script.write_text("", encoding="utf-8")
            cfg = PackConfig(script_path=str(script), output_dir=out)
            self.assertEqual(cfg.resolved_output_dir, Path(out).resolve())

    def test_explicit_relative_output_dir_based_on_script_dir(self):
        """相对 output_dir 基于脚本所在目录解析。"""
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / "main.py"
            script.write_text("", encoding="utf-8")
            cfg = PackConfig(script_path=str(script), output_dir="release/bin")
            self.assertEqual(cfg.resolved_output_dir, Path(d).resolve() / "release" / "bin")


if __name__ == "__main__":
    unittest.main()
