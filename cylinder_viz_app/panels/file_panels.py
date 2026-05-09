"""
file_panels.py

Panels for file loading, snapshot navigation and info display.
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSlider, QComboBox, QCheckBox,
                             QFileDialog, QGroupBox, QSpinBox, QMessageBox,
                             QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
                             QFrame, QScrollArea, QColorDialog, QTextEdit,
                             QListWidget, QTabWidget, QHeaderView, QTableWidget,
                             QTableWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from config import COLORMAPS, UI, MULTI_SPATIOTEMPORAL


class FileLoadPanel(QGroupBox):
    polar_loaded = pyqtSignal(str, dict, list)  # path, params, snapshots
    cyl_loaded = pyqtSignal(str, dict, list)

    def __init__(self, parent=None):
        super().__init__("1. Load Data Files", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Polar file
        polar_layout = QHBoxLayout()
        polar_layout.addWidget(QLabel("Polar (Top):"))
        self.polar_label = QLabel("No file")
        self.polar_label.setStyleSheet("color: gray; font-style: italic;")
        polar_layout.addWidget(self.polar_label, 1)
        polar_btn = QPushButton("Browse...")
        polar_btn.clicked.connect(self.load_polar_file)
        polar_layout.addWidget(polar_btn)
        layout.addLayout(polar_layout)

        # Cylindrical file
        cyl_layout = QHBoxLayout()
        cyl_layout.addWidget(QLabel("Cylindrical (Side):"))
        self.cyl_label = QLabel("No file")
        self.cyl_label.setStyleSheet("color: gray; font-style: italic;")
        cyl_layout.addWidget(self.cyl_label, 1)
        cyl_btn = QPushButton("Browse...")
        cyl_btn.clicked.connect(self.load_cyl_file)
        cyl_layout.addWidget(cyl_btn)
        layout.addLayout(cyl_layout)

        self.setLayout(layout)

    def load_polar_file(self):
        from core.data_loader import load_snapshots

        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Polar Data", "", "Data Files (*.dat);;All Files (*)"
        )
        if filename:
            try:
                params, snapshots = load_snapshots(filename)
                if snapshots and snapshots[0]['type'] == 'polar':
                    self.polar_label.setText(os.path.basename(filename))
                    self.polar_label.setStyleSheet("color: green;")
                    self.polar_loaded.emit(filename, params, snapshots)
                else:
                    QMessageBox.warning(self, "Error", "Not a valid polar data file!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")

    def load_cyl_file(self):
        from core.data_loader import load_snapshots

        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Cylindrical Data", "", "Data Files (*.dat);;All Files (*)"
        )
        if filename:
            try:
                params, snapshots = load_snapshots(filename)
                if snapshots and snapshots[0]['type'] == 'cylindrical':
                    self.cyl_label.setText(os.path.basename(filename))
                    self.cyl_label.setStyleSheet("color: green;")
                    self.cyl_loaded.emit(filename, params, snapshots)
                else:
                    QMessageBox.warning(self, "Error", "Not a valid cylindrical data file!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")


class SnapshotNavigationPanel(QGroupBox):
    snapshot_changed = pyqtSignal(int)  # new index

    def __init__(self, parent=None):
        super().__init__("2. Snapshot Selection", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Navigation controls
        nav_layout = QHBoxLayout()

        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.clicked.connect(self.prev_snapshot)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)

        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(0)
        self.spinbox.setMaximum(0)
        self.spinbox.valueChanged.connect(self.snapshot_changed.emit)
        self.spinbox.setEnabled(False)
        nav_layout.addWidget(self.spinbox, 1)

        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_snapshot)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

        # Time display
        self.time_label = QLabel("Time: --")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)

        self.setLayout(layout)

    def set_num_snapshots(self, num: int):
        self.spinbox.setMaximum(max(0, num - 1))
        self.spinbox.setEnabled(num > 0)
        self.prev_btn.setEnabled(num > 0)
        self.next_btn.setEnabled(num > 0)

    def set_time(self, time: float):
        self.time_label.setText(f"Time: {time:.6f}")

    def prev_snapshot(self):
        if self.spinbox.value() > 0:
            self.spinbox.setValue(self.spinbox.value() - 1)

    def next_snapshot(self):
        if self.spinbox.value() < self.spinbox.maximum():
            self.spinbox.setValue(self.spinbox.value() + 1)

    def get_current_index(self) -> int:
        return self.spinbox.value()

    def set_index(self, idx: int):
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(max(0, min(idx, self.spinbox.maximum())))
        self.spinbox.blockSignals(False)


class InfoPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Info", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.info_label = QLabel("Load data files to begin")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def set_text(self, text: str):
        self.info_label.setText(text)


class VolumeFilePanel(QWidget):
    file_load_requested = pyqtSignal()
    snapshot_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        file_group = QGroupBox("Load 3D Data")
        file_layout = QVBoxLayout(file_group)

        load_btn = QPushButton("Browse for 3D Volume Data...")
        load_btn.clicked.connect(self.file_load_requested)
        file_layout.addWidget(load_btn)

        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: gray; font-size: 10px;")
        file_layout.addWidget(self.file_label)
        layout.addWidget(file_group)

        snap_group = QGroupBox("Snapshot")
        snap_layout = QVBoxLayout(snap_group)

        nav = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self._prev)
        nav.addWidget(self.prev_btn)

        self.snapshot_spin = QSpinBox()
        self.snapshot_spin.setMinimum(0)
        self.snapshot_spin.setMaximum(0)
        self.snapshot_spin.setEnabled(False)
        self.snapshot_spin.valueChanged.connect(self.snapshot_changed)
        nav.addWidget(self.snapshot_spin, 1)

        self.next_btn = QPushButton("▶")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._next)
        nav.addWidget(self.next_btn)
        snap_layout.addLayout(nav)

        self.time_label = QLabel("Time: --")
        self.time_label.setAlignment(Qt.AlignCenter)
        snap_layout.addWidget(self.time_label)
        layout.addWidget(snap_group)

        info_group = QGroupBox("Model Parameters & Info")
        info_layout = QVBoxLayout(info_group)
        self.info_text = QTextEdit() if self._has_qtextedit() else QLabel()
        if hasattr(self.info_text, 'setReadOnly'):
            self.info_text.setReadOnly(True)
            self.info_text.setMaximumHeight(200)
            self.info_text.setStyleSheet("font-size: 10px; font-family: monospace;")
            self.info_text.setPlainText("Load a 3D volume file to begin")
        info_layout.addWidget(self.info_text)
        layout.addWidget(info_group)

    @staticmethod
    def _has_qtextedit():
        try:
            from PyQt5.QtWidgets import QTextEdit  # noqa
            return True
        except ImportError:
            return False

    def on_file_loaded(self, filename: str, n_snapshots: int):
        self.file_label.setText(filename.split('/')[-1].split('\\')[-1])
        self.file_label.setStyleSheet("color: green; font-size: 10px;")
        self.snapshot_spin.setMaximum(n_snapshots - 1)
        self.snapshot_spin.setValue(0)
        self.snapshot_spin.setEnabled(True)
        self.prev_btn.setEnabled(True)
        self.next_btn.setEnabled(True)

    def set_info_text(self, text: str):
        if hasattr(self.info_text, 'setPlainText'):
            self.info_text.setPlainText(text)

    def set_time_label(self, t: float):
        self.time_label.setText(f"Time: {t:.6f}")

    def _prev(self):
        v = self.snapshot_spin.value()
        if v > 0:
            self.snapshot_spin.setValue(v - 1)

    def _next(self):
        v = self.snapshot_spin.value()
        if v < self.snapshot_spin.maximum():
            self.snapshot_spin.setValue(v + 1)


class MultiFilePanel(QWidget):
    add_file_requested = pyqtSignal()
    remove_file_requested = pyqtSignal()
    clear_files_requested = pyqtSignal()
    grid_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # ── File list ─────────────────────────────────────────────────────
        file_group = QGroupBox("Data Files")
        file_layout = QVBoxLayout(file_group)

        add_btn = QPushButton("➕ Add Spatiotemporal File")
        add_btn.clicked.connect(self.add_file_requested)
        file_layout.addWidget(add_btn)

        remove_btn = QPushButton("➖ Remove Selected")
        remove_btn.clicked.connect(self.remove_file_requested)
        file_layout.addWidget(remove_btn)

        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(self.clear_files_requested)
        file_layout.addWidget(clear_btn)

        file_layout.addWidget(QLabel("Loaded files:"))
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(UI.FILE_LIST_MAX_HEIGHT)
        file_layout.addWidget(self.file_list)
        layout.addWidget(file_group)

        # ── Grid layout ───────────────────────────────────────────────────
        grid_group = QGroupBox("Grid Layout")
        grid_layout = QVBoxLayout(grid_group)

        rows_row = QHBoxLayout()
        rows_row.addWidget(QLabel("Rows:"))
        self.rows_spin = QSpinBox()
        self.rows_spin.setMinimum(MULTI_SPATIOTEMPORAL.GRID_MIN)
        self.rows_spin.setMaximum(MULTI_SPATIOTEMPORAL.GRID_MAX)
        self.rows_spin.setValue(MULTI_SPATIOTEMPORAL.DEFAULT_ROWS)
        self.rows_spin.valueChanged.connect(lambda _: self.grid_changed.emit())
        rows_row.addWidget(self.rows_spin)
        grid_layout.addLayout(rows_row)

        cols_row = QHBoxLayout()
        cols_row.addWidget(QLabel("Columns:"))
        self.cols_spin = QSpinBox()
        self.cols_spin.setMinimum(MULTI_SPATIOTEMPORAL.GRID_MIN)
        self.cols_spin.setMaximum(MULTI_SPATIOTEMPORAL.GRID_MAX)
        self.cols_spin.setValue(MULTI_SPATIOTEMPORAL.DEFAULT_COLS)
        self.cols_spin.valueChanged.connect(lambda _: self.grid_changed.emit())
        cols_row.addWidget(self.cols_spin)
        grid_layout.addLayout(cols_row)

        preset_row = QHBoxLayout()
        for label, r, c in [("2×2", 2, 2), ("3×2", 3, 2), ("2×3", 2, 3)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, rv=r, cv=c: self._set_preset(rv, cv))
            preset_row.addWidget(btn)
        grid_layout.addLayout(preset_row)
        layout.addWidget(grid_group)

    def _set_preset(self, rows: int, cols: int):
        self.rows_spin.setValue(rows)
        self.cols_spin.setValue(cols)


class SnapshotViewerPanel(QWidget):
    load_requested = pyqtSignal()
    snapshot_changed = pyqtSignal(int)
    prev_requested = pyqtSignal()
    next_requested = pyqtSignal()
    colormap_changed = pyqtSignal(str)
    gif_requested = pyqtSignal()

    def __init__(self, browse_label: str = "Browse for Data...",
                 extra_display_widget=None, parent=None):
        super().__init__(parent)
        self._build_ui(browse_label, extra_display_widget)

    def _build_ui(self, browse_label: str, extra_widget):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        file_group = QGroupBox("Load Data")
        file_layout = QVBoxLayout(file_group)

        load_btn = QPushButton(browse_label)
        load_btn.clicked.connect(self.load_requested)
        file_layout.addWidget(load_btn)

        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("padding: 5px; background: #f0f0f0;")
        file_layout.addWidget(self.file_label)
        layout.addWidget(file_group)

        nav_group = QGroupBox("Snapshot Navigation")
        nav_layout = QVBoxLayout(nav_group)

        self.snapshot_label = QLabel("Snapshot: 0/0")
        nav_layout.addWidget(self.snapshot_label)

        self.snapshot_spin = QSpinBox()
        self.snapshot_spin.setMinimum(0)
        self.snapshot_spin.setMaximum(0)
        self.snapshot_spin.valueChanged.connect(self.snapshot_changed)
        nav_layout.addWidget(self.snapshot_spin)

        btn_row = QHBoxLayout()
        prev_btn = QPushButton("◀ Prev")
        prev_btn.clicked.connect(self.prev_requested)
        next_btn = QPushButton("Next ▶")
        next_btn.clicked.connect(self.next_requested)
        btn_row.addWidget(prev_btn)
        btn_row.addWidget(next_btn)
        nav_layout.addLayout(btn_row)
        layout.addWidget(nav_group)

        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout(display_group)

        cmap_row = QHBoxLayout()
        cmap_row.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(COLORMAPS.SNAPSHOT)
        self.cmap_combo.currentTextChanged.connect(self.colormap_changed)
        cmap_row.addWidget(self.cmap_combo)
        display_layout.addLayout(cmap_row)

        if extra_widget is not None:
            display_layout.addWidget(extra_widget)
        layout.addWidget(display_group)

        gif_btn = QPushButton("🎬 Export GIF Animation")
        gif_btn.clicked.connect(self.gif_requested)
        gif_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 8px; "
            "background-color: #4CAF50; color: white; }")
        layout.addWidget(gif_btn)

        layout.addStretch()

    def on_file_loaded(self, basename: str, n_snapshots: int):
        self.file_label.setText(f"Loaded: {basename}\n{n_snapshots} snapshots")
        self.snapshot_spin.setMaximum(n_snapshots - 1)
        self.snapshot_spin.setValue(0)
