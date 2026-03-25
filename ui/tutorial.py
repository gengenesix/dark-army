from PyQt6.QtWidgets import (QWidget, QPushButton, QLabel, QVBoxLayout,
                              QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor


class TutorialOverlay(QWidget):
    """Semi-transparent overlay with step-by-step first-launch tutorial."""

    STEPS = [
        "1. Upload a face photo here \u2192",
        "2. Choose your performance mode",
        "3. Hit START to begin!",
        "4. Select \u2018Dark-Army Camera\u2019 in your video app",
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.current_step = 0
        self._setup_ui()
        self.resize(parent.size())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        self._step_label = QLabel(self.STEPS[0])
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_label.setWordWrap(True)
        self._step_label.setStyleSheet(
            "color: white; font-size: 20px; font-weight: 700; "
            "background: rgba(0,0,0,180); border-radius: 10px; padding: 18px 32px;"
        )
        layout.addWidget(self._step_label)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(16)

        self._next_btn = QPushButton("Next \u2192")
        self._next_btn.setObjectName("primaryBtn")
        self._next_btn.setFixedWidth(120)
        self._next_btn.clicked.connect(self._on_next)

        skip_btn = QPushButton("Skip Tutorial")
        skip_btn.setStyleSheet(
            "color: #8888A0; background: transparent; border: none; font-size: 13px;"
        )
        skip_btn.clicked.connect(self.close)

        btn_row.addWidget(self._next_btn)
        btn_row.addWidget(skip_btn)
        layout.addLayout(btn_row)

    def _on_next(self):
        self.current_step += 1
        if self.current_step >= len(self.STEPS):
            self.close()
            return
        self._step_label.setText(self.STEPS[self.current_step])
        if self.current_step == len(self.STEPS) - 1:
            self._next_btn.setText("Got it!")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 140))
        painter.end()

    def show(self):
        self.resize(self.parent().size())
        super().show()
        self.raise_()
