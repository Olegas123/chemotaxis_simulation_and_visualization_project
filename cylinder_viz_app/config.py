"""
config.py

Single source os all constants, defaults, and configuration
values used across the Chemotaxis Simulation Visualizer Suite.

Sections:
    DOMAIN       - physical / simulation geometry defaults
    GIF          - animation export settings
    COLORMAPS    - ordered colormap lists used in combo-boxes
    FIGURE       - Matplotlib figure sizes and export DPI
    UI           - window geometry and splitter sizes
    VOLUME       - 3D volume rendering parameters
    SCALAR_BAR   - PyVista scalar-bar positioning
    LIGHTING     - PyVista light intensities and positions
    ISOSURFACE   - iso-layer widget defaults
    CAMERA       - default camera position multipliers
    TITLE        - on-screen text / title defaults
"""

import numpy as np


# ── Domain / geometry ─────────────────────────────────────────────────────────

class DOMAIN:
    DEFAULT_RADIUS: float = 5.0  # R  - cylinder / disk outer radius
    DEFAULT_HEIGHT: float = 10.0  # H  - cylinder height
    DEFAULT_CIRCUMFERENCE: float = 2 * np.pi * DEFAULT_RADIUS  # L = 2 * pi * r

    DEFAULT_T: float = 400.0  # Total simulation time (fall-back)
    DEFAULT_L_POLAR: float = 2 * np.pi * 4.5  # Circumference fall-back for polar data
    DEFAULT_L_CYL: float = 2 * np.pi * 5.0  # Circumference fall-back for cylindrical data


class GIF:
    DEFAULT_FPS: int = 10
    DEFAULT_DPI: int = 100
    DEFAULT_SKIP: int = 1
    MAX_FPS: int = 60
    MIN_FPS: int = 1
    MAX_DPI: int = 300
    MIN_DPI: int = 50
    DPI_STEP: int = 50
    MAX_FRAME_SKIP: int = 50
    EXPORT_DPI: int = 300


class COLORMAPS:
    # General-purpose - used in most 2D viewers
    STANDARD = ['viridis', 'plasma', 'inferno', 'magma',
                'hot', 'cool', 'jet', 'turbo']

    # 3D slice colormaps (diverging maps included)
    SLICES = ['viridis', 'plasma', 'coolwarm', 'seismic']

    # Volume rendering colormaps
    VOLUME = ['viridis', 'plasma', 'inferno', 'magma', 'hot', 'cool']

    # FFT / spectral analysis
    FFT = ['viridis', 'hot', 'jet', 'turbo']

    # Combined-viewer colormaps
    COMBINED = ['viridis', 'plasma', 'inferno', 'magma',
                'cividis', 'coolwarm', 'seismic', 'turbo', 'jet']

    # Snapshot-only colormaps (shorter list for simple viewers)
    SNAPSHOT = ['viridis', 'plasma', 'inferno', 'magma', 'hot', 'cool']

    # Spatiotemporal analysis (full list)
    SPATIOTEMPORAL = ['viridis', 'plasma', 'inferno', 'magma',
                      'hot', 'cool', 'jet', 'turbo', 'RdBu', 'seismic',
                      'bwr', 'coolwarm']

    # Default selection shown when a combo-box first appears
    DEFAULT = 'viridis'


class FIGURE:
    POLAR_SNAPSHOT = (8, 8)
    CYL_SNAPSHOT = (12, 6)
    SPATIOTEMPORAL = (12, 8)
    TIME_SLICE = (12, 6)
    SPACE_SLICE = (12, 6)
    FFT = (12, 8)
    STATISTICS = (12, 10)
    MULTI_PANEL = (14, 10)
    VIEWER_1D = (12, 8)


class UI:
    LAUNCHER = (100, 100, 1400, 900)
    POLAR_VIEWER = (150, 150, 1400, 700)
    CYL_VIEWER = (150, 150, 1400, 700)
    COMBINED_VIEWER = (100, 100, 1600, 900)
    VOLUME_VIEWER = (100, 100, 1600, 900)
    SPATIOTEMPORAL = (100, 100, 1600, 900)
    MULTI_VIEWER = (100, 100, 1400, 900)
    VIEWER_1D = (150, 150, 1200, 800)

    SPLIT_POLAR = [300, 1100]
    SPLIT_CYL = [300, 1100]
    SPLIT_COMBINED = [350, 1250]
    SPLIT_VOLUME = [400, 1200]
    SPLIT_SPATIOTEMPORAL = [350, 1250]

    CONTROL_PANEL_MAX_WIDTH = 350
    INFO_TEXT_MAX_HEIGHT = 200
    FILE_LIST_MAX_HEIGHT = 150
    ISO_SCROLL_MIN_HEIGHT = 120
    ISO_SCROLL_MAX_HEIGHT = 300


