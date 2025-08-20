import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter, CSVExporter

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QHBoxLayout, QPushButton, QListWidgetItem,
    QLineEdit, QLabel, QCheckBox, QSpinBox, QFileDialog, QColorDialog, QMenu
)
from PyQt6.QtCore import pyqtSlot, Qt, QTimer, QPoint
from PyQt6.QtGui import QColor, QCursor

from ...core.simulation_logger import SimulationDataLogger
from ...utils import config
try:
    from ...utils.theme_config import theme_config
except Exception:
    theme_config = None


class SimulationPlotWidget(QWidget):
    """
    A modern scope widget with:
    - Variable filter + checkable list
    - Legend/grid/antialias toggles
    - Pause updates
    - Time window (ticks) + downsample control
    - Dual Y-axes (left/right) with context menu
    - Export to CSV/PNG
    - Crosshair readout
    - Preference persistence via config
    """
    def __init__(self, data_logger: SimulationDataLogger, parent=None):
        super().__init__(parent)
        self.data_logger = data_logger

        # var_name -> {"item": PlotDataItem, "axis": "left"/"right", "color": QColor}
        self.plotted_variables: dict[str, dict] = {}

        # Preferences
        self._cfg_prefix = "ui.plot"
        self._paused = False
        self._window_ticks = int(self._cfg_get("window_ticks", 1000))
        self._downsample_step = int(self._cfg_get("downsample_step", 1))
        self._show_legend = bool(self._cfg_get("legend", True))
        self._show_grid = bool(self._cfg_get("grid", True))
        self._antialias = bool(self._cfg_get("antialias", True))
        self._auto_range_y = bool(self._cfg_get("auto_range_y", True))

        # Color cycle
        self._color_cycle = [
            "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
            "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
            "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000",
            "#aaffc3", "#808000", "#ffd8b1", "#000075", "#808080"
        ]
        self._color_index = 0

        # Throttle UI updates
        self._update_pending = False
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(33)  # ~30 FPS
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_update)

        # UI
        self._build_ui()
        self._apply_plot_config()

    # ------------------ UI construction ------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.pause_cb = QCheckBox("Pause")
        self.pause_cb.setToolTip("Pause live updates")
        self.pause_cb.stateChanged.connect(self._on_pause_changed)
        toolbar.addWidget(self.pause_cb)

        self.auto_range_cb = QCheckBox("Auto-Range Y")
        self.auto_range_cb.setChecked(self._auto_range_y)
        self.auto_range_cb.setToolTip("Automatically adjust Y range")
        self.auto_range_cb.stateChanged.connect(self._on_auto_range_changed)
        toolbar.addWidget(self.auto_range_cb)

        self.grid_cb = QCheckBox("Grid")
        self.grid_cb.setChecked(self._show_grid)
        self.grid_cb.setToolTip("Show grid")
        self.grid_cb.stateChanged.connect(self._on_grid_changed)
        toolbar.addWidget(self.grid_cb)

        self.legend_cb = QCheckBox("Legend")
        self.legend_cb.setChecked(self._show_legend)
        self.legend_cb.setToolTip("Show legend")
        self.legend_cb.stateChanged.connect(self._on_legend_changed)
        toolbar.addWidget(self.legend_cb)

        self.antialias_cb = QCheckBox("Antialias")
        self.antialias_cb.setChecked(self._antialias)
        self.antialias_cb.setToolTip("Enable antialiasing (smoother curves, more CPU)")
        self.antialias_cb.stateChanged.connect(self._on_antialias_changed)
        toolbar.addWidget(self.antialias_cb)

        toolbar.addSpacing(12)

        toolbar.addWidget(QLabel("Window:"))
        self.window_spin = QSpinBox()
        self.window_spin.setRange(0, 1_000_000)
        self.window_spin.setValue(self._window_ticks)
        self.window_spin.setToolTip("Show only the last N ticks (0 = all)")
        self.window_spin.valueChanged.connect(self._on_window_changed)
        toolbar.addWidget(self.window_spin)

        toolbar.addWidget(QLabel("Step:"))
        self.downsample_spin = QSpinBox()
        self.downsample_spin.setRange(1, 10_000)
        self.downsample_spin.setValue(self._downsample_step)
        self.downsample_spin.setToolTip("Downsample factor (plot every Nth point)")
        self.downsample_spin.valueChanged.connect(self._on_downsample_changed)
        toolbar.addWidget(self.downsample_spin)

        self.fit_btn = QPushButton("Fit View")
        self.fit_btn.setToolTip("Auto-range both axes to fit data")
        self.fit_btn.clicked.connect(self._fit_view)
        toolbar.addWidget(self.fit_btn)

        toolbar.addStretch()

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.clicked.connect(self._export_png)
        toolbar.addWidget(self.export_png_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(self.export_csv_btn)

        main_layout.addLayout(toolbar)

        # Plot + control panel
        center_row = QHBoxLayout()
        center_row.setSpacing(8)
        main_layout.addLayout(center_row)

        # Plot area
        # Theme-aware colors (fallback to white/black)
        bg = "#1e1e1e"
        fg = "#dddddd"
        try:
            if theme_config:
                bg = getattr(theme_config, "COLOR_PLOT_BG", getattr(theme_config, "COLOR_BG_ELEVATED", bg))
                fg = getattr(theme_config, "COLOR_PLOT_FG", getattr(theme_config, "COLOR_TEXT_PRIMARY", fg))
        except Exception:
            pass

        pg.setConfigOption('background', bg)
        pg.setConfigOption('foreground', fg)
        pg.setConfigOptions(antialias=self._antialias)

        self.plot_widget = pg.PlotWidget()
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setLabel('bottom', 'Simulation Ticks')
        self.plot_item.setLabel('left', 'Value')
        self.plot_item.showGrid(x=self._show_grid, y=self._show_grid)
        center_row.addWidget(self.plot_widget, 4)

        # Right Y axis (for alternate scale)
        self.plot_item.showAxis('right')
        self.plot_item.getAxis('right').setLabel('Value (R)')
        self.right_vb = pg.ViewBox()
        self.plot_item.scene().addItem(self.right_vb)
        self.plot_item.getAxis('right').linkToView(self.right_vb)
        self.right_vb.setXLink(self.plot_item)
        # Keep right VB aligned with main VB
        self.plot_item.getViewBox().sigResized.connect(self._update_views)
        self._update_views()

        # Legend (created lazily to avoid duplicate)
        self.legend = None
        if self._show_legend:
            self.legend = self.plot_item.addLegend()

        # Crosshair
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color="#888", width=1))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(color="#888", width=1))
        self.plot_item.addItem(self.v_line, ignoreBounds=True)
        self.plot_item.addItem(self.h_line, ignoreBounds=True)
        self.coord_label = QLabel("x: -, y: -")
        self.coord_label.setStyleSheet("color: #aaa;")
        center_row.addWidget(self.coord_label, 0, Qt.AlignmentFlag.AlignTop)
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        # Control panel
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(6)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter variables (name or value type)")
        self.filter_edit.textChanged.connect(self._apply_filter)
        control_layout.addWidget(self.filter_edit)

        self.variable_list = QListWidget()
        self.variable_list.itemClicked.connect(self.on_variable_toggled)
        self.variable_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.variable_list.customContextMenuRequested.connect(self._on_variable_context_menu)
        control_layout.addWidget(self.variable_list, 1)

        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        btn_row.addWidget(self.select_all_btn)

        self.unselect_all_btn = QPushButton("Unselect All")
        self.unselect_all_btn.clicked.connect(self._unselect_all)
        btn_row.addWidget(self.unselect_all_btn)

        self.clear_btn = QPushButton("Clear Plot")
        self.clear_btn.clicked.connect(self.clear_all_plots)
        btn_row.addWidget(self.clear_btn)
        control_layout.addLayout(btn_row)

        center_row.addWidget(control_panel, 2)

    # ------------------ Configuration helpers ------------------
    def _cfg_get(self, key, default=None):
        full = f"{self._cfg_prefix}.{key}"
        try:
            if hasattr(config, "get"):
                return config.get(full, default)
            return config.get(full, default) if hasattr(config, "__getitem__") else default
        except Exception:
            return default

    def _cfg_set(self, key, value):
        full = f"{self._cfg_prefix}.{key}"
        try:
            if hasattr(config, "set"):
                config.set(full, value)
            elif hasattr(config, "__setitem__"):
                config[full] = value
            if hasattr(config, "save"):
                config.save()
        except Exception:
            pass

    def _apply_plot_config(self):
        # Legend visibility
        if self._show_legend and self.legend is None:
            self.legend = self.plot_item.addLegend()
        if self.legend:
            self.legend.setVisible(self._show_legend)

        # Grid
        self.plot_item.showGrid(x=self._show_grid, y=self._show_grid)

        # Antialias
        pg.setConfigOptions(antialias=self._antialias)

    # ------------------ Variable List & Plotting ------------------
    def update_variable_list(self, variables: dict):
        """
        Populate the list of plottable variables (booleans treated as 0/1).
        Preserves checked state for currently-plotted variables.
        """
        checked = set(self.plotted_variables.keys())
        filter_text = self.filter_edit.text().strip().lower()

        self.variable_list.clear()
        for var_name, value in variables.items():
            if not isinstance(value, (int, float, bool)):
                continue
            if filter_text and (filter_text not in var_name.lower()):
                continue
            item = QListWidgetItem(var_name, self.variable_list)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if var_name in checked else Qt.CheckState.Unchecked)

    @pyqtSlot(QListWidgetItem)
    def on_variable_toggled(self, item: QListWidgetItem):
        var_name = item.text()
        if item.checkState() == Qt.CheckState.Checked:
            self.add_plot(var_name)
        else:
            self.remove_plot(var_name)

    def add_plot(self, var_name: str, axis: str = "left", color: QColor | None = None):
        if var_name in self.plotted_variables:
            # Optionally move to axis or recolor
            entry = self.plotted_variables[var_name]
            if axis != entry["axis"]:
                self._move_plot_axis(var_name, axis)
            if color and color != entry["color"]:
                entry["color"] = color
                entry["item"].setPen(pg.mkPen(color, width=2))
            return

        if color is None:
            color = QColor(self._color_cycle[self._color_index % len(self._color_cycle)])
            self._color_index += 1

        pen = pg.mkPen(color, width=2)
        plot_item = pg.PlotDataItem(name=var_name, pen=pen)
        plot_item.setClipToView(True)

        if axis == "right":
            self.right_vb.addItem(plot_item)
        else:
            self.plot_item.addItem(plot_item)

        self.plotted_variables[var_name] = {"item": plot_item, "axis": axis, "color": color}

        if self.legend and self._show_legend:
            # Legend auto-tracks items in the plotItem; for right-axis items, add manually
            try:
                self.legend.addItem(plot_item, var_name)
            except Exception:
                pass

        # Trigger draw
        self.update_plot_data()

    def _move_plot_axis(self, var_name: str, axis: str):
        entry = self.plotted_variables.get(var_name)
        if not entry:
            return
        item = entry["item"]
        # Remove from current view
        try:
            if entry["axis"] == "right":
                self.right_vb.removeItem(item)
            else:
                self.plot_item.removeItem(item)
        except Exception:
            pass
        # Add to new view
        if axis == "right":
            self.right_vb.addItem(item)
        else:
            self.plot_item.addItem(item)
        entry["axis"] = axis
        self._update_views()

    def remove_plot(self, var_name: str):
        entry = self.plotted_variables.pop(var_name, None)
        if not entry:
            return
        item = entry["item"]
        try:
            if entry["axis"] == "right":
                self.right_vb.removeItem(item)
            else:
                self.plot_item.removeItem(item)
        except Exception:
            pass

        if self.legend:
            try:
                self.legend.removeItem(var_name)
            except Exception:
                pass

    def clear_all_plots(self):
        for var in list(self.plotted_variables.keys()):
            self.remove_plot(var)
        # Uncheck all items
        for i in range(self.variable_list.count()):
            self.variable_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    # ------------------ Updating data ------------------
    def update_plot_data(self):
        if self._paused:
            return
        if not self._update_pending:
            self._update_pending = True
            self._update_timer.start()

    def _perform_update(self):
        self._update_pending = False
        if not self.plotted_variables:
            return

        # Determine global max tick for windowing and x-range
        global_max_tick = None

        for var_name, entry in self.plotted_variables.items():
            data = self.data_logger.get_data_for_variable(var_name)
            if not data:
                continue

            # Windowing
            if self._window_ticks > 0:
                max_tick = data[-1][0]
                min_tick = max_tick - self._window_ticks
                data = [d for d in data if d[0] >= min_tick]
            else:
                max_tick = data[-1][0]

            if (global_max_tick is None) or (max_tick > global_max_tick):
                global_max_tick = max_tick

            # Downsample
            if self._downsample_step > 1:
                data = data[::self._downsample_step]

            ticks, values = zip(*data) if data else ([], [])
            # Coerce booleans to ints for plotting
            values = [int(v) if isinstance(v, bool) else v for v in values]

            entry["item"].setData(ticks, values)

        # Keep x-range aligned to last points (for windowed mode)
        if self._window_ticks > 0 and global_max_tick is not None:
            self.plot_item.setXRange(global_max_tick - self._window_ticks, global_max_tick, padding=0.02)

        # Manage Y auto-range
        vb = self.plot_item.getViewBox()
        if self._auto_range_y:
            vb.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
            self.right_vb.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        else:
            vb.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
            self.right_vb.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)

    # ------------------ Toolbar handlers ------------------
    def _on_pause_changed(self, state):
        self._paused = bool(state)
        if not self._paused:
            self.update_plot_data()

    def _on_auto_range_changed(self, state):
        self._auto_range_y = bool(state)
        self._cfg_set("auto_range_y", self._auto_range_y)
        self.update_plot_data()

    def _on_grid_changed(self, state):
        self._show_grid = bool(state)
        self._cfg_set("grid", self._show_grid)
        self.plot_item.showGrid(x=self._show_grid, y=self._show_grid)

    def _on_legend_changed(self, state):
        self._show_legend = bool(state)
        self._cfg_set("legend", self._show_legend)
        if self.legend is None and self._show_legend:
            self.legend = self.plot_item.addLegend()
            # Re-add current items
            for name, entry in self.plotted_variables.items():
                try:
                    self.legend.addItem(entry["item"], name)
                except Exception:
                    pass
        if self.legend:
            self.legend.setVisible(self._show_legend)

    def _on_antialias_changed(self, state):
        self._antialias = bool(state)
        self._cfg_set("antialias", self._antialias)
        pg.setConfigOptions(antialias=self._antialias)
        self.update_plot_data()

    def _on_window_changed(self, value):
        self._window_ticks = int(value)
        self._cfg_set("window_ticks", self._window_ticks)
        self.update_plot_data()

    def _on_downsample_changed(self, value):
        self._downsample_step = max(1, int(value))
        self._cfg_set("downsample_step", self._downsample_step)
        self.update_plot_data()

    def _fit_view(self):
        # Fit both left and right Y axes
        self.plot_item.getViewBox().autoRange()
        self.right_vb.autoRange()

    # ------------------ Export ------------------
    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Plot as PNG", "scope.png", "PNG Image (*.png)")
        if not path:
            return
        try:
            exp = ImageExporter(self.plot_item)
            exp.export(path)
        except Exception as e:
            print(f"Error exporting PNG: {e}")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Plot Data (CSV)", "scope.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            exp = CSVExporter(self.plot_item)
            exp.export(path)
        except Exception as e:
            print(f"Error exporting CSV: {e}")

    # ------------------ Crosshair & right axis layout ------------------
    def _on_mouse_moved(self, pos):
        vb = self.plot_item.getViewBox()
        if vb is None:
            return
        mouse_point = vb.mapSceneToView(pos)
        x = mouse_point.x()
        y = mouse_point.y()
        self.v_line.setPos(x)
        self.h_line.setPos(y)
        self.coord_label.setText(f"x: {x:.2f}, y: {y:.2f}")

    def _update_views(self):
        # Ensure right view box geometry follows the left one
        vb = self.plot_item.getViewBox()
        if vb is None:
            return
        self.right_vb.setGeometry(vb.sceneBoundingRect())
        self.right_vb.linkedViewChanged(vb, self.right_vb.XAxis)

    # ------------------ Variable list helpers ------------------
    def _apply_filter(self):
        text = self.filter_edit.text().strip().lower()
        for i in range(self.variable_list.count()):
            item = self.variable_list.item(i)
            item.setHidden(text not in item.text().lower())

    def _select_all(self):
        for i in range(self.variable_list.count()):
            item = self.variable_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)

    def _unselect_all(self):
        for i in range(self.variable_list.count()):
            item = self.variable_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)

    # Context menu for variables
    def _on_variable_context_menu(self, pos):
        item = self.variable_list.itemAt(pos)
        if not item:
            return
        var_name = item.text()
        plotted = var_name in self.plotted_variables

        menu = QMenu(self.variable_list)
        if not plotted:
            act_plot = menu.addAction("Plot")
        else:
            act_remove = menu.addAction("Remove from Plot")
            entry = self.plotted_variables[var_name]
            act_right_axis = menu.addAction("Assign to Right Axis")
            act_right_axis.setCheckable(True)
            act_right_axis.setChecked(entry["axis"] == "right")
            act_color = menu.addAction("Change Color…")
            act_show_only = menu.addAction("Show Only This")

        chosen = menu.exec(self.variable_list.mapToGlobal(pos))
        if not chosen:
            return

        if not plotted and chosen == act_plot:
            self.add_plot(var_name)
            item.setCheckState(Qt.CheckState.Checked)
        elif plotted and chosen == act_remove:
            self.remove_plot(var_name)
            item.setCheckState(Qt.CheckState.Unchecked)
        elif plotted and chosen == act_right_axis:
            new_axis = "right" if not self.plotted_variables[var_name]["axis"] == "right" else "left"
            self._move_plot_axis(var_name, new_axis)
        elif plotted and chosen == act_color:
            current = self.plotted_variables[var_name]["color"]
            color = QColorDialog.getColor(current, self, f"Select Color for {var_name}")
            if color.isValid():
                self.plotted_variables[var_name]["color"] = color
                self.plotted_variables[var_name]["item"].setPen(pg.mkPen(color, width=2))
        elif plotted and chosen == act_show_only:
            # Uncheck all others
            for i in range(self.variable_list.count()):
                it = self.variable_list.item(i)
                if it.text() != var_name:
                    it.setCheckState(Qt.CheckState.Unchecked)
            # Ensure current is checked
            item.setCheckState(Qt.CheckState.Checked)
            # Remove all other plotted
            for other in list(self.plotted_variables.keys()):
                if other != var_name:
                    self.remove_plot(other)