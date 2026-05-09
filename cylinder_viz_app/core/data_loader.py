"""
data_loader.py

Module for loading and parsing simulation data files.
Handles both polar and cylindrical data formats.
Also supports some historical functionality that needs to be removed
"""

import os
import re
from typing import List, Dict, Tuple, Optional
import numpy as np


def parse_header(lines: List[str]) -> Dict[str, float]:
    params = {}
    param_pattern = re.compile(r"#\s*([A-Za-z0-9_]+)\s*=\s*([\-0-9.eE]+)")

    for line in lines:
        if not line.startswith("#"):
            continue
        m = param_pattern.match(line.strip())
        if m:
            key = m.group(1)
            try:
                val = float(m.group(2))
            except ValueError:
                continue
            params[key] = val

    return params


# TODO: Refactor
def load_snapshots(path: str) -> Tuple[Dict[str, float], List[Dict]]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Split header and body
    header_lines = []
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("SNAPSHOT"):
            body_start = i
            break
        header_lines.append(line)

    params = parse_header(header_lines)
    snapshots = []

    file_type = None
    NR = None
    NPhi = None

    print(f"[DEBUG] Available parameters: {list(params.keys())}")

    if "N_PHI" in params:
        N_PHI_val = int(params["N_PHI"])

        # Check if this is a polar file (has N_RHO) or cylindrical file (has NZ)
        if "N_RHO" in params and "NZ" not in params:
            # 2D Polar file: N_RHO * N_PHI (radial * angular)
            file_type = "polar"
            N_RHO_val = int(params["N_RHO"])
            NR = N_RHO_val  # Number of rows = radial points
            NPhi = N_PHI_val  # Number of columns = angular points
            print(f"[DEBUG] Detected POLAR file: {NR} rows × {NPhi} columns")

        elif "NZ" in params:
            # 2D Cylindrical file: N_PHI * NZ (angular * vertical)
            file_type = "cylindrical"
            NZ_val = int(params["NZ"])
            NR = NZ_val  # Number of rows in file = vertical points (z-levels)
            NPhi = N_PHI_val  # Number of columns in file = angular points (phi)
            print(f"[DEBUG] Detected CYLINDRICAL file: {NR} rows (NZ) × {NPhi} columns (N_PHI)")

    elif "NX" in params and "NZ" in params:
        NX_val = int(params["NX"])
        NZ_val = int(params["NZ"])

        if "H" in params and "R" in params:
            H_val = params["H"]
            R_val = params["R"]

            if abs(H_val - R_val) < 0.1:
                file_type = "polar"
                NR = NZ_val
                NPhi = NX_val
                print(f"[DEBUG] Detected old POLAR file: {NR} rows (radial) × {NPhi} columns (angular)")
            else:
                file_type = "cylindrical"
                NR = NZ_val
                NPhi = NX_val
                print(f"[DEBUG] Detected old CYLINDRICAL file: {NR} rows (NZ) × {NPhi} columns (NX)")
        else:
            # Assume cylindrical if can't determine
            file_type = "cylindrical"
            NR = NZ_val
            NPhi = NX_val
            print(f"[DEBUG] Assumed CYLINDRICAL file: {NR} rows × {NPhi} columns")

    # Support even older files with ERDVE_RHO/ERDVE_PHI
    elif "ERDVE_RHO" in params and "ERDVE_PHI" in params:
        file_type = "polar"
        NR = int(params["ERDVE_RHO"])  # Radial points (rows)
        NPhi = int(params["ERDVE_PHI"])  # Angular points (columns)
        print(f"[DEBUG] Detected legacy POLAR file: {NR} rows × {NPhi} columns")

    if file_type is None or NR is None or NPhi is None:
        print("[ERROR] Cannot determine file type from header")
        print(f"[ERROR] Available params: {params}")

        # Try to detect by looking at first data block
        print("[DEBUG] Attempting to auto-detect from data structure...")

        # Find first SNAPSHOT
        for i in range(len(lines)):
            if lines[i].strip().startswith("SNAPSHOT"):
                # Count data lines
                j = i + 1
                test_rows = []
                while j < len(lines) and j < i + 500:
                    line = lines[j].strip()
                    j += 1

                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("SNAPSHOT"):
                        break

                    try:
                        values = [float(x) for x in line.split()]
                        if values:
                            test_rows.append(values)
                    except ValueError:
                        pass

                if test_rows:
                    NR = len(test_rows)
                    NPhi = len(test_rows[0])
                    print(f"[DEBUG] Auto-detected from data: {NR} rows × {NPhi} columns")
                    file_type = "cylindrical"  # Default assumption
                    break

        if file_type is None:
            return params, []

    # Parse snapshots
    i = body_start
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("SNAPSHOT"):
            # Parse time
            parts = line.split("=")
            if len(parts) == 2:
                try:
                    t = float(parts[1])
                except ValueError:
                    t = np.nan
            else:
                t = np.nan

            i += 1
            u_data = []
            rows_read = 0

            # Read data rows
            while i < len(lines) and rows_read < NR:
                stripped = lines[i].strip()
                i += 1

                if not stripped or stripped.startswith("#"):
                    continue
                if stripped.startswith("SNAPSHOT"):
                    i -= 1
                    break

                str_vals = stripped.split()
                row_vals = []
                for s in str_vals:
                    try:
                        row_vals.append(float(s))
                    except ValueError:
                        pass

                # Only add row if it has the expected number of columns
                if len(row_vals) == NPhi:
                    u_data.append(row_vals)
                    rows_read += 1
                elif len(row_vals) > 0:
                    # Warn about row mismatch
                    if rows_read == 0:  # Only warn once per snapshot
                        print(f"[WARNING] Row has {len(row_vals)} values, expected {NPhi}")

            # Add snapshot if complete
            if len(u_data) == NR:
                u_array = np.array(u_data, dtype=float)
                if any(abs(snap["t"] - t) < 1e-10 for snap in snapshots):  # TODO: Leffover from past, refactor
                    print(f"[WARNING] Skipping duplicate snapshot at t={t}")
                else:
                    snapshots.append({"t": t, "u": u_array, "type": file_type})
            elif len(u_data) > 0:
                print(f"[WARNING] Incomplete snapshot at t={t}: got {len(u_data)} rows, expected {NR}")
        else:
            i += 1

    if not snapshots:
        print(f"[ERROR] No snapshots found in file: {path}")
        print(f"[DEBUG] Searched from line {body_start} to {len(lines)}")

        # Show first few lines after header for debugging
        print("[DEBUG] First 10 lines after header:")
        for i in range(body_start, min(body_start + 10, len(lines))):
            print(f"  Line {i}: {lines[i][:80].strip()}")
    else:
        print(f"[INFO] Successfully loaded {len(snapshots)} {file_type} snapshots from {path}")
        print(f"[INFO] Grid size: {NR} rows × {NPhi} columns")
        if snapshots:
            print(f"[INFO] First snapshot: t = {snapshots[0]['t']}, shape = {snapshots[0]['u'].shape}")

    params["file_type"] = file_type
    params["NR"] = NR
    params["NPhi"] = NPhi
    return params, snapshots


