# fsm_designer_project/ui/widgets/modern_welcome_screen.py
"""
Modern welcome screen with enhanced visuals and animations and pro UX.
"""

import os
import platform
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect,
    QScrollArea, QGridLayout, QStyle, QCheckBox, QMenu, QLineEdit, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, PYQT_VERSION_STR,
    QEvent
)
from PyQt6.QtGui import (
    QFont, QIcon, QPixmap, QPainter, QBrush, QColor, QLinearGradient, QAction,
    QCursor, QDesktopServices, QPageSize, QFontMetrics, QGuiApplication, QTransform, QKeyEvent, QMouseEvent, QDragEnterEvent, QDropEvent, QEnterEvent, QCloseEvent, QShowEvent, QHideEvent, QFocusEvent, QPaintEvent, QPalette, QImage,
    QPainterPath
)
from PyQt6.QtCore import QUrl

from ...utils import get_standard_icon
from ...utils.theme_config import theme_config
from ...utils import config


def _reveal_in_file_manager(path: str):
    """Cross-platform best effort to reveal a file in the system file manager."""
    try:
        if platform.system() == "Windows":
            if os.path.isdir(path):
                os.startfile(path)
            else:
                os.system(f'explorer /select,"{os.path.normpath(path)}"')
        elif platform.system() == "Darwin":
            if os.path.isdir(path):
                os.system(f'open "{path}"')
            else:
                os.system(f'open -R "{path}"')
        else:
            # Linux and others: open folder
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            os.system(f'xdg-open "{folder}"')
    except Exception:
        try:
            # Fallback: open folder generically
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        except Exception:
            pass


class ActionCard(QFrame):
    """Modern action card with hover/focus effects, keyboard activation, and subtle animation."""
    clicked = pyqtSignal()

    def __init__(self, title, description, icon, parent=None):
        super().__init__(parent)
        self.title = title
        self.setAccessibleName(f"Action Card: {title}")
        self.init_ui(title, description, icon)

    def init_ui(self, title, description, icon):
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(280, 120)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Icon
        self.icon_label = QLabel()
        if isinstance(icon, QIcon):
            self.icon_label.setPixmap(icon.pixmap(48, 48))
        else:
            self.icon_label.setPixmap(self.create_gradient_icon())
        self.icon_label.setFixedSize(48, 48)
        layout.addWidget(self.icon_label)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)

        self.title_label = QLabel(title)
        self.title_label.setAccessibleName(f"{title} title")
        text_layout.addWidget(self.title_label)

        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setAccessibleName(f"{title} description")
        text_layout.addWidget(self.desc_label)
        text_layout.addStretch()

        layout.addLayout(text_layout)

        # --- FIX: Properly manage graphics effects ---
        # Create a container widget that will hold the effects. This prevents
        # one effect from implicitly deleting the other when set on the same widget.
        effect_container = QWidget(self)
        effect_container.setGeometry(self.rect())
        effect_container.lower() # Ensure it's behind other widgets if needed

        # Shadow effect
        self.shadow = QGraphicsDropShadowEffect(effect_container)
        self.shadow.setBlurRadius(10)
        self.shadow.setColor(QColor(0, 0, 0, 40))
        self.shadow.setOffset(0, 2)
        effect_container.setGraphicsEffect(self.shadow)

        # Opacity effect for intro fade-in
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        # --- END FIX ---

        self.update_styles(hover=False, focused=False)

    def create_gradient_icon(self):
        pix = QPixmap(48, 48)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, 48, 48)
        gradient.setColorAt(0, QColor(theme_config.COLOR_ACCENT_PRIMARY))
        gradient.setColorAt(1, QColor(theme_config.COLOR_ACCENT_SECONDARY))
        p.setBrush(QBrush(gradient))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 48, 48, 8, 8)
        p.end()
        return pix

    def update_styles(self, hover: bool, focused: bool):
        if hover or focused:
            self.setStyleSheet(f"""
                ActionCard {{
                    background-color: {theme_config.COLOR_BACKGROUND_LIGHT};
                    border: 2px solid {theme_config.COLOR_ACCENT_PRIMARY};
                    border-radius: 8px;
                }}
            """)
            self.shadow.setBlurRadius(20)
            self.shadow.setOffset(0, 4)
        else:
            self.setStyleSheet("""
                ActionCard {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 8px;
                }
            """)
            self.shadow.setBlurRadius(10)
            self.shadow.setOffset(0, 2)

        self.title_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_PRIMARY}; font-size: 12pt; font-weight: bold;")
        self.desc_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_SECONDARY}; font-size: 9pt;")

    def enterEvent(self, e: QEnterEvent):
        super().enterEvent(e)
        self.update_styles(True, self.hasFocus())

    def leaveEvent(self, e: QEvent):
        super().leaveEvent(e)
        self.update_styles(False, self.hasFocus())

    def focusInEvent(self, e: QFocusEvent):
        super().focusInEvent(e)
        self.update_styles(True, True)

    def focusOutEvent(self, e: QFocusEvent):
        super().focusOutEvent(e)
        self.update_styles(False, False)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(e)

    # API to support parent intro animation
    def set_intro_opacity(self, value: float):
        if not hasattr(self, "opacity_effect") or self.opacity_effect is None:
            self.opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(value)


