# -*- coding: utf-8 -*-
"""入口：启动连点器应用。"""

import tkinter as tk

from ui import App, BG


def main():
    root = tk.Tk()
    root.geometry("340x500")
    root.configure(bg=BG)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
