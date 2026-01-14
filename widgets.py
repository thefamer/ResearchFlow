"""
ResearchFlow - Custom Widgets
PyQt6 widgets for the application UI.
"""

from typing import Optional, TYPE_CHECKING
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QScrollArea, QFrame, QDockWidget, QDialog, QTextBrowser, QMessageBox,
    QColorDialog, QTextEdit, QListWidget, QListWidgetItem, QGroupBox, 
    QFormLayout, QMenu, QSplitter
)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import (
    QDrag, QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, 
    QAction, QIcon, QPixmap
)
if TYPE_CHECKING:
    from utils import ProjectManager

from utils import ModernTheme


# ============================================================================
# Welcome Dialog
# ============================================================================
class WelcomeDialog(QDialog):
    """
    Initial dialog for creating or opening projects.
    """
    
    project_selected = pyqtSignal(str, bool)  # name, is_new
    
    def __init__(self, existing_projects: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("ResearchFlow - Welcome")
        self.setMinimumSize(450, 400)
        self.setModal(True)
        
        self._setup_ui(existing_projects)
        self._apply_styles()
    
    def _setup_ui(self, existing_projects: list[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("ResearchFlow")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Portable Research Management Tool")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Create new project section
        new_frame = QFrame()
        new_frame.setFrameShape(QFrame.Shape.StyledPanel)
        new_layout = QVBoxLayout(new_frame)
        
        new_label = QLabel("Create New Project")
        new_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        new_layout.addWidget(new_label)
        
        name_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter project name...")
        self.name_input.returnPressed.connect(self._create_new)
        name_layout.addWidget(self.name_input)
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self._create_new)
        create_btn.setFixedWidth(80)
        name_layout.addWidget(create_btn)
        
        new_layout.addLayout(name_layout)
        layout.addWidget(new_frame)
        
        # Open existing project section
        if existing_projects:
            open_frame = QFrame()
            open_frame.setFrameShape(QFrame.Shape.StyledPanel)
            open_layout = QVBoxLayout(open_frame)
            
            open_label = QLabel("Open Existing Project")
            open_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            open_layout.addWidget(open_label)
            
            self.project_list = QListWidget()
            self.project_list.setMaximumHeight(150)
            for project in existing_projects:
                item = QListWidgetItem(project)
                item.setIcon(self._create_folder_icon())
                self.project_list.addItem(item)
            self.project_list.itemDoubleClicked.connect(self._open_selected)
            open_layout.addWidget(self.project_list)
            
            open_btn = QPushButton("Open Selected")
            open_btn.clicked.connect(self._open_selected)
            open_layout.addWidget(open_btn)
            
            layout.addWidget(open_frame)
        else:
            no_projects = QLabel("No existing projects found.")
            no_projects.setStyleSheet("color: #999; font-style: italic;")
            no_projects.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_projects)
        
        layout.addStretch()
    
    def _create_folder_icon(self) -> "QIcon":
        """Create a simple folder icon."""
        from PyQt6.QtGui import QIcon
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor("#FFC107"))
        return QIcon(pixmap)
    
    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
            }
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
        """)
    
    def _create_new(self) -> None:
        name = self.name_input.text().strip()
        if name:
            self.project_selected.emit(name, True)
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid Name", "Please enter a project name.")
    
    def _open_selected(self) -> None:
        if hasattr(self, 'project_list'):
            current = self.project_list.currentItem()
            if current:
                self.project_selected.emit(current.text(), False)
                self.accept()
            else:
                QMessageBox.warning(self, "No Selection", "Please select a project to open.")


# ============================================================================
# Draggable Tag Item
# ============================================================================
class DraggableTagItem(QLabel):
    """A tag that can be dragged onto nodes."""
    
    def __init__(self, tag_name: str, parent=None):
        super().__init__(tag_name, parent)
        self.tag_name = tag_name
        self._color = self._generate_color(tag_name)
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMinimumHeight(28)
        self.setContentsMargins(10, 5, 10, 5)
        
        self._update_style()
    
    def _generate_color(self, text: str) -> QColor:
        """Generate a consistent color based on tag name."""
        hash_val = sum(ord(c) for c in text)
        hue = (hash_val * 37) % 360
        return QColor.fromHsl(hue, 200, 120)
    
    def _update_style(self) -> None:
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self._color.name()};
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QLabel:hover {{
                background-color: {self._color.darker(110).name()};
            }}
        """)
    
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(f"tag:{self.tag_name}")
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