class RecentFileItem(QFrame):
    """Recent file item with preview, context menu, and path eliding."""
    clicked = pyqtSignal(str)
    revealRequested = pyqtSignal(str)
    removeRequested = pyqtSignal(str)
    copyPathRequested = pyqtSignal(str)

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setAccessibleName(f"Recent Project: {file_path}")
        self._exists = os.path.exists(file_path)
        self.init_ui()
        self.update_styles()

    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon = get_standard_icon(QStyle.StandardPixmap.SP_DirIcon if os.path.isdir(self.file_path) else QStyle.StandardPixmap.SP_FileIcon)
        icon_label.setPixmap(icon.pixmap(32, 32))
        layout.addWidget(icon_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        project_dir = os.path.dirname(self.file_path)
        project_name = os.path.basename(project_dir) if self.file_path.endswith(config.PROJECT_FILE_EXTENSION) else os.path.basename(self.file_path)
        self.name_label = QLabel(project_name or "Untitled Project")

        # Build subtitle with elided path and modified time
        self.path_label = QLabel()
        self._update_path_and_time()

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.path_label)

        layout.addLayout(info_layout)
        layout.addStretch()

    def _update_path_and_time(self):
        path = os.path.dirname(self.file_path) if self.file_path.endswith(config.PROJECT_FILE_EXTENSION) else self.file_path
        exists = os.path.exists(self.file_path)
        self._exists = exists

        modified = ""
        try:
            ts = os.path.getmtime(self.file_path)
            modified = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

        metrics = QFontMetrics(self.font())
        base_text = f"{path}"
        if modified:
            base_text = f"{path} • Modified: {modified}"

        elided = metrics.elidedText(base_text, Qt.TextElideMode.ElideMiddle, 600)
        self.path_label.setText(elided)

    def update_styles(self):
        base_bg = "transparent"
        hover_bg = theme_config.COLOR_BACKGROUND_LIGHT
        border = theme_config.COLOR_BORDER_LIGHT
        text_primary = theme_config.COLOR_TEXT_PRIMARY
        text_secondary = theme_config.COLOR_TEXT_SECONDARY
        missing_color = theme_config.COLOR_ACCENT_ERROR

        self.setStyleSheet(f"""
            RecentFileItem {{
                background-color: {base_bg};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px;
            }}
            RecentFileItem:hover {{
                background-color: {hover_bg};
                border: 1px solid {border};
            }}
        """)
        self.name_label.setStyleSheet(f"color: {text_primary}; font-weight: bold;")
        if self._exists:
            self.path_label.setStyleSheet(f"color: {text_secondary}; font-size: 8.5pt;")
        else:
            self.path_label.setStyleSheet(f"color: {missing_color}; font-size: 8.5pt; font-style: italic;")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_path_and_time()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        act_open = QAction("Open", self)
        act_reveal = QAction("Reveal in File Manager", self)
        act_copy = QAction("Copy Path", self)
        act_remove = QAction("Remove from Recents", self)

        menu.addAction(act_open)
        menu.addAction(act_reveal)
        menu.addAction(act_copy)
        menu.addSeparator()
        menu.addAction(act_remove)

        chosen = menu.exec(self.mapToGlobal(pos))
        if not chosen:
            return
        if chosen == act_open:
            self.clicked.emit(self.file_path)
        elif chosen == act_reveal:
            self.revealRequested.emit(self.file_path)
        elif chosen == act_copy:
            QGuiApplication.clipboard().setText(self.file_path)
            self.copyPathRequested.emit(self.file_path)
        elif chosen == act_remove:
            self.removeRequested.emit(self.file_path)


