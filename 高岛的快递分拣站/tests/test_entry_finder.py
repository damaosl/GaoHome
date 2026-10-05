"""entry_finder 模块的单元测试：文件夹入口自动识别。

纯逻辑测试：用临时目录搭建虚拟项目结构，不触发 PyInstaller。
"""
import tempfile
import unittest
from pathlib import Path

from app.core.entry_finder import scan_entry_candidates


class EntryFinderTestBase(unittest.TestCase):
    """共用脚手架：在临时目录中创建文件后调用扫描。"""

    def scan(self, files: list[str]) -> "scan_entry_candidates":
        """files 形如 ["main.py", "src/app.py"]，基于临时目录创建并扫描。"""
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        for rel in files:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# test\n", encoding="utf-8")
        return scan_entry_candidates(str(root))

    def tearDown(self) -> None:
        tmp = getattr(self, "_tmp", None)
        if tmp is not None:
            tmp.cleanup()


class TestEntryFinder(EntryFinderTestBase):
    def test_priority_name_wins(self):
        """常见入口名按优先级排序：main.py 排在 app.py 前面。"""
        result = self.scan(["app.py", "main.py"])
        self.assertEqual([p.name for p in result.candidates], ["main.py", "app.py"])
        self.assertEqual(result.best.name, "main.py")
        self.assertFalse(result.is_ambiguous)

    def test_single_candidate_auto_picked(self):
        """只有一个候选时直接作为最佳入口，且无歧义。"""
        result = self.scan(["foo.py"])
        self.assertEqual(result.best.name, "foo.py")
        self.assertFalse(result.is_ambiguous)

    def test_init_py_ignored(self):
        """__init__.py 不是入口，被忽略并记录。"""
        result = self.scan(["pkg/__init__.py"])
        self.assertEqual(result.candidates, [])
        self.assertEqual(len(result.ignored), 1)
        self.assertTrue(result.ignored[0].endswith("__init__.py"))

    def test_excluded_dirs_skipped(self):
        """虚拟环境、缓存、依赖目录里的脚本不参与候选。"""
        result = self.scan(
            [
                "main.py",
                "venv/Lib/site-packages/evil.py",
                "__pycache__/cache.py",
                ".git/hook.py",
                "node_modules/dep.py",
                "build/tmp.py",
                "dist/out.py",
                ".hidden/secret.py",
            ]
        )
        self.assertEqual([p.name for p in result.candidates], ["main.py"])

    def test_priority_beats_depth(self):
        """子目录的 main.py 优先于根目录的无名脚本。"""
        result = self.scan(["foo.py", "src/main.py"])
        self.assertEqual(result.best.name, "main.py")

    def test_shallow_priority_beats_nested_priority(self):
        """同为优先名时，层级浅的（根目录）胜出。"""
        result = self.scan(["src/main.py", "main.py"])
        relative = result.best.relative_to(Path(result.folder)).as_posix()
        self.assertEqual(relative, "main.py")  # 根目录直属文件
        self.assertFalse(result.is_ambiguous)

    def test_two_main_ambiguous(self):
        """两个同级 main.py 得分相同，视为有歧义。"""
        result = self.scan(["src/main.py", "app/main.py"])
        self.assertEqual(len(result.candidates), 2)
        self.assertTrue(result.is_ambiguous)

    def test_two_plain_files_ambiguous(self):
        """根目录两个普通脚本同级，视为有歧义。"""
        result = self.scan(["foo.py", "bar.py"])
        self.assertTrue(result.is_ambiguous)

    def test_stable_ordering(self):
        """同分候选按路径字典序稳定排序。"""
        result = self.scan(["foo.py", "bar.py"])
        self.assertEqual([p.name for p in result.candidates], ["bar.py", "foo.py"])

    def test_pyw_supported(self):
        """main.pyw 按 stem 参与优先级匹配。"""
        result = self.scan(["main.pyw", "app.py"])
        self.assertEqual(result.best.name, "main.pyw")

    def test_non_python_files_not_candidates(self):
        """txt / exe 等非脚本文件不是候选（入口自动识别只认脚本）。"""
        result = self.scan(["README.txt", "data.json", "run.exe"])
        self.assertEqual(result.candidates, [])

    def test_empty_folder(self):
        """空文件夹：无候选、无歧义。"""
        result = self.scan([])
        self.assertEqual(result.candidates, [])
        self.assertIsNone(result.best)
        self.assertFalse(result.is_ambiguous)

    def test_not_a_directory(self):
        """传入文件路径而非文件夹时安全返回空结果。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text("# x", encoding="utf-8")
            result = scan_entry_candidates(str(path))
        self.assertEqual(result.candidates, [])

    def test_nested_module_layout(self):
        """典型 src 布局：根目录无脚本时直接选中 src/main.py。"""
        result = self.scan(["README.md", "src/gaodao/__init__.py", "src/gaodao/main.py"])
        self.assertEqual(result.best.name, "main.py")
        self.assertFalse(result.is_ambiguous)


if __name__ == "__main__":
    unittest.main()
