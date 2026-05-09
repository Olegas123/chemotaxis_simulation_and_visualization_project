"""
visualization.py

Module for configuring and managing PyVista visualization.
Handles plotter setup, mesh rendering and camera controls.
"""

import pyvista as pv
from typing import Dict, Optional, Tuple
from config import DOMAIN, LIGHTING, SCALAR_BAR, CAMERA, COLORMAPS, TITLE, VISUALIZATION_CONFIG, COLORS


class VisualizationConfig:
    def __init__(self):
        self.disk_opacity = VISUALIZATION_CONFIG.DISK_OPACITY
        self.cylinder_opacity = VISUALIZATION_CONFIG.CYLINDER_OPACITY
        self.disk_colormap = VISUALIZATION_CONFIG.DEFAULT_COLORMAP
        self.cylinder_colormap = VISUALIZATION_CONFIG.DEFAULT_COLORMAP
        self.use_same_colormap = True
        self.use_separate_scaling = True
        self.show_disks = True
        self.show_cylinder = True
        self.show_edges = False

        self.title_position = TITLE.DEFAULT_POSITION
        self.title_font_size = TITLE.FONT_SIZE
        self.title_color = TITLE.COLOR

        self.camera_locked = False

    def to_dict(self) -> Dict:
        return {
            'disk_opacity': self.disk_opacity,
            'cylinder_opacity': self.cylinder_opacity,
            'disk_colormap': self.disk_colormap,
            'cylinder_colormap': self.cylinder_colormap,
            'use_same_colormap': self.use_same_colormap,
            'use_separate_scaling': self.use_separate_scaling,
            'show_disks': self.show_disks,
            'show_cylinder': self.show_cylinder,
            'show_edges': self.show_edges,
            'title_position': self.title_position,
            'title_font_size': self.title_font_size,
            'title_color': self.title_color,
            'camera_locked': self.camera_locked
        }