# ── 3-D volume rendering ──────────────────────────────────────────────────────

class VOLUME:
    RES_LOW: int = 30
    RES_MEDIUM: int = 50
    RES_HIGH: int = 70
    RES_ULTRA: int = 90

    # Opacity transfer function defaults
    DEFAULT_MAX_OPACITY: float = 0.60  # opacity at data maximum
    DEFAULT_MIN_OPACITY: float = 0.00  # opacity at threshold value
    DEFAULT_THRESHOLD: float = 0.30  # absolute value below which data is transparent

    # Slider ranges
    MAX_OPACITY_SLIDER_MIN: int = 10
    MAX_OPACITY_SLIDER_MAX: int = 100
    MIN_OPACITY_SLIDER_MAX: int = 50
    THRESHOLD_MAX: float = 5.0
    THRESHOLD_STEP: float = 0.1

    # Sampling
    NAN_FILL_VALUE: float = -999.0  # replaces NaN before GPU upload
    NAN_EXCLUDE_BELOW: float = -900.0  # guard value used when filtering NaN fill
    SAMPLE_DISTANCE_FACTOR: float = 0.5  # multiplied by min grid spacing

    # Background colour
    BACKGROUND_COLOR: str = 'white'


class SCALAR_BAR:
    HEIGHT: float = 0.6
    WIDTH: float = 0.05
    POSITION_X: float = 0.85
    POSITION_Y: float = 0.20
    TITLE: str = 'u koncentracija'

    DEFAULT_X: float = 0.75
    DEFAULT_Y: float = 0.20


class LIGHTING:
    AMBIENT_INTENSITY: float = 0.5
    KEY_INTENSITY: float = 0.8
    FILL_INTENSITY: float = 0.4

    KEY_Z_MULT: float = 3.0  # key light at R * KEY_Z_MULT above origin
    FILL_XY_MULT: float = 3.0  # fill lights at radius * FILL_XY_MULT
    FILL_Z_MULT: float = 0.5  # fill lights at height * FILL_Z_MULT


class ISOSURFACE:
    DEFAULT_MIN: float = 0.5
    DEFAULT_MAX: float = 0.8
    DEFAULT_OPACITY: int = 60  # percent (0–100)
    DEFAULT_COLOR_R: int = 0  # RGB components of initial colour (cyan)
    DEFAULT_COLOR_G: int = 255
    DEFAULT_COLOR_B: int = 255

    VALUE_RANGE_MIN: float = -100.0
    VALUE_RANGE_MAX: float = 100.0
    VALUE_STEP: float = 0.05
    VALUE_DECIMALS: int = 3

    OPACITY_MIN: int = 5
    OPACITY_MAX: int = 100

    # Luminance threshold for choosing black vs white label text on a swatch
    LUMINANCE_THRESHOLD: float = 128.0
    LUMINANCE_R_WEIGHT: float = 0.299
    LUMINANCE_G_WEIGHT: float = 0.587
    LUMINANCE_B_WEIGHT: float = 0.114


class CAMERA:
    ISO_XY_MULT: float = 2.5  # camera x/y = radius * ISO_XY_MULT
    ISO_Z_MULT: float = 0.7  # camera z   = height * ISO_Z_MULT
    FOCAL_Z_MULT: float = 0.5  # focal point z = height * FOCAL_Z_MULT


class TITLE:
    FONT_SIZE: int = 14
    COLOR: str = 'black'
    DEFAULT_POSITION_X: float = 0.5
    DEFAULT_POSITION_Y: float = 0.9
    DEFAULT_POSITION: str = 'upper_edge'


class COMBINED_VIEWER:
    DEFAULT_OPACITY: int = 90  # percent, used for both disk and cylinder sliders


class MULTI_SPATIOTEMPORAL:
    GRID_MIN: int = 1
    GRID_MAX: int = 4  # max rows or columns in the panel grid
    DEFAULT_ROWS: int = 2
    DEFAULT_COLS: int = 2

    ASPECT_RATIOS = {
        'auto': 'auto',
        'equal': 'equal',
        '2:1': 2.0,
        '1:2': 0.5,
        '3:1': 3.0,
        '1:3': 0.33,
    }


class VISUALIZATION_CONFIG:
    DISK_OPACITY: float = 0.9
    CYLINDER_OPACITY: float = 0.9
    DEFAULT_COLORMAP: str = 'viridis'


class COLORS:
    BACKGROUND: str = 'white'
    BOTTOM_DISK_GRAY: str = 'lightgray'
