# 高岛的快递分拣站

一键将 Python 脚本打包为 Windows 可执行文件（exe）的图形化工具。
界面与主题统一采用**极简风格**：纯白底、近黑字、细线分隔，无多余装饰。

## 功能

- 选择 `.py` / `.pyw` 脚本，一键打包为 exe
- 单文件 / 单目录、显示 / 隐藏控制台窗口
- 自定义图标（`.ico` / `.png`，png 自动转为 ico）
- 拖拽脚本文件到窗口即可填入
- 后台打包不卡界面，实时显示日志
- 打包完成后一键打开输出目录

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
│   │   ├── process_runner.py  # 后台进程执行 + 流式日志
│   │   └── packer.py          # 打包编排
│   ├── gui/                   # 界面层
│   │   ├── main_window.py     # 极简主窗口
│   │   ├── worker.py          # QThread 后台线程
│   │   └── theme.py           # 极简主题 QSS
│   └── utils/
│       └── icon_utils.py      # png → ico 转换
└── tests/                     # 单元测试
```

## 测试

```bash
python -m unittest discover -s tests -v          # 常规测试
SMOKE=1 python -m unittest tests.test_packer.TestPackerSmoke -v  # 真实打包冒烟
```
