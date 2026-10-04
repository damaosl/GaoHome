"""主窗口：极简风格的一键打包界面。

布局：标题 → 分隔线 → 脚本选择 → 选项 → 图标（可选）→ 按钮 → 日志。
单列纵向流、大留白，与 theme 的极简风格一致。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import PROJECT_ICON_PATH
from app.core.config import PackConfig
from app.gui.theme import QSS
from app.gui.worker import PackWorker
from app.utils.icon_utils import convert_to_ico


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._worker: Optional[PackWorker] = None
        self._dist_dir: str = ""  # 最近一次打包产物的输出目录

        self.setWindowTitle("高岛的快递分拣站")
        self.setWindowIcon(QIcon(PROJECT_ICON_PATH))
        self.setStyleSheet(QSS)

        self._build_ui()

    # ---------- UI 构建 ----------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(36, 30, 36, 26)
        root.setSpacing(14)

        # 标题区
        title = QLabel("高岛的快递分拣站")
        title.setObjectName("title")
        subtitle = QLabel("一键将 Python 脚本打包为 exe")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(self._separator())

        # 脚本文件
        root.addWidget(self._section("脚本文件"))
        self.script_edit = QLineEdit()
        self.script_edit.setPlaceholderText("选择要打包的 .py 文件")
        self.script_edit.textChanged.connect(self._on_input_changed)
        browse_script = QPushButton("浏览")
        browse_script.clicked.connect(self._browse_script)
        root.addLayout(self._row(self.script_edit, browse_script))

        # 选项
        self.onefile_check = QCheckBox("打包为单文件")
        self.onefile_check.setChecked(True)
        self.console_check = QCheckBox("显示控制台窗口")
        self.console_check.setChecked(True)
        opts = QHBoxLayout()
        opts.setSpacing(24)
        opts.addWidget(self.onefile_check)
        opts.addWidget(self.console_check)
        opts.addStretch(1)
        root.addLayout(opts)

        # 图标（可选）
        root.addWidget(self._section("图标（可选）"))
        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("选择 .ico 图标，留空则不设置")
        browse_icon = QPushButton("浏览")
        browse_icon.clicked.connect(self._browse_icon)
        root.addLayout(self._row(self.icon_edit, browse_icon))

        # 按钮区
        self.pack_btn = QPushButton("开始打包")
        self.pack_btn.setObjectName("primary")
        self.pack_btn.setEnabled(False)  # 初始脚本为空，禁用主按钮
        self.pack_btn.clicked.connect(self._start_pack)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_pack)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addWidget(self.pack_btn, 1)
        btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

        # 日志区
        log_header = QHBoxLayout()
        log_header.addWidget(self._section("日志"))
        log_header.addStretch(1)
        self.open_dir_btn = QPushButton("打开输出目录")
        self.open_dir_btn.setEnabled(False)
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        log_header.addWidget(self.open_dir_btn)
        root.addLayout(log_header)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("log")
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(180)
        root.addWidget(self.log_view, 1)

        self.resize(540, 640)

    # ---------- 小工具 ----------
    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section")
        return label

    @staticmethod
    def _row(*widgets: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        for w in widgets:
            row.addWidget(w)
        # 第一个控件占满剩余空间
        if widgets:
            row.setStretch(0, 1)
        return row

    @staticmethod
    def _separator() -> QFrame:
        frame = QFrame()
        frame.setObjectName("separator")
        frame.setFrameShape(QFrame.HLine)
        return frame

    # ---------- 事件处理 ----------
    def _browse_script(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Python 脚本", "", "Python 脚本 (*.py *.pyw)"
        )
        if path:
            self.script_edit.setText(path)

    def _browse_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图标", "", "图标文件 (*.ico *.png)"
        )
        if path:
            self.icon_edit.setText(path)

    def _on_input_changed(self, _text: str) -> None:
        """脚本路径为空时禁用主按钮，避免误点。"""
        self.pack_btn.setEnabled(bool(self.script_edit.text().strip()) and not self._is_running())

    def _start_pack(self) -> None:
        script = self.script_edit.text().strip()
        if not script:
            self._append_log("[错误] 请先选择脚本文件")
            return

        icon = self.icon_edit.text().strip()
        if icon.lower().endswith(".png"):
            try:
                icon = convert_to_ico(icon)
                self._append_log(f"[提示] 图标已转换：{icon}")
            except (ValueError, RuntimeError) as exc:
                self._append_log(f"[错误] 图标转换失败：{exc}")
                return

        config = PackConfig(
            script_path=script,
            onefile=self.onefile_check.isChecked(),
            console=self.console_check.isChecked(),
            icon_path=icon,
        )

        self._append_log(f"开始打包：{script}")
        self.open_dir_btn.setEnabled(False)
        self._set_running(True)

        self._worker = PackWorker(config)
        self._worker.log.connect(self._append_log)
        self._worker.pack_done.connect(self._on_pack_done)
        self._worker.start()

    def _cancel_pack(self) -> None:
        if self._worker is not None:
            self._append_log("[提示] 正在取消打包…")
            self._worker.cancel()

    def _on_pack_done(self, code: int) -> None:
        self._set_running(False)
        if code == 0:
            self._append_log("✓ 打包成功")
            self._dist_dir = str(Path(self.script_edit.text().strip()).parent / "dist")
            self._append_log(f"产物目录：{self._dist_dir}")
            self.open_dir_btn.setEnabled(True)
        else:
            self._append_log("✗ 打包失败（详见上方日志）")
        # 保留引用直到线程结束；置空以便下次打包复用
        self._worker = None

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def _open_output_dir(self) -> None:
        """用系统文件管理器打开产物目录。"""
        if self._dist_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._dist_dir))

    # ---------- 拖拽支持 ----------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """拖入 .py/.pyw 文件时自动填入脚本路径。"""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith((".py", ".pyw")):
                self.script_edit.setText(path)
                break

    # ---------- 状态 ----------
    def _is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _set_running(self, running: bool) -> None:
        self.pack_btn.setEnabled(not running and bool(self.script_edit.text().strip()))
        self.cancel_btn.setEnabled(running)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt 命名
        """关闭窗口时若有打包进行中，先取消再退出。"""
        if self._is_running() and self._worker is not None:
            self._worker.cancel()
            self._worker.wait(3000)
        event.accept()