def match_snapshots_by_time(snapshots1: List[Dict],
                            snapshots2: List[Dict],
                            tolerance: float = 1e-6) -> List[Tuple[int, int]]:
    matches = []

    for i1, snap1 in enumerate(snapshots1):
        t1 = snap1['t']

        # Find closest time in snapshots2
        best_match = None
        best_diff = float('inf')

        for i2, snap2 in enumerate(snapshots2):
            t2 = snap2['t']
            diff = abs(t1 - t2)
            if diff < best_diff:
                best_diff = diff
                best_match = i2

        # Consider it a match if times are very close
        if best_match is not None and best_diff < max(tolerance, abs(t1) * 0.001):
            matches.append((i1, best_match))

    return matches


def get_data_statistics(data: np.ndarray) -> Dict[str, float]:
    return {
        'min': np.nanmin(data),
        'max': np.nanmax(data),
        'mean': np.nanmean(data),
        'std': np.nanstd(data)
    }


def load_spatiotemporal_file(
        snapshot_filename: str,
        default_T: float,
        default_L: float,
) -> Optional[Dict]:
    base = os.path.splitext(snapshot_filename)[0]
    spatio_path = base + "_spatiotemporal.dat"

    if not os.path.exists(spatio_path):
        return None

    data_lines = []
    header_info = {}

    try:
        with open(spatio_path, 'r', encoding='utf-8') as f:
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

        return {
            'data': np.array(data_lines),
            'T': float(header_info.get('T', default_T)),
            'L': float(header_info.get('L', default_L)),
            'filename': spatio_path,
        }

    except Exception:
        return None


