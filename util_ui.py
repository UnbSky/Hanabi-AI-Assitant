from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QMainWindow, QLabel, QHBoxLayout, QGridLayout, QScrollBar, QFileDialog, QDesktopWidget

class CardButton(QWidget):
    def __init__(self, left_text, right_text, left_color, right_color, active_func, value, choices=None, parent=None):
        super().__init__(parent)
        top_widget = QWidget(self)
        top_widget.setFixedSize(120, 90)

        bottom_widget = QWidget(self)
        bottom_widget.setFixedSize(120, 10)

        layout = QVBoxLayout(self)
        layout.addWidget(top_widget)
        layout.addWidget(bottom_widget)

        self.setLayout(layout)
        self.setFixedSize(120, 100)

        self.left_button = QPushButton(left_text)
        self.right_button = QPushButton(right_text)
        self.value = value

        self.left_color = left_color
        self.right_color = right_color
        self.left_button.setStyleSheet(f"{left_color}; font: bold 36px;")
        self.right_button.setStyleSheet(f"{right_color}; font: bold 36px;")

        self.left_button.clicked.connect(lambda _, xx=value: active_func(xx))
        self.right_button.clicked.connect(lambda _, xx=value: active_func(xx))

        layout = QHBoxLayout(top_widget)
        layout.addWidget(self.left_button)
        layout.addWidget(self.right_button)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

    def highlight(self, lighted):
        if lighted:
            self.left_button.setStyleSheet(f"{self.left_color}; font: bold 45px;")
            self.right_button.setStyleSheet(f"{self.right_color}; font: bold 45px;")
        else:
            self.left_button.setStyleSheet(f"{self.left_color}; font: bold 36px;")
            self.right_button.setStyleSheet(f"{self.right_color}; font: bold 36px;")


class ValueButton(QPushButton):
    def __init__(self, text="", value=None, parent=None):
        super().__init__(text, parent)
        self._value = value

    def set_value(self, value):
        self._value = value

    def get_value(self):
        return self._value