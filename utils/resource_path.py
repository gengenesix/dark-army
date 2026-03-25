"""
resource_path() — resolve file paths correctly whether running from source
or from a PyInstaller-packaged build (sys._MEIPASS).

Usage:
    from utils.resource_path import resource_path
    path = resource_path("assets/icons/echelon.ico")
"""
import sys
import os
from pathlib import Path


def resource_path(relative: str) -> str:
    """
    Return the absolute path to a bundled resource.

    - In development: resolves relative to the project root (parent of utils/)
    - In PyInstaller build: resolves relative to sys._MEIPASS (the temp bundle dir)
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller extracts bundled files to sys._MEIPASS at runtime
        base = Path(sys._MEIPASS)
    else:
        # Development: go up one level from utils/ to project root
        base = Path(__file__).parent.parent

    return str(base / relative)
