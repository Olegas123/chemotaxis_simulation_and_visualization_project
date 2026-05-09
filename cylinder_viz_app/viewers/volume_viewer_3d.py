"""
volume_viewer_3d.py

3-D volume viewer for cylindrical simulation data.
Rendering backends: PyVista / VTK (volume + slices + isosurfaces).
UI: PyQt5 with panel widgets.
"""

# ============================================================================
DO_LOG = False  # Set to True to enable detailed console logging
# ============================================================================

import sys
import os
import numpy as np


def log(msg):
    if DO_LOG:
        print(msg)


from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QFileDialog,
                             QSpinBox, QGroupBox, QMessageBox, QSplitter,
                             QSlider, QCheckBox, QTabWidget, QDoubleSpinBox, QTextEdit,
                             QProgressDialog, QDialog, QDialogButtonBox, QFormLayout,
                             QColorDialog, QScrollArea, QFrame, QLineEdit)
from PyQt5.QtCore import Qt

os.environ['PYVISTA_OFF_SCREEN'] = 'false'
os.environ['VTK_USE_OSMESA'] = '0'
os.environ['QT_OPENGL'] = 'desktop'
os.environ['__GL_SYNC_TO_VBLANK'] = '0'

import warnings

warnings.filterwarnings('ignore')

import sys
import logging

logging.getLogger().setLevel(logging.ERROR)

try:
    from pyvistaqt import QtInteractor
    import pyvista as pv
    import vtk

    vtk.vtkObject.GlobalWarningDisplayOff()

    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False
    print("ERROR: pyvistaqt not available. Install with: pip install pyvistaqt")
    sys.exit(1)

from core.data_loader import load_snapshots, load_snapshots_3d, format_volume_info
from core.export import export_gif_3d
from panels.file_panels import VolumeFilePanel
from panels.iso_panels import IsoLayerPanel
from panels.slice_panels import (SliceControlPanel,
                                 VolumeControlPanel,
                                 VolumePositionPanel)
from core.mesh_builder import (build_cylindrical_slice_mesh, build_radial_slice_mesh,
                               build_horizontal_slice_mesh, build_isosurface_layer_mesh,
                               build_volume_mesh, build_cylinder_outline)
from config import DOMAIN, GIF, COLORMAPS, UI, VOLUME, SCALAR_BAR, ISOSURFACE, TITLE, CAMERA


