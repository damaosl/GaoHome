# 高岛的快递分拣站

一键将任意文件打包为 Windows 可执行文件（exe）的图形化工具。
界面与主题统一采用**极简风格**：纯白底、近黑字、细线分隔，无多余装饰。

## 功能

- 选择任意文件（脚本、文档、图片等）一键打包为 exe；非脚本文件会内置一个解包启动器，运行时自动打开
- 可放入文件夹：自动扫描并识别最合适的打包入口（main.py 等常见入口名优先），多个同级候选时弹窗选择
- 单文件 / 单目录、显示 / 隐藏控制台窗口
- 自定义图标（`.ico` / `.png`，png 自动转为 ico）
- 拖拽任意文件或文件夹到窗口即可填入
- 后台打包不卡界面，实时显示日志
- 打包完成后显示产物存储位置，并可一键打开输出目录

## 运行

```bash
pip install -r requirements.txt
python main.py
```

依赖：Python 3.8+、PySide6-Essentials、PyInstaller。

## 项目结构

```
├── main.py                    # 程序入口
├── requirements.txt
├── assets/app.ico             # 项目图标
├── app/
│   ├── core/                  # 核心逻辑层（不依赖 UI，可独立测试）
│   │   ├── config.py          # 打包配置数据模型
│   │   ├── command_builder.py # 配置 → PyInstaller 命令行
│   │   ├── entry_finder.py    # 文件夹入口自动识别（扫描 + 排序）
│   │   ├── launcher.py        # 非脚本文件的解包启动器
│   │   ├── process_runner.py  # 后台进程执行 + 流式日志
│   │   └── packer.py          # 打包编排
│   ├── gui/                   # 界面层
│   │   ├── main_window.py     # 极简主窗口
│   │   ├── worker.py          # QThread 后台线程
│   │   ├── theme.py           # 极简主题 QSS
│   │   └── widgets/
│   │       └── entry_select_dialog.py  # 多候选入口选择对话框
│   └── utils/
│       └── icon_utils.py      # png → ico 转换
└── tests/                     # 单元测试
```

## 测试

```bash
python -m unittest discover -s tests -v          # 常规测试
SMOKE=1 python -m unittest tests.test_packer.TestPackerSmoke -v  # 真实打包冒烟
```

## 入口自动识别规则

放入文件夹后，按以下规则自动找出合适的入口脚本（`.py` / `.pyw`）：

1. 跳过虚拟环境、缓存、依赖等无关目录（`venv`、`build`、`dist`、`__pycache__`、`.git`、`node_modules` 等）及隐藏目录；
2. 忽略 `__init__.py`；
3. 常见入口名优先：`main` > `app` > `run` > `start` > `server` > `gui` > `cli` > `__main__`，其次目录层级浅的优先；
4. 若第一名与第二名难分高下（同一层级下的多个同级候选），弹出选择框由你决定。
