"""入口选择对话框：文件夹扫描发现多个同级候选时，让用户挑一个。

极简风格与主窗口一致：白底近黑字、细边框、无多余装饰；
候选以相对路径展示，双击或选中后点「选择」确认。
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from app.gui.theme import QSS


class EntrySelectDialog(QDialog):
    """列出候选入口文件供用户选择，selected_path 为最终结果。"""

    def __init__(self, folder: Path, candidates: List[Path], parent=None) -> None:
        super().__init__(parent)
        self._selected: Optional[Path] = None

        self.setWindowTitle("选择打包入口")
        self.setStyleSheet(QSS)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 18)
        layout.setSpacing(12)

        # 标题与提示
        title = QLabel("发现多个候选入口")
        title.setObjectName("dialogTitle")
        hint = QLabel(f"文件夹：{folder}\n请选择要打包的入口文件：")
        hint.setObjectName("dialogHint")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        # 候选列表（显示相对路径，数据存绝对路径）
        self._list = QListWidget()
        for candidate in candidates:
            relative = self._display_path(candidate, folder)
            item = QListWidgetItem(relative)
            item.setData(Qt.ItemDataRole.UserRole, str(candidate))
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())
        layout.addWidget(self._list, 1)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("选择")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _display_path(candidate: Path, folder: Path) -> str:
        """展示用路径：优先显示相对文件夹的路径，失败时退回文件名。"""
        try:
            return candidate.relative_to(folder).as_posix()
        except ValueError:
            return candidate.name

    def accept(self) -> None:  # noqa: D102 - Qt 约定
        item = self._list.currentItem()
        if item is not None:
            self._selected = Path(item.data(Qt.ItemDataRole.UserRole))
        super().accept()

    @property
    def selected_path(self) -> Optional[Path]:
        """用户最终选择的入口文件；未选择时为 None。"""
        return self._selected