# ============================================================================
# Tag Dock Widget
# ============================================================================
# ============================================================================
# Modern Dock Title Bar
# ============================================================================
class ModernDockTitleBar(QWidget):
    """Custom title bar for the Project Dock to match Modern UI."""
    
    def __init__(self, dock_widget: QDockWidget):
        super().__init__(dock_widget)
        self.dock = dock_widget
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        
        # Title
        self.title_label = QLabel(self.dock.windowTitle())
        font = ModernTheme.get_ui_font(10, bold=True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(f"color: {ModernTheme.TEXT_PRIMARY};")
        
        layout.addWidget(self.title_label)
        layout.addStretch()
        
        # Close Button Style
        btn_style = f"""
            QPushButton {{
                background: transparent;
                color: #666666;
                border: 1px solid transparent;
                border-radius: 4px;
                font-family: "Segoe UI Symbol", "Microsoft YaHei", sans-serif;
                font-size: 16px;
                font-weight: bold;
                margin: 0px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {ModernTheme.BG_TERTIARY};
                color: {ModernTheme.ACCENT_COLOR};
            }}
        """
        
        # Close Button only
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self._request_close)
        self.close_btn.setStyleSheet(btn_style)
        layout.addWidget(self.close_btn)
    
    def _request_close(self):
        """Request animated close via signal."""
        self.dock.close_requested.emit()


