"""
slice_panels.py

Panels for 3D slice and volume rendering controls.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSlider, QComboBox, QCheckBox,
                             QFileDialog, QGroupBox, QSpinBox, QMessageBox,
                             QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
                             QFrame, QScrollArea, QColorDialog, QTextEdit,
                             QListWidget, QTabWidget, QHeaderView, QTableWidget,
                             QTableWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from config import COLORMAPS, VOLUME


class SliceControlPanel(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        rho_group = QGroupBox("Radial Slice (ρ)")
        rho_layout = QVBoxLayout(rho_group)

        self.show_rho = QCheckBox("Show")
        self.show_rho.stateChanged.connect(self.changed)
        rho_layout.addWidget(self.show_rho)

        rho_row = QHBoxLayout()
        rho_row.addWidget(QLabel("r:"))
        self.rho_slider = QSlider(Qt.Horizontal)
        self.rho_slider.setRange(0, 100)
        self.rho_slider.setValue(50)
        self.rho_slider.valueChanged.connect(self.changed)
        rho_row.addWidget(self.rho_slider)

        # Spinbox showing physical radius value
        self.rho_spin = QDoubleSpinBox()
        self.rho_spin.setRange(0.0, 999.0)
        self.rho_spin.setDecimals(3)
        self.rho_spin.setSingleStep(0.1)
        self.rho_spin.setFixedWidth(72)
        self.rho_spin.setToolTip("Physical radius value (read/write)")
        rho_row.addWidget(self.rho_spin)

        # Keep slider <-> spinbox in sync (physical update happens in viewer)
        self.rho_slider.valueChanged.connect(self._on_rho_slider)
        self.rho_spin.valueChanged.connect(self._on_rho_spin)
        rho_layout.addLayout(rho_row)

        # Expose a label alias so viewer label-update code still works
        self.rho_label = self.rho_spin  # alias
        layout.addWidget(rho_group)

        phi_group = QGroupBox("Angular Slice (φ)")
        phi_layout = QVBoxLayout(phi_group)

        self.show_phi = QCheckBox("Show")
        self.show_phi.stateChanged.connect(self.changed)
        phi_layout.addWidget(self.show_phi)

        phi_row = QHBoxLayout()
        phi_row.addWidget(QLabel("°:"))
        self.phi_slider = QSlider(Qt.Horizontal)
        self.phi_slider.setRange(0, 360)
        self.phi_slider.setValue(0)
        self.phi_slider.valueChanged.connect(self.changed)
        phi_row.addWidget(self.phi_slider)
        self.phi_spin = QDoubleSpinBox()
        self.phi_spin.setRange(0.0, 360.0)
        self.phi_spin.setDecimals(1)
        self.phi_spin.setSingleStep(1.0)
        self.phi_spin.setFixedWidth(72)
        self.phi_spin.setToolTip("Angle in degrees (read/write)")
        phi_row.addWidget(self.phi_spin)
        self.phi_slider.valueChanged.connect(self._on_phi_slider)
        self.phi_spin.valueChanged.connect(self._on_phi_spin)
        self.phi_label = self.phi_spin  # alias
        phi_layout.addLayout(phi_row)
        layout.addWidget(phi_group)

        z_group = QGroupBox("Vertical Slice (z)")
        z_layout = QVBoxLayout(z_group)

        self.show_z = QCheckBox("Show")
        self.show_z.stateChanged.connect(self.changed)
        z_layout.addWidget(self.show_z)

        z_row = QHBoxLayout()
        z_row.addWidget(QLabel("z:"))
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setRange(0, 100)
        self.z_slider.setValue(50)
        self.z_slider.valueChanged.connect(self.changed)
        z_row.addWidget(self.z_slider)
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(0.0, 999.0)
        self.z_spin.setDecimals(3)
        self.z_spin.setSingleStep(0.1)
        self.z_spin.setFixedWidth(72)
        self.z_spin.setToolTip("Physical z height value (read/write)")
        z_row.addWidget(self.z_spin)
        self.z_slider.valueChanged.connect(self._on_z_slider)
        self.z_spin.valueChanged.connect(self._on_z_spin)
        self.z_label = self.z_spin  # alias
        z_layout.addLayout(z_row)
        layout.addWidget(z_group)

        cmap_row = QHBoxLayout()
        cmap_row.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(COLORMAPS.SLICES)
        self.cmap_combo.currentTextChanged.connect(self.changed)
        cmap_row.addWidget(self.cmap_combo)
        layout.addLayout(cmap_row)

        layout.addStretch()

        # Internal ranges (physical units) - updated by viewer after data load
        self._rho_max = 1.0
        self._z_max = 1.0
        self._updating = False  # guard against recursive sync

    def _on_rho_slider(self, v: int):
        if self._updating:
            return
        self._updating = True
        self.rho_spin.setValue(v / 100.0 * self._rho_max)
        self._updating = False

    def _on_rho_spin(self, v: float):
        if self._updating:
            return
        self._updating = True
        if self._rho_max > 0:
            self.rho_slider.setValue(int(v / self._rho_max * 100))
        self._updating = False
        self.changed.emit()

    def _on_phi_slider(self, v: int):
        if self._updating:
            return
        self._updating = True
        self.phi_spin.setValue(float(v))
        self._updating = False

    def _on_phi_spin(self, v: float):
        if self._updating:
            return
        self._updating = True
        self.phi_slider.setValue(int(v))
        self._updating = False
        self.changed.emit()

    def _on_z_slider(self, v: int):
        if self._updating:
            return
        self._updating = True
        self.z_spin.setValue(v / 100.0 * self._z_max)
        self._updating = False

    def _on_z_spin(self, v: float):
        if self._updating:
            return
        self._updating = True
        if self._z_max > 0:
            self.z_slider.setValue(int(v / self._z_max * 100))
        self._updating = False
        self.changed.emit()

    def update_ranges(self, rho_max: float, z_max: float):
        self._rho_max = rho_max
        self._z_max = z_max
        self.rho_spin.setRange(0.0, rho_max)
        self.rho_spin.setSingleStep(rho_max / 100.0)
        self.z_spin.setRange(0.0, z_max)
        self.z_spin.setSingleStep(z_max / 100.0)

        # Sync spinboxes to current slider positions
        self.rho_spin.setValue(self.rho_slider.value() / 100.0 * rho_max)
        self.z_spin.setValue(self.z_slider.value() / 100.0 * z_max)


class VolumeControlPanel(QWidget):
    changed = pyqtSignal()
    opacity_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.show_volume = QCheckBox("Enable Volume Rendering")
        self.show_volume.stateChanged.connect(self.changed)
        layout.addWidget(self.show_volume)

        # Resolution
        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Resolution:"))
        self.resolution = QComboBox()
        self.resolution.addItems(["Low (30³)", "Medium (50³)", "High (70³)", "Ultra (90³)"])
        self.resolution.setCurrentIndex(0)
        self.resolution.currentTextChanged.connect(self.changed)
        res_row.addWidget(self.resolution)
        layout.addLayout(res_row)

        # Colormap
        cmap_row = QHBoxLayout()
        cmap_row.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(COLORMAPS.VOLUME)
        self.cmap_combo.currentTextChanged.connect(self.changed)
        cmap_row.addWidget(self.cmap_combo)
        layout.addLayout(cmap_row)

        # Max opacity
        max_op_row = QHBoxLayout()
        max_op_row.addWidget(QLabel("Max Opacity:"))
        self.opacity_max = QSlider(Qt.Horizontal)
        self.opacity_max.setRange(VOLUME.MAX_OPACITY_SLIDER_MIN, VOLUME.MAX_OPACITY_SLIDER_MAX)
        self.opacity_max.setValue(int(VOLUME.DEFAULT_MAX_OPACITY * 100))
        self.opacity_max.valueChanged.connect(self.opacity_changed)
        max_op_row.addWidget(self.opacity_max)
        self.opacity_max_label = QLabel(f"{int(VOLUME.DEFAULT_MAX_OPACITY * 100)}%")
        self.opacity_max.valueChanged.connect(lambda v: self.opacity_max_label.setText(f"{v}%"))
        max_op_row.addWidget(self.opacity_max_label)
        layout.addLayout(max_op_row)

        # Min opacity
        layout.addSpacing(10)
        min_op_row = QHBoxLayout()
        min_op_row.addWidget(QLabel("Min Opacity:"))
        self.opacity_min = QSlider(Qt.Horizontal)
        self.opacity_min.setRange(0, VOLUME.MIN_OPACITY_SLIDER_MAX)
        self.opacity_min.setValue(int(VOLUME.DEFAULT_MIN_OPACITY * 100))
        self.opacity_min.valueChanged.connect(self.opacity_changed)
        min_op_row.addWidget(self.opacity_min)
        self.opacity_min_label = QLabel(f"{int(VOLUME.DEFAULT_MIN_OPACITY * 100)}%")
        self.opacity_min.valueChanged.connect(lambda v: self.opacity_min_label.setText(f"{v}%"))
        min_op_row.addWidget(self.opacity_min_label)
        layout.addLayout(min_op_row)

        # Threshold
        threshold_layout = QVBoxLayout()
        threshold_layout.addWidget(QLabel("Transparency Threshold:"))
        threshold_row = QHBoxLayout()
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.0, VOLUME.THRESHOLD_MAX)
        self.threshold.setValue(VOLUME.DEFAULT_THRESHOLD)
        self.threshold.setSingleStep(0.1)
        self.threshold.setDecimals(2)
        self.threshold.setToolTip("Values below this are transparent")
        self.threshold.valueChanged.connect(self.opacity_changed)
        threshold_row.addWidget(self.threshold)
        threshold_row.addWidget(QLabel("(hide below)"))
        threshold_layout.addLayout(threshold_row)
        self.range_label = QLabel("Data range: [-, -]")
        self.range_label.setStyleSheet("color: gray; font-size: 9px;")
        threshold_layout.addWidget(self.range_label)
        layout.addLayout(threshold_layout)

        layout.addStretch()


class VolumePositionPanel(QWidget):
    time_position_changed = pyqtSignal()
    scale_bar_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        from config import TITLE, SCALAR_BAR
        layout = QVBoxLayout(self)

        group = QGroupBox("UI Element Positions")
        inner = QVBoxLayout(group)

        inner.addWidget(QLabel("<b>Time Text Position:</b>"))

        tx_row = QHBoxLayout()
        tx_row.addWidget(QLabel("X:"))
        self.time_x = QDoubleSpinBox()
        self.time_x.setRange(0.0, 1.0)
        self.time_x.setValue(TITLE.DEFAULT_POSITION_X)
        self.time_x.setSingleStep(0.05)
        self.time_x.valueChanged.connect(self.time_position_changed)
        tx_row.addWidget(self.time_x)
        inner.addLayout(tx_row)

        ty_row = QHBoxLayout()
        ty_row.addWidget(QLabel("Y:"))
        self.time_y = QDoubleSpinBox()
        self.time_y.setRange(0.0, 1.0)
        self.time_y.setValue(TITLE.DEFAULT_POSITION_Y)
        self.time_y.setSingleStep(0.05)
        self.time_y.valueChanged.connect(self.time_position_changed)
        ty_row.addWidget(self.time_y)
        inner.addLayout(ty_row)

        inner.addSpacing(10)
        inner.addWidget(QLabel("<b>Scale Bar Position:</b>"))

        sx_row = QHBoxLayout()
        sx_row.addWidget(QLabel("X:"))
        self.scale_x = QDoubleSpinBox()
        self.scale_x.setRange(0.0, 1.0)
        self.scale_x.setValue(SCALAR_BAR.DEFAULT_X)
        self.scale_x.setSingleStep(0.05)
        self.scale_x.valueChanged.connect(self.scale_bar_changed)
        sx_row.addWidget(self.scale_x)
        inner.addLayout(sx_row)

        sy_row = QHBoxLayout()
        sy_row.addWidget(QLabel("Y:"))
        self.scale_y = QDoubleSpinBox()
        self.scale_y.setRange(0.0, 1.0)
        self.scale_y.setValue(SCALAR_BAR.DEFAULT_Y)
        self.scale_y.setSingleStep(0.05)
        self.scale_y.valueChanged.connect(self.scale_bar_changed)
        sy_row.addWidget(self.scale_y)
        inner.addLayout(sy_row)

        layout.addWidget(group)
        layout.addStretch()
