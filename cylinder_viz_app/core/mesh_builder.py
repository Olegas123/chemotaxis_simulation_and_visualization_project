"""
mesh_builder.py

Functions for building PyVista meshes from simulation data.
All functions are stateless: they accept numpy arrays and return PyVista objects.
"""

import numpy as np
import pyvista as pv
from typing import Dict, Tuple
from config import DOMAIN


def create_disk_mesh(polar_data: np.ndarray,
                     r: float,
                     z_position: float,
                     wrap: bool = True) -> pv.StructuredGrid:
    NR, NPhi = polar_data.shape
    r_vals = np.linspace(0, r, NR)
    theta_vals = np.linspace(0, 2 * np.pi, NPhi, endpoint=False)
    R_grid, Theta_grid = np.meshgrid(r_vals, theta_vals)
    X = R_grid * np.cos(Theta_grid)
    Y = R_grid * np.sin(Theta_grid)
    Z = np.full_like(X, z_position)
    data_t = polar_data.T  # (NPhi, NR)
    if wrap:
        data_t = np.vstack([data_t, data_t[0:1, :]])
        X = np.vstack([X, X[0:1, :]])
        Y = np.vstack([Y, Y[0:1, :]])
        Z = np.vstack([Z, Z[0:1, :]])
    grid = pv.StructuredGrid()
    grid.points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    grid.dimensions = [NR, data_t.shape[0], 1]
    grid.point_data["u"] = data_t.ravel()
    return grid


def create_cylinder_mesh(cylindrical_data: np.ndarray,
                         r: float,
                         H: float,
                         wrap: bool = True) -> pv.StructuredGrid:
    NX, NZ = cylindrical_data.shape
    theta = np.linspace(0, 2 * np.pi, NX, endpoint=False)
    z = np.linspace(0, H, NZ)
    Theta, Z = np.meshgrid(theta, z)
    X = r * np.cos(Theta)
    Y = r * np.sin(Theta)
    data_t = cylindrical_data.T  # (NZ, NX)
    if wrap:
        data_t = np.hstack([data_t, data_t[:, 0:1]])
        X = np.hstack([X, X[:, 0:1]])
        Y = np.hstack([Y, Y[:, 0:1]])
        Z = np.hstack([Z, Z[:, 0:1]])
    grid = pv.StructuredGrid()
    grid.points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    grid.dimensions = [data_t.shape[1], data_t.shape[0], 1]
    grid.point_data["u"] = data_t.ravel()
    return grid


def build_combined_meshes(polar_data: np.ndarray,
                          cylindrical_data: np.ndarray,
                          polar_params: Dict[str, float],
                          cyl_params: Dict[str, float]) -> Dict[str, pv.StructuredGrid]:
    r = polar_params.get("R", cyl_params.get("r", DOMAIN.DEFAULT_RADIUS))
    H = cyl_params.get("H", DOMAIN.DEFAULT_HEIGHT)
    return {
        'top': create_disk_mesh(polar_data, r, H, wrap=True),
        'bottom': create_disk_mesh(polar_data, r, 0.0, wrap=True),
        'cylinder': create_cylinder_mesh(cylindrical_data, r, H, wrap=True),
    }


def get_separate_color_limits(polar_data: np.ndarray,
                              cylindrical_data: np.ndarray) -> Dict[str, tuple]:
    return {
        'polar': (float(np.nanmin(polar_data)), float(np.nanmax(polar_data))),
        'cylindrical': (float(np.nanmin(cylindrical_data)), float(np.nanmax(cylindrical_data))),
    }


def get_unified_color_limits(polar_data: np.ndarray,
                             cylindrical_data: np.ndarray) -> tuple:
    return (
        float(min(np.nanmin(polar_data), np.nanmin(cylindrical_data))),
        float(max(np.nanmax(polar_data), np.nanmax(cylindrical_data))),
    )

def build_cylindrical_slice_mesh(r: float,
                                 phi: np.ndarray,
                                 z: np.ndarray,
                                 data: np.ndarray) -> pv.StructuredGrid:
    Phi, Z = np.meshgrid(phi, z)
    X = r * np.cos(Phi)
    Y = r * np.sin(Phi)

    grid = pv.StructuredGrid()
    grid.points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    grid.dimensions = [len(phi), len(z), 1]
    grid.point_data["values"] = data.T.ravel()
    return grid


def build_radial_slice_mesh(rho: np.ndarray,
                            phi_angle: float,
                            z: np.ndarray,
                            data: np.ndarray) -> pv.StructuredGrid:
    Rho, Z = np.meshgrid(rho, z)
    X = Rho * np.cos(phi_angle)
    Y = Rho * np.sin(phi_angle)

    grid = pv.StructuredGrid()
    grid.points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    grid.dimensions = [len(rho), len(z), 1]
    grid.point_data["values"] = data.T.ravel()
    return grid


def build_horizontal_slice_mesh(rho: np.ndarray,
                                phi: np.ndarray,
                                z_level: float,
                                data: np.ndarray) -> pv.StructuredGrid:
    Rho, Phi = np.meshgrid(rho, phi)
    X = Rho * np.cos(Phi)
    Y = Rho * np.sin(Phi)
    Z = np.full_like(X, z_level)

    grid = pv.StructuredGrid()
    grid.points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    grid.dimensions = [len(rho), len(phi), 1]
    grid.point_data["values"] = data.T.ravel()
    return grid


