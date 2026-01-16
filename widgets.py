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
    QFormLayout, QMenu, QSplitter, QInputDialog
)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import (
    QDrag, QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, 
    QAction, QIcon, QPixmap
)
if TYPE_CHECKING:
    from utils import ProjectManager

from utils import ModernTheme

# Import latex2mathml for LaTeX formula rendering
try:
    import latex2mathml.converter
    LATEX2MATHML_AVAILABLE = True
except ImportError:
    LATEX2MATHML_AVAILABLE = False


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
    """A tag that can be dragged onto nodes, with customizable color."""
    
    DEFAULT_COLOR = "#607D8B"  # Gray-blue default for all tags
    color_changed = pyqtSignal(str, str)  # tag_name, new_color
    
    def __init__(self, tag_name: str, color: str = None, parent=None):
        super().__init__(tag_name, parent)
        self.tag_name = tag_name
        # Use provided color or default gray
        self._color = QColor(color) if color else QColor(self.DEFAULT_COLOR)
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedHeight(28)
        self.setContentsMargins(1, 1, 1, 1)
        
        self._update_style()
    
    def set_color(self, color: str) -> None:
        """Set a custom color for this tag."""
        self._color = QColor(color) if color else QColor(self.DEFAULT_COLOR)
        self._update_style()
    
    def get_color(self) -> str:
        """Get the current color as hex string."""
        return self._color.name()
    
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
    tag_renamed = pyqtSignal(str, str)  # old_name, new_name
    tag_color_changed = pyqtSignal(str, str)  # tag_name, new_color
    
    # UI Signals
    description_changed = pyqtSignal(str)
    todo_changed = pyqtSignal()
    edge_color_changed = pyqtSignal(str, str)  # pipeline_color, reference_color
    close_requested = pyqtSignal()  # For animated close
    
    # Undo/Redo Request Signals
    todo_added_requested = pyqtSignal(str)
    todo_removed_requested = pyqtSignal(int, str, bool) # index, text, is_done
    todo_edited_requested = pyqtSignal(int, str, str) # index, old, new
    todo_toggled_requested = pyqtSignal(int, bool) # index, new_state
    move_todo_requested = pyqtSignal(int, int) # from, to
    
    tag_added_requested = pyqtSignal(str)
    tag_removed_requested = pyqtSignal(str, str, int) # name, color, index
    tag_renamed_requested = pyqtSignal(str, str) # old, new
    tag_color_changed_requested = pyqtSignal(str, str, str) # name, old, new
    move_tag_requested = pyqtSignal(int, int) # from, to
    
    def __init__(self, parent=None):
        super().__init__("Project Manager", parent)
        self.setTitleBarWidget(ModernDockTitleBar(self))
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)  # No float
        self.setMinimumWidth(250)
        
        # Data storage - tags stored as list of {"name": str, "color": str|None}
        self._tags: list[dict] = []
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
    
    def set_description(self, text: str) -> None:
        """Set description programmatically (for Undo/Redo)."""
        self.desc_edit.blockSignals(True)
        self.desc_edit.setText(text)
        self.desc_edit.blockSignals(False)
        # Update project data if manager available
        if hasattr(self, 'parent') and hasattr(self.parent(), 'project_manager'):
            pm = self.parent().project_manager
            if pm.is_project_open:
                pm.project_data.description = text
    
    def add_todo(self, text: str) -> None:
        """Add a todo item programmatically (for Undo/Redo execute)."""
        self._create_todo_item(text, False)
        self.todo_changed.emit()
    
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
            
    def set_edge_colors(self, pipeline_color: str, reference_color: str) -> None:
        """Set edge colors programmatically (for Undo/Redo)."""
        self._pipeline_color = pipeline_color
        self._reference_color = reference_color
        self._update_color_buttons()
        # Note: Do NOT emit signal here to prevent recursion
        # The command will update the scene directly
            
    # --- TODO Logic ---
    
    def _add_todo(self) -> None:
        text = self.todo_input.text().strip()
        if text:
            # Emit request instead of creating directly
            self.todo_added_requested.emit(text)
            self.todo_input.clear()
    
    def _create_todo_item(self, text: str, done: bool) -> None:
        """Helper to create item visually (called by insert_todo or loading)."""
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
        
        # Apply strikeout if done
        font = item.font()
        font.setStrikeOut(done)
        item.setFont(font)
        
        self.todo_list.addItem(item)
    
    def _on_todo_item_changed(self, item) -> None:
        # Check if this is a toggle change
        # If we had text editing, we'd need to distinguish
        row = self.todo_list.row(item)
        is_done = item.checkState() == Qt.CheckState.Checked
        
        # Update visual style immediately for responsiveness
        font = item.font()
        font.setStrikeOut(is_done)
        item.setFont(font)
        
        # Emit request for undo history
        self.todo_toggled_requested.emit(row, is_done)
        self.todo_changed.emit()
    
    def _show_todo_menu(self, pos: QPoint) -> None:
        """Show context menu for todo items."""
        item = self.todo_list.itemAt(pos)
        if not item:
            return
            
        menu = QMenu(self)
        edit_action = menu.addAction("Edit...")
        
        menu.addSeparator()
        
        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete Task")
        
        action = menu.exec(self.todo_list.mapToGlobal(pos))
        
        if action == delete_action:
            row = self.todo_list.row(item)
            text = item.text()
            is_done = item.checkState() == Qt.CheckState.Checked
            self.todo_removed_requested.emit(row, text, is_done)
        elif action == edit_action:
            self._edit_todo(item)
        elif action == move_up_action:
            self._move_todo_up(item)
        elif action == move_down_action:
            self._move_todo_down(item)

    def _edit_todo(self, item: QListWidgetItem) -> None:
        """Edit todo item text."""
        old_text = item.text()
        text, ok = QInputDialog.getText(
            self, "Edit Task", "Task Description:", QLineEdit.EchoMode.Normal, old_text
        )
        if ok and text.strip() and text.strip() != old_text:
            index = self.todo_list.row(item)
            # Emit signal for undo/redo instead of directly modifying
            self.todo_edited_requested.emit(index, old_text, text.strip())
            
    def remove_todo_at(self, index: int) -> None:
        """Remove todo item at index."""
        if 0 <= index < self.todo_list.count():
            self.todo_list.takeItem(index)
            self.todo_changed.emit()

    def insert_todo(self, index: int, text: str, done: bool) -> None:
        """Insert todo item at index."""
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
        
        font = item.font()
        font.setStrikeOut(done)
        item.setFont(font)
        
        self.todo_list.insertItem(index, item)
        self.todo_changed.emit()

    def update_todo_text(self, index: int, text: str) -> None:
        """Update text of todo item at index."""
        if 0 <= index < self.todo_list.count():
            item = self.todo_list.item(index)
            item.setText(text)
            self.todo_changed.emit()

    def set_todo_status(self, index: int, done: bool) -> None:
        """Set completion status of todo item at index."""
        if 0 <= index < self.todo_list.count():
            item = self.todo_list.item(index)
            # Block signals to prevent recursion if calling from undo
            self.todo_list.blockSignals(True)
            item.setCheckState(Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
            font = item.font()
            font.setStrikeOut(done)
            item.setFont(font)
            self.todo_list.blockSignals(False)
            self.todo_changed.emit()

    def move_todo(self, from_index: int, to_index: int) -> None:
        """Move todo item from index to index."""
        if 0 <= from_index < self.todo_list.count() and 0 <= to_index < self.todo_list.count():
            item = self.todo_list.takeItem(from_index)
            self.todo_list.insertItem(to_index, item)
            # Restore selection?
            self.todo_changed.emit()
            
    def _move_todo_up(self, item: QListWidgetItem) -> None:
        """Move todo item up."""
        row = self.todo_list.row(item)
        if row > 0:
            # Signal to main window to execute move command
            if hasattr(self, 'move_todo_requested'):
                self.move_todo_requested.emit(row, row - 1)
            else:
                self.move_todo(row, row - 1)
            
    def _move_todo_down(self, item: QListWidgetItem) -> None:
        """Move todo item down."""
        row = self.todo_list.row(item)
        if row < self.todo_list.count() - 1:
            if hasattr(self, 'move_todo_requested'):
                self.move_todo_requested.emit(row, row + 1)
            else:
                self.move_todo(row, row + 1)
    
    def _add_tag(self) -> None:
        """Add a new tag."""
        name = self.tag_input.text().strip()
        if name:
            # Check for duplicate
            if any(t['name'] == name for t in self._tags):
                return
            
            self.tag_added_requested.emit(name)
            self.tag_input.clear()
    
    def _on_tag_color_changed(self, new_color: str) -> None:
        """Handle tag color change from widget."""
        widget = self.sender()
        if isinstance(widget, DraggableTagItem):
            # Find old color
            old_color = "#607D8B"
            for tag in self._tags:
                if tag["name"] == widget.tag_name:
                    old_color = tag["color"]
                    break
            
            if old_color != new_color:
                self.tag_color_changed_requested.emit(widget.tag_name, old_color, new_color)
    
    def _show_tag_menu(self, widget: DraggableTagItem) -> None:
        """Show context menu for tag."""
        from PyQt6.QtWidgets import QMenu, QColorDialog
        from PyQt6.QtGui import QCursor
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        color_action = menu.addAction("Change Color...")
        delete_action = menu.addAction("Delete")
        
        menu.addSeparator()
        move_up = menu.addAction("Move Up")
        move_down = menu.addAction("Move Down")
        
        action = menu.exec(QCursor.pos())
        
        if action == delete_action:
            self._remove_tag(widget.tag_name)
        elif action == rename_action:
            self._rename_tag(widget)
        elif action == color_action:
            self._change_tag_color(widget)
        elif action == move_up:
            self._move_tag_up(widget)
        elif action == move_down:
            self._move_tag_down(widget)
    
    def _change_tag_color(self, widget: DraggableTagItem) -> None:
        """Change tag color via color dialog."""
        from PyQt6.QtWidgets import QColorDialog
        current_color = QColor(widget.get_color())
        color = QColorDialog.getColor(current_color, self, f"Choose Color for '{widget.tag_name}'")
        if color.isValid():
            old_color = widget.get_color()
            new_color = color.name()
            if old_color != new_color:
                # Emit signal for undo/redo
                self.tag_color_changed_requested.emit(widget.tag_name, old_color, new_color)
    
    def _move_tag_up(self, widget: DraggableTagItem) -> None:
        try:
            idx = self._tag_widgets.index(widget)
            if idx > 0:
                self.move_tag_requested.emit(idx, idx - 1)
        except ValueError:
            pass
    
    def _move_tag_down(self, widget: DraggableTagItem) -> None:
        try:
            idx = self._tag_widgets.index(widget)
            if idx < len(self._tag_widgets) - 1:
                self.move_tag_requested.emit(idx, idx + 1)
        except ValueError:
            pass
    
    def _rebuild_tag_layout(self) -> None:
        """Rebuild the tag layout after reordering."""
        # Remove all widgets from layout (but don't delete them)
        while self.tags_layout.count() > 0:
            self.tags_layout.takeAt(0)
        
        # Re-add in new order
        for widget in self._tag_widgets:
            self.tags_layout.addWidget(widget)
        
        self.tags_layout.addStretch()
    
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
            # Emit signal for undo/redo (main.py will call rename_tag_item)
            self.tag_renamed_requested.emit(old_name, new_name)
    
    def _remove_tag(self, tag_name: str) -> None:
        """Remove a tag (emit signal for undo/redo)."""
        # Find tag data for undo
        tag_color = None
        tag_index = 0
        for i, tag_data in enumerate(self._tags):
            if tag_data["name"] == tag_name:
                tag_color = tag_data.get("color", "#607D8B")
                tag_index = i
                break
        
        # Emit signal for undo/redo (main.py will call remove_tag_by_name)
        self.tag_removed_requested.emit(tag_name, tag_color or "#607D8B", tag_index)
    
    def insert_tag(self, index: int, name: str, color: str = None) -> None:
        """Insert a tag at specific index."""
        tag_data = {"name": name, "color": color}
        self._tags.insert(index, tag_data)
        
        widget = DraggableTagItem(name, color=color)
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(lambda pos, w=widget: self._show_tag_menu(w))
        widget.color_changed.connect(self._on_tag_color_changed)
        
        self._tag_widgets.insert(index, widget)
        self.tags_layout.insertWidget(index, widget)
        self.tag_added.emit(name)

    def remove_tag_by_name(self, tag_name: str) -> None:
        """Remove a tag by name (called by undo/redo commands)."""
        # Find and remove from _tags list
        for tag_data in self._tags:
            if tag_data["name"] == tag_name:
                self._tags.remove(tag_data)
                break
            
        for widget in self._tag_widgets:
            if widget.tag_name == tag_name:
                self._tag_widgets.remove(widget)
                widget.deleteLater()
                break
        
        # Emit signal for node sync
        self.tag_removed.emit(tag_name)

    def rename_tag_item(self, old_name: str, new_name: str) -> None:
        """Rename a tag item."""
        # Find index
        idx = -1
        for i, tag in enumerate(self._tags):
            if tag["name"] == old_name:
                idx = i
                break
        
        if idx != -1:
            self._tags[idx]["name"] = new_name
            widget = self._tag_widgets[idx]
            widget.tag_name = new_name
            widget.setText(new_name)
            # Color stays the same - no need to regenerate
            self.tag_renamed.emit(old_name, new_name)

    def set_tag_color(self, tag_name: str, color: str) -> None:
        """Set color for a tag."""
        for i, tag in enumerate(self._tags):
            if tag["name"] == tag_name:
                tag["color"] = color
                widget = self._tag_widgets[i]
                widget.set_color(color)
                # Emit signal for node sync
                self.tag_color_changed.emit(tag_name, color)
                break

    def move_tag(self, from_index: int, to_index: int) -> None:
        """Move tag from index to index."""
        if 0 <= from_index < len(self._tags) and 0 <= to_index < len(self._tags):
            # Move in data list
            tag_data = self._tags.pop(from_index)
            self._tags.insert(to_index, tag_data)
            
            # Move in widget list
            widget = self._tag_widgets.pop(from_index)
            self._tag_widgets.insert(to_index, widget)
            
            self._rebuild_tag_layout()

    def set_tags(self, tags: list[dict]) -> None:
        """Set the tag list (for loading projects). Tags are dicts with 'name' and 'color'."""
        # Clear existing
        for widget in self._tag_widgets:
            widget.deleteLater()
        self._tag_widgets.clear()
        self._tags.clear()
        
        # Add new tags
        for tag_data in tags:
            tag_name = tag_data.get("name", "") if isinstance(tag_data, dict) else tag_data
            tag_color = tag_data.get("color") if isinstance(tag_data, dict) else None
            
            if not tag_name:
                continue
                
            self._tags.append({"name": tag_name, "color": tag_color})
            widget = DraggableTagItem(tag_name, color=tag_color)
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(lambda pos, w=widget: self._show_tag_menu(w))
            widget.color_changed.connect(self._on_tag_color_changed)
            self._tag_widgets.append(widget)
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, widget)
    
    def get_tags(self) -> list[dict]:
        """Get the current tag list with colors."""
        result = []
        for widget in self._tag_widgets:
            color = widget.get_color()
            result.append({
                "name": widget.tag_name,
                # Only store color if different from default
                "color": color if color != DraggableTagItem.DEFAULT_COLOR else None
            })
        return result


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
        if not LATEX2MATHML_AVAILABLE:
            return ""
        
        try:
            # Preprocess LaTeX to handle unsupported commands
            processed = self._preprocess_latex(latex)
            
            # Convert LaTeX to MathML using globally imported module
            mathml = latex2mathml.converter.convert(processed)
            return mathml
        except Exception:
            # Conversion failed (invalid LaTeX, etc.)
            return ""
    
    def _preprocess_latex(self, latex: str) -> str:
        """
        Preprocess LaTeX to handle commands not supported by latex2mathml.
        """
        import re
        
        result = latex
        
        # \pmb{x}, \pmb {x}, \pmb x -> \mathbf{x} (poor man's bold -> math bold)
        result = re.sub(r'\\pmb\s*\{([^}]*)\}', r'\\mathbf{\1}', result)
        result = re.sub(r'\\pmb\s+(\\\w+|\w)', r'\\mathbf{\1}', result)
        
        # \tag{n} -> remove (equation tags not needed in viewer)
        # Match all variations: \tag{1}, \tag 1, \tag1, \tag {1}, \tag{something}
        result = re.sub(r'\\tag\s*\{[^}]*\}', '', result)  # \tag{1} or \tag {1}
        result = re.sub(r'\\tag\s*(\d+)', '', result)  # \tag1 or \tag 1
        # Also handle \tag followed by word at end of line
        result = re.sub(r'\\tag\s*\w+\s*$', '', result, flags=re.MULTILINE)
        
        # \boldsymbol{x} -> \mathbf{x}
        result = re.sub(r'\\boldsymbol\s*\{([^}]*)\}', r'\\mathbf{\1}', result)
        
        # \bm{x} -> \mathbf{x}
        result = re.sub(r'\\bm\s*\{([^}]*)\}', r'\\mathbf{\1}', result)
        
        # \text{...} -> \mathrm{...} (more compatible)
        result = re.sub(r'\\text\s*\{([^}]*)\}', r'\\mathrm{\1}', result)
        
        # \operatorname{...} -> \mathrm{...}
        result = re.sub(r'\\operatorname\s*\{([^}]*)\}', r'\\mathrm{\1}', result)
        
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
    """A draggable module shape for the palette with customizable color."""
    
    color_changed = pyqtSignal(str, str)  # module_type, new_color
    
    def __init__(self, module_type: str, label: str, color: QColor, parent=None):
        super().__init__(label, parent)
        self.module_type = module_type
        self._color = color
        self._label = label
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedHeight(28)  # Match tag height
        self.setMinimumWidth(70)
        self.setContentsMargins(1, 1, 1, 1)  # Match tag margins
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self._update_style()
    
    def set_color(self, color: str) -> None:
        """Set the module color."""
        self._color = QColor(color)
        self._update_style()
    
    def get_color(self) -> str:
        """Get the current color as hex string."""
        return self._color.name()
    
    def _update_style(self) -> None:
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self._color.name()};
                color: white;
                border-radius: 6px;
                padding: 5px;
            }}
            QLabel:hover {{
                background-color: {self._color.darker(110).name()};
            }}
        """)
    
    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        change_color = menu.addAction("Change Color...")
        action = menu.exec(self.mapToGlobal(pos))
        
        if action == change_color:
            color = QColorDialog.getColor(self._color, self, f"Choose color for '{self._label}'")
            if color.isValid():
                self._color = color
                self._update_style()
                self.color_changed.emit(self.module_type, color.name())
    
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


class WaypointPaletteItem(QLabel):
    """A draggable waypoint item for connection bending."""
    
    def __init__(self, parent=None):
        super().__init__("Waypoint", parent) 
        self.module_type = "waypoint"
        self._color = QColor("#607D8B")
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedHeight(28)
        self.setMinimumWidth(75)
        self.setContentsMargins(8, 0, 8, 0)
        self.setToolTip("Waypoint - drag to create connection bend points")
        
        self._update_style()
    
    def set_color(self, color: str) -> None:
        """Update the waypoint palette color."""
        self._color = QColor(color)
        self._update_style()
    
    def _update_style(self) -> None:
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self._color.name()};
                color: white;
                border-radius: 14px;
                padding: 0 10px;
            }}
            QLabel:hover {{
                background-color: {self._color.darker(110).name()};
            }}
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(f"module:{self.module_type}")
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class GroupPaletteItem(QLabel):
    """A draggable group module with dashed border styling."""
    
    color_changed = pyqtSignal(str, str)  # module_type, new_color
    
    def __init__(self, parent=None):
        super().__init__("Group", parent)
        self.module_type = "group"
        self._color = QColor("#78909C")  # Blue-grey default
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedHeight(28)
        self.setMinimumWidth(60)
        self.setContentsMargins(1, 1, 1, 1)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self._update_style()
    
    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self._update_style()
    
    def get_color(self) -> str:
        return self._color.name()
    
    def _update_style(self) -> None:
        # Dashed border with semi-transparent background
        bg_color = QColor(self._color)
        bg_color.setAlpha(50)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 50);
                color: {self._color.darker(120).name()};
                border: 2px dashed {self._color.name()};
                padding: 3px 8px;
            }}
            QLabel:hover {{
                background-color: rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 80);
            }}
        """)
    
    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        change_color = menu.addAction("Change Color...")
        action = menu.exec(self.mapToGlobal(pos))
        
        if action == change_color:
            color = QColorDialog.getColor(self._color, self, "Choose color for 'Group'")
            if color.isValid():
                self._color = color
                self._update_style()
                self.color_changed.emit(self.module_type, color.name())
    
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText("module:group")
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ModulePalette(QWidget):
    """Palette of draggable module shapes with customizable colors."""
    
    color_changed = pyqtSignal(str, str)  # module_type, new_color
    
    DEFAULT_COLORS = {
        "input": "#4CAF50",
        "process": "#9C27B0",
        "decision": "#FF9800",
        "output": "#2196F3"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: dict[str, ModulePaletteItem] = {}
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
            ("input", "Input"),
            ("process", "Process"),
            ("decision", "Decision"),
            ("output", "Output"),
        ]
        
        for module_type, label_text in modules:
            color = QColor(self.DEFAULT_COLORS[module_type])
            item = ModulePaletteItem(module_type, label_text, color)
            item.color_changed.connect(self._on_item_color_changed)
            self._items[module_type] = item
            layout.addWidget(item)
        
        # Add separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #ccc; margin: 0 5px;")
        layout.addWidget(separator)
        
        # Group module (special styling)
        self.group_item = GroupPaletteItem()
        self.group_item.color_changed.connect(self._on_item_color_changed)
        layout.addWidget(self.group_item)
        
        # V3.9.0: Waypoint item
        self.waypoint_item = WaypointPaletteItem()
        layout.addWidget(self.waypoint_item)
        
        layout.addStretch()
        
        # Help text
        help_label = QLabel("Drag modules to canvas | Right-click to customize color")
        help_label.setStyleSheet("color: #999; font-style: italic;")
        layout.addWidget(help_label)
    
    def _on_item_color_changed(self, module_type: str, color: str) -> None:
        """Forward color change signal."""
        self.color_changed.emit(module_type, color)
    
    def set_colors(self, colors: dict) -> None:
        """Set module colors from project data."""
        for module_type, color in colors.items():
            if module_type in self._items:
                self._items[module_type].set_color(color)
            elif module_type == "group":
                self.group_item.set_color(color)
            elif module_type == "waypoint":
                self.waypoint_item.set_color(color)
    
    def set_color_for_type(self, module_type: str, color: str) -> None:
        """Set color for a module type programmatically."""
        if module_type in self._items:
            self._items[module_type].set_color(color)
        elif module_type == "group":
            self.group_item.set_color(color)
        elif module_type == "waypoint":
            self.waypoint_item.set_color(color)
        
        # Emit signal to update existing nodes
        self.color_changed.emit(module_type, color)

    def get_colors(self) -> dict:
        """Get current module colors."""
        colors = {mt: item.get_color() for mt, item in self._items.items()}
        colors["group"] = self.group_item.get_color()
        return colors
    
    def get_color(self, module_type: str) -> str:
        """Get color for a specific module type."""
        if module_type == "group":
            return self.group_item.get_color()
        if module_type in self._items:
            return self._items[module_type].get_color()
        return self.DEFAULT_COLORS.get(module_type, "#607D8B")


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
