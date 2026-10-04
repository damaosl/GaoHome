"""process_runner 模块的单元测试。"""
import sys
import unittest

from app.core.process_runner import ProcessRunner

PY = sys.executable


class TestProcessRunner(unittest.TestCase):
    def test_stdout_captured_and_exit_zero(self):
        lines: list[str] = []
        runner = ProcessRunner(
            [PY, "-c", "print('hello'); print('world')"], on_stdout=lines.append
        )
        code = runner.run()
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["hello", "world"])

    def test_stderr_captured(self):
        errs: list[str] = []
        runner = ProcessRunner(
            [PY, "-c", "import sys; sys.stderr.write('boom\\n')"],
            on_stderr=errs.append,
        )
        code = runner.run()
        self.assertEqual(code, 0)
        self.assertEqual(errs, ["boom"])

    def test_nonzero_exit_code(self):
        runner = ProcessRunner([PY, "-c", "import sys; sys.exit(3)"])
        self.assertEqual(runner.run(), 3)

    def test_cwd_respected(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            runner = ProcessRunner(
                [PY, "-c", "import os; print(os.getcwd())"],
                on_stdout=lambda ln: self.assertEqual(ln, os.path.realpath(d)),
                cwd=d,
            )
            self.assertEqual(runner.run(), 0)


if __name__ == "__main__":
    unittest.main()
