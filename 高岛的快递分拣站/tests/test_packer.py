"""packer 模块的单元测试。

说明：真实打包耗时较长（几十秒到几分钟），故拆成两类：
1. 快测（默认运行）：校验失败路径、日志回传等不触发 PyInstaller 的逻辑；
2. 冒烟测试（SMOKE=1 时运行）：真实打包一个极简脚本并验证 exe 产物。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

from app.core.config import PackConfig
from app.core.packer import Packer


class TestPackerValidation(unittest.TestCase):
    def test_invalid_script_fails_fast(self):
        """脚本不存在时应在校验阶段拦截，返回非零且不发命令。"""
        logs: list[str] = []
        packer = Packer(
            PackConfig(script_path="不存在的脚本.py"), on_log=logs.append
        )
        code = packer.pack()
        self.assertNotEqual(code, 0)
        self.assertTrue(any("脚本文件不存在" in ln for ln in logs))

    def test_wrong_extension_fails_fast(self):
        """非 .py/.pyw 扩展名应在校验阶段拦截。"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        try:
            logs: list[str] = []
            packer = Packer(PackConfig(script_path=path), on_log=logs.append)
            code = packer.pack()
            self.assertNotEqual(code, 0)
            self.assertTrue(any("仅支持" in ln for ln in logs))
        finally:
            os.unlink(path)


@unittest.skipUnless(os.environ.get("SMOKE") == "1", "设置 SMOKE=1 才运行真实打包冒烟测试")
class TestPackerSmoke(unittest.TestCase):
    def test_real_pack_produces_exe(self):
        """真实打包一个打印 hello 的脚本，验证退出码 0 且生成 exe。"""
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / "hello.py"
            script.write_text("print('hello from exe')\n", encoding="utf-8")

            logs: list[str] = []
            cfg = PackConfig(script_path=str(script), onefile=True, console=True)
            code = Packer(cfg, on_log=logs.append).pack()

            self.assertEqual(code, 0, "打包失败，日志：\n" + "\n".join(logs))
            exe = Path(d) / "dist" / "hello.exe"
            self.assertTrue(exe.exists(), f"未找到产物：{exe}")


if __name__ == "__main__":
    unittest.main()
