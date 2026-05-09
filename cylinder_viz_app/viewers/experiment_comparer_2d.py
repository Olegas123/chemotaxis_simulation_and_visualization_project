"""
experiment_comparer_2d.py

Grid viewer for comparing multiple 2-D experiment snapshots side by side.
Supports polar (top disk) and cylindrical (side surface) data in any
combination.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QFileDialog,
                             QGroupBox, QMessageBox, QListWidget, QSpinBox,
                             QCheckBox, QSlider, QSplitter, QApplication,
                             QTabWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView)
from PyQt5.QtCore import Qt

from config import DOMAIN, COLORMAPS, FIGURE, UI, GIF, MULTI_SPATIOTEMPORAL
from core.data_loader import load_snapshots
from panels.file_panels import MultiFilePanel
from panels.display_panels import MultiDisplayPanel, AxisLabelPanel


class ExperimentComparer2D(QMainWindow):
    def __init__(self):
        super().__init__()

        # Each entry is: {'label': str, 'params': dict, 'snapshots': list,
        #                 'data_type': 'polar'|'cylindrical', 'snap_idx': int}
        self.datasets = []

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("2D Experiment Comparer")
        self.setGeometry(*UI.MULTI_VIEWER)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        control = self._build_control_panel()
        control.setMaximumWidth(UI.CONTROL_PANEL_MAX_WIDTH)
        main_layout.addWidget(control)

        plot_widget = self._build_plot_widget()
        main_layout.addWidget(plot_widget)

        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)

        self.show()

    def _build_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignTop)

        file_group = QGroupBox("Add Experiments")
        file_layout = QVBoxLayout(file_group)

        add_top_btn = QPushButton("➕ Add Top (polar) data")
        add_top_btn.clicked.connect(lambda: self._load_file('polar'))
        add_top_btn.setStyleSheet("padding: 6px;")
        file_layout.addWidget(add_top_btn)

        add_side_btn = QPushButton("➕ Add Side (cylindrical) data")
        add_side_btn.clicked.connect(lambda: self._load_file('cylindrical'))
        add_side_btn.setStyleSheet("padding: 6px;")
        file_layout.addWidget(add_side_btn)

        remove_btn = QPushButton("➖ Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        file_layout.addWidget(remove_btn)

        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(self._clear_all)
        file_layout.addWidget(clear_btn)

        file_layout.addWidget(QLabel("Loaded experiments:"))
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(UI.FILE_LIST_MAX_HEIGHT)
        file_layout.addWidget(self.file_list)
        layout.addWidget(file_group)

        grid_group = QGroupBox("Grid Layout")
        grid_layout = QVBoxLayout(grid_group)

        cols_row = QHBoxLayout()
        cols_row.addWidget(QLabel("Columns:"))
        self.cols_spin = QSpinBox()
        self.cols_spin.setMinimum(MULTI_SPATIOTEMPORAL.GRID_MIN)
        self.cols_spin.setMaximum(MULTI_SPATIOTEMPORAL.GRID_MAX)
        self.cols_spin.setValue(3)
        self.cols_spin.valueChanged.connect(self.update_plot)
        cols_row.addWidget(self.cols_spin)
        grid_layout.addLayout(cols_row)

        preset_row = QHBoxLayout()
        for label, c in [("1", 1), ("2", 2), ("3", 3), ("4", 4)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, cv=c: self.cols_spin.setValue(cv))
            preset_row.addWidget(btn)
        grid_layout.addLayout(preset_row)
        layout.addWidget(grid_group)

        snap_group = QGroupBox("Snapshot")
        snap_layout = QVBoxLayout(snap_group)

        snap_layout.addWidget(QLabel("Index (applied to all):"))
        snap_row = QHBoxLayout()
        self.snap_spin = QSpinBox()
        self.snap_spin.setMinimum(0)
        self.snap_spin.setMaximum(0)
        self.snap_spin.valueChanged.connect(self._on_snap_changed)
        snap_row.addWidget(self.snap_spin)
        self.snap_label = QLabel("t = --")
        snap_row.addWidget(self.snap_label)
        snap_layout.addLayout(snap_row)

        nav_row = QHBoxLayout()
        prev_btn = QPushButton("◀")
        prev_btn.clicked.connect(
            lambda: self.snap_spin.setValue(max(0, self.snap_spin.value() - 1)))
        next_btn = QPushButton("▶")
        next_btn.clicked.connect(
            lambda: self.snap_spin.setValue(
                min(self.snap_spin.maximum(), self.snap_spin.value() + 1)))
        nav_row.addWidget(prev_btn)
        nav_row.addWidget(next_btn)
        snap_layout.addLayout(nav_row)
        layout.addWidget(snap_group)

        disp_group = QGroupBox("Display Settings")
        disp_layout = QVBoxLayout(disp_group)

        cmap_row = QHBoxLayout()
        cmap_row.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(COLORMAPS.STANDARD)
        self.cmap_combo.currentTextChanged.connect(self.update_plot)
        cmap_row.addWidget(self.cmap_combo)
        disp_layout.addLayout(cmap_row)

        self.same_scale_check = QCheckBox("Same colour scale for all panels")
        self.same_scale_check.stateChanged.connect(self.update_plot)
        disp_layout.addWidget(self.same_scale_check)

        self.show_colorbar_check = QCheckBox("Show colorbars")
        self.show_colorbar_check.setChecked(True)
        self.show_colorbar_check.stateChanged.connect(self.update_plot)
        disp_layout.addWidget(self.show_colorbar_check)

        self.show_labels_check = QCheckBox("Show panel labels (a, b, c, ...)")
        self.show_labels_check.setChecked(True)
        self.show_labels_check.stateChanged.connect(self.update_plot)
        disp_layout.addWidget(self.show_labels_check)

        layout.addWidget(disp_group)

        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)

        update_btn = QPushButton("🔄 Update Plot")
        update_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        update_btn.clicked.connect(self.update_plot)
        action_layout.addWidget(update_btn)

        save_btn = QPushButton("💾 Save Figure")
        save_btn.clicked.connect(self._save_figure)
        action_layout.addWidget(save_btn)
        layout.addWidget(action_group)

        self.axis_panel = AxisLabelPanel(default_x="x", default_y="z / t")
        self.axis_panel.cbar_edit.setText("u")
        self.axis_panel.changed.connect(self.update_plot)
        layout.addWidget(self.axis_panel)

        self.info_label = QLabel(
            "Add experiments using the buttons above.\n\n"
            "Top (polar) data: 2-D arrays in polar coordinates\n"
            "Side (cylindrical) data: 2-D arrays in cylindrical\n"
            "coordinates (angular × vertical).\n\n"
            "Use the snapshot slider to step through time.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 10px; background: #f0f8ff;")
        layout.addWidget(self.info_label)

        layout.addStretch()
        return panel

    def _build_plot_widget(self) -> QWidget:
        splitter = QSplitter(Qt.Vertical)

        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=FIGURE.MULTI_PANEL)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        canvas_layout.addWidget(self.toolbar)
        canvas_layout.addWidget(self.canvas)
        splitter.addWidget(canvas_widget)

        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setContentsMargins(4, 4, 4, 4)

        params_header = QHBoxLayout()
        params_header.addWidget(QLabel("<b>Model Parameters</b>"))
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self._refresh_params_table)
        params_header.addWidget(refresh_btn, alignment=Qt.AlignRight)
        params_layout.addLayout(params_header)

        self.params_table = QTableWidget()
        self.params_table.setAlternatingRowColors(True)
        self.params_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.params_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.params_table.verticalHeader().setDefaultSectionSize(22)
        self.params_table.setStyleSheet("font-family: monospace; font-size: 11px;")
        params_layout.addWidget(self.params_table)
        splitter.addWidget(params_widget)

        # Canvas gets ~65% of height, params table ~35%
        splitter.setSizes([650, 350])

        self.file_list.currentRowChanged.connect(lambda _: self._refresh_params_table())

        return splitter

    def _load_file(self, data_type: str):
        label = "Top (polar)" if data_type == 'polar' else "Side (cylindrical)"
        filename, _ = QFileDialog.getOpenFileName(
            self, f"Load {label} Data", "",
            "Data Files (*.dat);;All Files (*)"
        )
        if not filename:
            return
        try:
            params, snapshots = load_snapshots(filename)
            if not snapshots:
                QMessageBox.warning(self, "No Data", "No snapshots found in file.")
                return

            # Filter to expected type
            loaded_type = snapshots[0].get('type', data_type)
            entry = {
                'label': os.path.splitext(os.path.basename(filename))[0],
                'params': params,
                'snapshots': snapshots,
                'data_type': loaded_type,
                'snap_idx': 0,
            }
            self.datasets.append(entry)

            self.file_list.addItem(f"[{loaded_type[:3].upper()}] {entry['label']}")

            max_snaps = max(len(d['snapshots']) for d in self.datasets)
            self.snap_spin.setMaximum(max_snaps - 1)

            self.update_plot()
            self._refresh_params_table()
            self.info_label.setText(
                f"✓ {len(self.datasets)} experiment(s) loaded.\n"
                f"Last: {entry['label']} ({loaded_type}, "
                f"{len(snapshots)} snapshots)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load:\n{str(e)}")

    def _remove_selected(self):
        row = self.file_list.currentRow()
        if row < 0 or row >= len(self.datasets):
            return
        self.datasets.pop(row)
        self.file_list.takeItem(row)
        if self.datasets:
            max_snaps = max(len(d['snapshots']) for d in self.datasets)
            self.snap_spin.setMaximum(max_snaps - 1)
        else:
            self.snap_spin.setMaximum(0)
        self.update_plot()
        self._refresh_params_table()

    def _clear_all(self):
        self.datasets.clear()
        self.file_list.clear()
        self.snap_spin.setMaximum(0)
        self.figure.clear()
        self.canvas.draw()
        self._refresh_params_table()
        self.info_label.setText("All experiments cleared.")

    def _on_snap_changed(self, value: int):
        self.snap_label.setText(f"idx {value}")
        self.update_plot()

    def update_plot(self):
        self.figure.clear()

        if not self.datasets:
            self.canvas.draw()
            return

        rows = 1
        cols = self.cols_spin.value()
        cmap = self.cmap_combo.currentText()
        same_scale = self.same_scale_check.isChecked()
        show_cbar = self.show_colorbar_check.isChecked()
        show_labels = self.show_labels_check.isChecked()
        global_idx = self.snap_spin.value()
        panel_labels = ['a)', 'b)', 'c)', 'd)', 'e)', 'f)', 'g)', 'h)', 'i)', 'j)',
                        'k)', 'l)', 'm)', 'n)', 'o)', 'p)']

        n_panels = min(len(self.datasets), rows * cols)

        vmin = vmax = None
        if same_scale:
            all_vals = []
            for entry in self.datasets[:n_panels]:
                idx = min(global_idx, len(entry['snapshots']) - 1)
                all_vals.append(entry['snapshots'][idx]['u'].ravel())
            if all_vals:
                combined = np.concatenate(all_vals)
                vmin, vmax = float(np.nanmin(combined)), float(np.nanmax(combined))

        for panel_i, entry in enumerate(self.datasets[:n_panels]):
            ax = self.figure.add_subplot(rows, cols, panel_i + 1,
                                         projection='polar' if entry['data_type'] == 'polar' else None)

            idx = min(global_idx, len(entry['snapshots']) - 1)
            snap = entry['snapshots'][idx]
            u = snap['u']
            t = snap['t']
            params = entry['params']

            lim_kw = dict(vmin=vmin, vmax=vmax) if same_scale else {}

            if entry['data_type'] == 'polar':
                self._plot_polar(ax, u, params, cmap, lim_kw)
            else:
                self._plot_cylindrical(ax, u, params, cmap, lim_kw)

            title = f"{entry['label']}\nt = {t:.4f}"
            if show_labels and panel_i < len(panel_labels):
                title = f"{panel_labels[panel_i]}  {title}"
            ax.set_title(title, fontsize=8, pad=6)

            if show_cbar:
                _mappable = (ax.get_images() or ax.collections or [None])[0]
                if _mappable is not None:
                    cb = self.figure.colorbar(_mappable, ax=ax,
                                              pad=0.05, fraction=0.046)
                    cb.set_label(self.axis_panel.cbar_label)

        self.figure.tight_layout()
        self.canvas.draw()

        if self.datasets:
            idx = min(global_idx, len(self.datasets[0]['snapshots']) - 1)
            t = self.datasets[0]['snapshots'][idx]['t']
            self.snap_label.setText(f"t = {t:.4f}")

    def _plot_polar(self, ax, u: np.ndarray, params: dict, cmap: str, lim_kw: dict):
        NR, NPhi = u.shape
        R = params.get('R', DOMAIN.DEFAULT_RADIUS)
        r = np.linspace(0, R, NR)
        phi = np.linspace(0, 2 * np.pi, NPhi)
        R_grid, Phi_grid = np.meshgrid(r, phi)
        ax.pcolormesh(Phi_grid, R_grid, u.T, cmap=cmap, shading='auto', **lim_kw)
        # Hide tick labels but keep grid clean; show axis labels if set
        if not self.axis_panel.x_label and not self.axis_panel.y_label:
            ax.set_yticklabels([])
            ax.set_xticklabels([])
        ax.grid(False)

    def _plot_cylindrical(self, ax, u: np.ndarray, params: dict, cmap: str, lim_kw: dict):
        H = params.get('H', DOMAIN.DEFAULT_HEIGHT)
        L = params.get('L', DOMAIN.DEFAULT_L_CYL)
        u_rot = np.rot90(u.T, k=-1)
        ax.imshow(u_rot, aspect='auto', origin='lower',
                  extent=[0, L, 0, H], cmap=cmap, **lim_kw)
        ax.set_xlabel(self.axis_panel.x_label)
        ax.set_ylabel(self.axis_panel.y_label)
        if not self.axis_panel.x_label and not self.axis_panel.y_label:
            ax.axis('off')

    # ── Export ────────────────────────────────────────────────────────────────

    def _refresh_params_table(self):
        self.params_table.clear()
        if not self.datasets:
            self.params_table.setRowCount(0)
            self.params_table.setColumnCount(0)
            return

        priority_keys = [
            "R", "H", "L",
            "N_RHO", "N_PHI", "NZ", "D_RHO", "D_PHI", "DZ",
            "D_U", "CHI", "ALPHA", "BETA", "D_W", "GAMMA", "W_0",
            "T", "dt", "N_steps", "SAVE_EVERY_T",
        ]
        all_keys = list(priority_keys)
        for entry in self.datasets:
            for k in entry['params']:
                if k not in all_keys and k not in ('file_type', 'NR', 'NPhi'):
                    all_keys.append(k)

        present_keys = [k for k in all_keys
                        if any(k in e['params'] for e in self.datasets)]

        n_rows = len(present_keys)
        n_cols = len(self.datasets)

        self.params_table.setRowCount(n_rows)
        self.params_table.setColumnCount(n_cols)

        headers = []
        for entry in self.datasets:
            badge = "TOP" if entry['data_type'] == 'polar' else "SIDE"
            name = entry['label']
            # Truncate long names
            if len(name) > 20:
                name = name[:18] + "…"
            headers.append(f"[{badge}] {name}")
        self.params_table.setHorizontalHeaderLabels(headers)
        self.params_table.setVerticalHeaderLabels(present_keys)

        for row, key in enumerate(present_keys):
            values = [entry['params'].get(key) for entry in self.datasets]

            present_vals = [v for v in values if v is not None]
            all_same = len(set(
                round(v, 6) if isinstance(v, float) else v
                for v in present_vals
            )) <= 1 if present_vals else True

            for col, val in enumerate(values):
                if val is None:
                    text = "-"
                elif isinstance(val, float):
                    text = f"{int(val)}" if val == int(val) else f"{val:.6g}"
                else:
                    text = str(val)

                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)

                if val is None:
                    item.setForeground(
                        self.params_table.palette().color(
                            self.params_table.palette().Disabled,
                            self.params_table.palette().Text))
                elif not all_same:
                    from PyQt5.QtGui import QColor
                    item.setBackground(QColor(255, 255, 180))

                self.params_table.setItem(row, col, item)

    def _save_figure(self):
        if not self.datasets:
            QMessageBox.warning(self, "No Data", "No data to save.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", "experiment_comparison.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;All Files (*)"
        )
        if filename:
            self.figure.savefig(filename, dpi=GIF.EXPORT_DPI, bbox_inches='tight')
            QMessageBox.information(self, "Saved", f"Figure saved:\n{filename}")


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    viewer = ExperimentComparer2D()
    sys.exit(app.exec_())
