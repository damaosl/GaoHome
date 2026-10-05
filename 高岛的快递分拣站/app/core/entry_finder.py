"""入口查找器：给定一个文件夹，自动找出最适合打包的入口文件。

纯逻辑模块：只依赖标准库，不依赖 UI、也不依赖 PyInstaller，
可以在无图形环境、甚至未安装 PyInstaller 时被独立测试。

启发式（来自 GitHub 调研的通用实践，参考 QPyPack 等工具）：
1. 递归扫描文件夹下的 Python 脚本（.py / .pyw）；
2. 跳过虚拟环境、缓存、依赖等与入口无关的目录（EXCLUDE_DIRS），
   隐藏目录（点开头）也一并跳过；
3. 忽略 __init__.py（模块声明文件，不是入口）；
4. 候选按「入口得分」排序：常见入口名（main / app / run / start /
   server / gui / cli / __main__）优先，同一优先级下目录层级浅的优先，
   最后按路径字典序，保证结果稳定可复现；
5. 若第一名与第二名得分相同（如根目录下同时有 a.py 与 b.py），
   视为"有歧义"，由调用方（GUI）弹窗让用户选择。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# 可作为入口的脚本扩展名（与 config.PYTHON_SUFFIXES 保持一致）
PYTHON_SUFFIXES = (".py", ".pyw")

# 常见入口文件名（不含扩展名，小写；越靠前越优先）
PRIORITY_STEMS = ("main", "app", "run", "start", "server", "gui", "cli", "__main__")

# 扫描时跳过的目录：与打包入口无关，避免误选、也避免扫到依赖库拖慢速度
EXCLUDE_DIRS = {
    "__pycache__",
    ".git", ".hg", ".svn", ".idea", ".vscode",
    ".pytest_cache", ".mypy_cache", ".tox", ".nox", ".eggs",
    "venv", ".venv", "env", ".env", ".conda", "envs",
    "build", "dist", "node_modules", "site-packages",
}


def _rank_key(path: Path, root: Path) -> tuple:
    """候选入口的排序得分：(入口名优先级, 目录深度, 路径)。

    值越小越"适合当入口"；tuple 自带字典序比较。
    """
    relative = path.relative_to(root)
    depth = len(relative.parts) - 1
    stem = path.stem.lower()
    if stem in PRIORITY_STEMS:
        priority = PRIORITY_STEMS.index(stem)
    else:
        priority = len(PRIORITY_STEMS)
    return (priority, depth, relative.as_posix().lower())


@dataclass
class EntryScanResult:
    """一次文件夹扫描的结果。"""

    # 扫描的文件夹（规范化后的字符串路径）
    folder: str

    # 候选入口文件，已按"更适合当入口"排序（best 为第一名）
    candidates: List[Path]

    # 扫描中被忽略的文件（如 __init__.py），供日志与提示使用
    ignored: List[str] = field(default_factory=list)

    @property
    def best(self) -> Optional[Path]:
        """自动识别出的最佳入口；没有候选时为 None。"""
        return self.candidates[0] if self.candidates else None

    @property
    def is_ambiguous(self) -> bool:
        """前两名是否同「优先级、深度」（此时自动挑选不可靠，应让用户选择）。

        只比较得分的前两项，路径仅用于稳定排序，不参与歧义判定。
        """
        if len(self.candidates) < 2:
            return False
        folder = Path(self.folder)
        return _rank_key(self.candidates[0], folder)[:2] == _rank_key(self.candidates[1], folder)[:2]


def scan_entry_candidates(folder: str) -> EntryScanResult:
    """扫描文件夹，返回按"适合当入口"排序的候选文件列表。

    调用方用法：
        result = scan_entry_candidates(folder)
        if result.best is None:      # 未找到候选
            ...
        elif result.is_ambiguous:    # 多个同级候选，弹窗让用户选择
            ...
        else:                        # 直接用 result.best
            ...
    """
    root = Path(folder)
    if not root.is_dir():
        return EntryScanResult(folder=str(root), candidates=[])

    candidates: List[Path] = []
    ignored: List[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # 剪枝：跳过与入口无关的目录（隐藏目录也一并跳过）
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.startswith(".")
        )
        current = Path(dirpath)
        for name in sorted(filenames):
            path = current / name
            if path.suffix.lower() not in PYTHON_SUFFIXES:
                continue
            if path.stem == "__init__":
                ignored.append(str(path))
                continue
            candidates.append(path)

    candidates.sort(key=lambda p: _rank_key(p, root))
    return EntryScanResult(
        folder=str(root), candidates=candidates, ignored=ignored
    )
