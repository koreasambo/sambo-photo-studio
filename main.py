from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from sambo_photo.main_window import MainWindow


def resource_root() -> Path:
    # PyInstaller onefile extracts bundled data to sys._MEIPASS.
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("삼보사진관")
    window = MainWindow(resource_root() / "presets")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
