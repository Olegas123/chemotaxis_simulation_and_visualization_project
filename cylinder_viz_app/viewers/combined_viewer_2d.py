"""
combined_viewer_2d.py

3-D combined viewer - renders polar (top/bottom disk) and cylindrical
(side surface) data together on a single PyVista plotter.
"""
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSplitter, QMessageBox)

from config import UI, DOMAIN, COLORS

try:
    from pyvistaqt import QtInteractor
except ImportError:
    print("ERROR: pyvistaqt not available. Install with: pip install pyvistaqt")
    sys.exit(1)

from core.data_loader import match_snapshots_by_time
from core.export import export_gif_3d
from core.mesh_builder import (build_combined_meshes)
from viewers.visualization import CylinderVisualizer
from panels.display_panels import (TransparencyPanel,
                                   ColormapPanel,
                                   DisplayOptionsPanel,
                                   CameraPanel,
                                   TitlePanel,
                                   AxisLabelPanel)
from panels.file_panels import FileLoadPanel, SnapshotNavigationPanel, InfoPanel


class CylinderVisualizerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Data storage
        self.polar_params = None
        self.polar_snapshots = []

        self.cyl_params = None
        self.cyl_snapshots = []

        self.matches = []

        # Visualizer
        self.visualizer = None

        # Camera state
        self.saved_camera_position = None
        self.first_visualization = True

        # Initialize UI
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Cylinder Visualizer - Combined View")
        self.setGeometry(*UI.COMBINED_VIEWER)

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Create control panel
        control_panel = self.create_control_panel()

        # Create 3D view
        self.plotter = QtInteractor(self)
        self.plotter.set_background(COLORS.BACKGROUND)
        self.visualizer = CylinderVisualizer(self.plotter)

        # Add to splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(self.plotter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes(UI.SPLIT_COMBINED)

        main_layout.addWidget(splitter)

        self.show()

    def create_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignTop)

        # File loading
        self.file_panel = FileLoadPanel()
        self.file_panel.polar_loaded.connect(self.on_polar_loaded)
        self.file_panel.cyl_loaded.connect(self.on_cyl_loaded)
        layout.addWidget(self.file_panel)

        # Snapshot navigation
        self.snapshot_panel = SnapshotNavigationPanel()
        self.snapshot_panel.snapshot_changed.connect(self.on_snapshot_changed)
        layout.addWidget(self.snapshot_panel)

        # Transparency
        self.transparency_panel = TransparencyPanel()
        self.transparency_panel.transparency_changed.connect(self.on_transparency_changed)
        layout.addWidget(self.transparency_panel)

        # Colormaps
        self.colormap_panel = ColormapPanel()
        self.colormap_panel.settings_changed.connect(self.update_visualization)
        layout.addWidget(self.colormap_panel)

        # Display options
        self.display_panel = DisplayOptionsPanel()
        self.display_panel.visibility_changed.connect(self.on_visibility_changed)
        self.display_panel.edges_changed.connect(self.update_visualization)
        self.display_panel.bottom_disk_changed.connect(self.on_bottom_disk_changed)
        layout.addWidget(self.display_panel)

        # Title settings
        self.title_panel = TitlePanel()
        self.title_panel.title_settings_changed.connect(self.on_title_settings_changed)
        layout.addWidget(self.title_panel)

        # Camera
        self.camera_panel = CameraPanel()
        self.camera_panel.view_changed.connect(self.on_camera_view_changed)
        self.camera_panel.camera_lock_changed.connect(self.on_camera_lock_changed)
        layout.addWidget(self.camera_panel)

        # Action buttons
        action_layout = QVBoxLayout()

        self.update_btn = QPushButton("🔄 Update Visualization")
        self.update_btn.clicked.connect(self.update_visualization)
        self.update_btn.setEnabled(False)
        self.update_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
        action_layout.addWidget(self.update_btn)

        screenshot_btn = QPushButton("📷 Save Screenshot")
        screenshot_btn.clicked.connect(self.save_screenshot)
        action_layout.addWidget(screenshot_btn)

        self.gif_btn = QPushButton("🎬 Export GIF Animation")
        self.gif_btn.setEnabled(False)
        self.gif_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 8px; "
            "background-color: #4CAF50; color: white; }"
            "QPushButton:disabled { background-color: #aaa; }"
        )
        self.gif_btn.clicked.connect(self.export_gif)
        action_layout.addWidget(self.gif_btn)

        layout.addLayout(action_layout)

        # Axis / scalar bar labels
        self.axis_panel = AxisLabelPanel(default_x="X", default_y="Y")
        self.axis_panel.cbar_edit.setText("u")

        # Cbar label updates in-place; other field changes do full rebuild
        self.axis_panel.cbar_edit.textChanged.connect(self._update_cbar_label)
        layout.addWidget(self.axis_panel)

        # Info display
        self.info_panel = InfoPanel()
        layout.addWidget(self.info_panel)

        # Add stretch
        layout.addStretch()

        return panel

    def on_polar_loaded(self, path: str, params: dict, snapshots: list):
        self.polar_params = params
        self.polar_snapshots = snapshots
        self.check_ready_to_visualize()

    def on_cyl_loaded(self, path: str, params: dict, snapshots: list):
        self.cyl_params = params
        self.cyl_snapshots = snapshots
        self.check_ready_to_visualize()

    def check_ready_to_visualize(self):
        if self.polar_snapshots and self.cyl_snapshots:

            # Match snapshots
            self.matches = match_snapshots_by_time(
                self.polar_snapshots,
                self.cyl_snapshots
            )

            if self.matches:
                self.snapshot_panel.set_num_snapshots(len(self.matches))
                self.update_btn.setEnabled(True)
                self.gif_btn.setEnabled(True)

                self.info_panel.set_text(
                    f"Ready! Found {len(self.matches)} matching snapshots.\n"
                    f"Polar: {len(self.polar_snapshots)} snapshots\n"
                    f"Cylindrical: {len(self.cyl_snapshots)} snapshots"
                )

                # Auto-visualize first snapshot
                self.update_visualization()
            else:
                QMessageBox.warning(
                    self, "No Matches",
                    "No matching time points found between the two datasets!"
                )

    def on_snapshot_changed(self, index: int):
        self.update_visualization()

    def on_transparency_changed(self, disk_alpha: float, cyl_alpha: float):
        self.visualizer.update_transparency(disk_alpha, cyl_alpha)

    def on_visibility_changed(self, show_disks: bool, show_cylinder: bool):
        self.visualizer.update_visibility(show_disks, show_cylinder)

    def on_bottom_disk_changed(self, show_bottom: bool, use_gray: bool):
        self.visualizer.update_bottom_disk_settings(show_bottom, use_gray)

    def on_title_settings_changed(self, position: str, font_size: int):
        self.visualizer.set_title_position(position)
        self.visualizer.set_title_font_size(font_size)
        self.update_visualization()

    def on_camera_view_changed(self, view: str):
        self.visualizer.set_camera_position(view)

    def on_camera_lock_changed(self, locked: bool):
        if locked:
            # Lock the camera at current position
            success = self.visualizer.lock_camera()
            if success:
                print("✓ Camera locked at current position")
            else:
                print("✗ Failed to lock camera")
                self.camera_panel.set_lock_state(False)
        else:
            # Unlock the camera
            self.visualizer.unlock_camera()
            print("Camera unlocked")

    def update_visualization(self):
        if not self.matches:
            return

        # Save current camera position before clearing (if not first time)
        if not self.first_visualization:
            try:
                self.saved_camera_position = self.plotter.camera_position
            except:
                pass

        # Get current snapshot
        idx = self.snapshot_panel.get_current_index()
        i_polar, i_cyl = self.matches[idx]

        polar_data = self.polar_snapshots[i_polar]['u']
        cyl_data = self.cyl_snapshots[i_cyl]['u']
        t = self.polar_snapshots[i_polar]['t']

        self.snapshot_panel.set_time(t)

        # Get settings
        cmap_settings = self.colormap_panel.get_settings()
        display_settings = self.display_panel.get_settings()

        # Get intensity boost and threshold
        intensity_boost = cmap_settings['intensity_boost']
        boost_threshold = cmap_settings['boost_threshold']

        import numpy as np

        # TODO: Fix that hotfix - cylinder data was in not correct dimensions
        cyl_data = cyl_data.T

        cyl_data_boosted = cyl_data.copy()

        if intensity_boost > 0:
            mask = cyl_data > boost_threshold
            cyl_data_boosted[mask] = cyl_data[mask] + intensity_boost

        # Update visualizer config
        self.visualizer.config.disk_colormap = cmap_settings['disk_colormap']
        self.visualizer.config.cylinder_colormap = cmap_settings['cylinder_colormap']
        self.visualizer.config.use_same_colormap = cmap_settings['use_same_colormap']
        self.visualizer.config.use_separate_scaling = cmap_settings['use_separate_scaling']
        self.visualizer.config.show_edges = display_settings['show_edges']

        # Get geometry
        r = self.polar_params.get("R", self.cyl_params.get("r", DOMAIN.DEFAULT_RADIUS))
        H = self.cyl_params.get("H", DOMAIN.DEFAULT_HEIGHT)
        self.visualizer.radius = r
        self.visualizer.height = H

        if intensity_boost > 0 or not cmap_settings['use_separate_scaling']:
            # Use unified color scale so boost has visible effect
            global_min = min(np.nanmin(polar_data), np.nanmin(cyl_data_boosted))
            global_max = max(np.nanmax(polar_data), np.nanmax(cyl_data_boosted))
            polar_clim = (global_min, global_max)
            cyl_clim = (global_min, global_max)
        else:
            # Separate scaling only when no boost
            polar_min, polar_max = np.nanmin(polar_data), np.nanmax(polar_data)
            cyl_min_boosted, cyl_max_boosted = np.nanmin(cyl_data_boosted), np.nanmax(cyl_data_boosted)

            polar_clim = (polar_min, polar_max)
            cyl_clim = (cyl_min_boosted, cyl_max_boosted)

        # Create meshes (use boosted cylindrical data)
        meshes = build_combined_meshes(
            polar_data, cyl_data_boosted,
            self.polar_params, self.cyl_params
        )

        # Clear and rebuild visualization
        self.visualizer.clear()

        # Get bottom disk settings
        show_bottom, use_gray = self.display_panel.get_bottom_disk_settings()

        # Add meshes
        self.visualizer.add_disk_meshes(
            meshes['top'], meshes['bottom'],
            polar_clim, cmap_settings['disk_colormap'],
            show_bottom=show_bottom,
            bottom_gray=use_gray
        )

        self.visualizer.add_cylinder_mesh(
            meshes['cylinder'],
            cyl_clim, cmap_settings['cylinder_colormap'],
            scalar_bar_label=self.axis_panel.cbar_label
        )

        # Setup scene
        title_text = f"T = {t:.6f}"
        if intensity_boost > 0:
            title_text += f" [Boost: +{intensity_boost:.2f}"
            if boost_threshold > 0:
                title_text += f" (above {boost_threshold:.2f})"
            title_text += ", Unified scale]"
        elif cmap_settings['use_separate_scaling']:
            title_text += " "

        self.visualizer.setup_scene(title_text)

        # Update window title
        self.setWindowTitle(f"Cylinder Visualizer - {title_text}")

        # Apply current transparency
        disk_alpha, cyl_alpha = self.transparency_panel.get_transparency()
        self.visualizer.update_transparency(disk_alpha, cyl_alpha)

        # Apply visibility
        self.visualizer.update_visibility(
            display_settings['show_disks'],
            display_settings['show_cylinder']
        )

        # Restore camera position or reset on first visualization
        if self.first_visualization:
            self.visualizer.reset_camera()
            self.first_visualization = False
        elif self.saved_camera_position is not None:
            try:
                self.plotter.camera_position = self.saved_camera_position
            except:
                pass

        # Update info
        polar_min, polar_max = np.nanmin(polar_data), np.nanmax(polar_data)
        cyl_min, cyl_max = np.nanmin(cyl_data), np.nanmax(cyl_data)
        cyl_min_boosted, cyl_max_boosted = np.nanmin(cyl_data_boosted), np.nanmax(cyl_data_boosted)

        # Count how many values were boosted
        if intensity_boost > 0:
            num_boosted = np.sum(cyl_data > boost_threshold)
            total_points = cyl_data.size
            percent_boosted = (num_boosted / total_points) * 100

        info_text = (
            f"Snapshot {idx + 1}/{len(self.matches)}\n"
            f"Time: {t:.6f}\n"
            f"Polar: [{polar_min:.3f}, {polar_max:.3f}]\n"
            f"Cylinder (original): [{cyl_min:.3f}, {cyl_max:.3f}]"
        )
        if intensity_boost > 0:
            info_text += f"\nCylinder (boosted): [{cyl_min_boosted:.3f}, {cyl_max_boosted:.3f}]"
            info_text += f"\nBoost: +{intensity_boost:.2f}"
            info_text += f"\nThreshold: {boost_threshold:.2f}"
            info_text += f"\nBoosted: {percent_boosted:.1f}% of points"

        self.info_panel.set_text(info_text)

        self.plotter.render()

        # Restore camera position if locked
        self.visualizer.restore_locked_camera()

    def export_gif(self):
        idx_backup = self.snapshot_panel.get_current_index()
        camera_backup = self.plotter.camera_position
        export_gif_3d(
            parent=self,
            snapshots=self.matches,
            default_filename="combined_animation.gif",
            render_frame=self._render_gif_frame,
            hide_2d_actors=self._hide_2d_actors,
            restore_2d_actors=self._restore_2d_actors,
        )

        # Restore original snapshot and camera
        self.snapshot_panel.set_index(idx_backup)
        self.update_visualization()
        self.plotter.camera_position = camera_backup

    def _render_gif_frame(self, idx: int) -> "np.ndarray":
        self.snapshot_panel.set_index(idx)
        self.update_visualization()
        self.plotter.render()
        return self.plotter.screenshot(return_img=True, transparent_background=False)

    def _hide_2d_actors(self):
        backup = []
        for actor in self.plotter.renderer.GetActors2D():
            try:
                backup.append((actor, actor.GetVisibility()))
                actor.SetVisibility(False)
            except Exception:
                pass
        return backup

    def _restore_2d_actors(self, backup):
        for actor, vis in backup:
            try:
                actor.SetVisibility(vis)
            except Exception:
                pass

    def _update_cbar_label(self):
        if self.visualizer is None:
            return
        try:
            label = self.axis_panel.cbar_label or 'u'
            for bar in self.plotter.scalar_bars.values():
                if bar is not None:
                    bar.SetTitle(label)
            self.plotter.render()
        except Exception:
            pass  # silently ignore if scalar bar not yet created

    def save_screenshot(self):
        from PyQt5.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "cylinder_view.png",
            "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
        )
        if filename:
            self.visualizer.save_screenshot(filename)
            QMessageBox.information(
                self, "Success", f"Screenshot saved to:\n{filename}"
            )


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = CylinderVisualizerApp()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
