import os
import sys

# Adaugă directorul rădăcină în PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from src.login_interface import LoginInterface

if __name__ == "__main__":
    root = tk.Tk()
    app = LoginInterface(root)
    root.mainloop() 