"""
launcher_tabbed.py

Main hub/launcher for the Chemotaxis Simulation Visualizer Suite.
All visualization modes accessible via tabs in a single window.
"""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QTabWidget, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class TabbedVisualizerHub(QMainWindow):
    def __init__(self):
        super().__init__()
        self.viewers = {}  # Store viewer instances
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Chemotaxis Simulation Visualizer Suite")
        self.setGeometry(100, 100, 1400, 900)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(False)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setUsesScrollButtons(True)
        
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setExpanding(False)
        tab_bar.setDrawBase(False)
        tab_bar.setElideMode(Qt.ElideNone)  # Don't truncate text
        
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: white;
            }
            QTabBar::tab {
                background: #e0e0e0;
                color: #333;
                padding: 10px 15px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                color: #4a90e2;
            }
            QTabBar::tab:hover:!selected {
                background: #d0d0d0;
            }
        """)
        
        self.add_welcome_tab()
        
        self.add_placeholder_tab("🔵 2D Polar Analysis", "viewers.polar_viewer_2d",
                                 "PolarViewer2D")
        self.add_placeholder_tab("📊 2D Side Analysis", "viewers.cylindrical_viewer_2d",
                                 "CylindricalViewer2D")
        self.add_placeholder_tab("🎨 3D Combined Image Analysis", "viewers.combined_viewer_2d",
                                 "CylinderVisualizerApp")
        self.add_placeholder_tab("🔮 3D Volume Viewer", "viewers.volume_viewer_3d",
                                 "VolumeViewer3D")
        self.add_placeholder_tab("📊 Spatiotemporal Analysis",
                                 "viewers.multiple_spatiotemporal_analyzer",
                                 "MultiSpatiotemporalViewer")
        self.add_placeholder_tab("🔬 2D Experiment Comparer", "viewers.experiment_comparer_2d",
                                 "ExperimentComparer2D")

        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        main_layout.addWidget(self.tab_widget)

        self.show()


    def add_welcome_tab(self):
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title_label = QLabel("Chemotaxis Simulation Analysis and Visualization Tool")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Select a visualization mode from the tabs above")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(subtitle_label)

        layout.addSpacing(20)

        # Overview of modes
        overview_text = """
        <div style='font-size: 13px; line-height: 1.8;'>
        <h3 style='color: #4a90e2;'>Available Visualization Modes:</h3>
        
        <p><b>🔵 2D Polar View (Top Disk):</b><br/>
        Polar coordinate visualization with snapshots. Used for radial patterns and angular distributions.</p>
        
        <p><b>📊 2D Cylindrical View (Side Surface):</b><br/>
        Cylindrical unwrapped data with vertical pattern analysis.</p>
        
        <p><b>🎨 3D Combined View:</b><br/>
        Interactive 3D visualization with full cylinder geometry including top/bottom caps and real-time controls.</p>
        
        <p><b>🔮 3D Volume Viewer:</b><br/>
        Full volumetric 3D visualization with slicing planes and adaptive rendering capabilities.</p>
        
        <p><b>📊 Spatiotemporal Analyzer:</b><br/>
        Advanced spatiotemporal data analysis tool supporting multiple images plotting at the same time.</p>

        <p><b>🔬 2D Experiment Comparer:</b><br/> Side-by-side grid viewer for polar (top disk) and cylindrical (side 
        surface) snapshots. Add any mix of top/side data and compare across experiments.</p>
        
        <p style='margin-top: 30px; padding: 15px; background: #f0f8ff; border-left: 4px solid #4a90e2;'> <b>💡 
        Tip:</b> Click on any tab above to load that visualization mode. The viewer will initialize when you first 
        access it. </p> </div>"""

        overview_label = QLabel(overview_text)
        overview_label.setWordWrap(True)
        overview_label.setTextFormat(Qt.RichText)
        layout.addWidget(overview_label)

        layout.addStretch()

        self.tab_widget.addTab(welcome_widget, "🏠 Welcome")

    def add_placeholder_tab(self, tab_name: str, module_name: str, class_name: str):
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignCenter)

        loading_label = QLabel(f"Loading {tab_name}...")
        loading_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        loading_label.setFont(font)
        layout.addWidget(loading_label)

        # Store module info in the widget
        placeholder.module_name = module_name
        placeholder.class_name = class_name
        placeholder.tab_name = tab_name
        placeholder.is_placeholder = True

        self.tab_widget.addTab(placeholder, tab_name)

    def on_tab_changed(self, index: int):
        current_widget = self.tab_widget.widget(index)

        if hasattr(current_widget, 'is_placeholder') and current_widget.is_placeholder:
            self.load_viewer(index, current_widget)

    def load_viewer(self, tab_index: int, placeholder_widget):
        module_name = placeholder_widget.module_name
        class_name = placeholder_widget.class_name
        tab_name = placeholder_widget.tab_name

        try:
            module = __import__(module_name, fromlist=[class_name])
            viewer_class = getattr(module, class_name)

            original_show = viewer_class.show
            viewer_class.show = lambda self: None

            viewer_instance = viewer_class()

            viewer_class.show = original_show

            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)

            if isinstance(viewer_instance, QMainWindow):
                central_widget = viewer_instance.centralWidget()
                if central_widget is not None:
                    central_widget.setParent(container)
                    container_layout.addWidget(central_widget)

                    viewer_instance.hide()
                    self.viewers[tab_name + '_window'] = viewer_instance
                else:
                    raise Exception("Viewer has no central widget")
            else:
                viewer_instance.setParent(container)
                container_layout.addWidget(viewer_instance)

            self.viewers[tab_name] = container

            self.tab_widget.removeTab(tab_index)
            self.tab_widget.insertTab(tab_index, container, tab_name)
            self.tab_widget.setCurrentIndex(tab_index)

            print(f"✓ Loaded {tab_name}")

        except ImportError as e:
            QMessageBox.warning(
                self, "Module Not Found",
                f"Could not load {tab_name}:\n{str(e)}\n\n"
                f"Make sure {module_name}.py is in the current directory."
            )
            print(f"✗ Failed to load {tab_name}: {str(e)}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Error loading {tab_name}:\n{str(e)}"
            )
            print(f"✗ Error loading {tab_name}: {str(e)}")
            import traceback
            traceback.print_exc()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QWidget {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        }
    """)

    hub = TabbedVisualizerHub()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
