"""
dialogs.py

Dialogs used across the application.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSlider, QComboBox, QCheckBox,
                             QFileDialog, QGroupBox, QSpinBox, QMessageBox,
                             QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
                             QFrame, QScrollArea, QColorDialog, QTextEdit,
                             QListWidget, QTabWidget, QHeaderView, QTableWidget,
                             QTableWidgetItem, QSplitter)

class GifExportDialog(QDialog):
    def __init__(self, total_snapshots: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export GIF Animation")
        self.total_snapshots = total_snapshots
        self.init_ui()

    def init_ui(self):
        from config import GIF
        layout = QFormLayout(self)

        # Frame range
        self.start_spin = QSpinBox()
        self.start_spin.setMinimum(0)
        self.start_spin.setMaximum(self.total_snapshots - 1)
        self.start_spin.setValue(0)
        layout.addRow("Start frame:", self.start_spin)

        self.end_spin = QSpinBox()
        self.end_spin.setMinimum(0)
        self.end_spin.setMaximum(self.total_snapshots - 1)
        self.end_spin.setValue(self.total_snapshots - 1)
        layout.addRow("End frame:", self.end_spin)

        # Frame skip
        self.skip_spin = QSpinBox()
        self.skip_spin.setMinimum(1)
        self.skip_spin.setMaximum(GIF.MAX_FRAME_SKIP)
        self.skip_spin.setValue(GIF.DEFAULT_SKIP)
        self.skip_spin.setToolTip("Use every Nth frame (1 = all frames)")
        layout.addRow("Frame skip:", self.skip_spin)

        # FPS
        self.fps_spin = QSpinBox()
        self.fps_spin.setMinimum(GIF.MIN_FPS)
        self.fps_spin.setMaximum(GIF.MAX_FPS)
        self.fps_spin.setValue(GIF.DEFAULT_FPS)
        layout.addRow("FPS:", self.fps_spin)

        # DPI (used by 2-D viewers; ignored by volume viewer)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setMinimum(GIF.MIN_DPI)
        self.dpi_spin.setMaximum(GIF.MAX_DPI)
        self.dpi_spin.setValue(GIF.DEFAULT_DPI)
        self.dpi_spin.setSingleStep(GIF.DPI_STEP)
        layout.addRow("DPI (quality):", self.dpi_spin)

        # Preserve labels (2-D viewers) / preserve title (volume viewer)
        self.preserve_labels_check = QCheckBox("Preserve axes and labels")
        self.preserve_labels_check.setChecked(False)
        self.preserve_labels_check.setToolTip(
            "Keep axes, grid, and labels in GIF (uncheck for clean presentation)"
        )
        layout.addRow("", self.preserve_labels_check)

        # Info note
        info_label = QLabel("Note: GIF will capture current window size")
        info_label.setStyleSheet("color: gray; font-style: italic; font-size: 10px;")
        layout.addRow("", info_label)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def get_settings(self) -> dict:
        return {
            'start': self.start_spin.value(),
            'end': self.end_spin.value(),
            'skip': self.skip_spin.value(),
            'fps': self.fps_spin.value(),
            'dpi': self.dpi_spin.value(),
            'preserve_labels': self.preserve_labels_check.isChecked(),
            'preserve_title': self.preserve_labels_check.isChecked(),
        }
