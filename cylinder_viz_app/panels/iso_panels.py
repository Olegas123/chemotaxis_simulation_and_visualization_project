"""
iso_panels.py

Isosurface layer management panel.
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

from config import ISOSURFACE


class IsoLayerPanel(QWidget):
    layers_changed = pyqtSignal()
    opacity_fast = pyqtSignal(int)
    layer_removed = pyqtSignal(int)
    all_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layers = []  # list of layer config dicts
        self._build_ui()

    @property
    def layers(self):
        return self._layers

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(6)

        # Add-layer form
        add_group = QGroupBox("Add Iso-Layer")
        add_layout = QVBoxLayout(add_group)
        add_layout.setSpacing(4)

        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("Min:"))
        self._new_min = QDoubleSpinBox()
        self._new_min.setRange(ISOSURFACE.VALUE_RANGE_MIN, ISOSURFACE.VALUE_RANGE_MAX)
        self._new_min.setValue(ISOSURFACE.DEFAULT_MIN)
        self._new_min.setSingleStep(ISOSURFACE.VALUE_STEP)
        self._new_min.setDecimals(ISOSURFACE.VALUE_DECIMALS)
        self._new_min.setFixedWidth(70)
        range_row.addWidget(self._new_min)
        range_row.addWidget(QLabel("Max:"))
        self._new_max = QDoubleSpinBox()
        self._new_max.setRange(ISOSURFACE.VALUE_RANGE_MIN, ISOSURFACE.VALUE_RANGE_MAX)
        self._new_max.setValue(ISOSURFACE.DEFAULT_MAX)
        self._new_max.setSingleStep(ISOSURFACE.VALUE_STEP)
        self._new_max.setDecimals(ISOSURFACE.VALUE_DECIMALS)
        self._new_max.setFixedWidth(70)
        range_row.addWidget(self._new_max)
        add_layout.addLayout(range_row)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color:"))
        self._new_color = QColor(ISOSURFACE.DEFAULT_COLOR_R,
                                 ISOSURFACE.DEFAULT_COLOR_G,
                                 ISOSURFACE.DEFAULT_COLOR_B)
        self._new_color_btn = QPushButton()
        self._new_color_btn.setFixedSize(48, 22)
        self._update_color_btn(self._new_color_btn, self._new_color)
        self._new_color_btn.clicked.connect(self._pick_new_color)
        color_row.addWidget(self._new_color_btn)
        color_row.addStretch()
        add_layout.addLayout(color_row)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity:"))
        self._new_opacity = QSlider(Qt.Horizontal)
        self._new_opacity.setRange(ISOSURFACE.OPACITY_MIN, ISOSURFACE.OPACITY_MAX)
        self._new_opacity.setValue(ISOSURFACE.DEFAULT_OPACITY)
        opacity_row.addWidget(self._new_opacity)
        self._new_opacity_lbl = QLabel(f"{ISOSURFACE.DEFAULT_OPACITY}%")
        self._new_opacity.valueChanged.connect(lambda v: self._new_opacity_lbl.setText(f"{v}%"))
        opacity_row.addWidget(self._new_opacity_lbl)
        add_layout.addLayout(opacity_row)

        add_btn = QPushButton("＋  Add Layer")
        add_btn.setStyleSheet("font-weight:bold; padding:4px; background:#4CAF50; color:white;")
        add_btn.clicked.connect(self._add_layer)
        add_layout.addWidget(add_btn)
        outer.addWidget(add_group)

        # Layer list
        list_group = QGroupBox("Active Layers")
        list_outer = QVBoxLayout(list_group)
        list_outer.setContentsMargins(2, 4, 2, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(120)
        scroll.setMaximumHeight(300)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(2)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        list_outer.addWidget(scroll)

        clear_btn = QPushButton("✕  Remove All Layers")
        clear_btn.setStyleSheet("color:#c00; padding:3px;")
        clear_btn.clicked.connect(self._clear_all)
        list_outer.addWidget(clear_btn)
        outer.addWidget(list_group)
        outer.addStretch()

    def _update_color_btn(self, btn, color: QColor):
        r, g, b = color.red(), color.green(), color.blue()
        lum = (ISOSURFACE.LUMINANCE_R_WEIGHT * r
               + ISOSURFACE.LUMINANCE_G_WEIGHT * g
               + ISOSURFACE.LUMINANCE_B_WEIGHT * b)
        text = "#000" if lum > ISOSURFACE.LUMINANCE_THRESHOLD else "#fff"
        btn.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); color:{text}; "
            f"border:1px solid #888; border-radius:3px;")
        btn.setText(f"#{r:02X}{g:02X}{b:02X}")

    def _pick_new_color(self):
        col = QColorDialog.getColor(self._new_color, self, "Pick Layer Color")
        if col.isValid():
            self._new_color = col
            self._update_color_btn(self._new_color_btn, col)

    def _add_layer(self):
        val_min = self._new_min.value()
        val_max = self._new_max.value()
        if val_min >= val_max:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Range", "Min must be less than Max.")
            return
        layer = {
            'val_min': val_min,
            'val_max': val_max,
            'color': QColor(self._new_color),
            'opacity': self._new_opacity.value(),
            'visible': True,
        }
        self._layers.append(layer)
        self._build_row(len(self._layers) - 1)
        self.layers_changed.emit()

    def _build_row(self, idx):
        layer = self._layers[idx]

        row = QFrame()
        row.setFrameShape(QFrame.StyledPanel)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.setSpacing(4)

        vis_cb = QCheckBox()
        vis_cb.setChecked(layer['visible'])
        vis_cb.setToolTip("Toggle visibility")
        vis_cb.stateChanged.connect(lambda state, i=idx: self._toggle_visible(i, state))
        row_layout.addWidget(vis_cb)

        lbl = QLabel(f"{layer['val_min']:.3f} – {layer['val_max']:.3f}")
        lbl.setFixedWidth(100)
        lbl.setStyleSheet("font-size:10px;")
        row_layout.addWidget(lbl)

        color_btn = QPushButton()
        color_btn.setFixedSize(44, 20)
        self._update_color_btn(color_btn, layer['color'])
        color_btn.clicked.connect(lambda checked, i=idx, b=color_btn: self._change_color(i, b))
        row_layout.addWidget(color_btn)

        op_slider = QSlider(Qt.Horizontal)
        op_slider.setRange(ISOSURFACE.OPACITY_MIN, ISOSURFACE.OPACITY_MAX)
        op_slider.setValue(layer['opacity'])
        op_slider.setFixedWidth(60)
        op_lbl = QLabel(f"{layer['opacity']}%")
        op_lbl.setFixedWidth(30)
        op_lbl.setStyleSheet("font-size:10px;")
        op_slider.valueChanged.connect(lambda v, i=idx, l=op_lbl: self._change_opacity(i, v, l))
        row_layout.addWidget(op_slider)
        row_layout.addWidget(op_lbl)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet("color:#c00; font-weight:bold; padding:0;")
        del_btn.clicked.connect(lambda checked, i=idx: self._remove_layer(i))
        row_layout.addWidget(del_btn)

        count = self._list_layout.count()
        self._list_layout.insertWidget(count - 1, row)

    def _rebuild_list_ui(self):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i in range(len(self._layers)):
            self._build_row(i)

    def _toggle_visible(self, idx, state):
        if idx < len(self._layers):
            self._layers[idx]['visible'] = (state == Qt.Checked)
            self.layers_changed.emit()

    def _change_color(self, idx, btn):
        if idx >= len(self._layers):
            return
        col = QColorDialog.getColor(self._layers[idx]['color'], self, "Pick Layer Color")
        if col.isValid():
            self._layers[idx]['color'] = col
            self._update_color_btn(btn, col)
            self.layers_changed.emit()

    def _change_opacity(self, idx, value, lbl):
        if idx >= len(self._layers):
            return
        self._layers[idx]['opacity'] = value
        lbl.setText(f"{value}%")
        self.opacity_fast.emit(idx)

    def _remove_layer(self, idx):
        if idx >= len(self._layers):
            return
        self._layers.pop(idx)
        self.layer_removed.emit(idx)
        self._rebuild_list_ui()

    def _clear_all(self):
        self._layers.clear()
        self.all_cleared.emit()
        self._rebuild_list_ui()

    def reset_actors_list(self, count: int = None):
        pass  # Actor list is owned by viewer, panel just holds config
