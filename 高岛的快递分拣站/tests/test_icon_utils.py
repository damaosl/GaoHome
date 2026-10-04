"""icon_utils 模块的单元测试。"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from pathlib import Path

from PySide6.QtGui import QImage

from app.utils.icon_utils import convert_to_ico


class TestIconUtils(unittest.TestCase):
    def test_convert_png_to_ico(self):
        with tempfile.TemporaryDirectory() as d:
            png = Path(d) / "icon.png"
            img = QImage(64, 64, QImage.Format_ARGB32)
            img.fill(0xFF3366CC)
            self.assertTrue(img.save(str(png), "png"))

            ico = convert_to_ico(str(png))
            self.assertTrue(Path(ico).exists())
            self.assertEqual(Path(ico).suffix, ".ico")
            self.assertGreater(Path(ico).stat().st_size, 0)

    def test_convert_invalid_image_raises(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.png"
            bad.write_bytes(b"not an image")
            with self.assertRaises(ValueError):
                convert_to_ico(str(bad))


if __name__ == "__main__":
    unittest.main()