class ModernWelcomeScreen(QWidget):
    """Modern welcome screen with enhanced design, responsiveness, and pro UX."""

    # Existing Signals
    newFileRequested = pyqtSignal()
    openProjectRequested = pyqtSignal()
    openRecentRequested = pyqtSignal(str)
    showGuideRequested = pyqtSignal()
    showExamplesRequested = pyqtSignal()

    # New optional signals
    removeRecentRequested = pyqtSignal(str)
    revealRecentRequested = pyqtSignal(str)
    clearRecentsRequested = pyqtSignal()
    showOnStartupChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.cards_grid = None
        self.cards_widget = None
        self._show_on_startup_key = "ui.welcome.show_on_startup"
        self._recent_filter_text = ""

        # Drag & drop to open projects
        self.setAcceptDrops(True)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_layout.addWidget(self.scroll_area)

        # Content
        content = QWidget()
        self.scroll_area.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(60, 60, 60, 60)
        content_layout.setSpacing(32)

        # Header
        self.create_header(content_layout)

        # Options row
        self._create_options_row(content_layout)

        # Action cards (responsive grid)
        self.create_action_cards(content_layout)

        # Recent files (with filter and clear)
        self.create_recent_files(content_layout)

        # Footer
        self.create_footer(content_layout)

        content_layout.addStretch()
        self.update_styles()

        # Intro animations
        QTimer.singleShot(60, self._run_intro_animations)

    def update_styles(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme_config.COLOR_BACKGROUND_APP},
                    stop: 1 {QColor(theme_config.COLOR_BACKGROUND_APP).darker(105).name()}
                );
            }}
        """)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical {
                width: 12px;
                background-color: transparent;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 0, 0, 0.3);
            }
        """)
        self.title_label.setStyleSheet(f"color: {theme_config.COLOR_ACCENT_PRIMARY}; font-size: 32pt; font-weight: bold; padding: 12px;")
        self.version_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_SECONDARY}; font-size: 11pt;")
        self.tagline_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_PRIMARY}; font-size: 13pt; padding: 6px;")
        self.recent_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_PRIMARY}; font-size: 16pt; font-weight: bold;")
        self.no_recent_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_SECONDARY}; font-style: italic; padding: 24px; background-color: {theme_config.COLOR_BACKGROUND_LIGHT}; border: 1px solid {theme_config.COLOR_BORDER_LIGHT}; border-radius: 8px;")
        self.footer_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_SECONDARY}; font-size: 9pt; padding: 12px;")

        if hasattr(self, "show_on_startup_cb"):
            self.show_on_startup_cb.setStyleSheet(f"color: {theme_config.COLOR_TEXT_SECONDARY};")

        # Update all ActionCards / Recent items
        for child in self.findChildren(ActionCard):
            child.update_styles(False, False)
        for child in self.findChildren(RecentFileItem):
            child.update_styles()

    def create_header(self, layout):
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(6)

        self.title_label = QLabel(config.APP_NAME)
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label)

        self.version_label = QLabel(f"Version {config.APP_VERSION}")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.version_label)

        self.tagline_label = QLabel("Design, Simulate, and Generate Finite State Machines")
        self.tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.tagline_label)

        layout.addWidget(header_widget)

    def _create_options_row(self, layout):
        opt_row = QHBoxLayout()
        opt_row.setContentsMargins(0, 0, 0, 0)

        self.show_on_startup_cb = QCheckBox("Show this screen at startup")
        show_default = True
        try:
            if hasattr(config, "get"):
                show_default = bool(config.get(self._show_on_startup_key, True))
        except Exception:
            pass
        self.show_on_startup_cb.setChecked(show_default)
        self.show_on_startup_cb.stateChanged.connect(self._on_show_on_startup_changed)

        opt_row.addStretch()
        opt_row.addWidget(self.show_on_startup_cb)
        layout.addLayout(opt_row)

    def create_action_cards(self, layout):
        # Container to center
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addStretch()

        # Grid
        self.cards_widget = QWidget()
        self.cards_grid = QGridLayout(self.cards_widget)
        self.cards_grid.setSpacing(20)
        container_layout.addWidget(self.cards_widget)

        container_layout.addStretch()
        layout.addWidget(container)

        # Define cards
        new_card = ActionCard("New Project", "Start a new FSM project", get_standard_icon(QStyle.StandardPixmap.SP_FileIcon))
        new_card.clicked.connect(self.newFileRequested.emit)

        open_card = ActionCard("Open Project", "Open an existing .bsmproj file", get_standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton))
        open_card.clicked.connect(self.openProjectRequested.emit)

        guide_card = ActionCard("Quick Start Guide", "Learn the basics in minutes", get_standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        guide_card.clicked.connect(self.showGuideRequested.emit)

        examples_card = ActionCard("Browse Examples", "Explore sample FSM designs", get_standard_icon(QStyle.StandardPixmap.SP_DirIcon))
        examples_card.clicked.connect(self.showExamplesRequested.emit)

        self.cards = [new_card, open_card, guide_card, examples_card]
        self._reflow_cards()

    def _reflow_cards(self):
        if not self.cards_grid or not self.cards:
            return
        # Clear grid
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item and item.widget():
                self.cards_grid.removeWidget(item.widget())
        # Responsive columns based on available width
        avail = self.scroll_area.viewport().width() - 160  # account margins/padding
        min_card_w = 300
        cols = max(1, min(3, avail // (min_card_w + self.cards_grid.spacing())))
        for i, card in enumerate(self.cards):
            r = i // cols
            c = i % cols
            self.cards_grid.addWidget(card, r, c, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)

    def create_recent_files(self, layout):
        # Header row with filter + clear
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 6)

        self.recent_label = QLabel("Recent Projects")
        header_layout.addWidget(self.recent_label)
        header_layout.addStretch()

        self.recent_filter_edit = QLineEdit()
        self.recent_filter_edit.setPlaceholderText("Filter recent projects...")
        self.recent_filter_edit.textChanged.connect(self._on_recent_filter_changed)
        header_layout.addWidget(self.recent_filter_edit)

        self.clear_recent_btn = QPushButton("Clear")
        self.clear_recent_btn.setToolTip("Clear recent projects list")
        self.clear_recent_btn.clicked.connect(lambda: self.clearRecentsRequested.emit())
        header_layout.addWidget(self.clear_recent_btn)

        layout.addWidget(header_widget)

        # Container
        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(8)

        self.no_recent_label = QLabel("No recent projects")
        self.no_recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_layout.addWidget(self.no_recent_label)

        layout.addWidget(self.recent_container)

    def create_footer(self, layout):
        self.footer_label = QLabel(f"© 2024 FSM Designer | Built with PyQt{PYQT_VERSION_STR}")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.footer_label)

    def update_recent_files(self, recent_files):
        """Update recent files list, filtering for project extension and search text."""
        if not hasattr(self, 'recent_layout'):
            return

        # Clear
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filt = (self._recent_filter_text or "").strip().lower()
        project_files = [p for p in recent_files if p.endswith(config.PROJECT_FILE_EXTENSION)]
        if filt:
            project_files = [p for p in project_files if (filt in os.path.basename(p).lower() or filt in os.path.dirname(p).lower())]

        if not project_files:
            self.recent_layout.addWidget(self.no_recent_label)
            self.no_recent_label.show()
            return
        else:
            self.no_recent_label.hide()

        for file_path in project_files[:8]:  # show up to 8
            item = RecentFileItem(file_path)
            item.clicked.connect(self.openRecentRequested.emit)
            item.revealRequested.connect(self._on_recent_reveal)
            item.removeRequested.connect(self._on_recent_remove)
            self.recent_layout.addWidget(item)

    # --------- Event handlers and helpers ---------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_cards()

    def _on_recent_filter_changed(self, text: str):
        self._recent_filter_text = text
        # Parent should call update_recent_files(recent_list) again with same list or we can hide items:
        # Simpler: emit signal to let parent re-supply list if needed.
        # If parent doesn't, we can try to hide on the fly:
        for i in range(self.recent_layout.count()):
            w = self.recent_layout.itemAt(i).widget()
            if isinstance(w, RecentFileItem):
                p = w.file_path
                show = (text.strip().lower() in os.path.basename(p).lower()) or (text.strip().lower() in os.path.dirname(p).lower())
                w.setVisible(show or not text)

    def _on_recent_remove(self, file_path: str):
        self.removeRecentRequested.emit(file_path)

    def _on_recent_reveal(self, file_path: str):
        self.revealRecentRequested.emit(file_path)
        _reveal_in_file_manager(file_path)

    def _on_show_on_startup_changed(self, state):
        checked = bool(state)
        try:
            if hasattr(config, "set"):
                config.set(self._show_on_startup_key, checked)
            elif hasattr(config, "__setitem__"):
                config[self._show_on_startup_key] = checked
            if hasattr(config, "save"):
                config.save()
        except Exception:
            pass
        self.showOnStartupChanged.emit(checked)

    def _run_intro_animations(self):
        # Fade in title and cards
        try:
            # Cards: staggered fade-in
            delay = 0
            for card in self.cards:
                card.set_intro_opacity(0.0)
                anim = QPropertyAnimation(card.graphicsEffect(), b"opacity", self)
                anim.setDuration(350)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.setDelay(delay)
                anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
                delay += 80
        except Exception:
            pass

    # Drag & drop to open projects
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().endswith(config.PROJECT_FILE_EXTENSION):
                    e.acceptProposedAction()
                    return
        e.ignore()

    def dropEvent(self, e: QDropEvent):
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().endswith(config.PROJECT_FILE_EXTENSION):
                    self.openRecentRequested.emit(url.toLocalFile())
                    break
        e.acceptProposedAction()


# For compatibility with older code that might import WelcomeWidget
WelcomeWidget = ModernWelcomeScreen