--- fsm_designer_project/ui/ui_builder.py
+++ fsm_designer_project/ui/ui_builder.py
@@ -8,7 +8,7 @@
 from ..utils import get_standard_icon
 from ..utils.config import COLOR_BORDER_LIGHT
 from ..assets.target_profiles import TARGET_PROFILES
-from .widgets.ribbon_toolbar import ProfessionalRibbon, ProfessionalGroup
-from .widgets.modern_status_bar import ModernStatusBar, StatusSegment
+from .widgets.ribbon_toolbar import ProfessionalRibbon, ProfessionalGroup, GlobalSearchHandler
+from .widgets.modern_status_bar import ModernStatusBar
 from .graphics.graphics_scene import MinimapView
 from ..managers.data_dictionary_manager import DataDictionaryManager
 from ..managers.c_simulation_manager import CSimulationManager
@@ -216,33 +216,8 @@
         mw.setStatusBar(ModernStatusBar(mw))
         status_bar = mw.statusBar()
         if isinstance(status_bar, ModernStatusBar):
-             mw.main_op_status_label = status_bar.status_indicator.text_label
-             pass
+            mw.main_op_status_label = status_bar.status_indicator.text_label
         else:
-            status_bar = QStatusBar(mw)
-            mw.setStatusBar(status_bar)
             mw.main_op_status_label = QLabel("Ready")
-            status_bar.addWidget(mw.main_op_status_label, 1)
-            mw.mode_status_segment = StatusSegment(QStyle.StandardPixmap.SP_ArrowRight, "Sel", "Select", "Interaction Mode", "InteractionModeStatusLabel")
-            mw.zoom_status_segment = StatusSegment(QStyle.StandardPixmap.SP_FileDialogInfoView, "Zoom", "100%", "Zoom Level", "ZoomStatusLabel")
-            mw.pysim_status_segment = StatusSegment(QStyle.StandardPixmap.SP_MediaStop, "PySim", "Idle", "Python Sim Status", "PySimStatusLabel")
-            mw.matlab_status_segment = StatusSegment(QStyle.StandardPixmap.SP_MessageBoxWarning, "MATLAB", "Not Conn.", "MATLAB Status", "MatlabStatusLabel")
-            mw.net_status_segment = StatusSegment(QStyle.StandardPixmap.SP_MessageBoxQuestion, "Net", "Checking...", "Internet Status", "InternetStatusLabel")
-            status_bar.addPermanentWidget(mw.mode_status_segment)
-            status_bar.addPermanentWidget(mw.zoom_status_segment)
-            status_bar.addPermanentWidget(mw.pysim_status_segment)
-            status_bar.addPermanentWidget(mw.matlab_status_segment)
-            status_bar.addPermanentWidget(mw.net_status_segment)
-            mw.resource_monitor_widget = QWidget()
-            res_layout = QHBoxLayout(mw.resource_monitor_widget)
-            res_layout.setContentsMargins(4, 0, 4, 0)
-            res_layout.setSpacing(5)
-            mw.cpu_status_label = QLabel("CPU: --%")
-            res_layout.addWidget(mw.cpu_status_label)
-            mw.ram_status_label = QLabel("RAM: --%")
-            res_layout.addWidget(mw.ram_status_label)
-            mw.gpu_status_label = QLabel("GPU: N/A")
-            res_layout.addWidget(mw.gpu_status_label)
-            status_bar.addPermanentWidget(mw.resource_monitor_widget)
-            mw.resource_monitor_widget.setVisible(False)
+            status_bar.addWidget(mw.main_op_status_label, 1) # Fallback
             mw.progress_bar = QProgressBar()
             mw.progress_bar.setRange(0, 0)
             mw.progress_bar.hide()
             mw.progress_bar.setMaximumWidth(120)
             mw.progress_bar.setTextVisible(False)
             status_bar.addPermanentWidget(mw.progress_bar)