class VolumeViewer3D(QMainWindow):
    def __init__(self):
        super().__init__()

        self.params = None
        self.snapshots = []
        self.current_idx = 0
        self.current_volume = None

        self.mesh_rho_slice = None
        self.mesh_phi_slice = None
        self.mesh_z_slice = None
        self.mesh_isosurface = None
        self.mesh_volume = None
        self.mesh_outline = None

        self._grid_rho = None
        self._grid_phi = None
        self._grid_z = None

        self._last_rho_idx = None
        self._last_phi_idx = None
        self._last_z_idx = None

        self.iso_layer_actors = []
        self._iso_keys = []

        self.title_actor = None

        self.time_text_position = [TITLE.DEFAULT_POSITION_X, TITLE.DEFAULT_POSITION_Y]
        self.dragging_time_text = False

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("3D Volume Viewer")
        self.setGeometry(*UI.VOLUME_VIEWER)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        control_panel = self.create_control_panel()

        self.plotter = QtInteractor(self)
        self.plotter.set_background(VOLUME.BACKGROUND_COLOR)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(self.plotter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes(UI.SPLIT_VOLUME)

        main_layout.addWidget(splitter)

        self.show()
        self.setup_mouse_interactions()

    def setup_mouse_interactions(self):
        self.plotter.iren.add_observer("LeftButtonPressEvent", self.on_mouse_press)
        self.plotter.iren.add_observer("MouseMoveEvent", self.on_mouse_move)
        self.plotter.iren.add_observer("LeftButtonReleaseEvent", self.on_mouse_release)

    def update_time_text_position(self):
        self.time_text_position[0] = self.pos_panel.time_x.value()
        self.time_text_position[1] = self.pos_panel.time_y.value()

        if self.title_actor is not None:
            self.title_actor.SetPosition(self.time_text_position[0], self.time_text_position[1])
            self.plotter.render()

    def on_mouse_press(self, obj, event):
        click_pos = self.plotter.iren.GetEventPosition()

        size = self.plotter.iren.GetRenderWindow().GetSize()
        norm_x = click_pos[0] / size[0]
        norm_y = click_pos[1] / size[1]

        if self.title_actor is not None:
            dist_x = abs(norm_x - self.time_text_position[0])
            dist_y = abs(norm_y - self.time_text_position[1])
            if dist_x < 0.1 and dist_y < 0.05:
                self.dragging_time_text = True

    def on_mouse_move(self, obj, event):
        if self.dragging_time_text:
            click_pos = self.plotter.iren.GetEventPosition()
            size = self.plotter.iren.GetRenderWindow().GetSize()

            self.time_text_position[0] = click_pos[0] / size[0]
            self.time_text_position[1] = click_pos[1] / size[1]

            self.pos_panel.time_x.blockSignals(True)
            self.pos_panel.time_y.blockSignals(True)
            self.pos_panel.time_x.setValue(self.time_text_position[0])
            self.pos_panel.time_y.setValue(self.time_text_position[1])
            self.pos_panel.time_x.blockSignals(False)
            self.pos_panel.time_y.blockSignals(False)

            if self.title_actor is not None:
                self.title_actor.SetPosition(self.time_text_position[0], self.time_text_position[1])
                self.plotter.render()

    def on_mouse_release(self, obj, event):
        self.dragging_time_text = False

    def create_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignTop)

        self.file_panel = VolumeFilePanel()
        self.file_panel.file_load_requested.connect(self.load_file)
        self.file_panel.snapshot_changed.connect(self.on_snapshot_changed)
        layout.addWidget(self.file_panel)

        tabs = QTabWidget()
        tabs.addTab(self.create_slicing_controls(), "Slices")
        tabs.addTab(self.create_isosurface_controls(), "Isosurface")
        tabs.addTab(self.create_volume_controls(), "Volume")
        layout.addWidget(tabs)

        cbar_group = QGroupBox('Scalar Bar Label')
        cbar_layout = QHBoxLayout(cbar_group)
        cbar_layout.addWidget(QLabel('Label:'))
        self._cbar_label_edit = QLineEdit('u')
        self._cbar_label_edit.setPlaceholderText('colorbar label')
        self._cbar_label_edit.textChanged.connect(self._update_scalar_bar_label)
        cbar_layout.addWidget(self._cbar_label_edit)
        layout.addWidget(cbar_group)

        self.pos_panel = VolumePositionPanel()
        self.pos_panel.time_position_changed.connect(self.update_time_text_position)
        self.pos_panel.scale_bar_changed.connect(self._update_scalar_bar_position)
        layout.addWidget(self.pos_panel)

        camera_group = QGroupBox("Camera")
        camera_layout = QHBoxLayout(camera_group)
        view_fns = {
            'iso': self._set_iso_camera,
            'xy': lambda: self.plotter.view_xy(),
            'xz': lambda: self.plotter.view_xz(),
            'yz': lambda: self.plotter.view_yz(),
        }
        for view, fn in view_fns.items():
            btn = QPushButton(view.upper())
            btn.clicked.connect(fn)
            camera_layout.addWidget(btn)
        layout.addWidget(camera_group)

        export_group = QGroupBox("Screenshot & Animation")
        export_layout = QVBoxLayout(export_group)
        screenshot_btn = QPushButton("📷 Save Screenshot")
        screenshot_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        screenshot_btn.clicked.connect(self.save_screenshot)
        export_layout.addWidget(screenshot_btn)
        gif_btn = QPushButton("🎬 Export GIF Animation")
        gif_btn.setStyleSheet("font-weight: bold; padding: 8px; background-color: #4CAF50; color: white;")
        gif_btn.clicked.connect(self.export_gif)
        export_layout.addWidget(gif_btn)
        layout.addWidget(export_group)

        layout.addStretch()
        return panel

    def create_slicing_controls(self) -> QWidget:
        self.slice_panel = SliceControlPanel()
        self.slice_panel.changed.connect(lambda: self.update_visualization(False))
        return self.slice_panel

    def create_isosurface_controls(self) -> QWidget:
        self.iso_panel = IsoLayerPanel()
        self.iso_panel.layers_changed.connect(lambda: self.update_visualization(False))
        self.iso_panel.opacity_fast.connect(self._on_iso_opacity_fast)
        self.iso_panel.layer_removed.connect(self._on_iso_layer_removed)
        self.iso_panel.all_cleared.connect(self._on_iso_all_cleared)
        return self.iso_panel

    def _on_iso_opacity_fast(self, idx: int):
        if idx < len(self.iso_layer_actors) and self.iso_layer_actors[idx] is not None:
            try:
                opacity = self.iso_panel.layers[idx]['opacity'] / 100.0
                self.iso_layer_actors[idx].GetProperty().SetOpacity(opacity)
                self.plotter.render()
                return
            except Exception:
                pass
        self.update_visualization(False)

    def _on_iso_layer_removed(self, idx: int):
        if idx < len(self.iso_layer_actors):
            actor = self.iso_layer_actors.pop(idx)
            if idx < len(self._iso_keys):
                self._iso_keys.pop(idx)
            if actor is not None:
                try:
                    self.plotter.remove_actor(actor)
                except Exception:
                    pass
        self.update_visualization(False)

    def _on_iso_all_cleared(self):
        for actor in self.iso_layer_actors:
            if actor is not None:
                try:
                    self.plotter.remove_actor(actor)
                except Exception:
                    pass
        self.iso_layer_actors.clear()
        self._iso_keys.clear()
        self.plotter.render()

    def create_volume_controls(self) -> QWidget:
        self.vol_panel = VolumeControlPanel()
        self.vol_panel.changed.connect(lambda: self.update_visualization(False))
        self.vol_panel.opacity_changed.connect(self._vol_update_opacity_fast)
        return self.vol_panel

    def load_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load 3D Volume Data", "", "Data Files (*.dat);;All Files (*)"
        )
        if filename:
            try:
                print(f"\n{'=' * 60}")
                print(f"Loading 3D file: {filename}")
                print(f"{'=' * 60}")

                params, snapshots = load_snapshots_3d(filename)

                print(f"\nLoading results:")
                print(f"  Parameters found: {list(params.keys())}")
                print(f"  Snapshots loaded: {len(snapshots)}")

                if snapshots:
                    self.params = params
                    self.snapshots = snapshots
                    self.file_panel.on_file_loaded(filename, len(snapshots))
                    self.current_idx = 0

                    # Show data info
                    first_snap = snapshots[0]
                    shape = first_snap['u'].shape
                    print(f"\nFirst snapshot:")
                    print(f"  Time: {first_snap['t']}")
                    print(f"  Data shape: {shape}")
                    print(f"  Data range: [{np.min(first_snap['u']):.3f}, {np.max(first_snap['u']):.3f}]")

                    self.update_visualization(full_rebuild=True)
                    self.slice_panel.update_ranges(
                        rho_max=self.params.get('R', DOMAIN.DEFAULT_RADIUS),
                        z_max=self.params.get('H', DOMAIN.DEFAULT_HEIGHT),
                    )

                    QMessageBox.information(
                        self, "Success",
                        f"Loaded {len(snapshots)} 3D snapshots!\n"
                        f"Grid: {shape[0]} × {shape[1]} × {shape[2]}\n"
                        f"(ρ × φ × z)"
                    )
                else:
                    QMessageBox.warning(
                        self, "No Data",
                        "No 3D data found in file!"
                    )
            except Exception as e:
                import traceback
                error_msg = traceback.format_exc()
                print(f"\nERROR loading file:")
                print(error_msg)
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to load:\n{str(e)}"
                )

    def on_snapshot_changed(self, value):
        self.current_idx = value
        self.update_visualization(full_rebuild=True)

    def update_info_display(self):
        text = format_volume_info(
            self.params or {},
            self.snapshots,
            self.current_idx,
        )
        self.file_panel.set_info_text(text)
        if self.snapshots:
            self.file_panel.set_time_label(self.snapshots[self.current_idx]['t'])

    def _update_slice(self, show_checkbox, mesh_attr: str, grid_attr: str,
                      build_grid_fn, build_args: tuple, add_fn, add_args: tuple,
                      pos_attr: str = None, pos_val=None):
        old_actor = getattr(self, mesh_attr)
        old_grid = getattr(self, grid_attr)

        if not show_checkbox.isChecked():
            if old_actor is not None:
                self.plotter.remove_actor(old_actor)
                setattr(self, mesh_attr, None)
                setattr(self, grid_attr, None)
                if pos_attr:
                    setattr(self, pos_attr, None)
            return

        last_pos = getattr(self, pos_attr) if pos_attr else None
        position_changed = (pos_val is None or last_pos != pos_val)

        new_grid = build_grid_fn(*build_args)

        if (not position_changed and old_actor is not None
                and old_grid is not None
                and old_grid.n_points == new_grid.n_points):
            old_grid.point_data["values"] = new_grid.point_data["values"]
            old_grid.Modified()
        else:
            if old_actor is not None:
                self.plotter.remove_actor(old_actor)
            actor = add_fn(new_grid, *add_args)
            setattr(self, mesh_attr, actor)
            setattr(self, grid_attr, new_grid)
            if pos_attr and pos_val is not None:
                setattr(self, pos_attr, pos_val)

    def _set_iso_camera(self):
        if not self.snapshots:
            self.plotter.view_isometric()
            return
        R = self.params.get('R', DOMAIN.DEFAULT_RADIUS)
        H = self.params.get('H', DOMAIN.DEFAULT_HEIGHT)
        self.plotter.camera_position = [
            (R * CAMERA.ISO_XY_MULT, R * CAMERA.ISO_XY_MULT, H * CAMERA.ISO_Z_MULT),
            (0, 0, H * CAMERA.FOCAL_Z_MULT),
            (0, 0, 1),
        ]
        self.plotter.render()

    def update_visualization(self, full_rebuild=False):
        if not self.snapshots:
            return

        data = self.snapshots[self.current_idx]['u']
        t = self.snapshots[self.current_idx]['t']

        NRho, NPhi, NZ = data.shape
        R = self.params.get("R", DOMAIN.DEFAULT_RADIUS)
        H = self.params.get("H", DOMAIN.DEFAULT_HEIGHT)

        if full_rebuild:
            print(f"Full rebuild at t={t}")
            self.plotter.clear()

            # Reset all mesh references
            self.mesh_rho_slice = None
            self.mesh_phi_slice = None
            self.mesh_z_slice = None
            self.mesh_isosurface = None
            self.mesh_volume = None

            self._grid_rho = None
            self._grid_phi = None
            self._grid_z = None
            self._last_rho_idx = None
            self._last_phi_idx = None
            self._last_z_idx = None
            self.iso_layer_actors = [None] * len(self.iso_panel.layers)
            self._iso_keys = [None] * len(self.iso_panel.layers)

        self.file_panel.set_time_label(t)
        self.vol_panel.opacity_max_label.setText(f"{self.vol_panel.opacity_max.value()}%")
        self.vol_panel.opacity_min_label.setText(f"{self.vol_panel.opacity_min.value()}%")

        data_min, data_max = np.nanmin(data), np.nanmax(data)
        self.vol_panel.range_label.setText(f"Data range: [{data_min:.2f}, {data_max:.2f}]")

        rho = np.linspace(0, R, NRho)
        phi = np.linspace(0, 2 * np.pi, NPhi, endpoint=False)
        phi_closed = np.linspace(0, 2 * np.pi, NPhi + 1, endpoint=True)
        z = np.linspace(0, H, NZ)

        data_closed = np.concatenate([data, data[:, 0:1, :]], axis=1)

        cmap = self.slice_panel.cmap_combo.currentText()

        if self.mesh_outline is None:
            outline_mesh = build_cylinder_outline(R, H)
            self.mesh_outline = self.plotter.add_mesh(
                outline_mesh,
                color='black',
                line_width=1.5,
                opacity=0.4,
                render_lines_as_tubes=False,
            )

        _outline_visible = (
                not self.vol_panel.show_volume.isChecked()
                and len(self.iso_panel.layers) == 0
        )

        self.mesh_outline.SetVisibility(_outline_visible)

        rho_idx = int((self.slice_panel.rho_slider.value() / 100.0) * (NRho - 1))
        phi_idx = int((self.slice_panel.phi_slider.value() / 360.0) * (NPhi - 1))
        z_idx = int((self.slice_panel.z_slider.value() / 100.0) * (NZ - 1))

        self._update_slice(
            self.slice_panel.show_rho, 'mesh_rho_slice', '_grid_rho',
            build_cylindrical_slice_mesh, (rho[rho_idx], phi_closed, z, data_closed[rho_idx, :, :]),
            self._add_slice_to_plotter, (cmap,), '_last_rho_idx', rho_idx)
        self._update_slice(
            self.slice_panel.show_phi, 'mesh_phi_slice', '_grid_phi',
            build_radial_slice_mesh, (rho, phi[phi_idx], z, data[:, phi_idx, :]),
            self._add_slice_to_plotter, (cmap,), '_last_phi_idx', phi_idx)
        self._update_slice(
            self.slice_panel.show_z, 'mesh_z_slice', '_grid_z',
            build_horizontal_slice_mesh, (rho, phi_closed, z[z_idx], data_closed[:, :, z_idx]),
            self._add_slice_to_plotter, (cmap,), '_last_z_idx', z_idx)

        layers = self.iso_panel.layers
        n_layers = len(layers)

        while len(self.iso_layer_actors) < n_layers:
            self.iso_layer_actors.append(None)
            self._iso_keys.append(None)
        while len(self.iso_layer_actors) > n_layers:
            actor = self.iso_layer_actors.pop()
            self._iso_keys.pop()
            if actor is not None:
                try:
                    self.plotter.remove_actor(actor)
                except Exception:
                    pass

        for i, layer in enumerate(layers):
            actor = self.iso_layer_actors[i]
            visible = layer.get('visible', True)
            geo_key = (layer['val_min'], layer['val_max'], self.current_idx)

            if not visible:
                if actor is not None:
                    try:
                        actor.SetVisibility(False)
                    except Exception:
                        pass
                continue

            if actor is not None and self._iso_keys[i] == geo_key:
                try:
                    actor.SetVisibility(True)
                    actor.GetProperty().SetOpacity(layer['opacity'] / 100.0)
                    c = layer['color']
                    actor.GetProperty().SetColor(
                        c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0)
                except Exception:
                    pass
                continue

            if actor is not None:
                try:
                    self.plotter.remove_actor(actor)
                except Exception:
                    pass

            new_actor = self.add_isosurface_layer(rho, phi, z, data, layer)
            self.iso_layer_actors[i] = new_actor
            self._iso_keys[i] = geo_key if new_actor is not None else None

        if self.vol_panel.show_volume.isChecked():
            if self.mesh_volume is not None:
                self.plotter.remove_actor(self.mesh_volume)

            self.mesh_volume = self.add_volume(rho, phi, z, data)
        else:
            if self.mesh_volume is not None:
                self.plotter.remove_actor(self.mesh_volume)
                self.mesh_volume = None

        if full_rebuild:
            self.plotter.add_axes()

            if self.title_actor is not None:
                try:
                    self.plotter.remove_actor(self.title_actor)
                except:
                    pass

            try:
                self.title_actor = self.plotter.add_text(
                    f"T = {t:.6f}",
                    position=tuple(self.time_text_position),
                    font_size=TITLE.FONT_SIZE,
                    color=TITLE.COLOR,
                    viewport=True
                )
            except:
                pass
        else:
            if self.title_actor is not None:
                try:
                    self.title_actor.SetText(2, f"t = {t:.6f}")
                except:
                    pass

        self.plotter.render()
        self.update_info_display()

    def _add_slice_to_plotter(self, grid, cmap: str):
        return self.plotter.add_mesh(
            grid, scalars="values", cmap=cmap, lighting=False,
            scalar_bar_args={"title": self._cbar_label_edit.text() or SCALAR_BAR.TITLE}
        )

    def add_cylindrical_slice(self, r, phi, z, data, cmap):
        grid = build_cylindrical_slice_mesh(r, phi, z, data)
        return self.plotter.add_mesh(grid, scalars="values", cmap=cmap,
                                     lighting=False,
                                     scalar_bar_args={"title": self._cbar_label_edit.text() or SCALAR_BAR.TITLE})

    def add_radial_slice(self, rho, phi_angle, z, data, cmap):
        grid = build_radial_slice_mesh(rho, phi_angle, z, data)
        return self.plotter.add_mesh(grid, scalars="values", cmap=cmap,
                                     lighting=False,
                                     scalar_bar_args={"title": self._cbar_label_edit.text() or SCALAR_BAR.TITLE})

    def add_horizontal_slice(self, rho, phi, z_level, data, cmap):
        grid = build_horizontal_slice_mesh(rho, phi, z_level, data)
        return self.plotter.add_mesh(grid, scalars="values", cmap=cmap,
                                     lighting=False,
                                     scalar_bar_args={"title": self._cbar_label_edit.text() or SCALAR_BAR.TITLE})

    def add_isosurface_layer(self, rho, phi, z, data, layer: dict):
        val_min = layer['val_min']
        val_max = layer['val_max']
        color = layer['color']
        opacity = layer['opacity'] / 100.0

        iso = build_isosurface_layer_mesh(rho, phi, z, data, val_min, val_max)

        if iso.n_points > 0:
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0
            return self.plotter.add_mesh(
                iso,
                color=(r, g, b),
                opacity=opacity,
                smooth_shading=True,
            )
        return None

    def _update_scalar_bar_position(self):
        if self.mesh_volume is None:
            return
        try:
            for bar in self.plotter.scalar_bars.values():
                if bar is not None:
                    bar.SetPosition(self.pos_panel.scale_x.value(),
                                    self.pos_panel.scale_y.value())
            self.plotter.render()
        except Exception:
            self.update_visualization(False)

    def _update_scalar_bar_label(self):
        if self.mesh_volume is None:
            return
        try:
            label = self._cbar_label_edit.text() or 'u'
            for bar in self.plotter.scalar_bars.values():
                if bar is not None:
                    bar.SetTitle(label)
            self.plotter.render()
        except Exception:
            self.update_visualization(False)

    def _vol_update_opacity_fast(self):
        self.vol_panel.opacity_max_label.setText(f"{self.vol_panel.opacity_max.value()}%")
        self.vol_panel.opacity_min_label.setText(f"{self.vol_panel.opacity_min.value()}%")

        if self.mesh_volume is None:
            self.update_visualization(False)
            return

        try:
            opacity_max = self.vol_panel.opacity_max.value() / 100.0
            threshold_value = self.vol_panel.threshold.value()

            if self.snapshots:
                data = self.snapshots[self.current_idx]['u']
                actual_max = float(np.nanmax(data))
                threshold_value = min(threshold_value, actual_max)
            else:
                actual_max = 1.0

            opacity_min = self.vol_panel.opacity_min.value() / 100.0
            otf = self.mesh_volume.GetProperty().GetScalarOpacity()
            otf.RemoveAllPoints()
            otf.AddPoint(threshold_value, opacity_min)
            otf.AddPoint(actual_max, opacity_max)

            self.plotter.render()
        except Exception as e:
            print(f"Fast opacity update failed ({e}), falling back to rebuild")
            self.update_visualization(False)

    def add_volume(self, rho, phi, z, data):
        log("Adding volume rendering...")

        res_text = self.vol_panel.resolution.currentText()
        if 'Low' in res_text:
            res_factor = VOLUME.RES_LOW
        elif 'Medium' in res_text:
            res_factor = VOLUME.RES_MEDIUM
        elif 'High' in res_text:
            res_factor = VOLUME.RES_HIGH
        else:
            res_factor = VOLUME.RES_ULTRA

        log(f"Creating uniform grid at resolution: {res_text}")
        uniform_grid = build_volume_mesh(rho, phi, z, data, res_factor)
        values = uniform_grid.point_data["values"]

        valid_mask = ~np.isnan(values)
        if np.any(valid_mask):
            actual_min = np.min(values[valid_mask])
            actual_max = np.max(values[valid_mask])
        else:
            actual_min = 0.0
            actual_max = 1.0

        nan_value = VOLUME.NAN_FILL_VALUE

        values_copy = values.copy()
        values_copy[np.isnan(values_copy)] = nan_value
        uniform_grid.point_data["values"] = values_copy

        log(f"Kept as ImageData (no threshold) - GPU rendering will be smooth!")
        log(f"NaN replaced with {nan_value:.1f} (actual data range: [{actual_min:.3f}, {actual_max:.3f}])")

        try:
            log("Rendering volume...")
            cmap = self.vol_panel.cmap_combo.currentText()
            opacity_max = self.vol_panel.opacity_max.value() / 100.0

            all_values = uniform_grid.point_data["values"]
            actual_data_values = all_values[all_values > VOLUME.NAN_EXCLUDE_BELOW]

            if len(actual_data_values) > 0:
                data_min = np.min(actual_data_values)
                data_max = np.max(actual_data_values)
            else:
                data_min = 0.0
                data_max = 1.0

            threshold_value = self.vol_panel.threshold.value()
            threshold_value = min(threshold_value, data_max)

            log(f"Actual data range: [{data_min:.3f}, {data_max:.3f}]")
            log(f"Absolute transparency threshold: {threshold_value:.3f} (values below are transparent)")
            log(f"Max opacity: {opacity_max:.2f}")

            actor = self.plotter.add_volume(
                uniform_grid,
                scalars="values",
                cmap=cmap,
                opacity='linear',
                clim=[threshold_value, data_max],
                shade=False,
                mapper='smart',  # Smart mapper for better quality
                show_scalar_bar=True,
                scalar_bar_args={
                    'title': self._cbar_label_edit.text() or SCALAR_BAR.TITLE,
                    'vertical': True,
                    'height': SCALAR_BAR.HEIGHT,
                    'width': SCALAR_BAR.WIDTH,
                    'position_x': self.pos_panel.scale_x.value(),
                    'position_y': self.pos_panel.scale_y.value()
                }
            )

            if actor:
                volume_property = actor.GetProperty()

                opacity_min = self.vol_panel.opacity_min.value() / 100.0
                volume_property.GetScalarOpacity().RemoveAllPoints()
                volume_property.GetScalarOpacity().AddPoint(threshold_value, opacity_min)
                volume_property.GetScalarOpacity().AddPoint(data_max, opacity_max)
                volume_property.SetInterpolationTypeToLinear()

                volume_property.SetShade(False)  # Keep shading off

                mapper = actor.GetMapper()
                if hasattr(mapper, 'SetSampleDistance'):
                    sample_distance = min(uniform_grid.spacing) * VOLUME.SAMPLE_DISTANCE_FACTOR
                    mapper.SetSampleDistance(sample_distance)
                    mapper.SetAutoAdjustSampleDistances(0)  # Manual control

                log(f"Interpolation: Linear (smooth rendering)")
                log(f"Sample distance: {sample_distance:.4f} (fine quality)")

            log("Volume rendering complete (smooth + properly colored)!")
            return actor
        except Exception as e:
            print(f"Volume rendering error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_screenshot(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox

        # Get current time for default filename
        if self.snapshots and self.current_idx < len(self.snapshots):
            t = self.snapshots[self.current_idx]['t']
            default_name = f"volume_3d_t{t:.2f}.png"
        else:
            default_name = "volume_3d_screenshot.png"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            default_name,
            "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf);;All Files (*)"
        )

        if filename:
            try:
                self.plotter.screenshot(filename)

                QMessageBox.information(
                    self,
                    "Screenshot Saved",
                    f"Screenshot saved successfully:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save screenshot:\n{str(e)}"
                )

    def _hide_2d_actors(self):
        backup = []
        if self.title_actor is not None:
            backup.append((self.title_actor, self.title_actor.GetVisibility()))
            self.title_actor.SetVisibility(False)
        if hasattr(self.plotter, 'scalar_bars'):
            for bar in self.plotter.scalar_bars.values():
                if bar is not None:
                    backup.append((bar, bar.GetVisibility()))
                    bar.SetVisibility(False)
        for actor in self.plotter.renderer.GetActors2D():
            try:
                backup.append((actor, actor.GetVisibility()))
                actor.SetVisibility(False)
            except Exception:
                pass
        return backup

    def _restore_2d_actors(self, backup):
        for actor, visibility in backup:
            try:
                actor.SetVisibility(visibility)
            except Exception:
                pass

    def export_gif(self):
        idx_backup = self.current_idx
        camera_backup = self.plotter.camera_position
        export_gif_3d(
            parent=self,
            snapshots=self.snapshots,
            render_frame=self._render_gif_frame_3d,
            hide_2d_actors=self._hide_2d_actors,
            restore_2d_actors=self._restore_2d_actors,
            default_filename="volume_3d_animation.gif",
        )
        self.current_idx = idx_backup
        self.update_visualization(full_rebuild=True)
        self.plotter.camera_position = camera_backup

    def _render_gif_frame_3d(self, idx: int):
        self.current_idx = idx
        self.update_visualization(full_rebuild=True)
        self.plotter.render()
        return self.plotter.screenshot(return_img=True, transparent_background=False)


def main():
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = VolumeViewer3D()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