class CylinderVisualizer:
    def __init__(self, plotter):
        self.plotter = plotter
        self.config = VisualizationConfig()

        # Mesh references
        self.mesh_top = None
        self.mesh_bottom = None
        self.mesh_cylinder = None

        # Actor references
        self.title_actor = None
        self.scalar_bar_label_actor = None

        # Camera lock state
        self.locked_camera_position = None

        # Bottom disk settings
        self.show_bottom_disk = True
        self.bottom_disk_gray = False

        # Geometry parameters
        self.radius = DOMAIN.DEFAULT_RADIUS
        self.height = DOMAIN.DEFAULT_HEIGHT

    def clear(self):
        saved_camera = None
        if self.config.camera_locked and self.locked_camera_position is not None:
            saved_camera = self.locked_camera_position

        # Remove scalar bars explicitly before clearing (apparently some PyVista
        # versions do not remove them via plotter.clear())
        try:
            self.plotter.remove_scalar_bar()
        except Exception:
            pass
        self.plotter.clear()
        self.mesh_top = None
        self.mesh_bottom = None
        self.mesh_cylinder = None
        self.title_actor = None
        self.scalar_bar_label_actor = None

        # Restore camera position if it was locked
        if saved_camera is not None:
            try:
                self.plotter.camera_position = saved_camera
            except:
                pass

    def add_disk_meshes(self,
                        top_mesh: pv.StructuredGrid,
                        bottom_mesh: pv.StructuredGrid,
                        color_limits: Tuple[float, float],
                        colormap: str,
                        show_bottom: bool = True,
                        bottom_gray: bool = False):
        self.show_bottom_disk = show_bottom
        self.bottom_disk_gray = bottom_gray

        self.mesh_top = self.plotter.add_mesh(
            top_mesh,
            scalars="u",
            cmap=colormap,
            clim=color_limits,
            smooth_shading=False,
            lighting=False,
            opacity=self.config.disk_opacity,
            show_edges=self.config.show_edges,
            show_scalar_bar=False
        )

        if show_bottom:
            if bottom_gray:
                self.mesh_bottom = self.plotter.add_mesh(
                    bottom_mesh,
                    color=COLORS.BOTTOM_DISK_GRAY,
                    smooth_shading=False,
                    lighting=False,
                    opacity=self.config.disk_opacity,
                    show_edges=self.config.show_edges,
                    show_scalar_bar=False
                )
            else:
                self.mesh_bottom = self.plotter.add_mesh(
                    bottom_mesh,
                    scalars="u",
                    cmap=colormap,
                    clim=color_limits,
                    smooth_shading=False,
                    lighting=False,
                    opacity=self.config.disk_opacity,
                    show_edges=self.config.show_edges,
                    show_scalar_bar=False
                )
            show_edges = self.config.show_edges,
            show_scalar_bar = False

    def add_cylinder_mesh(self,
                          cylinder_mesh: pv.StructuredGrid,
                          color_limits: Tuple[float, float],
                          colormap: str,
                          scalar_bar_label: str = None):
        self.mesh_cylinder = self.plotter.add_mesh(
            cylinder_mesh,
            scalars="u",
            cmap=colormap,
            clim=color_limits,
            smooth_shading=False,
            lighting=False,
            opacity=self.config.cylinder_opacity,
            show_edges=self.config.show_edges,
            show_scalar_bar=True,
            scalar_bar_args={
                'title': scalar_bar_label if scalar_bar_label is not None else SCALAR_BAR.TITLE,
                'vertical': True,
                'height': SCALAR_BAR.HEIGHT,
                'width': SCALAR_BAR.WIDTH,
                'position_x': SCALAR_BAR.POSITION_X,
                'position_y': SCALAR_BAR.POSITION_Y,
            }
        )

    def setup_scene(self, title: str = "Combined Cylinder View"):
        self.plotter.add_axes(
            xlabel='X',
            ylabel='Y',
            zlabel='Z (Height)',
            line_width=3,
            labels_off=False
        )

        if self.title_actor is not None:
            try:
                self.plotter.remove_actor(self.title_actor)
            except:
                pass

        try:
            if self.config.title_position == 'upper_edge':
                self.title_actor = self.plotter.add_text(
                    title,
                    position=(TITLE.DEFAULT_POSITION_X, TITLE.DEFAULT_POSITION_Y),
                    font_size=self.config.title_font_size,
                    color=self.config.title_color,
                    viewport=True  # Use normalized viewport coordinates
                )
            else:
                self.title_actor = self.plotter.add_text(
                    title,
                    position=self.config.title_position,
                    font_size=self.config.title_font_size,
                    color=self.config.title_color
                )
        except:
            pass

        # Remove default lights and add custom bright lighting
        self.plotter.remove_all_lights()

        ambient_light = pv.Light(light_type='headlight')
        ambient_light.intensity = LIGHTING.AMBIENT_INTENSITY
        self.plotter.add_light(ambient_light)

        # Add bright key light from front
        key_light = pv.Light(position=(0, 0, self.height * LIGHTING.KEY_Z_MULT))
        key_light.intensity = LIGHTING.KEY_INTENSITY
        key_light.positional = True
        self.plotter.add_light(key_light)

        # Add fill lights from sides for even illumination
        fill_light1 = pv.Light(position=(self.radius * LIGHTING.FILL_XY_MULT, 0, self.height * LIGHTING.FILL_Z_MULT))
        fill_light1.intensity = LIGHTING.FILL_INTENSITY
        self.plotter.add_light(fill_light1)

        fill_light2 = pv.Light(position=(-self.radius * LIGHTING.FILL_XY_MULT, 0, self.height * LIGHTING.FILL_Z_MULT))
        fill_light2.intensity = LIGHTING.FILL_INTENSITY
        self.plotter.add_light(fill_light2)

        fill_light3 = pv.Light(position=(0, self.radius * LIGHTING.FILL_XY_MULT, self.height * LIGHTING.FILL_Z_MULT))
        fill_light3.intensity = LIGHTING.FILL_INTENSITY
        self.plotter.add_light(fill_light3)

        fill_light4 = pv.Light(position=(0, -self.radius * LIGHTING.FILL_XY_MULT, self.height * LIGHTING.FILL_Z_MULT))
        fill_light4.intensity = LIGHTING.FILL_INTENSITY
        self.plotter.add_light(fill_light4)

    def set_camera_position(self, position: str = 'isometric'):
        if position == 'isometric':
            self.plotter.camera_position = [
                (self.radius * CAMERA.ISO_XY_MULT, self.radius * CAMERA.ISO_XY_MULT, self.height * CAMERA.ISO_Z_MULT),
                (0, 0, self.height * CAMERA.FOCAL_Z_MULT),
                (0, 0, 1)
            ]
        elif position == 'top':
            self.plotter.view_xy()
        elif position == 'side':
            self.plotter.view_xz()
        elif position == 'front':
            self.plotter.view_yz()

        self.plotter.render()

    def reset_camera(self):
        self.set_camera_position('isometric')

    def lock_camera(self):
        try:
            self.locked_camera_position = self.plotter.camera_position
            self.config.camera_locked = True
            return True
        except Exception as e:
            print(f"Failed to lock camera: {e}")
            return False

    def unlock_camera(self):
        self.config.camera_locked = False
        self.locked_camera_position = None

    def is_camera_locked(self) -> bool:
        return self.config.camera_locked

    def restore_locked_camera(self):
        if self.config.camera_locked and self.locked_camera_position is not None:
            try:
                self.plotter.camera_position = self.locked_camera_position
                self.plotter.render()
            except Exception as e:
                print(f"Failed to restore camera: {e}")

    def get_camera_info(self) -> dict:
        try:
            pos = self.plotter.camera_position
            return {
                'position': pos[0],
                'focal_point': pos[1],
                'view_up': pos[2],
                'locked': self.config.camera_locked
            }
        except:
            return {'locked': self.config.camera_locked}

    def update_transparency(self, disk_opacity: Optional[float] = None,
                            cylinder_opacity: Optional[float] = None):
        if disk_opacity is not None:
            self.config.disk_opacity = disk_opacity
            if self.mesh_top is not None:
                self.mesh_top.GetProperty().SetOpacity(disk_opacity)
            if self.mesh_bottom is not None:
                self.mesh_bottom.GetProperty().SetOpacity(disk_opacity)

        if cylinder_opacity is not None:
            self.config.cylinder_opacity = cylinder_opacity
            if self.mesh_cylinder is not None:
                self.mesh_cylinder.GetProperty().SetOpacity(cylinder_opacity)

        self.plotter.render()

    def update_visibility(self, show_disks: Optional[bool] = None,
                          show_cylinder: Optional[bool] = None):
        if show_disks is not None:
            self.config.show_disks = show_disks
            if self.mesh_top is not None:
                self.mesh_top.SetVisibility(show_disks)
            if self.mesh_bottom is not None:
                # Bottom disk respects BOTH show_disks AND show_bottom_disk
                visible = show_disks and self.show_bottom_disk
                self.mesh_bottom.SetVisibility(visible)

        if show_cylinder is not None:
            self.config.show_cylinder = show_cylinder
            if self.mesh_cylinder is not None:
                self.mesh_cylinder.SetVisibility(show_cylinder)

        self.plotter.render()

    def update_bottom_disk_settings(self, show_bottom: bool, use_gray: bool):
        self.show_bottom_disk = show_bottom
        self.bottom_disk_gray = use_gray

        if self.mesh_bottom is not None:
            self.mesh_bottom.SetVisibility(show_bottom)

    def set_title_position(self, position: str):
        self.config.title_position = position

    def set_title_font_size(self, size: int):
        self.config.title_font_size = size

    def save_screenshot(self, filename: str):
        self.plotter.screenshot(filename)


# Available colormaps (kept for backward compatibility)
COLORMAPS = COLORMAPS.COMBINED
