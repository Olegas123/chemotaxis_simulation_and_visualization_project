"""
cylindrical_viewer_2d.py

2D cylindrical (side surface) snapshot viewer.
Shared control panel and GIF export loop come from gui_widgets and export modules.
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
                             QSpinBox, QGroupBox, QMessageBox, QSplitter,
                             QProgressDialog, QDialog,
                             QDialogButtonBox, QFormLayout, QCheckBox)
from PyQt5.QtCore import Qt
from config import DOMAIN, GIF, COLORMAPS, FIGURE, UI, SCALAR_BAR

from core.data_loader import load_snapshots
from panels.file_panels import SnapshotViewerPanel
from panels.display_panels import AxisLabelPanel
from core.export import export_gif_2d


class CylindricalViewer2D(QMainWindow):
    def __init__(self):
        super().__init__()

        self.params = None
        self.snapshots = []
        self.current_idx = 0

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("2D Cylindrical Viewer (Side View + Spatiotemporal)")
        self.setGeometry(*UI.CYL_VIEWER)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Control panel
        control_panel = self.create_control_panel()

        snapshot_widget = self.create_snapshot_tab()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(snapshot_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes(UI.SPLIT_CYL)

        main_layout.addWidget(splitter)

        self.show()

    def create_snapshot_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Matplotlib figure for snapshots
        self.figure_snapshot = Figure(figsize=FIGURE.CYL_SNAPSHOT)
        self.canvas_snapshot = FigureCanvas(self.figure_snapshot)
        self.toolbar_snapshot = NavigationToolbar(self.canvas_snapshot, self)

        layout.addWidget(self.toolbar_snapshot)
        layout.addWidget(self.canvas_snapshot)

        return tab

    def create_control_panel(self) -> QWidget:
        from PyQt5.QtWidgets import QVBoxLayout
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.ctrl = SnapshotViewerPanel(browse_label="Browse for Cylindrical Data...")
        self.ctrl.load_requested.connect(self.load_data)
        self.ctrl.snapshot_changed.connect(self.on_snapshot_changed)
        self.ctrl.prev_requested.connect(self.prev_snapshot)
        self.ctrl.next_requested.connect(self.next_snapshot)
        self.ctrl.colormap_changed.connect(self.update_snapshot_plot)
        self.ctrl.gif_requested.connect(self.export_gif)
        layout.addWidget(self.ctrl)

        self.axis_panel = AxisLabelPanel(default_x="x cylindrical length", default_y="z height")
        self.axis_panel.cbar_edit.setText(SCALAR_BAR.TITLE)
        self.axis_panel.changed.connect(self.update_snapshot_plot)
        layout.addWidget(self.axis_panel)

        return wrapper

    # TODO: Custom data loader -> move to data_loader.py
    def load_data(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Cylindrical Data", "", "Data Files (*.dat);;All Files (*)"
        )

        if not filename:
            return

        try:
            # Load snapshots
            self.params, self.snapshots = load_snapshots(filename)

            if not self.snapshots:
                QMessageBox.warning(self, "Error", "No snapshots found in file")
                return

            self.current_idx = 0
            self.ctrl.snapshot_spin.setMaximum(len(self.snapshots) - 1)
            self.ctrl.snapshot_spin.setValue(0)

            # Update file label
            basename = os.path.basename(filename)
            self.ctrl.file_label.setText(f"Loaded: {basename}\n{len(self.snapshots)} snapshots")

            self.update_snapshot_plot()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")

    def update_snapshot_plot(self):
        if not self.snapshots:
            return

        snapshot = self.snapshots[self.current_idx]
        u_data = snapshot['u']
        t = snapshot['t']

        self.figure_snapshot.clear()
        ax = self.figure_snapshot.add_subplot(111)

        NX, NZ = u_data.shape
        H = self.params.get('H', DOMAIN.DEFAULT_HEIGHT)
        L = self.params.get('L', DOMAIN.DEFAULT_L_CYL)

        # Rotate so that it would be correctly shown
        u_rotated = np.rot90(u_data.T, k=-1)

        im = ax.imshow(u_rotated, aspect='auto', origin='lower',
                       extent=[0, L, 0, H], cmap=self.ctrl.cmap_combo.currentText())

        cbar = self.figure_snapshot.colorbar(im, ax=ax)
        cbar.set_label(self.axis_panel.cbar_label)

        ax.set_ylabel(self.axis_panel.y_label)
        ax.set_xlabel(self.axis_panel.x_label)
        ax.set_title(self.axis_panel.title or f't = {t:.4f}')

        self.ctrl.snapshot_label.setText(f"Snapshot: {self.current_idx + 1}/{len(self.snapshots)}, t={t:.4f}")

        self.canvas_snapshot.draw()

    def export_gif(self):
        export_gif_2d(
            parent=self,
            snapshots=self.snapshots,
            default_filename="cylindrical_animation.gif",
            render_frame=self._render_gif_frame,
            cmap=self.ctrl.cmap_combo.currentText(),
        )


    def _render_gif_frame(self, snapshot: dict, dpi: int,
                          cmap: str, preserve_labels: bool) -> "np.ndarray":
        import matplotlib.pyplot as plt
        H = self.params.get('H', DOMAIN.DEFAULT_HEIGHT)
        L = self.params.get('L', DOMAIN.DEFAULT_L_CYL)
        fig = plt.figure(figsize=FIGURE.CYL_SNAPSHOT, dpi=dpi)
        ax = fig.add_subplot(111)
        u_rot = np.rot90(snapshot['u'].T, k=-1)
        ax.imshow(u_rot, aspect='auto', origin='lower',
                  extent=[0, L, 0, H], cmap=cmap)
        if not preserve_labels:
            ax.axis('off')
        else:
            ax.set_ylabel(self.axis_panel.y_label)
            ax.set_xlabel(self.axis_panel.x_label)
            ax.set_title(self.axis_panel.title or f"t = {snapshot['t']:.4f}")
        fig.canvas.draw()
        img = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
        plt.close(fig)
        return img

    def on_snapshot_changed(self, value):
        self.current_idx = value
        self.update_snapshot_plot()

    def prev_snapshot(self):
        if self.current_idx > 0:
            self.ctrl.snapshot_spin.setValue(self.current_idx - 1)

    def next_snapshot(self):
        if self.current_idx < len(self.snapshots) - 1:
            self.ctrl.snapshot_spin.setValue(self.current_idx + 1)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    viewer = CylindricalViewer2D()
    sys.exit(app.exec_())