class ProjectDockWidget(QDockWidget):
    """
    Project management dock containing:
    1. Project Description
    2. TODO List
    3. Global Color Settings
    4. Tag Management
    """
    
    # Tag signals
    tag_added = pyqtSignal(str)
    tag_removed = pyqtSignal(str)
    tag_renamed = pyqtSignal(str, str)
    
    # New V1.2.0 signals
    description_changed = pyqtSignal(str)
    todo_changed = pyqtSignal()  # Signal to save project
    edge_color_changed = pyqtSignal(str, str)  # pipeline_color, reference_color
    
    # V2.1.0: Animated close
    close_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("Project Manager", parent)
        self.setTitleBarWidget(ModernDockTitleBar(self))
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)  # No float
        self.setMinimumWidth(250)
        
        # Data storage
        self._tags: list[str] = []
        self._tag_widgets: list[DraggableTagItem] = []
        self._todos: list[dict] = []
        
        # Default colors
        self._pipeline_color = "#607D8B" 
        self._reference_color = "#4CAF50"
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # Main container using Splitter for adjustable layouts
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        
        # --- 1. Project Description ---
        desc_group = QGroupBox("Project Description")
        desc_layout = QVBoxLayout(desc_group)
        desc_layout.setContentsMargins(10, 15, 10, 10)
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Enter project description...")
        self.desc_edit.textChanged.connect(self._on_desc_changed)
        desc_layout.addWidget(self.desc_edit)
        self.splitter.addWidget(desc_group)
        
        # --- 2. Edge Colors ---
        color_group = QGroupBox("Connection Colors")
        color_layout = QFormLayout(color_group)
        color_layout.setContentsMargins(10, 15, 10, 10)
        
        # Pipeline Color
        self.btn_pipeline_color = QPushButton()
        self.btn_pipeline_color.setFixedSize(50, 24)
        self.btn_pipeline_color.clicked.connect(lambda: self._pick_color("pipeline"))
        color_layout.addRow("Pipeline:", self.btn_pipeline_color)
        
        # Reference Color
        self.btn_ref_color = QPushButton()
        self.btn_ref_color.setFixedSize(50, 24)
        self.btn_ref_color.clicked.connect(lambda: self._pick_color("reference"))
        color_layout.addRow("Reference:", self.btn_ref_color)
        
        self._update_color_buttons()
        self.splitter.addWidget(color_group)
        
        # --- 3. TODO List ---
        todo_group = QGroupBox("TODO List")
        todo_layout = QVBoxLayout(todo_group)
        todo_layout.setContentsMargins(10, 15, 10, 10)
        
        # Input
        todo_input_layout = QHBoxLayout()
        self.todo_input = QLineEdit()
        self.todo_input.setPlaceholderText("New task...")
        self.todo_input.returnPressed.connect(self._add_todo)
        
        add_todo_btn = QPushButton("+")
        add_todo_btn.setFixedSize(24, 24)
        add_todo_btn.clicked.connect(self._add_todo)
        
        todo_input_layout.addWidget(self.todo_input)
        todo_input_layout.addWidget(add_todo_btn)
        todo_layout.addLayout(todo_input_layout)
        
        # List
        self.todo_list = QListWidget()
        self.todo_list.setWordWrap(True)
        self.todo_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.todo_list.customContextMenuRequested.connect(self._show_todo_menu)
        self.todo_list.itemChanged.connect(self._on_todo_item_changed)
        todo_layout.addWidget(self.todo_list)
        self.splitter.addWidget(todo_group)
        
        # --- 4. Tags ---
        tag_group = QGroupBox("Tags")
        tag_layout = QVBoxLayout(tag_group)
        tag_layout.setContentsMargins(10, 15, 10, 10)
        
        # Tag Input
        tag_input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("New tag...")
        self.tag_input.returnPressed.connect(self._add_tag)
        
        add_tag_btn = QPushButton("+")
        add_tag_btn.setFixedSize(24, 24)
        add_tag_btn.clicked.connect(self._add_tag)
        add_tag_btn.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 2px;")
        
        tag_input_layout.addWidget(self.tag_input)
        tag_input_layout.addWidget(add_tag_btn)
        tag_layout.addLayout(tag_input_layout)
        
        # Tag List Container (Scrollable)
        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(5)
        self.tags_layout.addStretch()
        
        tags_scroll = QScrollArea()
        tags_scroll.setWidgetResizable(True)
        tags_scroll.setWidget(self.tags_container)
        tags_scroll.setFrameShape(QFrame.Shape.NoFrame)
        tag_layout.addWidget(tags_scroll)
        
        # Help text
        help_label = QLabel("Drag tags onto nodes to assign")
        help_label.setStyleSheet("color: #666; font-size: 9pt; font-style: italic; margin-top: 5px;")
        help_label.setWordWrap(True)
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag_layout.addWidget(help_label)
        
        self.splitter.addWidget(tag_group)
        
        # Styling
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #E0E0E0;
                height: 2px;
                margin: 2px 10px;
            }
            QSplitter::handle:hover {
                background-color: #2196F3;
                height: 4px;
            }
        """)

        wrapper_layout.addWidget(self.splitter)
        self.setWidget(wrapper)

    def get_layout_state(self) -> list[int]:
        if hasattr(self, 'splitter'):
            return self.splitter.sizes()
        return []
        
    def set_layout_state(self, sizes: list[int]) -> None:
        if hasattr(self, 'splitter') and sizes:
            self.splitter.setSizes(sizes)
    
    # --- Project Data Management ---
    
    def set_project_data(self, description: str, todos: list, tags: list, 
                        pipeline_color: str, reference_color: str) -> None:
        """Populate UI from project data."""
        # 1. Description
        self.desc_edit.blockSignals(True)
        self.desc_edit.setText(description)
        self.desc_edit.blockSignals(False)
        
        # 2. Colors
        self._pipeline_color = pipeline_color
        self._reference_color = reference_color
        self._update_color_buttons()
        
        # 3. TODOs
        self.todo_list.clear() # Clears widgets too?
        self._todos = todos
        for todo in todos:
            self._create_todo_item(todo["text"], todo["done"])
            
        # 4. Tags
        self.set_tags(tags)
    
    def get_description(self) -> str:
        return self.desc_edit.toPlainText()
    
    def get_todos(self) -> list[dict]:
        """Return list of todos: [{'text': '...', 'done': True/False}]"""
        todos = []
        for i in range(self.todo_list.count()):
            item = self.todo_list.item(i)
            todos.append({
                "text": item.text(),
                "done": item.checkState() == Qt.CheckState.Checked
            })
        return todos
    
    # --- Description Logic ---
    
    def _on_desc_changed(self) -> None:
        self.description_changed.emit(self.desc_edit.toPlainText())
        
    # --- Color Logic ---
    
    def _update_color_buttons(self) -> None:
        self.btn_pipeline_color.setStyleSheet(
            f"background-color: {self._pipeline_color}; color: white; border: none; border-radius: 4px;"
        )
        self.btn_ref_color.setStyleSheet(
            f"background-color: {self._reference_color}; color: white; border: none; border-radius: 4px;"
        )
    
    def _pick_color(self, type_: str) -> None:
        initial = QColor(self._pipeline_color if type_ == "pipeline" else self._reference_color)
        color = QColorDialog.getColor(initial, self, f"Select {type_.title()} Connection Color")
        
        if color.isValid():
            hex_color = color.name()
            if type_ == "pipeline":
                self._pipeline_color = hex_color
            else:
                self._reference_color = hex_color
            
            self._update_color_buttons()
            self.edge_color_changed.emit(self._pipeline_color, self._reference_color)
            
    # --- TODO Logic ---
    
    def _add_todo(self) -> None:
        text = self.todo_input.text().strip()
        if text:
            self._create_todo_item(text, False)
            self.todo_input.clear()
            self.todo_changed.emit()
    
    def _create_todo_item(self, text: str, done: bool) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
        
        # Apply strikeout if done
        font = item.font()
        font.setStrikeOut(done)
        item.setFont(font)
        
        self.todo_list.addItem(item)
    
    def _on_todo_item_changed(self, item) -> None:
        # Update strikeout style based on check state
        font = item.font()
        font.setStrikeOut(item.checkState() == Qt.CheckState.Checked)
        item.setFont(font)
        
        self.todo_changed.emit()
    
    def _show_todo_menu(self, pos: QPoint) -> None:
        item = self.todo_list.itemAt(pos)
        if not item:
            return
            
        menu = QMenu(self)
        delete_action = menu.addAction("Delete Task")
        action = menu.exec(self.todo_list.mapToGlobal(pos))
        
        if action == delete_action:
            row = self.todo_list.row(item)
            self.todo_list.takeItem(row)
            self.todo_changed.emit()
    
    def _add_tag(self) -> None:
        """Add a new tag."""
        tag_name = self.tag_input.text().strip()
        if tag_name and tag_name not in self._tags:
            self._tags.append(tag_name)
            
            widget = DraggableTagItem(tag_name)
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(lambda pos, w=widget: self._show_tag_menu(w))
            
            self._tag_widgets.append(widget)
            # Insert before the stretch
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, widget)
            
            self.tag_input.clear()
            self.tag_added.emit(tag_name)
    
    def _show_tag_menu(self, widget: DraggableTagItem) -> None:
        """Show context menu for a tag."""
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        
        rename_action = menu.addAction("Rename Tag")
        delete_action = menu.addAction("Delete Tag")
        
        action = menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))
        
        if action == rename_action:
            self._rename_tag(widget)
        elif action == delete_action:
            self._remove_tag(widget.tag_name)
    
    def _rename_tag(self, widget: DraggableTagItem) -> None:
        """Rename a tag."""
        from PyQt6.QtWidgets import QInputDialog
        old_name = widget.tag_name
        new_name, ok = QInputDialog.getText(
            self, "Rename Tag",
            "New name:",
            text=old_name
        )
        if ok and new_name and new_name != old_name:
            # Update internal list
            idx = self._tags.index(old_name)
            self._tags[idx] = new_name
            
            # Update widget
            widget.tag_name = new_name
            widget.setText(new_name)
            widget._color = widget._generate_color(new_name)
            widget._update_style()
            
            # Emit signal for syncing to nodes
            self.tag_renamed.emit(old_name, new_name)
    
    def _remove_tag(self, tag_name: str) -> None:
        """Remove a tag."""
        if tag_name in self._tags:
            self._tags.remove(tag_name)
            
            for widget in self._tag_widgets:
                if widget.tag_name == tag_name:
                    self._tag_widgets.remove(widget)
                    widget.deleteLater()
                    break
            
            self.tag_removed.emit(tag_name)
    
    def set_tags(self, tags: list[str]) -> None:
        """Set the tag list (for loading projects)."""
        # Clear existing
        for widget in self._tag_widgets:
            widget.deleteLater()
        self._tag_widgets.clear()
        self._tags.clear()
        
        # Add new tags
        for tag_name in tags:
            self._tags.append(tag_name)
            widget = DraggableTagItem(tag_name)
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(lambda pos, w=widget: self._show_tag_menu(w))
            self._tag_widgets.append(widget)
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, widget)
    
    def get_tags(self) -> list[str]:
        """Get the current tag list."""
        return self._tags.copy()


# ============================================================================
# Markdown Viewer Dialog
# ============================================================================
class MarkdownViewerDialog(QDialog):
    """
    Floating window for rendering Markdown content.
    """
    
    def __init__(self, title: str, markdown_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📄 {title}")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        self._setup_ui(markdown_path)
    
    def _setup_ui(self, markdown_path: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Text browser for rendering
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                padding: 20px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11pt;
                line-height: 1.6;
            }
        """)
        
        # Load and display content
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple markdown to HTML conversion
            html = self._markdown_to_html(content)
            self.browser.setHtml(html)
        except Exception as e:
            self.browser.setText(f"Error loading file: {e}")
        
        layout.addWidget(self.browser)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        btn_layout.addWidget(close_btn)
        btn_layout.setContentsMargins(10, 10, 10, 10)
        layout.addLayout(btn_layout)
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Markdown to HTML conversion with LaTeX support (offline-friendly)."""
        import re
        
        html = markdown
        
        # Handle LaTeX block formulas ($$...$$) - convert to MathML if possible
        def format_block_formula(match):
            formula = match.group(1).strip()
            
            # Extract tag number if present
            tag_html = ""
            tag_match = re.search(r'\\tag\s*\{([^}]*)\}|\\tag\s*(\d+)', formula)
            if tag_match:
                tag_num = tag_match.group(1) or tag_match.group(2)
                tag_html = f'<span class="equation-tag">({tag_num})</span>'
                # Remove tag from formula for processing
                formula = re.sub(r'\\tag\s*\{[^}]*\}|\\tag\s*\d+', '', formula).strip()
            
            mathml = self._latex_to_mathml(formula)
            if mathml:
                return f'<div class="math-block"><div class="math-content">{mathml}</div>{tag_html}</div>'
            else:
                return f'<div class="math-block"><div class="math-content"><span class="math-formula">{self._escape_html(formula)}</span></div>{tag_html}</div>'
        html = re.sub(r'\$\$(.+?)\$\$', format_block_formula, html, flags=re.DOTALL)
        
        # Handle LaTeX inline formulas ($...$) - convert to MathML if possible
        def format_inline_formula(match):
            formula = match.group(1)
            mathml = self._latex_to_mathml(formula)
            if mathml:
                return f'<span class="math-inline">{mathml}</span>'
            else:
                return f'<span class="math-inline math-fallback">{self._escape_html(formula)}</span>'
        html = re.sub(r'\$([^$\n]+?)\$', format_inline_formula, html)
        
        # Headers
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Code blocks
        html = re.sub(r'```(\w*)\n(.*?)```', r'<pre class="code-block"><code>\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code class="inline-code">\1</code>', html)
        
        # Links
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
        
        # Images (local paths only for portability)
        html = re.sub(r'!\[(.+?)\]\((.+?)\)', r'<img src="\2" alt="\1" style="max-width:100%;">', html)
        
        # Lists (unordered)
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html)
        
        # Lists (ordered)
        html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Blockquotes
        html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
        
        # Horizontal rules
        html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)
        
        # Line breaks (paragraphs)
        html = re.sub(r'\n\n+', '</p><p>', html)
        html = f'<p>{html}</p>'
        
        # Clean up empty paragraphs
        html = re.sub(r'<p>\s*</p>', '', html)
        html = re.sub(r'<p>(<h[1-4]>)', r'\1', html)
        html = re.sub(r'(</h[1-4]>)</p>', r'\1', html)
        html = re.sub(r'<p>(<ul>)', r'\1', html)
        html = re.sub(r'(</ul>)</p>', r'\1', html)
        html = re.sub(r'<p>(<pre)', r'\1', html)
        html = re.sub(r'(</pre>)</p>', r'\1', html)
        html = re.sub(r'<p>(<div)', r'\1', html)
        html = re.sub(r'(</div>)</p>', r'\1', html)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ 
                    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; 
                    line-height: 1.8; 
                    padding: 20px;
                    color: #333;
                }}
                h1 {{ color: #1976D2; border-bottom: 2px solid #E3F2FD; padding-bottom: 10px; }}
                h2 {{ color: #1565C0; margin-top: 24px; }}
                h3 {{ color: #0D47A1; margin-top: 20px; }}
                h4 {{ color: #0D47A1; margin-top: 16px; }}
                a {{ color: #2196F3; }}
                
                /* Code blocks */
                .code-block {{
                    background: #f5f5f5;
                    padding: 12px;
                    border-radius: 6px;
                    overflow-x: auto;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 13px;
                    border: 1px solid #e0e0e0;
                }}
                .inline-code {{
                    background: #f5f5f5;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 13px;
                }}
                
                /* LaTeX formulas - styled like Typedown */
                .math-block {{ 
                    background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
                    padding: 16px 24px;
                    margin: 16px 0;
                    border-radius: 8px;
                    overflow-x: auto;
                    border-left: 4px solid #495057;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }}
                .math-content {{
                    flex: 1;
                    text-align: center;
                }}
                .equation-tag {{
                    font-family: 'Times New Roman', serif;
                    font-size: 14px;
                    color: #495057;
                    margin-left: 20px;
                    white-space: nowrap;
                }}
                .math-formula {{
                    font-family: 'Cambria Math', 'Latin Modern Math', 'STIX Two Math', 'Times New Roman', serif;
                    font-size: 16px;
                    font-weight: 600;
                    color: #212529;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .math-inline {{
                    font-family: 'Cambria Math', 'Latin Modern Math', 'Times New Roman', serif;
                    font-size: 15px;
                    font-weight: 600;
                    color: #212529;
                    background: #E9ECEF;
                    padding: 2px 5px;
                    border-radius: 3px;
                }}
                /* MathML styling for bold appearance */
                math {{
                    font-size: 16px;
                    font-weight: 500;
                }}
                math mi, math mo, math mn {{
                    font-weight: inherit;
                }}
                
                /* Other elements */
                ul {{ padding-left: 24px; }}
                li {{ margin: 4px 0; }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    padding-left: 16px;
                    color: #666;
                    margin: 10px 0;
                    font-style: italic;
                }}
                hr {{
                    border: none;
                    border-top: 1px solid #ddd;
                    margin: 20px 0;
                }}
                table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f5f5f5; }}
            </style>
        </head>
        <body>{html}</body>
        </html>
        """
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters while preserving LaTeX."""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    def _latex_to_mathml(self, latex: str) -> str:
        """
        Convert LaTeX formula to MathML for native Qt rendering.
        Returns empty string if conversion fails.
        """
        try:
            from latex2mathml import converter
            
            # Preprocess LaTeX to handle unsupported commands
            processed = self._preprocess_latex(latex)
            
            # Convert LaTeX to MathML
            mathml = converter.convert(processed)
            return mathml
        except ImportError:
            # latex2mathml not installed
            return ""
        except Exception:
            # Conversion failed (invalid LaTeX, etc.)
            return ""
    
    def _preprocess_latex(self, latex: str) -> str:
        """
        Preprocess LaTeX to handle commands not supported by latex2mathml.
        """
        import re
        
        result = latex
        
        # \pmb{x} -> \mathbf{x} (poor man's bold -> math bold)
        result = re.sub(r'\\pmb\{([^}]*)\}', r'\\mathbf{\1}', result)
        result = re.sub(r'\\pmb\s+(\w)', r'\\mathbf{\1}', result)
        
        # \tag{n} -> remove (equation tags not needed in viewer)
        # Match all variations: \tag{1}, \tag 1, \tag1, \tag {1}, \tag{something}
        result = re.sub(r'\\tag\s*\{[^}]*\}', '', result)  # \tag{1} or \tag {1}
        result = re.sub(r'\\tag\s*(\d+)', '', result)  # \tag1 or \tag 1
        # Also handle \tag followed by word at end of line
        result = re.sub(r'\\tag\s*\w+\s*$', '', result, flags=re.MULTILINE)
        
        # \boldsymbol{x} -> \mathbf{x}
        result = re.sub(r'\\boldsymbol\{([^}]*)\}', r'\\mathbf{\1}', result)
        
        # \bm{x} -> \mathbf{x}
        result = re.sub(r'\\bm\{([^}]*)\}', r'\\mathbf{\1}', result)
        
        # \text{...} -> \mathrm{...} (more compatible)
        result = re.sub(r'\\text\{([^}]*)\}', r'\\mathrm{\1}', result)
        
        # \operatorname{...} -> \mathrm{...}
        result = re.sub(r'\\operatorname\{([^}]*)\}', r'\\mathrm{\1}', result)
        
        # \mathbb{X} -> X (double-struck, fallback)
        # Keep as is - latex2mathml should handle it
        
        # \eqref{...} -> remove
        result = re.sub(r'\\eqref\{[^}]*\}', '', result)
        
        # \label{...} -> remove
        result = re.sub(r'\\label\{[^}]*\}', '', result)
        
        # \nonumber -> remove
        result = result.replace('\\nonumber', '')
        
        # \\ for line breaks in non-array context -> space
        # Be careful - don't replace inside array/matrix
        
        # \hspace{...}, \vspace{...} -> remove
        result = re.sub(r'\\[hv]space\{[^}]*\}', ' ', result)
        
        # \quad, \qquad -> space
        result = result.replace('\\qquad', '  ')
        result = result.replace('\\quad', ' ')
        
        # Clean up multiple spaces
        result = re.sub(r'  +', ' ', result)
        
        return result.strip()


# ============================================================================
# Module Palette (Draggable Shapes)
# ============================================================================
class ModulePaletteItem(QLabel):
    """A draggable module shape for the palette."""
    
    def __init__(self, module_type: str, label: str, color: QColor, parent=None):
        super().__init__(label, parent)
        self.module_type = module_type
        self._color = color
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedSize(80, 30)
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color.name()};
                color: white;
                border-radius: 6px;
                padding: 5px;
            }}
            QLabel:hover {{
                background-color: {color.darker(110).name()};
            }}
        """)
    
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(f"module:{self.module_type}")
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ModulePalette(QWidget):
    """Palette of draggable module shapes."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        label = QLabel("Modules:")
        label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(label)
        
        # Module types
        modules = [
            ("input", "Input", QColor("#4CAF50")),
            ("process", "Process", QColor("#9C27B0")),
            ("decision", "Decision", QColor("#FF9800")),
            ("output", "Output", QColor("#2196F3")),
        ]
        
        for module_type, label_text, color in modules:
            item = ModulePaletteItem(module_type, label_text, color)
            layout.addWidget(item)
        
        layout.addStretch()
        
        # Help text
        help_label = QLabel("Drag modules to canvas")
        help_label.setStyleSheet("color: #999; font-style: italic;")
        layout.addWidget(help_label)


# ============================================================================
# Pipeline Required Dialog
# ============================================================================
class PipelineRequiredDialog(QDialog):
    """Dialog shown when a pipeline must be created first."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pipeline Required")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Icon/Title
        title = QLabel("⚠️ Pipeline Required")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Message
        msg = QLabel(
            "Before importing references, you must create at least one\n"
            "Pipeline Module to define your research workflow.\n\n"
            "Drag a module from the toolbar onto the canvas to begin."
        )
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)
        
        # OK button
        btn = QPushButton("Got it!")
        btn.clicked.connect(self.accept)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


# ============================================================================
# Image Viewer Dialog
# ============================================================================
class ImageViewerDialog(QDialog):
    """Dialog to view images in full size."""
    
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Viewer")
        self.resize(1000, 800)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setStyleSheet(f"background-color: {ModernTheme.BG_SECONDARY}; border: none;")
        
        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        scroll.setWidget(self.image_label)
        layout.addWidget(scroll)
        
        # Bottom bar
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(10, 10, 10, 10)
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(100, 32)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addWidget(btn_container)
