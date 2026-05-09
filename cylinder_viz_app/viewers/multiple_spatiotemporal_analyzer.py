"""
multiple_spatiotemporal_analyzer.py

Multi-panel spatiotemporal viewer - displays multiple x/t (spatiotemporal) diagrams in a
configurable grid layout.
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QFileDialog,
                             QGroupBox, QMessageBox, QListWidget, QSpinBox,
                             QCheckBox, QLineEdit, QTabWidget, QScrollArea)
from PyQt5.QtCore import Qt
from config import COLORMAPS, FIGURE, UI, GIF, MULTI_SPATIOTEMPORAL, SCALAR_BAR
from panels.file_panels import MultiFilePanel
from panels.display_panels import MultiDisplayPanel, AxisLabelPanel


class MultiSpatiotemporalViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.datasets = []  # Each entry: {'filename': str, 'data': np.array, 'T': float, 'L': float, 'params': dict}

        # Display settings
        self.grid_rows = 2
        self.grid_cols = 2
        self._ax_to_dataset = {}
        self.current_colormap = COLORMAPS.DEFAULT
        self.use_same_colorscale = False
        self.show_colorbar = True
        self.show_labels = True
        self.panel_labels = ['a)', 'b)', 'c)', 'd)', 'e)', 'f)', 'g)', 'h)', 'i)']

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Multi-Panel Spatiotemporal Viewer")
        self.setGeometry(*UI.MULTI_VIEWER)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Control panel
        control_panel = self.create_control_panel()
        control_panel.setMaximumWidth(UI.CONTROL_PANEL_MAX_WIDTH)
        main_layout.addWidget(control_panel)

        # Plot area
        plot_widget = self.create_plot_widget()
        main_layout.addWidget(plot_widget)

        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)

        self.show()

    def create_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignTop)

        self.file_panel = MultiFilePanel()
        self.file_panel.add_file_requested.connect(self.add_data_file)
        self.file_panel.remove_file_requested.connect(self.remove_selected_file)
        self.file_panel.clear_files_requested.connect(self.clear_all_files)
        self.file_panel.grid_changed.connect(self.on_grid_changed)
        layout.addWidget(self.file_panel)

        self.display_panel = MultiDisplayPanel()
        self.display_panel.settings_changed.connect(self.update_plot)
        self.display_panel.update_requested.connect(self.update_plot)
        self.display_panel.save_requested.connect(self.save_figure)
        layout.addWidget(self.display_panel)

        self.axis_panel = AxisLabelPanel(default_x="x", default_y="t")
        self.axis_panel.cbar_edit.setText(SCALAR_BAR.TITLE)
        self.axis_panel.changed.connect(self.update_plot)
        layout.addWidget(self.axis_panel)

        layout.addStretch()
        return panel

    def create_plot_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.figure = Figure(figsize=FIGURE.MULTI_PANEL)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # Hover info status bar
        self.hover_label = QLabel("Hover over a panel for details")
        self.hover_label.setStyleSheet(
            "padding: 4px 8px; background: #f0f8ff; "
            "border-top: 1px solid #ccc; font-size: 10px; font-family: monospace;"
        )
        self.hover_label.setMinimumHeight(22)
        layout.addWidget(self.hover_label)

        # Connect mouse move event
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('axes_leave_event', self._on_axes_leave)

        return widget

    def add_data_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Spatiotemporal Data", "",
            "Data Files (*.dat *.txt);;All Files (*)"
        )

        if not filename:
            return

        try:
            data_lines = []
            header_info = {}

            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#'):
                        if '=' in line:
                            parts = line[1:].split('=')
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                try:
                                    value = value.split('#')[0].split('(')[0].strip()
                                    header_info[key] = float(value)
                                except ValueError:
                                    header_info[key] = value
                    elif line:
                        values = [float(x) for x in line.split()]
                        data_lines.append(values)

            data = np.array(data_lines)

            T = float(header_info.get('T', data.shape[0]))
            L = float(header_info.get('L', data.shape[1]))

            # Add to datasets
            basename = os.path.basename(filename)
            self.datasets.append({
                'filename': basename,
                'data': data,
                'T': T,
                'L': L,
                'params': header_info
            })

            # Update file list
            self.file_panel.file_list.addItem(f"{len(self.datasets)}. {basename}")

            # Update info
            self.update_info_label()

            # Update plot
            self.update_plot()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")

    def remove_selected_file(self):
        current_row = self.file_panel.file_list.currentRow()
        if current_row >= 0:
            self.datasets.pop(current_row)
            self.file_panel.file_list.takeItem(current_row)

            for i in range(self.file_panel.file_list.count()):
                item = self.file_panel.file_list.item(i)
                basename = self.datasets[i]['filename']
                item.setText(f"{i + 1}. {basename}")

            self.update_info_label()
            self.update_plot()

    def clear_all_files(self):
        if self.datasets:
            reply = QMessageBox.question(
                self, "Confirm", "Clear all loaded files?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.datasets.clear()
                self.file_panel.file_list.clear()
                self.update_info_label()
                self.update_plot()

    def on_grid_changed(self):
        self.grid_rows = self.file_panel.rows_spin.value()
        self.grid_cols = self.file_panel.cols_spin.value()
        self.update_plot()

    def set_grid_preset(self, rows: int, cols: int):
        self.file_panel.rows_spin.setValue(rows)
        self.file_panel.cols_spin.setValue(cols)

    def update_info_label(self):
        if not self.datasets:
            self.display_panel.info_label.setText("No data loaded.\n\n"
                                                  "Load spatiotemporal files to display them in a grid.")
            return

        info_text = f"Loaded {len(self.datasets)} dataset(s)\n\n"
        for i, ds in enumerate(self.datasets):
            nt, nx = ds['data'].shape
            info_text += f"{i + 1}. {ds['filename']}\n"
            info_text += f"   Size: {nt}×{nx} (t×x)\n"
            info_text += f"   Range: t∈[0,{ds['T']:.1f}], x∈[0,{ds['L']:.2f}]\n"

        self.display_panel.info_label.setText(info_text)

    def update_plot(self):
        if not self.datasets:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Load data files to display',
                    ha='center', va='center', fontsize=14, color='gray')
            ax.axis('off')
            self.canvas.draw()
            return

        self.figure.clear()
        self._ax_to_dataset = {}

        # Get settings
        rows = self.grid_rows
        cols = self.grid_cols
        cmap = self.display_panel.cmap_combo.currentText()
        aspect_text = self.display_panel.aspect_combo.currentText()
        use_same_scale = self.display_panel.same_scale_check.isChecked()
        show_colorbar = self.display_panel.show_colorbar_check.isChecked()
        show_labels = self.display_panel.show_labels_check.isChecked()

        # Parse aspect ratio
        aspect = MULTI_SPATIOTEMPORAL.ASPECT_RATIOS.get(aspect_text, 'auto')

        # Calculate global color limits if using same scale
        if use_same_scale and self.datasets:
            global_vmin = min(np.nanmin(ds['data']) for ds in self.datasets)
            global_vmax = max(np.nanmax(ds['data']) for ds in self.datasets)

        # Create subplots
        total_panels = rows * cols

        for idx in range(total_panels):
            ax = self.figure.add_subplot(rows, cols, idx + 1)

            if idx < len(self.datasets):
                self._ax_to_dataset[ax] = idx

                ds = self.datasets[idx]
                data = ds['data']
                T = ds['T']
                L = ds['L']

                # Set color limits
                if use_same_scale:
                    vmin, vmax = global_vmin, global_vmax
                else:
                    vmin, vmax = np.nanmin(data), np.nanmax(data)

                # Plot
                im = ax.imshow(
                    data,
                    aspect=aspect,
                    cmap=cmap,
                    origin='lower',
                    extent=[0, L, 0, T],
                    interpolation='bilinear',
                    vmin=vmin,
                    vmax=vmax
                )

                # Colorbar
                if show_colorbar:
                    cbar = self.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                    cbar.set_label(self.axis_panel.cbar_label,
                                   rotation=90, labelpad=10, fontsize=9)
                    cbar.ax.tick_params(labelsize=8)

                # Labels
                ax.set_xlabel(self.axis_panel.x_label, fontsize=10)
                ax.set_ylabel(self.axis_panel.y_label, fontsize=10)
                ax.tick_params(labelsize=8)

                # Custom or auto title
                custom_title = self.axis_panel.title
                if custom_title:
                    ax.set_title(custom_title, fontsize=9)
                # Panel label (a, b, c, ...)
                if show_labels and idx < len(self.panel_labels):
                    ax.text(0.05, 0.95, self.panel_labels[idx],
                            transform=ax.transAxes,
                            fontsize=12, fontweight='bold',
                            va='top', ha='left',
                            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            else:
                # Empty panel
                ax.text(0.5, 0.5, 'Empty', ha='center', va='center',
                        fontsize=10, color='lightgray')
                ax.set_xticks([])
                ax.set_yticks([])
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['bottom'].set_visible(False)
                ax.spines['left'].set_visible(False)

        self.figure.tight_layout()
        self.canvas.draw()

    def _on_mouse_move(self, event):
        if event.inaxes is None:
            return
        ax = event.inaxes
        idx = self._ax_to_dataset.get(ax)
        if idx is None or idx >= len(self.datasets):
            self.hover_label.setText("-")
            return

        ds = self.datasets[idx]
        params = ds.get('params', {})

        # Key model parameters to display
        param_keys = [
            ('D_U', 'Du'),
            ('CHI', 'χ'),
            ('ALPHA', 'α'),
            ('BETA', 'β'),
            ('D_W', 'Dw'),
            ('GAMMA', 'γ'),
            ('W_0', 'W₀'),
            ('T', 'T'),
            ('L', 'L'),
        ]

        parts = [f"📊 {ds['filename']}"]
        for key, label in param_keys:
            if key in params:
                val = params[key]
                text = f"{int(val)}" if isinstance(val, float) and val == int(val) else f"{val:.4g}"
                parts.append(f"{label} = {text}")

        self.hover_label.setText("   |   ".join(parts))

    def _on_axes_leave(self, event):
        self.hover_label.setText("Hover over a panel for details")

    def save_figure(self):
        if not self.datasets:
            QMessageBox.warning(self, "Error", "No data to save")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", "spatiotemporal_multi_panel.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;All Files (*)"
        )

        if filename:
            self.figure.savefig(filename, dpi=GIF.EXPORT_DPI, bbox_inches='tight')
            QMessageBox.information(self, "Success",
                                    f"Figure saved:\n{filename}\n\nDPI: {GIF.EXPORT_DPI}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    viewer = MultiSpatiotemporalViewer()

    sys.exit(app.exec_())
