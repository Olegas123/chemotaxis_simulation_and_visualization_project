"""
display_panels.py

Panels for display settings: colormaps, transparency, camera, title.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSlider, QComboBox, QCheckBox,
                             QFileDialog, QGroupBox, QSpinBox, QMessageBox,
                             QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
                             QFrame, QScrollArea, QColorDialog, QTextEdit,
                             QListWidget, QTabWidget, QHeaderView, QTableWidget,
                             QTableWidgetItem, QSplitter, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from config import COLORMAPS, TITLE, COMBINED_VIEWER, MULTI_SPATIOTEMPORAL, SCALAR_BAR


class ColormapPanel(QGroupBox):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("4. Colormaps & Scaling", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Same colormap checkbox
        self.same_cmap_check = QCheckBox("Use same colormap for both")
        self.same_cmap_check.setChecked(True)
        self.same_cmap_check.stateChanged.connect(self.on_same_cmap_changed)
        layout.addWidget(self.same_cmap_check)

        # Disk colormap
        disk_layout = QHBoxLayout()
        disk_layout.addWidget(QLabel("Disk:"))
        self.disk_cmap_combo = QComboBox()
        self.disk_cmap_combo.addItems(COLORMAPS.COMBINED)
        self.disk_cmap_combo.setCurrentText(COLORMAPS.DEFAULT)
        self.disk_cmap_combo.currentTextChanged.connect(self.settings_changed.emit)
        self.disk_cmap_combo.setEnabled(False)
        disk_layout.addWidget(self.disk_cmap_combo)
        layout.addLayout(disk_layout)

        # Cylinder colormap
        cyl_layout = QHBoxLayout()
        cyl_layout.addWidget(QLabel("Cylinder:"))
        self.cyl_cmap_combo = QComboBox()
        self.cyl_cmap_combo.addItems(COLORMAPS.COMBINED)
        self.cyl_cmap_combo.setCurrentText(COLORMAPS.DEFAULT)
        self.cyl_cmap_combo.currentTextChanged.connect(self.settings_changed.emit)
        cyl_layout.addWidget(self.cyl_cmap_combo)
        layout.addLayout(cyl_layout)

        # Separate scaling
        self.separate_scaling_check = QCheckBox("Separate color scaling (recommended)")
        self.separate_scaling_check.setChecked(True)
        self.separate_scaling_check.stateChanged.connect(self.settings_changed.emit)
        layout.addWidget(self.separate_scaling_check)

        # Cylinder intensity boost
        boost_layout = QHBoxLayout()
        boost_layout.addWidget(QLabel("Cylinder intensity boost:"))
        self.boost_slider = QSlider(Qt.Horizontal)
        self.boost_slider.setMinimum(0)
        self.boost_slider.setMaximum(100)
        self.boost_slider.setValue(0)
        self.boost_slider.valueChanged.connect(self.on_boost_changed)
        boost_layout.addWidget(self.boost_slider)
        self.boost_label = QLabel("+0.00")
        boost_layout.addWidget(self.boost_label)
        layout.addLayout(boost_layout)

        # Boost threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Boost only values above:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(0)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        threshold_layout.addWidget(self.threshold_slider)
        self.threshold_label = QLabel("0.00")
        threshold_layout.addWidget(self.threshold_label)
        layout.addLayout(threshold_layout)

        self.setLayout(layout)

    def on_same_cmap_changed(self):
        same = self.same_cmap_check.isChecked()
        self.disk_cmap_combo.setEnabled(not same)

        if same:
            self.disk_cmap_combo.setCurrentText(self.cyl_cmap_combo.currentText())

        self.settings_changed.emit()

    def on_boost_changed(self):
        value = self.boost_slider.value()
        boost = value / 100.0
        self.boost_label.setText(f"+{boost:.2f}")
        self.settings_changed.emit()

    # Handle threshold slider change
    def on_threshold_changed(self):
        value = self.threshold_slider.value()
        threshold = value / 100.0  # Convert to 0.0 - 1.0
        self.threshold_label.setText(f"{threshold:.2f}")
        self.settings_changed.emit()

    def get_settings(self) -> dict:
        same_cmap = self.same_cmap_check.isChecked()
        intensity_boost = self.boost_slider.value() / 100.0
        boost_threshold = self.threshold_slider.value() / 100.0
        return {
            'use_same_colormap': same_cmap,
            'disk_colormap': self.disk_cmap_combo.currentText() if not same_cmap else self.cyl_cmap_combo.currentText(),
            'cylinder_colormap': self.cyl_cmap_combo.currentText(),
            'use_separate_scaling': self.separate_scaling_check.isChecked(),
            'intensity_boost': intensity_boost,
            'boost_threshold': boost_threshold
        }


class TransparencyPanel(QGroupBox):
    transparency_changed = pyqtSignal(float, float)  # disk_alpha, cyl_alpha

    def __init__(self, parent=None):
        super().__init__("3. Transparency", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Disk transparency
        disk_layout = QHBoxLayout()
        disk_layout.addWidget(QLabel("Disk:"))
        self.disk_slider = QSlider(Qt.Horizontal)
        self.disk_slider.setMinimum(0)
        self.disk_slider.setMaximum(100)
        self.disk_slider.setValue(COMBINED_VIEWER.DEFAULT_OPACITY)
        self.disk_slider.valueChanged.connect(self.on_slider_changed)
        disk_layout.addWidget(self.disk_slider)
        self.disk_label = QLabel(f"{COMBINED_VIEWER.DEFAULT_OPACITY}%")
        disk_layout.addWidget(self.disk_label)
        layout.addLayout(disk_layout)

        # Cylinder transparency
        cyl_layout = QHBoxLayout()
        cyl_layout.addWidget(QLabel("Cylinder:"))
        self.cyl_slider = QSlider(Qt.Horizontal)
        self.cyl_slider.setMinimum(0)
        self.cyl_slider.setMaximum(100)
        self.cyl_slider.setValue(COMBINED_VIEWER.DEFAULT_OPACITY)
        self.cyl_slider.valueChanged.connect(self.on_slider_changed)
        cyl_layout.addWidget(self.cyl_slider)
        self.cyl_label = QLabel(f"{COMBINED_VIEWER.DEFAULT_OPACITY}%")
        cyl_layout.addWidget(self.cyl_label)
        layout.addLayout(cyl_layout)

        self.setLayout(layout)

    def on_slider_changed(self):
        disk_val = self.disk_slider.value()
        cyl_val = self.cyl_slider.value()

        self.disk_label.setText(f"{disk_val}%")
        self.cyl_label.setText(f"{cyl_val}%")

        self.transparency_changed.emit(disk_val / 100.0, cyl_val / 100.0)

    def get_transparency(self) -> tuple:
        return (self.disk_slider.value() / 100.0,
                self.cyl_slider.value() / 100.0)


class DisplayOptionsPanel(QGroupBox):
    visibility_changed = pyqtSignal(bool, bool)  # show_disks, show_cylinder
    edges_changed = pyqtSignal(bool)
    bottom_disk_changed = pyqtSignal(bool, bool)  # show_bottom, use_gray

    def __init__(self, parent=None):
        super().__init__("5. Display Options", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.show_disk_check = QCheckBox("Show top/bottom disks")
        self.show_disk_check.setChecked(True)
        self.show_disk_check.stateChanged.connect(self.on_visibility_changed)
        layout.addWidget(self.show_disk_check)

        self.show_cyl_check = QCheckBox("Show cylinder surface")
        self.show_cyl_check.setChecked(True)
        self.show_cyl_check.stateChanged.connect(self.on_visibility_changed)
        layout.addWidget(self.show_cyl_check)

        # Bottom disk options
        from PyQt5.QtWidgets import QLabel
        bottom_label = QLabel("Bottom Disk:")
        bottom_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(bottom_label)

        self.show_bottom_check = QCheckBox("  Show bottom disk")
        self.show_bottom_check.setChecked(True)
        self.show_bottom_check.stateChanged.connect(self.on_bottom_disk_changed)
        layout.addWidget(self.show_bottom_check)

        self.gray_bottom_check = QCheckBox("  Use gray color")
        self.gray_bottom_check.setChecked(False)
        self.gray_bottom_check.stateChanged.connect(self.on_bottom_disk_changed)
        layout.addWidget(self.gray_bottom_check)

        # Mesh edges
        edges_label = QLabel("Mesh Edges:")
        edges_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(edges_label)

        self.show_edges_check = QCheckBox("  Show mesh edges")
        self.show_edges_check.setChecked(False)
        self.show_edges_check.stateChanged.connect(
            lambda: self.edges_changed.emit(self.show_edges_check.isChecked())
        )
        layout.addWidget(self.show_edges_check)

        self.setLayout(layout)

    def on_visibility_changed(self):
        self.visibility_changed.emit(
            self.show_disk_check.isChecked(),
            self.show_cyl_check.isChecked()
        )

    def on_bottom_disk_changed(self):
        self.bottom_disk_changed.emit(
            self.show_bottom_check.isChecked(),
            self.gray_bottom_check.isChecked()
        )

    def get_settings(self) -> dict:
        return {
            'show_disks': self.show_disk_check.isChecked(),
            'show_cylinder': self.show_cyl_check.isChecked(),
            'show_edges': self.show_edges_check.isChecked(),
            'show_bottom': self.show_bottom_check.isChecked(),
            'bottom_gray': self.gray_bottom_check.isChecked()
        }

    def get_bottom_disk_settings(self) -> tuple:
        return (self.show_bottom_check.isChecked(),
                self.gray_bottom_check.isChecked())


class CameraPanel(QGroupBox):
    view_changed = pyqtSignal(str)  # view type
    camera_lock_changed = pyqtSignal(bool)  # lock state

    def __init__(self, parent=None):
        super().__init__("6. Camera", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # View buttons
        view_layout = QHBoxLayout()

        iso_btn = QPushButton("Isometric")
        iso_btn.clicked.connect(lambda: self.view_changed.emit('isometric'))
        view_layout.addWidget(iso_btn)

        top_btn = QPushButton("Top")
        top_btn.clicked.connect(lambda: self.view_changed.emit('top'))
        view_layout.addWidget(top_btn)

        side_btn = QPushButton("Side")
        side_btn.clicked.connect(lambda: self.view_changed.emit('side'))
        view_layout.addWidget(side_btn)

        layout.addLayout(view_layout)

        # Reset button
        reset_btn = QPushButton("Reset Camera")
        reset_btn.clicked.connect(lambda: self.view_changed.emit('isometric'))
        layout.addWidget(reset_btn)

        # Camera lock section
        lock_label = QLabel("Camera Lock:")
        lock_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(lock_label)

        # Lock checkbox
        self.lock_camera_check = QCheckBox("🔒 Lock camera position")
        self.lock_camera_check.setToolTip(
            "Lock camera to prevent changes during data updates."
        )
        self.lock_camera_check.stateChanged.connect(self.on_lock_changed)
        layout.addWidget(self.lock_camera_check)

        # Lock status label
        self.lock_status_label = QLabel("Camera unlocked")
        self.lock_status_label.setStyleSheet("color: gray; font-size: 9px; font-style: italic;")
        layout.addWidget(self.lock_status_label)

        self.setLayout(layout)

    def on_lock_changed(self, state):
        is_locked = state == 2  # Qt.Checked
        self.camera_lock_changed.emit(is_locked)

        # Update status label
        if is_locked:
            self.lock_status_label.setText("Camera locked - position saved")
            self.lock_status_label.setStyleSheet("color: green; font-size: 9px; font-weight: bold;")
        else:
            self.lock_status_label.setText("Camera unlocked")
            self.lock_status_label.setStyleSheet("color: gray; font-size: 9px; font-style: italic;")

    def set_lock_state(self, locked: bool):
        self.lock_camera_check.setChecked(locked)

    def is_locked(self) -> bool:
        return self.lock_camera_check.isChecked()


class TitlePanel(QGroupBox):
    title_settings_changed = pyqtSignal(str, int)  # position, font_size

    def __init__(self, parent=None):
        super().__init__("Title Settings", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Position selector
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Position:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(['Top Center', 'Lower Left', 'Lower Center'])
        self.position_combo.setCurrentIndex(0)  # Default to 'Top Center'
        self.position_combo.currentTextChanged.connect(self.on_settings_changed)
        position_layout.addWidget(self.position_combo)
        layout.addLayout(position_layout)

        # Font size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_spin = QSpinBox()
        self.font_spin.setMinimum(8)
        self.font_spin.setMaximum(24)
        self.font_spin.setValue(TITLE.FONT_SIZE)
        self.font_spin.valueChanged.connect(self.on_settings_changed)
        font_layout.addWidget(self.font_spin)
        layout.addLayout(font_layout)

        self.setLayout(layout)

    def on_settings_changed(self):
        position_map = {
            'Top Center': 'upper_edge',
            'Lower Left': 'lower_left',
            'Lower Center': 'lower_edge'
        }
        position = position_map[self.position_combo.currentText()]
        font_size = self.font_spin.value()
        self.title_settings_changed.emit(position, font_size)

    def get_settings(self) -> dict:
        position_map = {
            'Top Center': 'upper_edge',
            'Lower Left': 'lower_left',
            'Lower Center': 'lower_edge'
        }
        return {
            'position': position_map[self.position_combo.currentText()],
            'font_size': self.font_spin.value()
        }


class MultiDisplayPanel(QWidget):
    settings_changed = pyqtSignal()
    update_requested = pyqtSignal()
    save_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout(display_group)

        cmap_row = QHBoxLayout()
        cmap_row.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(COLORMAPS.SPATIOTEMPORAL)
        self.cmap_combo.currentTextChanged.connect(self.settings_changed)
        cmap_row.addWidget(self.cmap_combo)
        display_layout.addLayout(cmap_row)

        preset_lbl = QLabel("Quick presets:")
        preset_lbl.setStyleSheet("font-size: 9px; color: #666; margin-top: 5px;")
        display_layout.addWidget(preset_lbl)

        preset_row = QHBoxLayout()
        for name in ['viridis', 'plasma', 'hot', 'gray']:
            btn = QPushButton(name.capitalize())
            btn.setStyleSheet("padding: 4px; font-size: 9px;")
            btn.clicked.connect(
                lambda checked, n=name: self.cmap_combo.setCurrentText(n))
            preset_row.addWidget(btn)
        display_layout.addLayout(preset_row)

        self.same_scale_check = QCheckBox("Use same color scale for all panels")
        self.same_scale_check.stateChanged.connect(self.settings_changed)
        display_layout.addWidget(self.same_scale_check)

        self.show_colorbar_check = QCheckBox("Show colorbars")
        self.show_colorbar_check.setChecked(True)
        self.show_colorbar_check.stateChanged.connect(self.settings_changed)
        display_layout.addWidget(self.show_colorbar_check)

        self.show_labels_check = QCheckBox("Show panel labels (a, b, c, ...)")
        self.show_labels_check.setChecked(True)
        self.show_labels_check.stateChanged.connect(self.settings_changed)
        display_layout.addWidget(self.show_labels_check)

        aspect_row = QHBoxLayout()
        aspect_row.addWidget(QLabel("Aspect:"))
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(list(MULTI_SPATIOTEMPORAL.ASPECT_RATIOS.keys()))
        self.aspect_combo.currentTextChanged.connect(self.settings_changed)
        aspect_row.addWidget(self.aspect_combo)
        display_layout.addLayout(aspect_row)
        layout.addWidget(display_group)

        # ── Actions ───────────────────────────────────────────────────────
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)

        update_btn = QPushButton("🔄 Update Plot")
        update_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        update_btn.clicked.connect(self.update_requested)
        action_layout.addWidget(update_btn)

        save_btn = QPushButton("💾 Save Figure")
        save_btn.clicked.connect(self.save_requested)
        action_layout.addWidget(save_btn)
        layout.addWidget(action_group)

        # ── Info ──────────────────────────────────────────────────────────
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout(info_group)
        self.info_label = QLabel(
            "Load spatiotemporal data files to begin.\n\n"
            "Files should contain x-t data with headers:\n"
            "# T = <time_max>\n"
            "# L = <space_max>\n\n"
            "Tip: Use viridis/plasma for colored figures!")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 10px; background: #f0f8ff;")
        info_layout.addWidget(self.info_label)
        layout.addWidget(info_group)

        layout.addStretch()


class AxisLabelPanel(QGroupBox):
    changed = pyqtSignal()

    def __init__(self, default_x: str = 'x', default_y: str = 'y',
                 default_title: str = '', parent=None):
        super().__init__("Axis Labels", parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        x_row = QHBoxLayout()
        x_row.addWidget(QLabel("X:"))
        self.x_edit = QLineEdit(default_x)
        self.x_edit.setPlaceholderText("x-axis label")
        self.x_edit.textChanged.connect(self.changed)
        x_row.addWidget(self.x_edit)
        layout.addLayout(x_row)

        y_row = QHBoxLayout()
        y_row.addWidget(QLabel("Y:"))
        self.y_edit = QLineEdit(default_y)
        self.y_edit.setPlaceholderText("y-axis label")
        self.y_edit.textChanged.connect(self.changed)
        y_row.addWidget(self.y_edit)
        layout.addLayout(y_row)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit(default_title)
        self.title_edit.setPlaceholderText("(auto = time value)")
        self.title_edit.textChanged.connect(self.changed)
        title_row.addWidget(self.title_edit)
        layout.addLayout(title_row)

        cbar_row = QHBoxLayout()
        cbar_row.addWidget(QLabel("Cbar:"))
        self.cbar_edit = QLineEdit(SCALAR_BAR.TITLE)
        self.cbar_edit.setPlaceholderText("colorbar label")
        self.cbar_edit.textChanged.connect(self.changed)
        cbar_row.addWidget(self.cbar_edit)
        layout.addLayout(cbar_row)

    @property
    def x_label(self) -> str:
        return self.x_edit.text()

    @property
    def y_label(self) -> str:
        return self.y_edit.text()

    @property
    def title(self) -> str:
        return self.title_edit.text()

    @property
    def cbar_label(self) -> str:
        return self.cbar_edit.text()
