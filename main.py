import sys
import os

# ── Windows DPI awareness (must be before Qt initializes) ──
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

import signal
import logging
from pathlib import Path

# ── Speed up startup: disable slow network checks before ANY imports ──
os.environ.setdefault("ALBUMENTATIONS_DISABLE_VERSION_CHECK", "1")
os.environ.setdefault("MPLCONFIGDIR", str(Path.home() / ".cache" / "matplotlib"))
os.environ["MPLBACKEND"] = "Agg"  # force headless matplotlib (insightface uses it)
os.environ.setdefault("NO_ALBUMENTATIONS_UPDATE", "1")

from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont

from utils.logger import setup_logging
from utils.resource_path import resource_path
from config.manager import AppConfig, ConfigManager
from core.hardware import HardwareDetector
from ui.main_window import MainWindow
from ui.onboarding import OnboardingDialog
from ui.tray import EchelonTray


def _make_splash(app):
    """Create a fast splash screen so user sees something immediately."""
    icon_path = Path(__file__).parent / "assets" / "icons" / "icon_256.png"
    pix = QPixmap(300, 300)
    pix.fill(QColor("#08090E"))

    painter = QPainter(pix)
    if icon_path.exists():
        logo = QPixmap(str(icon_path)).scaled(120, 120,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(90, 60, logo)

    painter.setPen(QColor("#F0F0FA"))
    font = QFont()
    font.setPointSize(22)
    font.setBold(True)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
    painter.setFont(font)
    painter.drawText(0, 205, 300, 40, Qt.AlignmentFlag.AlignCenter, "DARK-ARMY")

    painter.setPen(QColor("#50516A"))
    font2 = QFont()
    font2.setPointSize(11)
    painter.setFont(font2)
    painter.drawText(0, 245, 300, 30, Qt.AlignmentFlag.AlignCenter, "by Zero  ·  v1.0")

    painter.setPen(QColor("#5C5FFF"))
    font3 = QFont()
    font3.setPointSize(10)
    painter.setFont(font3)
    painter.drawText(0, 270, 300, 25, Qt.AlignmentFlag.AlignCenter, "Loading...")

    painter.end()

    splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()
    return splash


def main():
    setup_logging()
    logger = logging.getLogger("echelon.main")
    logger.info("Echelon starting up...")

    app = QApplication(sys.argv)
    app.setApplicationName("Dark-Army")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("DarkArmy")

    # Show splash IMMEDIATELY so user sees the app opened
    splash = _make_splash(app)

    # Load stylesheet
    qss_path = Path(resource_path("assets/styles/theme.qss"))
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding='utf-8'))
        logger.info("Stylesheet loaded")

    # Set app icon
    icon_path = Path(resource_path("assets/icons/icon_256.png"))
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    splash.showMessage("  Detecting hardware...",
                       Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                       QColor("#5C5FFF"))
    app.processEvents()

    config_mgr = ConfigManager()
    config = config_mgr.load()

    hw_detector = HardwareDetector()
    hw_info = hw_detector.detect()
    hw_detector.log_system_info(hw_info)

    if config.first_launch:
        config.performance_mode = hw_info.recommended_mode

    was_first_launch = config.first_launch

    if config.first_launch:
        splash.finish(None)
        onboarding = OnboardingDialog(config)
        result = onboarding.exec()
        if result != OnboardingDialog.DialogCode.Accepted:
            logger.info("Onboarding cancelled, exiting")
            sys.exit(0)
        splash = _make_splash(app)

    splash.showMessage("  Building UI...",
                       Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                       QColor("#5C5FFF"))
    app.processEvents()

    window = MainWindow(config, hw_info)
    tray = EchelonTray(window, app)
    window.tray = tray
    tray.show()

    # Close splash and show window
    splash.finish(window)

    if not config.start_minimized:
        window.show()
        window.raise_()
        window.activateWindow()
        if was_first_launch:
            QTimer.singleShot(500, window.show_tutorial)
    else:
        tray.show_notification("Echelon", "Started in background. Click tray icon to open.")

    signal.signal(signal.SIGINT, lambda *_: app.quit())

    logger.info("Echelon UI ready")
    exit_code = app.exec()

    config_mgr.save(config)
    logger.info(f"Echelon exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