def load_snapshots_3d(path: str):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Split header from body
    header_lines = []
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("SNAPSHOT"):
            body_start = i
            break
        header_lines.append(line)

    params = parse_header(header_lines)
    snapshots = []

    NRho = int(params.get("N_RHO", params.get("NRho", params.get("ERDVE_RHO", params.get("NR", 0)))))
    NPhi = int(params.get("N_PHI", params.get("NPhi", params.get("ERDVE_PHI", 0))))
    NZ = int(params.get("N_Z", params.get("NZ", 0)))

    print(f"3D Loader: Detected dimensions NRho={NRho}, NPhi={NPhi}, NZ={NZ}")

    if NRho == 0 or NPhi == 0 or NZ == 0:
        print("Error: Could not determine 3D grid dimensions from header")
        print(f"Available parameters: {list(params.keys())}")
        return params, []

    expected_lines = NRho * NZ

    i = body_start
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("SNAPSHOT"):
            parts = line.split("=")
            t = float(parts[1]) if len(parts) == 2 else 0.0
            print(f"Reading snapshot at t={t}")
            i += 1

            u_data = np.zeros((NRho, NPhi, NZ))
            lines_read = 0
            stripped = ""

            for rho in range(NRho):
                for z in range(NZ):
                    while i < len(lines):
                        stripped = lines[i].strip()
                        i += 1
                        if not stripped or stripped.startswith("#"):
                            continue
                        if stripped.startswith("SNAPSHOT"):
                            i -= 1
                            break
                        try:
                            values = [float(x) for x in stripped.split()]
                            if len(values) == NPhi:
                                u_data[rho, :, z] = values
                                lines_read += 1
                                break
                            else:
                                print(f"Warning: Expected {NPhi} values, got {len(values)} at rho={rho}, z={z}")
                        except ValueError as e:
                            print(f"Error parsing line: {e}")
                    if stripped.startswith("SNAPSHOT"):
                        break
                if stripped.startswith("SNAPSHOT"):
                    break

            print(f"  Read {lines_read}/{expected_lines} data lines")
            if lines_read > 0:
                snapshots.append({"t": t, "u": u_data, "type": "volume3d"})
        else:
            i += 1

    print(f"Loaded {len(snapshots)} 3D volumetric snapshots")
    return params, snapshots


def format_volume_info(params: Dict[str, float],
                       snapshots: List[Dict],
                       current_idx: int) -> str:
    if not snapshots:
        return "Load a 3D volume file to begin"

    data = snapshots[current_idx]['u']
    NRho, NPhi, NZ = data.shape

    lines = []

    lines.append("=== CURRENT SNAPSHOT ===")
    lines.append(f"Snapshot: {current_idx + 1}/{len(snapshots)}")
    lines.append(f"Time: {snapshots[current_idx]['t']:.6f}")
    lines.append(f"Grid: {NRho} × {NPhi} × {NZ} (ρ × φ × z)")
    lines.append(f"Data range: [{np.nanmin(data):.3f}, {np.nanmax(data):.3f}]")
    lines.append("")

    lines.append("=== MODEL PARAMETERS ===")

    chemotaxis_keys = [
        ("D_U", "Cell diffusion"),
        ("CHI", "Chemotactic sensitivity"),
        ("ALPHA", "Birth rate"),
        ("BETA", "Death rate"),
        ("D_W", "Chemical diffusion"),
        ("GAMMA", "Decay rate"),
        ("W_0", "Initial chemical"),
    ]
    lines.append("Chemotaxis:")
    for key, _ in chemotaxis_keys:
        if key in params:
            lines.append(f"  {key:8s} = {params[key]:8.4f}")
    lines.append("")

    domain_keys = [
        ("R", "Cylinder radius"),
        ("H", "Cylinder height"),
        ("L", "Circumference (2πR)"),
    ]
    lines.append("Domain:")
    for key, _ in domain_keys:
        if key in params:
            lines.append(f"  {key:8s} = {params[key]:8.4f}")
    lines.append("")

    grid_keys = [
        ("N_RHO", "Radial points"),
        ("N_PHI", "Angular points"),
        ("NZ", "Vertical points"),
        ("D_RHO", "Radial spacing"),
        ("D_PHI", "Angular spacing"),
        ("DZ", "Vertical spacing"),
    ]
    lines.append("Grid:")
    for key, desc in grid_keys:
        if key in params:
            lines.append(f"  {key:8s} = {params[key]:8.4f}  # {desc}")
    lines.append("")

    sim_keys = [
        ("T", "Total time"),
        ("dt", "Time step"),
        ("N_steps", "Total steps"),
        ("SAVE_EVERY_T", "Save interval"),
    ]
    lines.append("Simulation:")
    for key, desc in sim_keys:
        if key in params:
            val = params[key]
            if key == "N_steps":
                lines.append(f" {key:12s} = {int(val):8d} # {desc}")
            else:
                lines.append(f" {key:12s} = {val:8.6f} # {desc}")

    return "\n".join(lines)