def build_isosurface_layer_mesh(rho: np.ndarray,
                                phi: np.ndarray,
                                z: np.ndarray,
                                data: np.ndarray,
                                val_min: float,
                                val_max: float) -> pv.PolyData:
    from scipy.interpolate import RegularGridInterpolator

    data_max = float(np.nanmax(data))
    data_min = float(np.nanmin(data))
    effective_max = min(val_max, data_max)
    effective_min = max(val_min, data_min)
    if effective_min >= effective_max:
        return pv.PolyData()  # band is entirely outside data range
    iso_value = (effective_min + effective_max) / 2.0
    R = rho[-1]
    n_xy = max(len(rho) * 2, 40)

    x_lin = np.linspace(-R, R, n_xy)
    y_lin = np.linspace(-R, R, n_xy)
    z_lin = z

    X_uni, Y_uni, Z_uni = np.meshgrid(x_lin, y_lin, z_lin, indexing='ij')
    Rho_uni = np.sqrt(X_uni ** 2 + Y_uni ** 2)
    Phi_uni = np.arctan2(Y_uni, X_uni)
    Phi_uni[Phi_uni < 0] += 2 * np.pi

    interp = RegularGridInterpolator(
        (rho, phi, z),
        data,
        method='linear',
        bounds_error=False,
        fill_value=effective_min - 1.0,
    )
    pts = np.column_stack([Rho_uni.ravel(), Phi_uni.ravel(), Z_uni.ravel()])
    values_uni = interp(pts).reshape(X_uni.shape)

    out_of_cyl = Rho_uni > R
    out_of_band = (values_uni < effective_min) | (values_uni > effective_max)
    values_uni[out_of_cyl] = effective_min - 1.0
    values_uni[~out_of_cyl & out_of_band] = iso_value - 1e-6

    grid = pv.RectilinearGrid(x_lin, y_lin, z_lin)
    grid.point_data["values"] = values_uni.ravel(order="F")

    try:
        iso = grid.contour([iso_value], scalars="values")
        return iso
    except Exception:
        return pv.PolyData()


def build_volume_mesh(rho: np.ndarray,
                      phi: np.ndarray,
                      z: np.ndarray,
                      data: np.ndarray,
                      resolution: int) -> pv.ImageData:
    NRho, NPhi, NZ = len(rho), len(phi), len(z)
    R = rho[-1]

    x_min, x_max = -R, R
    y_min, y_max = -R, R
    z_min, z_max = z[0], z[-1]

    nx = ny = resolution
    nz = min(resolution, NZ)

    x_uniform = np.linspace(x_min, x_max, nx)
    y_uniform = np.linspace(y_min, y_max, ny)
    z_uniform = np.linspace(z_min, z_max, nz)

    X_uni, Y_uni, Z_uni = np.meshgrid(x_uniform, y_uniform, z_uniform, indexing='ij')

    Rho_uni = np.sqrt(X_uni ** 2 + Y_uni ** 2)
    Phi_uni = np.arctan2(Y_uni, X_uni)
    Phi_uni[Phi_uni < 0] += 2 * np.pi

    Rho_flat = Rho_uni.ravel()
    Phi_flat = Phi_uni.ravel()
    Z_flat = Z_uni.ravel()

    rho_idx = np.clip(np.searchsorted(rho, Rho_flat, side='left'), 0, NRho - 1)
    phi_idx = ((Phi_flat / (2 * np.pi)) * NPhi).astype(int) % NPhi
    z_idx = np.clip(np.searchsorted(z, Z_flat, side='left'), 0, NZ - 1)

    inside = Rho_flat <= R
    values = np.full(Rho_flat.shape, np.nan)
    values[inside] = data[rho_idx[inside], phi_idx[inside], z_idx[inside]]

    try:
        grid = pv.ImageData()
    except AttributeError:
        grid = pv.UniformGrid()

    grid.dimensions = [nx, ny, nz]
    grid.spacing = [
        (x_max - x_min) / max(nx - 1, 1),
        (y_max - y_min) / max(ny - 1, 1),
        (z_max - z_min) / max(nz - 1, 1),
    ]
    grid.origin = [x_min, y_min, z_min]
    grid.point_data["values"] = values.reshape(X_uni.shape).ravel(order='F')
    return grid


def build_cylinder_outline(R: float, H: float,
                           n_phi: int = 64) -> "pv.PolyData":
    phi = np.linspace(0, 2 * np.pi, n_phi, endpoint=False)
    x = R * np.cos(phi)
    y = R * np.sin(phi)

    lines = []

    top_pts = np.column_stack([x, y, np.full(n_phi, H)])
    for i in range(n_phi):
        lines.append(pv.Line(top_pts[i], top_pts[(i + 1) % n_phi]))

    bot_pts = np.column_stack([x, y, np.zeros(n_phi)])
    for i in range(n_phi):
        lines.append(pv.Line(bot_pts[i], bot_pts[(i + 1) % n_phi]))

    for i in range(0, n_phi, n_phi // 4):
        lines.append(pv.Line(bot_pts[i], top_pts[i]))

    return lines[0].merge(lines[1:]) if len(lines) > 1 else lines[0]
