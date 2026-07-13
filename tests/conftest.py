"""Make the board's src/ modules importable by the host test suite.

usage_view.py is pure Python (no MicroPython imports), so it runs fine under CPython.
"""
import os
import sys

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, os.path.abspath(SRC))
