"""
export.py

Shared 2D and 3D gif's export utilities.
"""

from typing import Callable, List
import numpy as np

from PyQt5.QtWidgets import (QWidget, QFileDialog, QMessageBox,
                             QProgressDialog, QDialog)
from PyQt5.QtCore import Qt

from panels.dialogs import GifExportDialog


def export_gif_2d(
        parent: QWidget,
        snapshots: list,
        default_filename: str,
        render_frame: Callable[[dict, object, object, str, bool], None],
        cmap: str,
) -> None:
    if not snapshots:
        QMessageBox.warning(parent, "Error", "No snapshots loaded.")
        return

    # ── Configuration dialog ──────────────────────────────────────────────
    dialog = GifExportDialog(len(snapshots), parent)
    if dialog.exec_() != QDialog.Accepted:
        return
    settings = dialog.get_settings()

    # ── Save path ─────────────────────────────────────────────────────────
    filename, _ = QFileDialog.getSaveFileName(
        parent, "Save GIF Animation", default_filename,
        "GIF Files (*.gif);;All Files (*)"
    )
    if not filename:
        return

    start_idx = settings['start']
    end_idx = settings['end']
    skip = settings['skip']
    fps = settings['fps']
    dpi = settings['dpi']
    preserve_labels = settings['preserve_labels']

    frame_indices = list(range(start_idx, end_idx + 1, skip))

    try:
        import imageio
    except ImportError:
        QMessageBox.critical(
            parent, "Missing Dependency",
            "imageio library is required for GIF export.\n\n"
            "Install with: pip install imageio"
        )
        return

    progress = QProgressDialog(
        "Generating GIF frames...", "Cancel",
        0, len(frame_indices), parent
    )
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)

    frames: List[np.ndarray] = []

    try:
        for i, idx in enumerate(frame_indices):
            if progress.wasCanceled():
                progress.close()
                return

            progress.setValue(i)
            progress.setLabelText(f"Generating frame {i + 1}/{len(frame_indices)}...")

            snapshot = snapshots[idx]

            image = render_frame(snapshot, dpi, cmap, preserve_labels)
            frames.append(image)

        if not frames:
            progress.close()
            return

        progress.setLabelText("Saving GIF file...")
        progress.setValue(len(frame_indices))

        imageio.mimsave(filename, frames, fps=fps, loop=0)
        progress.close()

        QMessageBox.information(
            parent, "Success",
            f"GIF saved successfully!\n\n"
            f"File: {filename}\n"
            f"Frames: {len(frames)}\n"
            f"FPS: {fps}\n"
            f"Duration: {len(frames) / fps:.1f}s"
        )

    except Exception as e:
        progress.close()
        QMessageBox.critical(parent, "Error", f"Failed to create GIF:\n{str(e)}")
        import traceback
        traceback.print_exc()


def export_gif_3d(
        parent,
        snapshots: list,
        render_frame,
        hide_2d_actors,
        restore_2d_actors,
        default_filename: str = "animation.gif",
) -> None:
    if not snapshots:
        QMessageBox.warning(parent, "Error", "No snapshots loaded for GIF export.")
        return

    dialog = GifExportDialog(len(snapshots), parent)
    if dialog.exec_() != QDialog.Accepted:
        return
    settings = dialog.get_settings()

    filename, _ = QFileDialog.getSaveFileName(
        parent, "Save GIF Animation", default_filename,
        "GIF Files (*.gif);;All Files (*)"
    )
    if not filename:
        return

    start_idx = settings['start']
    end_idx = settings['end']
    skip = settings['skip']
    fps = settings['fps']
    preserve_title = settings['preserve_title']
    frame_indices = list(range(start_idx, end_idx + 1, skip))

    try:
        import imageio
    except ImportError:
        QMessageBox.critical(
            parent, "Missing Dependency",
            "imageio is required for GIF export.\n\nInstall with: pip install imageio"
        )
        return

    progress = QProgressDialog(
        "Generating 3D Volume GIF frames...", "Cancel",
        0, len(frame_indices), parent
    )
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)

    frames = []
    try:
        for i, idx in enumerate(frame_indices):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            progress.setLabelText(f"Rendering frame {i + 1}/{len(frame_indices)}...")

            backup_2d = hide_2d_actors() if not preserve_title else []
            image = render_frame(idx)
            frames.append(image)
            if not preserve_title:
                restore_2d_actors(backup_2d)

        if not progress.wasCanceled() and frames:
            progress.setLabelText("Saving GIF file...")
            progress.setValue(len(frame_indices))
            imageio.mimsave(filename, frames, fps=fps, loop=0)
            progress.close()
            QMessageBox.information(
                parent, "Success",
                f"3D Volume GIF saved!\n\n"
                f"File: {filename}\n"
                f"Frames: {len(frames)}  FPS: {fps}\n"
                f"Duration: {len(frames) / fps:.1f}s"
            )
        else:
            progress.close()

    except Exception as e:
        progress.close()
        QMessageBox.critical(parent, "Error", f"Failed to create GIF:\n{str(e)}")
        import traceback
        traceback.print_exc()
