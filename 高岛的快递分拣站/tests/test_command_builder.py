"""command_builder 模块的单元测试（标准库 unittest，零额外依赖）。"""
import unittest

from app.core.command_builder import build_command
from app.core.config import PackConfig


class TestBuildCommand(unittest.TestCase):
    def test_basic_onefile_console(self):
        """默认：单文件 + 显示控制台，只带脚本路径。"""
        cfg = PackConfig(script_path="main.py")
        self.assertEqual(build_command(cfg), ["--onefile", "main.py"])

    def test_onedir_and_noconsole(self):
        """单目录 + 隐藏控制台。"""
        cfg = PackConfig(script_path="main.py", onefile=False, console=False)
        self.assertEqual(build_command(cfg), ["--onedir", "--noconsole", "main.py"])

    def test_name_icon_outputdir(self):
        """名称、图标、输出目录。"""
        cfg = PackConfig(
            script_path="main.py",
            name="myapp",
            icon_path="icon.ico",
            output_dir="dist_out",
        )
        self.assertEqual(
            build_command(cfg),
            [
                "--onefile",
                "--name", "myapp",
                "--icon", "icon.ico",
                "--distpath", "dist_out",
                "main.py",
            ],
        )

    def test_clean_and_data_and_hidden(self):
        """清理、附加数据、隐藏导入。"""
        cfg = PackConfig(
            script_path="main.py",
            clean=True,
            add_data=["res;res", "cfg.ini;."],
            hidden_imports=["cv2", "numpy"],
        )
        self.assertEqual(
            build_command(cfg),
            [
                "--onefile",
                "--clean",
                "--add-data", "res;res",
                "--add-data", "cfg.ini;.",
                "--hidden-import", "cv2",
                "--hidden-import", "numpy",
                "main.py",
            ],
        )

    def test_extra_args_preserve_order(self):
        """额外参数原样追加，且位于脚本路径之前。"""
        cfg = PackConfig(script_path="main.py", extra_args=["--upx-dir", "upx"])
        self.assertEqual(
            build_command(cfg),
            ["--onefile", "--upx-dir", "upx", "main.py"],
        )

    def test_script_path_always_last(self):
        """脚本路径必须始终是最后一个参数。"""
        cfg = PackConfig(
            script_path="main.py",
            name="x",
            icon_path="i.ico",
            clean=True,
            extra_args=["--foo"],
        )
        cmd = build_command(cfg)
        self.assertEqual(cmd[-1], "main.py")


if __name__ == "__main__":
    unittest.main()
